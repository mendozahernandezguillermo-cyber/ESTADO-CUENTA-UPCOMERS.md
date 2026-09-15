#!/usr/bin/env python3
"""
Compara la configuracion que ha entendido el usuario contra la alternativa.

  CONFIG B (lo que entendio): 3 cuentas de 100K, UN EA distinto en cada una.
           Las cuentas quedan descorrelacionadas entre si, pero cada cuenta
           enfrenta su 7% con la volatilidad de UNA sola estrategia.

  CONFIG A (lo que yo proponia): 3 cuentas de 100K, LAS TRES corriendo LAS
           TRES estrategias. Cada cuenta gana Sharpe por diversificacion
           interna:  s * raiz(3/(1+2rho)).  Las cuentas quedan perfectamente
           correlacionadas entre si -> la diversificacion NO viene de tener
           varias cuentas, viene de dentro de cada una.

  CONFIG C: 1 sola cuenta de 300K con las tres estrategias (referencia).

  CONFIG D: como A pero repartida en TRES FIRMAS distintas, que es lo que
           de verdad diversifica el riesgo de que no paguen.
"""
import io
import contextlib
from dataclasses import replace
import numpy as np

with contextlib.redirect_stdout(io.StringIO()):
    from marco_general import FIRMAS, motor

VOL   = 0.06
ANOS  = 3
NEA   = 3            # numero de estrategias disponibles


def sh_cartera(s, rho, n=NEA):
    """Sharpe de una cartera equiponderada de n estrategias."""
    return s * np.sqrt(n / (1.0 + (n - 1) * rho))


def escala(clave, tam, cuota=None):
    R = FIRMAS[clave]
    f = tam / R.cuenta
    return replace(R, cuenta=tam,
                   cuota=R.cuota * f if cuota is None else cuota)


def run(R, sharpe, n_cuentas, rho_ctas, vol=VOL, n=8000):
    return motor(R, sharpe, vol, umbral=0.02 * R.cuenta, anos=ANOS,
                 n=n, n_cuentas=n_cuentas, rho=rho_ctas)


print("=" * 80)
print("CAPITAL TOTAL 300.000 $  ·  3 estrategias disponibles  ·  vol 6%  ·  3 anos")
print("=" * 80)

for clave in ('upcomers_vanguard', 'ftmo_2step'):
    R100 = escala(clave, 100_000)
    R300 = escala(clave, 300_000)
    print(f"\n### {FIRMAS[clave].nombre}   (cuota escalada: "
          f"{R100.cuota:.0f} $ por cuenta de 100K)")
    print(f"{'s':>5}{'rho EAs':>9}  {'B: 1 EA por cuenta':>26}"
          f"  {'A: las 3 en cada cuenta':>26}")
    print(f"{'':>14}  {'EV':>11}{'P(tot>0)':>10}{'ruina':>7}"
          f"  {'EV':>11}{'Sharpe':>7}{'P(tot>0)':>10}")
    print("-" * 80)
    for s in (0.5, 1.0, 1.5):
        for rho in (0.0, 0.3, 0.6):
            # B: 3 cuentas, 1 EA cada una, cuentas correlacionadas a rho
            b = run(R100, s, 3, rho)
            # A: 3 cuentas identicas con la cartera dentro -> entre si rho=1
            sa = sh_cartera(s, rho)
            a  = run(R100, sa, 3, 1.0)
            mark = "  A gana" if a['ev_cartera'] > b['ev_cartera'] else "  B gana"
            print(f"{s:>5.1f}{rho:>9.1f}  {b['ev_cartera']:>11.0f}"
                  f"{b['p_cartera_pos']:>10.1%}{b['p_ruina']:>7.1%}"
                  f"  {a['ev_cartera']:>11.0f}{sa:>7.2f}"
                  f"{a['p_cartera_pos']:>10.1%}{mark}")
        print()

# ---------------------------------------------------------------- C y D
print("=" * 80)
print("REFERENCIAS ADICIONALES  ·  s = 1,0 · rho entre EAs = 0,3")
print("=" * 80)
s, rho = 1.0, 0.3
sa = sh_cartera(s, rho)
print(f"Sharpe de la cartera de 3 estrategias a rho=0,3: {sa:.2f}\n")

filas = []
for clave in ('upcomers_vanguard', 'ftmo_2step'):
    b = run(escala(clave, 100_000), s,  3, rho)
    a = run(escala(clave, 100_000), sa, 3, 1.0)
    c = run(escala(clave, 300_000), sa, 1, 0.0)
    filas.append((FIRMAS[clave].nombre, b, a, c))

print(f"{'firma':<30}{'B: 1 EA/cta':>14}{'A: 3 EA/cta':>14}"
      f"{'C: 1 cta 300K':>15}")
print("-" * 80)
for nom, b, a, c in filas:
    print(f"{nom:<30}{b['ev_cartera']:>14.0f}{a['ev_cartera']:>14.0f}"
          f"{c['ev_cartera']:>15.0f}")

# D: cartera completa en cada una de tres firmas distintas
print(f"\nCONFIG D — la cartera de 3 estrategias replicada en 3 FIRMAS:")
tot, det = 0.0, []
for clave in ('upcomers_vanguard', 'ftmo_2step', 'ftmo_1step'):
    R = escala(clave, 100_000)
    r = run(R, sa, 1, 0.0)
    det.append((FIRMAS[clave].nombre, R.cuota, r['ev_cuenta'], r['p_ruina']))
    tot += r['ev_cuenta']
print(f"{'firma':<32}{'cuota':>9}{'EV':>12}{'ruina':>9}")
print("-" * 80)
for nom, cu, ev, ru in det:
    print(f"{nom:<32}{cu:>9.0f}{ev:>12.0f}{ru:>9.1%}")
print(f"{'TOTAL':<32}{sum(d[1] for d in det):>9.0f}{tot:>12.0f}")
print("\nNota: en D las tres cuentas comparten estrategia, asi que el riesgo")
print("de ESTRATEGIA no se diversifica; lo que se diversifica es el riesgo")
print("de que una firma no pague, que es el termino que no puedo simular.")
