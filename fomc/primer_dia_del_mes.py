#!/usr/bin/env python3
"""
EL PRIMER DIA DEL MES, descompuesto.

Dos cosas que arreglar del test anterior:

  1. CONTROL INVALIDO. El oro no sirve como control negativo para un efecto de
     FLUJOS, porque las aportaciones mensuales a planes tambien compran oro.
     Se anade EUR/USD: un cruce de divisas no es objeto de aportacion mensual
     sistematica, asi que si el efecto aparece ahi es artefacto de calendario.

  2. LA DESCOMPOSICION QUE DECIDE SI SIRVE. El +16 bp de cierre a cierre del
     dia +1 se queda en +2 bp en el tramo intradia. Si el efecto vive en el
     HUECO NOCTURNO (cierre del ultimo dia del mes -> apertura del primero),
     entonces es INUTILIZABLE en una cuenta prop de futuros, que obliga a
     estar plano al cierre.

        r_total = (1 + r_hueco) x (1 + r_intradia) - 1

Presupuesto de pruebas: el dia +1 es 1 de los 4 dias de la ventana ya
declarada, asi que Bonferroni x4 -> hace falta |t| > 2,50.
"""
import os
import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

DIRY = "../nas100-data/yahoo"
BONF_T = 2.50

# control de flujos: un cruce de divisas
if not os.path.exists("%s/EURUSD.csv" % DIRY):
    d = yf.download("EURUSD=X", start="2003-12-01", progress=False,
                    auto_adjust=False)
    if isinstance(d.columns, pd.MultiIndex):
        d.columns = d.columns.get_level_values(0)
    d.to_csv("%s/EURUSD.csv" % DIRY)
    print("descargado EUR/USD: %d sesiones" % len(d))

INSTR = [
    ("NDX",    "NASDAQ 100",     "accion"),
    ("GSPC",   "S&P 500",        "accion"),
    ("GDAXI",  "DAX",            "accion"),
    ("N225",   "Nikkei 225",     "accion"),
    ("GCF",    "Oro",            "control flujo-sensible"),
    ("EURUSD", "EUR/USD",        "CONTROL de calendario"),
]


def cargar(tk):
    df = pd.read_csv("%s/%s.csv" % (DIRY, tk), index_col=0, parse_dates=True)
    df = df[["Open", "Close"]].dropna()
    df = df[(df > 0).all(axis=1)]
    prev = df["Close"].shift(1)
    df["r_hueco"] = df["Open"] / prev - 1.0
    df["r_intra"] = df["Close"] / df["Open"] - 1.0
    df["r_total"] = df["Close"] / prev - 1.0
    df = df.dropna()
    df = df[(df["r_total"].abs() < 0.15)]
    g = df.groupby([df.index.year, df.index.month])
    df["pos_ini"] = g.cumcount() + 1
    df["dia1"] = df["pos_ini"] == 1
    # fiabilidad de la apertura (control de calidad previo)
    df["open_mala"] = (np.abs(df["Open"] / df["Close"].shift(1) - 1) < 1e-9)
    return df


print("=" * 90)
print("DESCOMPOSICION DEL PRIMER DIA DEL MES")
print("cierre(ultimo dia del mes) -> apertura -> cierre(primer dia)")
print("=" * 90)
print(f"{'instrumento':<14}{'tipo':<24}{'n':>5}"
      f"{'HUECO':>16}{'INTRADIA':>16}{'TOTAL':>14}")
print(f"{'':<38}{'':>5}{'bp      t':>16}{'bp      t':>16}{'bp     t':>14}")
print("-" * 90)

res = {}
for tk, nom, tipo in INSTR:
    df = cargar(tk)
    frac_mala = df["open_mala"].mean()
    sub = df
    nota = ""
    if frac_mala > 0.05:
        sub = df[df.index.year >= 2016]
        nota = " [solo 2016+, apertura no fiable antes]"
    fila = ""
    guarda = {}
    for col in ("r_hueco", "r_intra", "r_total"):
        x = sub[col][sub["dia1"]] * 1e4
        y = sub[col][~sub["dia1"]] * 1e4
        t, p = stats.ttest_ind(x, y, equal_var=False)
        d = x.mean() - y.mean()
        guarda[col] = (d, t)
        anchura = 16 if col != "r_total" else 14
        fila += f"{('%+.1f %6.2f' % (d, t)):>{anchura}}"
    res[tk] = guarda
    n = int(sub["dia1"].sum())
    print(f"{nom:<14}{tipo:<24}{n:>5}{fila}{nota}")

print()
print("Bonferroni x4 (el dia +1 es 1 de los 4 dias de la ventana): |t| > 2,50")

# ------------------------------------------------------------- reparto
print()
print("=" * 90)
print("¿DONDE VIVE EL EFECTO? reparto entre hueco nocturno e intradia")
print("=" * 90)
print(f"{'instrumento':<16}{'hueco':>10}{'intradia':>11}{'total':>10}"
      f"{'% en el hueco':>16}")
print("-" * 90)
for tk, nom, tipo in INSTR:
    h, _ = res[tk]["r_hueco"]
    i, _ = res[tk]["r_intra"]
    t_, _ = res[tk]["r_total"]
    pct = 100.0 * h / t_ if abs(t_) > 1e-9 else np.nan
    print(f"{nom:<16}{h:>10.1f}{i:>11.1f}{t_:>10.1f}{pct:>15.0f}%")

# ------------------------------------------------------------- veredicto
print()
print("=" * 90)
print("VEREDICTO")
print("=" * 90)
acc = [tk for tk, _, tp in INSTR if tp == "accion"]
sig_tot = sum(1 for tk in acc if abs(res[tk]["r_total"][1]) > BONF_T)
sig_int = sum(1 for tk in acc if abs(res[tk]["r_intra"][1]) > BONF_T)
print("  indices de renta variable con |t| > 2,50:")
print("     cierre->cierre : %d de %d" % (sig_tot, len(acc)))
print("     INTRADIA       : %d de %d   <- el unico usable en prop de futuros"
      % (sig_int, len(acc)))
print()
eur = res["EURUSD"]["r_total"]
print("  CONTROL de calendario (EUR/USD): %+.1f bp, t=%.2f -> %s"
      % (eur[0], eur[1], "falla, BIEN" if abs(eur[1]) < 2.0
         else "TAMBIEN dispara: es efecto de calendario, no de flujo"))
oro = res["GCF"]["r_total"]
print("  Oro (flujo-sensible, no es control limpio): %+.1f bp, t=%.2f"
      % (oro[0], oro[1]))
print()
med_h = np.mean([res[tk]["r_hueco"][0] for tk in acc])
med_i = np.mean([res[tk]["r_intra"][0] for tk in acc])
print("  Media sobre los 4 indices: hueco %+.1f bp · intradia %+.1f bp" %
      (med_h, med_i))
if med_h > 2 * abs(med_i):
    print("  -> El efecto vive en el HUECO NOCTURNO. Una cuenta prop de futuros")
    print("     obliga a estar plano al cierre, asi que NO se puede capturar.")
