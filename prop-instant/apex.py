#!/usr/bin/env python3
"""
APEX 50K con sus reglas reales, dentro del marco que ya teniamos.

Reglas (verificadas en su centro de ayuda y en resumenes de agosto 2026):
  EVALUACION : objetivo 3.000 $ · trailing drawdown 2.500 $ · SIN consistencia
               · se puede pasar en 1 dia · cuota unica (con descuentos grandes)
  FINANCIADA : trailing 2.500 $ · 5 dias cualificados · consistencia 50%
               · minimo de retiro 500 $ · 100% del primer 25.000 $
               · maximo 6 payouts y la cuenta se cierra
  Y los frenos: trailing INTRADIA sobre no realizado, prohibido overnight
               desde marzo 2026, stop-loss obligatorio.

La pregunta que contesta: ¿de donde sale el dinero de quien cobra en Apex,
de su ventaja o de la estructura? Se mide el EV con ventaja CERO.
"""
import io
import contextlib
import numpy as np
from dataclasses import replace

with contextlib.redirect_stdout(io.StringIO()):
    from marco_general import Reglas, motor

# Apex no tiene "objetivo + objetivo": tiene evaluacion y luego financiada.
# Se modela como una fase de objetivo 6% (3.000 sobre 50K) y luego cobros.
APEX = Reglas(
    nombre='Apex 50K',
    cuenta=50_000.0,
    cuota=150.0,            # se barre despues: los descuentos bajan mucho
    reembolsable=False,
    split=1.00,             # 100% del primer 25.000 $
    dd_dia=0.99,            # Apex no tiene limite diario aparte del trailing
    dd_max=0.05,            # 2.500 $ = 5%
    tipo_dd='trail_rt',     # trailing intradia sobre NO REALIZADO
    objetivos=(0.06,),      # evaluacion: 3.000 $
    min_dias=5,
    min_benef_dia=0.0,      # los dias cualificados de Apex piden 50$/dia aprox
    best_day=0.50,          # consistencia 50%, mas permisiva que la de otros
)

print("=" * 78)
print("APEX 50K · trailing 5% en tiempo real · objetivo eval 3.000 $")
print("consistencia 50% · split 100% · cuota unica")
print("=" * 78)

# ------------------------------------------------- 1. ventaja CERO
print("\n1. CON VENTAJA CERO (Sharpe bruto 0, neto -0,25 tras costes)")
print(f"{'vol anual':>10}{'P(cobro)':>11}{'P(ruina)':>11}{'EV/cuenta':>12}")
print("-" * 78)
mejor = (-1e9, None)
for vol in (0.04, 0.06, 0.08, 0.12, 0.18, 0.25, 0.35):
    r = motor(APEX, 0.0, vol, umbral=500, anos=2, n=8000)
    print(f"{vol:>10.0%}{r['p_cobro']:>10.1%}{r['p_ruina']:>11.1%}"
          f"{r['ev_cuenta']:>12.0f}")
    if r['ev_cuenta'] > mejor[0]:
        mejor = (r['ev_cuenta'], vol)
print(f"   -> optimo sin ventaja: vol {mejor[1]:.0%}, EV {mejor[0]:.0f} $")

# ------------------------------------------------- 2. con ventaja
print("\n2. CON VENTAJA, a la vol optima de cada caso")
print(f"{'Sharpe bruto':>13}{'vol':>7}{'P(cobro)':>11}{'P(ruina)':>11}"
      f"{'EV/cuenta':>12}")
print("-" * 78)
opt = {}
for sh in (0.0, 0.5, 1.0, 1.5, 2.0):
    best = (-1e9, None, None)
    for vol in (0.04, 0.06, 0.08, 0.12, 0.18, 0.25):
        r = motor(APEX, sh, vol, umbral=500, anos=2, n=8000)
        if r['ev_cuenta'] > best[0]:
            best = (r['ev_cuenta'], vol, r)
    ev, vol, r = best
    opt[sh] = (vol, ev)
    print(f"{sh:>13.1f}{vol:>7.0%}{r['p_cobro']:>10.1%}{r['p_ruina']:>11.1%}"
          f"{ev:>12.0f}")

# ------------------------------------------------- 3. efecto de la cuota
print("\n3. EFECTO DEL PRECIO (Apex descuenta agresivamente y a menudo)")
print(f"{'cuota':>8}" + "".join(f"{'Sh ' + str(s):>13}" for s in (0.0, 1.0)))
print("-" * 78)
for cuota in (20, 50, 100, 150, 300):
    fila = ""
    for sh in (0.0, 1.0):
        R = replace(APEX, cuota=float(cuota))
        vol = opt[sh][0]
        r = motor(R, sh, vol, umbral=500, anos=2, n=8000)
        fila += f"{r['ev_cuenta']:>13.0f}"
    print(f"{cuota:>8}{fila}")

# ------------------------------------------------- 4. la cartera de 20
print("\n" + "=" * 78)
print("4. LA JUGADA QUE PERMITE LA ESTRUCTURA: 20 CUENTAS")
print("=" * 78)
print("Con cuota unica y 20 cuentas, lo racional NO es operar mejor: es")
print("repetir una apuesta de perdida acotada las veces que deje el reglamento.")
print()
print(f"{'cuentas':>8}{'cuota total':>13}{'EV total':>11}{'P(al menos 1 cobro)':>22}")
print("-" * 78)
CUOTA_DESC = 50.0
R = replace(APEX, cuota=CUOTA_DESC)
vol0 = opt[0.0][0]
r1 = motor(R, 0.0, vol0, umbral=500, anos=2, n=12000)
p1 = r1['p_cobro']
for n in (1, 5, 10, 20):
    p_alguno = 1 - (1 - p1) ** n
    print(f"{n:>8}{n * CUOTA_DESC:>13.0f}{n * r1['ev_cuenta']:>11.0f}"
          f"{p_alguno:>21.1%}")
print()
print("  (cuota de %.0f $ por cuenta, ventaja CERO, vol %.0f%%,"
      " P(cobro) individual %.1f%%)" % (CUOTA_DESC, vol0 * 100, p1 * 100))

print("\n" + "=" * 78)
print("LO QUE ESTO NO INCLUYE")
print("=" * 78)
print("""  - Que Apex pague. Es el termino dominante y no se puede simular.
  - El maximo de 6 payouts por cuenta antes de cerrarla.
  - El stop-loss obligatorio desde marzo 2026, que acota la cola pero
    tambien fuerza a materializar perdidas que antes se recuperaban.
  - Que el trailing es sobre NO REALIZADO tick a tick: mi simulacion mira
    la equity 4 veces al dia, asi que SUBESTIMA las roturas.
  - Y sobre todo: si operas 20 cuentas con la MISMA estrategia, no son 20
    apuestas independientes sino una multiplicada por 20. La columna
    'P(al menos 1 cobro)' solo vale si las cuentas son independientes,
    lo que exige estrategias distintas en cada una.""")
