#!/usr/bin/env python3
"""
¿EL EFECTO NOCTURNO ES REAL O UN ARTEFACTO?

Dos sospechas del resultado anterior:

  (1) El tramo intradia sale ~0 en varios indices, cuando mi medicion previa
      sobre el CFD daba 0,51. El camino C depende del intradia, asi que hay
      que saber cual de las dos mediciones vale.

  (2) El ORO, que era el control negativo, tiene el Sharpe nocturno MAS ALTO
      (+1,12). Si el efecto fuese una prima de riesgo de renta variable no
      deberia aparecer ahi. Sospecha: sesgo sistematico del precio de cierre
      (si el cierre se imprime bajo, el nocturno se infla y el intradia se
      deprime, a la vez y en todos los instrumentos).

Tres pruebas:
  A. Estabilidad por epoca: ¿existe el intradia 0,51 en algun subperiodo?
  B. Coste de ejecucion: el nocturno exige 2 transacciones AL DIA. ¿Sobrevive?
     Esta es la prueba decisiva: un efecto que no paga sus costes no existe
     a efectos practicos.
  C. La cuna cierre/apertura: si es artefacto, la suma de los dos tramos debe
     ser estable mientras el reparto entre ellos no lo es.
"""
import os
import numpy as np
import pandas as pd

DIR = "yahoo"
USABLES = {
    "NDX":   ("NASDAQ 100",   "EEUU"),
    "GSPC":  ("S&P 500",      "EEUU"),
    "DJI":   ("Dow 30",       "EEUU"),
    "RUT":   ("Russell 2000", "EEUU"),
    "GDAXI": ("DAX",          "EUROPA"),
    "N225":  ("Nikkei 225",   "ASIA"),
    "GCF":   ("Oro futuro",   "CONTROL"),
}
DESDE = {"GSPC": 2016, "RUT": 2011}      # tramos limpios del control de calidad


def legs(tk):
    df = pd.read_csv(os.path.join(DIR, "%s.csv" % tk),
                     index_col=0, parse_dates=True)
    df = df[["Open", "Close"]].dropna()
    df = df[(df > 0).all(axis=1)]
    if tk in DESDE:
        df = df[df.index.year >= DESDE[tk]]
    prev = df["Close"].shift(1)
    n = df["Open"] / prev - 1.0
    i = df["Close"] / df["Open"] - 1.0
    ok = n.notna() & i.notna() & (n.abs() < 0.15) & (i.abs() < 0.15)
    return n[ok], i[ok]


def sh(r):
    if len(r) < 250 or r.std() == 0:
        return np.nan
    return r.mean() / r.std() * np.sqrt(252)


# ================================================== A. estabilidad por epoca
print("=" * 86)
print("A. ESTABILIDAD POR EPOCA  (Sharpe nocturno / Sharpe intradia)")
print("=" * 86)
TR = [(2000, 2007), (2008, 2012), (2013, 2017), (2018, 2021), (2022, 2026)]
print(f"{'indice':<15}" + "".join(f"{'%d-%d' % t:>15}" for t in TR))
print("-" * 86)
for tk, (nom, _) in USABLES.items():
    n, i = legs(tk)
    fila = ""
    for a, b in TR:
        m = (n.index.year >= a) & (n.index.year <= b)
        if m.sum() < 200:
            fila += f"{'n/d':>15}"
        else:
            fila += f"{('%+.2f / %+.2f' % (sh(n[m]), sh(i[m]))):>15}"
    print(f"{nom:<15}{fila}")
print()
print("Lectura: el nocturno es positivo en casi todos los tramos. El intradia")
print("cambia de signo entre epocas -> no es una base sobre la que construir.")

# ================================================== B. coste de ejecucion
print()
print("=" * 86)
print("B. PRUEBA DECISIVA: ¿PAGA SUS COSTES?")
print("=" * 86)
print("El nocturno necesita comprar al cierre y vender a la apertura:")
print("2 transacciones x 252 dias = 504 al ano. El intradia, lo mismo.")
print()
print(f"{'indice':<15}{'media NOCT':>13}{'media INTRA':>13}"
      f"{'coste que anula NOCT':>22}{'... INTRA':>12}")
print("-" * 86)
for tk, (nom, _) in USABLES.items():
    n, i = legs(tk)
    # bp por sesion; el coste de ida y vuelta se resta una vez por sesion
    mn, mi = n.mean() * 1e4, i.mean() * 1e4
    print(f"{nom:<15}{mn:>12.2f}{mi:>13.2f}{mn:>21.2f}{mi:>12.2f}")
print()
print("Esa penultima columna es el coste de ida y vuelta, EN BP, que lleva el")
print("tramo a cero. Referencias reales para indices:")
print("   futuro E-mini NQ  ~0,5-1,0 bp ida y vuelta (comision + medio tick)")
print("   CFD de indice     ~2-5 bp   (spread de 0,8-2 puntos sobre 24.000)")
print("   y en la APERTURA y el CIERRE el spread es el MAS ANCHO del dia,")
print("   que es exactamente cuando el nocturno obliga a operar.")

# ================================================== C. la cuna
print()
print("=" * 86)
print("C. ¿ES UNA CUNA DE CONSTRUCCION DEL DATO?")
print("Si lo fuera, la SUMA de los dos tramos seria estable y solo el REPARTO")
print("entre ellos variaria. Se compara el Sharpe del total contra los tramos.")
print("=" * 86)
print(f"{'indice':<15}{'Sh NOCT':>10}{'Sh INTRA':>10}{'Sh TOTAL':>10}"
      f"{'noct+intra en bp':>18}{'total en bp':>13}")
print("-" * 86)
for tk, (nom, _) in USABLES.items():
    n, i = legs(tk)
    tot = (1 + n) * (1 + i) - 1
    print(f"{nom:<15}{sh(n):>10.2f}{sh(i):>10.2f}{sh(tot):>10.2f}"
          f"{(n.mean() + i.mean()) * 1e4:>17.2f}{tot.mean() * 1e4:>13.2f}")
print()
print("Si el Sharpe TOTAL es mucho menor que el del tramo nocturno, es que el")
print("nocturno esta 'prestado' del intradia: el mismo retorno reordenado, con")
print("menos varianza aparente porque cada tramo ve solo parte del ruido.")
print("Ese es el patron de una cuna de construccion, no de dos efectos.")
