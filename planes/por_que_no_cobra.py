#!/usr/bin/env python3
"""
DE LOS CAMINOS QUE NO COBRAN, ¿QUE REGLA LOS BLOQUEA?

En el horizonte de 2 años, el 36,3% de los caminos no cobra ni quema. Decir
"36% de probabilidad de no cobrar nunca" seria incorrecto por dos motivos:

  1. NUNCA no es 2 AÑOS. La cuenta de Upcomers no tiene limite de tiempo, asi
     que el horizonte relevante es mas largo. Se barre de 1 a 6 años.
  2. Hay TRES condiciones que deben cumplirse a la vez y no bloquean por
     igual. Saber cual aprieta cambia lo que se puede hacer al respecto:
        · 6 dias cerrados con >= +0,5%
        · 1% de beneficio total (250 $)
        · el mejor dia <= 20% del beneficio total

Al final de cada camino que no cobro se mira cual de las tres fallaba.
"""
import numpy as np
import pandas as pd

RNG = np.random.default_rng(20260903)
BLOQUE, SUB = 5, 8
N = 15_000
CUENTA = 25_000.0
DD, DD_DIA = 0.07, 0.04
UMBRAL, MIN_DIAS, MIN_BEN, BEST = 250.0, 6, 0.005, 0.20
REF, FMIN = 0.05, 0.25
COSTE_BP = 3.5


def cargar(vol_objetivo=0.045, w2=0.30):
    A = pd.read_csv("../trend/serie_cfd.csv", index_col=0, parse_dates=True)
    s1 = np.clip(A["s1"].values, -0.008, 0.008)
    s2 = A["s2"].values
    cart = (1 - w2) * s1 + w2 * s2
    lev = vol_objetivo / (cart.std() * np.sqrt(252))
    return (1 - w2) * s1 * lev, w2 * s2 * lev


def bootstrap_par(x1, x2, n_dias, n_caminos):
    nb = int(np.ceil(n_dias / BLOQUE))
    ini = RNG.integers(0, len(x1) - BLOQUE, size=(n_caminos, nb))
    idx = (ini[:, :, None] + np.arange(BLOQUE)[None, None, :]
           ).reshape(n_caminos, -1)[:, :n_dias]
    return x1[idx], x2[idx]


def simular(g1, g2, sd):
    n, dias = g1.shape
    bal = np.full(n, CUENTA); hwm = np.full(n, CUENTA)
    piso = np.full(n, CUENTA * (1 - DD))
    lock = np.zeros(n, bool); vivo = np.ones(n, bool)
    cual = np.zeros(n, int); mejor = np.zeros(n)
    extra = np.zeros(n); npag = np.zeros(n, int)
    paso0 = sd / np.sqrt(SUB)

    for d in range(dias):
        if not vivo.any():
            break
        ini_dia = bal.copy()
        pd_dia = ini_dia * (1 - DD_DIA)
        piso_dia = np.maximum(piso, pd_dia)
        f = np.clip((ini_dia - piso) / CUENTA / REF, FMIN, 1.0)

        eq = ini_dia + ini_dia * g1[:, d] * f
        vivo = vivo & ~(vivo & (eq < piso_dia))
        hwm = np.where(vivo, np.maximum(hwm, eq), hwm)

        act = np.where(vivo)[0]
        eq_fin = eq.copy()
        if act.size:
            fa = f[act]
            b = RNG.normal(0.0, paso0, size=(act.size, SUB)).cumsum(axis=1)
            k = np.arange(1, SUB + 1) / SUB
            br = (b - k[None, :] * b[:, -1:]) * fa[:, None] \
                 + k[None, :] * (g2[act, d] * fa)[:, None]
            cam = eq[act][:, None] + ini_dia[act][:, None] * br
            pico = np.maximum.accumulate(np.maximum(cam, hwm[act][:, None]), 1)
            pa = np.where(lock[act][:, None],
                          np.maximum(piso[act][:, None], CUENTA),
                          np.maximum(piso[act][:, None], pico * (1 - DD)))
            pa = np.maximum(pa, pd_dia[act][:, None])
            vivo[act] = ~(cam < pa).any(1)
            eq_fin[act] = cam[:, -1]
            hwm[act] = np.maximum(hwm[act], pico[:, -1])

        vivo = vivo & ~(vivo & (eq_fin < piso_dia))
        pnl = eq_fin - ini_dia
        bal = np.where(vivo, eq_fin, bal)
        hwm = np.where(vivo, np.maximum(hwm, bal), hwm)
        lock = lock | (vivo & (hwm * (1 - DD) >= CUENTA))
        piso = np.where(vivo & lock, np.maximum(piso, CUENTA),
                        np.where(vivo, np.maximum(piso, hwm * (1 - DD)), piso))
        cual = cual + (vivo & (pnl >= MIN_BEN * CUENTA))
        mejor = np.where(vivo, np.maximum(mejor, pnl), mejor)

        prof = bal - CUENTA
        pide = vivo & (prof >= UMBRAL) & (cual >= MIN_DIAS) \
               & (mejor <= BEST * np.maximum(prof, 1e-9))
        if pide.any():
            extra += np.where(pide, prof, 0.0)
            npag += pide
            bal = np.where(pide, CUENTA, bal)
            hwm = np.where(pide, CUENTA, hwm)
            piso = np.where(pide, CUENTA * (1 - DD), piso)
            lock = np.where(pide, False, lock)
            cual = np.where(pide, 0, cual)
            mejor = np.where(pide, 0.0, mejor)

    return dict(npag=npag, vivo=vivo, cual=cual, mejor=mejor,
                prof=bal - CUENTA, extra=extra)


