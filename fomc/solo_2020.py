#!/usr/bin/env python3
"""
¿QUE PASA SI SOLO MIRAMOS DE 2020 EN ADELANTE?

Hay un argumento legitimo para acortar la muestra: el mercado cambio en 2020
(tipos a cero y luego subidas rapidas, flujo minorista, opciones de vencimiento
diario, dominio algoritmico). Los datos de 2000-2019 podrian no describir el
mercado que vas a operar.

Y hay un coste: con menos datos, mas cosas parecen significativas sin serlo.

Este script mide las dos cosas a la vez:

  1. TODAS las hipotesis que hemos probado, restringidas a 2020-2026.
  2. La REFERENCIA DE RUIDO en esa misma ventana: se prueban 30 celdas de
     calendario arbitrarias (dia de la semana x semana del mes) que no
     responden a ninguna teoria. El maximo |t| de esas 30 celdas es lo que
     produce el azar con esta cantidad de datos.

Sin el punto 2, el punto 1 no se puede interpretar. Cualquier hipotesis con
|t| por debajo de ese maximo es indistinguible de una celda arbitraria.
"""
import numpy as np
import pandas as pd
from scipy import stats

DIRY = "../nas100-data/yahoo"
DESDE = 2020

EXCLUIR = {pd.Timestamp(x).date() for x in
           ["2003-09-15", "2020-03-02", "2020-03-15", "2020-03-18",
            "2025-08-22"]}
f = pd.read_csv("fomc_fechas.csv", parse_dates=["fecha"])
FOMC = set(f[~f["fecha"].dt.date.isin(EXCLUIR)]["fecha"].dt.date)


