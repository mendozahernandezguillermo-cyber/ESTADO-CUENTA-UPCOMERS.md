#!/usr/bin/env python3
"""
¿CUANTO RIESGO LLEVA CADA ESTRATEGIA?

Hasta ahora reparti el riesgo por VOLATILIDAD INVERSA, que es lo razonable si
el objetivo es maximizar el Sharpe de la cartera. Pero el objetivo NO es el
Sharpe: es cobrar de una cuenta prop, y la regla del mejor dia (20%) premia
tener MUCHOS dias activos.

La #1 opera 8 veces al año. La #2 esta en el mercado todos los dias. Asi que
el peso de la #2 no se elige por vol inversa: se elige midiendo la
probabilidad de cobro.

Universo del trend: B (los 8 mercados que existen como CFD). Elegido porque
es el unico que no añade ningun grado de libertad: se quitaron los 4 mercados
no operables y no se puso nada en su lugar.
"""
import numpy as np
import pandas as pd

D_TREND = "datos"
VOL_OBJETIVO = 0.10
MIRADA = 12
TOPE = 5.0
MIN_MERCADOS = 6

UNIV_B = {
    "S&P 500":  f"{D_TREND}/SPY.csv",
    "Nasdaq 100": f"{D_TREND}/QQQ.csv",
    "Oro":      f"{D_TREND}/GLD.csv",
    "Plata":    f"{D_TREND}/SLV.csv",
    "EUR/USD":  f"{D_TREND}/EURUSDX.csv",
    "USD/JPY":  f"{D_TREND}/USDJPYX.csv",
    "GBP/USD":  f"{D_TREND}/GBPUSDX.csv",
    "AUD/USD":  f"{D_TREND}/AUDUSDX.csv",
}

diarias, posiciones = {}, {}
for nom, p in UNIV_B.items():
    d = pd.read_csv(p, index_col=0, parse_dates=True)
    s = pd.to_numeric(d["Close"], errors="coerce").dropna()
    s = s[s > 0]
    r_d = s.pct_change().dropna()
    vol = r_d.rolling(252).std() * np.sqrt(252)
    m = s.resample("ME").last()
    vol_m = vol.resample("ME").last()
    pos = {}
    for i in range(MIRADA + 1, len(m)):
        pas = m.iloc[i - 1] / m.iloc[i - 1 - MIRADA] - 1.0
        v = vol_m.iloc[i - 1]
        if pd.isna(pas) or pd.isna(v) or v <= 0:
            continue
        pos[m.index[i]] = float(np.clip(np.sign(pas) * (VOL_OBJETIVO / v),
                                        -TOPE, TOPE))
    ps = pd.Series(pos).sort_index()
    pos_d = ps.reindex(r_d.index, method="bfill")
    posiciones[nom] = pos_d
    diarias[nom] = (pos_d * r_d).dropna()

DI = pd.DataFrame(diarias)
s2 = DI.mean(axis=1)[DI.notna().sum(axis=1) >= MIN_MERCADOS]

S1 = pd.read_csv("../planes/salida/cartera_diaria.csv",
                 index_col=0, parse_dates=True)["s1"]
A = pd.DataFrame({"s1": np.clip(S1, -0.008, 0.008), "s2": s2}).dropna()
A.to_csv("serie_cfd.csv")

E = "=" * 86
print(E)
print("SERIE DIARIA CON EL UNIVERSO CFD (8 mercados)")
print(E)
print(f"  dias            : {len(A):,}   {A.index.min().date()} -> {A.index.max().date()}")
print(f"  vol anual #1    : {A['s1'].std()*np.sqrt(252):>7.2%}   "
      f"(truncada a +-80 bp)")
print(f"  vol anual #2    : {A['s2'].std()*np.sqrt(252):>7.2%}")
print(f"  dias activos #1 : {(A['s1']!=0).sum():>7}  ({(A['s1']!=0).mean():.1%})")
print(f"  dias activos #2 : {(A['s2']!=0).sum():>7}  ({(A['s2']!=0).mean():.1%})")
print(f"  correlacion     : {A['s1'].corr(A['s2']):>+7.3f}")
print(f"  guardado en trend/serie_cfd.csv")

