# Triaje de candidatos DARWIN — ingeniería inversa para EA de MT5

Filtro aplicado: D-Score 55-100 · Ex 7-10 · Mc 6-max · Rs 7-10 · Ra 6-10 · R+ 6-10 · R- 6-10 · Dc 5-10 · La 7-10 · Cp 4-10

CAGR calculado como `(1 + retorno)^(1/años) - 1`. Ratio = CAGR / |MaxDD|.

---

## Ranking recalculado — candidatos con capital >= $500k y >= 2 años

| # real | # visto | Ticker | Histórico | Ret. total | CAGR | MaxDD | **Ratio** | D-Score | Capital | Inv. |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 3 | **MDZH** | 2a 4m | 100.77% | **34.8%** | -11.88% | **2.93** | **81.73** | $3.08M | 54 |
| 2 | 11 | **HZVF** | 2a 1m | 38.23% | 16.8% | -11.28% | **1.49** | 67.88 | $1.05M | 10 |
| 3 | 12 | THL | 4a 1m | 36.00% | 7.8% | -8.44% | 0.93 | 68.94 | $1.18M | 8 |
| 4 | 4 | SDI | 4a 6m | 96.00% | 16.1% | -18.51% | 0.87 | 67.47 | $2.32M | 3 |
| 5 | 2 | JHU | 8a 2m | 236.03% | 16.0% | -22.84% | 0.70 | 65.33 | $928k | 34 |
| 6 | 13 | UZI | 5a 2m | 33.94% | 5.8% | -8.93% | 0.65 | 57.06 | $1.99M | 10 |
| 7 | **1** | TNU | 11a 7m | 848.93% | 21.4% | -34.53% | 0.62 | 59.22 | $11.46M | 464 |
| 8 | 5 | HNH | 3a 3m | 83.27% | 20.5% | -34.19% | 0.60 | ~79 | $608k | 8 |
| 9 | 6 | KEL | 5a 7m | 64.83% | 9.4% | -19.11% | 0.49 | 57.58 | $972k | 7 |
| 10 | 23 | QSR | 5a 7m | 21.31% | 3.5% | -14.60% | 0.24 | 67.42 | $928k | 7 |

## Histórico corto (<2a) — watchlist, no construir sobre ellos

| Ticker | Histórico | Ret. | CAGR | MaxDD | Ratio | D-Score | Capital | Inv. |
|---|---|---|---|---|---|---|---|---|
| XAQP | 1a 4m | 45.96% | 32.8% | -5.97% | 5.5 | 71.12 | $1.59M | 36 |
| STCF | 11m | 23.03% | 25.4% | -6.90% | 3.68 | 62.92 | $17.8k | 1 |
| DZUL | 1a 3m | 22.18% | 17.4% | -5.70% | 3.05 | 62.02 | $711k | 8 |

---

## Clasificación

**Tier A — objetivos principales:** MDZH, HZVF
**Tier B — verificar antes de decidir:** SDI, THL, JHU, HNH
**Watchlist (revisar en 12 meses):** XAQP, DZUL
**Descartar:** TNU, UZI, KEL, QSR, LWS, STCF

---

## Verificaciones manuales (solo Tier A y B)

Rellenar una fila por candidato. Todo se saca del perfil del DARWIN en la web.

| Ticker | Zero o Live | Equity trader | Duración media trade | Divergencia | Ret. 12m | D-Leverage/Pos | ¿Salto atributos? | Activos | Veredicto |
|---|---|---|---|---|---|---|---|---|---|
| **MQOH** | **ZERO (virtual)** | **$0.00** | ? | ? | ? | **1.53** | no aparente | FOREX + index + commodity CFDs | **pendiente** |
| **HSYF** | **ZERO (virtual)** | **$0.00** | **45m** | ? | activo | **6.92** | Cs sin color? | FOREX + index + commodity CFDs (**3 activos, 1 dominante**) | **estudiar, no construir** |
| SDI | | | | | | | | | |
| **THL** | **LIVE** | **5.009,54 EUR** | **2h49m** | ? | **activo, en máximos** | **2.38** | ok | FOREX + index + commodity + stock + ETF CFDs (**4 activos**) | ✅ **OBJETIVO PRINCIPAL** |
| JHU | | | | | | | | | |
| HNH | | | | | | | | | |

### MQOH — DESCARTADO: estrategia dormida

**Motivo:** `Current monthly rotation: 0.40` vs `Max. monthly rotation: 318.44` -> actividad actual = **0.13% del pico**.
Los gráficos de rotación muestran operativa intensa solo entre ~25 Dic y ~17 Jun (unos 6 meses), y prácticamente cero desde entonces.
El track record de 2a 4m es en realidad **~6 meses de operativa + ~22 meses de inactividad**.

Estadísticas de comportamiento (útiles como referencia de arquetipo):

