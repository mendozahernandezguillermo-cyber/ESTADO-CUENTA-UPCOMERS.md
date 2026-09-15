# Protocolo: de auditar un historial a operar en vivo

Procedimiento completo, en cuatro tramos:

| Fases | De qué van |
|---|---|
| **0 a 7** | Auditar el historial de un tercero. Validado sobre la auditoría completa de **THL** (trader `joxemi`), partiendo de 48 candidatos del screener de Darwinex. Conclusión: su ventaja no existe. |
| **8 a 9** | Buscar una ventaja propia y elegir el vehículo. **19 familias de hipótesis probadas, 2 sobreviven.** Y el descubrimiento de que el control de riesgo es también una hipótesis que hay que medir. |
| **10 a 11** | Convertir la estrategia validada en código que la ejecuta, y descubrir que el bróker y el instrumento forman parte de la estrategia. |
| **12 a 13** | Las reglas de cobro de la firma, que resultan ser la restricción que manda. Y la puesta en marcha. |
| **14 a 15** | Lo que se aprende con la cuenta ya abierta: la mecánica del cobro fija el EV más que la estrategia, y el **coste de mantener la posición** decide antes que las dos. Aquí el sistema pasó de dos patas a una. |

**Nada de lo que sigue es teoría.** Cada umbral, cada filtro y cada aviso salió
de un error cometido o de una medición hecha. Cuando el documento dice «medido»,
hay un script en el repositorio que lo produjo; cuando dice «supuse», es un
aviso.

Los tres errores que más se repiten, y que conviene tener presentes al leer
cualquier fase:

1. **El fallo parcial silencioso.** Un filtro sin datos que devuelve cero, un
   parche que no encuentra su ancla, un redondeo con sesgo. Nada se rompe: todo
   sigue funcionando y midiendo lo que no es.
2. **El error de dirección.** Una decisión que parece prudente y es permisiva.
   `MathFloor` en el dimensionado, `MathMin` en un límite de pérdida, bloquear
   la cuenta al acercarse al suelo. Las tres parecían conservadoras.
3. **Verificar contra un punto que no distingue.** Contrastar una hipótesis
   contra un dato donde ella y su contraria dan el mismo resultado, y declararla
   confirmada.
4. **Medir la estrategia y no el entorno que la ejecuta.** Quince años de datos
   validaron la señal; nadie midió lo que cuesta tener la posición abierta en el
   bróker concreto. El carry resultó ser 1,74 veces todo el retorno, y una
   semana de demo lo habría enseñado gratis. Es el error más caro del proyecto
   y no aparecía en esta lista hasta la Fase 15.

---

## Fase 0 — Antes de empezar: la aritmética que decide si merece la pena

Esto va primero porque determina qué preguntas se pueden contestar y cuáles no.

### Umbral de detección según tamaño de muestra

Para separar un edge del ruido con α=0.05 (corregido por pruebas múltiples), el
acierto mínimo detectable es:

| n operaciones | acierto detectable |
|---|---|
| 155 | 59.8% |
| 500 | 55.5% |
| 1.000 | 53.9% |
| 2.000 | 52.7% |
| 3.500 | 52.1% |

### Operaciones necesarias para detectar un edge de tamaño dado

Con σ ≈ 70 bp por operación, potencia 80%:

| edge real | n necesaria | años a 160 op/año |
|---|---|---|
| +6,0 bp | 841 | 5 |
| +4,0 bp | 1.891 | 12 |
| +2,0 bp | 7.565 | 47 |
| +1,4 bp | 15.438 | **96** |

**Consecuencia práctica:** un trader que gana un 8% anual con 560 operaciones
necesita solo **1,4 bp por operación**. Ese edge es indetectable con cualquier
histórico existente. Si el objetivo es *demostrar* su ventaja, el proyecto está
muerto antes de empezar.

Lo que sí se puede hacer, y es el objeto de este protocolo: **identificar su
regla** a partir de ejemplos etiquetados. Reconocer un patrón binario con 900
casos marcados es rutina; estimar un retorno de 2 bp no lo es.

### Regla de oro

> Toda hipótesis derivada de los datos de precio debe contrastarse contra esos
> mismos datos con corrección por pruebas múltiples. Toda hipótesis derivada de
> los datos **del trader** puede contrastarse contra el precio como prueba única.
>
> La segunda vale mucho más. Prioriza siempre extraer información del trader
> antes de inventar hipótesis.

---

## Fase 0.5 — El embudo invertido (revisión posterior a THL)

El orden original de este protocolo —filtrar por rendimiento, coger los mejores,
investigar después el mecanismo— **es el orden equivocado**, y el motivo es
medible.

### El Sharpe que ves no es el que tiene

El estimador encoge hacia la media del universo con factor `k = τ²/(τ² + SE²)`,
donde `SE(s) = √((1 + s²/2)/T)`, `T` en años, y `τ` es la dispersión del Sharpe
verdadero entre darwins.

Un Sharpe **observado de 2,0** vale en realidad:

| Historial | SE | τ=0,3 | τ=0,5 | τ=0,8 |
|---|---|---|---|---|
| 6 meses | 2,45 | 0,03 | 0,08 | 0,19 |
| 12 meses | 1,73 | 0,06 | 0,15 | 0,35 |
| 24 meses | 1,22 | 0,11 | 0,29 | 0,60 |
| 60 meses | 0,77 | 0,26 | 0,59 | 1,03 |
| 120 meses | 0,55 | 0,46 | 0,91 | 1,36 |

Ni con diez años un 2,0 observado llega a valer 1,0 con `τ` realista.

### Y el screener te castiga por usarlo

Eligiendo el mejor de N candidatos por Sharpe observado (τ=0,3):

| N | 12 meses | 24 meses | 60 meses |
|---|---|---|---|
| 50 | 2,67 → **0,20** | 1,95 → 0,27 | 1,36 → 0,38 |
| 200 | 3,29 → **0,27** | 2,43 → 0,37 | 1,68 → 0,48 |
| 1000 | 3,92 → **0,36** | 2,90 → 0,47 | 2,04 → 0,59 |

Izquierda lo que muestra la pantalla, derecha lo que te llevas. **Cuantos más
candidatos filtres por rendimiento, peor es el ganador.**

Aplicado a THL: observado 0,491 sobre 50 meses → `SE`=0,52, `k`=0,48 →
**real ≈ 0,24**. Eso ya predecía que la réplica perdería dinero. Y perdió.

### El orden correcto

Ordenado por *cuánto se puede confiar en el filtro con historial corto*:

| # | Filtro | Por qué va aquí |
|---|---|---|
| 1 | **Longevidad** (≥36 meses, mejor 60) | es lo único que reduce el encogimiento, y no se puede fingir |
| 2 | **Mecanismo** (Fase 4.5) | mide *cómo* opera, no *cuánto* gana → **no sufre encogimiento y funciona con historial corto** |
| 3 | **Correlación** (Fase 5.5) | medible; su precisión depende del nº de bloques, no de la calidad del trader |
| 4 | **Rendimiento / Sharpe** | el más inflado por selección y el que menos decide |

**Cambio estructural que esto implica:** la extracción del journal (Fases 3-4)
deja de ser el análisis profundo de un finalista y pasa a ser un **filtro masivo**
aplicado a todos los supervivientes de la longevidad. El endpoint es público y
gratuito: usarlo sobre 30 candidatos cuesta lo mismo que sobre uno.

Y el objetivo cambia: **no busques `s`=2, que es inencontrable por selección.**
Busca tres estrategias con `s` real entre 0,5 y 1,0, mecanismo entendido y ρ baja.

---

## Fase 1 — Screener: obtener la lista corta

**Acceso:** requiere cuenta Darwinex (basta demo).

### Configuración validada

En `MANAGE CRITERIA`:

```
D-Score      55 – 100      ← SUELO, nunca techo
Ex           7 – 10        Experiencia
Mc           6 – max       Market Correlation
Rs           7 – 10        Risk Stability
Ra           6 – 10        Risk Adjustment
R+           6 – 10        Winning Consistency
R−           6 – 10        Losing Consistency
Dc           5 – 10        Duration Consistency
La           7 – 10        Loss Aversion
Cp           4 – 10        Scalability
```

**No marcar:** `Pf` (Performance) — está correlacionado con el D-Score y filtra dos
veces lo mismo. **Quitar** el VaR del subyacente — es redundante con `Ra`.

### Cuatro trampas del screener

**1. El D-Score como techo en vez de suelo.** Poner `0–55` devuelve un cementerio
de retornos negativos y cuentas con $0 de capital. Es un experimento de control
útil una vez; luego, siempre suelo.

**2. Ordenar por retorno acumulado *since inception*.** Ordena por antigüedad, no
por calidad. Un DARWIN de 11 años con 848% acumulado tiene un CAGR del 21%;
otro de 16 meses con 45% tiene un 32%. **Anualiza siempre antes de comparar.**

**3. El D-Score no mide lo que crees.** Desde 2020 se calcula solo con la
cotización del DARWIN, así que es momentum de la curva de equity. Sirve de suelo
de calidad, nunca de criterio de orden.

**4. Sobreajustar el filtro.** Si ajustas once criterios hasta que queda un solo
resultado, has sobreajustado el screener. Secuencia de relajación que funcionó:
quitar VaR → D-Score 70→55 → Mc 7→6 → Cp 5→4 → Dc 6→5.

**Salida esperada de esta fase:** 30-60 candidatos.

---

## Fase 2 — Triaje: de 48 a 1

**Acceso:** requiere cuenta (páginas de DARWIN individuales).

Aplicar en este orden. Cada filtro es eliminatorio y está ordenado por coste de
comprobación creciente.

### 2.1 Anualizar (gratis, elimina el ruido del ranking)

```
CAGR = (1 + retorno_acumulado)^(1/años) − 1
```

Recalcula el orden. En nuestro caso el mejor candidato aparecía 4º en la lista
original.

### 2.2 Test de rotación — ¿está la cuenta viva?

En la pestaña de comportamiento, busca la rotación **actual** y la **máxima
histórica**.

```
rotación_actual / rotación_máxima < 10%   →   DESCARTAR
```

**Caso real:** MQOH tenía 34,8% de CAGR, DD −11,88%, ratio 2,93 y un premio
DarwinIA de 60.000 €. Su rotación era `0,40 / 318,44 = 0,13%`. La cuenta estaba
**dormida**: el track record era histórico y el trader ya no operaba.

### 2.3 Zero vs Live — ¿hay dinero real detrás?

Busca `Trader's Total Equity` en la cabecera del DARWIN.

- `by ZERO` + equity `$0.00` → cuenta virtual de suscripción
- `LIVE` + equity real → dinero propio expuesto

No es eliminatorio por sí solo, pero una cuenta Zero exige el test de costes de
la fase 2.6 con mucho más rigor.

### 2.4 z-score del edge, corregido por selección múltiple

Con acierto `p`, ganador medio `W`, perdedor medio `L` y `n` operaciones:

```
WR_breakeven = L / (W + L)
margen       = p − WR_breakeven
SE           = sqrt(p(1−p)/n)
z            = margen / SE
```

Y aquí lo que casi nadie hace: **si has cribado 48 candidatos, esperas
`48 × p_valor` falsos positivos.**

**Caso real:** HSYF daba `z = 1,97`, `p ≈ 0,024`. Con 48 candidatos, eso son
`48 × 0,024 = 1,15` falsos positivos esperados. Su edge era exactamente lo que
cabía esperar del azar. **Descartado.**

### 2.5 Pestaña `Correlación` — el punto ciego del screener