# --------------------------------------------------- simulacion de la cuenta
import sys
sys.path.insert(0, "../prop-instant")
src = open("../prop-instant/upcomers_reglas_reales.py", encoding="utf-8").read()
src = src.split("# ------------------------------------------------------------------ main")[0]
ns = {}
exec(compile(src, "u", "exec"), ns)
simular, bootstrap_par = ns['simular'], ns['bootstrap_par']

VOL_CARTERA = 0.045


def preparar(w2, vol=VOL_CARTERA):
    w1 = 1.0 - w2
    cart = w1 * A["s1"].values + w2 * A["s2"].values
    lev = vol / (cart.std() * np.sqrt(252))
    return w1 * A["s1"].values * lev, w2 * A["s2"].values * lev, lev


iv1, iv2 = 1 / A["s1"].std(), 1 / A["s2"].std()
w2_volinv = iv2 / (iv1 + iv2)

print()
print(E)
print("BARRIDO DEL PESO DE LA #2   ·   cuenta 50K, DD 7%, vol 4,5%, reglas reales")
print(E)
print(f"  El reparto por volatilidad inversa daria w2 = {w2_volinv:.1%}")
print()
print(f"  {'peso #2':>9}{'apalanc':>9}{'P(cobro)':>11}{'cobros':>9}"
      f"{'P(quema)':>11}{'EV anual':>12}{'mejor dia*':>12}")
print("  " + "-" * 75)

mejor = None
for w2 in (0.10, w2_volinv, 0.25, 0.30, 0.40, 0.50, 0.60, 0.75):
    a1, a2, lev = preparar(w2)
    g1, g2 = bootstrap_par(a1, a2, 504, 15_000)
    r = simular(g1, g2, a2.std(), cuenta=50_000.0, dd=0.07, relativo=True,
                min_dias=5, escala_ref=0.05, escala_min=0.25, best_day=0.20)
    rs = simular(g1, g2, a2.std(), cuenta=50_000.0, dd=0.07, relativo=True,
                 min_dias=5, escala_ref=0.05, escala_min=0.25, best_day=0.0)
    coste_regla = (rs['npag'] > 0).mean() - (r['npag'] > 0).mean()
    ev = r['neto'].mean() / 2
    etq = f"{w2:.1%}" + (" *vi" if abs(w2 - w2_volinv) < 1e-9 else "")
    print(f"  {etq:>9}{lev:>9.2f}{(r['npag']>0).mean():>11.1%}"
          f"{r['npag'].mean():>9.2f}{r['quemada'].mean():>11.1%}"
          f"{ev:>11,.0f}${coste_regla:>11.1%}")
    if mejor is None or ev > mejor[1]:
        mejor = (w2, ev, r)

print()
print("  * 'mejor dia' = puntos porcentuales de P(cobro) que cuesta la regla")
print("    del 20%. Cuanto mas peso lleva la #2, menos duele.")
print(f"\n  Maximo de EV: peso #2 = {mejor[0]:.1%}  ->  {mejor[1]:,.0f} $/año")

# --------------------------------------------------- giro y coste real
print()
print(E)
print("¿CUANTO CUESTA OPERAR LA #2?")
print(E)
P = pd.DataFrame(posiciones)
giro_d = P.diff().abs().sum(axis=1).replace(0, np.nan).dropna()
print(f"  dias con rebalanceo        : {len(giro_d):,} de {len(P):,} "
      f"({len(giro_d)/len(P):.1%})")
print(f"  giro medio cuando ocurre   : {giro_d.mean():.3f} unidades de exposicion")
print(f"  giro total por año         : {giro_d.sum()/ (len(P)/252):.2f}")
print()
print(f"  {'coste ida (bp)':>16}{'coste anual':>14}{'sobre vol 1,26%':>18}")
print("  " + "-" * 48)
vol2 = A["s2"].std() * np.sqrt(252)
for bp in (1, 2, 5, 10):
    c = giro_d.sum() / (len(P) / 252) * bp / 1e4
    print(f"  {bp:>16}{c:>13.3%}{c/vol2*100:>17.1f}%")
print()
print("  Interpretacion: con 2 bp de coste de ida el giro anual cuesta")
print(f"  {giro_d.sum()/(len(P)/252)*2/1e4:.3%} sobre una volatilidad del {vol2:.1%}.")
print("  Es una estrategia barata: rebalancea una vez al mes por mercado.")