- Trades: 4.283 · Frecuencia: 5.98/día · Activos distintos: **13** (asignación ~uniforme)
- **Duración media: 1d 18h 49m** -> muy por encima del umbral de 4h, replicable en EA
- % trades ganadores: **74.99%** · Ganador medio **+31.11 pips** · Perdedor medio **-47.43 pips**
- Esperanza: `0.7499*31.11 + 0.2501*(-47.43)` = **+11.47 pips/trade**
- Payoff ratio 0.656 -> **win rate de equilibrio = 60.4%** (opera al 75%, margen de solo 14.6 pp)
- Sesiones: Europea 46.31% · Americana 28.81% · Asiática 24.88% (siempre activo, sin sesgo de sesión)
- Distribución por día de semana: plana (140/144/142/142/143)
- Excursión media +0.08% / -0.05% por trade · peor -3.60% · mejor **+87.19%** (outlier a investigar)
- Average daily rotation 2.16 · Max daily rotation 62.74

**Arquetipo inferido:** reversión a la media / short-vol sistemática sobre cesta de 13 activos,
holding ~1.8 días, una sola regla aplicada en paralelo. Sesgo negativo: la cola vive en el 25% perdedor.

### MQOH — datos del perfil

- Nombre: `knetsan_MT4` — plataforma MT4, **FOREX + index + commodity CFDs**
- Darwinex Score **81.7** · Return since inception **100.77%** · **Return/Risk 4.45**
- Max target risk (VaR 95%/mes): 6.50%
- **Average D-Leverage / Position: 1.53** (bajo -> evidencia contra martingala/grid)
- **Trader's Total Equity: $0.00** -> cuenta **Darwinex Zero (virtual)**, sin capital propio en riesgo
- 59 inversores · $3,109,075.62 · Used capacity **0%**
- DarwinIA **GOLD**, asignación **60.000 €**
- Drawdown (since inception): **en blanco en el perfil** — el listado marcaba -11.88%, hay que resolverlo

### Criterios de descarte

| Columna | Descartar si | Motivo |
|---|---|---|
| **Rotación actual / Rotación máx.** | **< 10%** | **Estrategia dormida: el track record describe algo que ya no opera** |
| Opera en Darwinex desde | < 2 años | Histórico pre-migración no verificado por el Risk Engine |
| Duración media trade | < 4h | Sensible a spread/slippage; irreplicable en un EA |
| Divergencia mensual | < -0.5% | La ejecución real se desvía de la estrategia |
| Ret. últimos 12m | negativo o plano | La estrategia puede estar agotada |
| Salto de atributos | La o Rs saltan >3 puntos | Probable cambio de estrategia -> replicarías un promedio de dos |
| Equity trader | muy bajo | Sin skin in the game |

### Detección de martingala / grid (inspección visual de la curva)

- Curva sospechosamente lineal con escalones descendentes bruscos y raros
- R^2 de la equity contra el tiempo > 0.98 -> riesgo de cola sin materializar
- DD/volatilidad anómalamente bajo

---

## Siguiente paso tras el triaje

Sobre los 2-4 supervivientes, vía Darwin Info API:

1. Descargar serie de cotización + histórico de Investable Attributes
2. Deflated Sharpe Ratio y Minimum Track Record Length (corrige el sesgo de selección: N = universo cribado)
3. Análisis de estilo basado en retornos contra librería de factores sintéticos generados en MT5
4. Ventanas horarias de actividad (segmentar varianza del retorno por hora)
5. Betas rodantes contra EURUSD / XAUUSD / US500 / GER40 / USDJPY para identificar instrumentos

Criterio de éxito final del EA: **correlación de retornos diarios > 0.5 contra el DARWIN objetivo, out-of-sample.**


---

## HSYF (ex-"HZVF") — `Sate89_MT5`, cuenta ZERO

**PASA el test de rotación:** actual 65.47 / máx 165.18 = **39.6%**.
Los gráficos muestran operativa **continua e ininterrumpida de Ago '24 a Ago '26**. Estrategia viva.

### Perfil
- Darwinex Score 67.9 · Return 38.25% · DD **-11.28%** · Return/Risk 1.93 · CAGR 16.8% · ratio 1.49
- **Average D-Leverage / Position: 6.92** (vs 1.53 de MQOH -> 4.5x más apalancado)
- Trader's Total Equity **$0.00** (Zero) · 10 inversores · $1.060.133 · **Used capacity 25.59%**
- DarwinIA GOLD puesto **567** · asignación 50.000 EUR

### Comportamiento — perfil MUY identificable
- **Sesión europea 84.90%** · americana 13.04% · asiática 2.06%
- Actividad concentrada en una ventana estrecha: **pico en ~13H**, cola hasta ~16H
- **3 activos, uno claramente dominante** (~95% del donut)
- Trades: **437** · frecuencia **0.83/día** · **duración media 45m**
- Ganador medio **+34.17 pips** · perdedor medio **-22.49 pips** · acierto **44.39%**
- Excursión media +1.02% / -0.70% · mejor +3.92% / peor -3.01% (simétrico, sin cola gorda)
- Viernes en **rojo** (73 vs 80-84 el resto de días)

### El problema: el edge es estadísticamente indistinguible de ruido

```
Esperanza      = 0.4439*34.17 + 0.5561*(-22.49) = +2.66 pips/trade
Payoff ratio   = 34.17 / 22.49 = 1.519
Win rate breakeven = 1/(1+1.519) = 39.70%
Margen         = 44.39% - 39.70% = 4.69 pp

Error estándar del win rate con n=437:
SE = sqrt(0.4439*0.5561/437) = 2.38 pp
z  = 4.69 / 2.38 = 1.97   ->  p ~ 0.024 (una cola)
```

