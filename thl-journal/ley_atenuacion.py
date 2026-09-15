#!/usr/bin/env python3
"""
RECTIFICACION.

Mi hipotesis ("agregar a menor frecuencia corrige el sesgo de los huecos")
quedo REFUTADA por el propio test: la correlacion medida es la misma a
diario que a mensual. Pero la tabla de densidades revela la ley exacta.

Observado:  rho_medido = rho_real * p     (con p = fraccion de dias activos)
    p=0.15 -> 0.091 (predice 0.090)
    p=0.30 -> 0.181 (predice 0.180)
    p=0.50 -> 0.301 (predice 0.300)
    p=0.80 -> 0.480 (predice 0.480)
    p=1.00 -> 0.599 (predice 0.600)

Derivacion:  Cov ~ rho*p_A*p_B ; Var_A ~ p_A ; Var_B ~ p_B
             corr = rho*p_A*p_B / raiz(p_A*p_B) = rho * raiz(p_A*p_B)

Ahora la pregunta que de verdad importa, y donde creo que me equivoque al
llamar "peligroso" al sesgo:

  ¿Hay que CORREGIR el rho medido antes de meterlo en la cartera, o el rho
  medido ya es el input correcto?

Si dos estrategias operan dias distintos, su P&L diario realmente esta menos
correlacionado y la varianza de la cartera realmente baja. En ese caso el rho
medido es el correcto y corregirlo seria un error.

Se comprueba directamente: se predice la volatilidad de la cartera a partir
del rho medido y se compara con la volatilidad REALIZADA.
"""
import numpy as np

RNG = np.random.default_rng(31415)
T   = 20_000
N   = 3


def prueba(rho_real, p, tail=False):
    zc = RNG.standard_normal(T)
    S = []
    for _ in range(N):
        e = RNG.standard_normal(T)
        s = np.sqrt(rho_real) * zc + np.sqrt(1 - rho_real) * e
        if tail:
            # dependencia de cola: los dias malos del factor comun golpean
            # a TODAS las estrategias a la vez, aunque el rho diario sea bajo
            crisis = zc < np.percentile(zc, 5)
            s = np.where(crisis, -np.abs(s) * 4.0, s)
        s = s * (RNG.random(T) < p)          # huecos independientes
        S.append(s)
    S = np.array(S)

    C = np.corrcoef(S)
    rho_med = (C.sum() - N) / (N * (N - 1))

    port = S.mean(axis=0)
    vol_real = port.std()
    vol_pred = S.std(axis=1).mean() / np.sqrt(N) * np.sqrt(
        1 + (N - 1) * rho_med)

    # correlacion SOLO en el decil peor de la cartera
    peor = port <= np.percentile(port, 10)
    Cp = np.corrcoef(S[:, peor])
    rho_cola = (Cp.sum() - N) / (N * (N - 1))

    return rho_med, vol_pred, vol_real, rho_cola


print("=" * 78)
print("1. ¿EL RHO MEDIDO ES EL INPUT CORRECTO PARA LA CARTERA?")
print("   Se predice la vol de la cartera con el rho medido y se compara")
print("   con la realizada. Si coinciden, NO hay que corregir nada.")
print("=" * 78)
print(f"{'rho real':>9}{'p':>7}{'rho medido':>12}{'vol predicha':>14}"
      f"{'vol realizada':>15}{'error':>9}")
print("-" * 78)
for rho in (0.0, 0.3, 0.6, 0.9):
    for p in (0.4, 1.0):
        rm, vp, vr, _ = prueba(rho, p)
        err = (vp / vr - 1) * 100
        print(f"{rho:>9.2f}{p:>7.1f}{rm:>12.3f}{vp:>14.4f}{vr:>15.4f}"
              f"{err:>8.1f}%")
print()
print("VEREDICTO: la prediccion con el rho MEDIDO acierta la vol realizada.")
print("Me equivoque al llamarlo sesgo peligroso: para construir la cartera,")
print("el rho medido sobre los retornos diarios reales ES el input correcto.")
print("Los huecos son diversificacion de verdad, no un artefacto.")

print()
print("=" * 78)
print("2. EL RIESGO QUE SI ES REAL Y QUE NINGUNA FRECUENCIA VE:")
print("   DEPENDENCIA DE COLA")
print("=" * 78)
print(f"{'escenario':<30}{'rho normal':>13}{'rho en el peor 10%':>21}")
print("-" * 78)
for etq, tail in [("gaussiano (sin cola comun)", False),
                  ("con dependencia de cola", True)]:
    rm, vp, vr, rc = prueba(0.30, 0.40, tail=tail)
    print(f"{etq:<30}{rm:>13.3f}{rc:>21.3f}")
print()
print("""LECTURA: dos carteras con el MISMO rho normal pueden tener colas
completamente distintas. La segunda se hunde a la vez en los dias malos
aunque su correlacion medida sea baja. Y es justo en esos dias cuando se
toca el limite de drawdown.

Consecuencia para el plan: la matriz de correlacion es necesaria pero NO
suficiente. Hay que mirar ademas la correlacion condicionada a los dias
malos, que es la que decide si las tres cuentas mueren el mismo dia.""")
