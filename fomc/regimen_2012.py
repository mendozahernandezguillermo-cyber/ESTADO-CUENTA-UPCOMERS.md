#!/usr/bin/env python3
"""
REAPERTURA SISTEMATICA DE LAS HIPOTESIS DESCARTADAS, BAJO REGIMEN POST-2012

Motivacion (del usuario, y la evidencia le da la razon): el mercado cambia por
regimenes y promediar 26 años puede enterrar efectos que solo existen en el
actual. Nuestros propios numeros lo muestran: el pre-FOMC del DAX esta ausente
antes de 2012 y presente despues; el trend cae de Sharpe 1,05 a 0,45; vender
volatilidad pasa de Sharpe >1 a 0,37.

GUARDARRAILES, declarados ANTES de volver a mirar:
  1. El inicio del regimen se fija en 2012 por una razon del MUNDO -- tipos a
     cero y QE consolidados, la Fed como conductor dominante del riesgo global
     -- y NO por donde salen bien los numeros.
  2. Dentro del regimen se exige significancia en las DOS MITADES por separado
     (2012-2018 y 2019-2026), con el MISMO SIGNO. Una sola mitad no vale.
  3. Se compara contra el TECHO DE RUIDO calculado en la misma ventana con
     celdas de calendario arbitrarias.
  4. Los controles negativos (oro, EUR/USD) tienen que seguir fallando.

Esto es una prueba sistematica de la hipotesis de regimen, no un rescate
selectivo: se reabren TODAS las descartadas, no solo las prometedoras.
"""
import numpy as np
import pandas as pd
from scipy import stats

DIRY = "../nas100-data/yahoo"
H1 = (2012, 2018)
H2 = (2019, 2026)

EXCL = {pd.Timestamp(x).date() for x in
        ["2003-09-15", "2020-03-02", "2020-03-15", "2020-03-18", "2025-08-22"]}
f = pd.read_csv("fomc_fechas.csv", parse_dates=["fecha"])
FOMC = set(f[~f["fecha"].dt.date.isin(EXCL)]["fecha"].dt.date)