Corrección por selección múltiple: se eligió entre **48 candidatos filtrados**.
Falsos positivos esperados a p<0.024 -> `48 * 0.024 = 1.15`.
**Encontrar exactamente un candidato así entre 48 es lo que predice el puro azar.**

### Combinación fatal
1. Esperanza de solo **+2.66 pips/trade**
2. Cuenta **virtual** -> costes de ejecución probablemente subestimados
3. Duración 45m -> muchas operaciones, mayor arrastre de costes

Si la ejecución real cuesta 1.5-2 pips más que la cuenta virtual, **el edge completo desaparece**.

### Hipótesis de arquetipo (valiosa aunque se descarte)
Pico a las ~13H + sesión europea + 45m de holding + ganadores de 34 pips + ~1 trade/día
+ un solo activo dominante -> **momentum en publicación de datos macro US** (13:30 UTC)
o **breakout del solape Londres-NY**. Hipótesis concreta y testeable.

### Veredicto
**Estudiar como ejercicio de fingerprinting, no construir un EA en producción.**
El *molde estructural* es el mejor que hemos visto; el edge es demasiado fino y está en cuenta virtual.

---

## ALERTA ESTRUCTURAL: el filtro está seleccionando cuentas virtuales

MQOH -> ZERO, equity $0.00
HSYF -> ZERO, equity $0.00

Dos de dos. Si SDI/THL/JHU/HNH también son ZERO, el screening completo está sesgado
hacia **track records simulados** y hay que replantear el enfoque.


---

## THL — `Izurdia` de `joxemi` — CUENTA LIVE — OBJETIVO PRINCIPAL

**Primer candidato con capital propio real: `Trader's Total Equity: 5.009,54 EUR`** (no ZERO).
Implicación clave: el track record subyacente proviene de **fills reales con spread y slippage reales**.

### Perfil
- Darwinex Score 68.9 · Return 36.00% · DD **-8.44%** · Return/Risk 1.39
- **Average D-Leverage / Position: 2.38** (moderado)
- 8 inversores · $1.190.274 · **Used capacity 21.08%**
- DarwinIA **SILVER**, sin asignación (los tiers dependen del equity -> 5.009 EUR cae en SILVER por construcción, no es señal de calidad inferior)
- Instrumentos: FOREX, index, commodity, **stock y ETF** CFDs

### Test de rotación: el mejor de los tres
```
Current: 84.19 / Max: 140.71 = 59.8%
```
**~4 años de operativa continua (Sep '22 -> Ago '26)** y la rotación está **en máximos históricos ahora mismo**
(110-125 entre May-Ago '26). No solo está viva: está **escalando**.

### Comportamiento
- Sesiones: **Americana 51.79%** · Asiática 25.00% · Europea 23.21% · activo en las 24h, pico 15H-17H
- Trades: **2.400** · frecuencia 2.25/día · **duración media 2h49m**
- Acierto **65.83%** · ganador medio **+22.02 pips** · perdedor medio **-24.35 pips**
- **4 activos**, uno dominante (~85% del donut)
- Excursión media +0.18% / -0.13% · mejor +2.94% · **peor -1.51%** (el mejor control de cola de los tres)

### El edge SÍ es estadísticamente real
```
Esperanza          = 0.6583*22.02 + 0.3417*(-24.35) = +6.18 pips/trade
Payoff ratio       = 22.02/24.35 = 0.9043
Win rate breakeven = 1/(1+0.9043) = 52.51%
Margen             = 65.83% - 52.51% = 13.32 pp

SE con n=2.400 = sqrt(0.6583*0.3417/2400) = 0.968 pp
z = 13.32 / 0.968 = 13.76
```
**z = 13.76** frente a **z = 1.97** de HSYF. Sobrevive a cualquier corrección por selección múltiple.
Y al ser cuenta live, los costes de ejecución **ya están descontados** en esos +6.18 pips.

### Corrección al ranking: el CAGR de 7.8% está diluido
El gráfico de rotación mensual muestra intensidad **baja en 2022-2023 (25-50)** y **alta desde mediados de 2024 (75-125)**.
El CAGR de 7.8% mezcla una fase de rampa con la fase actual. **El ratio 0.93 subestima la estrategia actual.**

### Hipótesis para fingerprinting
- Perfil americano/24h con pico 15H-17H, 4 activos con uno dominante, holding ~2h49m
- **Martes y jueves aparecen en rojo** en Daily Performance -> posible patrón de calendario macro.
  OJO: no he podido determinar la definición de la métrica (el color no correlaciona con la altura de barra).
  Verificar con hover. **Alto riesgo de sobreajuste** en efectos día-de-semana: tratar como hipótesis, no como regla.

---

## Comparativa de los tres candidatos analizados

| | MQOH | HSYF | **THL** |
|---|---|---|---|
| Cuenta | ZERO virtual | ZERO virtual | **LIVE 5.009 EUR** |
| Rotación actual/máx | **0.13%** | 39.6% | **59.8%, en máximos** |
| Operativa continua | ~6 meses | 2 años | **4 años** |
| Trades | 4.283 | 437 | 2.400 |
| Esperanza/trade | +11.47 pips | +2.66 pips | +6.18 pips |
| Margen sobre breakeven | 14.6 pp | 4.69 pp | 13.3 pp |
| **z-score del edge** | 22.0 | **1.97** | **13.76** |
| Duración media | 1d 18h 49m | 45m | 2h 49m |
| D-Leverage/posición | 1.53 | 6.92 | 2.38 |
| Peor excursión/trade | -3.60% | -3.01% | **-1.51%** |
| Veredicto | ❌ dormida | ⚠️ edge = ruido | ✅ **objetivo** |

Lección: MQOH tenía el z-score más alto (22.0) y **aun así no vale nada** porque dejó de operar.
La significancia estadística es necesaria, no suficiente. El orden correcto de checks es:
**1) ¿está viva? 2) ¿el edge es real? 3) ¿live o virtual? 4) ¿es replicable?**


