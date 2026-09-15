#!/usr/bin/env python3
"""
QUE DISTINGUE LAS OPORTUNIDADES QUE joxemi TOMA DE LAS QUE DESCARTA

Estado del problema:
  - su condicion de entrada esta identificada (posicion extrema del rango
    del dia, t = 34.7 / -37.0) pero replicada da ~0 bp
  - sus entradas reales dan +3.37 bp con t = 2.98
  - sus salidas no tienen habilidad (pierden contra cerrar a 4 h fijas)
  => el edge esta en QUE SUBCONJUNTO elige

Metodo:
  1. generar TODAS las velas M5 que cumplen la condicion (candidatas)
  2. etiquetar cada candidata: TOMADA si coincide (+-5 min y misma
     direccion) con una de sus 935 entradas reales; DESCARTADA si no
  3. comparar retorno futuro y rasgos entre los dos grupos

PRUEBA PRINCIPAL: el retorno futuro de las TOMADAS frente a las
DESCARTADAS. Si no hay diferencia, su seleccion no aporta nada y el
+3.37 bp de sus operaciones reales viene de otra parte.

Aviso sobre la n: las candidatas de velas M5 consecutivas estan muy
correlacionadas, asi que la n efectiva es menor que la nominal y las t
salen infladas. Se comenta al final.
"""
import glob
import json
import os
import numpy as np
import pandas as pd
from scipy import stats

RAW = "/projects/sandbox/nas100-data/raw"
BANDA_L, BANDA_C = 0.80, 0.20
SUELO = 0.60
MIN_MIN_DIA = 60
TOL_MS = 5 * 60 * 1000


def cargar():
    files = sorted(glob.glob(os.path.join(RAW, "*.csv")))
    partes = [pd.read_csv(f, usecols=["timestamp", "open", "high",
                                      "low", "close"]) for f in files]
    df = pd.concat(partes, ignore_index=True)
    df = df.drop_duplicates("timestamp").sort_values("timestamp")
    ny = pd.to_datetime(df["timestamp"], unit="ms", utc=True) \
           .dt.tz_convert("America/New_York")
    df = df.assign(fecha=ny.dt.date, tod=ny.dt.hour * 60 + ny.dt.minute,
                   dow=ny.dt.dayofweek)
    return df[df["dow"] < 5].reset_index(drop=True)


def entradas_reales():
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
    idx = np.where((J["nas"].notna() & prev.isna()).to_numpy())[0]
    return [(int(J["ms"].iloc[i]), int(J["nas"].iloc[i])) for i in idx
            if J["nas"].iloc[i] != 0]


