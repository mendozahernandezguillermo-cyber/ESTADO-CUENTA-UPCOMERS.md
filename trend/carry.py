#!/usr/bin/env python3
"""
OPCION B · CARRY  ·  version 2

La v1 fallo: DBV (el indice G10 de carry) esta DESLISTADO, y FRED no es
alcanzable desde este entorno (HTTP 000), asi que no tengo tipos cortos
internacionales para construir el carry de divisas de forma exacta.

SIMPLIFICACION DECLARADA Y SU JUSTIFICACION:
   Para DIVISAS uso AUD/JPY al contado, que es el carry trade canonico (la
   divisa de mayor tipo del G10 contra la de menor durante casi toda la
   muestra). Omito el diferencial de tipos, asi que el RETORNO y el Sharpe
   quedan SUBESTIMADOS. Pero la pregunta que decide esto es el PERFIL DE COLA,
   y el diferencial de tipos aporta deriva positiva suave sin aportar riesgo de
   cola: toda la asimetria y todos los desplomes del carry estan en el contado.
   Asi que asimetria, peor mes y correlacion en crisis se miden bien.

   Para BONOS: pendiente de la curva (10 años menos 3 meses) como señal para
   tomar duracion via TLT financiado con SHY. Term premium clasico, exacto.

PREDICCION REGISTRADA ANTES DE MIRAR:
   (b) asimetria negativa fuerte
   (c) las perdidas concentradas en aversion al riesgo
   (d) la correlacion con acciones SE DISPARA en esos episodios
"""
import os
import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

DIR = "datos"


def bajar(tk, desde="1995-01-01"):
    p = os.path.join(DIR, tk.replace("=", "").replace("^", "") + ".csv")
    if not os.path.exists(p):
        d = yf.download(tk, start=desde, progress=False, auto_adjust=True)
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)
        if d is None or len(d) == 0:
            return None
        d.to_csv(p)
    d = pd.read_csv(p, index_col=0, parse_dates=True)
    s = pd.to_numeric(d["Close"], errors="coerce").dropna()
    return s[s > 0] if len(s) else None


aud = bajar("AUDUSD=X")
jpy = bajar("USDJPY=X")
tlt, shy, spy = bajar("TLT"), bajar("SHY"), bajar("SPY")
tnx, irx = bajar("^TNX"), bajar("^IRX")

# AUD/JPY = AUDUSD * USDJPY
audjpy = (aud * jpy.reindex(aud.index, method="ffill")).dropna()
print("AUD/JPY construido: %d sesiones  %s -> %s"
      % (len(audjpy), audjpy.index.min().date(), audjpy.index.max().date()))

r_fx = audjpy.resample("ME").last().pct_change().dropna()

pend_m = (tnx - irx).dropna().resample("ME").last()
r_tlt = tlt.resample("ME").last().pct_change()
r_shy = shy.resample("ME").last().pct_change()
r_bd = (np.sign(pend_m.shift(1)) * (r_tlt - r_shy)).dropna()


def escalar(r, objetivo=0.10):
    v = r.rolling(24).std() * np.sqrt(12)
    return (r * (objetivo / v).shift(1).clip(upper=5)).dropna()


C = pd.DataFrame({"fx": escalar(r_fx), "bonos": escalar(r_bd)}).dropna()
C["carry"] = C[["fx", "bonos"]].mean(axis=1)
C["spy"] = spy.resample("ME").last().pct_change().reindex(C.index)
C = C.dropna()
print("meses: %d  ·  %s -> %s" % (len(C), C.index.min().date(),
                                  C.index.max().date()))


def resu(r):
    mu, sd = r.mean() * 12, r.std() * np.sqrt(12)
    return dict(sd=sd, sh=mu / sd if sd else np.nan, mu=mu,
                t=r.mean() / r.std() * np.sqrt(len(r)),
                skew=stats.skew(r), peor=r.min(),
                peor3=r.rolling(3).sum().min())


print()
print("=" * 86)
print("1. RENDIMIENTO Y FORMA  (el Sharpe de divisas esta SUBESTIMADO:")
print("   omite el diferencial de tipos, que historicamente aporta 2-4%/año)")
print("=" * 86)
print(f"{'':<16}{'Sharpe':>8}{'t':>7}{'ASIMETRIA':>12}{'peor mes':>11}"
      f"{'peor 3m':>11}")
