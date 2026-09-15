"""
¿ES SEÑAL O ES RUIDO? 40 bp contra 50 bp.

En el barrido, el EV salio 184 / 195 / 165 / 147 / 116 para 30 / 40 / 50 / 60 / 80.
Que 50 caiga por debajo de 30 Y de 40 rompe la monotonia y huele a ruido de
bootstrap. Si la diferencia 40-50 no supera su propio error, cambiar el EA en
vivo seria repetir el error del argmax que ya rechace una vez.

Metodo: numeros aleatorios comunes. Para cada semilla se sortean UNA vez los
indices del bootstrap y se aplican a las dos series de TP, asi la diferencia
esta emparejada y su varianza cae muchisimo. Se repite sobre semillas
independientes y se mira la dispersion de la diferencia.
"""
import numpy as np

ns = {"__name__": "addendum"}
exec(compile(open("cobros_reales_addendum.py", encoding="utf-8")
             .read().split("# ---8<--- INFORME")[0],
             "cobros_reales_addendum.py", "exec"), ns)
simular2 = ns["simular2"]; preparar = ns["preparar"]; mod = ns["mod"]
BLOQUE = mod["BLOQUE"]

NC, DIAS = 12_000, 504
SERIES = {tp: preparar(tp) for tp in (30.0, 40.0, 50.0, 60.0)}


def indices(rng, n_dias, n_caminos, largo):
    nb = int(np.ceil(n_dias / BLOQUE))
    ini = rng.integers(0, largo - BLOQUE, size=(n_caminos, nb))
    return (ini[:, :, None] + np.arange(BLOQUE)[None, None, :]
            ).reshape(n_caminos, -1)[:, :n_dias]


E = "=" * 92
print(E)
print("EV POR SEMILLA CON NUMEROS ALEATORIOS COMUNES  (horizonte 2 años)")
print(E)
print(f"  {'semilla':>9}" + "".join(f"{('TP '+str(int(t))):>10}" for t in SERIES)
      + f"{'40 menos 50':>14}")
print("  " + "-" * 66)
filas = {t: [] for t in SERIES}
difs = []
for s in range(8):
    rng = np.random.default_rng(1000 + s)
    largo = len(next(iter(SERIES.values()))[0])
    idx = indices(rng, DIAS, NC, largo)
    est = rng.bit_generator.state
    ev = {}
    for tp, (x1, x2, _) in SERIES.items():
        mod["RNG"].bit_generator.state = est      # mismo ruido intradia
        r = simular2(x1[idx], x2[idx], x2.std())
        ev[tp] = r["neto"].mean() / 2
        filas[tp].append(ev[tp])
    d = ev[40.0] - ev[50.0]
    difs.append(d)
    print(f"  {1000+s:>9}" + "".join(f"{ev[t]:>9,.0f}$" for t in SERIES)
          + f"{d:>13,.0f}$")

print("  " + "-" * 66)
print(f"  {'media':>9}" + "".join(f"{np.mean(filas[t]):>9,.0f}$" for t in SERIES)
      + f"{np.mean(difs):>13,.0f}$")
print(f"  {'desv.tip':>9}" + "".join(f"{np.std(filas[t],ddof=1):>9,.0f}$" for t in SERIES)
      + f"{np.std(difs,ddof=1):>13,.0f}$")

d = np.array(difs)
t = d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))
print()
print(f"  diferencia 40-50 emparejada: {d.mean():+,.0f} $/año  "
      f"error tipico {d.std(ddof=1)/np.sqrt(len(d)):,.0f} $  t = {t:,.2f}")
print(f"  signo positivo en {int((d>0).sum())} de {len(d)} semillas")
print()
if abs(t) < 2:
    print("  VEREDICTO: no se distingue de cero. No justifica tocar el EA en vivo.")
else:
    print("  VEREDICTO: la diferencia sobrevive al ruido del bootstrap.")
