#!/usr/bin/env python3
"""
¿HAY QUE BUSCAR UN DARWIN CON SHARPE 2?

El error de fondo: el Sharpe que VES no es el Sharpe que TIENE. Si eliges el
mejor de un monton de candidatos, lo que estas midiendo es sobre todo suerte.

Tres calculos:

  1. ENCOGIMIENTO (shrinkage). Dado un Sharpe observado y un historial, ¿cual
     es la mejor estimacion del Sharpe verdadero? Formula empirico-bayesiana:

         E[s_real | s_obs] = mu + k*(s_obs - mu),   k = tau^2/(tau^2 + SE^2)
         SE(s_obs) = raiz((1 + s_obs^2/2)/T)      T en anos

  2. SELECCION. Se simula un universo de darwins con Sharpe verdadero
     repartido, se observa cada uno con ruido, se coge el mejor y se mira
     que Sharpe verdadero tenia realmente.

  3. ¿Que hace falta para CREER que s_real >= 1?

tau = dispersion del Sharpe verdadero entre darwins. No es observable
directamente; se prueban tres valores, de generoso a muy generoso.
"""
import numpy as np

RNG = np.random.default_rng(20260829)


def se_sharpe(s, T):
    return np.sqrt((1.0 + s * s / 2.0) / T)


# ===================================================== 1. ENCOGIMIENTO
print("=" * 78)
print("1. SI VES UN SHARPE DE 2,0 ¿QUE SHARPE TIENE DE VERDAD?")
print("   (media del universo mu=0,0; k = factor de encogimiento)")
print("=" * 78)
S_OBS = 2.0
print(f"{'historial':>11}{'SE(s_obs)':>11}" +
      "".join(f"{'tau='+str(t):>16}" for t in (0.3, 0.5, 0.8)))
print("-" * 78)
for meses in (6, 12, 24, 36, 60, 120):
    T = meses / 12.0
    se = se_sharpe(S_OBS, T)
    fila = ""
    for tau in (0.3, 0.5, 0.8):
        k = tau ** 2 / (tau ** 2 + se ** 2)
        est = 0.0 + k * (S_OBS - 0.0)
        fila += f"{('k=%.2f -> %.2f' % (k, est)):>16}"
    print(f"{str(meses)+' meses':>11}{se:>11.2f}{fila}")
print()
print("LECTURA: con 12 meses y una dispersion realista (tau=0,3), un Sharpe")
print("observado de 2,0 encoge a ~0,2. Practicamente todo era ruido.")

# ======================================================= 2. SELECCION
print("\n" + "=" * 78)
print("2. ELIGES EL MEJOR DE N CANDIDATOS. ¿QUE SHARPE VERDADERO TIENE?")
print("=" * 78)


def seleccion(n_darwins, meses, tau, mu=0.0, top=1, rep=3000):
    T = meses / 12.0
    obs_sel, real_sel = [], []
    for _ in range(rep):
        real = RNG.normal(mu, tau, n_darwins)
        obs = real + RNG.normal(0, se_sharpe(np.abs(real) + 0.5, T),
                                n_darwins)
        idx = np.argsort(obs)[-top:]
        obs_sel.append(obs[idx].mean())
        real_sel.append(real[idx].mean())
    return np.mean(obs_sel), np.mean(real_sel)


for tau in (0.3, 0.5):
    print(f"\n  dispersion del universo tau = {tau}")
    print(f"{'N candidatos':>14}" +
          "".join(f"{str(m)+'m':>22}" for m in (12, 24, 60)))
    print(f"{'':>14}" + "".join(f"{'obs -> real':>22}" for _ in range(3)))
    print("  " + "-" * 74)
    for N in (50, 200, 1000):
        fila = ""
        for meses in (12, 24, 60):
            o, r = seleccion(N, meses, tau)
            fila += f"{('%.2f -> %.2f' % (o, r)):>22}"
        print(f"{N:>14}{fila}")

print()
print("LECTURA: el numero de la izquierda es lo que te ensena el screener.")
print("El de la derecha es lo que te llevas. La brecha crece con N y se")
print("cierra solo con historial largo.")

# ============================================ 3. ¿CUANDO CREER s>=1?
print("\n" + "=" * 78)
print("3. ¿QUE HISTORIAL HACE FALTA PARA CREER QUE s_real >= 1,0?")
print("   (probabilidad posterior de que el Sharpe verdadero supere 1,0,")
print("    dado lo observado, con tau=0,5 y mu=0)")
print("=" * 78)
print(f"{'s observado':>12}" +
      "".join(f"{str(m)+' meses':>13}" for m in (12, 24, 36, 60, 120)))
print("-" * 78)
from math import erf, sqrt
for s_obs in (1.0, 1.5, 2.0, 2.5, 3.0):
    fila = ""
    for meses in (12, 24, 36, 60, 120):
        T = meses / 12.0
        se = se_sharpe(s_obs, T)
        tau = 0.5
        k = tau ** 2 / (tau ** 2 + se ** 2)
        post_mu = k * s_obs
        post_sd = sqrt(k) * se
        z = (post_mu - 1.0) / post_sd
        p = 0.5 * (1 + erf(z / sqrt(2)))
        fila += f"{p:>12.1%} "
    print(f"{s_obs:>12.1f}{fila}")

print()
print("=" * 78)
print("CONSECUENCIA PARA EL CRITERIO DE BUSQUEDA")
print("=" * 78)
print("""El Sharpe es lo MENOS verificable de todo lo que puedes mirar, y es
justo lo que el screener te pone delante. Ordenado por cuanto se puede
confiar en cada filtro con un historial corto:

  1. MECANISMO (grid/martingala).  El detector mide COMO opera, no cuanto
     gana. Funciona con historial corto porque no depende de la muestra de
     retornos. Es binario y decisivo. -> Filtro numero uno.

  2. CORRELACION con los demas candidatos. Medible, y su error estandar
     baja con el numero de bloques, no con la calidad del trader.

  3. LONGEVIDAD. Sobrevivir muchos anos es en si mismo informativo, y no
     se puede fingir.

  4. SHARPE. El mas inflado por seleccion y el que menos aporta: en el
     marco general, incluso s=0 daba EV positivo en instant funding. El
     Sharpe decide la FIABILIDAD y cuantas cuentas necesitas, no el signo.

Buscar "uno con Sharpe 2" es ordenar por la columna mas ruidosa de la tabla.""")
