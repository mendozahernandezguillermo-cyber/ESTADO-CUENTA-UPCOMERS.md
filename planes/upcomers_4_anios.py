"""
RENTABILIDAD ESPERADA CON UPCOMERS A 4 AÑOS.

Configuracion: Upcomers Vanguard 25K, DD 7% trailing, diario 4%, w2 30%,
vol objetivo 4,5%. Se dan las dos variantes: TP 50 (lo que corre ahora) y
TP 40 (el cambio recomendado).

Sobre la palabra "rentabilidad": hay que decir respecto a QUE, porque las tres
respuestas se diferencian en tres ordenes de magnitud.
  - sobre los 25.000 $ de la cuenta -> enga\u00f1oso, ese dinero NO es tuyo y no
    responde a la pregunta de cuanto ganas tu;
  - sobre los 50 $ de la cuota -> es el unico capital tuyo en riesgo, y da
    porcentajes enormes que suenan a humo pero son literalmente correctos;
  - en dolares absolutos -> es el numero con el que se decide.
Se dan los tres.

El desglose año por año se hace con instantaneas SOBRE LOS MISMOS CAMINOS, no
restando medias de simulaciones distintas, para no confundir ruido con señal.
"""
import numpy as np

ns = {"__name__": "addendum"}
exec(compile(open("cobros_reales_addendum.py", encoding="utf-8")
             .read().split("# ---8<--- INFORME")[0],
             "cobros_reales_addendum.py", "exec"), ns)
simular2 = ns["simular2"]; mod = ns["mod"]
preparar = mod["preparar"]; CUOTA = mod["CUOTA"]

N = 40_000
ANIOS = 4
DIAS = 252 * ANIOS
CORTES = [252, 504, 756]
E = "=" * 94

res = {}
for tp in (50.0, 40.0):
    x1, x2, rg = preparar(tp)
    g1, g2 = mod["bootstrap_par"](x1, x2, DIAS, N)
    res[tp] = simular2(g1, g2, x2.std(), snaps=CORTES)

print(E)
print(f"UPCOMERS VANGUARD 25K A {ANIOS} AÑOS  ·  vol 4,5%  ·  DD 7% trailing")
print(E)
print(f"  {'':<30}{'TP 50 (ahora)':>18}{'TP 40 (recomendado)':>22}")
print("  " + "-" * 70)
f = []
for tp in (50.0, 40.0):
    r = res[tp]
    f.append(dict(
        bruto=r["recibido"].mean(), neto=r["neto"].mean(),
        med=np.median(r["recibido"]),
        p10=np.percentile(r["recibido"], 10),
        p90=np.percentile(r["recibido"], 90),
        pcob=(r["npag"] > 0).mean(), ncob=r["npag"].mean(),
        quema=r["quemada"].mean(), atr=r["atrapado"].mean(),
        bal=r["bal"].mean()))


def fila(etiq, clave, fmt="{:>17,.0f}$", extra="{:>21,.0f}$"):
    print(f"  {etiq:<30}" + fmt.format(f[0][clave]) + extra.format(f[1][clave]))


fila("dinero al bolsillo (media)", "bruto")
fila("neto de la cuota de 50 $", "neto")
fila("mediana", "med")
fila("percentil 10", "p10")
fila("percentil 90", "p90")
print(f"  {'probabilidad de cobrar algo':<30}{f[0]['pcob']:>17.1%} "
      f"{f[1]['pcob']:>20.1%} ")
print(f"  {'numero medio de cobros':<30}{f[0]['ncob']:>18.2f}"
      f"{f[1]['ncob']:>22.2f}")
print(f"  {'probabilidad de quemarla':<30}{f[0]['quema']:>17.1%} "
      f"{f[1]['quema']:>20.1%} ")
fila("atrapado (no retirable)", "atr")
fila("saldo final medio", "bal")

print()
print(E)
print("DESGLOSE AÑO POR AÑO (TP 40, mismos caminos, dinero al bolsillo)")
print(E)
r = res[40.0]
acum_prev = 0.0
print(f"  {'periodo':<12}{'acumulado':>12}{'del año':>11}{'% del total':>13}")
print("  " + "-" * 48)
series = [(f"año {i+1}", r["foto"][c] if c in r["foto"] else r["recibido"])
          for i, c in enumerate(CORTES)]
series.append((f"año {ANIOS}", r["recibido"]))
tot = r["recibido"].mean()
for etiq, arr in series:
    a = arr.mean()
    print(f"  {etiq:<12}{a:>11,.0f}${a-acum_prev:>10,.0f}${(a-acum_prev)/tot:>12.1%}")
    acum_prev = a

print()
print(E)
print("¿RENTABILIDAD SOBRE QUE?  (TP 40, 4 años)")
print(E)
b = f[1]["bruto"]; n = f[1]["neto"]
print(f"  dinero recibido en 4 años            : {b:>10,.0f} $")
print(f"  menos la cuota pagada una vez        : {n:>10,.0f} $ netos")
print()
print(f"  sobre los 50 $ de capital propio     : {n/50.0:>10.0%}"
      f"   ({(1+n/50.0)**0.25-1:>.0%} anualizado)")
print(f"  sobre los 25.000 $ de la cuenta      : {b/25000.0:>10.2%}"
      f"   ({b/25000.0/4:>.2%} al año)  <- ese dinero no es tuyo")
print(f"  en dolares por año                   : {n/ANIOS:>10,.0f} $/año")

print()
print(E)
print("REPARTO A 4 AÑOS (TP 40)")
print(E)
rr = res[40.0]["recibido"]
for lo, hi, etiq in ((-1, 1, "nada en 4 años"),
                     (1, 400, "1 cobro"),
                     (400, 900, "2 cobros"),
                     (900, 1700, "3 cobros"),
                     (1700, 1e9, "4 o mas")):
    m = (rr > lo) & (rr <= hi)
    print(f"  {etiq:<20}{m.mean():>8.1%}")
print()
print(f"  probabilidad de NO cobrar nunca en 4 años : "
      f"{(res[40.0]['npag']==0).mean():>6.1%}")
