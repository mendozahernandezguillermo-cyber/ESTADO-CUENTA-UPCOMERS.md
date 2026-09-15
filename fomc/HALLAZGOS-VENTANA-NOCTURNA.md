# La ventana nocturna pre-FOMC, medida sobre los 5,7 M de barras

Medido el 15-sep-2026 sobre `nas100-data/raw/` (5.736.908 barras M1, 2011-09-19
a 2026-08-28). Cuatro scripts nuevos en `fomc/`, uno en `mql5/`. Todo lo que
sigue es reproducible con los comandos del final.

El encargo era desarrollar un EA. La Fase 8.5 dice que antes hay que emparejar
la frecuencia de la familia con el suelo de ruido, y la 12.1 que el tamaño sale
de `f*(ventaja − 2·error típico)`. Esas dos cuentas son las que deciden, y con
los datos delante salen así.

---

## 1. El número documentado se reproduce, pero estaba medido contra cero

`ESTADO-CUENTA` y la Fase 10 dan la réplica de la ventana viva en **+20,28 bp
con t=4,86** sobre 117 eventos. Reproducido con la configuración exacta del EA
—entrada 15:57 NY del día anterior, salida 09:30 NY del día del anuncio—:

```
noches pre-FOMC       n=117   +26,19 bp   sd 61,5   se 5,69   t vs cero = 4,60
```

Mismo orden de magnitud, y el `t` vs cero es alto. **Pero `t` vs cero no es la
pregunta**, porque los índices tienen prima overnight y hay que descontarla:

```
todas las noches            n=4050    +3,69 bp
solo noches de miercoles    n= 637    +6,66 bp   <- el control que toca
noches pre-FOMC             n= 117   +26,19 bp
```

El 95% de los anuncios cae en miércoles, así que el control es la noche de
miércoles. **El exceso atribuible al FOMC es +19,54 bp, no +26,19.** Un cuarto
del número publicado es prima overnight genérica que se cobraría igual sin
anuncio.

## 2. El efecto es real: sobrevive a dos diseños independientes

Aquí me equivoqué primero y conviene dejarlo escrito. Mi primer control fueron
las noches del mismo día de la semana a −7 y −14 días. Contra ése el exceso baja
a +13,47 bp con t=1,83 (p=0,068), y el placebo a −14 días daba +19,18 bp con
t=2,41 — *más* significativo que el efecto real. Estuve a punto de cerrar la
familia con eso.

El error era el control: con n=228 oscila ±20 bp él solo, así que no informa ni
a favor ni en contra. Lo cazó el placebo, que es exactamente para lo que la Fase
7.5 lo exige. El diseño que sí decide es la aleatorización:

```
20.000 muestras de 117 noches de miercoles sin anuncio
  nula: p50 +6,67 · p95 +16,79 · p99 +20,98
  observado: +26,19 bp        p empirico = 0,0007
```

Y el placebo estructurado, que conserva calendario y día de la semana y solo
quita el anuncio — los mismos 117 eventos movidos k semanas:

```
  -42d +14,6   -35d +10,9   -28d  +7,3   -21d  +7,8   -14d  -8,4   -7d  +8,4
    0d +26,2  <== los de verdad, z = 2,83
  +14d +17,4   +21d  +2,1   +28d  -5,8   +35d  +5,8   +42d +10,1
```

**0 de 12 placebos alcanzan el valor real.** El mejor llega a z=1,52 contra 2,83.

## 3. Y NO murió en 2015 — esa predicción queda refutada

Cada tramo contra la nula de su propia época, porque el nivel de la prima
overnight cambia entre eras:

| tramo | n | FOMC | nula | exceso | p emp. |
|---|---|---|---|---|---|
| 2011-2015 | 33 | +28,57 | +6,74 | **+21,83** | 0,0155 |
| 2016-2020 | 39 | +29,59 | +7,31 | **+22,28** | 0,0231 |
| 2021-2026 | 45 | +21,51 | +6,02 | +15,49 | 0,0705 |
| **2016-2026** | 84 | +25,26 | +6,63 | **+18,64** | **0,0088** |
| TODO | 117 | +26,19 | +6,66 | +19,54 | 0,0008 |

