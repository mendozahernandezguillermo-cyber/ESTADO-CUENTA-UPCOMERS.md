#!/usr/bin/env python3
"""
EL HUECO NOCTURNO EN FECHAS SELECCIONADAS  ·  muestra completa 2000-2026

Todo lo que hemos encontrado vive en el hueco nocturno (cierre -> apertura
siguiente). Aqui se mide directamente, sobre los dos casos con mecanismo
alegado y fecha conocida de antemano:

   H1  el hueco de entrada al dia del anuncio del FOMC   (8 al año)
   H2  el hueco de entrada al primer dia de mes          (12 al año)

Presupuesto: DOS hipotesis declaradas. Bonferroni x2 -> |t| > 2,24.
Los instrumentos son confirmacion, no busqueda.

Solo se usan series cuya APERTURA paso el control de calidad, porque el hueco
la necesita: NASDAQ 0,7% · DAX 0,1% · Nikkei 0,0% · oro 2,8%.
El S&P 500 solo desde 2016 (antes, 26% de aperturas rellenadas).
EUR/USD como control de calendario.

Y el coste, con el modelo correcto que antes tenia mal:
   swap = 1,249 bp por NOCHE AGUANTADA (4,56% anual / 365)
   spread ida y vuelta = 2 x spread_ida
   -> solo se paga en las noches que se opera, no todos los dias del año
"""
import numpy as np
import pandas as pd
from scipy import stats

DIRY = "../nas100-data/yahoo"
BONF = 2.24
SWAP_NOCHE = 0.0456 / 365.0 * 1e4        # 1,249 bp

EXCLUIR = {pd.Timestamp(x).date() for x in
           ["2003-09-15", "2020-03-02", "2020-03-15", "2020-03-18",
            "2025-08-22"]}
f = pd.read_csv("fomc_fechas.csv", parse_dates=["fecha"])
FOMC = set(f[~f["fecha"].dt.date.isin(EXCLUIR)]["fecha"].dt.date)

INSTR = [
    ("NDX",    "NASDAQ 100",  None, "accion"),
    ("GDAXI",  "DAX",         None, "accion"),
    ("N225",   "Nikkei 225",  None, "accion"),
    ("GSPC",   "S&P 500",     2016, "accion"),
    ("GCF",    "Oro",         None, "flujo-sensible"),
    ("EURUSD", "EUR/USD",     None, "CONTROL calendario"),
]


def cargar(tk, desde=None):
    df = pd.read_csv("%s/%s.csv" % (DIRY, tk), index_col=0, parse_dates=True)
    df = df[["Open", "Close"]].dropna()
    df = df[(df > 0).all(axis=1)]
    if desde:
        df = df[df.index.year >= desde]
    prev = df["Close"].shift(1)
    df["hueco"] = (df["Open"] / prev - 1.0) * 1e4
    df["noches"] = df.index.to_series().diff().dt.days
    df = df.dropna()
    df = df[(df["hueco"].abs() < 1500) & (df["noches"].between(1, 5))]
    g = df.groupby([df.index.year, df.index.month])
    df["dia1"] = (g.cumcount() + 1) == 1
    df["fomc"] = pd.Series(df.index.date, index=df.index).isin(FOMC)
    return df


def prueba(df, mask, a=None, b=None):
    m = pd.Series(True, index=df.index)
    if a:
        m &= (df.index.year >= a) & (df.index.year <= b)
    x, y = df["hueco"][m & mask], df["hueco"][m & ~mask]
    if len(x) < 15:
        return None
    t, p = stats.ttest_ind(x, y, equal_var=False)
    return dict(n=len(x), mx=x.mean(), my=y.mean(), dif=x.mean() - y.mean(),
                sd=x.std(), t=t, p=p, noches=df["noches"][m & mask].mean())


TRAMOS = [("2000-2011", 2000, 2011), ("2012-2019", 2012, 2019),
          ("2020-2026", 2020, 2026)]

