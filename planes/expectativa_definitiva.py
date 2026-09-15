"""
LA EXPECTATIVA DE LA CONFIGURACION QUE QUEDA MONTADA.

Leida de las tres capturas del dialogo de Inputs, sin suponer nada:

  EA_FOMC_Gap    entrada 16:00 NY -3 min · salida 09:30 NY
                 stop 80 bp · TP 40 bp · riesgo 0,96% · spread max 3 bp
  EA_Trend_Multi 8 simbolos listados, 7 operables (NACUSD.c omitido)
                 vol 7,23%/mercado · divisor 8 · señal 12 meses
                 rebalanceo 10:00 NY · umbral 20% · espera 3 dias
  EA_Guardian    trailing 7% · diario 4% a las 00:00 UTC · factor 5%/0,25
                 posicion suelta 1,5% · latido USDCHF a los 25 dias

Se reporta el desglose año a año sobre los MISMOS caminos y la exposicion al
limite duro del 2% por operacion, que es lo que motivo los dos cambios.
"""
import numpy as np
import pandas as pd

ns = {"__name__": "addendum"}
exec(compile(open("cobros_reales_addendum.py", encoding="utf-8")
             .read().split("# ---8<--- INFORME")[0],
             "cobros_reales_addendum.py", "exec"), ns)
simular2 = ns["simular2"]; mod = ns["mod"]
serie_s1 = mod["serie_s1"]; STOP_BP = mod["STOP_BP"]

B7 = pd.read_csv("../trend/serie_cfd_b7.csv", index_col=0, parse_dates=True)
RIESGO, TP = 0.96, 40.0
MULT_TREND = 0.723 * 7.0 / 8.0
N, ANIOS = 40_000, 4
CORTES = [252, 504, 756]

mult1 = (RIESGO / 100.0) / (STOP_BP / 1e4)
s1 = pd.Series(0.0, index=B7.index)
for ts, r in serie_s1(TP).items():
    if ts in s1.index:
        s1.loc[ts] = r
D = pd.DataFrame({"s1": s1, "s2": B7["s2"]}).dropna()
D = D[D.index >= "2011-01-01"]
a = (D["s1"] * mult1).values
b = (D["s2"] * MULT_TREND).values

g1, g2 = mod["bootstrap_par"](a, b, 252 * ANIOS, N)
r = simular2(g1, g2, b.std(), snaps=CORTES)

E = "=" * 88
print(E)
print("EXPECTATIVA DE LA CONFIGURACION MONTADA")
print(E)
print(f"  volatilidad anual de la cartera      : {(a+b).std()*np.sqrt(252):>8.2%}")
print(f"  dinero al bolsillo a 4 años (media)  : {r['recibido'].mean():>7,.0f} $")
print(f"  por año                              : {r['recibido'].mean()/ANIOS:>7,.0f} $")
print(f"  mediana a 4 años                     : {np.median(r['recibido']):>7,.0f} $")
print(f"  probabilidad de cobrar algo          : {(r['npag']>0).mean():>8.1%}")
print(f"  probabilidad de quemar la cuenta     : {r['quemada'].mean():>8.1%}")
print(f"  atrapado no retirable a 4 años       : {r['atrapado'].mean():>7,.0f} $")

print()
print(f"  {'periodo':<12}{'acumulado':>12}{'del año':>11}")
print("  " + "-" * 35)
prev = 0.0
series = [(f"año {i+1}", r["foto"][c]) for i, c in enumerate(CORTES)]
series.append((f"año {ANIOS}", r["recibido"]))
for etq, arr in series:
    m = arr.mean()
    print(f"  {etq:<12}{m:>11,.0f}${m-prev:>10,.0f}$")
    prev = m

print()
print(E)
print("EXPOSICION AL LIMITE DURO DEL 2% POR OPERACION")
print(E)
print(f"  {'escenario':<46}{'% equity':>11}{'margen':>10}{'veredicto':>12}")
print("  " + "-" * 80)
for nom, bp in (("peor excursion con TP 40 (lo observado)", 108.2),
                ("la cola real del mercado (133,8 bp)", 133.8)):
    pct = bp / STOP_BP * RIESGO
    print(f"  {nom:<46}{pct:>10.2f}%{2.0-pct:>9.2f}%"
          f"{('ok' if pct < 2 else 'ROMPE'):>12}")
print()
print("  Antes de los cambios: 2,26% -> rompia. Ahora la peor caida que el")
print("  mercado hizo DE VERDAD se queda en 1,61%, con un 20% de margen.")
print("  Eso es exactamente lo que compraba bajar el riesgo a 0,96%.")
