#!/usr/bin/env python3
"""
Sensibilidad de la variante seleccionada (momentum alcista de apertura).

No es busqueda de parametros: la variante ya esta elegida. Esto
comprueba si el resultado depende de un valor concreto y fragil o si
se sostiene en una meseta. Si solo funciona en 15 minutos exactos y
muere en 10 y en 20, es sobreajuste y hay que descartarlo.
"""
import glob
import os
import numpy as np
import pandas as pd

RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")
PRE_INI, PRE_FIN = 8 * 60, 9 * 60 + 29
OPEN_MIN = 9 * 60 + 30
END_MIN = 16 * 60
COST_BP = 0.40


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
    return df[(df["dow"] < 5) & (df["tod"] >= PRE_INI) & (df["tod"] <= END_MIN)]


def sesiones(df):
    out = []
    for fecha, g in df.groupby("fecha", sort=True):
        tod = g["tod"].to_numpy()
        o = g["open"].to_numpy(float)
        c = g["close"].to_numpy(float)
        post = tod >= OPEN_MIN
        if post.sum() < 300:
            continue
        i0 = int(np.argmax(post))
        out.append(dict(fecha=fecha, tod=tod, o=o, c=c,
                        apertura=float(o[i0]), cierre=float(c[post][-1])))
    return out


def prueba(ses, lo, hi, mom_win, umbral_bp, salida):
    sub = [s for s in ses if lo <= s["fecha"].year <= hi]
    anos = len(sub) / 252.0
    r = []
    for s in sub:
        idx = np.where(s["tod"] >= OPEN_MIN + mom_win)[0]
        if not len(idx):
            continue
        im = int(idx[0])
        push = (s["o"][im] / s["apertura"] - 1) * 1e4
        if push <= umbral_bp:
            continue
        if salida == "cierre":
            px = s["cierre"]
        else:
            j = np.where(s["tod"] >= OPEN_MIN + mom_win + int(salida))[0]
            px = s["c"][int(j[0])] if len(j) else s["c"][-1]
        r.append((px / s["o"][im] - 1) * 1e4 - COST_BP)

    x = np.array(r) / 1e4
    n = len(x)
    if n < 50:
        return None
    tot = np.expm1(np.log1p(x).sum())
    cagr = 100 * ((1 + tot) ** (1 / anos) - 1)
    vol = 100 * x.std(ddof=1) * np.sqrt(n / anos)
    return n, cagr, vol, (cagr / vol if vol else np.nan), 100 * (x > 0).mean()


def tabla(ses, titulo, cab, valores, fn):
    print("\n%s" % titulo)
    print("  %-9s %5s %8s %8s %8s %9s" % (cab, "n", "CAGR", "vol",
                                          "Sharpe", "acierto"))
    print("  " + "-" * 52)
    for v in valores:
        r = fn(v)
        if r:
            print("  %-9s %5d %+7.2f%% %7.2f%% %8.3f %8.2f%%"
                  % (str(v), r[0], r[1], r[2], r[3], r[4]))


def main():
    ses = sesiones(cargar())
    print("Sesiones: %d  (%s -> %s)"
          % (len(ses), ses[0]["fecha"], ses[-1]["fecha"]))

    tabla(ses, "VENTANA DE MOMENTUM  (2020-2026, salida al cierre)", "minutos",
          [5, 10, 15, 20, 30, 45, 60],
          lambda v: prueba(ses, 2020, 2026, v, 0.0, "cierre"))

    tabla(ses, "MISMA REJILLA EN 2011-2019  (fuera de la ventana de decision)",
          "minutos", [5, 10, 15, 20, 30, 45, 60],
          lambda v: prueba(ses, 2011, 2019, v, 0.0, "cierre"))

    tabla(ses, "UMBRAL DE EMPUJE  (ventana 15 min, 2020-2026)", "bp",
          [0.0, 5.0, 10.0, 20.0, 40.0],
          lambda v: prueba(ses, 2020, 2026, 15, v, "cierre"))

    tabla(ses, "SALIDA  (ventana 15 min, umbral 0, 2020-2026)", "minutos",
          [60, 120, 169, 240, "cierre"],
          lambda v: prueba(ses, 2020, 2026, 15, 0.0, v))


if __name__ == "__main__":
    main()
