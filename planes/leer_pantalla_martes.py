"""
DECODIFICAR LA PANTALLA DEL MARTES 8-SEP (9-SEP hora servidor).

Datos leidos de la captura, sin interpretar:
  Balance 24.999,01   Equity 24.785,18   pie de la lista -213,83
  Margin 851,83       Free margin 23.933,35   Margin level 2.909,64%

Se comprueban tres cosas:
  1. ¿cuadra la suma de la columna Profit con el pie? La diferencia es swap +
     comision, y comparada con la de la semana pasada (6,07) dice si el cargo
     ACUMULA (swap) o fue unico (comision). Este es el test que llevabamos
     esperando.
  2. ¿que tamaño de contrato implica cada P&L? Se despeja del propio P&L, que
     es el unico dato que no se puede discutir.
  3. ¿es normal la caida, dada la volatilidad del sistema?
"""
POS = [
    # simbolo, lotes, apertura, actual, profit mostrado
    ("spcusd.c", 0.02, 7710.58, 7679.70,   -6.18),
    ("xauusd",   0.02, 4464.54, 4379.56, -169.96),
    ("xagusd",   0.01,   66.366,  66.367,    0.05),
    ("eurusd",   0.04,  1.16227, 1.16313,    3.44),
    ("usdjpy",   0.03, 155.486, 153.486,  -39.09),
    ("gbpusd",   0.03,  1.35151, 1.35464,    9.39),
    ("audusd",   0.04,  0.71920, 0.72242,   12.88),
]
BALANCE, EQUITY, PIE = 24_999.01, 24_785.18, -213.83
CUENTA = 25_000.0
DEDUC_ANTERIOR = 6.07          # medido el 3-sep, antes de cualquier rollover

E = "=" * 90
suma = sum(p[4] for p in POS)
print(E)
print("1. EL CARGO OCULTO: ¿SWAP O COMISION?")
print(E)
print(f"  suma de la columna Profit      : {suma:>10,.2f}")
print(f"  pie de la lista                : {PIE:>10,.2f}")
print(f"  equity - balance               : {EQUITY-BALANCE:>10,.2f}")
print(f"  DEDUCCION no visible           : {PIE-suma:>10,.2f}")
print()
print(f"  la misma deduccion el 3-sep    : {-DEDUC_ANTERIOR:>10,.2f}")
ded = -(PIE - suma)
crec = ded - DEDUC_ANTERIOR
print(f"  ha CRECIDO en                  : {crec:>10,.2f}")
print()
print("  Si fuera comision de apertura seria FIJA y seguiria en 6,07.")
print("  Ha crecido, asi que ACUMULA: es SWAP.")
noches = 4          # 3->4, 4->5, viernes->lunes, 7->8  (aprox)
print()
print(f"  noches cobradas (aprox)        : {noches}")
print(f"  swap por noche                 : {crec/noches:>10,.2f} $")
print(f"  proyectado a 365 noches        : {crec/noches*365:>10,.0f} $/año")
print(f"  como % de la cuenta            : {crec/noches*365/CUENTA:>10.2%} al año")
print()
print("  Retorno bruto esperado del sistema: ~3,5% anual (vol 3,46%, Sharpe ~1).")
print("  Si el swap es de este orden, se lo come TODO y con creces.")

print()
print(E)
print("2. TAMAÑO DE CONTRATO DESPEJADO DEL PROPIO P&L")
print(E)
print(f"  {'simbolo':<11}{'lotes':>7}{'mov. precio':>13}{'P&L':>10}"
      f"{'unidades/lote':>15}{'nocional $':>12}{'% cuenta':>10}")
print("  " + "-" * 80)
bruto = 0.0
for sim, lotes, ap, ac, pl in POS:
    dif = ac - ap
    if sim == "usdjpy":                     # cotizada al reves
        uds = pl / (lotes * (1.0/ac - 1.0/ap)) if dif else float("nan")
        noc = lotes * 100_000.0
    else:
        uds = pl / (lotes * dif) if dif else float("nan")
        noc = lotes * (uds if uds == uds else 0.0) * ac
    bruto += noc
    print(f"  {sim:<11}{lotes:>7.2f}{dif:>13.5f}{pl:>10.2f}"
          f"{uds:>15,.0f}{noc:>12,.0f}{noc/CUENTA:>10.1%}")

print("  " + "-" * 80)
print(f"  {'EXPOSICION BRUTA TOTAL':<41}{bruto:>22,.0f}{bruto/CUENTA:>10.1%}")
print()
print("  Lo que yo tenia apuntado: 69,4% de exposicion bruta y oro con nocional")
print("  por lote de 44.315 (o sea contrato de 10 onzas).")

print()
print(E)
print("3. ¿ES NORMAL LA CAIDA?")
print(E)
vol = 0.0346
dias = 6
sig = vol / (252 ** 0.5) * (dias ** 0.5)
perd = (EQUITY - CUENTA) / CUENTA
print(f"  equity contra inicial          : {perd:>10.2%}")
print(f"  desviacion esperada a {dias} dias : {sig:>10.2%}")
print(f"  cuantas sigmas                 : {perd/sig:>10.2f}")
print()
print(f"  del total de -{-suma:,.2f} de P&L, el oro aporta "
      f"{-POS[1][4]/-suma:.0%}")
print()
print("  El TAMAÑO de la caida es normal. Lo que no es normal es que una sola")
print("  posicion explique casi todo, y eso viene del tamaño del contrato.")