El efecto posterior a 2015 es **+18,64 bp con p=0,0088**, indistinguible del
anterior. La literatura lo da por muerto y en estos datos no lo está. Es la
única noticia buena del ejercicio, y va en contra de lo que la especificación
daba por supuesto.

## 4. Pero el tamaño defendible es cero en casi todo el espacio

Fricción: ida y vuelta `2 × 1,37 = 2,74 bp`, más el swap. El nocional implícito
es `25.000 × 1,10% / 80 bp = 34.375 $`, y una unidad de swap al 6,4% anual sobre
364 unidades vale **1,76 bp del nocional**.

| tramo | exceso | unid. swap | fricción | neto | `f` defendible |
|---|---|---|---|---|---|
| TODO | +19,54 | 1 | 4,50 | +15,04 | **+2,59 bp** |
| TODO | +19,54 | 3 | 8,01 | +11,52 | **f = 0** |
| 2016-2026 | +18,64 | 1 | 4,50 | +14,14 | **f = 0** |
| 2016-2026 | +18,64 | 3 | 8,01 | +10,62 | **f = 0** |
| 2021-2026 | +15,49 | 1 | 4,50 | +10,99 | **f = 0** |
| 2021-2026 | +15,49 | 3 | 8,01 | +7,48 | **f = 0** |

`2·error típico` vale 12,45 bp en la muestra completa y 15,75 en 2016-2026. El
efecto es real y **la muestra sigue siendo demasiado corta para dimensionar
sobre él**: 8 eventos al año es el suelo de ruido que la Fase 8.5 ya avisaba.

De las seis filas, una sola da tamaño positivo, y es la esquina más optimista:
muestra completa *y* una unidad de swap.

## 5. La unidad de swap es el dato que decide, y no está verificado

El anuncio es en miércoles, la entrada cae el martes por la tarde, y el rollover
es a las 00:00 del servidor = **18:00 NY**. La posición cruza siempre un
rollover. Si ese cruce cobra 1 unidad, la fila de arriba da +2,59 bp; si cobra 3
—porque el bróker asigne el triple al rollover que sella el miércoles— da cero.

`ESTADO-CUENTA` presupuesta **«50 $/año (8 noches)»**, que es contar noches. La
Fase 15 dice literalmente que hay que contar unidades y que el miércoles vale
tres. Con 3 unidades por evento el carry es ~145 $/año, no 50 $, sobre una
expectativa neta de ~337 $/año.

**No lo doy por sabido**: se resuelve gratis, y `mql5/Medir_Swap_Unidades.mq5`
lo hace por los dos caminos. `SYMBOL_SWAP_ROLLOVER3DAYS` dice qué día lleva el
triple —una línea, sin esperar— y el cargo real se mide con
`swap = (equity − saldo) − Σ Profit` en cada rollover, que es el método de la
Fase 15. Si los dos no coinciden, manda el segundo.

## 6. Dos correcciones sueltas, medidas

**`control_m1.py` apunta 105 minutos tarde en 2011-2012.** Fija
`anuncio = 14:15 si año ≤ 2012`, pero los días con conferencia de prensa de esos
dos años publicaban a las 12:30. Medido en el perfil agregado de |ret| por
minuto:

```
2013-2026 (n=108)  pico del agregado en 14:00  (31,2 bp)   <- la regla acierta
2011-2012 (n=  9)  pico del agregado en 12:38  (17,7 bp)   <- la regla falla
control no-FOMC    pico en 11:03 (9,4 bp) sobre mediana 6,5  <- plano, valido
```

Reacción media en cada candidata, 2011-2012: **12:30 → 12,0 bp** contra
14:15 → 5,9 bp. Su ventana «09:30 → justo antes del anuncio» contiene en esos
eventos el anuncio y 105 minutos de reacción posterior. No contamina la ventana
nocturna, que cierra a las 09:30 y va por delante de cualquiera de las dos horas.

**`fomc_fechas.csv` tiene la bandera `conf_prensa` mal.** No marca la reunión,
marca la época: está en `True` para las 8 reuniones de 2012 cuando solo 4-5
tuvieron comparecencia. Sirve para separar antes/después de abril-2011 y nada
más; la pertenencia a las 12:30 hay que medirla.

