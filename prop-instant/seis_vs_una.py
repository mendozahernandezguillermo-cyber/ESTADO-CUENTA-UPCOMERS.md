#!/usr/bin/env python3
"""
SEIS CUENTAS PEQUENAS vs UNA GRANDE, a capital total IGUAL (300K).

La clave que cambia la respuesta: si metes 6 estrategias descorrelacionadas
en UNA cuenta, la diversificacion baja la volatilidad de la cartera, y al
reapalancar para volver a la vol optima te quedas con un Sharpe MULTIPLICADO:

    Sharpe_cartera = s * raiz(6 / (1 + 5*rho))

    rho = 0,0  ->  2,45 x s
    rho = 0,3  ->  1,55 x s
    rho = 0,5  ->  1,31 x s
    rho = 1,0  ->  1,00 x s   (ninguna ganancia)

En 6 cuentas separadas ese efecto NO existe: cada cuenta enfrenta su propio
limite del 7% con la vol de UNA sola estrategia. Las perdidas de una cuenta
no se compensan con las ganancias de otra a efectos del drawdown.

Como todos los limites son porcentajes, el EV escala linealmente con el
tamano de cuenta; se asume tambien cuota lineal (90 $ por cada 50K).
"""
import io
import contextlib
import numpy as np

# marco_general imprime sus tablas al importarse; se silencian
with contextlib.redirect_stdout(io.StringIO()):
    from marco_general import FIRMAS, motor

CAP_TOTAL = 300_000.0
N         = 6


def sharpe_cartera(s, rho, n=N):
    return s * np.sqrt(n / (1.0 + (n - 1) * rho))


def caso_una_grande(clave, s, rho, vol=0.06):
    """1 cuenta de 300K con las 6 estrategias dentro."""
    R = FIRMAS[clave]
    esc = CAP_TOTAL / R.cuenta                 # factor de escala 6x
    sh  = sharpe_cartera(s, rho)
    r   = motor(R, sh, vol, umbral=0.02 * R.cuenta, n=8000)
    return dict(ev=r['ev_cuenta'] * esc, p_cobro=r['p_cobro'],
                p_ruina=r['p_ruina'], sharpe=sh,
                p_pos=1.0 - r['p_ruina'] if False else None)


def caso_seis(clave, s, rho, vol=0.06):
    """6 cuentas de 50K, una estrategia cada una."""
    R = FIRMAS[clave]
    r = motor(R, s, vol, umbral=0.02 * R.cuenta, n=8000,
              n_cuentas=N, rho=rho)
    return dict(ev=r['ev_cartera'], p_cobro=r['p_cobro'],
                p_ruina=r['p_ruina'], sharpe=s, p_pos=r['p_cartera_pos'])


for clave in ('upcomers_vanguard', 'ftmo_2step'):
    R = FIRMAS[clave]
    print("=" * 78)
    print(f"{R.nombre}  ·  capital total {CAP_TOTAL:,.0f} $  ·  vol objetivo 6%")
    print("=" * 78)
    print(f"{'s':>5}{'rho':>6}  {'6 CUENTAS DE 50K':<30}{'1 CUENTA DE 300K':<30}")
    print(f"{'':>11}  {'EV':>9}{'P(cart>0)':>11}{'ruina':>9}"
          f"  {'EV':>10}{'Sharpe':>8}{'ruina':>8}")
    print("-" * 78)
    for s in (0.5, 1.0, 1.5):
        for rho in (0.0, 0.3, 0.6, 1.0):
            a = caso_seis(clave, s, rho)
            b = caso_una_grande(clave, s, rho)
            gana = "GRANDE" if b['ev'] > a['ev'] else "seis"
            print(f"{s:>5.1f}{rho:>6.1f}  {a['ev']:>9.0f}{a['p_pos']:>11.1%}"
                  f"{a['p_ruina']:>9.1%}  {b['ev']:>10.0f}{b['sharpe']:>8.2f}"
                  f"{b['p_ruina']:>8.1%}   {gana}")
        print()

print("=" * 78)
print("LO QUE ESTO NO CAPTURA")
print("=" * 78)
print("""
El modelo dice que la cuenta grande domina por diversificacion interna.
Pero el riesgo DOMINANTE que identificamos no es estadistico, es de
contraparte: que la firma no pague. Y eso solo se diversifica repartiendo
cuentas entre FIRMAS DISTINTAS.

Ademas:
  - FTMO topa en 400.000 $ por trader O ESTRATEGIA.
  - Un fallo operativo (bug del EA, mal fill) se lleva la cuenta entera.
  - 6 cuentas dan 6 tiradas independientes a la loteria de "si pagan".
""")