def main():
    df = cargar()
    reales = entradas_reales()
    print("Entradas reales de NASDAQ: %d" % len(reales))
    ms_real = np.array([r[0] for r in reales])
    dir_real = np.array([r[1] for r in reales])
    orden = np.argsort(ms_real)
    ms_real, dir_real = ms_real[orden], dir_real[orden]
    ini, fin = ms_real.min(), ms_real.max()

    #--- generar candidatas -----------------------------------------
    cand = []
    hist = []
    for fecha, g in df.groupby("fecha", sort=True):
        T = g["tod"].to_numpy()
        MS = g["timestamp"].to_numpy(np.int64)
        O = g["open"].to_numpy(float)
        H = g["high"].to_numpy(float)
        L = g["low"].to_numpy(float)
        if len(T) < 400:
            continue
        rd = 1e4 * (H.max() - L.min()) / O[0]
        med = float(np.median(hist[-20:])) if len(hist) >= 20 else None
        hist.append(rd)
        if med is None or MS[-1] < ini - 86400000 or MS[0] > fin + 86400000:
            continue

        n = len(T)
        for j in range(n):
            if T[j] - T[0] < MIN_MIN_DIA or T[j] % 5 != 0:
                continue
            hi = H[:j].max() if j > 0 else H[0]
            lo = L[:j].min() if j > 0 else L[0]
            px = O[j]
            if px > hi:
                hi = px
            if px < lo:
                lo = px
            rng = hi - lo
            if rng <= 0:
                continue
            rbp = 1e4 * rng / px
            if rbp < SUELO * med:
                continue
            pos = (px - lo) / rng
            d = 1 if pos >= BANDA_L else (-1 if pos <= BANDA_C else 0)
            if d == 0:
                continue

            def ret(mins):
                k = int(np.searchsorted(MS, MS[j] + mins * 60000))
                if k >= len(MS):
                    k = len(MS) - 1
                return (O[k] / px - 1) * 1e4 * d if k > j else np.nan

            def prev_ret(mins):
                k = j - mins
                return (px / O[k] - 1) * 1e4 if k >= 0 and O[k] > 0 else np.nan

            vol30 = (float(np.std(np.diff(np.log(O[max(0, j - 30):j + 1]))) * 1e4)
                     if j >= 31 else np.nan)

            cand.append(dict(ms=int(MS[j]), dir=d, tod=int(T[j]),
                             transc=int(T[j] - T[0]), pos=pos, rbp=rbp,
                             rbp_rel=rbp / med, vol30=vol30,
                             dow=int(g["dow"].iloc[0]),
                             r15=prev_ret(15), r30=prev_ret(30),
                             r60=prev_ret(60), r120=prev_ret(120),
                             fwd75=ret(75), fwd240=ret(240)))

    C = pd.DataFrame(cand)
    print("Candidatas generadas: %d  (%s a %s)"
          % (len(C), pd.to_datetime(C.ms.min(), unit="ms"),
             pd.to_datetime(C.ms.max(), unit="ms")))

    #--- etiquetar --------------------------------------------------
    tomada = np.zeros(len(C), dtype=bool)
    cms = C["ms"].to_numpy()
    cdir = C["dir"].to_numpy()
    emparejadas = 0
    for m, d in zip(ms_real, dir_real):
        sel = np.where((np.abs(cms - m) <= TOL_MS) & (cdir == d))[0]
        if len(sel):
            tomada[sel[np.argmin(np.abs(cms[sel] - m))]] = True
            emparejadas += 1
    C["tomada"] = tomada
    print("Sus entradas emparejadas con una candidata: %d de %d (%.1f%%)"
          % (emparejadas, len(ms_real), 100.0 * emparejadas / len(ms_real)))
    print("Candidatas TOMADAS: %d   DESCARTADAS: %d"
          % (int(tomada.sum()), int((~tomada).sum())))
    print()

    A = C[C["tomada"]]
    B = C[~C["tomada"]]

    #================================================================
    print("=" * 86)
    print("  PRUEBA PRINCIPAL: retorno futuro de TOMADAS vs DESCARTADAS")
    print("=" * 86)
    for col, nom in [("fwd75", "cerrando a 75 min"),
                     ("fwd240", "cerrando a 240 min")]:
        a = A[col].dropna().to_numpy()
        b = B[col].dropna().to_numpy()
        t, p = stats.ttest_ind(a, b, equal_var=False)
        print("  %-20s TOMADAS %+7.2f bp (n=%4d)   "
              "DESCARTADAS %+7.2f bp (n=%5d)   dif=%+6.2f  t=%+5.2f  p=%.4f"
              % (nom, a.mean(), len(a), b.mean(), len(b),
                 a.mean() - b.mean(), t, p))
    print()

    #================================================================
    print("=" * 86)
    print("  QUE RASGOS LAS DISTINGUEN")
    print("=" * 86)
    print("  %-10s %11s %12s %11s %8s %9s"
          % ("rasgo", "tomadas", "descartadas", "diferencia", "t", "p"))
    print("  " + "-" * 80)
    for c in ["pos", "rbp", "rbp_rel", "vol30", "tod", "transc",
              "r15", "r30", "r60", "r120"]:
        a = A[c].dropna().to_numpy()
        b = B[c].dropna().to_numpy()
        if len(a) < 30 or len(b) < 30:
            continue
        t, p = stats.ttest_ind(a, b, equal_var=False)
        flag = "  ***" if p < 0.001 else ("  **" if p < 0.01 else
                                         ("  *" if p < 0.05 else ""))
        print("  %-10s %+11.3f %+12.3f %+11.3f %8.2f %9.5f%s"
              % (c, a.mean(), b.mean(), a.mean() - b.mean(), t, p, flag))

    print()
    print("=" * 86)
    print("  REPARTO POR DIRECCION Y DIA")
    print("=" * 86)
    print("  direccion:  tomadas %.1f%% largas   descartadas %.1f%% largas"
          % (100 * (A["dir"] == 1).mean(), 100 * (B["dir"] == 1).mean()))
    print("  dia semana: tomadas %s" % dict(A["dow"].value_counts().sort_index()))
    print("              descart %s" % dict(B["dow"].value_counts().sort_index()))

    C.to_csv("seleccion_candidatas.csv", index=False)
    print()
    print("AVISO: velas M5 consecutivas en banda estan muy correlacionadas,")
    print("asi que la n efectiva es menor que la nominal y las t van infladas.")
    print("Guardado seleccion_candidatas.csv (%d filas)" % len(C))


if __name__ == "__main__":
    main()
