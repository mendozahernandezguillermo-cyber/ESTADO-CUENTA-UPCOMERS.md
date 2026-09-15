"""
CON EL TREND APAGADO, EL RIESGO DEJA DE SER UN AJUSTE FINO: ES UN ACANTILADO.

La firma exige 6 dias cerrados con >= +0,5% de beneficio para poder cobrar.
Con el trend apagado, la UNICA fuente de P&L diario son los ~8 eventos FOMC al
año. Y un acierto rinde exactamente:

        TP / stop x riesgo  =  40/80 x riesgo  =  0,5 x riesgo

    riesgo 0,96%  ->  0,480%   NO cualifica (umbral 0,500%)
    riesgo 1,00%  ->  0,500%   justo en el filo
    riesgo 1,05%  ->  0,525%   cualifica

Si no cualifica, la cuenta puede ganar dinero y NO PODER COBRARLO NUNCA, porque
nunca acumula los 6 dias. Con el trend encendido esto no se veia, porque el
ruido diario del trend empujaba algunos dias por encima del umbral.

Se mide, porque la diferencia entre 0,96 y 1,05 deberia ser abismal y no
gradual. Y se comprueba el limite duro del 2% en cada caso.
"""
import numpy as np
import pandas as pd

ns = {"__name__": "addendum"}
exec(compile(open("cobros_reales_addendum.py", encoding="utf-8")
             .read().split("# ---8<--- INFORME")[0],
             "cobros_reales_addendum.py", "exec"), ns)
simular2 = ns["simular2"]; mod = ns["mod"]
serie_s1 = mod["serie_s1"]; STOP_BP = mod["STOP_BP"]; CUENTA = mod["CUENTA"]

TP = 40.0
CARRY_FOMC = 50.0
DIAS_ANIO = 252
N, ANIOS = 40_000, 4
PEOR_COLA_BP = 133.8        # la peor excursion que el mercado hizo de verdad

base = pd.read_csv("../trend/serie_cfd_b7.csv", index_col=0, parse_dates=True)
ev = serie_s1(TP)

# ¿cuantos eventos aciertan el TP?
tp_frac = np.mean([1.0 if abs(r - TP / 1e4) < 1e-9 else 0.0 for r in ev.values()])

E = "=" * 94
print(E)
print("SOLO FOMC: EL RIESGO CONTRA LA REGLA DE LOS 6 DIAS DE +0,5%")
print(E)
print(f"  eventos con TP alcanzado: {tp_frac:.1%} de {len(ev)}  "
      f"=> ~{tp_frac*8:.1f} dias cualificables al año de los 6 que piden")
print()
print(f"  {'riesgo':>8}{'rinde un TP':>13}{'cualifica':>11}{'peor caso':>11}"
      f"{'vs 2%':>8}{'recibido 4a':>13}{'por año':>10}{'P(cobra)':>10}")
print("  " + "-" * 86)
for rg in (0.96, 1.00, 1.05, 1.15, 1.30):
    rinde = TP / STOP_BP * rg
    peor = PEOR_COLA_BP / STOP_BP * rg
    mult1 = (rg / 100.0) / (STOP_BP / 1e4)
    s1 = pd.Series(0.0, index=base.index)
    for ts, r in ev.items():
        if ts in s1.index:
            s1.loc[ts] = r
    D = pd.DataFrame({"s1": s1}).dropna()
    D = D[D.index >= "2011-01-01"]
    drag = CARRY_FOMC / CUENTA / DIAS_ANIO
    a = (D["s1"] * mult1).values
    b = np.full(len(a), -drag)
    g1, g2 = mod["bootstrap_par"](a, b, DIAS_ANIO * ANIOS, N)
    r = simular2(g1, g2, 1e-9)
    rec = r["recibido"].mean()
    print(f"  {rg:>7.2f}%{rinde:>12.3f}%{('SI' if rinde >= 0.5 else 'NO'):>11}"
          f"{peor:>10.2f}%{('ok' if peor < 2 else 'ROMPE'):>8}"
          f"{rec:>12,.0f}${rec/ANIOS:>9,.0f}${(r['npag']>0).mean():>10.1%}")

print()
print("  El salto entre 0,96 y 1,05 no es gradual: es la diferencia entre poder")
print("  cobrar y no poder. Y 1,30% ya rompe el limite duro del 2%.")
print()
print(E)
print("LA VENTANA UTIL DEL RIESGO, CON EL TREND APAGADO")
print(E)
r_min = 0.5 * STOP_BP / TP
r_max = 2.0 * STOP_BP / PEOR_COLA_BP
print(f"  minimo para que un TP cualifique (0,5%)   : {r_min:>6.2f}%")
print(f"  maximo para no romper el 2% en la cola     : {r_max:>6.2f}%")
print(f"  ventana utilizable                         : "
      f"{r_min:.2f}% - {r_max:.2f}%")
print(f"  punto medio geometrico                     : "
      f"{(r_min*r_max)**0.5:>6.2f}%")
print()
print("  1,05% esta cerca del borde inferior: cualifica por 0,025 pp. Si el")
print("  bróker rellena el TP un poco peor, un dia cualificado se cae.")
print("  1,20% deja margen por los dos lados.")
