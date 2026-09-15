#!/usr/bin/env python3
"""
ESTRATEGIA #2 · candidata: VENCIMIENTOS DE OPCIONES Y FUTUROS SOBRE INDICES

Misma receta que produjo el unico resultado positivo del proyecto:
hipotesis pre-registrada, controles negativos, dos instrumentos, subperiodos,
correccion multiple.

DECLARADO ANTES DE MIRAR:
  H1  dia de vencimiento mensual   = tercer viernes del mes
  H2  semana de vencimiento        = 5 sesiones que terminan en ese viernes
  H3  vencimiento trimestral       = tercer viernes de marzo, junio, sep, dic
                                     ("triple witching", flujo mayor)
  Bonferroni x3 -> |t| > 2,39

Metrica primaria: retorno cierre->cierre. La descomposicion en hueco nocturno
e intradia se mira SOLO en lo que pase el primario (para no inflar el
presupuesto de pruebas).

CONTROLES:
  Nikkei  : sus opciones vencen el SEGUNDO viernes, no el tercero. Si el
            efecto es de vencimiento, el Nikkei debe FALLAR en el tercero y
            aparecer en el segundo. Es el control mas informativo del diseño.
  EUR/USD : no tiene complejo de opciones sobre indice ligado a esa fecha.

Se usa el indice de CONTADO, no el CFD: el CFD puede rodar contratos y
produciria un artefacto justo en las fechas de vencimiento.
"""
import numpy as np
import pandas as pd
from scipy import stats

DIRY = "../nas100-data/yahoo"
BONF = 2.39

INSTR = [
    ("NDX",    "NASDAQ 100",  None, "prueba"),
    ("GSPC",   "S&P 500",     None, "prueba"),
    ("GDAXI",  "DAX",         None, "prueba"),
    ("N225",   "Nikkei 225",  None, "CONTROL 3er viernes"),
    ("EURUSD", "EUR/USD",     None, "CONTROL calendario"),
]


def cargar(tk):
    df = pd.read_csv("%s/%s.csv" % (DIRY, tk), index_col=0, parse_dates=True)
    df = df[["Open", "Close"]].dropna()
    df = df[(df > 0).all(axis=1)]
    prev = df["Close"].shift(1)
    df["r_cc"] = (df["Close"] / prev - 1.0) * 1e4
    df["r_gap"] = (df["Open"] / prev - 1.0) * 1e4
    df["r_oc"] = (df["Close"] / df["Open"] - 1.0) * 1e4
    df = df.dropna()
    df = df[df["r_cc"].abs() < 1500]

    # ---- tercer y segundo viernes de cada mes -----------------------
    idx = df.index
    vie = idx[idx.dayofweek == 4]
    porm = pd.Series(vie).groupby([vie.year, vie.month])
    tercer, segundo = set(), set()
    for _, g in porm:
        g = sorted(g)
        if len(g) >= 2:
            segundo.add(g[1])
        if len(g) >= 3:
            tercer.add(g[2])
    # si el tercer viernes no cotiza, el vencimiento pasa al dia anterior
    df["venc3"] = idx.isin(tercer)
    df["venc2"] = idx.isin(segundo)
    df["trim"] = df["venc3"] & idx.month.isin([3, 6, 9, 12])

    # ---- semana de vencimiento: 5 sesiones que acaban en el 3er viernes
    sem = np.zeros(len(df), dtype=bool)
    pos = np.where(df["venc3"].values)[0]
    for p in pos:
        sem[max(0, p - 4):p + 1] = True
    df["semana"] = sem
    return df


TRAMOS = [("2000-2011", 2000, 2011), ("2012-2019", 2012, 2019),
          ("2020-2026", 2020, 2026), ("TODO", 2000, 2026)]