def cargar(tk, desde):
    d = pd.read_csv("%s/%s.csv" % (DIRY, tk), index_col=0, parse_dates=True)
    d = d[["Open", "Close"]].dropna()
    d = d[(d > 0).all(axis=1)]
    d = d[d.index.year >= desde]
    prev = d["Close"].shift(1)
    d["gap"] = (d["Open"] / prev - 1.0) * 1e4
    d["cc"] = (d["Close"] / prev - 1.0) * 1e4
    d["oc"] = (d["Close"] / d["Open"] - 1.0) * 1e4
    d = d.dropna()
    d = d[d["cc"].abs() < 1500]

    idx = d.index
    d["fomc"] = pd.Series(idx.date, index=idx).isin(FOMC)
    g = d.groupby([idx.year, idx.month])
    d["pos_ini"] = g.cumcount() + 1
    d["pos_fin"] = g.cumcount(ascending=False) + 1
    d["dia1"] = d["pos_ini"] == 1
    d["tom"] = (d["pos_fin"] == 1) | (d["pos_ini"] <= 3)
    d["dow"] = idx.dayofweek
    d["lunes_noche"] = d["dow"] == 1          # hueco que se abre el lunes
    # tercer viernes
    vie = idx[idx.dayofweek == 4]
    ter = set()
    for _, gg in pd.Series(vie).groupby([vie.year, vie.month]):
        s = sorted(gg)
        if len(s) >= 3:
            ter.add(s[2])
    d["venc"] = idx.isin(ter)
    sem = np.zeros(len(d), dtype=bool)
    for p in np.where(d["venc"].values)[0]:
        sem[max(0, p - 4):p + 1] = True
    d["sem_venc"] = sem
    prim = set()
    for _, gg in pd.Series(vie).groupby([vie.year, vie.month]):
        prim.add(min(gg))
    d["empleo"] = idx.isin(prim)
    d["ipc"] = (idx.day >= 9) & (idx.day <= 16)
    d["semana_mes"] = np.minimum((d["pos_ini"] - 1) // 5, 3)
    return d


def t_de(d, mask, col):
    x, y = d[col][mask], d[col][~mask]
    if len(x) < 8 or x.std() == 0:
        return None
    t, p = stats.ttest_ind(x, y, equal_var=False)
    return len(x), x.mean() - y.mean(), t, p


d = cargar("NDX", DESDE)
dl = cargar("NDX", 2000)
print("=" * 88)
print("MUESTRA 2020-2026: %d sesiones  ·  muestra larga 2000-2026: %d sesiones"
      % (len(d), len(dl)))
print("=" * 88)

HIP = [
    ("hueco pre-FOMC",          "fomc",        "gap"),
    ("primer dia del mes",      "dia1",        "gap"),
    ("ventana cierre de mes",   "tom",         "cc"),
    ("hueco del lunes",         "lunes_noche", "gap"),
    ("dia de vencimiento",      "venc",        "cc"),
    ("semana de vencimiento",   "sem_venc",    "cc"),
    ("hueco pre-empleo",        "empleo",      "gap"),
    ("hueco pre-IPC",           "ipc",         "gap"),
]

print()
print("1. LAS HIPOTESIS YA PROBADAS, EN LAS DOS VENTANAS")
print("-" * 88)
print(f"{'hipotesis':<24}{'2000-2026':>24}{'2020-2026':>24}")
print(f"{'':<24}{'n':>6}{'dif':>9}{'t':>9}{'n':>6}{'dif':>9}{'t':>9}")
print("-" * 88)
for nom, campo, col in HIP:
    rl = t_de(dl, dl[campo], col)
    rc = t_de(d, d[campo], col)
    if not rl or not rc:
        continue
    print(f"{nom:<24}{rl[0]:>6}{rl[1]:>9.1f}{rl[2]:>9.2f}"
          f"{rc[0]:>6}{rc[1]:>9.1f}{rc[2]:>9.2f}")

# ---------------------------------------------- referencia de ruido
print()
print("2. REFERENCIA DE RUIDO: 30 celdas de calendario ARBITRARIAS")
print("   (dia de la semana x semana del mes; ninguna responde a teoria)")
print("-" * 88)
res = {"2000-2026": [], "2020-2026": []}
for etq, df in [("2000-2026", dl), ("2020-2026", d)]:
    for dw in range(5):
        for sm in range(4):
            for col in ("gap", "cc"):
                m = (df["dow"] == dw) & (df["semana_mes"] == sm)
                r = t_de(df, m, col)
                if r and r[0] >= 15:
                    res[etq].append((abs(r[2]), dw, sm, col, r[0], r[1]))
for etq in res:
    L = sorted(res[etq], reverse=True)
    print("\n  %s  ·  %d celdas evaluadas" % (etq, len(L)))
    print("     max |t| = %.2f   ·  2o = %.2f  ·  3o = %.2f"
          % (L[0][0], L[1][0], L[2][0]))
    print("     celdas con |t| > 2,0: %d  (%.0f%%)"
          % (sum(1 for x in L if x[0] > 2), 100.0 * sum(1 for x in L if x[0] > 2) / len(L)))
    DOW = ["lun", "mar", "mie", "jue", "vie"]
    for a in L[:3]:
        print("       %s / semana %d / %s : dif %+.1f bp, |t|=%.2f (n=%d)"
              % (DOW[a[1]], a[2] + 1, a[3], a[5], a[0], a[4]))

# ---------------------------------------------- lectura
techo_l = sorted(res["2000-2026"], reverse=True)[0][0]
techo_c = sorted(res["2020-2026"], reverse=True)[0][0]
print()
print("=" * 88)
print("3. LECTURA")
print("=" * 88)
print("  Techo del ruido (max |t| de una celda arbitraria):")
print("     2000-2026 : %.2f" % techo_l)
print("     2020-2026 : %.2f" % techo_c)
print()
print("  Cualquier hipotesis por debajo de ese techo es indistinguible de una")
print("  celda de calendario elegida al azar.")
print()
print(f"  {'hipotesis':<24}{'t en 2020-2026':>16}{'¿supera el techo?':>20}")
print("  " + "-" * 62)
for nom, campo, col in HIP:
    rc = t_de(d, d[campo], col)
    if not rc:
        continue
    print(f"  {nom:<24}{rc[2]:>16.2f}{('SI' if abs(rc[2]) > techo_c else 'no'):>20}")
