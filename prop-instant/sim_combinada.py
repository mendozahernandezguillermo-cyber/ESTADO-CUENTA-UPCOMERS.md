#!/usr/bin/env python3
"""
Segunda vuelta: las reglas NO actuan por separado, actuan a la vez.
Y el coste NO es fijo: si apalancas para subir la volatilidad, la
rotacion sube con ella. Modelo el coste como proporcional al
apalancamiento -> equivale a un recorte CONSTANTE del Sharpe.

    coste_anual = 3.78% * (vol / 0.15)
    recorte_sharpe = coste_anual / vol = 0.252   (independiente del tamano)

Objetivo: encontrar el Sharpe VERDADERO minimo con EV > 0 bajo las
reglas reales, y compararlo con el Sharpe que se puede ESTABLECER con
12 meses de historial.
"""
import numpy as np

RNG      = np.random.default_rng(11235)
CUENTA   = 50_000.0
LIM_DIA  = 0.05 * CUENTA
LIM_DD   = 0.07 * CUENTA
OBJETIVO = 0.06 * CUENTA
SPLIT    = 0.80
CUOTA    = 90.0
DIAS     = 252
N        = 40_000
RECORTE  = 0.252          # coste en unidades de Sharpe


def simular(sharpe_bruto, vol, trailing=False, consistencia=None,
            con_coste=True, dias=DIAS, n=N):
    sh   = sharpe_bruto - (RECORTE if con_coste else 0.0)
    mu_d = sh * vol / DIAS * CUENTA
    sd_d = vol / np.sqrt(DIAS) * CUENTA
    pnl  = RNG.normal(mu_d, sd_d, size=(n, dias))

    eq   = np.cumsum(pnl, axis=1)
    pico = np.maximum.accumulate(np.maximum(eq, 0.0), axis=1)

    ruina = ((pico - eq) > LIM_DD) if trailing else (eq < -LIM_DD)
    ruina |= (pnl < -LIM_DIA)
    exito = eq >= OBJETIVO

    def primer(m):
        return np.where(m.any(axis=1), m.argmax(axis=1), dias + 1)

    tr, te = primer(ruina), primer(exito)
    cobra  = te < tr

    bloq = np.zeros(n, dtype=bool)
    if consistencia is not None and cobra.any():
        ganan = np.where(pnl > 0, pnl, 0.0)
        idx   = np.clip(te, 0, dias - 1)
        ok    = np.where(cobra)[0]
        mejor = np.array([ganan[i, :idx[i] + 1].max() for i in ok])
        total = np.array([eq[i, idx[i]]               for i in ok])
        mal   = ok[(total > 0) & (mejor / np.maximum(total, 1e-9) > consistencia)]
        bloq[mal] = True

    c = (cobra & ~bloq).mean()
    return c, (tr < te).mean(), bloq.mean(), c * OBJETIVO * SPLIT - CUOTA


vols = [0.05, 0.08, 0.12, 0.15, 0.20, 0.30]
shs  = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0]

print("=" * 76)
print("ESCENARIO REALISTA: DD trailing + consistencia 20% + coste proporcional")
print("Celda = EV en dolares tras la cuota unica de 90 $ (12 meses)")
print("=" * 76)
print(f"{'Sharpe real':<13}" + "".join(f"{f'vol {v:.0%}':>10}" for v in vols))
print("-" * 76)
mapa = {}
for sh in shs:
    fila = []
    for v in vols:
        c, q, b, ev = simular(sh, v, trailing=True, consistencia=0.20)
        mapa[(sh, v)] = (c, q, b, ev)
        fila.append(ev)
    print(f"{sh:<13.2f}" + "".join(f"{e:>10.0f}" for e in fila))

print("\nDetalle de la mejor columna (vol 8%) — trailing + consistencia 20%:")
print(f"{'Sharpe':<10}{'cobra':>9}{'quema':>9}{'bloq':>9}{'EV $':>10}")
print("-" * 47)
for sh in shs:
    c, q, b, ev = mapa[(sh, 0.08)]
    print(f"{sh:<10.2f}{c:>8.1%}{q:>9.1%}{b:>9.1%}{ev:>10.0f}")

print("\n" + "=" * 76)
print("VARIANTE BENIGNA: DD estatico + consistencia 30% + coste proporcional")
print("=" * 76)
print(f"{'Sharpe real':<13}" + "".join(f"{f'vol {v:.0%}':>10}" for v in vols))
print("-" * 76)
for sh in shs:
    fila = [simular(sh, v, trailing=False, consistencia=0.30)[3] for v in vols]
    print(f"{sh:<13.2f}" + "".join(f"{e:>10.0f}" for e in fila))

# ---------------------------------------------------------------
print("\n" + "=" * 76)
print("SESGO DE SELECCION: Sharpe que aparenta un darwin SIN habilidad")
print("cuando eliges el mejor de N tras 12 meses")
print("=" * 76)
print("SE(Sharpe) con 12 meses ~ 1.00, asi que el Sharpe observado del")
print("mejor de N candidatos sin ninguna habilidad es E[max de N normales]:")
print(f"\n{'N candidatos':<16}{'Sharpe aparente':>18}")
print("-" * 34)
for Nc in [10, 25, 50, 100, 250, 500, 1000, 2500]:
    m = RNG.standard_normal(size=(4000, Nc)).max(axis=1).mean()
    print(f"{Nc:<16}{m:>18.2f}")
