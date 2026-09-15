#!/usr/bin/env python3
"""
INCONSISTENCIA ENTRE LOS DOS EA: los parametros que he dado no son coherentes.

Le he dicho al usuario dos cosas que no encajan:

  · InpRiesgoPorEvento = 2.14  en EA_FOMC_Gap
  · InpVolPorMercado   = 7.23  en EA_Trend_Multi

El 2,14 se derivo para que la #1 SOLA rindiera una volatilidad de cartera del
4,5%. El 7,23 se derivo para que la #2 aportase el 30% (nominal) de una
cartera al 4,5%. Los dos numeros son correctos por separado y JUNTOS suman
mas riesgo del presupuestado.

Aqui se deriva el juego coherente desde una sola definicion: la volatilidad
objetivo de la CARTERA y el reparto nominal que se eligio midiendo la
probabilidad de cobro (w2 = 30%).
"""
import numpy as np
import pandas as pd

VOL_CARTERA = 0.045
W2 = 0.30
W1 = 1.0 - W2
STOP_BP = 80.0
PEOR_EVENTO_BP = 133.4     # peor relleno real medido en 117 eventos
LIMITE_DIARIO = 0.04

A = pd.read_csv("../trend/serie_cfd.csv", index_col=0, parse_dates=True)
s1 = A["s1"]      # #1 pre-FOMC, truncada a +-80 bp, exposicion UNITARIA
s2 = A["s2"]      # #2 trend, cesta a 10% de vol por mercado, media de 8

v1 = s1.std() * np.sqrt(252)
v2 = s2.std() * np.sqrt(252)
rho = s1.corr(s2)

E = "=" * 84
print(E)
print("LOS INGREDIENTES, MEDIDOS")
print(E)
print(f"  vol anual de la #1 a exposicion 1x   : {v1:>7.2%}")
print(f"  vol anual de la #2 a 10% por mercado : {v2:>7.2%}")
print(f"  correlacion entre las dos            : {rho:>+7.3f}")

cart = W1 * s1 + W2 * s2
v_cart = cart.std() * np.sqrt(252)
lev = VOL_CARTERA / v_cart

print()
print(E)
print("DERIVACION DEL JUEGO COHERENTE")
print(E)
print(f"  cartera nominal {W1:.0%}/{W2:.0%} -> vol {v_cart:.2%}")
print(f"  apalancamiento para llegar al {VOL_CARTERA:.1%}: x{lev:.3f}")

vol_pata1 = W1 * v1 * lev
vol_pata2 = W2 * v2 * lev
print()
print(f"  vol final de la pata #1 : {vol_pata1:>7.2%}")
print(f"  vol final de la pata #2 : {vol_pata2:>7.2%}")
print(f"  total (con rho={rho:+.3f})  : "
      f"{np.sqrt(vol_pata1**2 + vol_pata2**2 + 2*rho*vol_pata1*vol_pata2):>7.2%}")
print()
print(f"  reparto del RIESGO (varianza): "
      f"#1 {vol_pata1**2/(vol_pata1**2+vol_pata2**2):.0%}  ·  "
      f"#2 {vol_pata2**2/(vol_pata1**2+vol_pata2**2):.0%}")
print("  OJO: el '30% nominal' que elegi midiendo P(cobro) equivale al")
print(f"  {vol_pata2**2/(vol_pata1**2+vol_pata2**2):.0%} de la VARIANZA. Son cosas distintas y las he mezclado")
print("  al hablar. El numero que importa es el nominal, porque es el que")
print("  se barrio contra la probabilidad de cobro.")

# ---- parametros de cada EA
apal1 = W1 * lev
riesgo_evento = apal1 * STOP_BP / 100.0
volpm = 10.0 * (W2 * lev)

print()
print(E)
print("PARAMETROS QUE HAY QUE PONER")
print(E)
print(f"  EA_FOMC_Gap")
print(f"    apalancamiento implicado      : x{apal1:.3f}")
print(f"    InpRiesgoPorEvento            : {riesgo_evento:.2f}   "
      f"(= apalancamiento x stop de {STOP_BP:.0f} bp)")
print(f"    lo que te habia dicho         : 2.14   <-- MAL si corren los dos")
print()
print(f"  EA_Trend_Multi")
print(f"    InpVolPorMercado              : {volpm:.2f}   "
      f"(= 10% x {W2:.0%} x {lev:.3f})")
print(f"    lo que te habia dicho         : 7.23   <-- correcto")

# ---- el efecto colateral bueno
print()
print(E)
print("EFECTO COLATERAL: EL LIMITE DIARIO DEL 4% DEJA DE APRETAR")
print(E)
print(f"  {'riesgo':>8}{'apalanc':>9}{'peor evento medido':>20}"
      f"{'% del 4% diario':>18}{'con desliz x2':>16}")
print("  " + "-" * 71)
for r in (2.14, riesgo_evento, 1.00):
    ap = r / (STOP_BP / 100.0)
    peor = PEOR_EVENTO_BP * ap / 100.0
    peor2 = 190.0 * ap / 100.0
    marca = "  <- coherente" if abs(r - riesgo_evento) < 1e-9 else ""
    print(f"  {r:>7.2f}%{ap:>9.3f}{-peor:>19.2f}%{peor/LIMITE_DIARIO:>17.0%}"
          f"{-peor2:>15.2f}%{marca}")
print()
print("  Con el riesgo coherente, el peor evento historico consume el")
print(f"  {PEOR_EVENTO_BP*(riesgo_evento/(STOP_BP/100))/100/LIMITE_DIARIO:.0%} del limite diario en vez del 89%. La preocupacion que")
print("  levante hace unos turnos se disuelve sola al cuadrar los pesos:")
print("  no hacia falta un juicio sobre la cola, hacia falta cuadrar la suma.")

# ---- comprobacion contra el drawdown observado
print()
print(E)
print("COMPROBACION CONTRA EL DRAWDOWN QUE YA MEDIMOS EN EL PROBADOR")
print(E)
dd_observado = 0.0433      # 4 operaciones, riesgo 2.14
print(f"  El Probador dio {dd_observado:.2%} de drawdown de equity con "
      f"riesgo 2,14%.")
print(f"  Escalado al riesgo coherente ({riesgo_evento:.2f}%): "
      f"{dd_observado*riesgo_evento/2.14:.2%}")
print(f"  Presupuesto de la cuenta de 25K (DD 5%): 5,00%")
print(f"  -> queda para la #2 y para la mala suerte: "
      f"{0.05 - dd_observado*riesgo_evento/2.14:.2%}")
