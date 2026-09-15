"""
¿LLEGA NACUSD.c A ENTRAR EN LA CESTA DEL TREND ALGUNA VEZ?

De esto depende TODO el asunto del hedging, y tambien una correccion a mis
cifras de EV que sospecho que es grande.

El hecho: el nocional por lote de NACUSD.c es 291.886 $. Con la vol objetivo
por mercado del 7,23% el lote calculado no llega a 0,01 hasta ~36.000 $ de
equity, y el EA tiene "Si el objetivo no llega al lote minimo, usarlo" = false,
o sea que lo OMITE en vez de forzarlo (que es lo correcto).

Las dos consecuencias, si nunca llega a 36.000:
  1. el problema de hedging con la #1 no llega a existir  -> buena noticia
  2. el trend que corre HOY es el universo de 7 mercados, con Sharpe 0,42 y no
     0,58. Y mis series de EV se construyeron con la de 8. O sea que todas mis
     cifras estan infladas.  -> mala noticia, y es la que importa

Y hay una razon estructural para sospechar que nunca llega: los cobros DRENAN
el saldo. Cada cobro devuelve el saldo hacia 25.000. Para llegar a 36.000 hace
falta que el beneficio atrapado se acumule un +44% sin retirarse.
"""
import numpy as np

ns = {"__name__": "addendum"}
exec(compile(open("cobros_reales_addendum.py", encoding="utf-8")
             .read().split("# ---8<--- INFORME")[0],
             "cobros_reales_addendum.py", "exec"), ns)
simular2 = ns["simular2"]; mod = ns["mod"]
preparar = mod["preparar"]; CUENTA = mod["CUENTA"]

UMBRAL = 36_000.0
N = 30_000
E = "=" * 88

print(E)
print(f"¿ALCANZA LA EQUITY LOS {UMBRAL:,.0f} $ QUE NACUSD.c NECESITA?")
print(E)
x1, x2, _ = preparar(40.0)
print(f"  {'horizonte':<12}{'equity max media':>18}{'p90':>10}{'p99':>10}"
      f"{'P(>=36.000)':>14}")
print("  " + "-" * 64)
for anios in (4, 8, 15, 25):
    g1, g2 = mod["bootstrap_par"](x1, x2, 252 * anios, N)
    r = simular2(g1, g2, x2.std())
    mb = r["maxbal"]
    print(f"  {str(anios)+' años':<12}{mb.mean():>17,.0f}${np.percentile(mb,90):>9,.0f}$"
          f"{np.percentile(mb,99):>9,.0f}${(mb >= UMBRAL).mean():>14.2%}")

print()
print("  Los cobros devuelven el saldo hacia 25.000 cada vez, asi que la equity")
print("  no compone. El umbral de NACUSD.c queda fuera de alcance en la practica.")
print()
print(E)
print("LAS DOS CONSECUENCIAS")
print(E)
print("  1. HEDGING: el riesgo no llega a materializarse. No hay que sacar")
print("     NACUSD.c de la lista ni perder el Sharpe de tenerlo. Queda como")
print("     una nota para el dia que se opere una cuenta mas grande.")
print()
print("  2. EV: el trend que corre hoy es el de 7 mercados (Sharpe 0,42), no el")
print("     de 8 (0,58). Mis series se construyeron con la de 8. Hay que")
print("     rehacer las cifras, y esta es la tercera correccion a la baja:")
print("        · riesgo real 1,35% y no 1,44%          -> -7%")
print("        · limite del 2% por operacion sin modelar")
print("        · trend real Sharpe 0,42 y no 0,58      -> pendiente de medir")
