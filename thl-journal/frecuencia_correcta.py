#!/usr/bin/env python3
"""
¿A QUE FRECUENCIA HAY QUE MEDIR LA CORRELACION?

El problema detectado: con huecos (dias sin operar) la correlacion DIARIA se
sesga hacia cero y sobreestima la diversificacion.

Dos interpretaciones posibles, y solo una es correcta para nuestro fin:

  (a) Si A opera lunes y B opera martes, su P&L diario es de verdad
      independiente y la diversificacion es REAL.
  (b) Pero el limite de drawdown actua sobre la trayectoria ACUMULADA. Lo que
      importa no es si coinciden el mismo dia, sino si van a la vez a lo largo
      de semanas. Dos variantes de la misma idea con horarios distintos se
      hunden juntas aunque su correlacion diaria sea baja.

(b) es lo que decide la ruina, asi que la frecuencia de medida debe ser lo
bastante baja para agregar por encima de los huecos. Aqui se busca cual.
"""
import numpy as np
import pandas as pd

RNG = np.random.default_rng(20260829)
T   = 1260          # 5 anos de dias de mercado
REP = 400           # repeticiones por escenario


def medir(rho, p_activo, bloque, rep=REP):
    """Correlacion medida agregando en bloques de 'bloque' dias."""
    out = []
    for _ in range(rep):
        zc = RNG.standard_normal(T)
        a  = np.sqrt(rho) * zc + np.sqrt(1 - rho) * RNG.standard_normal(T)
        b  = np.sqrt(rho) * zc + np.sqrt(1 - rho) * RNG.standard_normal(T)
        # huecos independientes: cada uno opera solo p_activo de los dias
        a = a * (RNG.random(T) < p_activo)
        b = b * (RNG.random(T) < p_activo)
        n = (T // bloque) * bloque
        A = a[:n].reshape(-1, bloque).sum(1)
        B = b[:n].reshape(-1, bloque).sum(1)
        if A.std() > 0 and B.std() > 0:
            out.append(np.corrcoef(A, B)[0, 1])
    return float(np.mean(out)), float(np.std(out))


print("=" * 78)
print("CORRELACION MEDIDA SEGUN LA FRECUENCIA DE AGREGACION")
print("40% de dias activos (el caso tipico de un darwin intradia)")
print("=" * 78)
BLOQUES = [(1, "diario"), (5, "semanal"), (10, "bisemanal"),
           (21, "mensual"), (63, "trimestral")]
print(f"{'rho real':>9}" + "".join("%14s" % b[1] for b in BLOQUES))
print("-" * 78)
for rho in (0.0, 0.3, 0.6, 0.9):
    fila = []
    for bl, _ in BLOQUES:
        m, s = medir(rho, 0.40, bl)
        fila.append("%6.3f±%.02f" % (m, s))
    print(f"{rho:>9.2f}" + "".join("%14s" % v for v in fila))

print()
print("=" * 78)
print("EFECTO DE LA DENSIDAD DE OPERACION  (rho real = 0,60)")
print("=" * 78)
print(f"{'% dias activos':>15}" + "".join("%14s" % b[1] for b in BLOQUES))
print("-" * 78)
for p in (0.15, 0.30, 0.50, 0.80, 1.00):
    fila = []
    for bl, _ in BLOQUES:
        m, s = medir(0.60, p, bl)
        fila.append("%6.3f" % m)
    print(f"{p:>14.0%} " + "".join("%14s" % v for v in fila))

print()
print("=" * 78)
print("COSTE EN PRECISION: cuantos bloques quedan para estimar")
print("=" * 78)
print(f"{'frecuencia':>14}{'bloques en 5 anos':>20}{'SE de rho':>12}")
print("-" * 78)
for bl, nom in BLOQUES:
    nb = T // bl
    se = 1.0 / np.sqrt(max(1, nb - 3))
    print(f"{nom:>14}{nb:>20d}{se:>12.3f}")

print()
print("=" * 78)
print("CONCLUSION")
print("=" * 78)
print("""*** ATENCION: la hipotesis de este script quedo REFUTADA por sus propios
*** numeros. Ver ley_atenuacion.py para la rectificacion.

Lo que muestran las tablas de arriba:

  1. Agregar NO corrige nada. La correlacion medida es practicamente la
     misma a diario (0,237) que a mensual (0,231) para rho real 0,60.
     Mi hipotesis de partida era falsa.

  2. La atenuacion sigue una ley exacta:  rho_medido = rho_real * p,
     con p la fraccion de dias activos. Verificado a tres decimales en la
     tabla de densidades. En general: rho_medido = rho_real*raiz(p_A*p_B).

  3. Y lo mas importante: NO hay que corregirla. En ley_atenuacion.py se
     comprueba que la volatilidad de cartera predicha con el rho MEDIDO
     acierta la realizada con error -0,0%. Los huecos son diversificacion
     de verdad, no un artefacto. Llamarlo "sesgo peligroso" fue un error mio.

Lo unico que sigue en pie de este script es el coste en precision: con 12
meses solo hay 12 bloques mensuales, SE(rho) ~ 0,33, y no se puede
distinguir rho=0,3 de rho=0,6 con un ano de datos.""")
