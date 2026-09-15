"""
EL EV DE LA CONFIGURACION QUE DE VERDAD ESTA CORRIENDO.

Hasta ahora he dimensionado las dos patas a partir de un OBJETIVO de vol del
4,5% anual. El EA no funciona asi: tiene el riesgo puesto a mano. Y encima la
serie del trend que use tenia 8 mercados cuando el EA solo opera 7. O sea que
mis cifras estaban infladas por dos motivos a la vez.

Aqui se construyen las dos patas con las escalas REALES leidas del diálogo de
Inputs:

  #1 FOMC   InpRiesgoPorEvento = 1.35 % de la equity en un stop de 80 bp
            => multiplicador = 0.0135 / 0.0080 = 1.6875 sobre el retorno del indice

  #2 TREND  InpVolPorMercado = 7.23 % anual por mercado, sobre el 10 % con que
            se construyo la serie                        => x 0.723
            InpMercadosRef = 8 pero solo hay 7 mercados
            operables (NACUSD.c se omite por lote minimo) => x 7/8
            => multiplicador = 0.723 x 0.875 = 0.6326

Y la serie del trend es la de 7 mercados (serie_cfd_b7.csv, Sharpe 0,454)
en vez de la de 8 (0,522).
"""
import numpy as np
import pandas as pd

ns = {"__name__": "addendum"}
exec(compile(open("cobros_reales_addendum.py", encoding="utf-8")
             .read().split("# ---8<--- INFORME")[0],
             "cobros_reales_addendum.py", "exec"), ns)
simular2 = ns["simular2"]; mod = ns["mod"]
serie_s1 = mod["serie_s1"]; STOP_BP = mod["STOP_BP"]
CUENTA = mod["CUENTA"]

B7 = pd.read_csv("../trend/serie_cfd_b7.csv", index_col=0, parse_dates=True)
B8 = pd.read_csv("../trend/serie_cfd.csv", index_col=0, parse_dates=True)

MULT_TREND_REAL = 0.723 * 7.0 / 8.0     # 7,23% por mercado y 7 de 8 operables
N = 30_000
ANIOS = 4


def patas(tp_bp, riesgo_pct, s2_serie, mult_trend):
    mult1 = (riesgo_pct / 100.0) / (STOP_BP / 1e4)
    s1 = pd.Series(0.0, index=s2_serie.index)
    for ts, r in serie_s1(tp_bp).items():
        if ts in s1.index:
            s1.loc[ts] = r
    D = pd.DataFrame({"s1": s1, "s2": s2_serie}).dropna()
    D = D[D.index >= "2011-01-01"]
    a = (D["s1"] * mult1).values
    b = (D["s2"] * mult_trend).values
    vol = (a + b).std() * np.sqrt(252)
    return a, b, vol


E = "=" * 96
print(E)
print(f"EV A {ANIOS} AÑOS  ·  de mi modelo teorico a la configuracion real")
print(E)
print(f"  {'configuracion':<44}{'vol real':>10}{'recibido':>11}"
      f"{'por año':>10}{'P(cobra)':>10}{'P(quema)':>10}")
print("  " + "-" * 92)

casos = [
    ("lo que dije: vol 4,5% objetivo + 8 mercados", 40.0, 1.47, B8["s2"], 0.30 * 2.6250),
    ("EN VIVO AHORA: TP 80 · 1.35% · 7 mercados",   80.0, 1.35, B7["s2"], MULT_TREND_REAL),
    ("con TP 40: TP 40 · 1.35% · 7 mercados",       40.0, 1.35, B7["s2"], MULT_TREND_REAL),
    ("recomendado: TP 40 · 0.96% · 7 mercados",     40.0, 0.96, B7["s2"], MULT_TREND_REAL),
]
res = {}
for nom, tp, rg, s2, mt in casos:
    a, b, vol = patas(tp, rg, s2, mt)
    g1, g2 = mod["bootstrap_par"](a, b, 252 * ANIOS, N)
    r = simular2(g1, g2, b.std())
    res[nom] = r
    rec = r["recibido"].mean()
    print(f"  {nom:<44}{vol:>9.2%}{rec:>10,.0f}${rec/ANIOS:>9,.0f}$"
          f"{(r['npag']>0).mean():>10.1%}{r['quemada'].mean():>10.1%}")

print()
print(E)
print("EL TAMAÑO DE MI ERROR ACUMULADO")
print(E)
teor = res[casos[0][0]]["recibido"].mean()
vivo = res[casos[1][0]]["recibido"].mean()
tp40 = res[casos[2][0]]["recibido"].mean()
rec = res[casos[3][0]]["recibido"].mean()
print(f"  lo que te dije a 4 años            : {teor:>8,.0f} $   "
      f"({teor/ANIOS:,.0f} $/año)")
print(f"  lo que tu configuracion real da    : {vivo:>8,.0f} $   "
      f"({vivo/ANIOS:,.0f} $/año)   {vivo/teor:.2f}x")
print(f"  con el TP a 40                     : {tp40:>8,.0f} $   "
      f"({tp40/ANIOS:,.0f} $/año)")
print(f"  con TP 40 y riesgo 0,96%           : {rec:>8,.0f} $   "
      f"({rec/ANIOS:,.0f} $/año)")
print()
print("  Las tres causas, en orden de tamaño:")
print("   1. la serie del trend real tiene 7 mercados y Sharpe 0,454, no 0,522")
print("   2. el riesgo real es 1,35% y no el 1,44-1,47% que yo suponia")
print("   3. el trend opera al 7/8 de su escala porque NACUSD.c no cabe")
print()
print("  Nota: el TP 40 SUBE el EV y ademas mete la peor perdida por operacion")
print("  dentro del limite del 2%. Bajar el riesgo a 0,96% cuesta EV pero")
print("  compra margen contra un hard breach. Esa sigue siendo tu decision.")
