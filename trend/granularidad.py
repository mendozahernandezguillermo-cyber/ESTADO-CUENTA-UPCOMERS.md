#!/usr/bin/env python3
"""
¿ES 24.800 $ SUFICIENTE PARA ESTA CESTA?

El primer informe del EA reveló que los lotes se redondean con un paso de 0,01
y que el nocional por lote va de 21.000 $ (plata) a 260.000 $ (NASDAQ). Sobre
una cuenta de 24.800 $ las posiciones objetivo valen entre 372 $ y 4.130 $, o
sea entre 0,004 y 0,03 lotes. El redondeo deja de ser un detalle.

Se miden tres cosas:
  A. el sesgo de redondear hacia ABAJO (MathFloor, lo que tenia) contra
     redondear al MAS CERCANO (MathRound, lo que acabo de poner);
  B. cuanto se degrada la estrategia por la granularidad, a distintos
     tamaños de cuenta;
  C. que mercados sobreviven en cada tamaño.

Los nocionales por lote son los IMPLICADOS por el informe del EA (de los
lotes que calculó y las exposiciones objetivo). El proximo informe los dara
exactos, pero las cotas ya son estrechas.
"""
import numpy as np
import pandas as pd

VOL_OBJ = 7.23 / 100.0
MIRADA = 12
TOPE = 5.0
DIVISOR = 8
DIAS_VOL = 150
PASO = 0.01

#  simbolo    fichero              nocional/lote hoy   precio hoy   base USD
CESTA = [
    ("SPCUSD.c", "datos/SPY.csv",       70_000.0,  7000.0, False),
    ("NACUSD.c", "datos/QQQ.csv",      260_000.0, 26000.0, False),
    ("XAUUSD",   "datos/GLD.csv",       50_000.0,  5000.0, False),
    ("XAGUSD",   "datos/SLV.csv",       21_250.0,    85.0, False),
    ("EURUSD",   "datos/EURUSDX.csv",  118_500.0,   1.185, False),
    ("USDJPY",   "datos/USDJPYX.csv",  100_000.0, 155.0,   True),
    ("GBPUSD",   "datos/GBPUSDX.csv",  136_800.0,   1.368, False),
    ("AUDUSD",   "datos/AUDUSDX.csv",   69_600.0,   0.696, False),
]

series, contrato = {}, {}
for nom, p, noc, precio_hoy, base_usd in CESTA:
    d = pd.read_csv(p, index_col=0, parse_dates=True)
    s = pd.to_numeric(d["Close"], errors="coerce").dropna()
    series[nom] = s[s > 0]
    # el nocional por lote escala con el precio, salvo si la base es el dolar
    contrato[nom] = (None if base_usd else noc / precio_hoy, noc)

# la referencia de precio del CFD frente al ETF: factor de escala
factor_cfd = {}
for nom, p, noc, precio_hoy, base_usd in CESTA:
    factor_cfd[nom] = precio_hoy / series[nom].iloc[-1]


def construir(equity, modo):
    """modo: 'exacto', 'floor', 'round'. Devuelve (serie diaria, dict de uso)."""
    diarias, usados = {}, {}
    for nom, p, noc0, precio_hoy, base_usd in CESTA:
        s = series[nom]
        r_d = s.pct_change().dropna()
        vol = r_d.rolling(DIAS_VOL).std(ddof=1) * np.sqrt(252)
        m = s.resample("ME").last()
        vol_m = vol.resample("ME").last()
        cont, noc_fijo = contrato[nom]

        pos, n_ok, n_cero = {}, 0, 0
        for i in range(MIRADA + 1, len(m)):
            pas = m.iloc[i - 1] / m.iloc[i - 13] - 1.0
            v = vol_m.iloc[i - 1]
            if pd.isna(pas) or pd.isna(v) or v <= 0:
                continue
            e = float(np.clip(np.sign(pas) * (VOL_OBJ / v), -TOPE, TOPE)) / DIVISOR

            if modo == "exacto":
                pos[m.index[i]] = e
                n_ok += 1
                continue

            precio_cfd = m.iloc[i - 1] * factor_cfd[nom]
            noc_lote = noc_fijo if cont is None else cont * precio_cfd
            lotes = abs(e) * equity / noc_lote
            if modo == "floor":
                q = np.floor(lotes / PASO) * PASO
            else:
                q = np.round(lotes / PASO) * PASO
            if q < PASO - 1e-12:
                n_cero += 1
                pos[m.index[i]] = 0.0
                continue
            n_ok += 1
            pos[m.index[i]] = np.sign(e) * q * noc_lote / equity

        usados[nom] = (n_ok, n_cero)
        if pos:
            ps = pd.Series(pos).sort_index()
            diarias[nom] = (ps.reindex(r_d.index, method="bfill") * r_d).dropna()
    DI = pd.DataFrame(diarias)
    return DI.sum(axis=1)[DI.notna().sum(axis=1) >= 6], usados