**Y el dato que sí conviene tener presente: `control_m1.py` ya refutaba su propia
predicción** y no estaba anotado en ninguna parte. Su ventana intradía
09:30→anuncio da t=−0,57 en 2011-2015 y t=+0,07 en el total. El efecto no está
ahí; está en la nocturna. Son ventanas distintas y conviene no confundirlas.

---

## 7. Con el TP y el stop puestos: la esquina positiva NO se cierra

Todo lo anterior es el retorno de la ventana en bruto. `EA_FOMC_Gap` no opera
eso: abre **largo** y deja `sl = −80 bp` y `tp = +40 bp` en el servidor. Con el
TP a mitad de distancia que el stop la distribución queda truncada, así que hay
que caminar la senda M1 barra a barra — truncar el cierre no vale, porque el TP
se toca dentro de la noche.

`con_tp_y_stop.py` lo simula con la asimetría que toca: el **stop** rellena en
el open del hueco (peor que el nivel, que es lo que la Fase 9 midió) y el **TP**
rellena en el nivel, porque es una orden límite y un hueco a favor no la mejora.
Mi primera versión daba crédito por esos huecos favorables (16% de los eventos)
e inflaba la media 4,9 bp.

```
                          pre-FOMC   control   exceso   2se
sin TP ni stop               26,19      6,66    19,54  12,45
con TP 40 / stop 80          15,71      0,64    15,07   8,06
```

El TP se come 4,47 bp de exceso **y a la vez recorta 2·se de 12,45 a 8,06**. Los
dos efectos casi se cancelan:

| | exceso | unid. swap | fricción | neto | `f` defendible |
|---|---|---|---|---|---|
| en bruto | +19,54 | 1 | 4,50 | +15,04 | +2,59 bp |
| **con TP/stop** | **+15,07** | **1** | **4,50** | **+10,58** | **+2,52 bp** |
| en bruto | +19,54 | 3 | 8,01 | +11,52 | f = 0 |
| **con TP/stop** | **+15,07** | **3** | **8,01** | **+7,06** | **f = 0** |

**Mi predicción era que el descuento del TP cerraría la única esquina positiva, y
era falsa.** El TP no solo cuesta ventaja: compra precisión, y para la regla de
dimensionado sale a tablas. La lectura de la Fase 12 —«un TP corto cuesta
ventaja pero baja el listón»— está incompleta: también baja la varianza, que es
la mitad del criterio.

Y hay un motivo estructural detrás. Con las barreras puestas, el control de
miércoles se derrumba de +6,66 a **+0,64 bp**, mientras el efecto pre-FOMC solo
baja de 26,19 a 15,71. Las barreras filtran la prima overnight genérica —una
deriva pequeña contra un stop del doble de distancia da esperanza ~0— y dejan
pasar la del evento, que sí llega al TP. Se ve en los motivos de salida:

```
pre-FOMC   TP 53%   stop  7%   cierre 09:30 40%
control    TP 42%   stop 14%   cierre 09:30 44%
```

Eso rehabilita en parte la medición original contra cero: **con el TP puesto,
«contra cero» y «contra el control» casi coinciden**, porque el control es +0,64.

### Robustez, y dos validaciones cruzadas que salen gratis

| | pre-FOMC | control | exceso |
|---|---|---|---|
| completo | +15,71 | +0,64 | +15,07 |
| recortado al 2% | +18,57 | +3,43 | +15,14 |
| mediana | +40,00 | +15,28 | +24,72 |
| solo noches con agujeros ≤ 60 min | +16,24 | +2,50 | +13,75 |

No lo sostienen ni las colas ni los agujeros de datos. Y dos números que caen
por su cuenta y confirman que la tubería está bien montada:

- **36 de 117 eventos tienen agujeros de más de 60 minutos** (117 − 81). Es
  exactamente la cifra que la Fase 9 midió por otro camino.
- **El mejor día sale +137,50 $ = 0,550%** de la cuenta, que es literalmente el
  «un acierto rinde 0,550%» de `ESTADO-CUENTA`. Y es una **constante**, no una
  variable: con el TP capado, todo acierto rinde lo mismo.

