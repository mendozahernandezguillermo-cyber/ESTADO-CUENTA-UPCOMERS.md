#!/usr/bin/env python3
"""
ANALISIS FORENSE DE LAS SALIDAS de joxemi.

Las entradas ya estan resueltas: banda extrema del rango del dia, en
cierres M5, t = 34.7 / -37.0. Y esa regla sola no gana dinero
(t = 0.52 sobre 15 anos, y la replica en el broker dio PF 0.95).

Si su ventaja existe, tiene que estar en la SELECCION (toma ~230 de las
~490 oportunidades) o en las SALIDAS. Aqui atacamos las salidas.

El journal da las transiciones de salida de NASDAQ con timestamp exacto,
asi que cada operacion queda emparejada entrada -> salida.

PRUEBA PRINCIPAL, la que discrimina de verdad:
  para cada operacion, calcular que habria pasado cerrando a 15, 30, 45,
  60, 75, 90, 120, 150, 180 y 240 minutos, y comparar con su cierre real.
  Si su cierre real bate a TODAS las alternativas fijas, hay habilidad.
  Si queda en medio de ellas, su salida es indistinguible de un reloj.

Esto reconstruye el chart CLOSE_STRATEGY de Raw DARWIN Data, que no
tenemos porque el FTP exige ser cliente y Darwinex no opera en Mexico.

LIMITACION: precio = indice cash de Dukascopy; el opera el CFD del
futuro de Darwinex.
"""
import glob
import os
import numpy as np
import pandas as pd
from scipy import stats

RAW = "/projects/sandbox/nas100-data/raw"
ALTS = [15, 30, 45, 60, 75, 90, 120, 150, 180, 240]


def cargar_precio():
    files = sorted(glob.glob(os.path.join(RAW, "*.csv")))
    partes = [pd.read_csv(f, usecols=["timestamp", "open", "high",
                                      "low", "close"]) for f in files]
    df = pd.concat(partes, ignore_index=True)
    df = df.drop_duplicates("timestamp").sort_values("timestamp")
    return df.reset_index(drop=True)


