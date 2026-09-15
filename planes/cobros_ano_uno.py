"""
¿CUANTO SE ESPERA GANAR EN EL AÑO 1, EN DOLARES?

Aviso sobre las cifras anteriores: los "168 $/año" eran el neto TOTAL a dos años
dividido por dos. Eso NO es el EV del primer año. El primer año es peor que la
media por tres razones acumulativas:

  1. la cuota de 50 $ se paga una sola vez, al principio, y cae toda sobre el año 1;
  2. el primer cobro tarda una mediana de ~197 dias de mercado (~9,4 meses),
     asi que buena parte de los caminos termina el año 1 sin haber cobrado nada;
  3. el tope del primer tramo es el mas bajo de la escala (250 $), y los tramos
     altos (1.250, 1.560, 1.875, libre) caen casi todos fuera del año 1.

Se mide el horizonte de 252 dias directamente, y se reporta la DISTRIBUCION,
no solo la media: con estos numeros la media y la mediana no se parecen nada.
"""
import numpy as np

ns = {"__name__": "addendum"}
exec(compile(open("cobros_reales_addendum.py", encoding="utf-8")
             .read().split("# ---8<--- INFORME")[0],
             "cobros_reales_addendum.py", "exec"), ns)
simular2 = ns["simular2"]; preparar = ns["preparar"]; mod = ns["mod"]
CUOTA = mod["CUOTA"]

N = 20_000
E = "=" * 92

print(E)
print("AÑO 1 AISLADO  (252 dias de mercado, w2 30%, vol 4,5%)")
print(E)
print(f"  {'TP':>5}{'P(cobro)':>10}{'EV neto':>10}{'mediana':>10}{'p25':>8}"
      f"{'p75':>8}{'p90':>9}{'cobros':>8}{'atrapado':>10}{'P(quema)':>10}")
print("  " + "-" * 88)
guarda = {}
for tp in (40.0, 50.0):
    b1, b2, _ = preparar(tp)
    g1, g2 = mod["bootstrap_par"](b1, b2, 252, N)
    r = simular2(g1, g2, b2.std())
    guarda[tp] = r
    n = r["neto"]
    print(f"  {tp:>4.0f}{(r['npag']>0).mean():>10.1%}{n.mean():>9,.0f}$"
          f"{np.median(n):>9,.0f}${np.percentile(n,25):>7,.0f}$"
          f"{np.percentile(n,75):>7,.0f}${np.percentile(n,90):>8,.0f}$"
          f"{r['npag'].mean():>8.2f}{r['atrapado'].mean():>9,.0f}$"
          f"{r['quemada'].mean():>10.1%}")

r = guarda[40.0]
n = r["neto"]
print()
print(E)
print("DESGLOSE DEL AÑO 1 CON TP 40 bp")
print(E)
print(f"  cuota pagada                        : {-CUOTA:>10,.0f} $")
print(f"  cobros brutos recibidos (media)     : {r['recibido'].mean():>10,.0f} $")
print(f"  ---------------------------------------------------")
print(f"  EV NETO DEL AÑO 1                   : {n.mean():>10,.0f} $")
print()
print(f"  probabilidad de acabar el año 1 en perdida (-50 $) : "
      f"{(n < 0).mean():>6.1%}")
print(f"  probabilidad de cobrar al menos una vez            : "
      f"{(r['npag']>0).mean():>6.1%}")
print(f"  probabilidad de cobrar dos o mas veces             : "
      f"{(r['npag']>1).mean():>6.1%}")
print(f"  numero de cobros mas probable (moda)               : "
      f"{np.bincount(r['npag']).argmax():>6d}")
print()
print("  reparto del resultado del año 1:")
for lo, hi, etiq in ((-1e9, 0, "en perdida (no cobro)"),
                     (0, 200, "0 a 200 $"),
                     (200, 400, "200 a 400 $"),
                     (400, 700, "400 a 700 $"),
                     (700, 1e9, "mas de 700 $")):
    m = (n >= lo) & (n < hi)
    print(f"     {etiq:<24}{m.mean():>7.1%}")

print()
print(E)
print("POR QUE EL AÑO 2 ES MEJOR QUE EL AÑO 1")
print(E)
b1, b2, _ = preparar(40.0)
prev = 0.0
for anios, etiq in ((1, "año 1"), (2, "años 1-2"), (3, "años 1-3")):
    g1, g2 = mod["bootstrap_par"](b1, b2, 252 * anios, N)
    rr = simular2(g1, g2, b2.std())
    tot = rr["neto"].mean()
    print(f"  {etiq:<10} acumulado {tot:>8,.0f} $   "
          f"del periodo {tot-prev:>8,.0f} $   "
          f"cobros {rr['npag'].mean():>4.2f}   "
          f"P(quema) {rr['quemada'].mean():>5.1%}")
    prev = tot
print()
print("  El EV por año CRECE con el tiempo: la cuota ya esta pagada, los seis")
print("  dias cualificados ya estan hechos y los topes van subiendo de tramo.")
print("  Presentar el numero de largo plazo como si fuera el del año 1 seria")
print("  el mismo tipo de error optimista que tenia el modelo viejo.")
