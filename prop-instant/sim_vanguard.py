#!/usr/bin/env python3
"""
UPCOMERS VANGUARD (Instant Funding) 50K — reglas verificadas en su help center:

  * Drawdown maximo 7% = Dynamic Risk Shield(TM): TRAILING sobre el maximo
    historico de EQUITY (incluye posiciones abiertas), en tiempo real,
    sube pero nunca baja.
  * SE BLOQUEA en el balance inicial una vez la cuenta crece un 7%.
    -> a partir de +3.500 el nivel de ruina queda fijo en 50.000.
  * Drawdown diario 4% calculado sobre el MAYOR de (equity, balance)
    a las 00:00 UTC. Rompe con equity intradia (no realizado).
  * Trading minimo 6 dias. En el producto de futuros un dia solo cuenta
    si cierra con >= 0,5% de beneficio -> se prueban las dos versiones.
  * Payout bajo demanda, limite de tiempo ILIMITADO, profit split 90%.
  * Best Day Rule: 20% en futuros, 30% en Thunderbolt Legacy.
    Se prueba 20%, 30% y sin regla.

Como el payout es bajo demanda y el tiempo ilimitado, el juego NO es
"llegar a un objetivo": es un proceso de renovacion. Extraes, la cuenta
vuelve al inicio, y repites hasta que el trailing te mata. Con deriva
cero y stop trailing, la ruina es SEGURA a tiempo infinito. Lo que se
mide es cuanto extraes antes.

Se simula con 8 subpasos intradia para capturar el maximo/minimo de
equity dentro del dia, que es lo que mira el Shield.
"""
import numpy as np

RNG      = np.random.default_rng(4242)
CUENTA   = 50_000.0
DD_MAX   = 0.07
DD_DIA   = 0.04
LOCK     = CUENTA * (1 + DD_MAX)      # 53.500 -> el shield se congela
SPLIT    = 0.90
CUOTA    = 90.0
DIAS_ANO = 252
SUB      = 8                          # subpasos intradia
RECORTE  = 0.252                      # coste en unidades de Sharpe


def simular(sharpe_bruto, vol, umbral, anos=3, n=20_000,
            best_day=0.20, dia_cualifica_pct=0.005, min_dias=6):
    dias = int(anos * DIAS_ANO)
    sh   = sharpe_bruto - RECORTE
    mu_s = sh * vol / (DIAS_ANO * SUB) * CUENTA
    sd_s = vol / np.sqrt(DIAS_ANO * SUB) * CUENTA

    balance = np.full(n, CUENTA)
    hwm     = np.full(n, CUENTA)
    breach  = np.full(n, CUENTA * (1 - DD_MAX))
    locked  = np.zeros(n, dtype=bool)
    vivo    = np.ones(n, dtype=bool)

    cual    = np.zeros(n, dtype=int)      # dias cualificados del ciclo
    mejor   = np.zeros(n)                 # mejor dia del ciclo
    extraido= np.zeros(n)
    n_pagos = np.zeros(n, dtype=int)
    primer  = np.zeros(n, dtype=bool)

    for d in range(dias):
        act = np.where(vivo)[0]
        if act.size == 0:
            break

        ini    = balance[act]
        lim_d  = ini * (1 - DD_DIA)

        pasos  = RNG.normal(mu_s, sd_s, size=(act.size, SUB))
        eq     = ini[:, None] + np.cumsum(pasos, axis=1)

        eq_min = eq.min(axis=1)
        eq_max = eq.max(axis=1)
        eq_fin = eq[:, -1]

        # --- nivel de ruina vigente durante el dia -------------------
        # el shield sube DENTRO del dia con el maximo de equity
        nuevo_hwm = np.maximum(hwm[act], eq_max)
        br_din    = np.where(locked[act], breach[act],
                             np.maximum(breach[act], hwm[act] * (1 - DD_MAX)))
        # aproximacion conservadora: el shield del dia usa el hwm previo
        roto = (eq_min < br_din) | (eq_min < lim_d)

        # --- actualizar estado de los supervivientes ------------------
        sob = act[~roto]
        vivo[act[roto]] = False
        if sob.size == 0:
            continue

        i = ~roto
        hwm[sob]    = nuevo_hwm[i]
        nl          = hwm[sob] >= LOCK
        breach[sob] = np.where(nl | locked[sob], CUENTA,
                               np.maximum(breach[sob], hwm[sob] * (1 - DD_MAX)))
        locked[sob] = locked[sob] | nl

        pnl_d       = eq_fin[i] - ini[i]
        balance[sob]= eq_fin[i]
        mejor[sob]  = np.maximum(mejor[sob], pnl_d)
        cual[sob]  += (pnl_d >= dia_cualifica_pct * CUENTA)

        # --- intento de cobro ----------------------------------------
        prof = balance[sob] - CUENTA
        pide = (prof >= umbral) & (cual[sob] >= min_dias)
        if best_day is not None:
            pide &= (mejor[sob] <= best_day * np.maximum(prof, 1e-9))

        idx = sob[pide]
        if idx.size:
            extraido[idx] += balance[idx] - CUENTA
            n_pagos[idx]  += 1
            primer[idx]    = True
            # reset del ciclo: la cuenta vuelve al inicio y el shield se rearma
            balance[idx] = CUENTA
            hwm[idx]     = CUENTA
            breach[idx]  = CUENTA * (1 - DD_MAX)
            locked[idx]  = False
            cual[idx]    = 0
            mejor[idx]   = 0.0

    ev = (extraido * SPLIT).mean() - CUOTA
    return dict(p1=primer.mean(), ruina=(~vivo).mean(),
                pagos=n_pagos.mean(), bruto=extraido.mean(), ev=ev)


