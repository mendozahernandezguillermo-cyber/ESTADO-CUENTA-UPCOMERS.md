"""
¿CUANTO IMPORTA EL REPARTO DE BENEFICIOS, QUE SIGUE SIN CONFIRMAR?

Lleva turnos en la lista de pendientes: use 90% y la firma anuncia "hasta 100%".
Pero al ver que en el año 1 el cobro neto modal es EXACTAMENTE 174 $ me di
cuenta de algo: si el tope MUERDE, el reparto deja de importar para el importe
cobrado, porque cobras el tope y no tu porcentaje.

  bruto = min(beneficio_segmento x reparto, tope)

Con un segmento tipico de ~1.450 $ y tope 250 $, el primer termino es 1.305 $
con reparto 90% y 1.450 $ con 100%. Los dos superan 250, asi que bruto = 250 en
ambos casos. El reparto solo cambia 'sacado' = bruto/reparto, o sea cuanto sale
del saldo, y por tanto el atrapado.

Si esto es cierto, la incognita del reparto esta CERRADA sin tener que
confirmarla en el panel. Se mide.
"""
import numpy as np

ns = {"__name__": "addendum"}
exec(compile(open("cobros_reales_addendum.py", encoding="utf-8")
             .read().split("# ---8<--- INFORME")[0],
             "cobros_reales_addendum.py", "exec"), ns)
simular2 = ns["simular2"]; mod = ns["mod"]

N = 20_000
E = "=" * 92
print(E)
print("SENSIBILIDAD AL REPARTO DE BENEFICIOS  (TP 40 bp)")
print(E)
print(f"  {'reparto':>9}{'EV año 1':>11}{'EV 2 años/año':>15}"
      f"{'cobro modal':>13}{'atrapado 2a':>13}{'P(quema) 2a':>13}")
print("  " + "-" * 74)
for split in (0.80, 0.85, 0.90, 0.95, 1.00):
    mod["SPLIT"] = split
    ns["SPLIT"] = split
    b1, b2, _ = mod["preparar"](40.0)
    out = []
    for anios in (1, 2):
        g1, g2 = mod["bootstrap_par"](b1, b2, 252 * anios, N)
        out.append(simular2(g1, g2, b2.std()))
    n1 = out[0]["neto"]
    gan = n1[n1 > 0]
    modal = np.median(gan) if gan.size else float("nan")
    print(f"  {split:>8.0%}{n1.mean():>10,.0f}${out[1]['neto'].mean()/2:>14,.0f}$"
          f"{modal:>12,.0f}${out[1]['atrapado'].mean():>12,.0f}$"
          f"{out[1]['quemada'].mean():>13.1%}")

print()
print("  Si la columna 'EV año 1' apenas se mueve entre 80% y 100%, la incognita")
print("  del reparto queda cerrada por el tope y se puede sacar de la lista.")
