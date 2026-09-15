#!/usr/bin/env python3
"""
¿QUE SIGNIFICA EXACTAMENTE EL "+3.206"?

No es anual, no es de dos cuentas: es el VALOR ESPERADO de UNA cuenta de 50K
sobre un horizonte de 2 años (504 sesiones), neto de la cuota unica de 90 $.

Y una media sola engaña con esta distribucion, asi que se dan los percentiles,
la probabilidad de cada desenlace y el resultado condicionado a cobrar.
"""
import numpy as np
import pandas as pd

RNG = np.random.default_rng(4242)
BLOQUE = 5


def bootstrap(fuente, n_dias, n_caminos):
    x = np.asarray(fuente)
    nb = int(np.ceil(n_dias / BLOQUE))
    ini = RNG.integers(0, len(x) - BLOQUE, size=(n_caminos, nb))
    idx = ini[:, :, None] + np.arange(BLOQUE)[None, None, :]
    return x[idx].reshape(n_caminos, -1)[:, :n_dias]


def sim(ret, cuenta=50_000, cuota=90, split=0.90, dd_frac=0.07, dd_lock=0.07,
        dd_dia=0.04, min_dias=6, min_ben=0.005, best_day=0.20, umbral=1000):
    n, dias = ret.shape
    bal = np.full(n, cuenta); hwm = np.full(n, cuenta)
    piso = np.full(n, cuenta * (1 - dd_frac))
    lock = np.zeros(n, bool); vivo = np.ones(n, bool)
    cual = np.zeros(n, int); mejor = np.zeros(n)
    extra = np.zeros(n); npag = np.zeros(n, int)
    for d in range(dias):
        if not vivo.any():
            break
        pnl = bal * ret[:, d]
        nuevo = bal + pnl
        roto = vivo & ((nuevo < piso) | (pnl < -dd_dia * bal))
        vivo = vivo & ~roto
        if not vivo.any():
            continue
        bal = np.where(vivo, nuevo, bal)
        hwm = np.where(vivo, np.maximum(hwm, bal), hwm)
        lock = lock | (vivo & (hwm >= cuenta * (1 + dd_lock)))
        piso = np.where(vivo & lock, np.maximum(piso, cuenta),
                        np.where(vivo, np.maximum(piso, hwm * (1 - dd_frac)), piso))
        cual = cual + (vivo & (pnl >= min_ben * cuenta))
        mejor = np.where(vivo, np.maximum(mejor, pnl), mejor)
        prof = bal - cuenta
        pide = vivo & (prof >= umbral) & (cual >= min_dias)
        if best_day:
            pide = pide & (mejor <= best_day * np.maximum(prof, 1e-9))
        if pide.any():
            extra = extra + np.where(pide, prof, 0.0)
            npag = npag + pide
            bal = np.where(pide, cuenta, bal); hwm = np.where(pide, cuenta, hwm)
            piso = np.where(pide, cuenta * (1 - dd_frac), piso)
            lock = np.where(pide, False, lock)
            cual = np.where(pide, 0, cual); mejor = np.where(pide, 0.0, mejor)
    return extra * split - cuota, npag, ~vivo


A = pd.read_csv("salida/cartera_diaria.csv", index_col=0, parse_dates=True)
w1 = (1 / A["s1"].std()) / ((1 / A["s1"].std()) + (1 / A["s2"].std()))
w2 = 1 - w1
s1 = np.clip(A["s1"].values, -0.008, 0.008)        # stop y TP de 80 bp en la #1
cart = w1 * s1 + w2 * A["s2"].values
sd = cart.std() * np.sqrt(252)
lev = 0.045 / sd
neto, npag, quemada = sim(bootstrap(cart, 504, 40000) * lev)

E = "=" * 82
print(E)
print("UNA CUENTA DE 50K  ·  HORIZONTE DE 2 AÑOS (504 sesiones)")
print("vol objetivo 4,5% · apalancamiento x{:.2f} · stop y TP de la #1 en 80 bp"
      .format(lev))
print(E)
print("  {:<40}{:>16}".format("MEDIA (el +3.206 que te di)",
                              "{:+,.0f} USD".format(neto.mean())))
print("  {:<40}{:>16}".format("  equivalente ANUAL",
                              "{:+,.0f} USD".format(neto.mean() / 2)))
print()
print("  {:<40}{:>16}".format("MEDIANA", "{:+,.0f} USD".format(np.median(neto))))
for q in (10, 25, 75, 90):
    print("  {:<40}{:>16}".format("percentil {}".format(q),
                                  "{:+,.0f} USD".format(np.percentile(neto, q))))
print()
print("  {:<40}{:>15.1f}%".format("P(cobrar al menos una vez)",
                                  100 * (npag > 0).mean()))
print("  {:<40}{:>15.1f}%".format("P(quemar la cuenta)", 100 * quemada.mean()))
print("  {:<40}{:>15.1f}%".format("P(ni cobrar ni quemar)",
                                  100 * ((npag == 0) & ~quemada).mean()))
print("  {:<40}{:>16.2f}".format("numero medio de cobros en 2 años",
                                 npag.mean()))
print()
c = neto[npag > 0]
print("  SI COBRAS:")
print("     {:<37}{:>16}".format("media", "{:+,.0f} USD".format(c.mean())))
print("     {:<37}{:>16}".format("mediana", "{:+,.0f} USD".format(np.median(c))))
print("  SI NO COBRAS: pierdes los 90 USD de cuota y nada mas")
print()
print(E)
print("VARIAS CUENTAS CON LA MISMA ESTRATEGIA")
print(E)
print("  Correr lo mismo en N cuentas las deja perfectamente correlacionadas:")
print("  el EV se multiplica por N, pero tambien la dispersion. O cobran todas")
print("  o ninguna. Para independencia habria que escalonar los arranques.")
print()
print("  {:>8}{:>14}{:>18}{:>18}".format("cuentas", "cuota total",
                                         "EV a 2 años", "EV anual"))
print("  " + "-" * 58)
for N in (1, 2, 3, 5):
    print("  {:>8}{:>12,} USD{:>14,.0f} USD{:>14,.0f} USD".format(
        N, N * 90, N * neto.mean(), N * neto.mean() / 2))
