"""
¿DONDE GIRA LA CURVA DE VOL EN FTMO, Y ES CREIBLE?

En ftmo_pipeline.py el EV crecia de forma MONOTONA hasta el borde del barrido
(17%, 1.808 $/año). Cuando un modelo dice "arriesga todo lo que puedas" no ha
encontrado un optimo: ha llegado al limite de sus propios supuestos. La razon
es estructural y real: la cuota de 291 $ es una OPCION, perdida acotada y
ganancia sin tope, asi que con recompra infinita el EV sube con la vol.

Tres cosas que hay que mirar antes de creerselo:
  1. ¿gira la curva si se extiende el barrido? Si no gira, el modelo es
     degenerado y hay que decirlo, no publicar el argmax.
  2. FTMO recomienda 1-1,5% de riesgo por operacion y dice explicitamente que
     vigila patrones de comportamiento. A vol 10% vamos a 3,3% por evento y a
     vol 17% a 5,6%. Eso no es una restriccion dura, es una discrecional, que
     es peor: no te para, te deniega el cobro despues.
  3. El punto de comparacion honesto con Upcomers es a MISMO RIESGO, porque la
     unica razon por la que FTMO admite mas vol es que su suelo es 10% estatico
     en vez de 7% trailing.

Y la pregunta que decide: ¿que probabilidad de que FTMO invoque la clausula de
gap trading contra la #1 hace que FTMO deje de convenir?
"""
import numpy as np

ns = {"__name__": "pipe"}
exec(compile(open("ftmo_pipeline.py", encoding="utf-8")
             .read().split('E = "=" * 96')[0], "ftmo_pipeline.py", "exec"), ns)
pipeline = ns["pipeline"]; caminos = ns["caminos"]
preparar = ns["preparar"]; CUOTA = ns["CUOTA"]
N, ANIOS = 20_000, 3

E = "=" * 96
print(E)
print("BARRIDO EXTENDIDO: ¿gira la curva?")
print(E)
print(f"  {'vol':>6}{'riesgo/ev':>11}{'P(fondea)':>11}{'cuotas':>9}{'gasto':>9}"
      f"{'cobrado':>10}{'EV neto':>10}{'EV/año':>9}")
print("  " + "-" * 76)
curva = []
for vol in (0.10, 0.17, 0.25, 0.35, 0.50):
    x1, x2, rg = preparar(40.0, w2=0.30, vol=vol)
    g1, g2 = caminos(x1, x2, 252 * ANIOS, N)
    r = pipeline(g1, g2, x2.std(), 252 * ANIOS)
    ev = r["neto"].mean()
    curva.append((vol, ev))
    print(f"  {vol:>6.1%}{rg:>10.2f}%{r['fondeo'].mean():>11.1%}"
          f"{r['pagado'].mean()/CUOTA:>9.2f}{r['pagado'].mean():>8,.0f}$"
          f"{r['recibido'].mean():>9,.0f}${ev:>9,.0f}${ev/ANIOS:>8,.0f}$")

giro = max(range(len(curva)), key=lambda i: curva[i][1])
print()
if giro == len(curva) - 1:
    print("  NO GIRA. El optimo esta fuera del barrido y el modelo es degenerado:")
    print("  con recompra ilimitada la cuota es una opcion barata y conviene")
    print("  siempre subir la vol. Ese resultado NO se puede usar como consejo.")
else:
    print(f"  Gira en vol {curva[giro][0]:.1%} con {curva[giro][1]/ANIOS:,.0f} $/año.")

print()
print(E)
print("COMPARACION A MISMO RIESGO (la unica honesta)")
print(E)
print(f"  {'vehiculo':<46}{'vol':>7}{'riesgo/ev':>11}{'EV/año':>10}")
print("  " + "-" * 74)
x1, x2, rg = preparar(40.0, w2=0.30, vol=0.045)
g1, g2 = caminos(x1, x2, 252 * ANIOS, N)
r = pipeline(g1, g2, x2.std(), 252 * ANIOS)
print(f"  {'Upcomers Vanguard · 7% trailing':<46}{'4,5%':>7}{rg:>10.2f}%{269:>9,.0f}$")
print(f"  {'FTMO 2-Step · 10% estatico':<46}{'4,5%':>7}{rg:>10.2f}%"
      f"{r['neto'].mean()/ANIOS:>9,.0f}$")
print()
print("  A mismo riesgo FTMO PIERDE: hay que escalar +10% y +5% antes de cobrar")
print("  un dolar, y a 4,5% de vol eso son ~520 dias de mercado.")
print("  FTMO solo gana si se sube la vol, y solo se puede subir la vol porque")
print("  su suelo es estatico. La ventaja no es del vehiculo: es del permiso.")

print()
print(E)
print("¿QUE RIESGO DE LA CLAUSULA DE GAP TRADING HACE QUE FTMO DEJE DE CONVENIR?")
print(E)
UP = 269.0
for vol in (0.045, 0.08, 0.10):
    x1a, x2a, _ = preparar(40.0, w2=0.30, vol=vol)
    g1, g2 = caminos(x1a, x2a, 252 * ANIOS, N)
    con = pipeline(g1, g2, x2a.std(), 252 * ANIOS)["neto"].mean() / ANIOS
    x1b, x2b, _ = preparar(40.0, w2=1.00, vol=vol)
    g1, g2 = caminos(x1b, x2b, 252 * ANIOS, N)
    sin = pipeline(g1, g2, x2b.std(), 252 * ANIOS)["neto"].mean() / ANIOS
    if con > sin:
        p = (con - UP) / (con - sin)
        txt = (f"p* = {p:.0%}" if 0 <= p <= 1
               else ("nunca conviene" if p < 0 else "conviene siempre"))
    else:
        txt = "n/a"
    print(f"  vol {vol:>5.1%}   con la #1 {con:>7,.0f}$/año   "
          f"sin la #1 {sin:>7,.0f}$/año   Upcomers {UP:,.0f}$   ->  {txt}")
print()
print("  p* = probabilidad de que FTMO invalide la #1 que iguala los dos vehiculos.")
print("  Por debajo de p*, FTMO conviene. Por encima, no.")