Comprobado además que `serie_s1` en `planes/cobros_reales.py` ya usa esta misma
convención (`sal = tp` arriba, `sal = o if o <= sl else sl` abajo). No hay nada
que corregir ahí; el «mejor día 308 $» de la Fase 12 pertenece a la
configuración de dos patas, ya retirada.

## 8. Reconciliado: los −99,0 bp y los −133,4 bp de la Fase 9

Mi peor relleno realizado sale **−99,0 bp** y la Fase 9 publica **−133,4 bp**,
las dos supuestamente sobre los mismos M1 y los mismos 117 eventos. La causa es
un solo número: **`mql5/riesgo_de_salto.py` línea 40 fija `TP_BP = 80.0`**. Esas
cifras son de la configuración simétrica ±80, anterior a bajar el take profit.

`reconcilia_fase9.py` cambia **solo** el TP en mi simulador y reproduce la
Fase 9 entera:

| magnitud | Fase 9 | este script (TP=80) | |
|---|---|---|---|
| salidas por stop | 9 | 9 | ✓ |
| stops peor que −80 bp | 5 | 5 | ✓ |
| deslizamiento máximo | 54,1 bp | 54,1 bp | ✓ |
| deslizamiento medio | 19,7 bp | 19,7 bp | ✓ |
| **peor evento** | **−133,4 bp** | **−133,4 bp** | ✓ |

Cinco de cinco. Ninguna de las dos mediciones estaba mal: contestaban a
configuraciones distintas.

El residuo que faltaba —54,1 contra 53,4 bp— era la **definición** del
deslizamiento. `riesgo_de_salto.py` lo mide contra el precio del stop
(`sl/o − 1`) y yo lo medía contra el de entrada (`|ret| − 80`). Difieren en el
término de composición. Usando la suya, cuadra al decimal.

### Y el mecanismo, que sí es un hallazgo

Todo se juega en un evento, **2022-01-26**, misma senda de precios:

```
con TP=40 :    +40,0 bp   salida por take profit
con TP=80 :   -133,4 bp   salida por stop, 54,1 bp por debajo del nivel
```

Con el TP a 40 la posición **ya estaba cerrada cuando llegó el hueco**. Con el TP
a 80 seguía abierta. Es el mismo mecanismo que ya se veía en la varianza, ahora
en la cola: **el TP corto no solo trunca la cola buena, quita la mala**, porque
saca la posición antes de la ventana de huecos.

En la unidad que decide, el límite del 2% por operación:

```
TP=40 : peor evento  -99,0 bp = 1,36% de la cuenta  ->  margen 32%
TP=80 : peor evento -133,4 bp = 1,83% de la cuenta  ->  margen  8%
```

Las dos aguantan con el riesgo al 1,10%, así que la discrepancia no cambiaba
ninguna decisión. Pero **elegir el TP era también decidir sobre el hard breach**,
y en la Fase 12 —donde el TP se eligió por la regla del mejor día y la
probabilidad de cobro— eso no estaba contado. El TP de 40 se llevaba un tercer
beneficio que nadie le había atribuido.

## Qué haría ahora, en orden

1. **Medir la unidad de swap.** Sigue siendo el único dato que mueve el veredicto
   de `f=0` a `f>0`, y ahora se sabe que es el ÚNICO: el TP ya está descontado y
   no cierra la esquina. Cuesta una semana y hay una posición abierta con la que
   medirlo.
2. **No tocar el riesgo hasta tenerlo.** La subida pendiente de 0,96% a 1,10%
   escala el nocional y con él el swap, así que mueve la fricción en la
   dirección mala justo en el margen que decide.
3. Y solo entonces, la pregunta del EA. La familia tiene efecto real y
   verificado por dos diseños; lo que no tiene es muestra para dimensionarlo.
   Subir `n` no es cuestión de parámetros: es de eventos, y el candidato es el
   supuesto 2 de la especificación —IPC y empleo— que multiplica la frecuencia
   por cuatro. El S&P no sirve: correlaciona ~0,9 con el NASDAQ y no añade `n`.

## Reproducir