---

## HALLAZGO CRÍTICO: THL no parece ser una estrategia original

Pestaña `Correlación` del perfil de THL — correlación con **otros DARWINs** (ventana 1M):

| DARWIN | Corr. | ¿En DarwinIA? |
|---|---|---|
| **ZJM** | **0.92** | Sí |
| SHD | 0.79 | Ninguno |
| LROT | 0.60 | Sí |
| AABW | 0.41 | Sí |
| LUI | 0.40 | Sí |
| IYD | 0.40 | Sí |
| RWK | 0.39 | Sí |
| WSGW | 0.38 | Sí |
| BQVI | 0.38 | Ninguno |
| VFXR | 0.37 | Sí |

Detalle THL vs ZJM (1M): correlación **0.92**, curvas de equity casi superpuestas (ambas ~+1.90%).
Trades en el periodo: THL 170 · ZJM 212.

```
¿Participa THL en DarwinIA?   No
¿Participa ZJM en DarwinIA?   Si
DARWIN que elimina a THL:     ZJM
DARWIN que elimina a ZJM:     ---
```

### Implicaciones

1. **0.92 no es "estilo parecido", es la misma estrategia.** Con SHD a 0.79 y LROT a 0.60,
   THL pertenece a un **cluster de estrategias casi idénticas**.
2. Hipótesis principales: (a) un **EA comercial** ampliamente distribuido, (b) un servicio de señales,
   (c) el mismo trader con varias cuentas. El tamaño del cluster favorece (a) o (b).
3. **Darwinex prefiere ZJM sobre THL**: ZJM participa en DarwinIA y elimina a THL.
   A ZJM no lo elimina nadie -> ZJM es la instancia "primaria" del cluster.
4. Corrección a mi valoración previa: el perfil de THL mostraba "Participating in: DarwinIA SILVER",
   pero esta pestaña dice que **NO participa**. Mi lectura fue demasiado optimista.

### PUNTO CIEGO DEL SCREENING

**Ninguno de los 12 Investable Attributes mide la originalidad de la estrategia.**
Mc mide correlación con los *activos subyacentes*, no con *otros DARWINs*.
THL pasó Mc>=6 y aun asi es un clon. La pestaña `Correlación` hay que revisarla SIEMPRE, a mano.

Nuevo criterio de triaje: **si corr. con otro DARWIN > 0.7 -> investigar el cluster antes de seguir.**

### Implicación para la fase de portafolio

THL, ZJM, SHD y LROT **son una sola apuesta, no cuatro**. Replicar varios seria replicar
lo mismo N veces. Antes de construir el portafolio, matriz de correlaciones obligatoria.

### Acción
- Cambiar el objetivo a **ZJM** (instancia primaria segun Darwinex)
- Verificar la correlacion en ventanas **6M y 3M** (0.92 es solo 1 mes, 170 trades)
- Revisar perfil de ZJM: cuenta live o Zero, rotacion, equity del trader, duracion media


---

## RESUELTO: el cluster es UN SOLO TRADER (joxemi)

- **THL** = `Izurdia` by **joxemi**
- **ZJM** = `ZeruUrdinEg` by **joxemi**
- SHD (corr. 0.86 con ZJM) — verificar, probablemente tambien joxemi

No es un EA comercial distribuido. Es el mismo trader con variantes del mismo sistema.
Consecuencia buena: **sin crowding de miles de compradores retail**.
Consecuencia mala: **THL/ZJM/SHD no diversifican entre si**.

### ZJM publica la especificacion de su estrategia (parafraseado)

Del texto del propio trader en el perfil de ZJM:

| Dato declarado | Valor |
|---|---|
| Implementacion | **100% algoritmica, desarrollada en MQL5** |
| Frecuencia | **40-50 operaciones/mes** |
| Duracion media | **~7 horas** por operacion |
| Objetivo de beneficio | **25-40 pips** |
| Logica de entrada | Busca *momentos de mercado especificos*; no repite operacion hasta que la situacion vuelve a darse |
| Sizing | **Riesgo constante por operacion, no varia con ganancias ni perdidas** -> NO es martingala |

**Esto es practicamente el pliego de especificaciones del EA.**

### Verificacion de consistencia (la declaracion cuadra)
THL: 2.25 trades/dia x ~21 dias = **~47/mes** -> encaja con "40-50 operaciones mensuales" ✅
THL: ganador medio 22.02 pips -> algo por debajo del objetivo declarado de 25-40 pips (cierres parciales/anticipados) ✅
Discrepancia: duracion 2h49m (THL) vs ~7h (ZJM declarado) -> **variantes con salidas distintas**

