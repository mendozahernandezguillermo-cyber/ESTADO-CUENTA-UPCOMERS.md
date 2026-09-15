#!/usr/bin/env python3
"""
OPCION C · PRIMA DE RIESGO DE VARIANZA  ·  version 2

Arreglos de la v1:
  - ^VIX3M no tiene historico en Yahoo (devolvia 1 sesion), asi que la señal de
    contango por estructura temporal no se puede construir asi.
  - En su lugar se usa la PRIMA DE VARIANZA propiamente dicha, que es mas fiel
    al efecto documentado y no necesita datos extra:
        señal = VIX - volatilidad REALIZADA de 21 dias del S&P
    Cuando la implicita supera a la realizada, se vende volatilidad.
  - VXX empieza en 2018 (es la Serie B; la ETN original esta bajo otro ticker).
    La muestra 2018-2026 incluye los DOS desplomes historicos de la estrategia:
    5 de febrero de 2018 y marzo de 2020. Para analizar la cola, es la muestra
    que importa.
  - Se añade SVXY (2011+) como segundo instrumento, con el aviso de que en
    febrero de 2018 CAMBIO su apalancamiento de -1x a -0,5x porque la
    estrategia revento. Que el instrumento tuviera que rediseñarse ya es un
    dato sobre la estrategia.

PREDICCION REGISTRADA: (a) Sharpe alto 0,8-1,2 · (b) asimetria catastrofica ·
(c) rompe el limite del 7% con margen · (d) correlacion que se dispara en
crisis · (e) el detector de grid la marcaria.
"""
import os
import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

DIR = "datos"


def bajar(tk, desde="2004-01-01"):
    p = os.path.join(DIR, tk.replace("^", "").replace("=", "") + ".csv")
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


vix, vxx, svxy, spy = bajar("^VIX"), bajar("VXX"), bajar("SVXY"), bajar("SPY")

r_spy = spy.pct_change().dropna()
rv = r_spy.rolling(21).std() * np.sqrt(252) * 100        # realizada, en puntos
prima = (vix.reindex(rv.index, method="ffill") - rv).dropna()


def resu(r, per=252):
    r = r.dropna()
    if len(r) < 50:
        return None
    mu, sd = r.mean() * per, r.std() * np.sqrt(per)
    eq = (1 + r).cumprod()
    return dict(n=len(r), mu=mu, sd=sd, sh=mu / sd if sd else np.nan,
                skew=stats.skew(r), kurt=stats.kurtosis(r), peor=r.min(),
                peor5=r.rolling(5).sum().min(),
                peor21=r.rolling(21).sum().min(),
                dd=(eq / eq.cummax() - 1).min())


ESTRAT = {}
for nom, px, signo in [("corto VXX", vxx, -1.0), ("largo SVXY", svxy, +1.0)]:
    if px is None:
        continue
    r = px.pct_change().dropna()
    sig = np.sign(prima.reindex(r.index, method="ffill").shift(1)).clip(lower=0)
    ESTRAT[nom + " siempre"] = signo * r
    ESTRAT[nom + " con prima>0"] = (signo * r * sig).dropna()

print("=" * 88)
print("PRIMA DE VARIANZA · VIX menos volatilidad realizada de 21 dias")
print("=" * 88)
print("  prima positiva en %.1f%% de los dias · media %.1f puntos"
      % (100 * (prima > 0).mean(), prima.mean()))
print()
print(f"{'estrategia':<26}{'n':>6}{'retorno':>10}{'vol':>9}{'Sharpe':>8}"
      f"{'ASIM.':>8}{'curt.':>7}{'peor dia':>10}")
print("-" * 88)
for nom, r in ESTRAT.items():
    x = resu(r)
    if x:
        print(f"{nom:<26}{x['n']:>6}{x['mu']:>9.1%}{x['sd']:>9.1%}"
              f"{x['sh']:>8.2f}{x['skew']:>8.2f}{x['kurt']:>7.1f}"
              f"{x['peor']:>9.1%}")

PRINC = "corto VXX con prima>0"
r_c = ESTRAT[PRINC].dropna()
x = resu(r_c)

print()
print("=" * 88)
print("LOS PEORES DIAS DE '%s'" % PRINC)
print("=" * 88)
for d, v in r_c.nsmallest(8).items():
    print("   %s   %+7.1f%%" % (d.date(), v * 100))

print()
print("=" * 88)
print("¿SOBREVIVE A UN LIMITE DE DRAWDOWN TRAILING DEL 7%?")
print("=" * 88)
lev = 0.06 / x["sd"]
print("  vol anual sin apalancar: %.1f%%  ·  para llegar al 6%% habria que"
      " DESapalancar a x%.3f" % (x["sd"] * 100, lev))
print()
print(f"  {'ventana':<16}{'peor caso':>12}{'escalado a vol 6%':>20}"
      f"{'¿rompe el 7%?':>16}")
print("  " + "-" * 66)
for etq, v in [("1 dia", x["peor"]), ("5 dias", x["peor5"]),
               ("21 dias", x["peor21"]), ("drawdown max", x["dd"])]:
    a = v * lev
    print(f"  {etq:<16}{v:>11.1%}{a:>20.1%}{('SI' if a < -0.07 else 'no'):>16}")

print()
print("=" * 88)
print("CORRELACION CON ACCIONES")
print("=" * 88)
rs = r_spy.reindex(r_c.index)
malo = rs <= rs.quantile(0.05)
print("  rho global                 : %+.3f" % r_c.corr(rs))
print("  rho en el peor 5%% del S&P   : %+.3f" % r_c[malo].corr(rs[malo]))
print("  retorno medio esos dias    : %+.2f%%  (media global %+.3f%%)"
      % (r_c[malo].mean() * 100, r_c.mean() * 100))

print()
print("=" * 88)
print("NUESTRO PROPIO DETECTOR DE GRID, APLICADO A ESTA ESTRATEGIA")
print("=" * 88)
p01, p99 = np.percentile(r_c, [1, 99])
print("  %% de dias positivos           : %.1f%%" % (100 * (r_c > 0).mean()))
print("  percentil 1 / percentil 99    : %+.2f%% / %+.2f%%" % (p01 * 100, p99 * 100))
print("  ratio de colas izquierda/derecha: %.2f" % (abs(p01) / abs(p99)))
print("  asimetria                     : %.2f" % x["skew"])
print("  R5 (asimetria < -0,50)        : %s"
      % ("DISPARA" if x["skew"] < -0.5 else "no"))

print()
print("=" * 88)
print("CONTRASTE CON LA PREDICCION REGISTRADA")
print("=" * 88)
print("  (a) Sharpe alto 0,8-1,2   : %.2f -> %s" % (x["sh"],
      "SE CUMPLE" if 0.8 <= x["sh"] <= 1.2 else "NO: menor de lo que predije"))
print("  (b) asimetria catastrofica: %.2f -> %s" % (x["skew"],
      "SE CUMPLE" if x["skew"] < -1 else "negativa pero menos extrema"))
print("  (c) rompe el limite del 7%%: peor dia escalado %.1f%% -> %s"
      % (x["peor"] * lev * 100,
         "SE CUMPLE" if x["peor"] * lev < -0.07 else "NO se cumple"))
rg, rm = r_c.corr(rs), r_c[malo].corr(rs[malo])
print("  (d) correlacion se dispara: %+.3f -> %+.3f -> %s" % (rg, rm,
      "SE CUMPLE" if rm > rg + 0.1 else "NO se cumple"))
print("  (e) el detector la marca  : %s" % ("SI" if x["skew"] < -0.5 else "no"))