print("-" * 86)
for c, nom in (("fx", "carry divisas"), ("bonos", "carry bonos"),
               ("carry", "CARRY total")):
    r = resu(C[c])
    print(f"{nom:<16}{r['sh']:>8.2f}{r['t']:>7.2f}{r['skew']:>12.2f}"
          f"{r['peor']:>10.2%}{r['peor3']:>10.2%}")

print()
print("=" * 86)
print("2. ¿SE CONCENTRAN LAS PERDIDAS EN AVERSION AL RIESGO?")
print("=" * 86)
malo = C["spy"] <= C["spy"].quantile(0.10)
print("  meses en el peor decil del S&P: %d" % malo.sum())
print(f"  {'':<16}{'todos':>12}{'peor decil':>14}")
for c, nom in (("fx", "carry divisas"), ("bonos", "carry bonos"),
               ("carry", "CARRY total")):
    print(f"  {nom:<16}{C[c].mean():>11.2%}{C[c][malo].mean():>14.2%}")

print()
print("=" * 86)
print("3. ¿SE DISPARA LA CORRELACION CON ACCIONES CUANDO IMPORTA?")
print("=" * 86)
print(f"  {'':<16}{'rho global':>12}{'rho peor decil':>17}{'cambio':>10}")
for c, nom in (("fx", "carry divisas"), ("bonos", "carry bonos"),
               ("carry", "CARRY total")):
    rg = C[c].corr(C["spy"])
    rm = C[c][malo].corr(C["spy"][malo])
    print(f"  {nom:<16}{rg:>12.3f}{rm:>17.3f}{rm-rg:>+10.3f}")

# --------------------------------------------- comparacion con las dos
print()
print("=" * 86)
print("4. LAS TRES CANDIDATAS, EN LO QUE DECIDE UNA CUENTA PROP")
print("=" * 86)
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
tr = pd.read_csv("serie_trend.csv", parse_dates=["fecha"])
s2 = tr.set_index("fecha")["r"]
s2.index = s2.index + pd.offsets.MonthEnd(0)
A = pd.DataFrame({"fomc": s1, "trend": s2, "carry": C["carry"]}).dropna()
print("meses comunes a las tres: %d" % len(A))
print()
print(f"{'':<16}{'Sharpe':>8}{'ASIM.':>8}{'peor 3m':>10}"
      f"{'a vol 6%':>11}{'¿rompe 7%?':>13}")
print("-" * 86)
for c, nom in (("fomc", "#1 pre-FOMC"), ("trend", "#2 trend"),
               ("carry", "B carry")):
    r = resu(A[c])
    p3 = r["peor3"] * (0.06 / r["sd"])
    print(f"{nom:<16}{r['sh']:>8.2f}{r['skew']:>8.2f}{r['peor3']:>9.2%}"
          f"{p3:>11.2%}{('SI' if p3 < -0.07 else 'no'):>13}")

print()
print("5. CORRELACIONES")
print("-" * 86)
print(A[["fomc", "trend", "carry"]].corr().round(3).to_string())

print()
print("=" * 86)
print("CONTRASTE CON LA PREDICCION REGISTRADA")
print("=" * 86)
r = resu(C["carry"])
rg = C["carry"].corr(C["spy"])
rm = C["carry"][malo].corr(C["spy"][malo])
print("  (b) asimetria negativa fuerte  : %.2f  -> %s"
      % (r["skew"], "SE CUMPLE" if r["skew"] < -0.5 else "NO se cumple"))
print("  (c) perdidas en aversion       : %.2f%% vs %.2f%%  -> %s"
      % (C["carry"].mean() * 100, C["carry"][malo].mean() * 100,
         "SE CUMPLE" if C["carry"][malo].mean() < 0 else "NO se cumple"))
print("  (d) correlacion se dispara     : %.3f -> %.3f  -> %s"
      % (rg, rm, "SE CUMPLE" if rm > rg + 0.15 else "NO se cumple"))