### Comparativa THL vs ZJM — el mismo sistema, dos parametrizaciones

| | THL (Izurdia) | ZJM (ZeruUrdinEg) |
|---|---|---|
| Trader | joxemi | joxemi |
| Darwinex Score | **68.9** | 67.7 |
| Retorno (a origen) | 36.00% | 40.75% |
| **Drawdown** | **-8.44%** | **-26.62%** |
| **Retorno/Riesgo** | **1.39** | 1.15 |
| D-Leverage/posicion | 2.38 | 2.62 |
| Equity del trader | 5.009,54 EUR | 5.207,92 EUR |
| Inversores | 8 ($1.190.274) | 10 ($766.600) |
| Capacidad usada | 21.08% | 16.45% |
| DarwinIA | eliminado por ZJM | SILVER, 512o, **30.000 EUR** |

**THL es netamente mejor en riesgo-retorno**: drawdown 3x menor y Retorno/Riesgo superior.
La eliminacion de THL en DarwinIA afecta a los ingresos del trader, **no a su calidad como objetivo de replica**.

### DECISION: el objetivo sigue siendo THL
Se mantiene THL como objetivo (mejor perfil de riesgo) y se usa **la descripcion de ZJM como especificacion**.
El cluster deja de ser un problema y pasa a ser **una fuente de informacion**.

### Pendiente
- Track record de ZJM (para calcular su CAGR y confirmar que THL gana en riesgo-retorno)
- Trader de SHD (corr. 0.86)
- Correlacion THL-ZJM en ventanas 6M y 3M


---

## THL — pestaña `Estrategia subyacente` (Trading Journal)

### INSTRUMENTO IDENTIFICADO: NASDAQ 100 (Mini)

`Activos abiertos: NASDAQ 100 (Mini)` -> el activo dominante (~85% del donut) es **NAS100 / US100**.

Esto explica coherentemente todo el perfil observado:

| Observacion previa | Explicacion con NAS100 |
|---|---|
| Sesion americana 51.79% | NASDAQ es indice US |
| **Pico de actividad 15-17H** | **Apertura del cash US: 15:30 CET / 09:30 ET** |
| Sesion asiatica 25% | Los futuros de NASDAQ cotizan casi 24h |
| Ganador medio 22 pips / objetivo 25-40 | 25-40 puntos de NAS100 (~0.10-0.20% a 20.000) = movimiento intradia realista |
| "index CFDs" en la descripcion de instrumentos | El indice es NASDAQ |

Nota de zona horaria: si el eje esta en CET, 15-17H = apertura del cash US + primeras 1,5h. Encaja perfectamente.

### CONTRADICCION con lo que declara joxemi

Snapshot del journal, posicion 3181/3940:
```
Fecha inicio        07/04/2026 22:33:01
Fecha fin           07/04/2026 22:34:00   -> ventana de 59 segundos
Retorno posicion    3.39%
Retorno a origen    22.02%
Trades abiertos     2
D-Leverage          30.66     <-- 13x la media de 2.38
Activos abiertos    NASDAQ 100 (Mini)
```

Dos declaraciones del trader quedan en entredicho:

1. **"Riesgo constante por operacion, no varia"** -> D-Leverage de **30.66** frente a una media de 2.38.
   El grafico de D-Leverage muestra picos recurrentes hasta ~25. Distribucion muy sesgada:
   casi siempre bajo, ocasionalmente 10x mas alto. **El riesgo NO es constante.**
2. **"No repite operacion hasta que la situacion vuelve a darse"** (implica una a la vez)
   -> `Trades abiertos: 2`. **Solapa posiciones.**

Matiz honesto: D-Leverage se define como volatilidad del DARWIN frente a la del EURUSD, asi que en NASDAQ
un valor alto refleja en parte la volatilidad intrinseca del indice, no solo el tamano de la posicion.
Pero una variacion de 2.38 a 30.66 sigue siendo variacion de riesgo real.

### AVISO: el rendimiento parece concentrado en el ultimo ano

La vista **1A** muestra la curva subiendo de 0% a **~38-40%**.
Pero el retorno **desde origen** (4a 1m) es **36.00%**.

Si la lectura del eje es correcta -> **los ~3 primeros anos aportaron ~0 neto** y practicamente todo
el rendimiento viene de los ultimos ~12 meses. Coherente con el grafico de rotacion
(actividad baja 2022-2023, alta desde mediados de 2024).

**Impacto en la estadistica:** mi z = 13.76 usaba los 2.400 trades de todo el histórico.
Si el edge solo existe en el ultimo ano, la base de evidencia efectiva es **~1 ano, no 4**.
Hay que recalcular sobre el subperiodo. **VERIFICAR con la vista TOTAL antes de concluir.**

### El Trading Journal es un tape de trades manual

`Posicion 3181 / 3940` -> **3.940 entradas navegables**, cada una con:
fecha/hora inicio, fecha/hora fin, retorno de la posicion, D-Leverage, numero de trades abiertos
y **activos abiertos**.

Es, de facto, el tape de operaciones accesible sin API. Recorrerlo a mano es inviable,
pero **muestrear 30-50 entradas repartidas** basta para caracterizar:
mezcla de instrumentos, distribucion de D-Leverage, frecuencia de solapamiento y franjas horarias.


