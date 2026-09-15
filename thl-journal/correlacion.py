#!/usr/bin/env python3
"""
MATRIZ DE CORRELACION ENTRE DARWINS  (+ validacion del metodo)

El campo c2 del journal es el retorno acumulado (%). De ahi se saca una serie
de retornos diarios por darwin y se correlacionan entre si.

Este script hace cuatro cosas:

  1. VALIDA el metodo sobre series sinteticas de rho conocido, incluyendo el
     efecto de que los darwins no operan todos los dias (huecos).
  2. Mide la beta de THL contra el NASDAQ con datos propios, y cruza el
     resultado contra el 0,125 que publica Darwinex en su pestana de
     correlacion.
  3. Calcula el MULTIPLICADOR DE SHARPE de la cartera a partir de la matriz,
     que es el numero que alimenta la tabla de beneficio mensual.
  4. Queda listo para N darwins: basta anadir sus accountName a DARWINS.

Para anadir un darwin hace falta su accountName (D.xxxxxx), que se obtiene
en DevTools -> Network sobre la pestana "Estrategia subyacente".
"""
import json
import os
import numpy as np
import pandas as pd

DARWINS = {
    "THL": "D.259985",          # joxemi — el unico que tenemos
}

NAS_DIARIO = "/projects/sandbox/nas100-data/diario.csv"


# ------------------------------------------------------------ series
def serie_desde_journal(path):
    """Journal -> retornos diarios (log) desde el retorno acumulado c2."""
    with open(path) as f:
        raw = json.load(f)
    df = pd.DataFrame(raw, columns=["c%d" % i for i in range(11)])
    df["ts"] = pd.to_datetime(df["c1"], unit="ms", utc=True)
    df = df.sort_values("ts")
    # c2 es retorno acumulado en %: la equity es 1 + c2/100
    df["eq"] = 1.0 + pd.to_numeric(df["c2"], errors="coerce") / 100.0
    df = df[df["eq"] > 0]
    # ultimo valor de cada dia natural
    d = df.set_index("ts")["eq"].resample("1D").last().dropna()
    return np.log(d).diff().dropna()


def matriz(series, nombres, min_solape=60):
    k = len(series)
    M = np.full((k, k), np.nan)
    N = np.zeros((k, k), dtype=int)
    for i in range(k):
        for j in range(k):
            a, b = series[i].align(series[j], join="inner")
            # solo dias en que AL MENOS UNO opera (evita inflar con ceros)
            act = (a != 0) | (b != 0)
            a, b = a[act], b[act]
            N[i, j] = len(a)
            if len(a) >= min_solape and a.std() > 0 and b.std() > 0:
                M[i, j] = np.corrcoef(a, b)[0, 1]
    return pd.DataFrame(M, index=nombres, columns=nombres), N


def imprimir(M, N, titulo):
    print("\n%s" % titulo)
    print("    " + "".join("%9s" % c[:8] for c in M.columns))
    for i, r in enumerate(M.index):
        fila = "".join("      n/d" if np.isnan(v) else "%9.3f" % v
                       for v in M.iloc[i])
        print("%-4s%s" % (r[:4], fila))
    print("  (solape minimo en la matriz: %d dias)"
          % N[N > 0].min() if (N > 0).any() else "")


def mult_sharpe(M):
    """Multiplicador de Sharpe de la cartera equiponderada."""
    C = M.values.copy()
    if np.isnan(C).any():
        return np.nan
    n = len(C)
    w = np.ones(n) / n
    var = w @ C @ w
    return float((w.sum() / n) / np.sqrt(var)) if var > 0 else np.nan


# ============================================================ 1. VALIDACION
print("=" * 74)
print("1. VALIDACION DEL METODO sobre series sinteticas de rho CONOCIDO")
print("=" * 74)
rng = np.random.default_rng(7)
T = 900
print(f"{'rho real':>10}{'rho medido':>13}{'sin huecos':>13}"
      f"{'con 60% huecos':>17}")
print("-" * 74)
for rho in (0.0, 0.3, 0.6, 0.9, 0.95):
    zc = rng.standard_normal(T)
    a = np.sqrt(rho) * zc + np.sqrt(1 - rho) * rng.standard_normal(T)
    b = np.sqrt(rho) * zc + np.sqrt(1 - rho) * rng.standard_normal(T)
    lleno = np.corrcoef(a, b)[0, 1]
    # con huecos: 60% de los dias sin operar (retorno 0)
    ma = rng.random(T) < 0.4
    mb = rng.random(T) < 0.4
    ah, bh = a * ma, b * mb
    act = (ah != 0) | (bh != 0)
    hueco = np.corrcoef(ah[act], bh[act])[0, 1]
    print(f"{rho:>10.2f}{lleno:>13.3f}{lleno:>13.3f}{hueco:>17.3f}")
