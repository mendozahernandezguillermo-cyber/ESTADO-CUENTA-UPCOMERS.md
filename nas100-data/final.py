#!/usr/bin/env python3
"""
Validacion final con los parametros exactos del EA que se entrega:
  ventana de momentum 15 min, umbral 5 bp, salida en la campana,
  stop de catastrofe 2% del precio, coste 0.40 bp ida+vuelta.

Comprueba tambien cuantas veces se toca el stop, porque el backtest
original no llevaba stop y anadirlo cambia la estrategia.
"""
import glob
import os
import numpy as np
import pandas as pd
from scipy import stats

RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")
OPEN_MIN = 9 * 60 + 30
END_MIN = 16 * 60
MOM_WIN = 15
PUSH_BP = 5.0
STOP_PCT = 2.0
COST_BP = 0.40
SWAP_ANUAL = 4.56


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


def correr(df, lo, hi):
    ops, stops, prev = [], 0, None
    dias = 0
    bh = []
    for fecha, g in df.groupby("fecha", sort=True):
        if not (lo <= fecha.year <= hi):
            continue
        tod = g["tod"].to_numpy()
        o = g["open"].to_numpy(float)
        l = g["low"].to_numpy(float)
        c = g["close"].to_numpy(float)
        if len(tod) < 300:
            continue
        dias += 1
        cierre = float(c[-1])
        if prev:
            bh.append(np.log(cierre / prev))
        prev = cierre

        idx = np.where(tod >= OPEN_MIN + MOM_WIN)[0]
        if not len(idx):
            continue
        im = int(idx[0])
        entrada = float(o[im])
        push = (entrada / float(o[0]) - 1) * 1e4
        if push <= PUSH_BP:
            continue

        stop = entrada * (1 - STOP_PCT / 100.0)
        peor = float(l[im:].min())
        if peor <= stop:
            r = -STOP_PCT * 100.0 - COST_BP     # en bp
            stops += 1
        else:
            r = (cierre / entrada - 1) * 1e4 - COST_BP
        ops.append(r)

    return np.array(ops) / 1e4, stops, dias, np.array(bh)


def resumen(x, stops, dias, bh, nom):
    anos = dias / 252.0
    n = len(x)
    tot = np.expm1(np.log1p(x).sum())
    cagr = 100 * ((1 + tot) ** (1 / anos) - 1)
    vol = 100 * x.std(ddof=1) * np.sqrt(n / anos)
    eq = np.log1p(x).cumsum()
    mdd = 100 * float((np.maximum.accumulate(eq) - eq).max())
    t, p2 = stats.ttest_1samp(x, 0.0)

    bh_cagr = 100 * (np.exp(bh.sum() / anos) - 1) - SWAP_ANUAL
    bh_vol = 100 * bh.std(ddof=1) * np.sqrt(252)
    eqb = bh.cumsum()
    bh_mdd = 100 * float((np.maximum.accumulate(eqb) - eqb).max())

    print("\n--- %s  (%d sesiones, %.1f anos) ---" % (nom, dias, anos))
    print("  EA          n=%4d  op/ano=%3.0f  CAGR=%+6.2f%%  vol=%5.2f%%  "
          "Sharpe=%.3f  maxDD=%5.1f%%  acierto=%5.2f%%  t=%+.2f"
          % (n, n / anos, cagr, vol, cagr / vol, mdd,
             100 * (x > 0).mean(), t))
    print("  comprar/man          exposicion 100%%  CAGR=%+6.2f%%  vol=%5.2f%%  "
          "Sharpe=%.3f  maxDD=%5.1f%%" % (bh_cagr, bh_vol,
                                          bh_cagr / bh_vol, bh_mdd))
    print("  stop 2%% tocado: %d veces (%.1f%% de las operaciones)"
          % (stops, 100.0 * stops / n if n else 0))
    print("  ratio maxDD EA / comprar-mantener: %.2f" % (mdd / bh_mdd))
    print("  exposicion: %.1f%% de las sesiones, ~%.1f%% del calendario"
          % (100.0 * n / dias, 100.0 * n / dias * 6.5 / 24.0))


def main():
    df = cargar()
    for lo, hi, nom in [(2011, 2019, "FUERA DE LA VENTANA DE SELECCION 2011-2019"),
                        (2020, 2026, "VENTANA DE SELECCION 2020-2026"),
                        (2023, 2026, "SUBVENTANA 2023-2026"),
                        (2011, 2026, "MUESTRA COMPLETA 2011-2026")]:
        x, st, dias, bh = correr(df, lo, hi)
        resumen(x, st, dias, bh, nom)


if __name__ == "__main__":
    main()
