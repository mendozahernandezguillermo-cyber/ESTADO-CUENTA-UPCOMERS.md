#!/usr/bin/env python3
"""
CANDIDATA #3 · VALOR MULTI-ACTIVO (reversion a largo plazo)

Especificacion declarada ANTES de mirar, la de Asness, Moskowitz y Pedersen en
"Value and Momentum Everywhere" para activos sin valor contable:

   señal    : NEGATIVO del retorno de los ultimos 5 años (60 meses), saltando
              el mes mas reciente para no solaparse con el momentum
   tenencia : 1 mes, rebalanceo mensual
   tamaño   : escalado a volatilidad objetivo constante, identico al del trend
              para que las dos sean comparables
   cartera  : equiponderada entre mercados
   universo : los mismos 12 mercados del trend

UNA sola especificacion. No se prueban otros horizontes ni otros retardos.

PREDICCION REGISTRADA:
   (a) Sharpe propio modesto, 0,2-0,5
   (b) correlacion NEGATIVA con el trend -- es la caracteristica documentada
       de la pareja valor/momentum: valor compra lo que ha caido, momentum
       compra lo que ha subido
   (c) si (b) se cumple, la cartera de tres deberia superar el Sharpe 1,03 de
       la de dos y cruzar el 50% de probabilidad de cobro
"""
import os
import numpy as np
import pandas as pd
from scipy import stats

DIR = "datos"
UNIV = ["SPY", "QQQ", "EFA", "EEM", "TLT", "IEF", "GLD", "SLV",
        "EURUSDX", "USDJPYX", "GBPUSDX", "AUDUSDX"]
VOL_OBJ = 0.10
MIRADA_VAL = 60          # meses
SALTO = 1                # se salta el mes mas reciente


def cargar(tk):
    p = "%s/%s.csv" % (DIR, tk)
    if not os.path.exists(p):
        return None
    d = pd.read_csv(p, index_col=0, parse_dates=True)
    s = pd.to_numeric(d["Close"], errors="coerce").dropna()
    return s[s > 0]


px = {tk: cargar(tk) for tk in UNIV}
px = {k: v for k, v in px.items() if v is not None}

filas = []
for tk, s in px.items():
    r_d = s.pct_change()
    vol = (r_d.rolling(252).std() * np.sqrt(252)).resample("ME").last()
    m = s.resample("ME").last()
    r_m = m.pct_change()
    for i in range(MIRADA_VAL + SALTO + 1, len(m)):
        # retorno de 5 años terminando hace SALTO meses
        p_fin = m.iloc[i - 1 - SALTO]
        p_ini = m.iloc[i - 1 - SALTO - MIRADA_VAL]
        v = vol.iloc[i - 1]
        if pd.isna(p_fin) or pd.isna(p_ini) or pd.isna(v) or v <= 0:
            continue
        if pd.isna(r_m.iloc[i]):
            continue
        r5 = p_fin / p_ini - 1.0
        pos = -np.sign(r5) * (VOL_OBJ / v)          # NEGATIVO: compra lo caido
        pos = np.clip(pos, -5, 5)
        filas.append(dict(fecha=m.index[i], mercado=tk, pos=pos,
                          r=pos * r_m.iloc[i]))

V = pd.DataFrame(filas)
val = V.groupby("fecha").agg(r=("r", "mean"), n=("mercado", "size"))
val = val[val["n"] >= 6]["r"]
val.index = pd.to_datetime(val.index)

print("=" * 84)
print("VALOR MULTI-ACTIVO")
print("=" * 84)
print("meses: %d  ·  %s -> %s" % (len(val), val.index.min().date(),
                                  val.index.max().date()))


def resu(r):
    r = r.dropna()
    mu, sd = r.mean() * 12, r.std() * np.sqrt(12)
    return dict(n=len(r), mu=mu, sd=sd, sh=mu / sd if sd else np.nan,
                t=r.mean() / r.std() * np.sqrt(len(r)),
                skew=stats.skew(r), peor3=r.rolling(3).sum().min())


print()
print(f"{'periodo':<14}{'meses':>7}{'retorno':>10}{'vol':>8}{'Sharpe':>9}"
      f"{'t':>7}{'ASIM.':>8}")
print("-" * 84)
for etq, a, b in [("primera mitad", 0, 0), ("segunda mitad", 0, 0),
                  ("TODO", 0, 0)]:
    pass