**Ningún Investable Attribute mide originalidad.** `Mc` mide correlación con los
*activos subyacentes*, no con *otros DARWINs*.

Abre la pestaña `Correlación`, ventana 1M:

```
correlación > 0.7 con otro DARWIN   →   investigar el clúster
```

**Caso real:** THL correlacionaba 0,92 con ZJM. Al abrir ZJM: **el mismo
trader**, `joxemi`, con dos implementaciones de la misma idea. Si hubiéramos
metido los dos en una cartera "diversificada", habríamos duplicado la apuesta.

Ojo también con esto: si un DARWIN tiene una correlación alta y el otro no
aparece en la lista del primero, el asimétrico suele ser el original.

### 2.6 Test de estrés de costes

Con el spread real del instrumento que vas a operar:

```
esperanza_neta = p·W − (1−p)·L − spread
```

Repítelo con spread ×2 y ×4. Si no sobrevive a ×2, descartar.

**Nota importante:** los "pips" que publica Darwinex **son inservibles si el
trader opera varios instrumentos**. En THL, el ganador medio de 22,02 "pips"
mezclaba puntos de índice con pips de divisa. Sobre NASDAQ a 29.000, 22 puntos
son el 0,8% de una sola vela de un minuto — imposible que sea el objetivo de
alguien que aguanta 2h49m. **Usa solo métricas adimensionales:** acierto,
payoff, duración, frecuencia, reparto por sesión.

### 2.7 Comprobación de significancia del propio track record

Antes de invertir un mes en ingeniería inversa, comprueba si el trader ha
demostrado algo:

```
SR_mensual = SR_anual / √12
SE(SR)     = √((1 + SR_mensual²/2) / n_meses) × √12
t          = SR_anual / SE(SR)
```

**Caso real:** THL, Sharpe 0,491 sobre 50 meses → `SE = 0,492` → **`t ≈ 1,0`**.

El mejor de 48 candidatos no tenía track record estadísticamente significativo.
Ese cálculo cuesta dos minutos y te ahorra semanas.

---

## Fase 3 — Extracción forense vía DevTools

**Acceso: NINGUNO.** El endpoint es público. Funciona sin cuenta, sin sesión y
sin pagar.

Esta es la fase que convierte la auditoría de estadística en forense.

### 3.1 Localizar el `accountName` del DARWIN

1. Abre la página del DARWIN, p. ej. `darwinex.com/darwin/THL.5.17`
2. Abre DevTools **antes de tocar nada**:
   - Clic derecho → `Inspeccionar` (el más fiable)
   - o `Ctrl` + `Shift` + `I`
   - o menú `⋮` → `Más herramientas` → `Herramientas para desarrolladores`
   - en portátiles, `F12` suele estar capturado: prueba `Fn` + `F12`
3. Pestaña `Network` → filtro `Fetch/XHR`
4. `Ctrl` + `R` para recargar con DevTools abierto
5. Pulsa la pestaña **`Estrategia subyacente`** (ahí vive el Trading Journal)
6. Ordena por la columna `Size` pulsando en su cabecera
7. La petición más pesada será `tradingjournal?accountName=...` (~425 kB)
8. Clic derecho sobre ella → `Copy` → `Copy link address`

### 3.2 El endpoint

```
https://www.darwinex.com/api/tradingaccounts/tradingjournal
    ?accountName=D.259985
    &graphic=JOURNAL
    &zoom=ALL
```

- `accountName` — identificador de la cuenta del DARWIN (no es tuyo, es suyo)
- `zoom=ALL` — histórico completo; es lo que hace que pese 425 kB
- **No requiere cabeceras ni cookies.** Se puede bajar con `curl` desde cualquier
  máquina:

```bash
curl -s -o journal.json \
  "https://www.darwinex.com/api/tradingaccounts/tradingjournal?accountName=D.259985&graphic=JOURNAL&zoom=ALL"
```

### 3.3 Otros endpoints visibles en la misma pestaña

```
drawdowns?from=0&to=...        ~70 kB
THL.5.17?start=0&end=...       ~25 kB   (cotización del DARWIN)
```

### 3.4 Nota sobre legitimidad

Es contenido que el navegador ya recibe para pintar una página pública. No hay
control de acceso que sortear. Aun así: ve sin prisa, no martillees el servidor,
y guarda el JSON en local en vez de repetir la petición.

---

## Fase 4 — Decodificar el journal

El fichero es un array de arrays de **11 campos**. Esquema deducido:

| campo | contenido |
|---|---|
| `c1` | **timestamp en ms epoch (UTC)** |
| `c5` | puntuación tipo D-Score en ese momento |
| `c6` | **contador acumulado de posiciones** (su máximo = total del journal) |
| `c8` | **número de operaciones abiertas** (0-7) |
| `c9` | **instrumentos abiertos, con signo**: `+` largo, `−` corto, vacío = plano |
| `c0,c2,c3,c4,c7,c10` | retornos y métricas auxiliares, no imprescindibles |

### 4.1 El hallazgo clave sobre el formato

**No es una lista de operaciones: es una línea temporal de estados.** Cada
registro es un momento en que cambió la composición de la cartera.

```
[6840.0, 1.65936600039E12, ..., "+NASDAQ 100 (Mini)", 0.0]
[6846.0, 1.659366360047E12, ..., "+Germany 30 (Mini),+NASDAQ 100 (Mini)", 0.0]
[6860.0, 1.659367200073E12, ..., "", 0.0]
```

De ahí se derivan entradas y salidas:

```python
def estado(txt, instrumento="NASDAQ"):
    """+1 largo, -1 corto, 0 cubierto, None si no está abierto."""
    if not isinstance(txt, str) or instrumento not in txt:
        return None
    for p in txt.split(","):
        p = p.strip()
        if instrumento in p:
            return 1 if p.startswith("+") else (-1 if p.startswith("-") else 0)
    return None

J["est"] = J["c9"].apply(estado)
prev = J["est"].shift(1)
entradas = J["est"].notna() & prev.isna()    # ausente -> presente
salidas  = J["est"].isna() & prev.notna()    # presente -> ausente
```

### 4.2 Dos avisos técnicos que cuestan tiempo

**Trabaja en milisegundos epoch, no en `datetime`.** Los dos ficheros (journal y
precio) vienen en ms UTC. Convertir a `datetime` con zona provoca errores de
`tz-naive vs tz-aware` en `searchsorted` que no aportan nada.

**Cuidado con la zona horaria de la página.** El histograma de sesiones de la
página del DARWIN está en **UTC**, no en CET. Leerlo como CET desplaza toda la
estrategia dos horas. En nuestro caso construimos un EA entero apuntando a la
apertura cash cuando su pico real estaba dos horas después.

---

## Fase 4.5 — Detector de mecanismo: grid y martingala

**El filtro más valioso del protocolo**, por tres razones: es binario, descarta
la única cosa que arruina el plan de forma catastrófica, y **funciona con
historial corto** porque mide el mecanismo y no la muestra de retornos.

Usa tres campos del journal: `c3` (P&L abierto), `c5` (tamaño) y `c8`
(operaciones abiertas simultáneas).

### Los seis rasgos, con THL como referencia negativa medida

| Rasgo | Qué mide | THL (limpio) | Umbral |
|---|---|---|---|
| **R1** añadir a perdedoras | `P(c8↑ \| pierde y empeora)` contra `P(c8↑ \| gana y mejora)` | ratio **0,59** | ratio >1,5 y p>0,35 |
| **R2** escalar en pérdida | % episodios con `c5` creciendo >5% estando en pérdida | **0,0%** exacto | >2% |
| **R3** cobertura | registros con `±` (largo y corto del mismo activo) | 0,13% | >1% |
| **R4** simultáneas | fracción de registros con `c8` ≥ 5 | 2,8% | >8% |
| **R5** asimetría | asimetría del resultado por episodio (Δ`c2`) | **+1,01** | < −0,50 |
| **R6** no cortar pérdidas | duración mediana perdedoras / ganadoras | 1,44 | >2,0 |

Veredicto: 0 banderas limpio · 1 revisar a mano · 2-3 dudoso · ≥4 rechazar.

Dato estructural útil: THL escala **hacia fuera**. `c8` baja monótonamente en
46,3% de los episodios y sube monótonamente en solo 4,4%.

### Obligatorio: validar con controles positivos

**Un detector que nunca ha disparado no está validado.** Hay que fabricar dos
journals sintéticos —una martingala y una grid— con el mismo esquema de campos, y
comprobar que salen rechazados. En este proyecto la primera versión marcaba una
martingala genuina como *«probablemente limpia»* (1 de 6). Tres errores que solo
aparecieron con el control:

1. **Umbrales puestos a ojo.** Exigía 15% en R2 cuando la referencia limpia real
   marca **0,0%**. Cualquier valor distinto de cero ya es anómalo.
2. **R4 usaba la media** de operaciones abiertas, que no discrimina: THL 1,92
   contra grid sintética 1,96. Lo que discrimina es el peso de la cola.
3. **R5 y R6 medían sobre ceros** por un bug del generador: `c2` no evolucionaba
   dentro del episodio.

Corregido, separa limpiamente: **THL 0/6 · martingala 4/6 · grid 6/6.**

### Por qué este filtro es el crítico

Una grid muestra volatilidad baja y Sharpe alto durante doce meses y luego pierde
el 40% en una tarde. Falsifica justo la variable que decide el resultado en una
cuenta prop. Medido: con drawdown trailing, una grid da `P(cobrar)` = **0,0%** y
EV = −(cuota), mientras su track record parecía impecable.

Implementación: `thl-journal/detector_grid.py` + `control_positivo.py`.

---

## Fase 5 — Análisis forense

### 5.1 Caracterización descriptiva (barata y muy informativa)

Sobre los timestamps de entrada:

| Medición | Qué revela | Valor en THL |
|---|---|---|
| % en múltiplos de 5/15/30/60 min | **el timeframe en que evalúa** | 92% en múltiplos de 5 |
| % con segundo = 00 | órdenes a mercado en cierre de vela vs órdenes en espera | 95,3% |
| histograma por hora local | su ventana real | pico 11:00 NY |
| ¿el pico se mueve con el DST? | a qué reloj está anclado | fijo en NY/CET, se mueve en UTC |
| reparto largo/corto | sesgo direccional | 64 / 36 |
| entradas por día operado | frecuencia | 1,83 |
| % que terminan en otro día natural | ¿pasa la noche? | 18% |
| evolución por año | ¿ha cambiado el sistema? | pico movido de 11:00 a 11:30 en 2025 |

**El test de múltiplos de 5 minutos es el más rentable de todos.** Con dos líneas
de código te dice si el sistema es dirigido por vela o por nivel de precio.

### 5.2 Identificación del disparador — controles emparejados

El diseño que funciona:

> Cada entrada real se compara con **controles del mismo minuto de reloj en otros
> días**. Eso elimina por construcción el efecto de hora del día.

```python
# para cada entrada: 3 controles al azar en el mismo minuto, otras fechas
# luego comparar rasgos con ttest_ind
```

Rasgos que merecen la pena:

- retorno de los 5/15/30/60/120 minutos previos
- **posición dentro del rango del día** `(px − low) / (high − low)`
- rango del día acumulado, en bp
- volatilidad realizada de los 30 min previos
- distancia al máximo y al mínimo del día

**Caso real:** la posición en el rango dio `t = +34,7` en sus largos y `t = −37,0`
en sus cortos. Compra en la banda alta (mediana 0,904), vende en la baja
(mediana 0,110), y los dos histogramas casi no se solapan. **Ese es el
disparador, leído, no adivinado.**

