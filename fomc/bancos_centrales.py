#!/usr/bin/env python3
"""
¿GENERALIZA LA PRIMA NOCTURNA A OTROS BANCOS CENTRALES?

El mecanismo que emergio: prima de riesgo de MERCADO en la ventana nocturna
previa a un anuncio de politica monetaria. Si eso es lo que hay, no es
exclusivo de la Fed.

DISEÑO 2x2, que es lo que hace esta prueba fuerte:

                        anuncio del BoJ      anuncio de la Fed
      Nikkei 225        <- deberia SI        <- deberia NO
      NASDAQ 100        <- deberia NO        <- SI (ya medido, t=3,76)

Cada indice frente a SU banco central y frente al EXTRANJERO. La prediccion no
es solo "hay efecto", es un PATRON DIAGONAL. Un efecto de calendario, un
artefacto de datos o un sesgo global no produciria una diagonal.

Fechas del BoJ: 128 reuniones 2013-2026, extraidas de las URLs de sus
comunicados de decision (patron /k{YYMMDD}), con recuentos validados
(14/año antes de 2016, 8/año despues, 9 en 2020 por la reunion de emergencia).

Horarios: el BoJ anuncia entre las 11:30 y las 12:30 JST, con la sesion del
Nikkei de 09:00 a 15:00. El hueco nocturno (cierre 15:00 -> apertura 09:00)
esta ENTERO antes del anuncio, igual que en el caso de la Fed.
"""
import re
import glob
import datetime as dt
import numpy as np
import pandas as pd
from scipy import stats

DIRY = "../nas100-data/yahoo"

# ---------------------------------------------------------- fechas BoJ
BOJ = set()
for p in sorted(glob.glob("boj/boj*.html")):
    y = p.split("boj")[-1][:4]
    t = open(p, encoding="utf-8", errors="ignore").read()
    for s in set(re.findall(r"/k(\d{6})[a-z]?\.", t)):
        if s[:2] != y[2:]:
            continue
        try:
            BOJ.add(dt.datetime.strptime(s, "%y%m%d").date())
        except ValueError:
            pass
print("reuniones del BoJ: %d  ·  %s -> %s"
      % (len(BOJ), min(BOJ), max(BOJ)))

# ---------------------------------------------------------- fechas Fed
EXCLUIR = {pd.Timestamp(x).date() for x in
           ["2003-09-15", "2020-03-02", "2020-03-15", "2020-03-18",
            "2025-08-22"]}
f = pd.read_csv("fomc_fechas.csv", parse_dates=["fecha"])
FED = set(f[~f["fecha"].dt.date.isin(EXCLUIR)]["fecha"].dt.date)


def gaps(tk, desde=2013):
    d = pd.read_csv("%s/%s.csv" % (DIRY, tk), index_col=0, parse_dates=True)
    d = d[["Open", "Close"]].dropna()
    d = d[(d > 0).all(axis=1)]
    d = d[d.index.year >= desde]
    prev = d["Close"].shift(1)
    g = ((d["Open"] / prev - 1.0) * 1e4).dropna()
    return g[g.abs() < 1000]


def contrasta(g, fechas, a=None, b=None):
    idx = g.index
    m = pd.Series(idx.date, index=idx).isin(fechas)
    if a:
        sel = (idx.year >= a) & (idx.year <= b)
        g, m = g[sel], m[sel]
    x, y = g[m], g[~m]
    if len(x) < 10:
        return None
    t, p = stats.ttest_ind(x, y, equal_var=False)
    return dict(n=len(x), mx=x.mean(), my=y.mean(),
                dif=x.mean() - y.mean(), t=t, p=p)


G = {"N225": gaps("N225"), "NDX": gaps("NDX"), "GDAXI": gaps("GDAXI"),
     "EURUSD": gaps("EURUSD")}

# =========================================================== la matriz 2x2
print()
print("=" * 84)
print("MATRIZ 2x2 · hueco nocturno previo al anuncio, 2013-2026")
print("=" * 84)
print(f"{'':<16}{'anuncio del BoJ':>32}{'anuncio de la Fed':>32}")
print(f"{'':<16}{'n':>6}{'dif':>9}{'t':>8}{'p':>9}"
      f"{'n':>6}{'dif':>9}{'t':>8}{'p':>9}")
