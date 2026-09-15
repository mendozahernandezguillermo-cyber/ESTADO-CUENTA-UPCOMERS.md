#!/usr/bin/env python3
"""
ESTRATEGIA #2 · candidata: DIFERENCIAL NASDAQ - S&P EN EL HUECO PRE-FOMC

Por que este dominio y no otro efecto de calendario: el pozo de los efectos de
calendario direccionales sobre indices esta seco (13 familias probadas, 1 pasa).
Un DIFERENCIAL es estructuralmente distinto:

  - elimina el riesgo de mercado comun, que es la mayor parte del ruido
  - si las dos patas correlacionan ~0,9, sd(diferencial) ~ 0,45 x sd(pata)
    -> el umbral de deteccion baja a menos de la mitad

RAZON TEORICA, documentada y previa: el NASDAQ es un activo de DURACION MAS
LARGA (crecimiento, flujos lejanos) y por tanto mas sensible a las
expectativas de tipos. El FOMC es precisamente lo que mueve esas expectativas.

DECLARADO ANTES DE MIRAR:
  primaria    : diferencial QQQ - SPY en el hueco 16:00 -> apertura, dias FOMC
  descriptivas: QQQ-DIA e IWM-SPY (para ver si es "tech contra amplio" o algo
                mas general).  Se etiquetan como descriptivas, no cuentan
                como pruebas.
  control     : los mismos dias de IPC y empleo, donde ya demostramos que NO
                hay prima nocturna. Si el diferencial dispara ahi tambien, es
                un efecto de calendario y no del FOMC.

Se usan ETFs y no indices porque su apertura es un precio NEGOCIADO de verdad.
Coste: un diferencial son DOS patas, asi que se paga el spread dos veces.
"""
import os
import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

DIRY = "../nas100-data/yahoo"
ETFS = ["QQQ", "SPY", "DIA", "IWM"]

for tk in ETFS:
    p = "%s/%s.csv" % (DIRY, tk)
    if not os.path.exists(p):
        d = yf.download(tk, start="1999-03-10", progress=False,
                        auto_adjust=False)
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)
        d.to_csv(p)
        print("descargado %s: %d sesiones" % (tk, len(d)))

EXCLUIR = {pd.Timestamp(x).date() for x in
           ["2003-09-15", "2020-03-02", "2020-03-15", "2020-03-18",
            "2025-08-22"]}
f = pd.read_csv("fomc_fechas.csv", parse_dates=["fecha"])
FOMC = set(f[~f["fecha"].dt.date.isin(EXCLUIR)]["fecha"].dt.date)


def gaps(tk):
    d = pd.read_csv("%s/%s.csv" % (DIRY, tk), index_col=0, parse_dates=True)
    d = d[["Open", "Close"]].dropna()
    d = d[(d > 0).all(axis=1)]
    prev = d["Close"].shift(1)
    g = (d["Open"] / prev - 1.0) * 1e4
    mala = (np.abs(d["Open"] / prev - 1) < 1e-9).mean()
    return g.dropna(), mala


print()
print("=" * 88)
print("CONTROL DE CALIDAD DE LA APERTURA DE LOS ETFs")
print("=" * 88)
G = {}
for tk in ETFS:
    g, mala = gaps(tk)
    G[tk] = g
    print("  %-5s  %d sesiones  ·  Open==cierre previo: %.2f%%  %s"
          % (tk, len(g), 100 * mala, "OK" if mala < 0.02 else "SOSPECHOSO"))

# dias de IPC y empleo (control): primer viernes y mitad de mes
idx = G["SPY"].index
vie = idx[idx.dayofweek == 4]
prim = pd.Series(vie).groupby([vie.year, vie.month]).min()
PRIM_VIE = set(pd.to_datetime(prim.values).date)
MID = {d.date() for d in idx if 9 <= d.day <= 16}

PARES = [("QQQ", "SPY", "PRIMARIA"), ("QQQ", "DIA", "descriptiva"),
         ("IWM", "SPY", "descriptiva")]
TRAMOS = [("2000-2011", 2000, 2011), ("2012-2019", 2012, 2019),
          ("2020-2026", 2020, 2026), ("TODO", 1999, 2026)]

