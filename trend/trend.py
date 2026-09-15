#!/usr/bin/env python3
"""
ESTRATEGIA #2 · candidata: MOMENTUM DE SERIES TEMPORALES MULTI-ACTIVO

Por que este dominio: es el efecto sistematico mejor documentado que existe
(Moskowitz, Ooi y Pedersen 2012, y toda la industria de managed futures), es
CONTINUO en vez de 8 eventos al año, y funciona en clases de activo distintas,
asi que seria ortogonal a la prima pre-FOMC.

ESPECIFICACION DECLARADA ANTES DE MIRAR (la canonica de MOP, sin variantes):
   señal    : signo del retorno de los ultimos 12 meses
   tenencia : 1 mes, rebalanceo mensual (observaciones NO solapadas)
   tamaño   : escalado a volatilidad objetivo constante, usando la
              desviacion de los retornos diarios de los ultimos 12 meses
   cartera  : equiponderada entre mercados
UNA sola especificacion. No se prueban otros periodos de mirada atras ni otras
tenencias: eso seria la busqueda de parametros que ha hundido todo lo demas.

EXPECTATIVA REGISTRADA DE ANTEMANO: espero que salga DEBILITADO despues de
2010, porque asi lo documentan la literatura y los resultados de la industria.
Si sale con t=4 en la muestra reciente, buscare el error antes de creerlo.

UNIVERSO: 12 mercados en 4 clases de activo. Se usan ETFs de replica fisica y
divisas al contado a proposito: nada de futuros continuos ni de ETFs de
materias primas con decaimiento por rollover, que meterian señales falsas.
"""
import os
import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

DIR = "datos"
os.makedirs(DIR, exist_ok=True)

UNIVERSO = [
    ("SPY",      "S&P 500",        "ACCIONES"),
    ("QQQ",      "Nasdaq 100",     "ACCIONES"),
    ("EFA",      "Desarrollados",  "ACCIONES"),
    ("EEM",      "Emergentes",     "ACCIONES"),
    ("TLT",      "Treasury 20y",   "BONOS"),
    ("IEF",      "Treasury 10y",   "BONOS"),
    ("GLD",      "Oro",            "METALES"),
    ("SLV",      "Plata",          "METALES"),
    ("EURUSD=X", "EUR/USD",        "DIVISAS"),
    ("USDJPY=X", "USD/JPY",        "DIVISAS"),
    ("GBPUSD=X", "GBP/USD",        "DIVISAS"),
    ("AUDUSD=X", "AUD/USD",        "DIVISAS"),
]

VOL_OBJETIVO = 0.10          # 10% anual por mercado antes de agregar
MIRADA = 12                  # meses
MIN_MESES = 36               # historial minimo para entrar en la cartera


def cargar(tk):
    p = os.path.join(DIR, tk.replace("=", "") + ".csv")
    if not os.path.exists(p):
        d = yf.download(tk, start="1995-01-01", progress=False,
                        auto_adjust=True)
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)
        d.to_csv(p)
    d = pd.read_csv(p, index_col=0, parse_dates=True)
    s = pd.to_numeric(d["Close"], errors="coerce").dropna()
    return s[s > 0]


print("=" * 84)
print("UNIVERSO")
print("=" * 84)
precios, clases = {}, {}
for tk, nom, cl in UNIVERSO:
    s = cargar(tk)
    precios[nom] = s
    clases[nom] = cl
    print("  %-16s %-11s %5d sesiones  %s -> %s"
          % (nom, cl, len(s), s.index.min().date(), s.index.max().date()))

# ------------------------------------------------- construir la estrategia
filas = []
for nom, s in precios.items():
    r_d = s.pct_change().dropna()
    # volatilidad anualizada con los retornos diarios de los ultimos 12 meses
    vol = r_d.rolling(252).std() * np.sqrt(252)
    m = s.resample("ME").last()
    r_m = m.pct_change()
    vol_m = vol.resample("ME").last()

    for i in range(MIRADA + 1, len(m)):
        # señal: retorno de los 12 meses ANTERIORES al mes que se opera
        pas = m.iloc[i - 1] / m.iloc[i - 1 - MIRADA] - 1.0
        v = vol_m.iloc[i - 1]
        if pd.isna(pas) or pd.isna(v) or v <= 0 or pd.isna(r_m.iloc[i]):
            continue
        pos = np.sign(pas) * (VOL_OBJETIVO / v)
        pos = np.clip(pos, -5, 5)          # tope de apalancamiento por mercado
        filas.append(dict(fecha=m.index[i], mercado=nom, clase=clases[nom],
                          señal=np.sign(pas), pos=pos,
                          r_mercado=r_m.iloc[i], r_estrat=pos * r_m.iloc[i]))

