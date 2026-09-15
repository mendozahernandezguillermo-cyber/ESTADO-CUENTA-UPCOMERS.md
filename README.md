# Auditoría cuantitativa y operación en cuenta prop

Repositorio de trabajo del proyecto. **Si abres esto desde un chat nuevo, lee
esta página primero** y luego los dos documentos que se citan: contienen el
estado y el porqué de cada decisión, que la conversación no lleva consigo.

---

## Estado del proyecto en una frase

De 19 familias de hipótesis probadas sobrevivieron dos. Una de ellas —el trend
multi-activo— resultó **inviable por coste de financiación**, no por falta de
señal. Queda **una sola estrategia** en producción: la prima nocturna previa a
los anuncios del FOMC, sobre NASDAQ.

## Por dónde empezar

| documento | qué contiene |
|---|---|
| **`ESTADO-CUENTA-UPCOMERS.md`** | el estado operativo: reglas de la firma, los cuatro relojes, la configuración de los tres EAs input por input, la expectativa y los cabos sueltos. **Una página. Empieza aquí.** |
| **`PROTOCOLO-AUDITORIA-DARWINS.md`** | las Fases 0 a 15. Cada umbral sale de una medición o de un error cometido. La 14 y la 15 son las importantes: la mecánica del cobro y el carry. |
| `CORRECCIONES-PROTOCOLO-2.1.md` | correcciones a un documento hermano que vive en otro chat. Seis puntos, con el número que hay que cambiar en cada uno. |

## Las dos conclusiones que más cuestan de aceptar

**1. El carry decide antes que la estrategia.** En una cartera tendencial de 7
posiciones el coste de financiación fue **1.524 $/año contra 387 $ de retorno
bruto** — 1,74 veces todo lo que ganaba. La plata sola era el 65% del carry con
el 13% de la cuenta, al **30% anual sobre su nocional**. Fase 15.

**2. La mecánica del cobro fija el EV más que la señal.** Topes escalonados por
cobro y una regla de consistencia que obliga a acumular ~5,2 veces el día mayor
antes de poder pedir nada: sale el **18-20% del beneficio generado**, y el resto
se queda dentro. Fase 14.

## Estructura

```
mql5/          los tres EAs (.mq5) y verificar_mql5.py, un comprobador estatico
planes/        modelo de cobros, carry, dimensionado, comparacion de vehiculos
fomc/          la estrategia #1: rejilla de 56 especificaciones horarias
trend/         la estrategia #2 (retirada) y los datos de los proxies ETF
nas100-data/   M1 de NASDAQ 2011-2026 en raw/, y los estudios intradia
prop-instant/  diseno del guardian de riesgo y reglas de las firmas
thl-journal/   la auditoria del DARWIN THL, que dio negativo
darwin-thl/    ingesta de la API de Darwinex (necesita .env, ver .env.example)
```

## Los datos

**`nas100-data/raw/`** — 16 ficheros, uno por año, **5.736.908 barras M1** de
2011-09-19 a 2026-08-28.

```
usatechidxusd-m1-bid-AAAA-01-01-AAAA-12-31.csv
formato   : timestamp,open,high,low,close
timestamp : epoch en MILISEGUNDOS, UTC
```

`usatechidxusd` es el código de Dukascopy para el US Tech 100.

**Tres limitaciones que hay que tener presentes antes de medir con ellos:**

1. **Solo BID.** No hay ask ni volumen; el spread hay que añadirlo sintético.
   El medido en el bróker para NACUSD.c es **1,37 bp**, y la fricción correcta es
   `2 × spread / stop` (ida y vuelta), no media horquilla en la entrada.
2. **La densidad cambia en 2018**: de 241-284 días/año hasta 2017 a 310-312
   desde 2018. Es un cambio en los datos, no en el mercado. Contamina cualquier
   comparación año contra año que dependa del recuento de barras.
3. **2011 son 5 días y 2012 arranca el 19 de enero.** El histórico útil empieza
   en 2013.

Otros datos: `trend/datos/` (ETF y divisas, cierre diario ajustado) y
`nas100-data/yahoo/` (índices para el universo de sustitución).

## Reproducir las mediciones clave

```bash
pip install pandas numpy scipy      # el sandbox los pierde a menudo

# el carry real, contando unidades de swap y no noches
python3 planes/carry_corregido.py

# las tres configuraciones con el carry dentro -> por que se apago el trend
python3 planes/con_carry_dentro.py

# el acantilado del dia cualificado: 2 puntos basicos valen 435 $ de 510
python3 planes/riesgo_solo_fomc.py

# el limite del 2% por operacion, que es un hard breach
python3 planes/max_perdida_operacion.py

# el caso de la ruptura de canal, cerrado con 15 años (t = -3,38)
cd nas100-data && python3 cierre_fase_12_11.py

# comprobador estatico de los EAs antes de compilar
cd mql5 && python3 verificar_mql5.py
```

## Convención del repositorio

Cuando un documento dice **«medido»** hay un script que lo produjo. Cuando dice
**«supuse»** es un aviso, y hay al menos un caso en el que ese aviso se escribió
tarde: la fila del beneficio atrapado de la Fase 14 se presentó como hallazgo
durante varios turnos siendo un supuesto. Está marcada.
