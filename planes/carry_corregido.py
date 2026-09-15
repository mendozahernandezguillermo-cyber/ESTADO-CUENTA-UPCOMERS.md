"""
CORRECCION DEL CARRY: CONTE MAL LAS NOCHES.

Dato nuevo: martes 21:38 en Villahermosa (UTC-6) = MIERCOLES 05:38 en el
servidor (GMT+2). O sea que el rollover triple del miercoles YA se cobro, y los
-25,12 $ de la captura YA lo incluyen. Yo lo conte como 4 noches simples y
encima anuncie el triple como si estuviera por venir.

Recuento correcto desde la apertura (jueves 3-sep 16:00 servidor):
    rollover a viernes 4      x1
    rollover a lunes 7        x1
    rollover a martes 8       x1
    rollover a miercoles 9    x3   <-- el triple, ya cobrado
    -------------------------------
    total                     6 unidades de swap

Un año tiene 364 unidades (52 semanas x 7: cinco rollovers, con el miercoles
contando triple para cubrir el fin de semana).
"""
CUENTA = 25_000.0
UNIDADES = 6          # y no 4
UNIDADES_ANIO = 364
RETORNO_BRUTO = 0.035 * CUENTA

POS = {
    "xagusd":   (3_313.50, -16.36),
    "xauusd":   (8_755.14,  -4.66),
    "spcusd.c": (1_535.88,  -1.62),
    "eurusd":   (4_651.76,  -1.38),
    "gbpusd":   (4_063.35,  -0.50),
    "audusd":   (2_888.56,  -0.46),
    "usdjpy":   (3_000.00,  -0.14),
}

E = "=" * 90
tot = sum(v[1] for v in POS.values())
print(E)
print("CARRY CORREGIDO  (6 unidades de swap, no 4)")
print(E)
print(f"  {'simbolo':<11}{'nocional':>11}{'swap':>9}{'$/unidad':>11}"
      f"{'$/año':>10}{'% nocional':>12}{'% cuenta':>11}")
print("  " + "-" * 76)
for sim, (noc, sw) in sorted(POS.items(), key=lambda x: x[1][1]):
    por = sw / UNIDADES
    anio = -por * UNIDADES_ANIO
    print(f"  {sim:<11}{noc:>10,.0f}${sw:>8.2f}${por:>10.2f}${anio:>9,.0f}$"
          f"{anio/noc:>11.1%}{anio/CUENTA:>11.2%}")
print("  " + "-" * 76)
carry = -tot / UNIDADES * UNIDADES_ANIO
print(f"  {'TOTAL':<11}{sum(v[0] for v in POS.values()):>10,.0f}$"
      f"{tot:>8.2f}${tot/UNIDADES:>10.2f}${carry:>9,.0f}${'':>11}"
      f"{carry/CUENTA:>11.2%}")

print()
print(E)
print("EL VEREDICTO, CON EL NUMERO BUENO")
print(E)
antes = -tot / 4 * 365
print(f"  lo que dije (mal, 4 noches)    : {antes:>8,.0f} $/año   "
      f"{antes/CUENTA:>6.2%}")
print(f"  correcto (6 unidades)          : {carry:>8,.0f} $/año   "
      f"{carry/CUENTA:>6.2%}")
print(f"  retorno bruto esperado         : {RETORNO_BRUTO:>8,.0f} $/año   3.50%")
print(f"  el carry es                    : {carry/RETORNO_BRUTO:>8.2f} veces el retorno")
print()
print("  Me pase un 50% al alza. La conclusion NO cambia: el carry sigue siendo")
print("  mayor que todo lo que la estrategia gana, y el trend sigue siendo el")
print("  agujero. Pero el numero bueno es 6,1% y no 9,2%.")

print()
print(E)
print("¿CUANTO CUESTA ESPERAR A DECIDIR CON DATOS?")
print(E)
por_noche = -tot / UNIDADES
print(f"  carry por unidad de swap       : {por_noche:>8.2f} $")
print(f"  de eso, la plata               : {16.36/UNIDADES:>8.2f} $  "
      f"({16.36/-tot:.0%})")
print()
for d, etq in ((1, "una noche"), (2, "dos noches"), (7, "una semana"),
               (22, "hasta el rebalanceo del 1-oct")):
    print(f"  {etq:<32}{por_noche*d:>8.2f} $")
print()
print("  Esperar a medir bien cuesta unos 4 $ por noche. Decidir tres cosas a")
print("  la vez a las 21:40 con un carry que acabo de corregir un 50% cuesta")
print("  mas que eso.")

print()
print(E)
print("LOS CUATRO RELOJES, CON TU HORA")
print(E)
print("  Villahermosa (UTC-6)   martes    21:38   <- tu")
print("  UTC                    miercoles 03:38")
print("  servidor (GMT+2)       miercoles 05:38   <- el triple ya paso")
print("  Nueva York (EDT)       martes    23:38")
print()
print("  Proximos hitos:")
print("    15-16 sep   FOMC. El EA entra el dia ANTERIOR a las 13:57 locales.")
print("    1 oct       primer rebalanceo que cierra y reabre, 08:00 locales.")