T = pd.DataFrame(filas)
T["anio"] = T["fecha"].dt.year
print()
print("observaciones mercado-mes: %d  ·  %s -> %s"
      % (len(T), T["fecha"].min().date(), T["fecha"].max().date()))

# ------------------------------------------------- cartera equiponderada
cart = T.groupby("fecha").agg(r=("r_estrat", "mean"),
                              n=("mercado", "size")).reset_index()
cart = cart[cart["n"] >= 6]          # al menos 6 mercados disponibles
cart["anio"] = cart["fecha"].dt.year


def resumen(r):
    r = r.dropna()
    if len(r) < 24:
        return None
    mu, sd = r.mean() * 12, r.std() * np.sqrt(12)
    sh = mu / sd if sd > 0 else np.nan
    t = r.mean() / r.std() * np.sqrt(len(r))
    return dict(n=len(r), mu=mu, sd=sd, sh=sh, t=t,
                p=2 * (1 - stats.norm.cdf(abs(t))))


print()
print("=" * 84)
print("RESULTADO DE LA CARTERA  ·  sin costes todavia")
print("=" * 84)
print(f"{'periodo':<16}{'meses':>7}{'retorno':>10}{'vol':>8}"
      f"{'Sharpe':>9}{'t':>7}{'p':>9}")
print("-" * 84)
TRAMOS = [("1997-2009", 1997, 2009), ("2010-2026", 2010, 2026),
          ("2010-2017", 2010, 2017), ("2018-2026", 2018, 2026),
          ("TODO", 1997, 2026)]
for etq, a, b in TRAMOS:
    r = resumen(cart[(cart["anio"] >= a) & (cart["anio"] <= b)]["r"])
    if r:
        print(f"{etq:<16}{r['n']:>7}{r['mu']:>9.1%}{r['sd']:>8.1%}"
              f"{r['sh']:>9.2f}{r['t']:>7.2f}{r['p']:>9.4f}")

# ------------------------------------------------- por clase de activo
print()
print("=" * 84)
print("POR CLASE DE ACTIVO  (confirmacion cruzada, no busqueda)")
print("=" * 84)
print(f"{'clase':<12}{'1997-2009':>22}{'2010-2026':>22}")
print(f"{'':<12}{'Sharpe':>10}{'t':>12}{'Sharpe':>10}{'t':>12}")
print("-" * 84)
for cl in ("ACCIONES", "BONOS", "METALES", "DIVISAS"):
    sub = T[T["clase"] == cl].groupby("fecha")["r_estrat"].mean()
    sub.index = pd.to_datetime(sub.index)
    fila = ""
    for a, b in [(1997, 2009), (2010, 2026)]:
        r = resumen(sub[(sub.index.year >= a) & (sub.index.year <= b)])
        fila += (f"{r['sh']:>10.2f}{r['t']:>12.2f}" if r
                 else f"{'n/d':>10}{'':>12}")
    print(f"{cl:<12}{fila}")

# ------------------------------------------------- costes
print()
print("=" * 84)
print("CON COSTES DE TRANSACCION")
print("=" * 84)
T = T.sort_values(["mercado", "fecha"])
T["pos_prev"] = T.groupby("mercado")["pos"].shift(1).fillna(0.0)
T["giro"] = (T["pos"] - T["pos_prev"]).abs()
giro_medio = T.groupby("fecha")["giro"].mean()
print("  giro medio por mes y mercado: %.3f (en unidades de exposicion)"
      % giro_medio.mean())
print()
print(f"  {'coste ida (bp)':>16}{'retorno neto':>15}{'Sharpe neto':>14}"
      f"{'t':>8}")
print("  " + "-" * 56)
for bp in (0, 2, 5, 10, 20):
    coste = T.groupby("fecha").apply(
        lambda g: (g["giro"] * bp / 1e4).mean(), include_groups=False)
    neto = (cart.set_index("fecha")["r"] - coste).dropna()
    r = resumen(neto)
    print(f"  {bp:>16}{r['mu']:>14.1%}{r['sh']:>14.2f}{r['t']:>8.2f}")

print()
print("=" * 84)
print("CONTRASTE CON LA EXPECTATIVA REGISTRADA")
print("=" * 84)
r1 = resumen(cart[cart["anio"] <= 2009]["r"])
r2 = resumen(cart[cart["anio"] >= 2010]["r"])
print("  registre de antemano: espero que salga DEBILITADO despues de 2010")
print("     1997-2009 : Sharpe %.2f · t=%.2f" % (r1["sh"], r1["t"]))
print("     2010-2026 : Sharpe %.2f · t=%.2f" % (r2["sh"], r2["t"]))
print("     -> %s" % ("se cumple: decae" if r2["sh"] < r1["sh"]
                      else "NO se cumple: no decae, revisar por que"))
