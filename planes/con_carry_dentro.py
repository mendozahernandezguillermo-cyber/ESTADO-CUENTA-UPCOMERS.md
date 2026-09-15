"""
¿SIGUE EN PIE LA PROYECCION, CON EL CARRY DENTRO?

Hasta ahora TODOS mis modelos de EV han supuesto carry cero. Es el agujero mas
grande que he tenido, y se tapa aqui.

Carry medido en la cuenta real (6 unidades de swap, 364 al año):
    xagusd 993 $/año   xauusd 283   spcusd.c 98   eurusd 84
    gbpusd  30         audusd  28   usdjpy    8
    TOTAL 1.524 $/año = 6,10% de la cuenta

La #1 solo aguanta 1 noche por evento x 8 eventos = ~50 $/año. Despreciable.
El trend aguanta 364 noches: se come el resto.

Se comparan tres configuraciones, todas con el carry que les corresponde:
    A  como esta ahora            trend 7 mercados (con plata)
    B  sin plata                  trend 6 mercados
    C  solo FOMC                  trend apagado

Y ojo a la regla de los 6 dias con +0,5%: con el trend apagado hay 8 eventos al
año, de los que aciertan la mitad. Puede que no haya con que cualificar.
"""
import numpy as np
import pandas as pd

ns = {"__name__": "addendum"}
exec(compile(open("cobros_reales_addendum.py", encoding="utf-8")
             .read().split("# ---8<--- INFORME")[0],
             "cobros_reales_addendum.py", "exec"), ns)
simular2 = ns["simular2"]; mod = ns["mod"]
serie_s1 = mod["serie_s1"]; STOP_BP = mod["STOP_BP"]; CUENTA = mod["CUENTA"]

# --- series del trend: con plata (7 mercados) y sin plata (6)
src = open("../trend/trend_cfd.py", encoding="utf-8").read().split('E = "=" * 86')[0]
cfd = {"__name__": "cfd"}
import os
os.chdir("../trend")
exec(compile(src, "trend_cfd.py", "exec"), cfd)
os.chdir("../planes")
U7 = [m for m in cfd["UNIV_B"] if m != "Nasdaq 100"]
U6 = [m for m in U7 if m != "Plata"]
_, s2_7 = cfd["construir"](U7)
_, s2_6 = cfd["construir"](U6)

RIESGO = 1.05          # el ajuste que hace que un TP de 40 bp rinda 0,525%
TP = 40.0
MULT7 = 0.723 * 7.0 / 8.0
MULT6 = 0.723 * 6.0 / 8.0
DIAS_ANIO = 252
N, ANIOS = 40_000, 4

CARRY = {"A": 1_524.0, "B": 1_524.0 - 993.0, "C": 50.0}


def construir_patas(s2, mult, carry_anual):
    mult1 = (RIESGO / 100.0) / (STOP_BP / 1e4)
    idx = s2.index if s2 is not None else None
    base = pd.Series(0.0, index=idx)
    for ts, r in serie_s1(TP).items():
        if ts in base.index:
            base.loc[ts] = r
    D = pd.DataFrame({"s1": base, "s2": (s2 if s2 is not None else 0.0)}).dropna()
    D = D[D.index >= "2011-01-01"]
    drag = carry_anual / CUENTA / DIAS_ANIO           # fraccion por dia de mercado
    a = (D["s1"] * mult1).values
    b = (D["s2"] * mult).values - drag                # el carry entra aqui
    return a, b


E = "=" * 96
print(E)
print(f"EV A {ANIOS} AÑOS CON EL CARRY DENTRO  (riesgo {RIESGO}%, TP {TP:.0f} bp)")
print(E)
print(f"  {'config':<26}{'carry/año':>11}{'retorno':>10}{'neto':>9}"
      f"{'recibido':>11}{'por año':>10}{'P(cobra)':>10}{'P(quema)':>10}")
print("  " + "-" * 92)

casos = [
    ("A  como esta (con plata)", s2_7, MULT7, CARRY["A"]),
    ("B  sin plata",             s2_6, MULT6, CARRY["B"]),
    ("C  solo FOMC",             None, 0.0,   CARRY["C"]),
]
guarda = {}
for nom, s2, mult, carry in casos:
    if s2 is None:
        s2 = pd.Series(0.0, index=s2_7.index)
    a, b = construir_patas(s2, mult, carry)
    bruto = (a + b + carry / CUENTA / DIAS_ANIO).mean() * DIAS_ANIO * CUENTA
    neto = (a + b).mean() * DIAS_ANIO * CUENTA
    g1, g2 = mod["bootstrap_par"](a, b, DIAS_ANIO * ANIOS, N)
    sd = b.std() if b.std() > 0 else 1e-9
    r = simular2(g1, g2, sd)
    guarda[nom] = r
    rec = r["recibido"].mean()
    print(f"  {nom:<26}{-carry:>10,.0f}${bruto:>9,.0f}${neto:>8,.0f}$"
          f"{rec:>10,.0f}${rec/ANIOS:>9,.0f}${(r['npag']>0).mean():>10.1%}"
          f"{r['quemada'].mean():>10.1%}")

print()
print(E)
print("¿HAY CON QUE CUALIFICAR LOS 6 DIAS DE +0,5%?")
print(E)
print(f"  Un TP de {TP:.0f} bp con riesgo {RIESGO}% rinde "
      f"{TP/STOP_BP*RIESGO:.3f}% de la cuenta.")
print(f"  El umbral de la firma es 0,500%. Margen: "
      f"{TP/STOP_BP*RIESGO-0.5:.3f} puntos porcentuales.")
print()
print("  Con el trend ENCENDIDO ese acierto tiene que sobrevivir al ruido del")
print("  trend de ese dia. Con el trend APAGADO cualifica siempre, pero solo")
print("  hay ~8 eventos al año y aciertan la mitad: ~4-5 dias cualificados/año")
print("  contra los 6 que pide la firma.")

print()
print(E)
print("VEREDICTO")
print(E)
for nom in guarda:
    r = guarda[nom]
    print(f"  {nom:<26} recibido {r['recibido'].mean():>7,.0f} $ en {ANIOS} años"
          f"   P(cobrar algo) {(r['npag']>0).mean():>5.1%}")
print()
print("  Comparar con lo que proyecte antes de conocer el carry: 749 $ / 187 $ al año.")