---

## CORRECCION: el rendimiento NO esta concentrado. Es notablemente consistente.

Mi lectura de la vista 1A era erronea. La tabla mensual de la vista TOTAL:

| Ano | Total | Nota |
|---|---|---|
| 2022 (Jul-Dic) | **+0.17%** | Plano durante el mercado bajista del NASDAQ |
| 2023 | **+8.98%** | |
| 2024 | **+8.10%** | |
| 2025 | **+9.59%** | |
| 2026 (Ene-Ago) | **+5.49%** | ~8.35% anualizado |
| **TOTAL** | **36.99%** | |

**Cuatro anos consecutivos entre 8.1% y 9.6%.** Desviacion tipica de los retornos anuales: **~0.75 pp**.
Esa estabilidad es el verdadero activo de esta estrategia, no la magnitud.

CAGR real: `1.3699^(1/4.17) - 1` = **7.84%** · Max DD **-8.44%** -> ratio **0.93** (confirma el calculo original).

### Estadisticas de performance
- % dias ganadores: **51.28%** (apenas por encima de una moneda al aire)
- % semanas ganadoras: **55.93%**
- Peor mes: **-3.94%** (Oct 2024) · Mejor mes: **+6.39%** (Oct 2025)
- Rango mensual acotado entre ~-4% y ~+6.4%

Coherente: 65.83% de trades ganadores pero solo 51.28% de dias ganadores -> varios trades por dia diluyen.

### NUEVO: fecha de creacion del DARWIN = 02/09/2023

El grafico arranca en Sep '22 pero el DARWIN se creo el **02/09/2023**.
-> El primer ano (Sep'22-Sep'23) es **historico previo a la creacion**, no verificado por el Risk Engine.
-> **Historico DARWIN verificado: ~3 anos** (Sep 2023 - Ago 2026), no 4.

Aun asi, 2024, 2025 y 2026 son integramente post-creacion y mantienen la consistencia. El dato aguanta.

### Valoracion honesta de la magnitud

El DARWIN opera a un objetivo de **6.5% VaR mensual**, que Darwinex describe como el perfil de
volatilidad del S&P 500. Rendir ~8-9% anual a riesgo tipo S&P es **aproximadamente lo que da el S&P**.

-> El valor de esta estrategia **no es batir al indice, es la consistencia y la descorrelacion**.
-> Accion: usar el desplegable `Comparar con: S&P 500` de la pestana Retorno/Riesgo para cuantificarlo.

### CONFIRMADO: patron martes/jueves

En ambas capturas, `Rendimiento Diario`:
```
Lunes 114 (verde) · Martes 135 (ROJO) · Miercoles 125 (verde) · Jueves 129 (ROJO) · Viernes 121 (verde)
```
Martes y jueves pierden, y son los dos dias de **mayor** altura de barra -> mas actividad en los dias que pierden.
La altura no es el conteo total de trades (suma 624 vs 2.400 totales), asi que la metrica exacta sigue sin confirmar,
pero el signo por dia de semana es consistente en las dos vistas.

### CONFIRMADO: distribucion horaria
Pico claro en **15H**, alto en 16H-17H, elevado desde 13H-14H, bajo de madrugada.
-> Apertura del cash US y primeras horas. Consistente con NAS100.


---

## VEREDICTO FINAL SOBRE THL: dominado por comprar y mantener

Comparativa `Retorno/Riesgo` contra S&P 500, mismo periodo (Sep '22 - Sep '26):

```
S&P 500 :  88.01%   ->  CAGR ~16.3%
THL     :  36.00%   ->  CAGR ~7.7%
```

**El S&P rindió más del doble.** Y el contexto de riesgo lo agrava: el DARWIN opera a
**6.5% VaR mensual, que Darwinex describe como el perfil de volatilidad del S&P 500**.
Es decir: mismo nivel de riesgo objetivo, menos de la mitad de retorno.

Ajustado por drawdown (DD del S&P estimado del grafico, ~-15%):
```
S&P 500 :  16.3 / ~14.9  =  ~1.10
THL     :   7.7 /   8.44 =   0.91
```
**El indice pasivo gana incluso en base ajustada por riesgo.**

### La ironia central
THL opera **NASDAQ 100 intradia**. En 4 anos capturo 36% mientras el S&P subio 88%
(y el propio NASDAQ 100, probablemente mas por el sesgo tecnologico).
**La estrategia no bate al instrumento que opera.**

### Lo que si vale de THL
En Mar-Abr '26 el S&P se desploma (~88% -> ~60%) y **THL se queda plano en ~30-33%**.
No participo en la caida. La descorrelacion es real (coherente con Mc >= 6).
-> Como *sleeve* descorrelacionado dentro de una cartera con exposicion a bolsa, tiene sentido.
-> Como estrategia autonoma que justifique ~4 meses de ingenieria, **no**.

### DECISION: no construir el EA sobre THL

---

## EL CRITERIO QUE FALTABA (el mas potente de todos)

Todos los DARWINs estan normalizados a **6.5% VaR mensual ~ volatilidad del S&P 500**.
Por tanto:

> **Cualquier DARWIN con CAGR por debajo de ~16% ha rendido menos que un indice pasivo
> a nivel de riesgo comparable.**

