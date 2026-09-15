"""
EL TEST QUE DE VERDAD DECIDE: bootstrap SOBRE LOS 117 EVENTOS.

En cobros_reales_ruido.py salio t = 79,74 para la diferencia 40-50. Ese numero
NO sirve para esta decision y hay que decirlo claro: mide solo el ruido Monte
Carlo de los caminos simulados, condicionando en los 117 eventos EXACTOS que
ocurrieron. Con 20.000 caminos ese ruido tiende a cero por construccion. Que
tienda a cero no dice nada sobre si 40 bp seguira ganando en los proximos
eventos: eso es error de MUESTREO de los eventos, y es justo la objecion por
la que rechace el argmax de 40 bp la primera vez.

Test correcto: remuestrear CON REEMPLAZO los 117 eventos, recalcular la serie
de la #1 para cada TP sobre ese remuestreo, y contar en que fraccion de
remuestreos 40 bp sigue ganando a 50 bp. Si 40 gana en el 55% de los mundos
posibles, es una moneda al aire disfrazada de optimizacion.

Nota: los eventos se recolocan en los MISMOS huecos del calendario, para no
alterar ni el numero de eventos por año ni la alineacion con la pata #2.
"""
import numpy as np
import pandas as pd

ns = {"__name__": "addendum"}
exec(compile(open("cobros_reales_addendum.py", encoding="utf-8")
             .read().split("# ---8<--- INFORME")[0],
             "cobros_reales_addendum.py", "exec"), ns)
simular2 = ns["simular2"]; mod = ns["mod"]
serie_s1 = mod["serie_s1"]; s2_full = mod["s2_full"]
BLOQUE = mod["BLOQUE"]; STOP_BP = mod["STOP_BP"]

TPS = (30.0, 40.0, 50.0, 60.0)
CRUDO = {tp: serie_s1(tp) for tp in TPS}          # dict fecha -> retorno
FECHAS = [f for f in CRUDO[50.0] if f in s2_full.index]
NEV = len(FECHAS)
print(f"eventos alineados con la pata #2: {NEV}")

VAL = {tp: np.array([CRUDO[tp][f] for f in FECHAS]) for tp in TPS}
W2, VOL = 0.30, 0.045
NC, DIAS, REPS = 4_000, 504, 40


def preparar_de(vals):
    """misma normalizacion que preparar(), pero con retornos ya dados"""
    s1 = pd.Series(0.0, index=s2_full.index)
    s1.loc[FECHAS] = vals
    D = pd.DataFrame({"s1": s1, "s2": s2_full}).dropna()
    D = D[D.index >= "2011-01-01"]
    cart = (1 - W2) * D["s1"] + W2 * D["s2"]
    lev = VOL / (cart.std() * np.sqrt(252))
    return ((1 - W2) * D["s1"] * lev).values, (W2 * D["s2"] * lev).values


def indices(rng, largo):
    nb = int(np.ceil(DIAS / BLOQUE))
    ini = rng.integers(0, largo - BLOQUE, size=(NC, nb))
    return (ini[:, :, None] + np.arange(BLOQUE)[None, None, :]
            ).reshape(NC, -1)[:, :DIAS]


rng = np.random.default_rng(777)
res = {tp: [] for tp in TPS}
for k in range(REPS):
    pick = rng.integers(0, NEV, size=NEV)          # remuestreo de EVENTOS
    x1x2 = {tp: preparar_de(VAL[tp][pick]) for tp in TPS}
    largo = len(x1x2[50.0][0])
    idx = indices(rng, largo)
    est = rng.bit_generator.state
    for tp in TPS:
        x1, x2 = x1x2[tp]
        mod["RNG"].bit_generator.state = est
        r = simular2(x1[idx], x2[idx], x2.std())
        res[tp].append(r["neto"].mean() / 2)

E = "=" * 92
print()
print(E)
print(f"BOOTSTRAP SOBRE LOS {NEV} EVENTOS  ({REPS} remuestreos, {NC:,} caminos cada uno)")
print(E)
print(f"  {'TP':>5}{'EV medio':>11}{'desv.tip':>11}{'p5':>9}{'p50':>9}{'p95':>9}")
print("  " + "-" * 54)
for tp in TPS:
    a = np.array(res[tp])
    print(f"  {tp:>4.0f}{a.mean():>10,.0f}${a.std(ddof=1):>10,.0f}$"
          f"{np.percentile(a,5):>8,.0f}${np.percentile(a,50):>8,.0f}$"
          f"{np.percentile(a,95):>8,.0f}$")

d = np.array(res[40.0]) - np.array(res[50.0])
print()
print(f"  diferencia 40-50 por remuestreo: media {d.mean():+,.0f} $  "
      f"desv.tip {d.std(ddof=1):,.0f} $")
print(f"  40 bp gana a 50 bp en {(d>0).mean():.0%} de los mundos remuestreados")
print(f"  t de la diferencia = {d.mean()/(d.std(ddof=1)/np.sqrt(len(d))):,.2f}")
print()
gana = {tp: 0 for tp in TPS}
M = np.array([res[tp] for tp in TPS])
for j in range(REPS):
    gana[TPS[int(np.argmax(M[:, j]))]] += 1
print("  ¿quien es el argmax en cada mundo?  " +
      "  ".join(f"TP{int(t)}: {gana[t]/REPS:.0%}" for t in TPS))
print()
print("  Comparar con el t=79,74 del test Monte Carlo: ese numero era un artefacto")
print("  de subir los caminos. Este es el que manda.")
