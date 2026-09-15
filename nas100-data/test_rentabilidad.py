#!/usr/bin/env python3
"""
TEST DE RENTABILIDAD PRE-REGISTRADO

Regla, derivada ENTERAMENTE de los 890 timestamps de entrada de joxemi
(no de estos precios):

    En cada cierre de vela M5, calcular la posicion del precio dentro
    del rango del dia acumulado HASTA LA VELA ANTERIOR.
      posicion >= 0.80  ->  LARGO
      posicion <= 0.20  ->  CORTO
    Mantener 75 minutos. Maximo 2 operaciones por dia.

Evidencia que la justifica (entradas reales vs controles emparejados
por hora del dia):
    posicion en el rango, largos:  0.87 vs 0.56   t = +34.7
    posicion en el rango, cortos:  0.14 vs 0.57   t = -37.0
    mediana de la posicion: 0.904 en largos, 0.110 en cortos
    duracion mediana: 65-82 min
    1.83 entradas por dia operado

CAUSALIDAD: el rango se calcula con las velas ANTERIORES a la de
entrada, nunca incluyendo la propia. En el analisis forense usaba la
vela en curso, lo cual era valido para comparar entradas contra
controles (mismo sesgo en ambos) pero seria mirar el futuro aqui.

LIMITACION: precio = indice cash de Dukascopy. joxemi opera el CFD
"NASDAQ 100 (Mini)" de Darwinex, derivado del futuro.
"""
import glob
import os
import numpy as np
import pandas as pd
from scipy import stats

RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")

UMBRAL = 0.80        # pre-registrado
HOLD = 75            # pre-registrado (minutos)
MAX_DIA = 2          # pre-registrado
MIN_BARS = 60        # minutos de dia transcurridos antes de operar
COST_BP = 0.40


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
        out.append((fecha, T, g["open"].to_numpy(float),
                    g["high"].to_numpy(float), g["low"].to_numpy(float)))
    return out


def correr(D, umbral, hold, lo_a, hi_a, solo_dir=None):
    ops = []
    for fecha, T, O, H, L in D:
        if not (lo_a <= fecha.year <= hi_a):
            continue
        n = len(T)
        j = 0
        # arrancar tras MIN_BARS minutos de dia
        while j < n and T[j] < T[0] + MIN_BARS:
            j += 1
        ndia = 0
        while j < n - 1 and ndia < MAX_DIA:
            if T[j] % 5 != 0:            # solo cierres de vela M5
                j += 1
                continue
            hi = H[:j].max()             # SIN incluir la vela j
            lo = L[:j].min()
            rng = hi - lo
            if rng <= 0:
                j += 1
                continue
            px = O[j]
            pos = (px - lo) / rng
            d = 0
            if pos >= umbral:
                d = 1
            elif pos <= 1.0 - umbral:
                d = -1
            if d == 0 or (solo_dir is not None and d != solo_dir):
                j += 1
                continue

            k = np.searchsorted(T, T[j] + hold)
            if k >= n:
                k = n - 1
            if k <= j:
                j += 1
                continue
            r = (O[k] / px - 1) * 1e4 * d - COST_BP
            ops.append((fecha, T[j], d, r, pos))
            ndia += 1
            j = k + 1                    # sin solapar posiciones
    return pd.DataFrame(ops, columns=["fecha", "tod", "dir", "bp", "pos"])


def linea(t_, etq, anios):
    if len(t_) < 30:
        print("  %-26s n=%d insuficiente" % (etq, len(t_)))
        return
    x = t_["bp"].to_numpy()
    t, p2 = stats.ttest_1samp(x, 0.0)
    p = p2 / 2 if t > 0 else 1 - p2 / 2
    ops_ano = len(x) / anios
    anual = x.mean() * ops_ano / 100.0
    print("  %-26s n=%5d  %5.0f op/ano  media=%+7.2f bp  t=%+6.2f  "
          "p=%.5f  acierto=%5.2f%%  anual=%+7.2f%%"
          % (etq, len(x), ops_ano, x.mean(), t, p,
             100.0 * (x > 0).mean(), anual))


def main():
    df = cargar()
    D = dias(df)
    print("Dias: %d   (%s -> %s)" % (len(D), D[0][0], D[-1][0]))
    print()

    per = [(2011, 2026, "TODO 2011-2026", 14.6),
           (2011, 2019, "2011-2019", 8.3),
           (2020, 2024, "2020-2024", 5.0),
           (2025, 2026, "2025-2026 (su epoca)", 1.65)]

    print("=" * 108)
    print("  PRIMARIA: umbral %.2f, mantener %d min, ambas direcciones"
          % (UMBRAL, HOLD))
    print("=" * 108)
    for a, b, etq, an in per:
        linea(correr(D, UMBRAL, HOLD, a, b), etq, an)

    print()
    print("=" * 108)
    print("  DESGLOSE por direccion (muestra completa)")
    print("=" * 108)
    for d, nom in [(1, "solo LARGOS"), (-1, "solo CORTOS")]:
        linea(correr(D, UMBRAL, HOLD, 2011, 2026, solo_dir=d), nom, 14.6)

    print()
    print("=" * 108)
    print("  CONTEXTO: sensibilidad (declarado; no es la prueba primaria)")
    print("=" * 108)
    for u in [0.70, 0.80, 0.90, 0.95]:
        linea(correr(D, u, HOLD, 2011, 2026), "umbral=%.2f" % u, 14.6)
    print()
    for h in [30, 45, 75, 120, 180]:
        linea(correr(D, UMBRAL, h, 2011, 2026), "hold=%d min" % h, 14.6)

    print()
    t_ = correr(D, UMBRAL, HOLD, 2011, 2026)
    t_.to_csv(os.path.join(os.path.dirname(RAW), "ops_regla_joxemi.csv"),
              index=False)
    print("Guardado ops_regla_joxemi.csv (%d operaciones)" % len(t_))

    # curva de equity y drawdown
    x = t_.sort_values(["fecha", "tod"])["bp"].to_numpy() / 1e4
    eq = np.log1p(x).cumsum()
    mdd = float((np.maximum.accumulate(eq) - eq).max())
    print("  retorno acumulado sin apalancar: %+.1f%%   maxDD: %.1f%%"
          % (100 * (np.exp(eq[-1]) - 1), 100 * mdd))


if __name__ == "__main__":
    main()
