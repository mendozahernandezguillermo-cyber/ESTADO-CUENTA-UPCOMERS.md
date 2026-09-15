# Correcciones y añadidos al PROTOCOLO 2.1

Salen de medir en una cuenta real de 25.000 $ durante su primera semana de vida,
y de cerrar con datos el caso que la Fase 12.11 dejó abierto. Cada punto lleva
el número que hay que cambiar y por qué.

---

## 1. Fase 12.2 — el número del carry está inflado un 50%

**Dice:** «el carry fue −2.292 al año contra +387 de retorno bruto: 2,6 veces
todo lo que la estrategia ganaba. La plata sola era el 65% del carry con el 13%
de la cuenta —45% anual sobre su nocional— frente al 4,9% del oro y el 2,7% de
EUR/USD.»

**Ese −2.292 es mío y está mal.** Conté 4 noches simples cuando eran **6
unidades de swap**: la especificación del símbolo dice `Wednesday 3`, o sea que
el rollover del miércoles cobra **triple** para cubrir el fin de semana. Un año
tiene ~364 unidades.

| | mal (4 noches) | **bien (6 unidades)** |
|---|---|---|
| por unidad | 6,28 $ | **4,19 $** |
| al año | 2.292 $ | **1.524 $** |
| % de la cuenta | 9,17% | **6,10%** |
| veces el retorno bruto | 2,6× | **1,74×** |

Y las tasas por nocional, corregidas:

| símbolo | dice | **es** |
|---|---|---|
| plata | 45% | **30,0%** |
| oro | 4,9% | **3,2%** |
| EUR/USD | 2,7% | **1,8%** |
| NASDAQ (SPCUSD.c) | — | 6,4% |

La conclusión no cambia —el carry seguía siendo mayor que todo el retorno— pero
el número sí. **Regla que se deriva: se cuentan unidades de swap, no noches.**

---

## 2. Fase 10 — trampa nueva: el nocional se despeja del P&L, nunca se apunta

Tenía anotado el oro con contrato de **10 onzas** y la plata con **500**. Son
**100 y 5.000**. Los dos 10× pequeños, el mismo error propagado desde una única
lectura mal hecha del tick value.

Coste: dos días de análisis de riesgo construidos sobre exposiciones falsas.

```
exposicion bruta que tenia anotada : 69,3%
exposicion bruta REAL              : 112,8%
```

La cifra que no admite discusión sale del dinero:

```
unidades por lote = P&L / (lotes x delta_precio)
```

La columna `Value` del terminal la confirma. **Y el efecto no es cosmético:**
con el nocional bueno, el oro pasó de ser la posición más segura de la cartera
—necesitaba un 56% de caída para romper el límite por operación— a necesitar un
**5,7%**. La tabla de riesgo se invierte entera.

---

## 3. Fase 12.11 — se puede cerrar con datos, ya no «por falta de ellos»

**Dice:** «Estado: cerrado, y no por falta de ideas sino por falta de datos.
Reabrir exige histórico multianual real.»

Ese histórico existe: **M1 de NASDAQ de sep-2011 a ago-2026, 5,7 M de barras**,
ajeno a las 1.626 combinaciones que corrieron sobre 2026 — o sea holdout limpio
de verdad. Replicando la señal exacta del `.mq5` (canal 48 M5, ruptura de cierre,
máx. 2/día) con la fricción completa de la 12.2 (`2 × 1,37 / 100 = 0,0274R`):

| objetivo | n | aciertos | exp. R | t |
|---|---|---|---|---|
| **1,0R** | 8.430 | 49,5% | **−0,0368R** | **−3,38** |
| 1,5R | 8.430 | 40,5% | −0,0198R | −1,49 |
| 2,0R | 8.430 | 34,0% | −0,0289R | −1,91 |
| 3,0R | 8.430 | 28,0% | −0,0302R | −1,68 |
| 5,0R | 8.430 | 24,7% | −0,0260R | −1,25 |

**Hipótesis 6 —«era la muestra»— descartada.** Y la descomposición es lo que de
verdad cierra el caso:

```
expectativa BRUTA   -0,0094R   t = -0,86   <- indistinguible de cero
friccion             0,0274R
expectativa NETA    -0,0368R   t = -3,38
```

**La señal es una moneda al aire y la fricción es la pérdida entera.** Es
exactamente el diagnóstico que la propia 12.2 escribió para esta escala, ahora
confirmado sobre 8.430 operaciones por un camino independiente.

Los otros tres tests del documento, aplicados:

- **Fase 12.10** (acierto por subtramos, equilibrio 51,4%): **6 años de 15** por
  encima, alternando sin persistencia. 2022: 44,6% · 2023: 45,4% · 2020: 53,6%.
  No son dos regímenes: es ruido alrededor del equilibrio.
- **Fase 11**: `DD/vol = 13,95` contra el objetivo `< 1,1`. El peor quintil de la
  tabla de supervivencia (3,18) ya da 22,6% de quema; esto es **4,4× peor**.
- **Fase 12.9** (coherencia mecánica): pago medio implícito −4,59 $ contra el
  techo de 125 $. Coherente, no hay artefacto: es la señal.

Y en la unidad que decide, contra lo que sí tiene ventaja:

