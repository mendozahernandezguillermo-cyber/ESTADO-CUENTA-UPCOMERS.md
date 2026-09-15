#!/usr/bin/env python3
"""
Quedan dos supuestos optimistas que pueden explicar el EV positivo con
Sharpe 0:

  (a) RECORTE POR COSTES = 0,252 Sharpe. En una cuenta prop con spreads
      anchos y una estrategia que necesita muchos dias de +0,5%, la
      rotacion es alta y el coste puede ser mucho mayor.

  (b) GRANULARIDAD: mirar la equity 4 veces al dia subestima las roturas,
      porque el Dynamic Risk Shield mira en TIEMPO REAL.

Se barren los dos para encontrar el umbral en que el EV cambia de signo.
"""
import numpy as np

DIAS_ANO = 252
C        = 50_000.0
DD_MAX   = 0.07
DD_DIA   = 0.04
SPLIT    = 0.90
CUOTA    = 90.0
MIN_DIAS = 6
MIN_BEN  = 0.005
BEST_DAY = 0.20


def motor(sharpe_bruto, vol, recorte, sub, umbral=1000, anos=3, n=12_000,
          semilla=31):
    rng  = np.random.default_rng(semilla)
    dias = int(anos * DIAS_ANO)
    sh   = sharpe_bruto - recorte
    sd_d = vol / np.sqrt(DIAS_ANO) * C
    mu_s = sh * vol / (DIAS_ANO * sub) * C
    sd_s = sd_d / np.sqrt(sub)

    balance = np.full(n, C)
    hwm     = np.full(n, C)
    piso    = np.full(n, C * (1 - DD_MAX))
    locked  = np.zeros(n, dtype=bool)
    vivo    = np.ones(n, dtype=bool)
    cual    = np.zeros(n, dtype=int)
    mejor   = np.zeros(n)
    extra   = np.zeros(n)
    cobrado = np.zeros(n, dtype=bool)

    for _ in range(dias):
        if not vivo.any():
            break
        z  = rng.standard_normal((n, sub))
        eq = balance[:, None] + np.cumsum(mu_s + sd_s * z, axis=1)
        emin, emax, efin = eq.min(1), eq.max(1), eq[:, -1]

        roto = vivo & ((emin < piso) | (emin < balance * (1 - DD_DIA)))
        vivo = vivo & ~roto
        if not vivo.any():
            continue

        pnl     = np.where(vivo, efin - balance, 0.0)
        balance = np.where(vivo, efin, balance)
        hwm     = np.where(vivo, np.maximum(hwm, emax), hwm)
        locked  = locked | (vivo & (hwm >= C * (1 + DD_MAX)))
        piso    = np.where(vivo & ~locked,
                           np.maximum(piso, hwm * (1 - DD_MAX)), piso)
        piso    = np.where(vivo & locked, np.maximum(piso, C), piso)

        cual  = cual + (vivo & (pnl >= MIN_BEN * C))
        mejor = np.where(vivo, np.maximum(mejor, pnl), mejor)
        prof  = balance - C

        pide = vivo & (prof >= umbral) & (cual >= MIN_DIAS) \
               & (mejor <= BEST_DAY * np.maximum(prof, 1e-9))
        if pide.any():
            extra   = extra + np.where(pide, prof, 0.0)
            cobrado = cobrado | pide
            balance = np.where(pide, C, balance)
            hwm     = np.where(pide, C, hwm)
            piso    = np.where(pide, C * (1 - DD_MAX), piso)
            locked  = np.where(pide, False, locked)
            cual    = np.where(pide, 0, cual)
            mejor   = np.where(pide, 0.0, mejor)

    return extra.mean() * SPLIT - CUOTA, cobrado.mean(), (~vivo).mean()


print("=" * 70)
print("(a) SENSIBILIDAD AL RECORTE POR COSTES  ·  Vanguard · vol 8%")
print("=" * 70)
print(f"{'recorte':>9}{'Sh bruto 0':>13}{'Sh bruto 1':>13}{'Sh bruto 2':>13}")
print("-" * 70)
for rec in (0.25, 0.50, 0.75, 1.00, 1.50, 2.00):
    fila = [motor(sh, 0.08, rec, 4)[0] for sh in (0.0, 1.0, 2.0)]
    print(f"{rec:>9.2f}" + "".join(f"{v:>13.0f}" for v in fila))

print("\n" + "=" * 70)
print("(b) SENSIBILIDAD A LA GRANULARIDAD DE VIGILANCIA · vol 8% · recorte 0,25")
print("=" * 70)
print(f"{'subpasos/dia':>14}{'Sh 0':>10}{'P(ruina)':>11}{'Sh 1':>10}"
      f"{'P(ruina)':>11}")
print("-" * 70)
for sub in (1, 4, 16, 64, 256):
    e0, _, r0 = motor(0.0, 0.08, 0.25, sub)
    e1, _, r1 = motor(1.0, 0.08, 0.25, sub)
    print(f"{sub:>14}{e0:>10.0f}{r0:>11.1%}{e1:>10.0f}{r1:>11.1%}")

print("\n" + "=" * 70)
print("(c) LAS DOS A LA VEZ, caso realista pesimista")
print("=" * 70)
print(f"{'recorte':>9}{'sub':>6}{'Sh bruto 0':>13}{'Sh bruto 1':>13}"
      f"{'Sh bruto 2':>13}")
print("-" * 70)
for rec, sub in ((0.25, 4), (0.75, 64), (1.00, 64), (1.50, 256)):
    fila = [motor(sh, 0.08, rec, sub)[0] for sh in (0.0, 1.0, 2.0)]
    print(f"{rec:>9.2f}{sub:>6}" + "".join(f"{v:>13.0f}" for v in fila))