print("-" * 84)
for tk, nom in [("N225", "Nikkei 225"), ("NDX", "NASDAQ 100"),
                ("GDAXI", "DAX"), ("EURUSD", "EUR/USD")]:
    fila = ""
    for fechas in (BOJ, FED):
        r = contrasta(G[tk], fechas)
        fila += (f"{r['n']:>6}{r['dif']:>9.1f}{r['t']:>8.2f}{r['p']:>9.3f}"
                 if r else f"{'-':>32}")
    print(f"{nom:<16}{fila}")

print()
print("  Prediccion del mecanismo: DIAGONAL fuerte (Nikkei-BoJ y NASDAQ-Fed),")
print("  fuera de la diagonal plano. Un efecto de calendario o un sesgo global")
print("  no distingue de que banco central se trata.")

# =========================================================== por subperiodos
print()
print("=" * 84)
print("NIKKEI ANTE EL BoJ, POR SUBPERIODOS")
print("=" * 84)
print(f"{'tramo':<14}{'n':>5}{'BoJ':>9}{'resto':>8}{'dif':>8}{'t':>7}{'p':>8}")
print("-" * 84)
for etq, a, b in [("2013-2015", 2013, 2015), ("2016-2019", 2016, 2019),
                  ("2020-2026", 2020, 2026), ("TODO", 2013, 2026)]:
    r = contrasta(G["N225"], BOJ, a, b)
    if r:
        print(f"{etq:<14}{r['n']:>5}{r['mx']:>9.1f}{r['my']:>8.1f}"
              f"{r['dif']:>8.1f}{r['t']:>7.2f}{r['p']:>8.3f}")

# =========================================================== economia
print()
print("=" * 84)
print("ECONOMIA COMBINADA si el BoJ funciona")
print("=" * 84)
rb = contrasta(G["N225"], BOJ)
rf = contrasta(G["NDX"], FED)
gb = G["N225"][pd.Series(G["N225"].index.date,
                         index=G["N225"].index).isin(BOJ)]
gf = G["NDX"][pd.Series(G["NDX"].index.date, index=G["NDX"].index).isin(FED)]
COSTE = 1.25 + 2 * 0.75          # swap de una noche + spread ida y vuelta
print(f"{'estrategia':<22}{'ev/año':>8}{'bruto':>9}{'neto':>8}"
      f"{'sd':>8}{'Sharpe':>9}")
print("-" * 84)
for nom, serie, n_ano in [("Fed -> NASDAQ", gf, 8),
                          ("BoJ -> Nikkei", gb, 9)]:
    neto = serie.mean() - COSTE
    sh = neto / serie.std() * np.sqrt(n_ano)
    print(f"{nom:<22}{n_ano:>8}{serie.mean():>9.1f}{neto:>8.1f}"
          f"{serie.std():>8.1f}{sh:>9.2f}")
# cartera: correlacion entre las dos series de eventos (casi nunca coinciden)
print()
comunes = set(gb.index.date) & set(gf.index.date)
print("  dias en que coinciden ambos eventos: %d" % len(comunes))
print("  -> son eventos casi disjuntos, asi que la cartera suma operaciones")
print("     sin solaparse: ~17 al año")

print()
print("=" * 84)
print("VEREDICTO")
print("=" * 84)
diag = [("Nikkei ante BoJ", contrasta(G["N225"], BOJ)),
        ("NASDAQ ante Fed", contrasta(G["NDX"], FED))]
off = [("Nikkei ante Fed", contrasta(G["N225"], FED)),
       ("NASDAQ ante BoJ", contrasta(G["NDX"], BOJ)),
       ("EUR/USD ante BoJ", contrasta(G["EURUSD"], BOJ))]
for nom, r in diag:
    print("  DIAGONAL   %-18s %+.1f bp · t=%.2f %s"
          % (nom, r["dif"], r["t"], "OK" if r["t"] > 1.96 else "<- falla"))
for nom, r in off:
    print("  fuera diag %-18s %+.1f bp · t=%.2f %s"
          % (nom, r["dif"], r["t"], "OK (plano)" if abs(r["t"]) < 1.96
             else "<- DISPARA, mal"))