def prueba(df, mask, col="r_cc", a=None, b=None):
    m = pd.Series(True, index=df.index)
    if a:
        m &= (df.index.year >= a) & (df.index.year <= b)
    x, y = df[col][m & mask], df[col][m & ~mask]
    if len(x) < 15:
        return None
    t, p = stats.ttest_ind(x, y, equal_var=False)
    return dict(n=len(x), mx=x.mean(), my=y.mean(),
                dif=x.mean() - y.mean(), t=t, p=p)


DATOS = {tk: cargar(tk) for tk, _, _, _ in INSTR}

for hnom, campo in [("H1 · DIA DE VENCIMIENTO MENSUAL (3er viernes)", "venc3"),
                    ("H2 · SEMANA DE VENCIMIENTO (5 sesiones)", "semana"),
                    ("H3 · VENCIMIENTO TRIMESTRAL (triple witching)", "trim")]:
    print("=" * 90)
    print(hnom + "   ·   metrica: cierre -> cierre")
    print("=" * 90)
    print(f"{'instrumento':<14}{'tipo':<22}{'tramo':<11}{'n':>5}"
          f"{'evento':>9}{'resto':>8}{'dif':>8}{'t':>7}{'p':>8}")
    print("-" * 90)
    for tk, nom, _, tipo in INSTR:
        df = DATOS[tk]
        for tetq, a, b in TRAMOS:
            r = prueba(df, df[campo], "r_cc", a, b)
            if not r:
                continue
            marca = " *" if abs(r["t"]) > BONF else ""
            primero = tetq == "2000-2011"
            print(f"{nom if primero else '':<14}{tipo if primero else '':<22}"
                  f"{tetq:<11}{r['n']:>5}{r['mx']:>9.1f}{r['my']:>8.1f}"
                  f"{r['dif']:>8.1f}{r['t']:>7.2f}{r['p']:>8.3f}{marca}")
        print()

# ------------------------------------------- control clave: 2o vs 3er viernes
print("=" * 90)
print("CONTROL CLAVE · ¿el efecto sigue al VENCIMIENTO o al CALENDARIO?")
print("Las opciones del Nikkei vencen el 2o viernes; las de EE.UU. y DAX el 3o")
print("=" * 90)
print(f"{'instrumento':<14}{'2o viernes':>22}{'3er viernes':>22}")
print(f"{'':<14}{'dif':>12}{'t':>10}{'dif':>12}{'t':>10}")
print("-" * 90)
for tk, nom, _, tipo in INSTR:
    df = DATOS[tk]
    r2 = prueba(df, df["venc2"])
    r3 = prueba(df, df["venc3"])
    print(f"{nom:<14}{r2['dif']:>12.1f}{r2['t']:>10.2f}"
          f"{r3['dif']:>12.1f}{r3['t']:>10.2f}")
print()
print("Lo que confirmaria el mecanismo: EE.UU. y DAX fuertes en el 3er viernes")
print("y planos en el 2o; Nikkei al contrario.")

# ------------------------------------------- veredicto
print()
print("=" * 90)
print("VEREDICTO")
print("=" * 90)
pruebas = [tk for tk, _, _, tp in INSTR if tp == "prueba"]
for hnom, campo in [("H1 dia venc.", "venc3"), ("H2 semana", "semana"),
                    ("H3 trimestral", "trim")]:
    pos = sig = 0
    for tk in pruebas:
        r = prueba(DATOS[tk], DATOS[tk][campo])
        pos += r["dif"] > 0
        sig += abs(r["t"]) > BONF
    print("  %-16s dif>0 en %d/%d · |t|>2,39 en %d/%d"
          % (hnom, pos, len(pruebas), sig, len(pruebas)))
print()
for tk in ("N225", "EURUSD"):
    r = prueba(DATOS[tk], DATOS[tk]["venc3"])
    nom = dict((a, b) for a, b, _, _ in INSTR)[tk]
    print("  CONTROL %-12s 3er viernes: %+.1f bp · t=%.2f -> %s"
          % (nom, r["dif"], r["t"], "falla" if abs(r["t"]) < 2.0 else "DISPARA"))