Nuevo filtro obligatorio: **CAGR > CAGR del benchmark del periodo**, y ademas
comparar contra el **instrumento dominante que opera**, no solo contra el S&P.

### Aplicado a los candidatos ya analizados

| Candidato | CAGR | Supera ~16%? | Estado |
|---|---|---|---|
| MQOH | 34.8% | Si | ❌ dormida |
| XAQP | 32.8% | Si | ⚠️ solo 16 meses |
| TNU | 21.4% | Si | ❌ en decadencia (D-Score 59) |
| **HNH** | **20.5%** | **Si** | 🔍 sin revisar |
| **IMTZ** | **19.3%** | **Si** | 🔍 sin revisar — mejor ratio de la 1a criba (1.64) |
| **SUG** | **19.0%** | **Si** | 🔍 sin revisar — 7a 9m, 263 inversores |
| DZUL | 17.4% | Si | ⚠️ solo 15 meses |
| HSYF | 16.8% | Limite | ❌ edge = ruido (z=1.97) |
| SDI | 16.1% | Limite | 🔍 sin revisar |
| JHU | 16.0% | Limite | 🔍 sin revisar |
| **THL** | **7.7%** | **NO** | ❌ **dominado por buy & hold** |

**Siguientes objetivos: IMTZ, SUG, HNH.** Los tres superan el benchmark y ninguno se ha revisado.
IMTZ y SUG eran precisamente el #1 y #2 del primer re-ranking por CAGR/DD.

---

## CONCLUSION METODOLOGICA

El entregable real de este trabajo no es un candidato: es una **secuencia de filtros que funciona**.
Cada uno elimino un candidato que parecia bueno en superficie:

| # | Filtro | Victima |
|---|---|---|
| 1 | Rotacion actual/max < 10% | MQOH (dormida) |
| 2 | z-score del edge con correccion por seleccion multiple | HSYF (ruido) |
| 3 | Pestana Correlacion > 0.7 con otro DARWIN | cluster joxemi (THL/ZJM/SHD) |
| 4 | Zero vs Live (equity del trader) | MQOH, HSYF |
| 5 | **CAGR vs benchmark pasivo** | **THL** |
| 6 | D-Score como suelo, nunca como orden | (evito el filtro invertido) |
| 7 | Anualizar siempre: nunca ordenar por retorno acumulado | reordeno todas las listas |

Orden de aplicacion optimo: **6 -> 7 -> 5 -> 1 -> 3 -> 4 -> 2**
(los baratos primero; el z-score al final porque exige estadisticas de comportamiento)


---

# OPCION B: THL como sleeve descorrelacionado — REVIERTE EL VEREDICTO

## Mi error: premisa falsa sobre el nivel de riesgo

Dije "el DARWIN opera a 6.5% VaR mensual ~ volatilidad del S&P, luego 8% de retorno a riesgo
tipo S&P es malo". **La premisa era falsa.** El 6.5% es un TECHO, no el nivel operativo real.

Volatilidad real de THL, calculada desde sus 50 retornos mensuales:
```
Vol mensual   2.08 %
Vol ANUAL     7.22 %     <-- menos de la mitad del S&P (~17%)
VaR mensual implicito = 1.645 * 2.08 = 3.4 %   (contra un techo de 6.5%)
```
THL opera a **~52% de su presupuesto de riesgo permitido**.
Coherente con `Capacidad usada 21.08%` y notas altas en Rs y Ra.

Comparar 36% contra 88% era comparar peras con manzanas.

## Criterio de la Opcion B

    Anadir S a la cartera B mejora el Sharpe  <=>  SR_S > rho(S,B) * SR_B
    Umbral:  rho_max = SR_S / SR_B

```
SR_THL   = (7.65 - 4) / 7.22  = 0.506
SR_S&P   = (16.35 - 4) / 17.0 = 0.726
rho_max  = 0.506 / 0.726      = 0.697
```

**THL mejora la cartera mientras su correlacion con el S&P sea < 0.70.**

| rho | Sharpe cartera | Mejora | Peso optimo THL |
|---|---|---|---|
| 0.00 | 0.885 | **+21.9%** | 62.1% |
| 0.10 | 0.847 | +16.6% | 60.2% |
| 0.20 | 0.814 | +12.1% | 57.6% |
| 0.30 | 0.787 | +8.3% | 54.2% |
| 0.50 | 0.745 | +2.6% | 41.6% |
| 0.70 | 0.726 | 0.0% | — (umbral) |

THL se queda plano durante la caida del S&P de Mar-Abr '26 -> **rho real probablemente 0.0-0.3**
-> mejora del Sharpe de cartera del **8-22%** con peso optimo del **54-62%**.

**VEREDICTO REVISADO: THL es un objetivo VALIDO bajo la Opcion B.**

## Por que THL esta descorrelacionado — principio de diseno del EA

Holding de 2h49m en ventana 15-17H -> **plano fuera de sesion**.
El *drift* de los indices de renta variable se acumula mayoritariamente **overnight**.
Un sistema que cierra plano no puede heredar beta de buy & hold.

> **PRINCIPIO: plano overnight = descorrelacion estructural de la beta de bolsa.**

Esto deja de ser una observacion sobre THL y pasa a ser un **requisito de diseno del EA**.

## Que cambia en los criterios

