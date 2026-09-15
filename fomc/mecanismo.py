#!/usr/bin/env python3
"""
¿POR QUE EXISTE EL HUECO PRE-FOMC?  Busqueda de mecanismo.

Sin mecanismo, la confianza tiene techo: un efecto estable puede seguir siendo
una coincidencia de 15 años. Pero aqui hay una ventaja metodologica: el propio
staff report de la Fed de Nueva York (sr512) especifico los condicionantes:

   "Pre-FOMC returns are higher in periods when the slope of the Treasury
    yield curve is low, implied equity market volatility is high, and when
    past pre-FOMC returns have been high."

O sea que los condicionantes estan PRE-REGISTRADOS por terceros. Probarlos no
es pescar. Se prueban los dos primeros (el tercero es circular):

   C1  volatilidad implicita alta  -> VIX
   C2  curva de tipos plana       -> 10 años menos 3 meses

Presupuesto: 2 hipotesis. Bonferroni x2 -> |t| > 2,24.

Y una distincion critica que decide si el condicionante sirve de algo:
   si el efecto crece en BP proporcionalmente al VIX, es solo que todo es mas
   grande cuando hay volatilidad, y la ventaja ajustada por riesgo NO mejora.
   Solo si crece MAS que proporcionalmente hay senal aprovechable.
Por eso se mide en bp y tambien NORMALIZADO por la volatilidad.

Se usa el VIX del cierre ANTERIOR al hueco: es la informacion disponible en el
momento en que habria que abrir la posicion.
"""
import os
import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

DIRY = "../nas100-data/yahoo"
BONF = 2.24

# ------------------------------------------------------- datos auxiliares
for tk, nom in [("^VIX", "VIX"), ("^TNX", "TNX"), ("^IRX", "IRX")]:
    p = "%s/%s.csv" % (DIRY, nom)
    if not os.path.exists(p):
        d = yf.download(tk, start="1999-06-01", progress=False,
                        auto_adjust=False)
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)
        d.to_csv(p)
        print("descargado %s: %d sesiones" % (nom, len(d)))

EXCLUIR = {pd.Timestamp(x).date() for x in
           ["2003-09-15", "2020-03-02", "2020-03-15", "2020-03-18",
            "2025-08-22"]}
f = pd.read_csv("fomc_fechas.csv", parse_dates=["fecha"])
FOMC = set(f[~f["fecha"].dt.date.isin(EXCLUIR)]["fecha"].dt.date)


def serie(nom, col="Close"):
    d = pd.read_csv("%s/%s.csv" % (DIRY, nom), index_col=0, parse_dates=True)
    return pd.to_numeric(d[col], errors="coerce").dropna()


# huecos del NASDAQ (apertura fiable: 0,7% de contaminacion)
ndx = pd.read_csv("%s/NDX.csv" % DIRY, index_col=0, parse_dates=True)
ndx = ndx[["Open", "Close"]].dropna()
ndx = ndx[(ndx > 0).all(axis=1)]
prev = ndx["Close"].shift(1)
d = pd.DataFrame(index=ndx.index)
d["hueco"] = (ndx["Open"] / prev - 1.0) * 1e4
d["es_fomc"] = pd.Series(d.index.date, index=d.index).isin(FOMC)
d = d.dropna()
d = d[d["hueco"].abs() < 1500]

# condicionantes, tomados del cierre ANTERIOR (informacion disponible)
vix = serie("VIX").reindex(d.index, method="ffill").shift(1)
tnx = serie("TNX").reindex(d.index, method="ffill").shift(1)
irx = serie("IRX").reindex(d.index, method="ffill").shift(1)
d["vix"] = vix
d["pendiente"] = tnx - irx
# volatilidad realizada de los huecos, para normalizar
d["vol60"] = d["hueco"].rolling(60).std()
d = d.dropna()

fo = d[d["es_fomc"]].copy()
no = d[~d["es_fomc"]].copy()
print("eventos FOMC con condicionantes: %d · %s -> %s"
      % (len(fo), fo.index.min().date(), fo.index.max().date()))