### 5.3 Prueba de las salidas — contra la rejilla de tiempos fijos

Empareja cada entrada con su salida y calcula qué habría pasado cerrando a 15,
30, 45, 60, 75, 90, 120, 150, 180 y 240 minutos.

```
Si su cierre real bate a TODAS las alternativas fijas → hay habilidad
Si queda en medio                                     → su salida es un reloj
```

**Caso real:** su salida real dio +3,37 bp; cerrar mecánicamente a 240 minutos
daba +3,83 bp. Test emparejado: `−0,46 bp, t = −0,23`. **Sin habilidad en la
salida.** Esto reconstruye el chart `CLOSE_STRATEGY` del Raw DARWIN Data sin
necesitar acceso FTP.

Complementos útiles:

- **captura = resultado / MFE** — cuánto del recorrido favorable se lleva
  (THL: 28% de mediana; cierra cerca del máximo solo el 7,3% de las veces)
- **distribución del resultado** — un pico en una banda positiva concreta
  delataría un objetivo duro; THL no lo tiene (sd 34,5 bp, distribución ancha)
- **duración vs resultado** — en THL es monótono (`t` de −7,74 a +5,49): corta
  perdedoras y deja correr ganadoras. Pero **la duración es consecuencia, no
  causa**: no se puede "operar solo las largas".

### 5.4 Prueba de la selección

Genera todas las oportunidades que marca la regla, etiquétalas según si él las
tomó (±5 min y misma dirección), y compara el **retorno futuro** de tomadas
frente a descartadas.

Si hay diferencia, la selección aporta valor y los rasgos que difieren señalan
el criterio. Si no, el edge está en otra parte.

**Caso real:** tomadas +5,07 bp vs descartadas +1,07 bp a 240 min. Dirección
correcta pero `t = 1,74`: **no significativo**. Y de los dos rasgos que las
distinguían con fuerza (volatilidad `t=6,28`, hora del día `t=−8,12`), al
comprobar si llevaban retorno: la volatilidad **no** (opera en uno de los peores
quintiles) y la hora **sí, pero solo desde 2020**.

---

## Fase 5.5 — Matriz de correlación entre candidatos

Sirve para dos cosas: detectar que dos darwins son **el mismo trader** (aquí THL
y ZJM a ρ=0,92 lo eran) y calcular el multiplicador de Sharpe de la cartera, que
es lo que convierte candidatos en dinero.

Serie de retornos = diferencias de `log(1 + c2/100)` resampleadas a diario.

### El multiplicador de Sharpe

Para `n` estrategias equiponderadas con correlación media ρ:

```
mult = √(n / (1 + (n−1)·ρ))
```

| ρ | mult (n=3) |
|---|---|
| 0,0 | 1,73 |
| 0,3 | 1,37 |
| 0,6 | 1,17 |
| 0,9 | 1,04 |

A ρ=0,9 tener tres estrategias no aporta nada: es una sola apuesta repetida.

### La ley de atenuación por huecos, y por qué NO hay que corregirla

Si los darwins no operan todos los días, la correlación medida se atenúa:

```
ρ_medido = ρ_real · √(p_A · p_B)      p = fracción de días activos
```

Verificado a tres decimales. Y **agregar a menor frecuencia no lo corrige**: ρ
real 0,60 se mide 0,237 en diario y 0,231 en mensual.

Pero la conclusión es la contraria de la intuitiva: **no hay que corregirlo.**
Predecir la volatilidad de la cartera con el ρ *medido* acierta la realizada con
error −0,0%. Los huecos son diversificación real, no un artefacto. (Yo me
equivoqué aquí primero: lo llamé sesgo peligroso y propuse agregar. Las dos cosas
eran falsas y el test las refutó.)

### Lo que la matriz NO ve: dependencia de cola

Dos carteras con el mismo ρ de Pearson pueden hundirse de forma muy distinta en
los días malos, que son justo los que tocan el límite de drawdown. Ninguna
frecuencia de Pearson lo detecta. Hay que mirar la correlación condicionada a días
malos **condicionando sobre una variable externa** (p. ej. los peores días del
índice), nunca sobre la propia cartera: condicionar sobre su peor decil
anticorrelaciona los componentes por construcción y da un número sin sentido.

### Límite de precisión

Con 12 meses hay ~12 bloques mensuales → `SE(ρ) ≈ 0,33`. **No se puede distinguir
ρ=0,3 de ρ=0,6 con un año de datos.** Esa horquilla hay que arrastrarla al
resultado, no ignorarla.

Implementación: `thl-journal/correlacion.py`, `ley_atenuacion.py`.

---

## Fase 6 — Disciplina de validación

Los tres errores que cometimos, cómo se ven y cómo evitarlos.

### 6.1 Prueba de desplazamiento de ancla

**Mueve el punto de medida un minuto.** Si el efecto se desploma, vivía en un
artefacto del instante concreto, no en el mercado.

```
ancla 09:30+0min    +10,31 bp   t=+2,68
ancla 09:30+1min     +3,55 bp   t=+0,87   ← se desploma
```

Un efecto real no depende de un minuto exacto.

### 6.2 Contraste obligatorio contra los datos del bróker

**El backtest en tu bróker no es una formalidad final: es el único detector de
errores que funcionó.** Los tres bugs de este proyecto los encontró el Probador
de MT5, ninguno el análisis.

Antes de creer un backtest sobre datos externos, mide sobre los datos del
instrumento que vas a operar de verdad:

- ¿coincide el número de señales? (nosotros: 72 = 72, correcto)
- ¿coincide la microestructura? (salto en la apertura, tamaño de las primeras
  velas)
- ¿coinciden los niveles de precio?

**Aviso serio:** un CFD derivado de futuros y un índice cash **no son la misma
serie**. En marzo de 2026 la base entre ambos pasó de +2,2 a +259,5 puntos
alrededor del vencimiento del E-mini, y los retornos de 15 minutos divergían
hasta 75 bp. Un backtest de 15 años sobre el cash **no describe** el CFD que
operas.

### 6.3 Los filtros deben fallar en CERRADO

```cpp
// MAL: si no hay referencia, deja pasar todo
if(mediana > 0 && rango < umbral * mediana) return;

// BIEN: si no hay referencia, no se opera
if(mediana <= 0) { contador++; return; }
if(rango < umbral * mediana) return;
```

Escribimos un filtro que exigía 20 días de histórico y devolvía 0 si no los
había. Con un histórico que arrancaba un mes antes, **el filtro se saltó por
completo durante el primer 13% del test** y contaminó las estadísticas sin dar
ni un aviso.

### 6.4 Cuidado con las unidades homónimas

Dos errores del mismo tipo:

- **Spread**: `(ask−bid)/_Point` con `Digits=2` convierte 0,80 puntos de índice en
  **80**. Un límite de "3" rechazaba todos los días. **Expresa los umbrales en
  bp**, que no dependen de la escala.
- **Rango acumulado vs rango de día completo**: comparar el rango de media mañana
  contra medianas de días enteros no es homologable. El rango crece como `√t`;
  normaliza: `esperado = mediana_20d × √(transcurrido/1440)`.

### 6.5 La `n` efectiva no es la nominal

71.635 velas M5 consecutivas en banda dan `t = 5,40`. La misma regla sin
solapar, con máximo 2 al día, da `t = 0,52` sobre 7.138 operaciones.

**Velas contiguas cuentan el mismo movimiento muchas veces.** Cualquier `t`
calculada sobre candidatas solapadas está inflada.

### 6.6 Verificación de implementación antes de leer resultados

No mires el P&L hasta haber comprobado que el EA hace lo que dice. Registra en el
log el valor de la condición en cada entrada:

```
LARGO 0.02 @ 24734.65 | pos_rango 0.983 | rango 120 bp | spread 0.32 bp
```

Si `pos_rango` sale 0,55 cuando la banda es 0,80, hay un bug y el resto de
números no significa nada. Si sale **por encima de 1,000**, el rango excluye la
vela actual y la semántica no coincide con la de la medición.

### 6.7 El Probador de MT5 conserva los inputs viejos

Nos costó dos vueltas. **Comprueba a mano la pestaña `Inputs`** cada vez que
recompiles, especialmente si has añadido parámetros nuevos.

---

## Fase 7 — Criterio de decisión

### Cuándo seguir adelante

- El disparador queda identificado con `|t| > 5` sobre controles emparejados
- La regla replicada, en backtest limpio y sin solapar, da `t > 2` **en las dos
  mitades de la muestra**
- Sobrevive al desplazamiento de ancla
- El conteo de señales coincide con los datos de tu bróker
- Sobrevive al spread ×2

### Cuándo parar

- El óptimo de un parámetro **se mueve** entre subperiodos (5 min en una mitad,
  15 en la otra) → es un pico, no una meseta
- El efecto solo existe en la mitad reciente
- **El SIGNO de la media cambia** según cambios triviales de especificación, o
  una fracción apreciable de las variantes pierde el efecto por completo

  *Corrección de la primera versión, que decía «la `t` oscila entre 0,4 y 3,4».
  Esa redacción es incorrecta y habría rechazado una estrategia válida.
  `t = media / sd × √n`, así que alargar una tenencia sube la desviación sin
  cambiar la media y la `t` cae por pura aritmética. Medido en la rejilla de 56
  especificaciones horarias de la estrategia pre-FOMC: la `t` va de 1,54 a 4,61
  mientras la media se mantiene entre +18,9 y +32,2 bp y **ninguna de las 56
  celdas sale negativa**. Lo que hay que barrer y publicar es la rejilla de
  MEDIAS, contando cambios de signo; la `t` solo dice con qué eficiencia
  capturas el efecto.*

  Y la distinción que hay que hacer siempre: **una degradación que sigue una
  dirección predicha de antemano, por un mecanismo medido por separado, es
  confirmación del mecanismo.** Una que va en direcciones arbitrarias es
  fragilidad. Registra la predicción antes de correr el barrido; si no, no
  podrás distinguirlas.

  Si la especificación elegida resulta ser el máximo de la rejilla, dilo. Y
  comprueba si el máximo de la MEDIA cae en otra celda: si tu elección maximiza
  la `t` pero no la media, es indicio de que no estabas ajustando el retorno.
- El propio track record del trader tiene `t ≈ 1`
- **El detector de mecanismo marca 2 o más banderas** (Fase 4.5)
- **ρ con un candidato ya aceptado supera 0,85** → es el mismo trader, no una
  segunda estrategia
- **El Sharpe observado, encogido con `k = τ²/(τ² + SE²)`, queda por debajo de
  0,3** — que es donde quedó THL

### Y lo más importante

> Llevar la cuenta de cuántas pruebas has hecho sobre la misma serie de precios.
>
> A partir de cierto punto, todo hallazgo nuevo es simplemente el siguiente de la
> cola de los que no replicarán. En este proyecto ese punto llegó tras cuatro
> hipótesis y unas veinte especificaciones. Reconocerlo y parar es parte del
> método, no un fracaso.

---

## Fase 8 — Del DARWIN a la cuenta prop

El destino de esto es normalmente una cuenta financiada, y sus reglas cambian qué
estrategia sirve. Dos principios medidos:

### La volatilidad óptima es propiedad de la FIRMA, no tuya

**El objetivo de beneficio pone un suelo a la volatilidad; el tipo de drawdown
pone un techo.**

| Estructura | Vol óptima (s=1) |
|---|---|
| Instant funding sin objetivo, trailing 7% | **6%** |
| Challenge +10% y +5%, estático 10% | **12%** |