print()
print("LECTURA: los huecos SESGAN LA CORRELACION HACIA CERO. Dos darwins que")
print("operen en dias distintos pareceran descorrelacionados aunque sigan la")
print("misma idea. Es un sesgo optimista y hay que tenerlo presente.")

# ====================================================== 2. THL vs NASDAQ
print("\n" + "=" * 74)
print("2. THL CONTRA EL NASDAQ  (¿cuanto de THL es solo beta del indice?)")
print("=" * 74)
thl = serie_desde_journal("j1.json")
print("serie de THL: %d dias  ·  %s -> %s"
      % (len(thl), thl.index.min().date(), thl.index.max().date()))
print("  dias con movimiento: %d (%.1f%%)"
      % ((thl != 0).sum(), 100.0 * (thl != 0).mean()))

if os.path.exists(NAS_DIARIO):
    nas = pd.read_csv(NAS_DIARIO)
    col_f = [c for c in nas.columns if "fecha" in c.lower()][0]
    nas[col_f] = pd.to_datetime(nas[col_f], utc=True, errors="coerce")
    nas = nas.dropna(subset=[col_f]).set_index(col_f)
    col_r = "r_total" if "r_total" in nas.columns else nas.columns[-1]
    nser = nas[col_r].astype(float)
    nser = nser.resample("1D").last().dropna()
    if nser.abs().median() > 0.5:      # viene en %, se pasa a fraccion
        nser = nser / 100.0

    a, b = thl.align(nser, join="inner")
    act = a != 0
    a, b = a[act], b[act]
    r = np.corrcoef(a, b)[0, 1]
    beta = np.polyfit(b, a, 1)[0]
    resid = a - beta * b
    print("\n  solape: %d dias operados" % len(a))
    print("  correlacion THL vs NASDAQ diario : %+.3f" % r)
    print("  beta                             : %+.3f" % beta)
    print("  R^2 (fraccion explicada por el indice): %.1f%%" % (100 * r ** 2))
    print("  sd de THL %.4f  ·  sd del residuo %.4f  ->  %.1f%% de la"
          " varianza es propia" % (a.std(), resid.std(),
                                   100.0 * resid.var() / a.var()))
    print("\n  Darwinex publica 0,125 de correlacion en su pestana.")
    print("  Medido aqui: %+.3f  ->  %s" % (r, "coherente"
          if abs(abs(r) - 0.125) < 0.12 else "DISCREPA, revisar"))
else:
    print("  [no encuentro %s]" % NAS_DIARIO)

# ============================================ 3. MATRIZ Y MULTIPLICADOR
print("\n" + "=" * 74)
print("3. MATRIZ DE CORRELACION")
print("=" * 74)
series, nombres = [thl], ["THL"]
for tk, acc in DARWINS.items():
    if tk == "THL":
        continue
    p = "j_%s.json" % tk
    if os.path.exists(p):
        series.append(serie_desde_journal(p))
        nombres.append(tk)

if len(series) == 1:
    print("Solo tengo 1 darwin (THL). La matriz necesita al menos 2.")
    print()
    print("Para completarla necesito el accountName de cada candidato:")
    print("  1. abre la pagina del darwin -> pestana 'Estrategia subyacente'")
    print("  2. DevTools (Ctrl+Shift+I) -> Network -> filtra 'tradingjournal'")
    print("  3. copia el accountName=D.xxxxxx de la URL")
    print()
    print("Con eso descargo cada journal y saco la matriz completa.")
    print()
    print("Mientras tanto, esto es lo que la matriz PRODUCIRA, sobre tres")
    print("escenarios de rho, y el multiplicador de Sharpe de cada uno:")
    print()
    print(f"{'escenario':<34}{'rho medio':>11}{'mult. Sharpe':>14}"
          f"{'$/mes (s=0,75)':>16}")
    print("-" * 74)
    # mult = sqrt(n/(1+(n-1)rho)); $/mes interpolado de beneficio_mensual.py
    ref = {0.0: 1067, 0.3: 805, 0.6: 675, 0.9: 560}
    for etq, rho in [("3 estrategias independientes", 0.0),
                     ("3 estrategias parecidas", 0.3),
                     ("3 variantes del mismo sesgo", 0.6),
                     ("el caso THL/ZJM (mismo trader)", 0.9)]:
        m = np.sqrt(3.0 / (1.0 + 2.0 * rho))
        print(f"{etq:<34}{rho:>11.2f}{m:>14.2f}{ref[rho]:>16,d}")
else:
    M, N = matriz(series, nombres)
    imprimir(M, N, "correlacion de retornos diarios")
    ms = mult_sharpe(M)
    print("\n  multiplicador de Sharpe de la cartera equiponderada: %.2f" % ms)
    for i in range(len(nombres)):
        for j in range(i + 1, len(nombres)):
            v = M.iloc[i, j]
            if not np.isnan(v) and v > 0.85:
                print("  AVISO: %s y %s a rho=%.2f -> probablemente el MISMO"
                      " trader" % (nombres[i], nombres[j], v))
