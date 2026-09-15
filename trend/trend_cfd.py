#!/usr/bin/env python3
"""
EL TREND MULTI-ACTIVO, RESTRINGIDO A LO QUE SE PUEDE OPERAR COMO CFD

MOTIVO DE ESTA MEDICION
La especificacion original usaba 12 mercados, y CUATRO no existen como CFD en
un broker retail: EFA (desarrollados), EEM (emergentes), TLT y IEF (bonos del
Tesoro). Escribir el EA con esa cesta seria escribir algo inejecutable. Y los
bonos son una CLASE DE ACTIVO ENTERA, asi que quitarlos no es un detalle.

LA ESPECIFICACION NO SE TOCA. Es la misma de trend.py, literal:
   señal    : signo del retorno de los 12 meses anteriores
   tenencia : 1 mes, rebalanceo mensual
   tamaño   : escalado a vol objetivo del 10% anual por mercado, con la
              desviacion de los retornos diarios de los ultimos 12 meses
   tope     : +-5 de exposicion por mercado
   cartera  : equiponderada entre mercados, minimo 6 disponibles

LO QUE CAMBIA ES SOLO EL UNIVERSO, y lo hago en dos pasos para separar lo que
es una RESTRICCION de lo que seria una ELECCION:

  A. ORIGINAL (12 mercados)         referencia. No operable.
  B. SOLO QUITAR (8 mercados)       se eliminan los 4 que no mapean y NO se
                                    añade nada. Cero grados de libertad
                                    nuevos. Esta es la medicion que manda.
  C. QUITAR Y SUSTITUIR (12)        los 4 huecos se rellenan con indices que
                                    si son CFD estandar: GER40, UK100, JP225,
                                    AUS200. Esto SI añade un grado de
                                    libertad, asi que se reporta aparte y con
                                    desconfianza.

EXPECTATIVA REGISTRADA ANTES DE MIRAR: en el analisis original, post-2010 el
efecto solo sobrevivia en ACCIONES. Si eso es cierto, quitar bonos deberia
costar poco en la muestra reciente y bastante en la antigua. Si B sale MEJOR
que A en el periodo reciente, sospecho de mi mismo antes de creerlo.

Nota sobre los datos: para los indices se usa el precio (sin dividendos),
que es lo que replica un CFD sobre indice. Para los ETF y las divisas se usa
la serie ajustada, igual que en la medicion original. El precio sin
dividendos es la eleccion conservadora: baja el retorno medido.
"""
import os
import numpy as np
import pandas as pd
from scipy import stats

D_TREND = "datos"
D_YAHOO = "../nas100-data/yahoo"

VOL_OBJETIVO = 0.10
MIRADA = 12
TOPE = 5.0
MIN_MERCADOS = 6

#            nombre           fichero                 clase       cfd
CATALOGO = {
    "S&P 500":       (f"{D_TREND}/SPY.csv",      "ACCIONES", "SPX500"),
    "Nasdaq 100":    (f"{D_TREND}/QQQ.csv",      "ACCIONES", "NAS100"),
    "Desarrollados": (f"{D_TREND}/EFA.csv",      "ACCIONES", None),
    "Emergentes":    (f"{D_TREND}/EEM.csv",      "ACCIONES", None),
    "Treasury 20y":  (f"{D_TREND}/TLT.csv",      "BONOS",    None),
    "Treasury 10y":  (f"{D_TREND}/IEF.csv",      "BONOS",    None),
    "Oro":           (f"{D_TREND}/GLD.csv",      "METALES",  "XAUUSD"),
    "Plata":         (f"{D_TREND}/SLV.csv",      "METALES",  "XAGUSD"),
    "EUR/USD":       (f"{D_TREND}/EURUSDX.csv",  "DIVISAS",  "EURUSD"),
    "USD/JPY":       (f"{D_TREND}/USDJPYX.csv",  "DIVISAS",  "USDJPY"),
    "GBP/USD":       (f"{D_TREND}/GBPUSDX.csv",  "DIVISAS",  "GBPUSD"),
    "AUD/USD":       (f"{D_TREND}/AUDUSDX.csv",  "DIVISAS",  "AUDUSD"),
    "DAX":           (f"{D_YAHOO}/GDAXI.csv",    "ACCIONES", "GER40"),
    "FTSE 100":      (f"{D_YAHOO}/FTSE.csv",     "ACCIONES", "UK100"),
    "Nikkei 225":    (f"{D_YAHOO}/N225.csv",     "ACCIONES", "JP225"),
    "ASX 200":       (f"{D_YAHOO}/AXJO.csv",     "ACCIONES", "AUS200"),
}

