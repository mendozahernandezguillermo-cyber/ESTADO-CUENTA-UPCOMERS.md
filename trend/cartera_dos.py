#!/usr/bin/env python3
"""
¿SIRVE EL TREND COMO ESTRATEGIA #2?

La razon de buscarlo era la DESCORRELACION con la prima pre-FOMC. Pero
post-2010 el trend sobrevive sobre todo en ACCIONES, que es la misma clase de
activo donde vive la #1. Asi que hay que medir la correlacion, no suponerla.

Y lo que de verdad decide si vale la pena no es el Sharpe combinado: es si
SUAVIZA la trayectoria. La #1 tiene 8 eventos al año, muy irregulares, y el
problema que la hacia no desplegable era que la desviacion de un solo evento
apalancado quedaba a 3,3 sigmas del limite de drawdown. Una estrategia continua
arregla eso aunque su Sharpe sea modesto.

Se alinean las dos en frecuencia MENSUAL:
   #1 : suma de los retornos de los eventos FOMC que caen en ese mes (0, 1 o 2)
   #2 : retorno de la cartera de trend en ese mes
"""
import os
import glob
import numpy as np
import pandas as pd
from scipy import stats

# ------------------------------------------------- #1: prima pre-FOMC
EXCLUIR = {pd.Timestamp(x).date() for x in
           ["2003-09-15", "2020-03-02", "2020-03-15", "2020-03-18",
            "2025-08-22"]}
f = pd.read_csv("../fomc/fomc_fechas.csv", parse_dates=["fecha"])
FOMC = set(f[~f["fecha"].dt.date.isin(EXCLUIR)]["fecha"].dt.date)

ndx = pd.read_csv("../nas100-data/yahoo/NDX.csv", index_col=0,
                  parse_dates=True)
ndx = ndx[["Open", "Close"]].dropna()
ndx = ndx[(ndx > 0).all(axis=1)]
gap = (ndx["Open"] / ndx["Close"].shift(1) - 1.0).dropna()
gap = gap[gap.abs() < 0.10]
es_f = pd.Series(gap.index.date, index=gap.index).isin(FOMC)
COSTE = 3.4 / 1e4                       # swap de una noche + spread
ev = (gap[es_f] - COSTE)
s1 = ev.resample("ME").sum()            # 0, 1 o 2 eventos por mes
s1 = s1.reindex(pd.date_range(s1.index.min(), s1.index.max(), freq="ME"),
                fill_value=0.0)

# ------------------------------------------------- #2: trend
import subprocess
if not os.path.exists("serie_trend.csv"):
    print("[recalculando la serie de trend ...]")
    exec(open("trend.py").read().split("# ------------------------------------------------- costes")[0]
         .replace('print("=" * 84)', 'pass  #'))
    cart[["fecha", "r"]].to_csv("serie_trend.csv", index=False)
tr = pd.read_csv("serie_trend.csv", parse_dates=["fecha"])
s2 = tr.set_index("fecha")["r"]
s2.index = s2.index + pd.offsets.MonthEnd(0)

A = pd.DataFrame({"fomc": s1, "trend": s2}).dropna()
print("=" * 80)
print("MESES COMUNES: %d  ·  %s -> %s"
      % (len(A), A.index.min().date(), A.index.max().date()))
print("=" * 80)


def resu(r, etq):
    mu, sd = r.mean() * 12, r.std() * np.sqrt(12)
    sh = mu / sd if sd else np.nan
    t = r.mean() / r.std() * np.sqrt(len(r))
    return dict(etq=etq, mu=mu, sd=sd, sh=sh, t=t)


print()
print("1. LAS DOS POR SEPARADO Y SU CORRELACION")
print("-" * 80)
print(f"{'estrategia':<20}{'retorno':>10}{'vol':>9}{'Sharpe':>9}{'t':>7}")
for c, nom in (("fomc", "#1 prima pre-FOMC"), ("trend", "#2 trend")):
    r = resu(A[c], nom)
    print(f"{nom:<20}{r['mu']:>9.2%}{r['sd']:>9.2%}{r['sh']:>9.2f}{r['t']:>7.2f}")
rho = A["fomc"].corr(A["trend"])
n = len(A)
t_rho = rho * np.sqrt((n - 2) / max(1e-9, 1 - rho ** 2))
print()
print("  correlacion mensual: %+.3f   (t=%.2f, n=%d)" % (rho, t_rho, n))
print("  -> %s" % ("descorrelacionadas" if abs(rho) < 0.2
                   else "OJO: correlacion no despreciable"))

# ------------------------------------------------- combinacion
print()
print("2. CARTERA COMBINADA  ·  reparto por riesgo (paridad de volatilidad)")
print("-" * 80)
w1 = (1 / A["fomc"].std()) / ((1 / A["fomc"].std()) + (1 / A["trend"].std()))
w2 = 1 - w1
A["mix"] = w1 * A["fomc"] + w2 * A["trend"]
print("  pesos: #1 %.0f%% del riesgo, #2 %.0f%%" % (w1 * 100, w2 * 100))
print()
print(f"{'':<20}{'Sharpe':>9}{'t':>7}{'peor mes':>11}{'peor 3 meses':>14}")
for c, nom in (("fomc", "#1 sola"), ("trend", "#2 sola"), ("mix", "cartera")):
    r = resu(A[c], nom)
    p3 = A[c].rolling(3).sum().min()
    print(f"{nom:<20}{r['sh']:>9.2f}{r['t']:>7.2f}{A[c].min():>10.2%}"
          f"{p3:>13.2%}")
print()
print("  Sharpe teorico si rho=0: raiz(s1^2+s2^2) = %.2f"
      % np.sqrt(resu(A['fomc'],'')['sh']**2 + resu(A['trend'],'')['sh']**2))

# ------------------------------------------------- lo que de verdad importa
print()
print("3. LO QUE DECIDE SI VALE LA PENA: ¿SUAVIZA LA TRAYECTORIA?")
print("-" * 80)
print("  El problema de la #1 no era su Sharpe, era la irregularidad: 8 eventos")
print("  al año y, apalancada al optimo, un evento a 3,3 sigmas del limite.")
print()
print(f"{'':<20}{'meses sin operar':>18}{'% meses en cero':>17}")
for c, nom in (("fomc", "#1 sola"), ("mix", "cartera")):
    cero = (A[c].abs() < 1e-9).sum()
    print(f"{nom:<20}{cero:>18}{100.0*cero/len(A):>16.0f}%")
print()
# apalancamiento necesario y distancia al limite del 7%
for c, nom in (("fomc", "#1 sola"), ("mix", "cartera")):
    sd_m = A[c].std()
    lev = 0.06 / (sd_m * np.sqrt(12))       # llevar a 6% de vol anual
    sd_ev = sd_m * lev
    print("  %-12s apalancamiento x%.1f -> sd mensual %.2f%% -> "
          "limite del 7%% a %.1f sigmas" % (nom, lev, sd_ev * 100,
                                            0.07 / sd_ev))