def bloque(titulo, sharpe, **kw):
    print(f"\n{titulo}")
    print(f"{'vol':>6}{'umbral':>9}{'P(1er cobro)':>14}{'P(ruina 3a)':>13}"
          f"{'pagos':>8}{'EV $':>10}")
    print("-" * 60)
    mejor = (None, -1e9)
    for vol in [0.04, 0.06, 0.08, 0.12, 0.18]:
        for umb in [500, 1000, 2000, 3500]:
            r = simular(sharpe, vol, umb, **kw)
            print(f"{vol:>6.0%}{umb:>9.0f}{r['p1']:>13.1%}{r['ruina']:>13.1%}"
                  f"{r['pagos']:>8.2f}{r['ev']:>10.0f}")
            if r['ev'] > mejor[1]:
                mejor = ((vol, umb, r), r['ev'])
    v, u, r = mejor[0]
    print(f"  -> mejor: vol {v:.0%}, umbral {u:.0f} $ "
          f"-> EV {r['ev']:.0f} $, P(1er cobro) {r['p1']:.1%}")
    return mejor[0]


print("=" * 60)
print("VANGUARD 50K · trailing 7% con lock · diario 4% · split 90%")
print("6 dias cualificados (>= 0,5% cada uno) · Best Day 20% · 3 anos")
print("=" * 60)
bloque("SIN VENTAJA (Sharpe bruto 0,00 -> neto -0,25)", 0.00)
bloque("VENTAJA MEDIA (Sharpe bruto 1,00 -> neto 0,75)", 1.00)
bloque("VENTAJA ALTA  (Sharpe bruto 2,00 -> neto 1,75)", 2.00)

print("\n" + "=" * 60)
print("SENSIBILIDAD A LAS REGLAS QUE NO HE PODIDO VERIFICAR")
print("=" * 60)
for etiq, kw in [
    ("Best Day 30% en vez de 20%",            dict(best_day=0.30)),
    ("Sin Best Day Rule",                     dict(best_day=None)),
    ("Dia cualifica con cualquier beneficio", dict(dia_cualifica_pct=0.0)),
    ("Sin Best Day + dia = cualquier benef.", dict(best_day=None,
                                                  dia_cualifica_pct=0.0)),
]:
    r = simular(1.00, 0.06, 1000, **kw)
    print(f"{etiq:<42} EV {r['ev']:>7.0f} $  "
          f"P(1er cobro) {r['p1']:>6.1%}  ruina {r['ruina']:>6.1%}")
