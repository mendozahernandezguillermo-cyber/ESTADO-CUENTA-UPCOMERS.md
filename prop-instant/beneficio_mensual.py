#!/usr/bin/env python3
"""
BENEFICIO MENSUAL ESPERADO
3 cuentas de 100K, cada una con las 3 estrategias dentro, split 80%.

Devuelve la DISTRIBUCION, no solo la media: con probabilidad de ruina alta la
media esta dominada por unos pocos caminos buenos y no describe lo que te va
a pasar. Se reportan media, mediana, cuartiles y P(cero).
"""
import numpy as np

DIAS_ANO = 252
SUB      = 4
MESES    = 36
ANOS     = 3

CUENTA   = 100_000.0
N_CTAS   = 3
SPLIT    = 0.80
CUOTA    = 180.0          # 90 $ por cada 50K, escalado
DD_MAX   = 0.07
DD_DIA   = 0.04
MIN_DIAS = 6
MIN_BEN  = 0.005
BEST_DAY = 0.20
UMBRAL   = 0.02 * CUENTA
RECORTE  = 0.252
NEA      = 3


def sharpe_cartera(s, rho, n=NEA):
    return s * np.sqrt(n / (1.0 + (n - 1) * rho))


def simular(sharpe_neto_bruto, vol=0.06, n=20_000, semilla=2026):
    """Un camino = una cuenta. Las 3 cuentas son identicas (misma cartera),
    asi que el total es 3 x el resultado de una, camino a camino."""
    rng  = np.random.default_rng(semilla)
    dias = int(ANOS * DIAS_ANO)
    sh   = sharpe_neto_bruto - RECORTE
    sd_d = vol / np.sqrt(DIAS_ANO) * CUENTA
    mu_s = sh * vol / (DIAS_ANO * SUB) * CUENTA
    sd_s = sd_d / np.sqrt(SUB)

    bal   = np.full(n, CUENTA)
    hwm   = np.full(n, CUENTA)
    piso  = np.full(n, CUENTA * (1 - DD_MAX))
    lock  = np.zeros(n, dtype=bool)
    vivo  = np.ones(n, dtype=bool)
    cual  = np.zeros(n, dtype=int)
    mejor = np.zeros(n)
    extra = np.zeros(n)

    for _ in range(dias):
        if not vivo.any():
            break
        z  = rng.standard_normal((n, SUB))
        eq = bal[:, None] + np.cumsum(mu_s + sd_s * z, axis=1)
        emin, emax, efin = eq.min(1), eq.max(1), eq[:, -1]

        roto = vivo & ((emin < piso) | (emin < bal * (1 - DD_DIA)))
        vivo = vivo & ~roto
        if not vivo.any():
            continue

        pnl   = np.where(vivo, efin - bal, 0.0)
        bal   = np.where(vivo, efin, bal)
        hwm   = np.where(vivo, np.maximum(hwm, emax), hwm)
        lock  = lock | (vivo & (hwm >= CUENTA * (1 + DD_MAX)))
        piso  = np.where(vivo & ~lock,
                         np.maximum(piso, hwm * (1 - DD_MAX)), piso)
        piso  = np.where(vivo & lock, np.maximum(piso, CUENTA), piso)
        cual  = cual + (vivo & (pnl >= MIN_BEN * CUENTA))
        mejor = np.where(vivo, np.maximum(mejor, pnl), mejor)
        prof  = bal - CUENTA

        pide = vivo & (prof >= UMBRAL) & (cual >= MIN_DIAS) \
               & (mejor <= BEST_DAY * np.maximum(prof, 1e-9))
        if pide.any():
            extra = extra + np.where(pide, prof, 0.0)
            bal   = np.where(pide, CUENTA, bal)
            hwm   = np.where(pide, CUENTA, hwm)
            piso  = np.where(pide, CUENTA * (1 - DD_MAX), piso)
            lock  = np.where(pide, False, lock)
            cual  = np.where(pide, 0, cual)
            mejor = np.where(pide, 0.0, mejor)

    # total de las 3 cuentas, camino a camino (identicas => x3)
    neto = (extra * SPLIT - CUOTA) * N_CTAS
    return neto, (~vivo)


print("=" * 79)
print("BENEFICIO MENSUAL · 3 cuentas de 100K · 3 estrategias en cada una")
print("split 80% · cuota 180 $/cuenta · vol 6% · horizonte 3 anos (36 meses)")
print("=" * 79)
print(f"{'s':>5}{'rho':>6}{'Sh cart':>9}{'MEDIA/mes':>12}{'MEDIANA/mes':>13}"
      f"{'p25':>9}{'p75':>10}{'P(cero)':>10}")
print("-" * 79)

for s in (0.5, 0.75, 1.0, 1.5, 2.0):
    for rho in (0.0, 0.3, 0.6):
        shc = sharpe_cartera(s, rho)
        neto, muerto = simular(shc)
        mes = neto / MESES
        p_cero = (neto <= 0).mean()
        print(f"{s:>5.2f}{rho:>6.1f}{shc:>9.2f}{mes.mean():>12.0f}"
              f"{np.median(mes):>13.0f}{np.percentile(mes, 25):>9.0f}"
              f"{np.percentile(mes, 75):>10.0f}{p_cero:>10.1%}")
    print()

print("=" * 79)
print("CASO CENTRAL DETALLADO  ·  s = 0,75 · rho = 0,3  ->  Sharpe cartera 1,03")
print("=" * 79)
neto, muerto = simular(sharpe_cartera(0.75, 0.3))
mes = neto / MESES
for etiq, val in [
    ("media al mes",                      mes.mean()),
    ("mediana al mes",                    np.median(mes)),
    ("percentil 10",                      np.percentile(mes, 10)),
    ("percentil 25",                      np.percentile(mes, 25)),
    ("percentil 75",                      np.percentile(mes, 75)),
    ("percentil 90",                      np.percentile(mes, 90)),
    ("media si sobrevive los 3 anos",     mes[~muerto].mean()),
    ("media si la cuenta muere",          mes[muerto].mean()),
]:
    print(f"  {etiq:<34}{val:>12,.0f} $")
print(f"  {'P(perder las cuotas y nada mas)':<34}{(neto <= 0).mean():>11.1%}")
print(f"  {'P(quemar las 3 cuentas en 3 anos)':<34}{muerto.mean():>11.1%}")
print(f"  {'total acumulado 3 anos (media)':<34}{neto.mean():>12,.0f} $")

print("\n" + "=" * 79)
print("ANCLAJE HONESTO")
print("=" * 79)
print("""La unica estrategia con numeros medidos en tu Probador
(NAS100_OpenMomentum v2.00) dio t ~ 1,1 sobre 48 operaciones. Eso es
compatible con s entre 0 y ~1,0; el estimador puntual ronda 0,4-0,5 y NO es
distinguible de cero. La fila s=0,5 es por tanto la mas defendible hoy, y
las de s=1,5 y 2,0 requieren una calidad que aun no has demostrado en
ninguna estrategia.""")