| | ruptura M5 | evento pre-FOMC |
|---|---|---|
| ventaja bruta | −0,009R | **+0,254R** |
| fricción | 0,027R | 0,034R |
| 2 × error típico | 0,022R | 0,104R |
| **`f = f*(medida − 2se)`** | **0** | **+0,115R** |

Misma fricción; uno tiene de dónde pagarla.

---

## 4. Fase 12.3 — añadido: el riesgo tiene un mínimo, no solo un máximo

La 12.3.b fija el techo (`D ≤ margen/25`). Falta el **suelo**, y solo aparece
cuando el sistema tiene una sola pata.

Un acierto rinde `TP/stop × riesgo`. Si la firma exige días cerrados con
**≥ +0,5%** para poder cobrar, hay un riesgo por debajo del cual **ningún acierto
cualifica nunca**:

| riesgo | rinde un TP de 40 bp / stop 80 | ¿cualifica? | peor caso vs límite 2% |
|---|---|---|---|
| 0,96% | 0,480% | **NO** | 1,61% ok |
| 1,00% | 0,500% | justo | 1,67% ok |
| **1,10%** | **0,550%** | **sí** | **1,84% ok** |
| 1,30% | 0,650% | sí | **2,17% ROMPE** |

Medido: **dos puntos básicos valen 435 $ de 510** a cuatro años. Por debajo del
umbral la cuenta gana dinero y no puede cobrarlo nunca.

```
riesgo minimo = 0,5% x stop / TP        (regla del dia cualificado)
riesgo maximo = limite_por_operacion x stop / peor_excursion_historica
```

En el caso medido la ventana es **1,00%–1,20%**. Con dos patas esto es invisible,
porque el ruido diario de la segunda empuja algunos días por encima del umbral;
al apagarla, el umbral queda desnudo.

---

## 5. Añadido a la Fase 10 — la semana de demo, obligatoria

Fallo de método, de categoría y no de detalle: **la estrategia se validó contra
15 años de datos y el entorno de ejecución no se validó nunca.**

| | ¿lo caza una demo del mismo bróker? |
|---|---|
| swap por símbolo **y por dirección** | **sí** |
| nocional real por lote | **sí** |
| spread y comisión reales | **sí** |
| granularidad de lote (símbolos que no entran) | **sí** |
| relleno en huecos | no — rellenan demasiado bien |
| reglas de la firma | no — es su contabilidad, no la del bróker |

Los dos errores más caros del proyecto —el carry y los nocionales— los habría
cazado **una semana de demo, gratis**. Cinco números.

---

## 6. Fallos concretos de `EA_pocas_grandes_FTMO_US100.mq5` v1.03

Independientes del veredicto sobre la señal; el andamiaje de reglas es
reutilizable una vez arreglados.

**a) `g_bloqueado` no se resetea nunca — congela el EA en silencio.**
`VigilaCierreExterno()` lo pone a `true` si una posición se cierra antes de 120 s,
y `OnTick()` hace `return` para siempre. Nada lo levanta. Y como el stop no se
coloca hasta los 150 s, la única forma de cerrar antes es la rama de «el precio ya
pasó el stop», que ocurre **con edad < 150 s** y por tanto **activa el bloqueo**.
El primer movimiento adverso rápido mata el EA.

**b) La posición corre desnuda 150 segundos** con nocional del **125%** de la
cuenta (`D/stop` = 125/0,01 = 12.500 $ sobre 10K). Un 2% en contra son 250 $, el
2,5% de la cuenta, sin protección. Y la regla que justifica esa ventana es una que
el propio código admite que **no tiene evidencia pública en FTMO**.

**c) La fórmula del suelo diario es incorrecta para FTMO, en la dirección
peligrosa.** El código usa `ancla × (1 − 5%)`, o sea el 5% del saldo **actual**.
La regla del 2-Step es *saldo a las 00:00 CE(S)T menos el 5% del capital
**inicial***. Con saldo 11.000 e inicial 10.000: suelo real 10.500, del código
10.450 → **50 $ de margen inventado.** Misma clase de error que el
`MENOR`/`MAYOR` de la Fase 9.

**d) El corte diario es 00:00 CE(S)T**, no la medianoche del servidor. Confirmado
en la documentación de FTMO, que además aclara que la restricción de noticias
**también cubre que salte un SL o TP** dentro de la ventana — el EA solo bloquea
la apertura. Y `InpHorariosNoticiasCSV` viene **vacío por defecto**: sin filtro.

---

## Resumen de los cambios

| # | fase | qué cambia |
|---|---|---|
| 1 | 12.2 | carry −2.292 → **−1.524**; ratio 2,6× → **1,74×**; unidades de swap, no noches |
| 2 | 10 | trampa nueva: nocional desde el P&L; exposición 69,3% → **112,8%** |
| 3 | 12.11 | **cerrada con datos**: −0,0368R, t=−3,38, 8.430 ops, 15 años |
| 4 | 12.3 | el riesgo tiene **suelo** además de techo: ventana 1,00%–1,20% |
| 5 | 10 | semana de demo obligatoria antes de cuenta real |
| 6 | — | cuatro fallos del `.mq5`, con el `g_bloqueado` como el grave |
