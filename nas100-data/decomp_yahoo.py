#!/usr/bin/env python3
"""
REPLICACION CRUZADA de la descomposicion intradia / nocturno.

Referencia propia, medida antes en NASDAQ (CFD Dukascopy M1, 3.682 sesiones,
2011-2026):
      nocturno Sharpe 0.71 · intradia 0.51 · rho -0.007

Aqui se repite en varios indices con datos oficiales de contado y periodo mas
largo. El NASDAQ sirve de doble comprobacion: fuente distinta, periodo
distinto. Si no reproduce ~0.71/0.51, el problema esta en mi medicion previa.

Disciplina:
  - UNA hipotesis, varios instrumentos. La correccion multiple va sobre la
    hipotesis, no sobre los instrumentos.
  - Los indices de EE.UU. NO son pruebas independientes entre si: se cuenta
    por BLOQUE (EE.UU. / Europa / Asia).
  - ORO como control negativo: no es renta variable. Si el efecto sale igual
    de fuerte, no es una prima de riesgo de acciones.
  - Se excluyen los indices cuyo Open no es real (control de calidad previo).
"""
import os
import numpy as np
import pandas as pd

DIR = "yahoo"
LIMITE_CALIDAD = 0.05          # max fraccion de Open==PrevClose tolerada

TICKERS = {
    "NDX":   ("NASDAQ 100",   "EEUU"),
    "GSPC":  ("S&P 500",      "EEUU"),
    "DJI":   ("Dow 30",       "EEUU"),
    "RUT":   ("Russell 2000", "EEUU"),
    "GDAXI": ("DAX",          "EUROPA"),
    "FTSE":  ("FTSE 100",     "EUROPA"),
    "N225":  ("Nikkei 225",   "ASIA"),
    "AXJO":  ("ASX 200",      "ASIA"),
    "GCF":   ("Oro futuro",   "CONTROL"),
}


def cargar(tk):
    p = os.path.join(DIR, "%s.csv" % tk)
    if not os.path.exists(p):
        return None
    df = pd.read_csv(p, index_col=0, parse_dates=True)
    df = df[["Open", "High", "Low", "Close"]].dropna()
    return df[(df > 0).all(axis=1)]


def contaminacion(df):
    prev = df["Close"].shift(1)
    return np.abs(df["Open"] / prev - 1.0) < 1e-9


def sharpe(r):
    r = r.dropna()
    if len(r) < 250 or r.std() == 0:
        return np.nan, np.nan
    s = r.mean() / r.std() * np.sqrt(252)
    se = np.sqrt((1 + s * s / 2) / (len(r) / 252.0))
    return s, se


# ============================================ 1. ¿la contaminacion es de epoca?
print("=" * 84)
print("1. ¿ESTA LA CONTAMINACION CONCENTRADA EN ALGUNA EPOCA?")
print("   (fraccion de dias con Open == cierre previo, por tramo)")
print("=" * 84)
TRAMOS = [(2000, 2005), (2006, 2010), (2011, 2015), (2016, 2020), (2021, 2026)]
print(f"{'indice':<15}" + "".join(f"{'%d-%d' % t:>12}" for t in TRAMOS))
print("-" * 84)
recuperables = {}
for tk, (nom, blq) in TICKERS.items():
    df = cargar(tk)
    if df is None:
        continue
    mal = contaminacion(df)
    fila, limpios = "", []
    for a, b in TRAMOS:
        m = (df.index.year >= a) & (df.index.year <= b)
        f = mal[m].mean() if m.sum() > 50 else np.nan
        fila += f"{f:>11.1%} " if not np.isnan(f) else f"{'n/d':>12}"
        if not np.isnan(f) and f <= LIMITE_CALIDAD:
            limpios.append((a, b))
    print(f"{nom:<15}{fila}")
    if limpios:
        recuperables[tk] = limpios

print()
print("Si un indice esta limpio solo en tramos recientes, se usa ese tramo.")
print("Recortar por EPOCA es legitimo; quitar dias sueltos contaminados NO,")
print("porque esos dias no son una muestra aleatoria.")

# ==================================================== 2. la descomposicion
print()
print("=" * 84)
print("2. DESCOMPOSICION INTRADIA / NOCTURNO")
print("=" * 84)
print(f"{'indice':<15}{'bloque':<9}{'periodo':>12}{'ses':>6}"
      f"{'Sh NOCTURNO':>17}{'Sh INTRADIA':>17}{'rho':>8}")
print("-" * 84)