| | Opcion A (antes) | **Opcion B (ahora)** |
|---|---|---|
| Objetivo del EA | Maximizar retorno | **Maximizar SR - rho*SR_bench** |
| Suelo de CAGR | > 16% (benchmark) | **Irrelevante**: vale 7-8% si la vol es baja y rho bajo |
| Atributo clave | Pf, D-Score | **Mc (Market Correlation) >= 7** |
| Volatilidad | Secundaria | **Tan importante como el retorno** |
| Retorno/Riesgo de la web | Ignorado | **Metrica primaria** (THL: 1.39) |
| Overnight | Sin criterio | **Debe cerrar plano** |
| Fase de portafolio | Opcional, al final | **Es el objetivo central** |

## Candidatos: reevaluacion bajo Opcion B

El filtro de CAGR > 16% deja de aplicar. Vuelven a estar en juego los descartados por retorno bajo,
**siempre que tengan vol baja y Mc alto**. Prioridad: **Mc alto + Retorno/Riesgo alto + vol baja**.

Pendiente para cerrar: **medir rho(THL, S&P) de verdad**, no estimarlo del grafico.
Requiere transcribir bien la tabla mensual (mi lectura compone 43.04% vs el 36.00% oficial -> tiene errores).


---

# RESULTADO DEFINITIVO — Opcion B, con datos reales

Serie mensual de THL verificada (50 meses, Jul'22-Ago'26; los 5 totales anuales y el
compuesto de 36.01% cuadran). Benchmark: ^GSPC mensual real (Yahoo, adjusted close =
retorno total con dividendos, o sea el benchmark **mas exigente**).

| | THL | S&P 500 |
|---|---|---|
| CAGR | 7.66% | 18.62% |
| Vol anualizada | **7.44%** | 14.75% |
| Max DD (mensual) | **-5.34%** | -13.19% |
| **Sharpe** | **0.491** | 0.991 |

```
Correlacion REAL       rho = +0.125
Umbral tolerable       rho_max = 0.496
Test                   SR_THL 0.491  >  rho * SR_S&P 0.124     -> PASA
```

## Cartera optima
```
56.1% S&P 500  +  43.9% THL
Sharpe solo S&P    0.991
Sharpe cartera     1.058     -> +6.8%
```

## LO MAS IMPORTANTE: comportamiento en los peores meses del S&P

| Mes | S&P 500 | THL |
|---|---|---|
| 2022-08 | -4.24% | **+3.76%** |
| 2022-09 | -9.34% | -1.67% |
| 2022-12 | -5.90% | **+0.85%** |
| 2023-09 | -4.87% | -1.49% |
| 2025-03 | -5.75% | **+1.77%** |
| 2026-03 | -5.09% | **+0.35%** |
| **Media** | **-5.87%** | **+0.59%** |

**4 de los 6 peores meses del S&P fueron POSITIVOS para THL.** Media positiva.
Eso no es solo correlacion baja: es comportamiento convexo en cola izquierda.
Es lo que de verdad protege una cartera.

## Matiz honesto sobre el +6.8%

El Sharpe del S&P en esta ventana es **0.991**, excepcionalmente alto (mercado alcista fuerte).
Historicamente el Sharpe del S&P a largo plazo ronda 0.4-0.5. Recalculando con SR_B = 0.5:

```
rho_max            = 0.491 / 0.5 = 0.98    (THL pasa trivialmente)
Sharpe cartera     = 0.661
MEJORA             = +32%
```

-> **El +6.8% es la medicion en el escenario MAS desfavorable posible.**
En un regimen de bolsa normal el aporte de THL seria de ~+32%.

---

# ESPECIFICACION DEL EA (Opcion B)

| Parametro | Valor | Fuente |
|---|---|---|
| Instrumento | **NAS100 / US100** | pestana Estrategia subyacente |
| Ventana | **15-17H CET** (apertura cash US) | Distribucion Horas Trading |
| **Overnight** | **CERRAR PLANO — requisito, no opcion** | es el origen de la descorrelacion |
| Objetivo | 25-40 puntos | descripcion de joxemi (ZJM) |
| Duracion media | ~2h49m | Behaviour Statistics |
| Frecuencia | ~47/mes | 2.25/dia |
| Sizing | riesgo fijo real | joxemi lo declara pero NO lo cumple |
| Incognita | **el disparador de entrada** | hipotesis: breakout rango pre-apertura / momentum primeros minutos / gap fill |

## Criterio de exito (sustituye al de correlacion > 0.5)

```
1.  SR_EA  >  rho(EA, S&P) * SR_S&P
2.  Retorno POSITIVO en los peores meses del benchmark
3.  Sobrevivir al test de spread x2
```

## Dos mejoras concretas sobre joxemi

1. **Saltarse martes y jueves.** Son sus dos dias perdedores y los de mayor actividad.
   Riesgo de sobreajuste: validar con walk-forward, no asumirlo.
2. **Riesgo realmente constante.** Su D-Leverage medio es 2.38 pero pica hasta ~30.
   Implementando sizing fijo de verdad, el DD deberia bajar y el Sharpe subir.

-> Bajo la Opcion B **no hace falta clonarlo**: basta construir algo con su perfil de
descorrelacion y mejor control de riesgo. Objetivo mas alcanzable y mas valioso.
