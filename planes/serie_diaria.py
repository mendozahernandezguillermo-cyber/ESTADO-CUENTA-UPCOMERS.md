#!/usr/bin/env python3
"""
Construye la serie DIARIA de la cartera (#1 pre-FOMC + #2 trend).

Por que diaria y no mensual: las reglas de la cuenta prop actuan dia a dia
-- limite diario, trailing sobre equity -- asi que simular con retornos
mensuales oculta justo el riesgo que importa.

  #1 : retorno del hueco nocturno los dias de FOMC, cero el resto de dias.
  #2 : posicion del mes (señal de 12 meses, escalada a vol) multiplicada por
       el retorno DIARIO de cada mercado, agregada equiponderadamente.
"""
import os
import glob
import numpy as np
import pandas as pd

DIRY = "../nas100-data/yahoo"
DIRT = "../trend/datos"
os.makedirs("salida", exist_ok=True)

# ----------------------------------------------------------- #1 pre-FOMC
EXCL = {pd.Timestamp(x).date() for x in
        ["2003-09-15", "2020-03-02", "2020-03-15", "2020-03-18", "2025-08-22"]}
f = pd.read_csv("../fomc/fomc_fechas.csv", parse_dates=["fecha"])
FOMC = set(f[~f["fecha"].dt.date.isin(EXCL)]["fecha"].dt.date)

ndx = pd.read_csv("%s/NDX.csv" % DIRY, index_col=0, parse_dates=True)
ndx = ndx[["Open", "Close"]].dropna()
ndx = ndx[(ndx > 0).all(axis=1)]
gap = (ndx["Open"] / ndx["Close"].shift(1) - 1.0).dropna()
gap = gap[gap.abs() < 0.10]
COSTE = 3.4 / 1e4
esf = pd.Series(gap.index.date, index=gap.index).isin(FOMC)
s1 = pd.Series(0.0, index=gap.index)
s1[esf] = gap[esf] - COSTE

# ----------------------------------------------------------- #2 trend
UNIV = ["SPY", "QQQ", "EFA", "EEM", "TLT", "IEF", "GLD", "SLV",
        "EURUSDX", "USDJPYX", "GBPUSDX", "AUDUSDX"]
VOL_OBJ, MIRADA = 0.10, 12
px = {}
for tk in UNIV:
    p = "%s/%s.csv" % (DIRT, tk)
    if not os.path.exists(p):
        continue
    d = pd.read_csv(p, index_col=0, parse_dates=True)
    s = pd.to_numeric(d["Close"], errors="coerce").dropna()
    px[tk] = s[s > 0]

contrib = {}
for tk, s in px.items():
    r_d = s.pct_change()
    vol = r_d.rolling(252).std() * np.sqrt(252)
    m = s.resample("ME").last()
    pos_m = {}
    for i in range(MIRADA + 1, len(m)):
        pas = m.iloc[i - 1] / m.iloc[i - 1 - MIRADA] - 1.0
        v = vol.resample("ME").last().iloc[i - 1]
        if pd.isna(pas) or pd.isna(v) or v <= 0:
            continue
        pos_m[m.index[i]] = np.clip(np.sign(pas) * (VOL_OBJ / v), -5, 5)
    if not pos_m:
        continue
    ps = pd.Series(pos_m)
    # la posicion del mes se aplica a todos los dias de ese mes
    pos_d = ps.reindex(r_d.index, method="bfill")
    pos_d = pos_d.where(pos_d.index <= ps.index.max())
    contrib[tk] = (pos_d * r_d).dropna()

TR = pd.DataFrame(contrib)
n_disp = TR.notna().sum(axis=1)
s2 = TR.mean(axis=1)[n_disp >= 6]

# ----------------------------------------------------------- cartera
A = pd.DataFrame({"s1": s1, "s2": s2}).dropna()
iv1, iv2 = 1 / A["s1"].std(), 1 / A["s2"].std()
w1, w2 = iv1 / (iv1 + iv2), iv2 / (iv1 + iv2)
A["cartera"] = w1 * A["s1"] + w2 * A["s2"]
A.to_csv("salida/cartera_diaria.csv")

print("=" * 80)
print("SERIE DIARIA DE LA CARTERA")
print("=" * 80)
print("dias: %d  ·  %s -> %s" % (len(A), A.index.min().date(),
                                 A.index.max().date()))
print("pesos por paridad de riesgo: #1 %.0f%%  #2 %.0f%%" % (w1 * 100, w2 * 100))
print()
print(f"{'':<12}{'ret.anual':>11}{'vol.anual':>11}{'Sharpe':>9}"
      f"{'peor dia':>10}{'peor 21d':>10}{'peor 63d':>10}")
print("-" * 80)
for c, nom in (("s1", "#1 FOMC"), ("s2", "#2 trend"), ("cartera", "CARTERA")):
    r = A[c]
    mu, sd = r.mean() * 252, r.std() * np.sqrt(252)
    print(f"{nom:<12}{mu:>10.2%}{sd:>11.2%}{mu/sd:>9.2f}{r.min():>10.2%}"
          f"{r.rolling(21).sum().min():>10.2%}"
          f"{r.rolling(63).sum().min():>10.2%}")
print()
print("correlacion diaria #1 vs #2: %+.3f" % A["s1"].corr(A["s2"]))
print("guardado salida/cartera_diaria.csv")