res = {}
for tk, (nom, blq) in TICKERS.items():
    df = cargar(tk)
    if df is None:
        continue
    mal = contaminacion(df)

    # se elige el tramo continuo mas largo con contaminacion aceptable
    if mal.mean() <= LIMITE_CALIDAD:
        sub = df
    elif tk in recuperables:
        a = min(t[0] for t in recuperables[tk])
        sub = df[df.index.year >= a]
        if contaminacion(sub).mean() > LIMITE_CALIDAD or len(sub) < 500:
            print(f"{nom:<15}{blq:<9}{'DESCARTADO — Open no fiable':>40}")
            continue
    else:
        print(f"{nom:<15}{blq:<9}{'DESCARTADO — Open no fiable':>40}")
        continue

    prev = sub["Close"].shift(1)
    r_noct = sub["Open"] / prev - 1.0
    r_intra = sub["Close"] / sub["Open"] - 1.0
    ok = r_noct.notna() & r_intra.notna() & \
         (r_noct.abs() < 0.15) & (r_intra.abs() < 0.15)
    r_noct, r_intra = r_noct[ok], r_intra[ok]

    sn, en = sharpe(r_noct)
    si, ei = sharpe(r_intra)
    rho = r_noct.corr(r_intra)
    per = "%d-%d" % (sub.index.year.min(), sub.index.year.max())
    res[tk] = dict(nom=nom, blq=blq, n=len(r_noct), sn=sn, en=en,
                   si=si, ei=ei, rho=rho, per=per)
    print(f"{nom:<15}{blq:<9}{per:>12}{len(r_noct):>6}"
          f"{('%+.2f ± %.2f' % (sn, en)):>17}"
          f"{('%+.2f ± %.2f' % (si, ei)):>17}{rho:>8.3f}")

# ============================================== 3. recuento por bloque
print()
print("=" * 84)
print("3. RECUENTO POR BLOQUE INDEPENDIENTE")
print("=" * 84)
blq = {}
for r in res.values():
    blq.setdefault(r["blq"], []).append(r)
print(f"{'bloque':<10}{'instr':>7}{'Sh NOCT medio':>16}{'Sh INTRA medio':>17}"
      f"{'rho medio':>11}{'noct>intra':>12}")
print("-" * 84)
for b in ("EEUU", "EUROPA", "ASIA", "CONTROL"):
    if b not in blq:
        continue
    L = blq[b]
    print(f"{b:<10}{len(L):>7}{np.nanmean([x['sn'] for x in L]):>16.2f}"
          f"{np.nanmean([x['si'] for x in L]):>17.2f}"
          f"{np.nanmean([x['rho'] for x in L]):>11.3f}"
          f"{('%d/%d' % (sum(1 for x in L if x['sn'] > x['si']), len(L))):>12}")

# ============================================== 4. veredicto
print()
print("=" * 84)
print("4. VEREDICTO")
print("=" * 84)
reales = [x for x in res.values() if x["blq"] != "CONTROL"]
ctrl = [x for x in res.values() if x["blq"] == "CONTROL"]
if reales:
    print("  referencia propia (NASDAQ CFD M1): noct 0.71 · intra 0.51 · rho -0.007")
    if "NDX" in res:
        r = res["NDX"]
        print("  NASDAQ aqui (Yahoo, 2000-2026): noct %+.2f · intra %+.2f · rho %+.3f"
              % (r["sn"], r["si"], r["rho"]))
        print("     -> %s" % ("reproduce" if abs(r["sn"] - 0.71) < 0.4
                              else "NO reproduce: revisar la medicion previa"))
    print()
    nb = len(set(x["blq"] for x in reales))
    print("  bloques independientes con datos usables: %d" % nb)
    print("  nocturno > 0     en %d de %d indices"
          % (sum(1 for x in reales if x["sn"] > 0), len(reales)))
    print("  nocturno > intra en %d de %d indices"
          % (sum(1 for x in reales if x["sn"] > x["si"]), len(reales)))
    rr = [x["rho"] for x in reales if not np.isnan(x["rho"])]
    print("  rho intradia-nocturno: media %+.3f · max |rho| %.3f"
          % (np.mean(rr), np.max(np.abs(rr))))
if ctrl:
    c = ctrl[0]
    print()
    print("  CONTROL (oro): noct %+.2f ± %.2f · intra %+.2f ± %.2f"
          % (c["sn"], c["en"], c["si"], c["ei"]))
    print("     -> si el nocturno del oro es igual de fuerte que el de los")
    print("        indices, el efecto NO es una prima de renta variable.")