Un `s`=1 a vol 4% en un challenge da EV negativo: sobrevives pero nunca llegas al
objetivo. En instant funding la vol baja es óptima porque cobras desde el primer
dólar.

### Los datos que hay que extraer de cualquier reglamento

```
cuota · reembolsable · split
dd_dia (%) · dd_max (%) · tipo_dd (estático / trailing EOD / trailing tiempo real)
objetivos de beneficio · días mínimos · beneficio mínimo por día · best day (%)
```

Ordenados por impacto medido: (1) estático contra trailing, (2) regla de
consistencia, (3) objetivo de beneficio, (4) historial de pagos verificable,
(5) cuota y split. Los dos primeros cambian el EV por múltiplos o le cambian el
signo; los últimos lo mueven decenas de por ciento.

### Estructura de cartera

A capital igualado: **repartir estrategias en cuentas distintas cuesta un tercio
del EV**; repartir cuentas entre firmas es gratis (45.341 $ contra 45.596 $). Cada
cuenta debe llevar **la cartera completa**, y las cuentas deben estar en **firmas
distintas** — porque el riesgo dominante no es estadístico, es que no paguen, y
eso solo se diversifica entre firmas.

### Dos restricciones contractuales

FTMO limita a 400.000 $ «per trader **or strategy**», y usar la misma estrategia
en varias cuentas para saltarse el límite es violación expresa. Y confirma por
escrito que permiten **operativa automatizada y replicación de señales** antes de
mirar cualquier otra cosa: es un filtro binario que invalida todo lo demás.

Implementación: `prop-instant/marco_general.py`, paramétrico por firma.

---

## Fase 9 — El control de riesgo también es una hipótesis

Todas las fases anteriores tratan la estrategia como algo que hay que medir y
el control de riesgo como algo que se diseña. Eso está mal, y me costó
descubrirlo escribiendo `EA_Guardian`.

**El fallo.** Escribí un vigilante que cerraba todas las posiciones y bloqueaba
la cuenta cuando la equity se acercaba al suelo del drawdown. Parece
evidentemente prudente. Al simularlo apareció lo contrario:

| Diseño | P(quema) | P(cobro) | EV anual |
|---|---|---|---|
| Sin vigilante | 11,4% | 69,0% | 1.619 $ |
| Cerrar con colchón 1,5% y bloquear | **21,6%** | 66,9% | 1.577 $ |
| Cerrar con colchón 3,0% y bloquear | **41,3%** | 59,5% | 1.419 $ |
| Escalar el tamaño con el margen | **0,3%** | 66,1% | 1.535 $ |
| Escalar **y además** cerrar al 0,5% | 1,0% | 66,2% | 1.523 $ |

El vigilante que cerraba **triplicaba** la probabilidad de perder la cuenta.

**El mecanismo.** Si la equity queda por debajo del nivel de cierre, el bloqueo
se levanta al día siguiente pero la equity sigue debajo, así que vuelve a
disparar. Y otra vez. Es un **estado absorbente**: la cuenta no rompe el límite
pero no vuelve a operar, y cada intervención cruza un spread que la empuja al
suelo. Un drawdown recuperable se convierte en una muerte lenta segura.

Con coste de ejecución cero el efecto no se ve: la cuenta se queda congelada,
la quema baja al 5,8% y el diseño parece bueno. **El bug solo aparece cuando se
cobra el coste real de cerrar.** Un modelo de riesgo sin costes de transacción
puede recomendar exactamente lo contrario de lo correcto.

**Las reglas que se deducen.**

1. **Un control de riesgo se mide con el mismo rigor que una señal de entrada.**
   Barrido de parámetros, coste de ejecución cobrado, y comparación contra la
   referencia de no hacer nada. «Es prudente» no es evidencia.

2. **Cobra siempre el coste de cada intervención.** Es el término que separa un
   control que funciona de uno que sangra. Si el control actúa a menudo, ese
   término domina.

3. **Desconfía de cualquier control que pueda dejar la cuenta sin operar.** Una
   cuenta que no opera no puede recuperarse. Todo umbral de bloqueo necesita una
   vía de salida que no dependa de operar para cruzarlo.

4. **Reducir tamaño domina a parar.** Escalar la exposición con el presupuesto
   de riesgo que queda agota el presupuesto de forma asintótica en vez de a
   golpe, y conserva la capacidad de recuperación. Es la misma idea que el
   dimensionado por volatilidad, aplicada al margen en vez de a la varianza.

5. **Apilar controles no suma.** Añadir el cierre duro por encima del escalado
   empeoró el resultado: cristaliza la pérdida y paga el spread justo cuando la
   posición ya reducida habría aguantado. Cada capa hay que medirla *dado* que
   las otras están puestas.

6. **Separa el drawdown de la avería.** Un drawdown es el funcionamiento normal
   de una estrategia con varianza: se gestiona con tamaño. Una avería —un EA
   abriendo en bucle, un stop que no llegó al servidor— es algo roto: ahí sí hay
   que cerrar y bloquear hasta que un humano lo mire. Confundirlas hace que el
   sistema trate el ruido como una emergencia.

### El corolario sobre el supuesto del stop

El mismo escepticismo se aplica al stop loss. Todas mis simulaciones daban por
hecho que un stop de 80 bp se ejecuta a 80 bp. Medido sobre los M1 reales, en
117 eventos:

- 9 stops ejecutados, de los cuales **5 rellenaron peor que −80 bp**;
- deslizamiento máximo **54,1 bp**, medio 19,7 bp cuando ocurre;
- peor evento real **−133,4 bp**, no los −80 supuestos;
- 36 de 117 eventos tuvieron un hueco sin cotización de más de 60 minutos, y el
  más largo fue de 240 minutos. Durante un hueco un stop no puede ejecutarse.

**Un stop es una orden, no una garantía.** Cualquier cifra de «pérdida máxima»
derivada de la distancia del stop es un suelo optimista. Mídela contra los
rellenos reales antes de dimensionar con ella.

### Los errores de dirección: el patrón que más veces se ha repetido

Escribiendo los tres EAs aparecieron **tres bugs con la misma forma**: una
decisión que parecía prudente y que en realidad era permisiva. Ninguno lo
detectó el compilador y dos habrían costado la cuenta.

| Dónde | Lo que escribí | Por qué parecía prudente | Lo que hacía de verdad |
|---|---|---|---|
| Dimensionado del trend | `MathFloor` en los lotes | «redondear hacia abajo arriesga menos» | sesgo del −20% en la volatilidad de la pata; el peso efectivo de la estrategia se hundía |
| Base del límite diario | `MathMin(saldo, equity)` | «la lectura estricta no te descalifica por optimista» | base menor → suelo menor → **81% de margen inventado** |
| Bloqueo del vigilante | cerrar y bloquear cerca del suelo | «parar antes de romper» | estado absorbente: triplicaba la probabilidad de ruina |

**La regla.** Ante cualquier `min`, `max`, `floor`, `ceil` o umbral en un
control de riesgo, escribe explícitamente qué dirección es la permisiva
**antes** de elegir. La intuición de «lo estricto» falla porque el signo se
invierte dos veces: una base más baja da un suelo más bajo, y un suelo más
bajo da más margen. Dos inversiones y ya estás en el lado equivocado.

### Verifica solo contra puntos donde las hipótesis divergen

Éste es el error epistemológico más caro de toda la sesión, y no es de código.

Comprobé mi fórmula del límite diario contra el panel real de la firma y
coincidió **al céntimo**: `24.759,77 × 0,96 = 23.769,38`. Lo declaré verificado.

Pero en ese instante el P/G flotante era **cero**, así que el saldo y la equity
eran el mismo número y `min` y `max` daban idéntico resultado. **Contrasté la
hipótesis contra el único punto de datos incapaz de distinguirla de su
contraria.** El bug sobrevivió a su propia verificación y siguió ahí ocho
turnos, hasta que apareció la documentación oficial.

**Las reglas que se deducen.**

1. **Antes de verificar, pregunta qué valor tomaría la hipótesis rival en ese
   punto.** Si la respuesta es «el mismo», el punto no vale y hay que buscar
   otro. Una coincidencia entre hipótesis indistinguibles no es evidencia de
   nada.

2. **Construye el punto de contraste a propósito.** Aquí bastaba con dejar una
   posición abierta con flotante distinto de cero: en cuanto `saldo ≠ equity`,
   las dos fórmulas se separan y la comparación decide.

3. **Desconfía especialmente de las verificaciones que salen perfectas.** Un
   ajuste al céntimo sobre un solo punto suele significar que el punto era
   trivial, no que la fórmula sea correcta. Los aciertos limpios de la sesión
   que sí valieron algo —el control positivo del EA del FOMC, la invariancia
   de escala del empalme— se hicieron sobre 117 y 8 casos, no sobre uno.

4. **Cuando exista documentación oficial, léela antes de deducir la regla de
   los datos.** Dediqué un turno entero a inferir la fórmula del drawdown
   desde capturas del panel, y acerté en la forma pero fallé en dos detalles
   (`MAYOR` en vez de `MENOR`, y las 00:00 UTC en vez de las 17:00 de Nueva
   York) que el documento decía de forma explícita. La ingeniería inversa es
   para cuando no hay documento, no para ahorrarse buscarlo.

### Y una trampa de operación, no de cálculo

Las variables globales del terminal MT5 son **del terminal, no de la cuenta**.
Al iniciar sesión en otra cuenta, un vigilante que persista su estado ahí se
encuentra el pico de equity y la base diaria de la cuenta anterior, y calcula
los suelos de una cuenta que ya no existe — con números que parecen válidos.
Todo estado persistente tiene que ir marcado con el identificador de la cuenta
y borrarse cuando cambie.

---

## Fase 10 — De la estrategia validada al EA que la ejecuta

Las fases anteriores terminan cuando una estrategia sobrevive a la validación.
Eso no es el final: es el punto en que empieza la parte donde se pierde el
dinero. Tres EAs y unos treinta bugs después, esto es lo que aprendí.

**La regla que resume la fase.** Ningún bug de los que aparecieron lo encontró
leyendo el código. Todos los encontró el Probador, el log en vivo, un control
escrito aparte, o un comprobador mecánico. **Revisar tu propio código no
funciona.** Hay que construir algo que lo contradiga.

### Catálogo de trampas, por familia

**1. Trampas de unidades.** La más caras y las más fáciles de escribir.

| Qué escribí | Qué pasó |
|---|---|
| Spread medido en `_Point` | con `Digits=2` convertía 0,80 en 80 y rechazaba todos los días |
| Deslizamiento en puntos | 30 puntos son 0,07 bp en el oro y 2,6 bp en EUR/USD: el mismo número significa cosas 37 veces distintas |
| Lotes desde el tamaño de contrato | los tamaños reales eran 10, 10, 500 y 100.000 según el instrumento; nada de lo que supuse coincidió |

La solución general: **derivar todo del `tick value` y el `tick size` del
símbolo**, que ya vienen en la divisa de la cuenta.

```
lotes = exposición × equity × tickSize / (precio × tickValue)
nocional por lote = precio × tickValue / tickSize
```

Esa fórmula funciona en índices, metales y divisas sin casos especiales. Mi
predicción de qué mercados cabrían en la cuenta falló; el EA acertó, porque
leyó las especificaciones en vez de suponerlas.

**2. Trampas de tiempo.** Hay cuatro relojes y ninguno es el que crees.

```
hora local del PC     ->  la que sale en los timestamps del log
hora del servidor     ->  TimeCurrent()
UTC                   ->  TimeGMT(), y define el día de riesgo de la firma
hora de Nueva York    ->  la que define la estrategia
```

