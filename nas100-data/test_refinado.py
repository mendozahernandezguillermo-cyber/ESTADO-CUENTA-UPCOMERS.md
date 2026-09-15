#!/usr/bin/env python3
"""
SEGUNDA (Y ULTIMA) PRUEBA PRE-REGISTRADA

La regla de posicion-en-rango dispara 513 veces al ano; joxemi entra unas
230 veces al ano en NASDAQ. Es decir: la condicion que identificamos es
NECESARIA pero no SUFICIENTE. Sobra la mitad. El filtro que falta es
donde podria estar el edge.

El analisis forense senala exactamente un filtro, y solo para los cortos:

    rango del dia, cortos:  184.4 bp en sus entradas vs 131.9 en controles   t = +7.68
    volatilidad 30 min:       4.72 vs 3.24                                    t = +5.90
    los mismos rasgos en sus LARGOS:  +14.4 bp (t=2.99) y +0.11 (t=0.67)

O sea: sus cortos exigen dia ancho y volatil; sus largos no. Eso encaja
con que nuestros cortos sin filtrar pierdan (t=-2.19).

REGLA REFINADA:
    LARGO  si posicion >= 0.80                       (sin filtro de vol)
    CORTO  si posicion <= 0.20 Y el rango del dia
           hasta ese momento supera su mediana movil de 20 dias por
           el factor observado en sus datos (184/132 = 1.40)

Ademas se prueba el efecto de exigir el filtro a las dos direcciones,
para no elegir a posteriori.

Esta es la ultima prueba. Si sale plana, la conclusion es que la regla
identificada describe QUE hace joxemi pero no contiene su ventaja.
"""
import glob
import os
import numpy as np
import pandas as pd
from scipy import stats

RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")

UMBRAL = 0.80
HOLD = 75
MAX_DIA = 2
MIN_BARS = 60
COST_BP = 0.40
FACTOR = 1.40          # 184.4 / 131.9 medido en sus cortos
LOOKBACK = 20


def cargar():
    files = sorted(glob.glob(os.path.join(RAW, "*.csv")))
    partes = [pd.read_csv(f, usecols=["timestamp", "open", "high",
                                      "low", "close"]) for f in files]
    df = pd.concat(partes, ignore_index=True)
    df = df.drop_duplicates("timestamp").sort_values("timestamp")
    ny = pd.to_datetime(df["timestamp"], unit="ms", utc=True) \
           .dt.tz_convert("America/New_York")
    df = df.assign(fecha=ny.dt.date,
                   tod=ny.dt.hour * 60 + ny.dt.minute,
                   dow=ny.dt.dayofweek)
    return df[df["dow"] < 5]


def dias(df):
    out = []
    for fecha, g in df.groupby("fecha", sort=True):
        T = g["tod"].to_numpy()
        if len(T) < 400:
            continue
        O = g["open"].to_numpy(float)
        H = g["high"].to_numpy(float)
        L = g["low"].to_numpy(float)
        rng_dia = 1e4 * (H.max() - L.min()) / O[0]
        out.append((fecha, T, O, H, L, rng_dia))
    return out


def correr(D, filtro_largos, filtro_cortos, lo_a, hi_a):
    """filtro_* : exigir rango ancho para esa direccion."""
    ops = []
    hist = []                     # rangos diarios previos
    for fecha, T, O, H, L, rng_dia in D:
        med = float(np.median(hist[-LOOKBACK:])) if len(hist) >= LOOKBACK else None
        hist.append(rng_dia)
        if not (lo_a <= fecha.year <= hi_a) or med is None:
            continue

        n = len(T)
        j = 0
        while j < n and T[j] < T[0] + MIN_BARS:
            j += 1
        ndia = 0
        while j < n - 1 and ndia < MAX_DIA:
            if T[j] % 5 != 0:
                j += 1
                continue
            hi = H[:j].max()
            lo = L[:j].min()
            rng = hi - lo
            if rng <= 0:
                j += 1
                continue
            px = O[j]
            pos = (px - lo) / rng
            rng_hasta_bp = 1e4 * rng / px
            ancho = rng_hasta_bp >= FACTOR * med

            d = 0
            if pos >= UMBRAL and (ancho or not filtro_largos):
                d = 1
            elif pos <= 1.0 - UMBRAL and (ancho or not filtro_cortos):
                d = -1
            if d == 0:
                j += 1
                continue

            k = np.searchsorted(T, T[j] + HOLD)
            if k >= n:
                k = n - 1
            if k <= j:
                j += 1
                continue
            ops.append((fecha, T[j], d,
                        (O[k] / px - 1) * 1e4 * d - COST_BP))
            ndia += 1
            j = k + 1
    return pd.DataFrame(ops, columns=["fecha", "tod", "dir", "bp"])


def linea(t_, etq, anios):
    if len(t_) < 30:
        print("  %-34s n=%d insuficiente" % (etq, len(t_)))
        return
    x = t_["bp"].to_numpy()
    t, p2 = stats.ttest_1samp(x, 0.0)
    p = p2 / 2 if t > 0 else 1 - p2 / 2
    print("  %-34s n=%5d  %4.0f op/ano  media=%+7.2f bp  t=%+6.2f  "
          "p=%.5f  acierto=%5.2f%%  anual=%+7.2f%%"
          % (etq, len(x), len(x) / anios, x.mean(), t, p,
             100.0 * (x > 0).mean(),
             x.mean() * (len(x) / anios) / 100.0))


def main():
    D = dias(cargar())
    print("Dias: %d" % len(D))
    print()
    print("=" * 112)
    print("  REGLA REFINADA: largos sin filtro, cortos solo en dia ancho "
          "(rango >= 1.40 x mediana 20d)")
    print("=" * 112)
    for a, b, etq, an in [(2011, 2026, "TODO 2011-2026", 14.6),
                          (2011, 2019, "2011-2019", 8.3),
                          (2020, 2024, "2020-2024", 5.0),
                          (2025, 2026, "2025-2026 (su epoca)", 1.65)]:
        linea(correr(D, False, True, a, b), etq, an)

    print()
    print("=" * 112)
    print("  CONTROLES: para no haber elegido el filtro a posteriori")
    print("=" * 112)
    linea(correr(D, False, False, 2011, 2026), "sin filtro (la primaria)", 14.6)
    linea(correr(D, True, True, 2011, 2026), "filtro en AMBAS direcciones", 14.6)
    linea(correr(D, True, False, 2011, 2026), "filtro solo en LARGOS", 14.6)
    linea(correr(D, False, True, 2011, 2026), "filtro solo en CORTOS", 14.6)

    print()
    print("=" * 112)
    print("  DESGLOSE de la refinada por direccion")
    print("=" * 112)
    t_ = correr(D, False, True, 2011, 2026)
    for d, nom in [(1, "largos"), (-1, "cortos (dia ancho)")]:
        linea(t_[t_["dir"] == d], nom, 14.6)

    x = t_.sort_values(["fecha", "tod"])["bp"].to_numpy() / 1e4
    eq = np.log1p(x).cumsum()
    mdd = float((np.maximum.accumulate(eq) - eq).max())
    print()
    print("  acumulado sin apalancar: %+.1f%%   maxDD: %.1f%%"
          % (100 * (np.exp(eq[-1]) - 1), 100 * mdd))


if __name__ == "__main__":
    main()