def cargar(tk):
    d = pd.read_csv("%s/%s.csv" % (DIRY, tk), index_col=0, parse_dates=True)
    d = d[["Open", "Close"]].dropna()
    d = d[(d > 0).all(axis=1)]
    prev = d["Close"].shift(1)
    d["gap"] = (d["Open"] / prev - 1.0) * 1e4
    d["cc"] = (d["Close"] / prev - 1.0) * 1e4
    d["oc"] = (d["Close"] / d["Open"] - 1.0) * 1e4
    d = d.dropna()
    d = d[d["cc"].abs() < 1500]
    idx = d.index
    d["fomc"] = pd.Series(idx.date, index=idx).isin(FOMC)
    g = d.groupby([idx.year, idx.month])
    d["pi"] = g.cumcount() + 1
    d["pf"] = g.cumcount(ascending=False) + 1
    d["dia1"] = d["pi"] == 1
    d["tom"] = (d["pf"] == 1) | (d["pi"] <= 3)
    d["dow"] = idx.dayofweek
    d["lunes"] = d["dow"] == 1
    vie = idx[idx.dayofweek == 4]
    ter, prim = set(), set()
    for _, gg in pd.Series(vie).groupby([vie.year, vie.month]):
        s = sorted(gg)
        prim.add(s[0])
        if len(s) >= 3:
            ter.add(s[2])
    d["venc"] = idx.isin(ter)
    d["trim"] = d["venc"] & idx.month.isin([3, 6, 9, 12])
    sem = np.zeros(len(d), dtype=bool)
    for p in np.where(d["venc"].values)[0]:
        sem[max(0, p - 4):p + 1] = True
    d["semvenc"] = sem
    d["empleo"] = idx.isin(prim)
    d["ipc"] = (idx.day >= 9) & (idx.day <= 16)
    d["todos"] = True
    d["semmes"] = np.minimum((d["pi"] - 1) // 5, 3)
    return d


D = {tk: cargar(tk) for tk in
     ("NDX", "GSPC", "GDAXI", "N225", "QQQ", "SPY", "GCF", "EURUSD")}

# diferencial QQQ-SPY
sp = (D["QQQ"]["gap"] - D["SPY"]["gap"]).dropna()
SPREAD = pd.DataFrame({"gap": sp[sp.abs() < 800]})
SPREAD["fomc"] = pd.Series(SPREAD.index.date, index=SPREAD.index).isin(FOMC)
D["QQQ-SPY"] = SPREAD


def t_en(df, campo, col, a, b):
    m = (df.index.year >= a) & (df.index.year <= b)
    if campo not in df.columns or col not in df.columns:
        return None
    x = df[col][m & df[campo]]
    y = df[col][m & ~df[campo]]
    if len(x) < 12 or x.std() == 0:
        return None
    t, p = stats.ttest_ind(x, y, equal_var=False)
    return len(x), x.mean() - y.mean(), t


# --------------------------------------------- techo de ruido por mitad
def techo(df, a, b):
    ts = []
    for dw in range(5):
        for sm in range(4):
            for col in ("gap", "cc"):
                if col not in df.columns:
                    continue
                m = (df["dow"] == dw) & (df["semmes"] == sm)
                mm = (df.index.year >= a) & (df.index.year <= b)
                x, y = df[col][mm & m], df[col][mm & ~m]
                if len(x) >= 12 and x.std() > 0:
                    ts.append(abs(stats.ttest_ind(x, y, equal_var=False).statistic))
    return max(ts) if ts else np.nan


tc1, tc2 = techo(D["NDX"], *H1), techo(D["NDX"], *H2)
print("=" * 92)
print("TECHO DE RUIDO (max |t| de 40 celdas de calendario arbitrarias)")
print("   2012-2018: %.2f      2019-2026: %.2f" % (tc1, tc2))
print("=" * 92)

HIP = [
    ("hueco pre-FOMC",        "NDX",     "fomc",    "gap", "prueba"),
    ("hueco pre-FOMC",        "GSPC",    "fomc",    "gap", "prueba"),
    ("hueco pre-FOMC",        "GDAXI",   "fomc",    "gap", "prueba"),
    ("diferencial QQQ-SPY",   "QQQ-SPY", "fomc",    "gap", "prueba"),
    ("primer dia del mes",    "NDX",     "dia1",    "gap", "prueba"),
    ("ventana cierre de mes", "NDX",     "tom",     "cc",  "prueba"),
    ("hueco del lunes",       "NDX",     "lunes",   "gap", "prueba"),
    ("dia de vencimiento",    "NDX",     "venc",    "cc",  "prueba"),
    ("semana vencimiento",    "NDX",     "semvenc", "cc",  "prueba"),
    ("vencim. trimestral",    "NDX",     "trim",    "cc",  "prueba"),
    ("hueco pre-empleo",      "NDX",     "empleo",  "gap", "prueba"),
    ("hueco pre-IPC",         "NDX",     "ipc",     "gap", "prueba"),
    ("prima nocturna total",  "NDX",     "todos",   "gap", "prueba"),
    ("prima intradia",        "NDX",     "todos",   "oc",  "prueba"),
    ("CONTROL oro pre-FOMC",  "GCF",     "fomc",    "gap", "control"),
    ("CONTROL EURUSD preFOMC","EURUSD",  "fomc",    "gap", "control"),
]

print()
print(f"{'hipotesis':<24}{'instr':<9}{'2012-2018':>20}{'2019-2026':>20}"
      f"{'veredicto':>15}")
print(f"{'':<33}{'n':>5}{'dif':>7}{'t':>8}{'n':>5}{'dif':>7}{'t':>8}")
print("-" * 92)

sobreviven = []
for nom, tk, campo, col, tipo in HIP:
    df = D[tk]
    r1 = t_en(df, campo, col, *H1)
    r2 = t_en(df, campo, col, *H2)
    if not r1 or not r2:
        print(f"{nom:<24}{tk:<9}{'sin datos suficientes':>40}")
        continue
    ok = (abs(r1[2]) > 1.96 and abs(r2[2]) > 1.96
          and np.sign(r1[1]) == np.sign(r2[1])
          and abs(r1[2]) > tc1 * 0.75 and abs(r2[2]) > tc2 * 0.75)
    ver = "PASA" if ok else "no"
    if tipo == "control":
        ver = "control OK" if not ok else "CONTROL DISPARA"
    elif ok:
        sobreviven.append((nom, tk, campo, col))
    print(f"{nom:<24}{tk:<9}{r1[0]:>5}{r1[1]:>7.1f}{r1[2]:>8.2f}"
          f"{r2[0]:>5}{r2[1]:>7.1f}{r2[2]:>8.2f}{ver:>15}")

print()
print("=" * 92)
print("RESULTADO DE LA HIPOTESIS DE REGIMEN")
print("=" * 92)
print("  Criterio: |t|>1,96 en LAS DOS mitades, mismo signo, y por encima del")
print("  75%% del techo de ruido de cada ventana.")
print()
if sobreviven:
    print("  SOBREVIVEN %d hipotesis:" % len(sobreviven))
    for nom, tk, campo, col in sobreviven:
        r = t_en(D[tk], campo, col, 2012, 2026)
        print("     %-24s %-9s regimen completo: %+.1f bp · t=%.2f"
              % (nom, tk, r[1], r[2]))
else:
    print("  NINGUNA sobrevive.")
print()
print("  Comparacion: en la muestra completa 2000-2026 pasaban 2 de 18.")