h1, h2 = cargar()
sd = h2.std()

E = "=" * 84
print(E)
print("¿CUANTO CAMBIA CON EL HORIZONTE?   (la cuenta no tiene limite de tiempo)")
print(E)
print(f"  {'años':>6}{'P(cobra)':>11}{'P(quema)':>11}{'P(ni una ni otra)':>20}"
      f"{'cobros medios':>16}")
print("  " + "-" * 62)
guardado = {}
for anios in (1, 2, 3, 4, 6):
    g1, g2 = bootstrap_par(h1, h2, int(252 * anios), N)
    r = simular(g1, g2, sd)
    guardado[anios] = r
    pc = (r['npag'] > 0).mean()
    pq = (~r['vivo']).mean()
    print(f"  {anios:>6}{pc:>11.1%}{pq:>11.1%}"
          f"{((r['npag'] == 0) & r['vivo']).mean():>19.1%}"
          f"{r['npag'].mean():>16.2f}")

print()
print(E)
print("DE LOS QUE NO COBRAN EN 2 AÑOS, ¿QUE REGLA LES FALTA?")
print(E)
r = guardado[2]
sin = (r['npag'] == 0) & r['vivo']
n_sin = sin.sum()
cual, mejor, prof = r['cual'][sin], r['mejor'][sin], r['prof'][sin]

fd = cual < MIN_DIAS                        # faltan dias cualificados
fb = prof < UMBRAL                          # falta el 1% de beneficio
fc = mejor > BEST * np.maximum(prof, 1e-9)  # el mejor dia pasa del 20%

print(f"  caminos que no cobran: {n_sin:,} de {N:,} ({n_sin/N:.1%})")
print()
print(f"  {'regla que falla':<44}{'% de los que no cobran':>24}")
print("  " + "-" * 68)
print(f"  {'solo los 6 dias al +0,5%':<44}{(fd & ~fb & ~fc).mean():>24.1%}")
print(f"  {'solo el 1% de beneficio total':<44}{(~fd & fb & ~fc).mean():>24.1%}")
print(f"  {'solo la regla del mejor dia (20%)':<44}{(~fd & ~fb & fc).mean():>24.1%}")
print(f"  {'dias + beneficio':<44}{(fd & fb).mean():>24.1%}")
print(f"  {'dias + mejor dia':<44}{(fd & ~fb & fc).mean():>24.1%}")
print(f"  {'beneficio + mejor dia':<44}{(~fd & fb & fc).mean():>24.1%}")
print("  " + "-" * 68)
print(f"  {'les faltan dias cualificados (total)':<44}{fd.mean():>24.1%}")
print(f"  {'les falta beneficio (total)':<44}{fb.mean():>24.1%}")
print(f"  {'les bloquea el mejor dia (total)':<44}{fc.mean():>24.1%}")

print()
print("  Estado medio de los que no cobran a los 2 años:")
print(f"     dias cualificados : {cual.mean():.2f} de {MIN_DIAS} necesarios")
print(f"     beneficio         : {prof.mean():+,.0f} $  (mediana "
      f"{np.median(prof):+,.0f} $)")
print(f"     mejor dia         : {mejor.mean():,.0f} $  ->  necesitarian "
      f"{mejor.mean()*5:,.0f} $ de beneficio para el 20%")

print()
print(E)
print("LOS QUE NO COBRAN, ¿ESTAN EN PERDIDAS?")
print(E)
print(f"  con beneficio positivo : {(prof > 0).mean():>6.1%}")
print(f"  en perdidas            : {(prof <= 0).mean():>6.1%}")
print(f"  beneficio > 250 $      : {(prof >= UMBRAL).mean():>6.1%}")
print()
print("  Es la lectura que importa: no cobrar NO es lo mismo que perder.")
print("  La cuenta sigue viva y el contador de dias cualificados NO se")
print("  reinicia con el tiempo, solo despues de un cobro.")