En la instalación de este caso: local UTC−6, servidor GMT+2, ocho horas de
diferencia entre el log y el servidor. Los bugs que salieron de ahí:

- **`TimeGMT()` devuelve lo mismo que `TimeCurrent()` en el Probador.** Mi
  guardarraíl era `|dif| <= 14 h`, y `dif = 0` lo pasaba. El EA operó dos
  horas antes durante todo un backtest sin una sola señal de alarma. Un
  guardarraíl tiene que comprobar que el dato EXISTE, no solo que no es
  absurdo: `dif != 0 && |dif| <= 14h`.
- **Truncamiento entero de una diferencia de fechas.** `(ahora - ahoraNY)/3600`
  con las dos muestras tomadas medio segundo aparte da 21599 s, y la división
  entera se come una hora. Salía «GMT+1» y «desfase 5 h» cuando eran GMT+2 y
  6 h. Redondear, nunca truncar.
- **Offset fijo servidor→NY.** El servidor estaba en GMT+2 fijo y Nueva York
  no: el desfase cambia de 6 a 7 horas el primer domingo de noviembre. Un
  offset fijo habría operado una hora tarde media temporada, en silencio.
- **La resta de `datetime` sin signo.** Restar dos `datetime` y comparar contra
  otro `datetime` deja pasar diferencias negativas como si fueran enormes.
  Calcular la edad en `long` con signo y declarar caducado lo que venga del
  futuro.

**3. Trampas de fallo parcial silencioso.** La familia más peligrosa, porque
no produce ningún síntoma.

- **Un filtro sin datos que devuelve 0 y se salta solo.** Todo filtro que no
  pueda evaluarse debe **fallar en cerrado** y contarlo en un contador visible.
- **`MathFloor` al redondear lotes.** Parecía prudente. Introducía un sesgo
  sistemático que dejaba la pata entera al 80% de su volatilidad objetivo en
  una cuenta de 25K. Redondear al más cercano deja el error centrado; medido,
  los errores individuales van de −12% a +12% y **la suma da en el blanco**.
- **Un mes marcado como rebalanceado aunque las órdenes fallen.** La
  descarga de histórico de MT5 es asíncrona y las primeras lecturas salen
  vacías; el EA lo interpretaba como «no hay mercados» y se saltaba el mes.
  La función de rebalanceo tiene que devolver si se ejecutó de verdad.
- **Sustituciones de código que no encuentran su ancla.** Tres veces un parche
  mío se aplicó a medias: quedaron usos de variables nunca declaradas y una
  función definida dos veces. Toda sustitución automática necesita un `assert`
  que falle en alto cuando el ancla no coincide.

**4. Trampas del lenguaje.** `final` es palabra reservada en MQL5 (heredada de
C++11) y `exp` es el nombre de una función (alias de `MathExp`). Las dos como
nombre de variable producen errores que no mencionan la causa.

**5. Trampas de estado persistente.** Las variables globales de MT5 son **del
terminal, no de la cuenta**. Al entrar en otra cuenta, un vigilante que
persista su pico de equity ahí calcula los suelos de una cuenta que ya no
existe, con números que parecen válidos. Todo estado persistente lleva el
identificador de la cuenta y se borra cuando cambia.

Y una variante peor: **`GlobalVariableTime()` no garantiza su base horaria.**
Comparar esa marca contra `TimeCurrent()` con ocho horas de diferencia entre
los dos relojes declaraba el dato caducado **siempre**, y el control de riesgo
más importante del sistema llevaba desactivado sin un solo síntoma más allá de
una línea de aviso que parecía informativa. La solución: que el emisor publique
`TimeCurrent()` **como valor**, y que los dos lados comparen en la misma base.

### El comprobador mecánico

Después del tercer parche a medias escribí `verificar_mql5.py`, que comprueba
cuatro cosas que el balance de llaves no ve:

1. balance de llaves, paréntesis y corchetes
2. **funciones definidas dos veces** (`already defined and has body`)
3. **identificadores usados y nunca declarados** (`undeclared identifier`)
4. declaraciones adelantadas sin definición

Y —esto es la parte que importa— **lo verifiqué contra un fichero con los dos
bugs metidos a propósito** antes de confiar en él. Un verificador sin verificar
no vale nada.

### El control positivo del código, no de la estrategia

La técnica que más bugs cazó: **reescribir la lógica del EA en Python y
correrla sobre los mismos datos.** No para validar la estrategia —eso ya está
hecho— sino para validar que el código hace lo que dice.

- La réplica del EA del FOMC sobre 117 eventos de M1: `+20,28 bp`, `t = 4,86`,
  compatible con la medición original. Y confirmó que la hora de entrada era
  15:57 NY en 117 de 117 casos.
- El control del empalme de señales: factor `1,0000` y error `0,00%` en los
  ocho mercados cuando referencia y «bróker» son la misma serie, más
  invariancia de escala de `0,00 bp` al multiplicar los precios por 10.
- Ese mismo control cazó un bug que el compilador no ve: una función que
  devolvía `20260900` en vez de `202609` porque multiplicaba por 10.000 y por
  100 a la vez. Ningún mes habría coincidido con la tabla y los ocho símbolos
  se habrían omitido en silencio.

---

## Fase 11 — El bróker y el instrumento son parte de la estrategia

Se puede validar un efecto con quince años de datos limpios y descubrir después
que **no se puede operar en el sitio donde tienes la cuenta**. Pasó dos veces.

### El instrumento no es el índice

`NACUSD.c` rueda contratos: su base estaba **+259,5 puntos** por encima del
índice de contado. Un backtest de quince años sobre el contado no describe ese
instrumento. Hay que medir el efecto **en el instrumento que vas a operar**, no
en su subyacente.

### El histórico del bróker es un límite duro

Medido en el terminal con `Bars()` y `SeriesInfoInteger()`:

```
los 8 símbolos:  desde 2026.01.12   ·   163-180 barras D1   ·   9 barras MN1
SERIES_SYNCHRONIZED = verdadero
```

Ocho meses. Incluido `EURUSD`, que tiene décadas en cualquier otro sitio. Y
sincronizado, así que **no es un problema de descarga: el servidor no lo
tiene.** Consecuencias:

- **No se puede hacer backtest de nada** en ese bróker más allá de siete meses.
- Una señal de 12 meses es **imposible** de calcular con datos locales.

Dos maneras de distinguir «histórico corto» de «histórico no descargado», que
tienen soluciones opuestas:

```
CopyClose(sim, tf, 0, N, arr)              pide por POSICIÓN: NO fuerza descarga
CopyClose(sim, tf, desde, hasta, arr)      pide por RANGO:    sí la fuerza
Bars() y SeriesInfoInteger(SERIES_FIRSTDATE)   dicen la verdad
```

### El empalme: traer los datos de fuera sin romper la escala

Acortar la señal a ocho meses habría sido ajustar la estrategia a una
limitación de datos. En su lugar se empalman dos series reescalando en el mes
de solape:

```
factor = cierre_broker[solape] / cierre_referencia[solape]
P[t]   = cierre_broker[t]              si el bróker lo tiene
P[t]   = cierre_referencia[t] × factor si no
señal  = signo( P[mes −1] / P[mes −13] − 1 )
```

Tres propiedades que lo hacen aceptable:

1. **Invariante de escala.** Solo se usan cocientes, así que da igual que la
   referencia sea un ETF que cotiza a un décimo del índice. Comprobado:
   multiplicar los precios por 10 cambia el retorno en `0,00 bp`.
2. **Se apaga solo.** Cuando el bróker acumule 14 barras mensuales, el empalme
   deja de usarse sin tocar nada. Cero mantenimiento recurrente.
3. **La barra parcial no contamina.** El mes en que empieza el histórico está
   incompleto, pero su *cierre* sigue siendo el cierre real de ese mes.

Rechacé la alternativa —un fichero externo actualizado a mano cada mes— porque
medí lo que cuesta olvidarlo: **una señal con un mes de retraso cuesta el 13%
del Sharpe**, y un paso manual mensual se olvida.

### Lo que se puede recortar sin coste, y hay que medirlo

La especificación pedía volatilidad de 252 días y solo había 163. Medido:

| | Vol 252 días | Vol 150 días |
|---|---|---|
| Vol de la pata | 3,85% | 3,82% |
| Sharpe | 0,53 | 0,54 |
| Peor día | −2,07% | −1,98% |

**Correlación entre las dos series de cartera: 0,9947.** El error típico en la
volatilidad individual es del 9%, pero se cancela al agregar ocho mercados.
Gratis. La lección no es «recortar da igual», es **mide antes de conceder**.

### La granularidad de lotes decide qué universo puedes operar

| Símbolo | Nocional por lote |
|---|---|
| NAS100 | 290.000 $ |
| GBP/USD | 135.000 $ |
| EUR/USD | 116.000 $ |
| USD/JPY | 100.000 $ |
| S&P 500 | 76.700 $ |
| Oro | 43.000 $ |
| Plata | 33.000 $ |

Con un paso de lote de 0,01 y una cuenta de 25.000 $, **el NASDAQ no cabe**: su
posición objetivo son 1.000 $ y el mínimo mueve 2.900 $. Entra a partir de una
equity de unos 36.000 $.

Dos decisiones de diseño que salen de esto:

- **Omitir el mercado, no usar el lote mínimo.** Forzarlo habría sobreexpuesto
  el oro 4,3 veces y la plata 5,3.
- **Dividir entre `max(mercados_activos, mercados_de_referencia)`.** Si un
  mercado se cae de la cesta, la exposición total **baja** en vez de subir.
  Repartir solo entre los que quedan concentra el riesgo justo cuando hay
  menos diversificación.

### Los filtros de ejecución hay que calibrarlos en unidades de equity

Puse un filtro de spread de 8 bp en una estrategia de rebalanceo mensual. El
error: **el spread se paga sobre el nocional de la posición, no sobre la
equity.**

| Mercado | Exposición | Spread | Coste en equity |
|---|---|---|---|
| Plata | 1,3% | 15 bp | **0,20 bp** |
| EUR/USD | 18,6% | 2,5 bp | 0,46 bp |

Pagar los siete spreads completos en la peor hora del día cuesta **2,48 bp de
la equity: 6,20 $**. Mi filtro rechazaba la plata para ahorrarse cincuenta
céntimos, y un mercado rechazado **se queda plano un mes entero** porque el
rebalanceo es mensual.

Y de paso: mis estimaciones de spread eran pesimistas por un factor de 2 a 5
en los siete mercados. Los reales, medidos en la columna `Sp` del terminal, van
de 0,26 bp en EUR/USD a 6,11 bp en la plata.

---

## Fase 12 — Las reglas de cobro SON la estrategia

Ésta es la fase que más me sorprendió. Diseñé una estrategia y luego la
enfrenté a las reglas de la firma, como si fueran dos problemas separados. No
lo son: **las reglas de cobro determinan qué estrategia tiene sentido.**

### Léelas, no las deduzcas

Dediqué un turno a inferir la fórmula del drawdown diario desde capturas del
panel. Acerté en la forma y fallé en dos detalles que su documentación decía de
forma explícita:

| | Lo que deduje | Lo que dice el documento |
|---|---|---|
| Base del límite diario | **MENOR** de saldo y equity | **MAYOR** de los dos |
| Momento del reinicio | 17:00 de Nueva York | **00:00 UTC** |

El primero es el peligroso: una base menor da un suelo menor, o sea **más
margen del que existe**. En su propio ejemplo —saldo 105.000, equity 102.000—
el suelo real es 99.750 y quedan 2.250; mi versión calculaba 97.920 y habría
anunciado 4.080. **Un 81% de margen inventado.**