for etiqueta, campo in [("H1 · HUECO DE ENTRADA AL DIA DEL FOMC", "fomc"),
                        ("H2 · HUECO DE ENTRADA AL PRIMER DIA DE MES", "dia1")]:
    print("=" * 92)
    print(etiqueta)
    print("=" * 92)
    print(f"{'instrumento':<14}{'tipo':<20}{'tramo':<11}{'n':>5}"
          f"{'hueco':>9}{'resto':>8}{'dif':>8}{'t':>7}{'p':>8}")
    print("-" * 92)
    for tk, nom, desde, tipo in INSTR:
        df = cargar(tk, desde)
        for tetq, a, b in TRAMOS + [("TODO", 2000, 2026)]:
            r = prueba(df, df[campo], a, b)
            if not r:
                continue
            marca = " *" if abs(r["t"]) > BONF else ""
            print(f"{nom if tetq=='2000-2011' or desde else '':<14}"
                  f"{tipo if tetq=='2000-2011' or desde else '':<20}"
                  f"{tetq:<11}{r['n']:>5}{r['mx']:>9.1f}{r['my']:>8.1f}"
                  f"{r['dif']:>8.1f}{r['t']:>7.2f}{r['p']:>8.3f}{marca}")
        print()

# ==================================================== economia de la estrategia
print("=" * 92)
print("ECONOMIA DE LA ESTRATEGIA SELECTIVA  (solo las noches con evento)")
print("=" * 92)
print("coste por noche = %.2f bp de swap + spread ida y vuelta" % SWAP_NOCHE)
print()
for sp in (0.75, 1.50):
    print("  --- spread de ida %.2f bp (ida y vuelta %.2f) ---" % (sp, 2 * sp))
    print(f"  {'instrumento':<14}{'ev/año':>8}{'bruto':>9}{'coste':>8}"
          f"{'NETO':>8}{'bp/año':>9}{'Sharpe':>9}")
    print("  " + "-" * 74)
    for tk, nom, desde, tipo in INSTR:
        if tipo != "accion":
            continue
        df = cargar(tk, desde)
        sel = df["fomc"] | df["dia1"]
        x = df["hueco"][sel]
        anos = (df.index.max() - df.index.min()).days / 365.25
        n_ano = len(x) / anos
        coste = df["noches"][sel].mean() * SWAP_NOCHE + 2 * sp
        neto = x - (df["noches"][sel] * SWAP_NOCHE + 2 * sp)
        sh = neto.mean() / neto.std() * np.sqrt(n_ano) if neto.std() > 0 else np.nan
        print(f"  {nom:<14}{n_ano:>8.0f}{x.mean():>9.1f}{-coste:>8.1f}"
              f"{neto.mean():>8.1f}{neto.mean()*n_ano:>9.0f}{sh:>9.2f}")
    print()

# ==================================================== veredicto
print("=" * 92)
print("VEREDICTO")
print("=" * 92)
acc = [(tk, nom, desde) for tk, nom, desde, tp in INSTR if tp == "accion"]
for campo, etq in (("fomc", "H1 FOMC"), ("dia1", "H2 primer dia")):
    sig = pos = 0
    for tk, nom, desde in acc:
        r = prueba(cargar(tk, desde), cargar(tk, desde)[campo])
        if r:
            pos += r["dif"] > 0
            sig += abs(r["t"]) > BONF
    print("  %-16s dif>0 en %d/%d · |t|>2,24 en %d/%d"
          % (etq, pos, len(acc), sig, len(acc)))
print()
for tk, nom in (("EURUSD", "EUR/USD (control calendario)"), ("GCF", "Oro")):
    df = cargar(tk)
    for campo, e in (("fomc", "FOMC"), ("dia1", "dia 1")):
        r = prueba(df, df[campo])
        if r:
            print("  %-30s %-7s %+.1f bp · t=%.2f" % (nom, e, r["dif"], r["t"]))