UNIV_A = ["S&P 500", "Nasdaq 100", "Desarrollados", "Emergentes",
          "Treasury 20y", "Treasury 10y", "Oro", "Plata",
          "EUR/USD", "USD/JPY", "GBP/USD", "AUD/USD"]
UNIV_B = [m for m in UNIV_A if CATALOGO[m][2] is not None]
UNIV_C = UNIV_B + ["DAX", "FTSE 100", "Nikkei 225", "ASX 200"]


def cargar(nombre):
    p = CATALOGO[nombre][0]
    d = pd.read_csv(p, index_col=0, parse_dates=True)
    s = pd.to_numeric(d["Close"], errors="coerce").dropna()
    return s[s > 0]


PRECIOS = {}
for m in set(UNIV_A) | set(UNIV_C):
    try:
        PRECIOS[m] = cargar(m)
    except Exception as e:
        print(f"  no se pudo cargar {m}: {e}")


def construir(universo):
    """Devuelve (tabla mercado-mes, serie diaria de la cartera)."""
    filas, diarias = [], {}
    for nom in universo:
        s = PRECIOS[nom]
        r_d = s.pct_change().dropna()
        vol = r_d.rolling(252).std() * np.sqrt(252)
        m = s.resample("ME").last()
        r_m = m.pct_change()
        vol_m = vol.resample("ME").last()

        pos_por_mes = {}
        for i in range(MIRADA + 1, len(m)):
            pas = m.iloc[i - 1] / m.iloc[i - 1 - MIRADA] - 1.0
            v = vol_m.iloc[i - 1]
            if pd.isna(pas) or pd.isna(v) or v <= 0:
                continue
            pos = float(np.clip(np.sign(pas) * (VOL_OBJETIVO / v), -TOPE, TOPE))
            pos_por_mes[m.index[i]] = pos
            if not pd.isna(r_m.iloc[i]):
                filas.append(dict(fecha=m.index[i], mercado=nom,
                                  clase=CATALOGO[nom][1], pos=pos,
                                  r_estrat=pos * r_m.iloc[i]))
        if pos_por_mes:
            ps = pd.Series(pos_por_mes).sort_index()
            pos_d = ps.reindex(r_d.index, method="bfill")
            diarias[nom] = (pos_d * r_d).dropna()

    T = pd.DataFrame(filas)
    DI = pd.DataFrame(diarias)
    n_disp = DI.notna().sum(axis=1)
    serie_d = DI.mean(axis=1)[n_disp >= MIN_MERCADOS]
    return T, serie_d


def resumen(r, per=12):
    r = pd.Series(r).dropna()
    if len(r) < 24:
        return None
    mu, sd = r.mean() * per, r.std() * np.sqrt(per)
    return dict(n=len(r), mu=mu, sd=sd, sh=(mu / sd if sd > 0 else np.nan),
                t=r.mean() / r.std() * np.sqrt(len(r)))


E = "=" * 86
print(E)
print("LOS TRES UNIVERSOS")
print(E)
for etq, u in (("A ORIGINAL", UNIV_A), ("B SOLO QUITAR", UNIV_B),
               ("C QUITAR Y SUSTITUIR", UNIV_C)):
    clases = pd.Series([CATALOGO[m][1] for m in u]).value_counts().to_dict()
    print(f"\n  {etq}  ({len(u)} mercados)")
    print(f"    {', '.join(sorted(clases[k]*'' or f'{k}:{clases[k]}' for k in clases))}")
    print(f"    {', '.join(u)}")

RES = {}
for etq, u in (("A", UNIV_A), ("B", UNIV_B), ("C", UNIV_C)):
    RES[etq] = construir(u)

print()
print(E)
print("RESULTADO MENSUAL, SIN COSTES")
print(E)
TRAMOS = [("1997-2009", 1997, 2009), ("2010-2026", 2010, 2026),
          ("2018-2026", 2018, 2026), ("TODO", 1990, 2026)]
print(f"  {'periodo':<12}", end="")
for etq in ("A", "B", "C"):
    print(f"{'  '+etq+': Sharpe':>14}{'t':>7}", end="")
print()
print("  " + "-" * 78)
for nom, a, b in TRAMOS:
    print(f"  {nom:<12}", end="")
    for etq in ("A", "B", "C"):
        T, _ = RES[etq]
        c = T.groupby("fecha")["r_estrat"].mean()
        c = c[(c.index.year >= a) & (c.index.year <= b)]
        r = resumen(c)
        if r:
            print(f"{r['sh']:>14.2f}{r['t']:>7.2f}", end="")
        else:
            print(f"{'n/d':>14}{'':>7}", end="")
    print()