Y las reglas **dependen del producto**: el 5% general pide 5 días mínimos, el
7% pide 6. Nada de lo que verifiques en un producto se traslada al otro.

### Verifica solo contra puntos donde las hipótesis divergen

Comprobé mi fórmula del límite diario contra el panel real y coincidió **al
céntimo**. La declaré verificada. Pero en ese instante el P/G flotante era
**cero**, así que saldo y equity eran el mismo número y `MENOR` y `MAYOR` daban
idéntico resultado. **Contrasté la hipótesis contra el único punto de datos
incapaz de distinguirla de su contraria.** El bug sobrevivió a su propia
verificación durante ocho turnos.

El contraste bueno costaba nada: dejar una posición abierta pasando el reinicio
diario. Con `saldo ≠ equity` las dos fórmulas se separan y la comparación
decide. Resultado cuando por fin se hizo:

```
base diaria 25.072,11 = MAYOR de saldo 24.999,15 y equity 25.072,11
suelo diario 24.069,23        (25.072,11 × 0,96, exacto)
con MENOR habría salido 23.999,18
```

### La regla de consistencia es la que ata, no el beneficio

De los caminos que no cobran en dos años, descomponiendo qué condición les
falta:

```
les faltan días cualificados  :  19,0%
les falta el beneficio mínimo :  50,3%
les bloquea el MEJOR DÍA (20%):  99,9%   ←  y el 48,4% SOLO por ella
```

Estado medio de un camino bloqueado: **10,09 días cualificados de los 6
necesarios**, beneficio **+247 $**, y un mejor día de **333 $** que le obliga a
acumular **1.666 $** antes de poder retirar nada.

Y ese mejor día tiene nombre. Con un riesgo del 1,35% y un stop de 80 bp el
apalancamiento es ×1,688, así que el take profit vale `80 × 1,688 = 1,35%` de
la equity = **337,50 $** sobre una cuenta de 25.000. Contra los 333 $ medidos.
**El mejor día ES el take profit de la estrategia de eventos.**

De ahí sale la consecuencia que no habría adivinado: **el take profit es una
palanca sobre la probabilidad de cobro, no solo sobre el retorno.** Barriéndolo
con el stop fijo, sobre M1 reales:

| TP | Media | Mejor día | Listón 20% | P(cobro) | 1er cobro |
|---|---|---|---|---|---|
| 40 bp | +15,7 bp | 308 $ | 1.538 $ | 74,5% | 196 d |
| 50 bp | +15,4 bp | 319 $ | 1.593 $ | 71,8% | 212 d |
| 80 bp | +19,4 bp | 391 $ | 1.956 $ | 67,7% | 241 d |
| sin TP | +19,5 bp | 543 $ | 2.714 $ | **47,7%** | 282 d |

Un take profit corto **cuesta ventaja** (19,4 → 15,4 bp) y aun así **compra
probabilidad de cobro**, porque baja el listón más de lo que recorta el retorno.
Sin take profit tendrías que acumular el 10,9% de la cuenta antes de retirar un
céntimo.

**Y hay que medirlo sobre datos intradía.** Un take profit se toca dentro del
día; truncar el retorno de cierre solo ve los eventos que *cierran* por encima
del TP y subestima muchísimo su efecto. Ése fue el error de la primera
elección de ±80 simétrico.

### La regla del día cualificado castiga a las estrategias tranquilas

«Cada día debe cerrar con al menos +0,5%» suena inocuo. A una volatilidad de
cartera del 4,5%, un día de +0,5% es un movimiento de **1,7 sigmas**:

| Vol de cartera | Días que llegan al +0,5% | Al año | 6 días en |
|---|---|---|---|
| 4,5% | 3,37% | 8,5 | **8,5 meses** |
| 6,0% | 6,04% | 15,2 | 4,7 meses |
| 7,0% | 8,22% | 20,7 | 3,5 meses |

**La regla no pide que ganes: pide que ganes a golpes.** Y eso crea un óptimo
de volatilidad que no existiría sin ella:

| Vol | P(cobro) | P(quema) | EV anual |
|---|---|---|---|
| 3,5% | 60,8% | 0,0% | 503 $ |
| **4,5%** | **63,8%** ← máximo | 0,5% | 680 $ |
| 5,5% | 63,0% | 3,1% | 811 $ |
| 7,5% | 59,6% | 17,0% | 1.003 $ |

Dos fuerzas cruzándose: con menos volatilidad no juntas los días, con más
quemas la cuenta antes de cobrar. **El EV sigue subiendo con la volatilidad
pero la probabilidad de cobrar tiene un máximo interior.** Cuál de los dos
maximizas es una decisión, no un cálculo.

### El umbral de beneficio propio no sirve para nada

Barriendo el umbral con el que pedir el cobro: **250, 500 y 1.000 $ dan
resultados idénticos** (P(cobro) 63,8%, EV 680 $). No es casualidad: las
restricciones que atan son los días cualificados y la regla del mejor día, y
cuando por fin se cumplen ya hay muy por encima del umbral.

**No eliges cuándo cobrar. Lo elige la regla de consistencia.** Y esperar
destruye valor rápido: con umbral de 3.000 $ la mediana del resultado pasa a
ser negativa, y no retirar nunca da un EV de **−25 $/año**.

El argumento de fondo es estructural: con el suelo bloqueado en el saldo
inicial, **todo el beneficio no retirado es perdible**. Puedes caer de 27.000 a
25.000 sin romper ninguna regla, y has perdido los 2.000. Y cada máximo
intradía que toques sube el suelo del trailing de forma permanente: en el
primer día real de operativa, un pico no realizado de 25.163,24 subió el suelo
151,81 $ para siempre.

### «Nunca» no es «en dos años»

Cuando la cuenta no tiene límite de tiempo, la probabilidad de no cobrar cae
sola:

| Horizonte | P(cobra) | P(quema) | P(ninguna) |
|---|---|---|---|
| 1 año | 33,7% | 0,0% | 66,3% |
| 2 años | 64,1% | 0,6% | 35,4% |
| 4 años | 84,2% | 2,9% | 13,9% |
| 6 años | **91,7%** | 5,6% | 5,8% |

Y el contador de días cualificados **no se reinicia con el tiempo**, solo
después de un cobro. Por eso un camino bloqueado sigue acumulando. De los que
no cobran a los dos años, el **59,6% está en beneficio**: no cobrar no es
perder.

### Costes que no estaban en el modelo

Mi contabilidad tenía dos partidas —coste de intervención del vigilante y giro
del rebalanceo— y **el carry de mantener una cesta multi-activo un mes entero
no estaba en ninguna**. Sobre 69% de exposición bruta, mi estimación pata por
pata daba −0,62 $/día ≈ −156 $/año ≈ **el 21% de la expectativa bruta**.

Y hay una distinción de un factor treinta que hay que resolver
empíricamente: una deducción de 6,07 $ es **comisión** (una vez por
rebalanceo, ~73 $/año) o **swap** (cada noche, ~2.216 $/año, que se comería la
estrategia entera). Se despeja así:

```
swap acumulado = (equity − saldo) − suma de la columna Profit
```

y se distingue observando si crece **después de un rollover con el mercado
abierto**. Fallé tres veces en fijar ese momento, siempre por el mismo motivo:
mezclar hora local con hora de servidor. El rollover es a las 00:00 del
servidor, y el viernes cae después del cierre del mercado, así que el
contraste válido es el lunes.

---

## Fase 13 — Puesta en marcha: predecir antes de mirar

La disciplina que hizo útiles los primeros días en vivo fue una sola:
**escribir qué debe decir el log antes de leerlo.** Una predicción escrita
convierte cada arranque en un experimento; sin ella, cada log es una
confirmación de lo que ya creías.

### Cómo se hace

Antes de cada ejecución, calcular en Python lo que el EA debe imprimir y
publicarlo. Ejemplos reales y su resultado:

| Predicción | Resultado |
|---|---|
| Señales y volatilidades de los 8 mercados | **7 de 8 correctas**. `EUR/USD` falló: su retorno de 12 meses era −0,8% y el factor de empalme del 1% le cambió el signo |
| Qué mercados no llegan al lote mínimo | **fallé**: predije oro y plata, cayó el NASDAQ |
| Suelo diario tras el reinicio | **acertó**: 24.069,23 contra mi 24.064 con la equity de una hora antes |
| Lotes de las 7 posiciones | **exactos**: 0,02 / 0,02 / 0,01 / 0,04 / 0,03 / 0,03 / 0,04 |
| Exposición bruta agregada | 69,39% real contra 69,58% objetivo |

Que la predicción de los lotes fallara y el EA acertara fue lo más valioso del
proceso: confirmó que derivar del `tick value` era correcto y que mi modelo
mental de los contratos no lo era.

### El EA no puede necesitar que estés delante

El primer arranque del rebalanceo mensual disparaba a cualquier hora, porque el
contador de «último mes rebalanceado» valía cero. Eso significaba abrir siete
posiciones a las tres de la madrugada de Nueva York, con los spreads
ensanchados, y obligaba a que un humano estuviera presente a una hora concreta.

La corrección distingue dos situaciones que no son la misma:

- **primeros días del mes, fuera de la ventana** → esperar al próximo día de
  mercado en horario líquido
- **ya tarde en el mes** → operar a la hora que sea, porque perder el mes es
  peor que pagar un spread ancho

Resultado en vivo: disparó a las **10:00:00 de Nueva York**, siete órdenes en
1,7 segundos, sin fallos, mientras el operador estaba en el trabajo.

### El modelo y la implementación no coinciden, y hay que medir la brecha

El vigilante publica un factor de tamaño que los demás EAs aplican. Mis
simulaciones lo aplicaban **a los retornos de cada día**; el sistema real lo
aplica **al abrir**, y las posiciones mantienen su tamaño hasta el siguiente
rebalanceo mensual. Medido:

| Variante | P(quema) |
|---|---|
| Factor diario (lo que simulé) | 0,6% |
| **Factor mensual (el sistema real)** | **1,1%** |
| Sin factor | 14,6% |

Mi error era real —casi el doble— pero cae donde no importa: **el factor
mensual conserva el 96% de la protección** que prometía el diario. La razón:
un drawdown lo bastante profundo para importar tarda semanas en formarse, y el
rebalanceo mensual llega a tiempo.

Y redimensionar entre rebalanceos **no merece la pena**: compra 0,3 puntos de
ruina a cambio de EV y de un punto de probabilidad de cobro, y añade código
nuevo a un sistema que ya funciona.

La lección general: **toda diferencia entre lo que simulaste y lo que el código
hace es una hipótesis con signo desconocido.** Hay que medirla, no razonarla.

### La arquitectura de tres piezas

| EA | Qué hace | Qué NO hace |
|---|---|---|
| Estrategia de eventos | abre y cierra su posición, con stop y TP en el servidor | no sabe nada de la cuenta |
| Estrategia continua | rebalancea una vez al mes | no lleva stops, por diseño |
| Vigilante | no opera; publica el factor de tamaño y cierra ante averías | no gestiona drawdown cerrando |

Se comunican por variables globales del terminal, con dos reglas:

1. **el emisor publica un latido con `TimeCurrent()` como valor**, para que la
   frescura se mida en la misma base horaria
2. **el consumidor falla hacia el tamaño pleno si no hay dato fresco**, no
   hacia cero — porque en el Probador solo corre un EA y el backtest tiene que
   funcionar

