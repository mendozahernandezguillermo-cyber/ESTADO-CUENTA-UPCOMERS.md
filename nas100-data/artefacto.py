#!/usr/bin/env python3
"""
Prueba si el "momentum de apertura" es un artefacto del calculo del
indice cash en los primeros minutos.

El NASDAQ 100 cash se computa con los precios de sus 100 componentes.
En la apertura no abren todos a la vez, asi que el indice publicado
persigue durante unos minutos al valor que el futuro ya marcaba. Eso
produce un empuje inicial que NO es momentum de mercado: es el indice
poniendose al dia consigo mismo. Y no seria replicable en un CFD
derivado del E-mini, que cotiza toda la noche.

TEST: desplazar el ancla de medida unos minutos despues de la apertura.
  - Si el efecto sobrevive  -> es momentum real.
  - Si el efecto se hunde   -> era el artefacto del calculo del indice.

Se mide siempre una ventana de 15 minutos y salida en la campana.
"""
import glob
import os
import numpy as np
import pandas as pd
from scipy import stats

RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")
OPEN_MIN = 9 * 60 + 30
END_MIN = 16 * 60
WIN = 15
PUSH_BP = 5.0
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
    return df[(df["dow"] < 5) & (df["tod"] >= OPEN_MIN - 60) &
              (df["tod"] <= END_MIN)]


def sesiones(df):
    out = []
    for fecha, g in df.groupby("fecha", sort=True):
        tod = g["tod"].to_numpy()
        o = g["open"].to_numpy(float)
        c = g["close"].to_numpy(float)
        post = tod >= OPEN_MIN
        if post.sum() < 300:
            continue
        out.append(dict(fecha=fecha, tod=tod, o=o, c=c,
                        cierre=float(c[post][-1])))
    return out


def px_en(s, minuto):
    idx = np.where(s["tod"] >= minuto)[0]
    return (float(s["o"][int(idx[0])]) if len(idx) else None)


def correr(ses, ancla_off, lo, hi):
    """ancla_off = minutos despues de la apertura donde empieza a medir."""
    r = []
    ini = OPEN_MIN + ancla_off
    for s in ses:
        if not (lo <= s["fecha"].year <= hi):
            continue
        p0 = px_en(s, ini)
        p1 = px_en(s, ini + WIN)
        if p0 is None or p1 is None or p0 <= 0:
            continue
        push = (p1 / p0 - 1) * 1e4
        if push <= PUSH_BP:
            continue
        r.append((s["cierre"] / p1 - 1) * 1e4 - COST_BP)
    return np.array(r)


def linea(x, ses_n, etiqueta):
    n = len(x)
    if n < 30:
        print("  %-14s  n=%d  (insuficiente)" % (etiqueta, n))
        return
    t, p2 = stats.ttest_1samp(x, 0.0)
    p = p2 / 2 if t > 0 else 1 - p2 / 2
    print("  %-14s %5d %6.1f%% %+8.2f %7.1f %+6.2f %8.4f %7.2f%%"
          % (etiqueta, n, 100.0 * n / ses_n, x.mean(), x.std(ddof=1),
             t, p, 100.0 * (x > 0).mean()))


def main():
    ses = sesiones(cargar())
    print("Sesiones: %d" % len(ses))

    for lo, hi, nom in [(2011, 2026, "MUESTRA COMPLETA 2011-2026"),
                        (2020, 2026, "2020-2026")]:
        sn = len([s for s in ses if lo <= s["fecha"].year <= hi])
        print("\n%s   (ventana de medida = 15 min, salida en campana)" % nom)
        print("  %-14s %5s %7s %8s %7s %6s %8s %8s"
              % ("ancla", "n", "%ses", "media_bp", "sd", "t", "p", "acierto"))
        print("  " + "-" * 68)
        for off in [0, 1, 2, 3, 5, 10, 15, 30]:
            x = correr(ses, off, lo, hi)
            linea(x, sn, "9:30+%dmin" % off)

    print("\nLECTURA: si la media_bp y la t caen mucho al mover el ancla de")
    print("0 a 2-3 minutos, el efecto vivia en el calculo del indice en la")
    print("apertura y NO es replicable en un CFD sobre el futuro.")


if __name__ == "__main__":
    main()
