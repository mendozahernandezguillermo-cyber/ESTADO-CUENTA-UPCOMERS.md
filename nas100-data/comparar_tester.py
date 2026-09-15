#!/usr/bin/env python3
"""
Compara like-with-like contra el Probador de MT5.

El Probador corrio 2026-01-16 -> 2026-08-28 sobre NACUSD.c y dio:
    37 operaciones, 64.86% acierto, payoff 0.467, neto -96.38 sobre 25.000
    = -0.385% en total, -2.60 por operacion

Con riesgo 0.5% por operacion y stop 2%, un movimiento de 1 bp del
indice equivale a 0.0025% del equity. Asi que -2.60 sobre 25.000
(-0.0104% del equity) son -4.16 bp por operacion.

Esta es la cifra que hay que reproducir.
"""
import glob
import os
import datetime as dt
import numpy as np
import pandas as pd

RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")
OPEN_MIN = 9 * 60 + 30
END_MIN = 16 * 60
MOM_WIN = 15
PUSH_BP = 5.0
STOP_PCT = 2.0
COST_BP = 0.40

INI = dt.date(2026, 1, 16)
FIN = dt.date(2026, 8, 28)


def cargar():
    files = sorted(glob.glob(os.path.join(RAW, "*.csv")))
    partes = [pd.read_csv(f, usecols=["timestamp", "open", "high",
                                      "low", "close"]) for f in files]
    df = pd.concat(partes, ignore_index=True)
    df = df.drop_duplicates("timestamp").sort_values("timestamp")
    et = pd.to_datetime(df["timestamp"], unit="ms", utc=True) \
           .dt.tz_convert("America/New_York")
    df = df.assign(fecha=et.dt.date,
                   tod=et.dt.hour * 60 + et.dt.minute,
                   dow=et.dt.dayofweek)
    return df[(df["dow"] < 5) & (df["tod"] >= OPEN_MIN) & (df["tod"] <= END_MIN)]


def correr(df, ini, fin):
    ops, stops, sesiones, saltadas = [], 0, 0, 0
    for fecha, g in df.groupby("fecha", sort=True):
        if not (ini <= fecha <= fin):
            continue
        tod = g["tod"].to_numpy()
        o = g["open"].to_numpy(float)
        l = g["low"].to_numpy(float)
        c = g["close"].to_numpy(float)
        if len(tod) < 300:
            continue
        sesiones += 1
        idx = np.where(tod >= OPEN_MIN + MOM_WIN)[0]
        if not len(idx):
            continue
        im = int(idx[0])
        entrada = float(o[im])
        push = (entrada / float(o[0]) - 1) * 1e4
        if push <= PUSH_BP:
            saltadas += 1
            continue
        stop = entrada * (1 - STOP_PCT / 100.0)
        if float(l[im:].min()) <= stop:
            r = -STOP_PCT * 100.0 - COST_BP
            stops += 1
        else:
            r = (float(c[-1]) / entrada - 1) * 1e4 - COST_BP
        ops.append(r)
    return np.array(ops), stops, sesiones, saltadas


def main():
    df = cargar()
    x, stops, ses, salt = correr(df, INI, FIN)
    n = len(x)
    gan = x[x > 0]
    per = x[x <= 0]

    print("PYTHON, mismas fechas que el Probador (%s -> %s)" % (INI, FIN))
    print("=" * 66)
    print("  sesiones evaluadas ....... %d" % ses)
    print("  saltadas por empuje ...... %d" % salt)
    print("  OPERACIONES .............. %d   (%.1f%% de las sesiones)"
          % (n, 100.0 * n / ses))
    print("  acierto .................. %.2f%%" % (100.0 * len(gan) / n))
    print("  ganancia media ........... %+.2f bp" % gan.mean())
    print("  perdida media ............ %+.2f bp" % per.mean())
    print("  payoff ................... %.3f" % (gan.mean() / abs(per.mean())))
    print("  MEDIA POR OPERACION ...... %+.2f bp" % x.mean())
    print("  total .................... %+.1f bp" % x.sum())
    print("  stop 2%% tocado ........... %d" % stops)
    print()
    print("  MT5 dijo: 37 ops, 64.86%% acierto, payoff 0.467, -4.16 bp/op")
    print()

    # en dinero, con el mismo dimensionado del EA
    eq = 25000.0
    riesgo = 0.005          # 0.5% por operacion
    # 1 bp de indice = riesgo/200bp del equity
    eur_por_bp = eq * riesgo / (STOP_PCT * 100.0)
    print("  equivalente en dinero con equity 25.000 y riesgo 0.5%%:")
    print("    %.2f $ por bp  ->  neto %+.2f $" % (eur_por_bp,
                                                   x.sum() * eur_por_bp))
    print("    MT5 dio -96.38 $")

    # cuanto de esto es el periodo y cuanto seria lo normal
    print()
    print("Contraste: la misma regla en periodos de 7.5 meses, 2011-2026")
    todos = []
    for a in range(2011, 2027):
        for m0 in (1, 6):
            i = dt.date(a, m0, 16)
            f = i + dt.timedelta(days=225)
            xx, _, s, _ = correr(df, i, f)
            if len(xx) >= 20:
                todos.append((i, len(xx), xx.mean(), xx.sum()))
    med = np.array([t[2] for t in todos])
    print("  %d ventanas de ~7.5 meses" % len(todos))
    print("  media por operacion: mediana %+.2f bp   p10 %+.2f   p90 %+.2f"
          % (np.median(med), np.percentile(med, 10), np.percentile(med, 90)))
    print("  ventanas con media NEGATIVA: %d de %d (%.0f%%)"
          % ((med < 0).sum(), len(med), 100.0 * (med < 0).mean()))
    peor = min(todos, key=lambda t: t[2])
    print("  peor ventana: %s  %+.2f bp/op" % (peor[0], peor[2]))


if __name__ == "__main__":
    main()