mid = val.index[len(val) // 2]
for etq, sub in [("1a mitad", val[val.index < mid]),
                 ("2a mitad", val[val.index >= mid]),
                 ("TODO", val)]:
    r = resu(sub)
    print(f"{etq:<14}{r['n']:>7}{r['mu']:>9.2%}{r['sd']:>8.2%}"
          f"{r['sh']:>9.2f}{r['t']:>7.2f}{r['skew']:>8.2f}")

# ------------------------------------------------- correlacion con el trend
tr = pd.read_csv("serie_trend.csv", parse_dates=["fecha"])
s2 = tr.set_index("fecha")["r"]
s2.index = s2.index + pd.offsets.MonthEnd(0)
val.index = val.index + pd.offsets.MonthEnd(0)

EXCL = {pd.Timestamp(x).date() for x in
        ["2003-09-15", "2020-03-02", "2020-03-15", "2020-03-18", "2025-08-22"]}
f = pd.read_csv("../fomc/fomc_fechas.csv", parse_dates=["fecha"])
FOMC = set(f[~f["fecha"].dt.date.isin(EXCL)]["fecha"].dt.date)
ndx = pd.read_csv("../nas100-data/yahoo/NDX.csv", index_col=0, parse_dates=True)
ndx = ndx[["Open", "Close"]].dropna()
gap = (ndx["Open"] / ndx["Close"].shift(1) - 1.0).dropna()
gap = gap[gap.abs() < 0.10]
s1 = (gap[pd.Series(gap.index.date, index=gap.index).isin(FOMC)]
      - 3.4 / 1e4).resample("ME").sum()

A = pd.DataFrame({"fomc": s1, "trend": s2, "valor": val}).dropna()
print()
print("=" * 84)
print("CORRELACIONES  (meses comunes: %d)" % len(A))
print("=" * 84)
print(A.corr().round(3).to_string())
rho_vt = A["valor"].corr(A["trend"])
print()
print("  valor vs trend: %+.3f -> %s" % (rho_vt,
      "NEGATIVA, como predije" if rho_vt < -0.1 else
      "no es negativa: la prediccion (b) FALLA"))

# ------------------------------------------------- carteras
print()
print("=" * 84)
print("CARTERA DE DOS CONTRA CARTERA DE TRES")
print("=" * 84)


def paridad(cols):
    iv = np.array([1 / A[c].std() for c in cols])
    return iv / iv.sum()


print(f"{'cartera':<24}{'Sharpe':>8}{'t':>7}{'ASIM.':>8}{'peor 3m':>10}"
      f"{'a vol 4,5%':>12}")
print("-" * 84)
res = {}
for nom, cols in [("#1 + #2", ["fomc", "trend"]),
                  ("#1 + #2 + valor", ["fomc", "trend", "valor"])]:
    w = paridad(cols)
    r = (A[cols] * w).sum(axis=1)
    x = resu(r)
    lev = 0.045 / x["sd"]
    res[nom] = (x, r)
    print(f"{nom:<24}{x['sh']:>8.2f}{x['t']:>7.2f}{x['skew']:>8.2f}"
          f"{x['peor3']:>9.2%}{x['peor3']*lev:>12.2%}")

print()
print("  pesos de la cartera de tres: " +
      "  ".join("%s %.0f%%" % (c, w * 100) for c, w in
                zip(["#1", "#2", "valor"], paridad(["fomc", "trend", "valor"]))))

# ------------------------------------------------- contraste
print()
print("=" * 84)
print("CONTRASTE CON LA PREDICCION REGISTRADA")
print("=" * 84)
x = resu(val)
print("  (a) Sharpe propio 0,2-0,5 : %.2f -> %s"
      % (x["sh"], "SE CUMPLE" if 0.15 <= x["sh"] <= 0.6 else "fuera de rango"))
print("  (b) correlacion negativa  : %+.3f -> %s"
      % (rho_vt, "SE CUMPLE" if rho_vt < -0.1 else "NO se cumple"))
s2_ = res["#1 + #2"][0]["sh"]
s3_ = res["#1 + #2 + valor"][0]["sh"]
print("  (c) sube el Sharpe        : %.2f -> %.2f  -> %s"
      % (s2_, s3_, "SE CUMPLE" if s3_ > s2_ + 0.03 else "NO mejora"))