```bash
pip install pandas numpy scipy

cd fomc
python3 hora_del_anuncio.py          # guardian de reloj -> horas_medidas.csv
python3 ventana_nocturna.py          # la ventana viva, controles y rejilla
python3 aleatorizacion_nocturna.py   # aleatorizacion + barrido + friccion
python3 con_tp_y_stop.py             # lo que opera el EA: TP 40 / stop 80
python3 reconcilia_fase9.py          # cierra el -99,0 contra el -133,4
python3 control_m1.py                # el de antes, para contrastar

cd ../mql5
python3 verificar_mql5.py Medir_Swap_Unidades.mq5
```


---

## 9. Sustituir a EA_Trend_Multi: las dos vías cerradas y la que queda

Solo con el FOMC hacen falta **~17 meses** para juntar los 6 días cualificados:
8 eventos al año × 53% que alcanzan el TP = 4,24 días/año. La premisa es
correcta y ésta es la aritmética.

### Lo que ya estaba refutado en el propio repositorio

Recomendé dos veces multiplicar eventos con IPC y empleo. **Estaba medido y
refutado, y no lo comprobé antes de recomendarlo.** `fomc/eventos_830.py` y
`fomc/bancos_centrales.py`:

```
IPC + empleo (n=351)     -5,0 bp   t=-1,17   NO GENERALIZA
  empleo solo (n=177)   -12,9 bp   t=-2,31   negativo
BoJ -> Nikkei (n=128)    -5,3 bp   t=-0,83   falla la diagonal
NASDAQ -> Fed            +20,7 bp   t=+3,38   la unica que funciona
```

El diseño 2×2 de `bancos_centrales.py` es concluyente: las tres celdas fuera de
la diagonal salen planas, como debían, y la diagonal del BoJ **falla**. No es
una «prima por evento programado»: es específico de la Fed sobre el NASDAQ, y
sigue sin mecanismo conocido. La vía de multiplicar eventos está cerrada.

### El trend no hay que sustituirlo, hay que quitarle la plata

`trend/trend_bajo_carry.py`. Primero, el carry no se compara por nocional sino
**por unidad de riesgo**, porque la estrategia dimensiona por volatilidad
objetivo y un instrumento tranquilo necesita más nocional:

| mercado | swap/año | vol | swap/vol |
|---|---|---|---|
| **Plata** | 30,0% | 33,3% | **0,900** |
| S&P 500 | 6,4% | 18,9% | 0,338 |
| Oro | 3,2% | 18,2% | 0,175 |
| EUR/USD | 1,8% | 11,0% | 0,164 |
| GBP/USD | 1,0% | 9,2% | 0,108 |
| USD/JPY | 1,0% | 11,5% | 0,087 |
| AUD/USD | 1,0% | 12,3% | 0,081 |

Ese reorden importa: el oro paga casi el doble que EUR/USD sobre nocional y
**cuesta lo mismo por unidad de riesgo**.

| universo | n | Sharpe | t | carry $/año | neto $/año |
|---|---|---|---|---|---|
| B completo | 7 | 0,74 | 4,21 | −568 | +260 |
| **B sin plata** | **6** | **0,74** | **4,21** | **−336** | **+493** |
| divisas + oro | 5 | 0,33 | 1,84 | −230 | +144 |
| solo divisas | 4 | 0,21 | 1,15 | −194 | +40 |

**Quitar la plata es gratis.** El Sharpe con 7 y con 6 es 0,735586 contra
0,736707 — comprobado con decimales porque parecía un fallo parcial silencioso
de los de la Fase 6.3, y no lo es: las siete series están cargadas. La plata no
aporta señal y cuesta 232 $/año.

**Seguir quitando no es gratis.** Con solo divisas el Sharpe se hunde de 0,74 a
0,21. La diversificación entre clases es lo que hace funcionar al trend, así que
«solo divisas, que son las baratas» queda descartado por medición.

### Y los días cualificados

| configuración | días/año | con el FOMC | meses a 6 días |
|---|---|---|---|
| solo FOMC | 0,0 | 4,2 | **17,0** |
| B sin plata | 9,4 | 13,6 | **5,3** |

Los días cualificados los da la **volatilidad**, no la ventaja: todos los
universos escalados a 4,5% dan 9,0-9,8 días/año independientemente de su Sharpe.

## 10. Pero antes hay que resolver una contradicción del repositorio

La tabla de arriba supone que el día cualificado se cuenta por **cambio de
equity**, que es lo que hace el modelo:

```
planes/cobros_reales.py:225   cual += (vivo & (pnl >= 0.005*CUENTA))
                        219   bal = np.where(vivo, eqf, bal)     -> marca a mercado
```

La Fase 13 razona lo contrario: dice que la pata continua «casi no realiza
beneficio ningún día» y que eso es «una ventaja estructural». Eso solo tiene
sentido si la regla mira el **realizado**.

| lectura | qué aporta el trend | consecuencia |
|---|---|---|
| por equity | los 9,4 días de la tabla | 5,3 meses, y aprieta la regla del 20% |
| por realizado | techo de ~12 días (rebalancea 1×mes), realista 2-3 | la tabla es papel mojado |

Es la Fase 12 —«léelas, no las deduzcas»— y la Fase 9 —«verifica solo contra
puntos donde las hipótesis divergen»—. **Se resuelve gratis mirando el panel de
la firma tras un día con la equity arriba y nada cerrado.** Hasta entonces no se
sabe si el sustituto tiene que mantener volatilidad o tiene que cerrar
operaciones a menudo, y son dos EAs distintos.

### Y el intercambio, dicho entero

La Fase 15 comparó las dos configuraciones con la mecánica de cobro dentro:

```
sin plata   : recibido a 4 años 233 $ · P(cobra) 50,0% · P(quema) 7,0%
solo el FOMC: recibido a 4 años 509 $ · P(cobra) 89,5% · P(quema) 0,0%
```

Con el objetivo «maximizar lo recibido a 4 años» el FOMC solo gana, y la
decisión de la Fase 15 era correcta. Lo que cambia es el objetivo: si lo que
aprieta es el **tiempo hasta el primer cobro**, la pata sin plata pasa de 17
meses a ~5. Es un intercambio real, no un almuerzo gratis: se paga con **7
puntos de probabilidad de ruina**.


---

## 11. Corrección al apartado 9, y sobre qué cuenta está hecho todo esto

### El fallo

La tabla del apartado 9 daba Sharpe 0,74 y t=4,21. **Estaba mal.** Promediaba con
`dropna(how="all")`, así que las fechas en que solo cotizaba el S&P (1995-2005)
entraban como una cartera de un solo mercado, lo que infla el Sharpe y hace
incomparables los universos entre sí. `trend_cfd.py` lo evita con
`MIN_MERCADOS = 6` y yo no puse el filtro.

Corregido exigiendo que **todos** los mercados del universo tengan dato, con lo
que todos arrancan en 2006-05:

| universo | días | Sharpe | t | carry $/año | neto $/año |
|---|---|---|---|---|---|
| B completo (7) | 5071 | 0,47 | 2,09 | −672 | **−148** |
| **B sin plata (6)** | 5071 | **0,47** | **2,11** | −387 | **+141** |
| divisas + oro (5) | 5071 | 0,31 | 1,37 | −275 | +69 |
| solo divisas (4) | 5257 | 0,21 | 0,97 | −220 | +20 |

La conclusión no cambia y ahora **coincide con la Fase 15**, que daba +156 $/año
para «sin plata» por un camino distinto. Yo doy +141. Quitar la plata sigue
siendo gratis en señal (0,47 → 0,47) y es lo que pone el neto en positivo.

Lo que sí cambia es la fuerza de la pata: **Sharpe 0,47 con t=2,11 sobre 20
años**, no 0,74 con t=4,21. Es marginal, y conviene tenerlo presente antes de
apoyarse en ella.

### Aplicado al EA

`mql5/EA_Trend_Multi.mq5`:

```
InpSimbolos    = "SPCUSD.c,NACUSD.c,XAUUSD,EURUSD,USDJPY,GBPUSD,AUDUSD"
InpMercadosRef = 7      (era 8)
```

`InpMercadosRef` tiene que bajar a 7. Si se queda en 8, el divisor
`max(activos, ref)` deja la exposición permanentemente en 7/8 del objetivo: una
desactivación silenciosa del 12,5% del riesgo, que es justo la clase de error de
dirección de la Fase 9. `XAGUSD` se queda en `REF_SIMBOLO`/`REF_CIERRE` porque
es solo tabla de consulta para el empalme y ya no se consulta.

