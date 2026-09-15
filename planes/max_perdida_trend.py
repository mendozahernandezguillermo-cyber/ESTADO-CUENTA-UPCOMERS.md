"""
LA PATA DEL TREND CONTRA EL MISMO LIMITE DURO DEL 2% POR OPERACION.

La #1 no es la unica expuesta. El trend mantiene 7 posiciones abiertas, y las
mantiene SEMANAS o MESES (el rebalanceo solo las cambia si la señal se mueve
mas de InpUmbralCambio=20%). Una sola de ellas puede acumular mas de un 2% de
perdida sobre la cuenta sin que ningun stop la corte, porque el trend NO LLEVA
STOP: sale por señal o por rebalanceo.

Tamaños REALES de las posiciones abiertas, deducidos del log del broker y de
los nocionales por lote medidos:
"""
import glob, os
import numpy as np
import pandas as pd

CUENTA = 25_000.0
LIMITE = 0.02 * CUENTA           # 500 $, hard breach

# nocional por lote medido en el broker x lotes reales abiertos el 3-sep
POS = {                       # simbolo: (lotes, nocional por lote, proxy)
    "SPCUSD.c": (0.02, 76_733.0, "SPY"),
    "XAUUSD":   (0.02, 44_315.0, "GLD"),
    "XAGUSD":   (0.01, 33_050.0, "SLV"),
    "EURUSD":   (0.04, 115_966.0, "EURUSDX"),
    "USDJPY":   (0.03, 99_999.0, "USDJPYX"),
    "GBPUSD":   (0.03, 134_946.0, "GBPUSDX"),
    "AUDUSD":   (0.04, 71_920.0, "AUDUSDX"),
}
VENTANAS = (21, 63, 126, 252)    # 1, 3, 6, 12 meses de mercado

DIR = "../trend/datos"


def cargar(nom):
    p = os.path.join(DIR, nom + ".csv")
    d = pd.read_csv(p)
    col = [c for c in d.columns if c.lower() in ("date", "fecha")][0]
    pc = [c for c in d.columns if c.lower() in ("close", "adj close", "cierre")]
    d = d[[col, pc[0]]].dropna()
    d.columns = ["f", "p"]
    d["f"] = pd.to_datetime(d["f"], errors="coerce")
    return d.dropna().set_index("f")["p"].astype(float).sort_index()


E = "=" * 96
print(E)
print("¿PUEDE UNA SOLA POSICION DEL TREND ROMPER EL LIMITE DEL 2% (500 $)?")
print(E)
print(f"  {'simbolo':<11}{'nocional':>10}{'% cuenta':>10}{'mov. que':>10}"
      f"{'  peor excursion adversa por ventana':<38}")
print(f"  {'':<11}{'':>10}{'':>10}{'rompe':>10}"
      f"{'1 mes':>9}{'3 meses':>9}{'6 meses':>9}{'12 meses':>10}")
print("  " + "-" * 88)

resumen = []
for sim, (lotes, noc_lote, proxy) in POS.items():
    noc = lotes * noc_lote
    umbral = LIMITE / noc                     # movimiento adverso que rompe
    try:
        s = cargar(proxy)
    except Exception as e:
        print(f"  {sim:<11}  (sin datos: {e})")
        continue
    peores = []
    for w in VENTANAS:
        # peor caida desde el precio de entrada dentro de una ventana de w dias
        mn = s.rolling(w).min().shift(-w + 1)
        caida = (1.0 - mn / s).dropna()
        peores.append(caida.max())
    resumen.append((sim, noc, umbral, peores))
    print(f"  {sim:<11}{noc:>9,.0f}${noc/CUENTA:>9.1%}{umbral:>9.1%}"
          + "".join(f"{p:>9.1%}" if i < 3 else f"{p:>10.1%}"
                    for i, p in enumerate(peores)))

print()
print(E)
print("VEREDICTO POR POSICION  (¿rompe el 2% antes del siguiente rebalanceo?)")
print(E)
print(f"  {'simbolo':<11}{'a 1 mes':>10}{'a 3 meses':>12}{'a 6 meses':>12}"
      f"{'a 12 meses':>13}")
print("  " + "-" * 60)
riesgo_total = 0
for sim, noc, umbral, peores in resumen:
    marcas = []
    for p in peores:
        marcas.append("ROMPE" if p > umbral else "ok")
    if marcas[1] == "ROMPE":
        riesgo_total += 1
    print(f"  {sim:<11}{marcas[0]:>10}{marcas[1]:>12}{marcas[2]:>12}"
          f"{marcas[3]:>13}")

print()
print(f"  posiciones que romperian el limite en un horizonte de 3 meses: "
      f"{riesgo_total} de {len(resumen)}")
print()
print("  Recordatorio de por que esto es grave y distinto de la #1:")
print("   - el trend NO LLEVA STOP. Sale por señal o por rebalanceo mensual.")
print("   - el limite es HARD BREACH: cierra la cuenta al instante, aunque")
print("     la cuenta este en beneficio y aunque las otras 6 posiciones ganen.")
print("   - InpMaxPerdidaPosPct del Guardian esta en 3.0, por encima del 2%")
print("     real, asi que hoy NO cortaria a tiempo.")
