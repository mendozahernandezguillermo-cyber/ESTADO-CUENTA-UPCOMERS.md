"""
DOS COMPROBACIONES ANTES DE CONCLUIR.

(1) En atrapado_o_en_cola.py la cola de la lectura B bajaba 789 -> 264 -> 47 $ y
    lo iba a presentar como "la cola se drena". Pero a 15 años el 93,3% de las
    cuentas esta MUERTA, y una cuenta muerta tiene saldo pegado al suelo, o sea
    max(saldo-inicial,0) = 0. Seria exactamente el mismo error de seleccion que
    ya cace con el colchon. Se condiciona en SUPERVIVIENTES.

(2) Queda una via por la que el dinero atrapado podria salir: el 8º cobro, que
    ya no tiene tope. ¿Se llega vivo alguna vez? Y ojo, mi propio modelo da por
    supuesto que al 7º cobro la cuenta se reinicia y el atrapado se BORRA, que
    es otro supuesto mio sin verificar y el mas hostil de los posibles.
"""
import numpy as np

ns = {"__name__": "addendum"}
exec(compile(open("cobros_reales_addendum.py", encoding="utf-8")
             .read().split("# ---8<--- INFORME")[0],
             "cobros_reales_addendum.py", "exec"), ns)
simular2 = ns["simular2"]; mod = ns["mod"]
preparar = mod["preparar"]; CUENTA = mod["CUENTA"]; TOPES = mod["TOPES"]

N = 30_000
E = "=" * 94
x1, x2, _ = preparar(40.0)
sd = x2.std()

print(E)
print("(1) LA COLA, SOLO ENTRE SUPERVIVIENTES  (lectura B)")
print(E)
print(f"  {'horizonte':<12}{'todas':>12}{'vivas':>12}{'% vivas':>10}"
      f"{'cola en vivas':>16}")
print("  " + "-" * 62)
for anios in (4, 8, 15):
    g1, g2 = mod["bootstrap_par"](x1, x2, 252 * anios, N)
    r = simular2(g1, g2, sd, cola=True)
    dentro = np.maximum(r["bal"] - CUENTA, 0.0)
    viva = ~r["quemada"]
    print(f"  {str(anios)+' años':<12}{dentro.mean():>11,.0f}$"
          f"{dentro[viva].mean():>11,.0f}${viva.mean():>10.1%}"
          f"{dentro[viva].mean():>15,.0f}$")
print()
print("  Si la cola entre VIVAS no baja, no se drenaba: se morian.")

print()
print(E)
print("(2) ¿SE LLEGA VIVO AL 8º COBRO, EL TRAMO SIN TOPE?  (lectura A)")
print(E)
print(f"  {'horizonte':<12}{'cobros':>9}{'P(>=8 cobros)':>15}"
       f"{'P(quema)':>11}{'atrapado en vivas':>19}")
print("  " + "-" * 66)
for anios in (4, 8, 15, 25):
    g1, g2 = mod["bootstrap_par"](x1, x2, 252 * anios, N)
    r = simular2(g1, g2, sd, cola=False)
    viva = ~r["quemada"]
    print(f"  {str(anios)+' años':<12}{r['npag'].mean():>9.2f}"
          f"{(r['npag'] >= len(TOPES)+1).mean():>15.1%}"
          f"{r['quemada'].mean():>11.1%}"
          f"{r['atrapado'][viva].mean():>18,.0f}$")

print()
print(E)
print("RESPUESTA A LA PREGUNTA, CON LOS TRES SUPUESTOS QUE LA SOSTIENEN")
print(E)
print("  supuesto 1: el beneficio sobre el tope pasa a ser BASE  (sin verificar)")
print("  supuesto 2: al 7º cobro la cuenta se reinicia y el atrapado se borra")
print("              (sin verificar, y es el supuesto mas hostil posible)")
print("  supuesto 3: no hay ninguna via de retirada extraordinaria")
print("              (sin verificar)")
print()
print("  Si los tres son ciertos: NO SALE NUNCA. Su unica funcion es servir de")
print("  colchon contra el suelo del trailing, y desaparece con la cuenta.")
print("  Si el supuesto 1 es falso (lectura B): SI SALE, a plazos, y de hecho")
print("  cobras casi el doble a 4 años, pero te quedas sin colchon y la")
print("  probabilidad de quemar la cuenta se multiplica por 3,6.")
