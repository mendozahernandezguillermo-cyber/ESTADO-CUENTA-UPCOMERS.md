"""
¿EL BENEFICIO NO RETIRABLE SALE ALGUN DIA O NO SALE NUNCA?

Confesion primero: en la Fase 14 escribi "atrapado para siempre" como si fuera
un hecho verificado. NO LO ES. Es MI LECTURA de una frase del documento de
Upcomers, y el texto fuente no esta guardado en el repositorio. Todo el
resultado de la Fase 14 cuelga de una sola linea de codigo:

    ref_seg[idx] = bal[idx]      <-- lectura A
    ref_seg[idx] = CUENTA        <-- lectura B

  LECTURA A: "cada cobro se calcula sobre el beneficio del segmento en curso,
  desde el cobro anterior". El saldo tras retirar pasa a ser la nueva base, asi
  que lo que quedo por encima del tope se convierte en BASE y ya no es
  beneficio nunca mas. ATRAPADO PARA SIEMPRE.

  LECTURA B: el tope limita el RITMO de salida, no el total. El beneficio
  acumulado sobre el saldo inicial sigue siendo cobrable en ciclos posteriores.
  EN COLA. Sale, pero a plazos de 250, 500, 750, 1.000...

Las dos son lecturas defendibles del mismo texto. Se miden las dos, porque la
diferencia decide no solo el EV de Upcomers sino tambien si conviene FTMO.
"""
import numpy as np

ns = {"__name__": "addendum"}
exec(compile(open("cobros_reales_addendum.py", encoding="utf-8")
             .read().split("# ---8<--- INFORME")[0],
             "cobros_reales_addendum.py", "exec"), ns)
simular2 = ns["simular2"]; mod = ns["mod"]
preparar = mod["preparar"]; CUENTA = mod["CUENTA"]

N = 30_000
E = "=" * 94
x1, x2, _ = preparar(40.0)
sd = x2.std()

print(E)
print("LAS DOS LECTURAS, LADO A LADO  (TP 40, vol 4,5%)")
print(E)
print(f"  {'horizonte':<11}{'lectura':<26}{'recibido':>11}{'en la cuenta':>14}"
      f"{'cobros':>8}{'P(quema)':>10}{'saldo final':>13}")
print("  " + "-" * 88)
guarda = {}
for anios in (4, 8, 15):
    g1, g2 = mod["bootstrap_par"](x1, x2, 252 * anios, N)
    for cola, etiq in ((False, "A · atrapado (Fase 14)"),
                       (True, "B · en cola, sale a plazos")):
        r = simular2(g1, g2, sd, cola=cola)
        guarda[(anios, cola)] = r
        dentro = np.maximum(r["bal"] - CUENTA, 0.0)
        print(f"  {(str(anios)+' años') if not cola else '':<11}{etiq:<26}"
              f"{r['recibido'].mean():>10,.0f}${dentro.mean():>13,.0f}$"
              f"{r['npag'].mean():>8.2f}{r['quemada'].mean():>10.1%}"
              f"{r['bal'].mean():>12,.0f}$")
    print()

a4 = guarda[(4, False)]["recibido"].mean()
b4 = guarda[(4, True)]["recibido"].mean()
print(f"  A 4 años la lectura B paga {b4-a4:+,.0f} $ mas que la A "
      f"({b4/max(a4,1e-9):.2f}x)")
a15 = guarda[(15, False)]["recibido"].mean()
b15 = guarda[(15, True)]["recibido"].mean()
print(f"  A 15 años la diferencia es {b15-a15:+,.0f} $ ({b15/max(a15,1e-9):.2f}x)")

print()
print(E)
print("¿SE DRENA LA COLA?  (lectura B, cuanto queda dentro sin cobrar)")
print(E)
print(f"  {'horizonte':<12}{'dentro sin cobrar':>20}{'% del maximo':>15}")
print("  " + "-" * 48)
mx = max(np.maximum(guarda[(a, True)]["bal"] - CUENTA, 0).mean()
         for a in (4, 8, 15))
for anios in (4, 8, 15):
    d = np.maximum(guarda[(anios, True)]["bal"] - CUENTA, 0.0).mean()
    print(f"  {str(anios)+' años':<12}{d:>19,.0f}${d/mx:>14.0%}")
print()
print("  Si la cifra NO baja con el horizonte, la cola no se drena: el sistema")
print("  genera beneficio mas rapido de lo que los topes lo dejan salir, y")
print("  entonces incluso en la lectura B hay dinero que en la practica no sale.")

print()
print(E)
print("EL TEST QUE LO RESUELVE SIN PREGUNTAR A NADIE")
print(E)
print("  Las dos lecturas dan lo MISMO en el primer cobro y se separan en el")
print("  SEGUNDO. Concretamente, en el importe maximo que te deja pedir:")
print()
seg1 = 1447.0            # beneficio tipico del segmento al primer cobro
tope1, tope2 = 250.0, 500.0
sacado1 = tope1 / 0.90
print(f"     beneficio del segmento al pedir el 1er cobro : {seg1:>8,.0f} $")
print(f"     cobras el tope del tramo 1                   : {tope1:>8,.0f} $")
print(f"     sale del saldo                               : {sacado1:>8,.1f} $")
print(f"     queda por encima del inicial                 : "
      f"{seg1-sacado1:>8,.0f} $")
print()
print(f"  LECTURA A: el 2º cobro exige generar 1% NUEVO desde cero y el panel")
print(f"             te ofrecera como maximo el 90% de ESE beneficio nuevo.")
print(f"  LECTURA B: nada mas cerrar el 1er cobro ya tienes "
      f"{seg1-sacado1:,.0f} $ sobre el")
print(f"             inicial, o sea que en cuanto pasen los 6 dias y la regla")
print(f"             del mejor dia, el panel te ofrecera el tope 2 COMPLETO")
print(f"             ({tope2:,.0f} $) sin necesidad de generar nada nuevo.")
print()
print("  O sea: mira el importe que el panel te ofrece justo despues del primer")
print("  cobro. Si es ~0, es la lectura A. Si ya es el tope del tramo 2, es la B.")
print("  Se resuelve solo, gratis, y sin depender de que soporte conteste.")