# ============================================================ C1: VIX
print()
print("=" * 90)
print("C1 · VOLATILIDAD IMPLICITA (VIX del cierre anterior)")
print("=" * 90)
for etq, col, unidad in [("EN BP (sin normalizar)", "hueco", "bp"),
                         ("NORMALIZADO por vol60", "z", "sd")]:
    if col == "z":
        fo["z"] = fo["hueco"] / fo["vol60"]
        no["z"] = no["hueco"] / no["vol60"]
    q = fo["vix"].quantile([1/3, 2/3]).values
    print("\n  %s" % etq)
    print(f"  {'tercil de VIX':<22}{'n':>5}{'FOMC':>10}{'resto':>10}"
          f"{'dif':>9}{'t':>7}")
    print("  " + "-" * 66)
    res = {}
    for nom, lo, hi in [("bajo  (VIX<%.0f)" % q[0], -np.inf, q[0]),
                        ("medio", q[0], q[1]),
                        ("ALTO  (VIX>%.0f)" % q[1], q[1], np.inf)]:
        mf = (fo["vix"] > lo) & (fo["vix"] <= hi)
        mn = (no["vix"] > lo) & (no["vix"] <= hi)
        x, y = fo[col][mf].dropna(), no[col][mn].dropna()
        if len(x) < 10:
            continue
        t, _ = stats.ttest_ind(x, y, equal_var=False)
        res[nom] = (x.mean() - y.mean(), t, len(x))
        print(f"  {nom:<22}{len(x):>5}{x.mean():>10.2f}{y.mean():>10.2f}"
              f"{x.mean()-y.mean():>9.2f}{t:>7.2f}")
    # interaccion: alto contra bajo
    k = list(res)
    if len(k) == 3:
        alto = fo[col][fo["vix"] > q[1]].dropna()
        bajo = fo[col][fo["vix"] <= q[0]].dropna()
        t, p = stats.ttest_ind(alto, bajo, equal_var=False)
        print(f"  {'INTERACCION alto-bajo':<22}{'':>5}{alto.mean()-bajo.mean():>25.2f}"
              f"{t:>7.2f}   p=%.3f %s" % (p, "*" if abs(t) > BONF else ""))

# ============================================================ C2: pendiente
print()
print("=" * 90)
print("C2 · PENDIENTE DE LA CURVA (10 años menos 3 meses, cierre anterior)")
print("=" * 90)
q = fo["pendiente"].quantile([1/3, 2/3]).values
print(f"  {'tercil de pendiente':<26}{'n':>5}{'FOMC':>10}{'resto':>10}"
      f"{'dif':>9}{'t':>7}")
print("  " + "-" * 70)
for nom, lo, hi in [("PLANA (<%.2f)" % q[0], -np.inf, q[0]),
                    ("media", q[0], q[1]),
                    ("empinada (>%.2f)" % q[1], q[1], np.inf)]:
    mf = (fo["pendiente"] > lo) & (fo["pendiente"] <= hi)
    mn = (no["pendiente"] > lo) & (no["pendiente"] <= hi)
    x, y = fo["hueco"][mf], no["hueco"][mn]
    if len(x) < 10:
        continue
    t, _ = stats.ttest_ind(x, y, equal_var=False)
    print(f"  {nom:<26}{len(x):>5}{x.mean():>10.1f}{y.mean():>10.1f}"
          f"{x.mean()-y.mean():>9.1f}{t:>7.2f}")
plana = fo["hueco"][fo["pendiente"] <= q[0]]
emp = fo["hueco"][fo["pendiente"] > q[1]]
t, p = stats.ttest_ind(plana, emp, equal_var=False)
print(f"  {'INTERACCION plana-empinada':<26}{'':>5}{plana.mean()-emp.mean():>29.1f}"
      f"{t:>7.2f}   p=%.3f %s" % (p, "*" if abs(t) > BONF else ""))

# ============================================================ regresion
print()
print("=" * 90)
print("REGRESION CONJUNTA sobre los eventos FOMC")
print("  hueco = a + b1*VIX + b2*pendiente")
print("=" * 90)
X = np.column_stack([np.ones(len(fo)), fo["vix"].values,
                     fo["pendiente"].values])
y = fo["hueco"].values
beta, *_ = np.linalg.lstsq(X, y, rcond=None)
resid = y - X @ beta
s2 = resid @ resid / (len(y) - 3)
se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
for nom, b, e in zip(["constante", "VIX", "pendiente"], beta, se):
    print("  %-12s %+8.2f   SE %.2f   t = %+.2f" % (nom, b, e, b / e))

print()
print("=" * 90)
print("LECTURA")
print("=" * 90)
print("""  Lo que decidiria que hay mecanismo:
    - el efecto es claramente mayor con VIX alto Y sigue siendo mayor tras
      normalizar por volatilidad  -> el condicionante aporta senal
    - la interaccion pasa |t| > 2,24
  Si solo crece en bp pero desaparece al normalizar, entonces el VIX no es un
  mecanismo: es solo que todo es mas grande cuando hay volatilidad, y no
  mejora la ventaja ajustada por riesgo.""")
