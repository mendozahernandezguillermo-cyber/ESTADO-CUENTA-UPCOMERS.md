# Estado de la cuenta Upcomers Vanguard 25K

Documento operativo. Una sola página, para no volver a reconstruir el estado de
memoria. Última medición: 9-sep-2026, 05:38 hora servidor.

---

## La cuenta

```
login <el tuyo> · servidor Upcomers-Server (GMT+2) · modo Hedge
saldo inicial 25.000 $ · trailing 7% RELATIVO al pico, se bloquea en 25.000
diario 4% sobre el MAYOR de (saldo, equity) a las 00:00 UTC
LIMITE POR OPERACION 2% = 500 $  ->  HARD BREACH, cierra la cuenta al instante
6 dias minimos, cada uno cerrando con >= +0,5%
1% de beneficio por segmento para poder cobrar
mejor dia <= 20% del P&L neto del ciclo (blanda: retrasa, no rompe)
INACTIVIDAD: 35 dias naturales sin CERRAR nada -> la cuenta expira
```

**Sin verificar, y manda sobre el dimensionado:** si el límite por operación es
2% o 3%. La documentación es ambigua entre productos. Si fuera 3%, el riesgo
puede subir y el EV con él. **Es la pregunta más rentable que queda abierta.**

## Los cuatro relojes

```
Villahermosa (UTC-6)  ->  servidor GMT+2 = local + 8 h
UTC = local + 6 h     ->  Nueva York (EDT) = local + 2 h
entrada del evento 15:57 NY = 13:57 local · salida 09:30 NY = 07:30 local
reinicio del dia de riesgo 00:00 UTC = 18:00 local
rollover del swap: 00:00 servidor = 16:00 local · MIERCOLES cuenta TRIPLE
```

## Configuración de los EAs

**EA_FOMC_Gap** — gráfico NACUSD.c M1 — *la única pata que se queda*

| input | valor | nota |
|---|---|---|
| `InpSimbolo` | NACUSD.c | |
| `InpHoraEntradaNY` / `InpMinutosAntes` | 16:00 / 3 | entra desde 15:57 NY |
| `InpHoraSalidaNY` | 09:30 | del día del anuncio |
| `InpStopBp` | 80.0 | |
| `InpTakeProfitBp` | **40.0** | trunca la cola: 1,61% contra 2,41% con 80 |
| `InpRiesgoPorEvento` | **0.96** → **pendiente 1.10** | ver abajo |
| `InpSpreadMaxBp` | 3.0 | spread real medido 1,37 bp |
| `InpMagic` | 20260101 | |

**EA_Guardian** — gráfico EURUSD H1 — versión 2.00, recompilada y verificada

| input | valor | nota |
|---|---|---|
| `InpSaldoInicial` | 25000.0 | |
| `InpTrailingPct` / `InpDiarioPct` | 7.0 / 4.0 | |
| `InpDDRelativo` / `InpTrailingSeBloquea` | true / true | confirmado en la doc de la firma |
| `InpHoraResetUTC` | 0 | |
| `InpMargenPleno` / `InpFactorMinimo` | 5.0 / 0.25 | factor sobre el suelo TRAILING, a propósito |
| `InpColchon*` | 0.0 / 0.0 | cierre de emergencia DESACTIVADO, medido que empeora |
| `InpMaxPerdidaPosPct` | **1.50** | contra el hard breach del 2% |
| `InpPagoReiniciaSuelo` | false | |
| `InpVigilarInactiv` / `InpDiasSinCerrar` | true / 25 | 10 días de margen sobre los 35 |
| `InpSimboloActividad` | **USDCHF** | NO usar ninguno del trend: sería hedging |
| `InpSoloAvisar` / `InpReiniciarPico` | false / false | **críticos** |

**EA_Trend_Multi** — gráfico XAUUSD M15 — **a retirar**

## Lo que queda por hacer, en orden

1. **Quitar EA_Trend_Multi del gráfico.** Clic derecho → `Expert Advisors` →
   `Remove`. Si algún día se reattacha, poner `InpSoloDiagnostico = true`
   **antes**: `g_ultimoMesRebal` arranca en 0 y rebalancea al instante.
2. **Cerrar las 7 posiciones**, en sesión de Nueva York (08:00–15:00 local), no
   de madrugada. Realiza ~−224 $; la equity no cambia y el suelo del trailing
   tampoco, porque depende del pico de 25.163,24.
3. **`InpRiesgoPorEvento` de 0.96 a 1.10.** No es opcional: con una sola pata, a
   0,96% un acierto rinde 0,480% y **no llega al umbral de 0,5%** de la firma. La
   cuenta ganaría dinero sin poder cobrarlo nunca. Ventana útil 1,00%–1,20%.

## Expectativa de lo que queda

| | |
|---|---|
| retorno esperado | **~128 $/año** · ~515 $ en 4 años |
| P(cobrar algo en 4 años) | ~89% |
| P(quemar la cuenta) | **~0%** |
| carry | 50 $/año (8 noches) contra 1.524 $ con el trend |
| primer cobro | ~año y medio (solo el 53% de los eventos alcanza el TP) |

Comparado con la configuración con trend: **−810 $/año y 77,3% de probabilidad
de destruir la cuenta.**

## Fechas

```
15-16 sep 2026   primer FOMC con la configuracion nueva.
                 El EA entra el dia ANTERIOR a las 13:57 locales.
1 oct 2026       fecha del rebalanceo que YA NO ocurre (trend retirado).
~4 oct 2026      vence el plazo de inactividad si no se cierra nada antes.
                 El latido de USDCHF lo cubre a los 25 dias.
```

## Cabos sueltos

| # | qué | por qué importa |
|---|---|---|
| 1 | ¿límite por operación 2% o 3%? | decide si el riesgo puede subir; vale ~+90 $/año |
| 2 | ¿el beneficio sobre el tope sale a plazos o nunca? | se resuelve mirando el panel en el 2º cobro |
| 3 | ¿reparto 90% o 100%? | **cerrado**: da igual, el tope muerde antes |
| 4 | camino de cierre del Guardian sin probar | forzar en demo con `InpMaxPosiciones=1` |

## Referencias

```
PROTOCOLO-AUDITORIA-DARWINS.md   Fases 0-15, la 15 es el carry
CORRECCIONES-PROTOCOLO-2.1.md    lo que hay que cambiar en el otro documento
planes/carry_corregido.py        el carry, 6 unidades de swap
planes/con_carry_dentro.py       las tres configuraciones con carry dentro
planes/riesgo_solo_fomc.py       el acantilado del dia cualificado
planes/max_perdida_operacion.py  el limite del 2% por operacion
nas100-data/cierre_fase_12_11.py el caso de la ruptura, cerrado con 15 años
```
