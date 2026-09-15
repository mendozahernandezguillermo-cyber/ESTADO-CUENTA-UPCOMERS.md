#!/usr/bin/env python3
"""
LA NOCHE DEL LUNES AL MARTES — prueba con disciplina.

Hallazgo bruto: es la mejor noche en 6 de 6 indices de renta variable, y el
control (oro) NO lo muestra. Magnitud 2-7 bp, frente a 1,25 bp de financiacion
por una sola noche.

Pero acabo de SELECCIONAR sobre 5 cubos de dia de la semana, asi que:

  - Presupuesto de pruebas: 5 hipotesis (una por noche). Bonferroni: para
    alpha=0,05 hace falta p < 0,01, o |t| > 2,58.
  - La consistencia entre instrumentos es CONFIRMACION, no busqueda: los
    6 indices no multiplican el presupuesto.
  - Los 4 de EE.UU. no son 4 pruebas: bloques EEUU / EUROPA / ASIA.
  - Prueba fuera de muestra por EPOCA: el efecto debe estar en las dos
    mitades, no solo en una.
  - El control (oro) tiene que SEGUIR fallando.
  - Y todo neto de costes, no bruto.
"""
import os
import numpy as np
import pandas as pd
from scipy import stats

DIR = "yahoo"
BP_NOCHE = 0.0456 / 365.0 * 1e4          # 1,249 bp de financiacion por noche

INSTR = {
    "NDX":   ("NASDAQ 100",   "EEUU",    None),
    "GSPC":  ("S&P 500",      "EEUU",    2016),
    "DJI":   ("Dow 30",       "EEUU",    None),
    "RUT":   ("Russell 2000", "EEUU",    2011),
    "GDAXI": ("DAX",          "EUROPA",  None),
    "N225":  ("Nikkei 225",   "ASIA",    None),
    "GCF":   ("Oro CONTROL",  "CONTROL", None),
}
NOCHES = {0: "lun->mar", 1: "mar->mie", 2: "mie->jue", 3: "jue->vie",
          4: "vie->lun"}


def cargar(tk, desde):
    df = pd.read_csv(os.path.join(DIR, "%s.csv" % tk),
                     index_col=0, parse_dates=True)
    df = df[["Open", "Close"]].dropna()
    df = df[(df > 0).all(axis=1)]
    if desde:
        df = df[df.index.year >= desde]
    d = pd.DataFrame(index=df.index)
    d["bruto"] = (df["Open"] / df["Close"].shift(1) - 1.0) * 1e4
    d["noches"] = df.index.to_series().diff().dt.days
    d = d.dropna()
    d = d[(d["bruto"].abs() < 1500) & (d["noches"] >= 1) & (d["noches"] <= 5)]
    # cubo = dia de la semana en que se ABRIO la posicion (cierre anterior)
    idx = d.index
    prev = pd.Series(idx, index=idx).shift(1)
    d["dow_abre"] = pd.Series(idx, index=idx).shift(1).dt.dayofweek
    d = d.dropna(subset=["dow_abre"])
    d["dow_abre"] = d["dow_abre"].astype(int)
    return d


def neto(d, spread_ida):
    return d["bruto"] - d["noches"] * BP_NOCHE - 2 * spread_ida


# ============================================ 1. las 5 noches, neto, con t
SP = 1.50          # spread de ida realista en apertura/cierre de CFD
print("=" * 90)
print("1. LAS CINCO NOCHES, NETAS DE COSTES  (spread de ida %.2f bp)" % SP)
print("   valor = bp netos por operacion, y (t) del contraste contra cero")
print("=" * 90)
print(f"{'indice':<15}" + "".join(f"{NOCHES[i]:>15}" for i in range(5)))
print("-" * 90)
tabla = {}
for tk, (nom, blq, desde) in INSTR.items():
    d = cargar(tk, desde)
    d["neto"] = neto(d, SP)
    fila, guarda = "", {}
    for i in range(5):
        x = d["neto"][d["dow_abre"] == i]
        if len(x) < 80:
            fila += f"{'n/d':>15}"
            continue
        t = stats.ttest_1samp(x, 0).statistic
        guarda[i] = (x.mean(), t, len(x))
        fila += f"{('%+.2f (%.2f)' % (x.mean(), t)):>15}"
    tabla[tk] = guarda
    print(f"{nom:<15}{fila}")