print()
print("=" * 88)
print("DIFERENCIAL EN EL HUECO NOCTURNO  ·  dias FOMC contra el resto")
print("=" * 88)
resultados = {}
for a, b, tipo in PARES:
    s = (G[a] - G[b]).dropna()
    s = s[s.abs() < 800]
    fom = pd.Series(s.index.date, index=s.index).isin(FOMC)
    print("\n  %s - %s   [%s]   sd del diferencial: %.1f bp   "
          "(patas: %.1f y %.1f)"
          % (a, b, tipo, s.std(), G[a].reindex(s.index).std(),
             G[b].reindex(s.index).std()))
    print(f"  {'tramo':<12}{'n':>5}{'FOMC':>9}{'resto':>8}{'dif':>8}"
          f"{'t':>7}{'p':>8}")
    print("  " + "-" * 60)
    for etq, y0, y1 in TRAMOS:
        m = (s.index.year >= y0) & (s.index.year <= y1)
        x, y = s[m & fom], s[m & ~fom]
        if len(x) < 12:
            continue
        t, p = stats.ttest_ind(x, y, equal_var=False)
        if etq == "TODO":
            resultados[(a, b)] = dict(dif=x.mean() - y.mean(), t=t, p=p,
                                      n=len(x), sd=x.std(), mx=x.mean())
        print(f"  {etq:<12}{len(x):>5}{x.mean():>9.1f}{y.mean():>8.1f}"
              f"{x.mean()-y.mean():>8.1f}{t:>7.2f}{p:>8.3f}")

# ------------------------------------------------------------- control
print()
print("=" * 88)
print("CONTROL · ¿dispara tambien en dias SIN prima nocturna demostrada?")
print("(empleo y IPC: ya medimos que ahi no hay prima en el nivel)")
print("=" * 88)
s = (G["QQQ"] - G["SPY"]).dropna()
s = s[s.abs() < 800]
fom = pd.Series(s.index.date, index=s.index).isin(FOMC)
emp = pd.Series(s.index.date, index=s.index).isin(PRIM_VIE)
ipc = pd.Series(s.index.date, index=s.index).isin(MID)
base = s[~(fom | emp | ipc)]
print(f"  {'grupo':<22}{'n':>6}{'media':>9}{'base':>8}{'dif':>8}{'t':>7}{'p':>8}")
print("  " + "-" * 62)
for nom, m in [("FOMC", fom), ("empleo (1er viernes)", emp & ~fom),
               ("IPC (mitad de mes)", ipc & ~fom)]:
    x = s[m]
    t, p = stats.ttest_ind(x, base, equal_var=False)
    print(f"  {nom:<22}{len(x):>6}{x.mean():>9.1f}{base.mean():>8.1f}"
          f"{x.mean()-base.mean():>8.1f}{t:>7.2f}{p:>8.3f}")

# ------------------------------------------------------------- economia
print()
print("=" * 88)
print("ECONOMIA · un diferencial paga el spread DOS VECES")
print("=" * 88)
r = resultados[("QQQ", "SPY")]
print("  diferencial QQQ-SPY en dias FOMC: %+.1f bp brutos (sd %.1f, n=%d)"
      % (r["mx"], r["sd"], r["n"]))
print()
print(f"  {'spread/pata':>13}{'coste total':>13}{'neto':>9}"
      f"{'bp/año (8 ev)':>15}{'Sharpe':>9}")
print("  " + "-" * 62)
SWAP = 0.0456 / 365 * 1e4 * 0          # un diferencial es casi neutral en swap
for sp in (0.25, 0.5, 1.0, 2.0):
    coste = 4 * sp                     # 2 patas x ida y vuelta
    neto = r["mx"] - coste
    sh = neto / r["sd"] * np.sqrt(8)
    print(f"  {sp:>13.2f}{-coste:>13.1f}{neto:>9.1f}{neto*8:>15.0f}{sh:>9.2f}")
print()
print("  Nota: al ser largo de uno y corto del otro, la financiacion casi se")
print("  cancela. Eso elimina el coste que mato a la prima nocturna general.")

print()
print("=" * 88)
print("VEREDICTO")
print("=" * 88)
r = resultados[("QQQ", "SPY")]
print("  PRIMARIA QQQ-SPY: %+.1f bp · t=%.2f · p=%.4f · n=%d"
      % (r["dif"], r["t"], r["p"], r["n"]))
for k in [("QQQ", "DIA"), ("IWM", "SPY")]:
    if k in resultados:
        rr = resultados[k]
        print("  descriptiva %s-%s: %+.1f bp · t=%.2f"
              % (k[0], k[1], rr["dif"], rr["t"]))
print()
print("  Umbral con una sola hipotesis primaria: |t| > 1,96")
print("  Y para compararlo con la pata sola: el hueco del NASDAQ dio t=3,76")