print()
print(E)
print("POR CLASE DE ACTIVO EN EL UNIVERSO ORIGINAL  (¿aportaban algo los bonos?)")
print(E)
T, _ = RES["A"]
print(f"  {'clase':<12}{'mercados':>9}{'1997-2009':>20}{'2010-2026':>20}")
print(f"  {'':<12}{'':>9}{'Sharpe':>10}{'t':>10}{'Sharpe':>10}{'t':>10}")
print("  " + "-" * 61)
for cl in ("ACCIONES", "BONOS", "METALES", "DIVISAS"):
    sub = T[T["clase"] == cl]
    nm = sub["mercado"].nunique()
    s = sub.groupby("fecha")["r_estrat"].mean()
    print(f"  {cl:<12}{nm:>9}", end="")
    for a, b in ((1997, 2009), (2010, 2026)):
        r = resumen(s[(s.index.year >= a) & (s.index.year <= b)])
        print(f"{r['sh']:>10.2f}{r['t']:>10.2f}" if r
              else f"{'n/d':>10}{'':>10}", end="")
    print()

print()
print(E)
print("GIRO Y COSTES")
print(E)
print(f"  {'universo':<10}{'giro/mes':>10}", end="")
for bp in (0, 2, 5, 10):
    print(f"{'  '+str(bp)+'bp Sh':>10}", end="")
print()
print("  " + "-" * 52)
for etq in ("A", "B", "C"):
    T, _ = RES[etq]
    T = T.sort_values(["mercado", "fecha"])
    T["prev"] = T.groupby("mercado")["pos"].shift(1).fillna(0.0)
    T["giro"] = (T["pos"] - T["prev"]).abs()
    cart = T.groupby("fecha")["r_estrat"].mean()
    print(f"  {etq:<10}{T.groupby('fecha')['giro'].mean().mean():>10.3f}", end="")
    for bp in (0, 2, 5, 10):
        coste = T.groupby("fecha")["giro"].mean() * bp / 1e4
        r = resumen((cart - coste).dropna())
        print(f"{r['sh']:>10.2f}", end="")
    print()

# ----------------------------------------------- cartera con la #1
print()
print(E)
print("LA CARTERA COMPLETA: correlacion, pesos y Sharpe conjunto")
print(E)
S1 = pd.read_csv("../planes/salida/cartera_diaria.csv",
                 index_col=0, parse_dates=True)["s1"]
s1 = np.clip(S1, -0.008, 0.008)

print(f"  {'universo':<10}{'dias':>7}{'vol #2':>9}{'corr con #1':>13}"
      f"{'peso #1':>9}{'peso #2':>9}{'Sharpe cartera':>16}{'peor dia':>10}")
print("  " + "-" * 84)
for etq in ("A", "B", "C"):
    _, sd_ = RES[etq]
    A2 = pd.DataFrame({"s1": s1, "s2": sd_}).dropna()
    iv1, iv2 = 1 / A2["s1"].std(), 1 / A2["s2"].std()
    w1 = iv1 / (iv1 + iv2)
    w2 = 1 - w1
    cart = w1 * A2["s1"] + w2 * A2["s2"]
    r = resumen(cart, per=252)
    print(f"  {etq:<10}{len(A2):>7}{A2['s2'].std()*np.sqrt(252):>8.1%}"
          f"{A2['s1'].corr(A2['s2']):>+13.3f}{w1:>9.1%}{w2:>9.1%}"
          f"{r['sh']:>16.2f}{cart.min():>10.2%}")

print()
print(E)
print("CONTRASTE CON LA EXPECTATIVA REGISTRADA")
print(E)
print("  Registre: post-2010 el efecto solo sobrevivia en ACCIONES, asi que")
print("  quitar bonos deberia costar POCO en la muestra reciente.")
for etq in ("A", "B"):
    T, _ = RES[etq]
    c = T.groupby("fecha")["r_estrat"].mean()
    r1 = resumen(c[c.index.year <= 2009])
    r2 = resumen(c[c.index.year >= 2010])
    print(f"    {etq}: 1997-2009 Sharpe {r1['sh']:.2f} (t={r1['t']:.2f})"
          f"   ·   2010-2026 Sharpe {r2['sh']:.2f} (t={r2['t']:.2f})")