print()
print("Bonferroni con 5 hipotesis: hace falto |t| > 2,58 para alpha=0,05.")

# ============================================ 2. recuento por bloque
print()
print("=" * 90)
print("2. ¿SE SOSTIENE LA NOCHE DEL LUNES POR BLOQUES INDEPENDIENTES?")
print("=" * 90)
print(f"{'indice':<15}{'bloque':<9}{'n':>6}{'neto lun':>11}{'t':>8}"
      f"{'Sharpe anual':>14}{'signif.':>10}")
print("-" * 90)
for tk, (nom, blq, desde) in INSTR.items():
    if tk not in tabla or 0 not in tabla[tk]:
        continue
    d = cargar(tk, desde)
    d["neto"] = neto(d, SP)
    x = d["neto"][d["dow_abre"] == 0]
    anos = (d.index.max() - d.index.min()).days / 365.25
    n_ano = len(x) / anos
    sh = x.mean() / x.std() * np.sqrt(n_ano) if x.std() > 0 else np.nan
    t = stats.ttest_1samp(x, 0).statistic
    print(f"{nom:<15}{blq:<9}{len(x):>6}{x.mean():>11.2f}{t:>8.2f}"
          f"{sh:>14.2f}{('SI' if abs(t) > 2.58 else 'no'):>10}")

# ============================================ 3. fuera de muestra por epoca
print()
print("=" * 90)
print("3. PRUEBA FUERA DE MUESTRA: LAS DOS MITADES DEL HISTORIAL")
print("   (la noche del lunes, neta. Debe estar en AMBAS.)")
print("=" * 90)
print(f"{'indice':<15}{'1a mitad':>24}{'2a mitad':>24}{'coherente':>12}")
print(f"{'':<15}{'periodo':>13}{'neto':>7}{'t':>4}"
      f"{'periodo':>13}{'neto':>7}{'t':>4}")
print("-" * 90)
coh = 0
tot = 0
for tk, (nom, blq, desde) in INSTR.items():
    d = cargar(tk, desde)
    d["neto"] = neto(d, SP)
    x = d[d["dow_abre"] == 0]
    if len(x) < 200:
        continue
    corte = x.index[len(x) // 2]
    a, b = x[x.index < corte]["neto"], x[x.index >= corte]["neto"]
    ta = stats.ttest_1samp(a, 0).statistic
    tb = stats.ttest_1samp(b, 0).statistic
    ok = (a.mean() > 0) and (b.mean() > 0)
    if blq != "CONTROL":
        tot += 1
        coh += ok
    print(f"{nom:<15}"
          f"{('%d-%d' % (a.index.year.min(), a.index.year.max())):>13}"
          f"{a.mean():>7.2f}{ta:>4.1f}"
          f"{('%d-%d' % (b.index.year.min(), b.index.year.max())):>13}"
          f"{b.mean():>7.2f}{tb:>4.1f}"
          f"{('SI' if ok else 'NO'):>12}")

# ============================================ 4. veredicto
print()
print("=" * 90)
print("4. VEREDICTO")
print("=" * 90)
print("  coherente en las dos mitades: %d de %d indices (sin el control)"
      % (coh, tot))
if "GCF" in tabla and 0 in tabla["GCF"]:
    m, t, n = tabla["GCF"][0]
    print("  CONTROL (oro), noche del lunes: %+.2f bp, t=%.2f -> %s"
          % (m, t, "sigue fallando, BIEN" if abs(t) < 2.0
             else "TAMBIEN dispara: sospechoso"))
print()
print("  Sensibilidad al spread — noche del lunes, NASDAQ:")
d = cargar("NDX", None)
for sp in (0.30, 0.75, 1.50, 2.50, 3.50):
    x = (d["bruto"] - d["noches"] * BP_NOCHE - 2 * sp)[d["dow_abre"] == 0]
    anos = (d.index.max() - d.index.min()).days / 365.25
    sh = x.mean() / x.std() * np.sqrt(len(x) / anos)
    print("     spread ida %.2f bp -> neto %+.2f bp · Sharpe %+.2f"
          % (sp, x.mean(), sh))
