"""
REOPTIMIZAR w2 Y LA VOL OBJETIVO CONTRA EL MODELO DE COBROS REAL.

Motivo: w2=30% y vol=4,5% se eligieron maximizando P(cobro) bajo el modelo
VIEJO, que suponia que se retiraba todo el beneficio y la cuenta se reiniciaba.
Ese objetivo ya no existe. Bajo el modelo real la pinza (mejor dia x tope)
dice que el segmento necesario es ~5,2 veces el dia mas grande, asi que
CUALQUIER cosa que suavice el P&L diario deberia liberar mas dinero.
La pata #2 (trend) es mucho mas suave que la #1 (FOMC), luego subir w2 es,
a priori, el dial de primer orden. Se mide en vez de suponerlo.
"""
import numpy as np

# el addendum ya carga el script principal en su namespace; se ejecuta solo
# la parte anterior a los prints y se reutilizan sus funciones
ns = {"__name__": "addendum"}
exec(compile(open("cobros_reales_addendum.py", encoding="utf-8")
             .read().split("# ---8<--- INFORME")[0],
             "cobros_reales_addendum.py", "exec"), ns)
simular2 = ns["simular2"]
preparar = ns["preparar"]; bootstrap_par = ns["bootstrap_par"]

E = "=" * 92
print(E)
print("REOPTIMIZAR PESO DE LA #2 Y VOL OBJETIVO  (TP 40 bp, horizonte 2 años)")
print(E)
print(f"  {'w2':>5}{'vol':>7}{'riesgo#1':>10}{'P(cobro)':>10}{'1er cobro':>11}"
      f"{'EV anual':>10}{'atrapado':>10}{'%liberado':>11}{'P(quema)':>10}")
print("  " + "-" * 84)
mejor = None
for vol in (0.035, 0.045, 0.055):
    for w2 in (0.30, 0.45, 0.60, 0.75):
        b1, b2, rg = preparar(40.0, w2=w2, vol=vol)
        g1, g2 = bootstrap_par(b1, b2, 504, 12_000)
        r = simular2(g1, g2, b2.std(), traza=True)
        m = ~np.isnan(r["seg1"])
        lib = (np.median(r["sal1"][m] / np.maximum(r["seg1"][m], 1e-9))
               if m.any() else np.nan)
        dd = r["d1"][r["d1"] >= 0]
        ev = r["neto"].mean() / 2
        print(f"  {w2:>5.0%}{vol:>7.1%}{rg:>9.2f}%{(r['npag']>0).mean():>10.1%}"
              f"{(np.median(dd) if len(dd) else np.nan):>10.0f}d{ev:>9,.0f}$"
              f"{r['atrapado'].mean():>9,.0f}${lib:>10.0%}"
              f"{r['quemada'].mean():>10.1%}")
        if mejor is None or ev > mejor[0]:
            mejor = (ev, w2, vol, r["quemada"].mean(), (r["npag"] > 0).mean())
    print()

print(f"  Maximo de EV: w2={mejor[1]:.0%}  vol={mejor[2]:.1%}  ->  "
      f"{mejor[0]:,.0f} $/año, P(quema) {mejor[3]:.1%}, P(cobro) {mejor[4]:.1%}")
print("  (comparar con la configuracion en vivo: w2=30%, vol=4,5%, TP 50)")
