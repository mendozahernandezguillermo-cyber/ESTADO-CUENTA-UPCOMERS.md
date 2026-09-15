"""
EL CARRY REAL, MEDIDO POSICION POR POSICION.

Datos de las capturas del 9-sep 04:55 hora servidor. Las posiciones se abrieron
el 3-sep 16:00, o sea 4 rollovers cobrados (jue/vie, vie/sab, lun/mar, mar/mie).
El triple del miercoles todavia NO ha entrado.

Especificacion de EURUSD leida del broker:
  Contract size 100.000 EUR · Swap type IN POINTS
  Swap long -8,26  ·  Swap short +1,05
  Swap rates: lun 1, mar 1, MIE 3, jue 1, vie 1
  Comisiones: 5 USD por lote, "instant by deal volume"

Los dos hechos que importan:
  1. el swap en corto es POSITIVO (+1,05) donde en largo es -8,26. La direccion
     lo cambia todo, y el trend va largo y corto.
  2. la comision es calderilla: 0,19 lotes en total x 5 USD = 0,95 $.
     Asi que el cargo que llevabamos persiguiendo era swap desde el principio.
"""
CUENTA = 25_000.0
NOCHES = 4

# simbolo: (nocional Value del broker, swap acumulado, profit)
POS = {
    "audusd":   (2_888.56,  -0.46,   11.76),
    "eurusd":   (4_651.76,  -1.38,    2.68),
    "gbpusd":   (4_063.35,  -0.50,    8.82),
    "spcusd.c": (1_535.88,  -1.62,   -6.24),
    "usdjpy":   (3_000.00,  -0.14,  -37.88),
    "xagusd":   (3_313.50, -16.36,   -4.80),
    "xauusd":   (8_755.14,  -4.66, -173.94),
}

E = "=" * 94
tot_noc = sum(v[0] for v in POS.values())
tot_swap = sum(v[1] for v in POS.values())

print(E)
print("EL CARRY, POSICION POR POSICION")
print(E)
print(f"  {'simbolo':<11}{'nocional':>11}{'% cuenta':>10}{'swap 4 noches':>15}"
      f"{'$/noche':>10}{'% anual del':>13}{'% anual de':>12}{'% del':>8}")
print(f"  {'':<11}{'':>11}{'':>10}{'':>15}{'':>10}{'nocional':>13}"
      f"{'la cuenta':>12}{'carry':>8}")
print("  " + "-" * 88)
for sim, (noc, sw, pl) in sorted(POS.items(), key=lambda x: x[1][1]):
    porn = sw / NOCHES
    an_noc = -porn * 365 / noc
    an_cta = -porn * 365 / CUENTA
    print(f"  {sim:<11}{noc:>10,.0f}${noc/CUENTA:>9.1%}{sw:>14.2f}$"
          f"{porn:>9.2f}${an_noc:>12.1%}{an_cta:>11.2%}{sw/tot_swap:>8.0%}")
print("  " + "-" * 88)
print(f"  {'TOTAL':<11}{tot_noc:>10,.0f}${tot_noc/CUENTA:>9.1%}"
      f"{tot_swap:>14.2f}${tot_swap/NOCHES:>9.2f}$"
      f"{'':>12}{-tot_swap/NOCHES*365/CUENTA:>11.2%}")

print()
print(E)
print("EL VEREDICTO ECONOMICO")
print(E)
carry = -tot_swap / NOCHES * 365
print(f"  carry proyectado a un año        : {carry:>9,.0f} $   "
      f"({carry/CUENTA:>.2%} de la cuenta)")
print(f"  retorno bruto esperado           : {0.035*CUENTA:>9,.0f} $   (3,50%)")
print(f"  diferencia                       : {0.035*CUENTA-carry:>9,.0f} $")
print()
print("  Con las 7 posiciones LARGAS, el carry es "
      f"{carry/(0.035*CUENTA):.1f} veces el retorno esperado.")
print()
print("  Atenuante real: el swap en corto es POSITIVO. En EURUSD, -8,26 largo")
print("  contra +1,05 corto. Si el trend esta corto la mitad del tiempo, el")
print(f"  carry medio seria del orden de {carry*0.44:,.0f} $/año "
      f"({carry*0.44/CUENTA:.2%}), que SIGUE")
print("  siendo mas que el retorno esperado.")

print()
print(E)
print("EL CULPABLE, Y NO ES EL QUE YO SEÑALABA")
print(E)
noc, sw, _ = POS["xagusd"]
print(f"  LA PLATA es el {sw/tot_swap:.0%} de todo el carry con solo el "
      f"{noc/CUENTA:.1%} de la cuenta.")
print(f"  Su tasa de financiacion es del {-sw/NOCHES*365/noc:.0%} ANUAL sobre el nocional.")
print()
sin_plata = tot_swap - sw
c2 = -sin_plata / NOCHES * 365
print(f"  carry sin la plata               : {c2:>9,.0f} $   "
      f"({c2/CUENTA:>.2%} de la cuenta)")
print(f"  reduccion                        : {carry-c2:>9,.0f} $   "
      f"({1-c2/carry:>.0%} menos)")
print()
print("  Yo venia culpando al oro por el tamaño del contrato. El oro cuesta")
print(f"  {-POS['xauusd'][1]/NOCHES*365/POS['xauusd'][0]:.1%} anual sobre su nocional, que es caro pero normal.")
print("  La plata cuesta diez veces mas. Sacar XAGUSD de la cesta es la palanca.")

print()
print(E)
print("PREDICCION FALSABLE PARA ESTA NOCHE")
print(E)
print("  Hoy es MIERCOLES y la especificacion dice 'Wednesday 3': el rollover de")
print("  esta noche cobra TRIPLE. Si mi modelo es correcto:")
print(f"     swap ahora                    : {tot_swap:>9.2f} $")
print(f"     cargo de esta noche (x3)      : {tot_swap/NOCHES*3:>9.2f} $")
print(f"     swap manaña por la manana     : {tot_swap + tot_swap/NOCHES*3:>9.2f} $")
print()
print("  Si manaña la columna Swap no marca en torno a esa cifra, mi modelo del")
print("  carry esta mal y hay que rehacerlo antes de decidir nada.")
