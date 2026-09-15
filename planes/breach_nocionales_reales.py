"""
REHACER LA TABLA DE HARD BREACH CON LOS NOCIONALES REALES.

Ayer calcule que posiciones podian romper el limite del 2% por operacion, y use
nocionales que ahora se demuestran equivocados en los METALES: tenia oro con
contrato de 10 onzas y plata con 500, cuando el P&L de la pantalla dice 100 y
5.000. Los dos 10x pequeños, el mismo error propagado.

Consecuencia directa: ayer el oro salia como la posicion MAS SEGURA (necesitaba
un 56% de caida para romper). Con el nocional real necesita un 5,7%.

Nocionales despejados del P&L de la captura del 8-sep, que es el unico dato
que no admite discusion.
"""
CUENTA = 25_000.0
LIMITE = 0.02 * CUENTA          # 500 $, hard breach
GUARDIAN = 0.015 * CUENTA       # 375 $, donde corta el Guardian

# simbolo: (nocional real $, peor caida 1 mes historica, P&L actual)
POS = {
    "XAUUSD":   (8_759.0, 0.214, -169.96),
    "EURUSD":   (4_653.0, 0.167,    3.44),
    "GBPUSD":   (4_064.0, 0.147,    9.39),
    "XAGUSD":   (3_318.0, 0.371,    0.05),
    "USDJPY":   (3_000.0, 0.201,  -39.09),
    "AUDUSD":   (2_890.0, 0.252,   12.88),
    "SPCUSD.c": (1_537.0, 0.310,   -6.18),
}

E = "=" * 92
print(E)
print("HARD BREACH DEL 2% CON LOS NOCIONALES REALES")
print(E)
print(f"  {'simbolo':<11}{'nocional':>10}{'% cuenta':>10}{'mov. que':>10}"
       f"{'peor 1 mes':>12}{'veredicto':>12}{'ya perdido':>12}")
print(f"  {'':<11}{'':>10}{'':>10}{'rompe':>10}{'historico':>12}{'':>12}{'':>12}")
print("  " + "-" * 78)
for sim, (noc, peor, pl) in sorted(POS.items(), key=lambda x: -x[1][0]):
    umbral = LIMITE / noc
    ver = "ROMPE" if peor > umbral else "ok"
    print(f"  {sim:<11}{noc:>9,.0f}${noc/CUENTA:>9.1%}{umbral:>9.1%}"
          f"{peor:>12.1%}{ver:>12}{pl:>11.2f}$")

print()
print(E)
print("LO QUE ESTO SIGNIFICA HOY MISMO, CON EL ORO YA EN PERDIDA")
print(E)
noc, peor, pl = POS["XAUUSD"]
print(f"  oro: nocional {noc:,.0f} $  ({noc/CUENTA:.1%} de la cuenta)")
print(f"  perdida actual                        : {pl:>9.2f} $  "
      f"({-pl/CUENTA:.2%} de la cuenta)")
print(f"  el Guardian corta en 1,5%             : {-GUARDIAN:>9.2f} $")
print(f"  falta para que corte                  : {-(GUARDIAN+pl):>9.2f} $")
print(f"  o sea, otra caida del oro de          : {(GUARDIAN+pl)/noc:>9.2%}")
print()
print(f"  el hard breach de la firma esta en    : {-LIMITE:>9.2f} $")
print(f"  o sea, una caida del oro de           : {LIMITE/noc:>9.2%}")
print()
print("  Es MUY probable que el Guardian cierre el oro si sigue cayendo. Eso es")
print("  el Guardian funcionando, no un fallo. Y significa que ponerlo ayer en")
print("  1,5 en vez de 3,0 fue probablemente el cambio mas valioso de la semana:")
print("  con 3,0 habria cortado en 750 $, o sea DESPUES del breach de 500 $.")
print()
print(E)
print("EXPOSICION BRUTA")
print(E)
tot = sum(v[0] for v in POS.values())
print(f"  real (despejada del P&L)   : {tot:>9,.0f} $   {tot/CUENTA:>7.1%}")
print(f"  lo que yo tenia apuntado   : {17_315.0:>9,.0f} $   {17_315/CUENTA:>7.1%}")
print(f"  el error es casi todo oro y plata: {tot-17_315:>+9,.0f} $")