def main():
    pr = cargar_precio()
    # Todo en milisegundos epoch: los dos ficheros vienen asi de origen y
    # se evitan los problemas de tz-naive / tz-aware.
    T = pr["timestamp"].to_numpy(np.int64)
    O = pr["open"].to_numpy(float)
    H = pr["high"].to_numpy(float)
    L = pr["low"].to_numpy(float)
    print("Velas de precio: %d" % len(T))

    #--- reconstruir entradas Y salidas del journal ------------------
    import json
    with open("j1.json") as f:
        raw = json.load(f)
    J = pd.DataFrame(raw, columns=["c%d" % i for i in range(11)])
    J["ms"] = J["c1"].astype(np.int64)
    J = J.sort_values("ms").reset_index(drop=True)

    def nas(txt):
        if not isinstance(txt, str) or "NASDAQ" not in txt:
            return None
        for p in txt.split(","):
            p = p.strip()
            if "NASDAQ" in p:
                return 1 if p.startswith("+") else (-1 if p.startswith("-") else 0)
        return None

    J["nas"] = J["c9"].apply(nas)
    prev = J["nas"].shift(1)
    ent = np.where((J["nas"].notna() & prev.isna()).to_numpy())[0]
    sal = np.where((J["nas"].isna() & prev.notna()).to_numpy())[0]

    ops = []
    for i in ent:
        j = sal[sal > i]
        if not len(j):
            continue
        ops.append((int(J["ms"].iloc[i]), int(J["ms"].iloc[int(j[0])]),
                    int(J["nas"].iloc[i])))
    print("Operaciones emparejadas entrada->salida: %d" % len(ops))
    print()

    #--- calcular resultados reales y alternativos -------------------
    filas = []
    for t_in, t_out, d in ops:
        if d == 0:
            continue
        i = int(np.searchsorted(T, t_in))
        k = int(np.searchsorted(T, t_out))
        if i >= len(T) or k >= len(T) or k <= i:
            continue
        # tolerancia: la vela encontrada no debe estar a mas de 5 min
        if abs(T[i] - t_in) > 5 * 60 * 1000:
            continue
        p_in = O[i]
        if p_in <= 0:
            continue

        real = (O[k] / p_in - 1) * 1e4 * d
        dur = (t_out - t_in) / 60000.0

        # excursiones durante la vida real de la operacion
        seg_h = H[i:k + 1]
        seg_l = L[i:k + 1]
        if d > 0:
            mfe = (seg_h.max() / p_in - 1) * 1e4
            mae = (seg_l.min() / p_in - 1) * 1e4
        else:
            mfe = (1 - seg_l.min() / p_in) * 1e4
            mae = (1 - seg_h.max() / p_in) * 1e4

        f = dict(dur=dur, real=real, mfe=mfe, mae=mae, dir=d)

        # alternativas de cierre por tiempo fijo
        for a in ALTS:
            kk = int(np.searchsorted(T, t_in + a * 60 * 1000))
            if kk >= len(T):
                f["alt%d" % a] = np.nan
            else:
                f["alt%d" % a] = (O[kk] / p_in - 1) * 1e4 * d
        filas.append(f)

    D = pd.DataFrame(filas)
    print("Operaciones con precio alineado: %d" % len(D))
    print()

    #================================================================
    print("=" * 84)
    print("  1. SU SALIDA REAL frente a cerrar a un tiempo FIJO")
    print("=" * 84)
    real = D["real"].dropna().to_numpy()
    t, p2 = stats.ttest_1samp(real, 0.0)
    print("  %-22s n=%4d  media=%+7.2f bp  t=%+6.2f  acierto=%5.2f%%"
          % ("SALIDA REAL", len(real), real.mean(), t,
             100.0 * (real > 0).mean()))
    print("  " + "-" * 78)
    mejores = []
    for a in ALTS:
        x = D["alt%d" % a].dropna().to_numpy()
        if len(x) < 30:
            continue
        ta, _ = stats.ttest_1samp(x, 0.0)
        mejores.append((a, x.mean(), ta))
        marca = "  <-- mejor fija" if False else ""
        print("  cerrar a %3d min       n=%4d  media=%+7.2f bp  t=%+6.2f  "
              "acierto=%5.2f%%%s"
              % (a, len(x), x.mean(), ta, 100.0 * (x > 0).mean(), marca))

    mej = max(mejores, key=lambda z: z[1])
    print()
    print("  Mejor alternativa fija: %d min con %+.2f bp" % (mej[0], mej[1]))
    print("  Su salida real:                  %+.2f bp" % real.mean())
    print("  Diferencia:                      %+.2f bp  -> %s"
          % (real.mean() - mej[1],
             "su salida GANA a la mejor fija" if real.mean() > mej[1]
             else "su salida PIERDE contra una fija"))

    # test emparejado contra la mejor fija
    sub = D[["real", "alt%d" % mej[0]]].dropna()
    dif = sub["real"].to_numpy() - sub["alt%d" % mej[0]].to_numpy()
    td, pd2 = stats.ttest_1samp(dif, 0.0)
    print("  Test emparejado (real - mejor fija): media=%+.2f bp  t=%+.2f  p=%.4f"
          % (dif.mean(), td, pd2 / 2 if td > 0 else 1 - pd2 / 2))

    #================================================================
    print()
    print("=" * 84)
    print("  2. CAPTURA: cuanto del recorrido favorable se lleva")
    print("=" * 84)
    v = D[(D["mfe"] > 5)].copy()
    v["captura"] = v["real"] / v["mfe"]
    print("  n=%d operaciones con MFE > 5 bp" % len(v))
    print("  MFE medio ............... %+7.2f bp" % v["mfe"].mean())
    print("  MAE medio ............... %+7.2f bp" % v["mae"].mean())
    print("  resultado medio ......... %+7.2f bp" % v["real"].mean())
    print("  captura = real / MFE .... %6.1f%%  (mediana %.1f%%)"
          % (100 * v["captura"].mean(), 100 * v["captura"].median()))
    print("  cierra en maximo (>90%%): %.1f%% de las veces"
          % (100 * (v["captura"] > 0.9).mean()))
    print("  cierra en perdida ....... %.1f%%" % (100 * (v["real"] < 0).mean()))

    #================================================================
    print()
    print("=" * 84)
    print("  3. HAY OBJETIVO FIJO? distribucion del resultado real")
    print("=" * 84)
    print("  banda de resultado        n     %")
    for lo, hi in [(-1e9, -100), (-100, -50), (-50, -20), (-20, 0),
                   (0, 20), (20, 50), (50, 100), (100, 1e9)]:
        n = int(((real >= lo) & (real < hi)).sum())
        print("  %+7.0f a %+7.0f bp   %4d  %5.1f%%  %s"
              % (lo if lo > -1e8 else -999, hi if hi < 1e8 else 999,
                 n, 100.0 * n / len(real), "#" * int(40.0 * n / len(real))))
    print()
    print("  Si hubiera un objetivo duro, habria un pico en una banda "
          "positiva concreta.")
    print("  desviacion tipica del resultado: %.1f bp" % real.std())

    #================================================================
    print()
    print("=" * 84)
    print("  4. DURACION frente a resultado")
    print("=" * 84)
    for lo, hi in [(0, 30), (30, 60), (60, 90), (90, 150), (150, 300),
                   (300, 1e9)]:
        s = D[(D["dur"] >= lo) & (D["dur"] < hi)]
        if len(s) >= 20:
            tt, _ = stats.ttest_1samp(s["real"].to_numpy(), 0.0)
            print("  %4.0f-%4.0f min  n=%4d  media=%+7.2f bp  t=%+5.2f"
                  % (lo, hi, len(s), s["real"].mean(), tt))

    D.to_csv("forense_salidas.csv", index=False)
    print()
    print("Guardado forense_salidas.csv (%d filas)" % len(D))


if __name__ == "__main__":
    main()
