"""
RENDIMIENTO ESPERADO EN DOLARES, AÑO 1 / 2 / 3 / 4.

Configuracion exacta que quedo montada (leida de las capturas del dialogo):
  #1 FOMC   stop 80 bp · TP 40 bp · riesgo 0,96% de la equity
  #2 TREND  7 mercados operables de 8 listados · vol 7,23%/mercado · divisor 8
  Guardian  trailing 7% · diario 4% a 00:00 UTC · factor 5%/0,25

La media sola engaña: la distribucion tiene dos picos (cobras o no cobras), asi
que se dan tambien la MEDIANA y la PROBABILIDAD de cobrar algo cada año. Los
incrementos anuales se calculan sobre LOS MISMOS caminos con instantaneas, no
restando medias de simulaciones distintas.
"""
import numpy as np
import pandas as pd

ns = {"__name__": "addendum"}
exec(compile(open("cobros_reales_addendum.py", encoding="utf-8")
             .read().split("# ---8<--- INFORME")[0],
             "cobros_reales_addendum.py", "exec"), ns)
simular2 = ns["simular2"]; mod = ns["mod"]
serie_s1 = mod["serie_s1"]; STOP_BP = mod["STOP_BP"]

B7 = pd.read_csv("../trend/serie_cfd_b7.csv", index_col=0, parse_dates=True)
RIESGO, TP = 0.96, 40.0
MULT_TREND = 0.723 * 7.0 / 8.0
N, ANIOS = 60_000, 4
CORTES = [252, 504, 756]

mult1 = (RIESGO / 100.0) / (STOP_BP / 1e4)
s1 = pd.Series(0.0, index=B7.index)
for ts, r in serie_s1(TP).items():
    if ts in s1.index:
        s1.loc[ts] = r
D = pd.DataFrame({"s1": s1, "s2": B7["s2"]}).dropna()
D = D[D.index >= "2011-01-01"]
a = (D["s1"] * mult1).values
b = (D["s2"] * MULT_TREND).values

g1, g2 = mod["bootstrap_par"](a, b, 252 * ANIOS, N)
r = simular2(g1, g2, b.std(), snaps=CORTES)

acum = [r["foto"][252], r["foto"][504], r["foto"][756], r["recibido"]]
inc = [acum[0], acum[1] - acum[0], acum[2] - acum[1], acum[3] - acum[2]]

E = "=" * 88
print(E)
print("RENDIMIENTO ESPERADO EN DOLARES, POR AÑO")
print(E)
print(f"  {'año':<6}{'esperado':>11}{'mediana':>10}{'P(cobras':>11}"
      f"{'acumulado':>12}{'mediana':>10}{'P(has':>9}")
print(f"  {'':<6}{'del año':>11}{'del año':>10}{'ese año)':>11}"
      f"{'esperado':>12}{'acum.':>10}{'cobrado)':>9}")
print("  " + "-" * 69)
for i in range(4):
    print(f"  {i+1:<6}{inc[i].mean():>10,.0f}${np.median(inc[i]):>9,.0f}$"
          f"{(inc[i] > 0).mean():>11.1%}{acum[i].mean():>11,.0f}$"
          f"{np.median(acum[i]):>9,.0f}${(acum[i] > 0).mean():>9.1%}")

print()
print(E)
print("LO QUE PUEDE PASAR CADA AÑO, EN DETALLE")
print(E)
for i in range(4):
    x = inc[i]
    print(f"\n  AÑO {i+1}   esperado {x.mean():,.0f} $")
    for lo, hi, etq in ((-1, 1, "nada"), (1, 300, "un cobro"),
                        (300, 800, "dos cobros"), (800, 1e9, "tres o mas")):
        m = (x > lo) & (x <= hi)
        if m.mean() > 0.0005:
            print(f"     {etq:<14}{m.mean():>7.1%}")

print()
print(E)
print("RESUMEN")
print(E)
tot = acum[3].mean()
print(f"  total esperado a 4 años      : {tot:>8,.0f} $")
print(f"  media por año                : {tot/4:>8,.0f} $")
print(f"  mediana a 4 años             : {np.median(acum[3]):>8,.0f} $")
print(f"  percentil 10 / percentil 90  : {np.percentile(acum[3],10):>8,.0f} $"
      f" / {np.percentile(acum[3],90):,.0f} $")
print(f"  P(no cobrar nada en 4 años)  : {(acum[3] <= 0).mean():>8.1%}")
print(f"  P(quemar la cuenta)          : {r['quemada'].mean():>8.1%}")
print()
print("  El reparto es tan desigual porque los topes por cobro SUBEN de tramo:")
print("  250, 500, 750, 1.000... El año 1 solo alcanza el primer tramo, y para")
print("  eso hace falta pasar 6 dias con +0,5% y la regla del mejor dia.")