**Aviso:** con la plata fuera quedan 7 en la lista, y `NACUSD.c` se omite por
granularidad en una cuenta de 25K, así que operan **6** con `InpMinMercados = 6`.
Margen cero: si falla un símbolo, el EA deja de operar. Falla en cerrado, que es
lo correcto, pero conviene saberlo.

Y una decisión pendiente que no he tocado porque no se pidió: `trend/sin_nasdaq.py`
mide que sacar `NACUSD.c` cuesta **0,61% anual con t=2,12** y las carteras
correlacionan 0,9711 — por su propio criterio (>0,99 y sin `t`) **no es gratis**.
Pero hay que sacarlo igual por cumplimiento: si el trend se pone corto en
`NACUSD.c` y llega un FOMC, la pata #1 abre un largo en el mismo símbolo, que es
lo que Upcomers prohíbe. Hoy no ocurre porque la granularidad lo omite.

### Sobre qué cuenta está hecho todo esto: **Upcomers, sin excepción**

Todas las constantes salen de `ESTADO-CUENTA-UPCOMERS.md` y de
`planes/cobros_reales.py`:

```
CUENTA 25.000 · riesgo 1,10% · stop 80 bp · spread 1,37 bp · swap 6,4%
MIN_DIAS=6 · MIN_BEN=0,005 · BEST=0,20        <- regla de consistencia Upcomers
TOPES = 250, 500, 750, 1000, 1250, 1560, 1875 <- topes escalonados Upcomers
limite 2% por operacion (hard breach)         <- Upcomers
vol optima 4,5%                               <- Fase 12, instant funding
```

**En FTMO 2-Step casi nada de eso aplica**, y lo tienes medido en
`planes/ftmo_2step.py`:

| | Upcomers Vanguard | FTMO 2-Step |
|---|---|---|
| días mínimos | **6, cada uno ≥ +0,5%** | **4 por fase, sin umbral diario** |
| topes de cobro | escalonados 250→1875 | **ninguno** |
| regla del mejor día | 20% | **ninguna** |
| pérdida máxima | trailing 7% sobre el pico | **10% estática** sobre el inicial |
| objetivo antes de cobrar | ninguno | **+10% y luego +5%** |

**El problema de los 17 meses es una regla de Upcomers, no de FTMO.** En FTMO no
existe el día cualificado, así que el apartado 10 —la contradicción entre contar
por equity o por realizado— **deja de importar**. Lo que aprieta es el objetivo.

Y con ello cambia la volatilidad óptima, que es la Fase 8 al pie de la letra
(«la volatilidad óptima es propiedad de la firma, no tuya»):

```
   vol   riesgo/ev   P(pasa las 2)   hasta fondear   EV/año   P(quema tras fondear)
  4,5%      1,47%        96,9%            2,5a         214$          0,0%
  7,0%      2,29%        88,6%            1,4a         863$         13,3%
 10,0%      3,28%        77,6%            0,8a       1.248$         50,4%
 14,0%      4,59%        56,8%            0,4a         879$         92,1%

  Upcomers Vanguard 7% (en vivo)                        269$
```

FTMO al 7% de vol rinde **3,2 veces** Upcomers; al 10%, 4,6 veces. Porque
desaparece la pinza que confiscaba el 82%.

### Las dos consecuencias que hay que sacar de aquí

**La decisión sobre la plata es robusta al cambio de firma, y a mejor.** A 7-10%
de vol el apalancamiento es 1,6-2,2× el de 4,5%, y el carry escala con él: la
plata pasaría de −285 a −455/−633 $/año. Quitarla importa **más** en FTMO.

**El dimensionado NO es robusto, y aquí me tienes que corregir el consejo.** Te
dije «no subas el riesgo de 0,96% a 1,10% hasta medir el swap». Ese razonamiento
es de Upcomers: el techo lo pone el **límite del 2% por operación**, que en FTMO
no existe. La tabla de arriba pide 2,29-3,28% de riesgo por evento para que el
reto tenga sentido, y eso en Upcomers sería breach instantáneo. La ventana
«1,00%-1,20%» de la Fase 15 es **exclusivamente de Upcomers**.

O sea que antes de seguir hay que fijar sobre qué cuenta se está optimizando,
porque las dos respuestas son incompatibles, no matizadas.