E = "=" * 90
print(E)
print("A) EL SESGO DEL REDONDEO HACIA ABAJO")
print(E)
print(f"  {'cuenta':>9}{'modo':>9}{'vol anual':>12}{'% del 3,91% obj':>18}"
      f"{'Sharpe':>9}{'peor dia':>11}")
print("  " + "-" * 68)
for eq in (24_804.63, 50_000.0, 100_000.0):
    for modo in ("exacto", "floor", "round"):
        x, _ = construir(eq, modo)
        v = x.std() * np.sqrt(252)
        sh = x.mean() / x.std() * np.sqrt(252)
        etq = f"{eq:,.0f}" if modo == "exacto" else ""
        print(f"  {etq:>9}{modo:>9}{v:>12.2%}{v/0.0391:>17.0%}"
              f"{sh:>9.2f}{x.min():>11.2%}")
    print()

print(E)
print("B) QUE MERCADOS SOBREVIVEN A CADA TAMAÑO DE CUENTA (modo round)")
print(E)
print(f"  {'simbolo':<11}{'noc/lote':>11}", end="")
for eq in (24_804.63, 50_000.0, 100_000.0, 200_000.0):
    print(f"{eq/1000:>13,.0f}k", end="")
print()
print("  " + "-" * 65)
tablas = {}
for eq in (24_804.63, 50_000.0, 100_000.0, 200_000.0):
    _, u = construir(eq, "round")
    tablas[eq] = u
for nom, p, noc0, ph, bu in CESTA:
    print(f"  {nom:<11}{noc0:>11,.0f}", end="")
    for eq in (24_804.63, 50_000.0, 100_000.0, 200_000.0):
        n_ok, n_cero = tablas[eq][nom]
        tot = n_ok + n_cero
        print(f"{1 - n_cero/max(tot,1):>13.0%}", end="")
    print()
print("  " + "-" * 65)
print("  (porcentaje de meses en que el mercado consigue una posicion)")

print()
print(E)
print("C) LO QUE ESTO LE HACE A LA CARTERA COMPLETA")
print(E)
S1 = pd.read_csv("../planes/salida/cartera_diaria.csv",
                 index_col=0, parse_dates=True)["s1"]
s1 = np.clip(S1, -0.008, 0.008)
print(f"  {'cuenta':>9}{'vol #2':>9}{'peso #2 efectivo':>19}"
      f"{'Sharpe cartera':>17}")
print("  " + "-" * 54)
x_ex, _ = construir(1e12, "exacto")
for eq in (24_804.63, 50_000.0, 100_000.0):
    x, _ = construir(eq, "round")
    A = pd.DataFrame({"s1": s1, "s2": x}).dropna()
    # se mantiene el escalado a 4,5% de vol de cartera con pesos 70/30
    w1, w2 = 0.70, 0.30
    cart = w1 * A["s1"] + w2 * A["s2"]
    lev = 0.045 / (cart.std() * np.sqrt(252))
    # peso efectivo de la #2 en RIESGO, no en nominal
    v1 = (w1 * A["s1"]).std()
    v2 = (w2 * A["s2"]).std()
    sh = cart.mean() / cart.std() * np.sqrt(252)
    print(f"  {eq:>9,.0f}{A['s2'].std()*np.sqrt(252):>9.2%}"
          f"{v2/(v1+v2):>18.0%}{sh:>17.2f}")
print()
print("  El 'peso efectivo' es la parte del riesgo que aporta de verdad la #2")
print("  despues del redondeo. Si cae muy por debajo del 30%, la regla del")
print("  mejor dia vuelve a apretar y la probabilidad de cobro baja.")
