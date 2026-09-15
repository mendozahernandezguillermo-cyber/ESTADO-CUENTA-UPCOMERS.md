"""
RECALCULO CON LA CONFIGURACION QUE DE VERDAD ESTA CORRIENDO.

La captura del dialogo de Inputs desmiente lo que yo tenia apuntado:
  apuntado:  InpTakeProfitBp = 50.0   InpRiesgoPorEvento = 1.44
  REAL:      InpTakeProfitBp = 80.0   InpRiesgoPorEvento = 1.35

O sea que el EA en vivo lleva la configuracion SIMETRICA ±80 original. Todos
los numeros que he dado en los ultimos turnos asumian un ajuste que nunca se
aplico al grafico. Se recalcula la exposicion al limite duro del 2% con los
valores reales.

Excursiones adversas maximas medidas sobre los 117 eventos en M1
(de max_perdida_por_tp.py, flotante = peor punto durante la vida de la
operacion, que es lo que cuenta si el limite se evalua sobre posicion abierta):
"""
STOP_BP = 80.0
LIMITE = 2.0

# TP -> peor excursion adversa flotante, en bp
PEOR = {40.0: 108.2, 50.0: 133.8, 80.0: 133.8}

E = "=" * 84
print(E)
print("EXPOSICION AL LIMITE DURO DEL 2% CON LOS VALORES REALES")
print(E)
print(f"  {'configuracion':<30}{'peor bp':>10}{'% equity':>11}"
      f"{'margen':>10}{'veredicto':>14}")
print("  " + "-" * 75)
casos = [
    ("EN VIVO AHORA: TP 80 · 1.35%", 80.0, 1.35),
    ("lo que yo creia: TP 50 · 1.44%", 50.0, 1.44),
    ("cambiando solo TP: TP 40 · 1.35%", 40.0, 1.35),
    ("TP 40 · 1.20% (sin margen)", 40.0, 1.20),
    ("TP 40 · 0.96% (25% margen)", 40.0, 0.96),
]
for nom, tp, r in casos:
    bp = PEOR[tp]
    pct = bp / STOP_BP * r
    ver = "ROMPE" if pct > LIMITE else "ok"
    print(f"  {nom:<30}{bp:>10.1f}{pct:>10.2f}%{LIMITE-pct:>9.2f}%{ver:>14}")

print()
print(E)
print("LO QUE ESTO CAMBIA")
print(E)
r_seguro = LIMITE * STOP_BP / PEOR[50.0]
print(f"  1. La configuracion EN VIVO rompe el limite: 2,26% contra 2,00%.")
print(f"     Hay un evento historico real que habria cerrado la cuenta.")
print()
print(f"  2. Cambiar SOLO el TP a 40 ya la mete dentro: 1,83%, margen 0,17 pp.")
print(f"     Es mas margen del que te dije (0,05 pp) porque tu riesgo real es")
print(f"     1,35% y no el 1,44% que yo tenia apuntado.")
print()
print(f"  3. Pero ese margen depende de que el evento toque +40 bp ANTES de")
print(f"     hundirse. Contra la cola real de {PEOR[50.0]:.1f} bp el riesgo maximo")
print(f"     sin margen es {r_seguro:.2f}%, y tu estas en 1,35%. Sigues por encima.")
print()
print(f"  4. Mis cifras de EV estaban ~7% infladas por otro motivo: a 1,35% de")
print(f"     riesgo la vol efectiva es ~4,1% y no 4,5%. Los 332 $/año a cuatro")
print(f"     años son mas bien {332*1.35/1.44:.0f} $/año con tu ajuste real.")