Y la separación conceptual que importa: **drawdown y avería no son lo mismo.**
El drawdown es el funcionamiento normal de algo con varianza y se gestiona con
tamaño. Una avería —un EA abriendo en bucle, un stop que no llegó al
servidor— es algo roto: ahí sí hay que cerrar y bloquear hasta que un humano
lo mire.

### Qué NO hacer una vez está corriendo

No cerrar posiciones a mano, y la razón menos obvia es la que más pesa: **la
regla de consistencia mira el mejor día.** La estrategia continua, tal como
está, casi no realiza beneficio ningún día —el umbral del 20% mantiene las
posiciones y no se cierra nada—, y eso es una ventaja estructural. Cerrar un
ganador a mano concentra beneficio realizado en un día y **te sube el listón
del 20% tú mismo**.

Las tres excepciones en que sí hay que intervenir: el vigilante no está
corriendo y la equity se acerca al suelo; un EA hace algo que no debería; o el
panel de la firma y el vigilante discrepan en el margen disponible —y ahí manda
el panel.

### El vehículo: dónde poner la estrategia

Con la misma estrategia, dos vehículos y dos economías distintas:

| | Cuenta prop | Track record auditado (D-Zero) |
|---|---|---|
| Coste año 1 | 50 $ una vez | ~636 $/año |
| EV año 1 | ~680 $ | 0 $ sin asignación |
| AUM de equilibrio | — | **46.893 $** |
| Compone | **no**, se reinicia en cada cobro | sí, el AUM crece |
| Techo | ~680 $/año por cuenta | ~12.900 $/año con 1 M€ |

Y una aritmética que se aplica a los dos y que conviene tener presente antes de
elegir: con un Sharpe neto de **0,66**, alcanzar `t = 2` requiere **11,2 años**.
A los dos años el `t` esperado es 0,85. **Ningún historial en vivo de duración
razonable va a confirmar esta estrategia.** Lo que un historial sí hace es
refutar —un resultado muy malo es informativo aunque uno bueno no sea
concluyente— y verificar ejecución, que se ve en semanas.

> **Corrección posterior.** La fila «EV año 1 ~680 $» de esta tabla es falsa.
> Se calculó con un modelo de cobros que suponía retirada íntegra y reinicio de
> cuenta. Con las reglas reales el EV es **168 $/año**. La comparación de
> vehículos cambia de signo y está rehecha en la Fase 14.

---

## Fase 14 — El EV no lo fija la estrategia, lo fija la mecánica del cobro

La Fase 12 concluyó que las reglas de cobro son parte de la estrategia. Se
quedó corta. Al leer la documentación de la firma sobre *payout structure*
aparecieron cuatro supuestos míos, **los cuatro optimistas**:

| | Lo que supuse | Lo que dicen las reglas |
|---|---|---|
| Importe del cobro | todo el beneficio | **tope escalonado**: 250, 500, 750, 1.000, 1.250, 1.560, 1.875 y libre desde el 8º |
| Estado tras cobrar | saldo, pico y suelo al inicial | **no se reinicia**; solo baja lo retirado |
| Beneficio sobre el tope | se cobra en el siguiente segmento | **atrapado** — pero ver el aviso de abajo |
| Comisiones de proceso | ninguna | 19,9 $ + 2,49% |

> **Aviso: la tercera fila es un SUPUESTO, no un hallazgo.** La escribí como
> hecho verificado y no lo es: es mi lectura de una frase, y el texto fuente no
> quedó guardado. Todo el resultado de esta fase cuelga de una línea de código,
> `ref_seg = bal` contra `ref_seg = CUENTA`. Las dos lecturas son defendibles:
>
> - **A** — el saldo tras retirar pasa a ser la nueva base, así que lo que quedó
>   por encima del tope deja de ser beneficio. No sale nunca.
> - **B** — el tope limita el *ritmo*, no el total. Lo no cobrado sigue en cola.
>
> Medidas las dos: **B paga 1,81× más a 4 años y 0,75× a 15**, porque retirar el
> colchón multiplica por 3,8 la probabilidad de quemar la cuenta. Y en las dos
> lecturas queda dinero dentro que no sale: entre cuentas vivas, la cola de B es
> de 968 $ a 4 años y 473 $ a 15. **No se drena nunca.**
>
> Se resuelve gratis en el segundo cobro: si el panel te ofrece ~0, es la lectura
> A; si te ofrece el tope del tramo 2 sin haber generado nada nuevo, es la B.
> Hay dos supuestos más sin verificar: que al 7º cobro el atrapado se borre, y
> que no exista vía de retirada extraordinaria.

Efecto sobre el mismo sistema, sin cambiar una línea del EA:

| horizonte | EV viejo | EV real | atrapado | P(quema) |
|---|---|---|---|---|
| 2 años | 779 $/año | **168 $/año** | 1.400 $ | 1,8% |
| 3 años | 794 $/año | **232 $/año** | 2.012 $ | 3,4% |
| 5 años | 779 $/año | **335 $/año** | 2.984 $ | 5,9% |

**Un factor 4,6 de error, y no venía de la estrategia.** La serie de retornos
es idéntica en las dos columnas.

> **Y estas cifras también quedaron obsoletas, dos veces.** Se calcularon con la
> serie de 8 mercados cuando el EA solo opera 7, con un objetivo de volatilidad
> teórico en vez del riesgo real del gráfico, y **con carry cero**. Los números
> vivos están en la Fase 15; el orden de magnitud del error acumulado es de 4×
> a la baja. La lección no es aritmética: **cada vez que un modelo se cae, hay
> que auditar las decisiones que se tomaron optimizando contra él**, no solo
> recalcular su salida.

### La pinza: dos reglas que por separado son inocuas

Lo interesante no es que el tope sea bajo. Es que el tope y la regla del mejor
día **se multiplican**:

- la regla del mejor día exige que el día mayor sea ≤20% del beneficio del
  ciclo, lo que **obliga a acumular** un segmento de ~5,2 veces el día mayor
  antes de poder pedir nada;
- el tope del primer tramo solo libera `250 / 0,90` = **277,8 $** de saldo;
- la diferencia queda atrapada, y no se recupera nunca.

| TP | día mayor | segmento al pedir | × día mayor | liberado | atrapado | % liberado |
|---|---|---|---|---|---|---|
| 30 bp | 239 $ | 1.388 $ | 5,2 | 278 $ | 1.110 $ | 20% |
| 40 bp | 260 $ | 1.447 $ | 5,2 | 278 $ | 1.169 $ | 19% |
| 50 bp | 287 $ | 1.548 $ | 5,2 | 278 $ | 1.270 $ | 18% |
| 80 bp | 367 $ | 1.985 $ | 5,1 | 278 $ | 1.707 $ | 14% |

El multiplicador 5,2 es **una constante de las reglas**, no de la estrategia:
sale igual con cualquier TP y con cualquier peso. Y como el día mayor escala
con el take profit, **el dinero atrapado escala con el take profit**. Eso da un
argumento estructural para bajarlo que no depende del argmax de ninguna curva.

### La hipótesis que parecía obvia y era falsa

Si la pinza premia el P&L suave, subir el peso de la pata lenta debería liberar
más dinero. Se midió, con la esperanza de haber encontrado el dial de primer
orden:

| w2 | P(cobro) | EV anual | atrapado | **% liberado** |
|---|---|---|---|---|
| 30% | 74,3% | 194 $ | 1.403 $ | **19%** |
| 45% | 67,4% | 165 $ | 1.172 $ | **20%** |
| 60% | 62,3% | 134 $ | 1.046 $ | **19%** |
| 75% | 59,1% | 116 $ | 977 $ | **19%** |

**El `% liberado` no se mueve.** Suavizar el P&L reduce a la vez el numerador y
el denominador del cociente del mejor día, y la pinza es invariante. Lo único
que consigue subir `w2` es cambiar retorno por nada. `w2` = 30% y vol = 4,5%
**sobreviven** a la reoptimización; de los tres diales, solo el take profit se
mueve.

Lección: cuando un modelo se cae, no basta con recalcular el resultado. Hay que
volver a preguntarse **qué decisiones se tomaron optimizando contra él.** Aquí
eran tres. Dos aguantaron y una no, y no se sabía cuál sin medirlas.

### Un `t` de 79,74 que no valía nada

Con las reglas reales, 40 bp adelanta a 50 bp (198 $ contra 167 $). Pero yo ya
había rechazado 40 bp una vez por ser **el argmax de una curva de 117 eventos**,
así que la pregunta era si esta vez la diferencia era real.

Primer test: números aleatorios comunes sobre los caminos simulados. Salió
`t` = **79,74**, error típico de 0 $, signo positivo en 8 de 8 semillas.

**Ese número es basura y por poco lo presento como prueba.** Mide el ruido
Monte Carlo de los caminos, condicionando en los 117 eventos exactos que
ocurrieron. Tiende a cero **por construcción** al subir el número de caminos:
lo único que demuestra es que la simulación converge. No dice absolutamente
nada sobre si 40 bp ganará en los próximos eventos, que es error de **muestreo
de los eventos** —o sea, la objeción original, intacta.

Test correcto: remuestrear con reemplazo los 117 **eventos**, recalcular la
serie para cada TP y contar en cuántos mundos gana cada uno.

| TP | EV medio | desv. típica | p5 | p95 | argmax en |
|---|---|---|---|---|---|
| 30 bp | 189 $ | 26 $ | 142 $ | 233 $ | 8% |
| **40 bp** | **201 $** | 29 $ | 145 $ | 243 $ | **92%** |
| 50 bp | 171 $ | 29 $ | 123 $ | 212 $ | 0% |
| 60 bp | 153 $ | 28 $ | 105 $ | 190 $ | 0% |

La desviación típica real es de 29 $, no de 0 $ —siete veces mayor que la que
daba el test malo—. Y aun así **40 bp gana a 50 bp en el 100% de los mundos**
(`t` = 12,24 emparejado). La objeción del argmax queda contestada: no porque
el ruido sea pequeño, sino porque la nueva función objetivo **discrimina mucho
más** que la anterior. El take profit ya no entra solo por el retorno medio;
entra por el tamaño del día mayor, que es lo que gobierna la pinza.

Límite de este test, que hay que decir: remuestrea eventos de forma
independiente, así que acota el **error de muestreo** y no el **cambio de
régimen**. Si la prima del FOMC se degrada, este intervalo no lo ve.

### El colchón: la conclusión buena con la prueba mala

Observé que el beneficio atrapado no es retirable pero sigue en la equity, y lo
«demostré» comparando `P(quema | hubo cobro)` = 2,9% contra
`P(quema | no hubo cobro)` = 38,3%.

**Esa comparación no mide ningún colchón: condiciona sobre el resultado.** Casi
todas las cuentas sin cobro son cuentas que se quemaron *antes* de poder
pedirlo. Es causalidad invertida, y la brecha de 35 puntos es selección pura.

El test es contrafactual, mismos caminos y misma semilla, cambiando solo si el
atrapado se queda en el saldo o se barre:

| horizonte | atrapado se queda | atrapado se barre | valor del colchón |
|---|---|---|---|
| 2 años | P(quema) 1,8% · EV 166 $ | P(quema) 34,2% · EV 79 $ | **+32,4 pp · +87 $/año** |
| 5 años | P(quema) 5,8% · EV 336 $ | P(quema) 71,3% · EV 83 $ | **+65,5 pp · +253 $/año** |

La conclusión sobrevive y el efecto es enorme. Pero llegó por la razón
equivocada, y la coincidencia numérica entre el estadístico malo (2,9/38,3) y
el bueno (1,8/34,2) es **pura suerte**. Si el mecanismo hubiera sido más débil,
el número contaminado por selección lo habría tapado igual de bien.

