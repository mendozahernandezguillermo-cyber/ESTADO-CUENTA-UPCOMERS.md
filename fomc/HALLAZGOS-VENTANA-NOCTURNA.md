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

## Qué haría ahora, en orden

1. **Medir la unidad de swap.** Es el único dato que mueve el veredicto de `f=0`
   a `f>0`, cuesta una semana y ya hay una posición abierta con la que medirlo.
2. **No tocar el riesgo hasta tenerlo.** La subida pendiente de 0,96% a 1,10%
   escala el nocional y con él el swap, así que mueve la fricción en la
   dirección mala justo en el margen que decide.
3. **Medir la ventana CON el TP de 40 bp puesto.** Lo de arriba es el retorno de
   la ventana en bruto; la Fase 12 ya midió que el TP corto cuesta ventaja
   (19,4 → 15,4 bp) a cambio de probabilidad de cobro. Si ese descuento se
   aplica al exceso de +19,54, la única esquina positiva también se cierra.
4. Y solo entonces, la pregunta del EA. La familia tiene efecto real y
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
python3 control_m1.py                # el de antes, para contrastar

cd ../mql5
python3 verificar_mql5.py Medir_Swap_Unidades.mq5
```