### Lo que hay que sacar de esta fase

1. **El EV de una cuenta prop no lo fija la estrategia.** Lo fija la mecánica
   del cobro. Aquí la estrategia aportó el 100% de la serie y el 22% del EV.
2. **Busca la interacción entre reglas, no las reglas sueltas.** El tope es
   inocuo. El mejor día es inocuo. Juntos confiscan el 81%.
3. **Cuando cae un modelo, audita las decisiones que dependían de él**, no solo
   sus resultados.
4. **Un error típico de cero es una alarma, no un logro.** Casi siempre
   significa que estás midiendo la convergencia de tu simulación en vez de la
   incertidumbre de tu conclusión.
5. **Condicionar sobre el resultado no es un test.** Si los grupos que comparas
   se definen por lo que pasó, la respuesta ya estaba dentro de la pregunta.

---

## Fase 15 — El coste de mantener la posición decide antes que la estrategia

Las Fases 11 y 12 dicen que el bróker y las reglas de cobro son parte de la
estrategia. Se quedaron cortas. Existe un tercer factor que domina a los dos y
que no medí nunca: **lo que cuesta tener la posición abierta.**

Contexto: el sistema llevaba seis días en una cuenta real de 25.000 $ cuando
apareció, y todas las cifras de EV de las Fases 12 a 14 se habían calculado con
**carry cero**.

### El descubrimiento, y cómo se decodifica

El síntoma fue una deducción que no cuadraba: la suma de la columna `Profit`
daba −189,47 y el pie de la lista −213,83. La diferencia, **−24,36**, no estaba
en ninguna columna visible.

La prueba que lo identifica es de dos observaciones separadas en el tiempo:

```
deduccion el dia de apertura, antes de cualquier rollover :  -6,07
deduccion seis dias despues                              : -24,36
```

Una comisión de apertura es **fija**. Si el número crece, **acumula: es swap**.
Y la comisión resultó ser calderilla: 5 USD por lote sobre 0,19 lotes = 0,95 $.

### Contar las noches bien, que es donde me equivoqué

Conté 4 rollovers cuando eran **6 unidades de swap**, porque la
especificación del símbolo dice `Wednesday 3`: el rollover del miércoles cobra
**triple** para cubrir el fin de semana. Un año tiene ~364 unidades, no 252 ni
365 noches simples.

```
mal  (4 noches)  -> 6,28 $/unidad -> 2.292 $/año -> 9,17% de la cuenta
bien (6 unidades)-> 4,19 $/unidad -> 1.524 $/año -> 6,10% de la cuenta
```

Me pasé un 50%. **Si has copiado el −2.292 a algún sitio, corrígelo a −1.524, y
el ratio de 2,6× a 1,74×.**

### El desglose, que señala a un solo símbolo

| símbolo | % cuenta | $/año | **% anual del nocional** | % del carry |
|---|---|---|---|---|
| **XAGUSD** | 13,3% | **993 $** | **30,0%** | **65%** |
| XAUUSD | 35,0% | 283 $ | 3,2% | 19% |
| SPCUSD.c | 6,1% | 98 $ | 6,4% | 6% |
| EURUSD | 18,6% | 84 $ | 1,8% | 5% |
| GBPUSD · AUDUSD · USDJPY | 40% | 66 $ | ~1% | 5% |

**La plata cuesta diez veces más que el oro por unidad de nocional.** El 65% del
problema con el 13% de la cuenta. Y el atenuante: el swap en corto puede ser
**positivo** (EURUSD paga −8,26 largo y **+1,05** corto), así que una estrategia
que va en las dos direcciones paga menos de la mitad.

### La descomposición que decide el diseño

El carry no afecta igual a todas las patas. Lo que importa es **cuántas noches
se aguanta**, no cuánto riesgo se toma:

| pata | noches/año | retorno bruto | carry | **neto** |
|---|---|---|---|---|
| evento pre-FOMC (17 h × 8) | 8 | +487 $ | −63 $ | **+424 $** |
| trend multi-activo (continuo) | 364 | +387 $ | −1.461 $ | **−1.074 $** |

**La pata con menos retorno bruto era la única viable.** Y la que parecía
diversificar destruía la cuenta.

Medido sobre el pipeline completo de cobros, a 4 años:

| configuración | carry/año | neto/año | recibido | P(cobra) | **P(quema)** |
|---|---|---|---|---|---|
| con plata | −1.524 $ | **−810 $** | 18 $ | 6,9% | **77,3%** |
| sin plata | −531 $ | +156 $ | 233 $ | 50,0% | 7,0% |
| **solo el evento** | **−50 $** | **+337 $** | **509 $** | **89,5%** | **0,0%** |

### Regla: el nocional se despeja del P&L, nunca se apunta

Tenía el oro con contrato de 10 onzas y la plata con 500. Son **100 y 5.000**.
Los dos 10× pequeños, el mismo error propagado, y me llevó dos días de análisis
construidos sobre exposiciones falsas: **112,8% de exposición bruta real contra
el 69,3% que tenía anotado.**

```
unidades por lote = P&L / (lotes x delta_precio)
```

Es la única cifra que no admite discusión, porque sale del dinero. La columna
`Value` del terminal la confirma. **No te fíes de tu propia nota del tick value.**

Consecuencia directa: el oro pasó de ser la posición **más segura** de la cartera
—necesitaba un 56% de caída para romper el límite por operación— a necesitar un
**5,7%**. La misma tabla de riesgo, con el nocional bueno, se invierte.

### La tercera regla de muerte

Las Fases 9 y 12 modelan dos formas de morir: el trailing y el diario. Hay una
tercera, y es de tipo *hard breach*: **pérdida máxima por operación**. En el
producto medido son el 2% de la cuenta, y cierra la cuenta al instante aunque
esté en beneficio.

```
configuracion en vivo (TP 80 bp, riesgo 1,35%) -> 2,26%  ROMPE
con TP 40 bp y riesgo 0,96%                    -> 1,61%  ok, 20% de margen
```

Había un evento histórico real que habría cerrado la cuenta. Y no se puede
vigilar, **solo dimensionar**: en un hueco el precio atraviesa el stop y el
umbral del guardián en el mismo tick.

El guardián sí protege la pata lenta, donde la pérdida se acumula en semanas.
Bajar su umbral de 3,0% a 1,5% fue, sin saberlo, el cambio más valioso de la
semana: con 3,0% habría cortado en 750 $, o sea **después** del breach de 500 $.

### El acantilado del día cualificado

Con una sola pata, el riesgo deja de ser un ajuste fino. Un acierto rinde
`TP/stop × riesgo`, y la firma exige días con **≥ +0,5%**:

| riesgo | rinde un TP | ¿cualifica? | peor caso vs 2% | recibido 4 años |
|---|---|---|---|---|
| 0,96% | 0,480% | **NO** | 1,61% ok | **75 $** |
| 1,00% | 0,500% | sí | 1,67% ok | 467 $ |
| **1,10%** | **0,550%** | **sí** | **1,84% ok** | **~515 $** |
| 1,30% | 0,650% | sí | **2,17% ROMPE** | 543 $ |

**Dos puntos básicos valen 435 $ de los 510.** Por debajo del umbral la cuenta
gana dinero y no puede cobrarlo nunca. La ventana útil es **1,00%–1,20%**:
el mínimo lo fija la regla del día cualificado y el máximo el límite por
operación. Con dos patas esto no se veía, porque el ruido diario de la segunda
empujaba algunos días por encima del umbral.

### La semana de demo, que ahora es obligatoria

Este es el fallo de método, y es de categoría: **validé la estrategia contra 15
años de datos y no validé nunca el entorno de ejecución.**

| | ¿lo caza una demo? |
|---|---|
| swap por símbolo y por dirección | **sí** |
| nocional real por lote | **sí** |
| spread y comisión reales | **sí** |
| granularidad de lote (símbolos que no entran) | **sí** |
| calidad de relleno en huecos | no — rellenan demasiado bien |
| reglas de la firma (límite por operación, topes) | no — es contabilidad de la firma |

**Los dos errores más grandes del proyecto los habría cazado una demo de siete
días, gratis.** Cinco números, una semana, y habrían cambiado la arquitectura
antes de arriesgar la cuenta.

### Cierre del caso NASDAQ, con los datos que faltaban

Un sistema de ruptura de canal M5 quedó cerrado «por falta de histórico».
Medido sobre **8.430 operaciones y 15 años**, con la fricción completa
`2 × (spread + comisión) / stop = 0,0274R`:

| objetivo | aciertos | exp. R | t |
|---|---|---|---|
| 1,0R | 49,5% | **−0,0368R** | **−3,38** |
| 1,5R a 5,0R | 40,5% a 24,7% | −0,020R a −0,030R | −1,25 a −1,91 |

Y la descomposición es la que cierra el asunto:

```
expectativa BRUTA   -0,0094R   t = -0,86   indistinguible de cero
friccion             0,0274R
expectativa NETA    -0,0368R   t = -3,38
```

**La señal es una moneda al aire; la fricción es la pérdida entera.** Ninguna
gestión arregla eso. `DD/vol = 13,95` contra el objetivo de diseño `< 1,1`, y el
acierto cruza el equilibrio en **6 de 15 años**, alternando sin persistencia.

Comparado con lo que sí tiene ventaja, en la misma unidad:

| | ruptura M5 | evento pre-FOMC |
|---|---|---|
| ventaja bruta | −0,009R | **+0,254R** |
| fricción | 0,027R | 0,034R |
| 2 × error típico | 0,022R | 0,104R |
| **tamaño defendible** | **0** | **+0,115R** |

Misma fricción. Uno tiene de dónde pagarla y el otro no.

### Lo que hay que sacar de esta fase

1. **Mide el carry antes de diseñar la cartera, no después.** Es lo primero que
   hay que saber de un instrumento, antes del spread y antes de la señal.
2. **Un mercado puede ser inoperable solo por su financiación.** La plata a 30%
   anual sobre nocional no la salva ninguna señal.
3. **El carry escala con las noches, no con el riesgo.** Una estrategia de
   evento con 8 noches al año es inmune; una tendencial continua no.
4. **Despeja el nocional del dinero, no de tus notas.**
5. **Cuenta las unidades de swap, no las noches.** El miércoles vale tres.
6. **Una semana de demo en el mismo bróker antes de cualquier cuenta real.**
7. Y la de siempre, otra vez: **cuando un modelo se cae, audita las decisiones
   que dependían de él.** Aquí eran tres, y una era el peso de una pata entera.

---

## Resumen del caso THL

| Componente | Veredicto | Evidencia |
|---|---|---|
| Condición de entrada | **Identificada** | `t` = 34,7 / −37,0 |
| Timeframe de evaluación | **Identificado**: velas M5 | 92% en múltiplos de 5, 95% seg=00 |
| Entrada replicada | Sin retorno | `t` = 0,52 (15 años) / −0,19 (bróker) |
| Selección dentro de la regla | Dirección correcta, sin significancia | +2,1 a +4,0 bp, `t` = 1,5-1,7 |
| Momento de salida | **Sin habilidad** | pierde contra hold fijo, `t` = −0,23 |
| Preferencia por volatilidad | **No lleva retorno** | opera en el peor quintil |
| Track record propio | **No significativo** | Sharpe 0,491 ± 0,492 |

Auditoría completa. Disparador leído con precisión. Y nada de lo que hace,
replicado, produce retorno demostrable.

Ese es un resultado válido y es la conclusión más probable de cualquier auditoría
honesta. El protocolo sirve para llegar a ella en una tarde en vez de en cinco
sesiones.
