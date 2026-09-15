#!/usr/bin/env python3
"""
¿HAY UNA VERSION DEL TREND QUE SOBREVIVA AL CARRY?

El problema que resuelve. Solo con el FOMC hacen falta ~17 meses para juntar los
6 dias cualificados que exige la firma, porque la pata da 8 eventos al año y
solo el 53% alcanza el TP: ~4,2 dias al año. El trend arreglaba eso y se retiro
por CARRY, no por señal (Fase 15: -1.461 $/año contra +387 de bruto).

Antes de proponer una familia nueva hay que agotar la que ya esta validada. Y la
Fase 8.5 es explicita: una familia adicional tiene que pasar por las Fases 14 y
15 —cobros y carry— antes de que su Sharpe cuente para nada. Asi que esto no
busca señal: la señal ya esta medida (Sharpe 0,66, t=3,17 sobre 276 meses). Lo
que busca es el SUBCONJUNTO cuyo carry no se come el retorno.

LA SUTILEZA QUE CAMBIA EL ANALISIS. La tabla de la Fase 15 ordena el carry por
% anual del NOCIONAL, y con ese criterio las divisas ganan de calle. Pero el
nocional no es la unidad relevante: la estrategia dimensiona por VOLATILIDAD
OBJETIVO, asi que un instrumento tranquilo necesita mas nocional para aportar el
mismo riesgo, y paga mas swap por el mismo riesgo aportado. Lo que decide es

    coste de carry por unidad de volatilidad = tasa_swap_anual / vol_anual

Con ese criterio la plata sigue siendo catastrofica, pero el orden del resto no
es el que sugiere la tabla del nocional.

Prediccion registrada ANTES de correrlo:
  - la plata es la peor por mucho con las dos metricas
  - las divisas NO dominan una vez normalizado por volatilidad
  - quitar la plata basta para poner el neto en positivo (la Fase 15 ya lo vio)

RESULTADO, y una comprobacion que hubo que hacer. El Sharpe con 7 mercados y
con 6 sale IGUAL a dos decimales (0,74 y t=4,21), lo que parecia un fallo
parcial silencioso de los que avisa la Fase 6.3. No lo es: con mas decimales son
0,735586 y 0,736707, y las siete series estan cargadas y con cobertura correcta
(Plata: 5.115 dias, 2006-05 a 2026-08). La plata simplemente NO APORTA SEÑAL y
cuesta 232 $/año de carry. Sacarla es gratis.

Lo que NO es gratis es seguir quitando: con solo divisas el Sharpe se hunde de
0,74 a 0,21. La diversificacion entre clases de activo es lo que hace funcionar
al trend, asi que la hipotesis de "solo divisas, que son las baratas" queda
descartada por esta medicion.
"""
import os

import numpy as np
import pandas as pd
from scipy import stats

AQUI = os.path.dirname(os.path.abspath(__file__))
D_TREND = os.path.join(AQUI, "datos")
D_YAHOO = os.path.join(AQUI, "..", "nas100-data", "yahoo")

VOL_OBJETIVO = 0.10
MIRADA = 12
TOPE = 5.0

CUENTA = 25000.0
UNID_ANIO = 364.0          # unidades de swap al año, con el miercoles triple

# Tasas de swap medidas en la Fase 15, en % anual sobre el nocional. Solo estan
# las SIETE que se midieron en la cuenta real; el resto no tiene medicion y por
# eso no entra en ningun universo candidato.
SWAP = {
    "Plata":     0.300,
    "S&P 500":   0.064,
    "Oro":       0.032,
    "EUR/USD":   0.018,
    "GBP/USD":   0.010,
    "AUD/USD":   0.010,
    "USD/JPY":   0.010,
}

FICHERO = {
    "S&P 500": f"{D_TREND}/SPY.csv", "Oro": f"{D_TREND}/GLD.csv",
    "Plata": f"{D_TREND}/SLV.csv", "EUR/USD": f"{D_TREND}/EURUSDX.csv",
    "USD/JPY": f"{D_TREND}/USDJPYX.csv", "GBP/USD": f"{D_TREND}/GBPUSDX.csv",
    "AUD/USD": f"{D_TREND}/AUDUSDX.csv",
}

UNIVERSOS = [
    ("B completo (7)", list(SWAP)),
    ("B sin plata (6)", [m for m in SWAP if m != "Plata"]),
    ("divisas + oro (5)", ["Oro", "EUR/USD", "GBP/USD", "AUD/USD", "USD/JPY"]),
    ("solo divisas (4)", ["EUR/USD", "GBP/USD", "AUD/USD", "USD/JPY"]),
    ("las 3 baratas (3)", ["GBP/USD", "AUD/USD", "USD/JPY"]),
]


def cargar(nom):
    d = pd.read_csv(FICHERO[nom], index_col=0, parse_dates=True)
    s = pd.to_numeric(d["Close"], errors="coerce").dropna()
    return s[s > 0]


PRECIOS = {m: cargar(m) for m in FICHERO}


def pata(nom):
    """Serie diaria de la pata, con posicion dimensionada por volatilidad."""
    s = PRECIOS[nom]
    r_d = s.pct_change().dropna()
    vol = r_d.rolling(252).std() * np.sqrt(252)
    m = s.resample("ME").last()
    vol_m = vol.resample("ME").last()
    pos = {}
    for i in range(MIRADA + 1, len(m)):
        pas = m.iloc[i - 1] / m.iloc[i - 1 - MIRADA] - 1.0
        v = vol_m.iloc[i - 1]
        if pd.isna(pas) or pd.isna(v) or v <= 0:
            continue
        pos[m.index[i]] = float(np.clip(np.sign(pas) * (VOL_OBJETIVO / v),
                                        -TOPE, TOPE))
    if not pos:
        return None, None
    ps = pd.Series(pos).sort_index()
    pos_d = ps.reindex(r_d.index, method="bfill")
    return (pos_d * r_d).dropna(), pos_d.abs()


SERIES, EXPO, VOLS = {}, {}, {}
for m in FICHERO:
    r, e = pata(m)
    if r is None:
        continue
    SERIES[m] = r
    EXPO[m] = e
    VOLS[m] = PRECIOS[m].pct_change().dropna().std() * np.sqrt(252)


def resumen(r, per=252):
    r = pd.Series(r).dropna()
    mu, sd = r.mean() * per, r.std() * np.sqrt(per)
    return dict(n=len(r), mu=mu, sd=sd, sh=mu / sd if sd > 0 else np.nan,
                t=r.mean() / r.std() * np.sqrt(len(r)))


E = "=" * 84

print(E)
print("1. CARRY POR NOCIONAL CONTRA CARRY POR UNIDAD DE RIESGO")
print(E)
print("  %-10s%10s%9s%12s%14s" % ("mercado", "swap/año", "vol", "expo. media",
                                  "swap/vol"))
print("  " + "-" * 58)
coste = {}
for m in sorted(SWAP, key=lambda k: -SWAP[k] / VOLS[k]):
    cv = SWAP[m] / VOLS[m]
    coste[m] = cv
    print("  %-10s%9.1f%%%8.1f%%%11.2fx%13.3f"
          % (m, SWAP[m] * 100, VOLS[m] * 100, EXPO[m].mean(), cv))
print()
print("  La columna que decide es la ultima. Ordena distinto que la primera:")
print("  el oro paga 3,2% del nocional y EUR/USD 1,8%, pero por unidad de")
print("  riesgo cuestan casi lo mismo, porque EUR/USD necesita mas nocional.")

print()
print(E)
print("2. CADA UNIVERSO: SEÑAL, CARRY Y NETO")
print(E)
print("  %-20s%5s%7s%8s%7s%8s%9s%9s" %
      ("universo", "n", "dias", "Sharpe", "t", "vol", "carry $", "neto $"))
print("  " + "-" * 74)

RES = {}
for etq, uni in UNIVERSOS:
    uni = [m for m in uni if m in SERIES]
    if len(uni) < 2:
        continue
    # FALLO CORREGIDO. La primera version hacia dropna(how="all") y promediaba,
    # asi que las fechas en que solo cotizaba el S&P (1995-2005) entraban con
    # una cartera de UN mercado. Eso inflaba el Sharpe y hacia incomparables los
    # universos entre si. trend_cfd.py evita esto con MIN_MERCADOS=6.
    # Aqui se exige que TODOS los mercados del universo tengan dato, con lo que
    # todos los universos arrancan en la misma fecha (2006-05, que es cuando
    # empiezan Plata y AUD/USD) y la comparacion es homologable.
    D = pd.DataFrame({m: SERIES[m] for m in uni})
    D = D[D.notna().all(axis=1)]
    serie = D.mean(axis=1).dropna()
    r = resumen(serie)

    # Carry: la exposicion media por pata, sobre el nocional que implica, a la
    # tasa medida. Escalado a que la CARTERA rinda VOL_OBJETIVO_CARTERA.
    VOL_CART = 0.045
    lev = VOL_CART / r["sd"] if r["sd"] > 0 else 0.0
    carry = 0.0
    for m in uni:
        noc = CUENTA * lev * EXPO[m].mean() / len(uni)
        carry += noc * SWAP[m]
    bruto = CUENTA * r["mu"] * lev
    RES[etq] = dict(uni=uni, serie=serie, lev=lev, sh=r["sh"], t=r["t"],
                    sd=r["sd"] * lev, carry=carry, bruto=bruto)
    print("  %-20s%5d%7d%8.2f%7.2f%6.1f%%%9.0f%9.0f"
          % (etq, len(uni), len(serie), r["sh"], r["t"], r["sd"] * lev * 100,
             -carry, bruto - carry))

print()
print("  Escalado para que la cartera de la pata rinda 4,5% de volatilidad")
print("  anual, que es el optimo de P(cobro) de la Fase 12.")

print()
print(E)
print("3. LO QUE DE VERDAD SE NECESITA: DIAS CUALIFICADOS")
print(E)
print("  La firma pide 6 dias cerrando con >= +0,5%. El FOMC da 8 eventos al")
print("  año y el 53% alcanza el TP: 4,24 dias al año -> 17 meses.")
print()
print("  %-20s%12s%14s%16s" %
      ("universo", "dias/año", "con el FOMC", "meses a 6 dias"))
print("  " + "-" * 64)
FOMC_DIAS = 8 * 0.53
print("  %-20s%12.1f%14.1f%16.1f"
      % ("solo FOMC", 0.0, FOMC_DIAS, 6.0 / FOMC_DIAS * 12))
for etq in RES:
    R = RES[etq]
    d = R["serie"] * R["lev"]
    frac = float((d >= 0.005).mean())
    dias = frac * 252
    tot = dias + FOMC_DIAS
    print("  %-20s%12.1f%14.1f%16.1f"
          % (etq, dias, tot, 6.0 / tot * 12))

print()
print(E)
print("4. EL AVISO QUE HAY QUE LEER ANTES DE USAR LA TABLA 3")
print(E)
print("  Esa tabla supone que el dia cualificado se cuenta por CAMBIO DE")
print("  EQUITY, que es lo que hace planes/cobros_reales.py en su linea 225:")
print("     cual += (vivo & (pnl >= 0.005*CUENTA))   con pnl = equity - inicial")
print()
print("  Pero la Fase 13 razona lo contrario: dice que la pata continua 'casi")
print("  no realiza beneficio ningun dia' y que eso es 'una ventaja")
print("  estructural'. Eso solo tiene sentido si la regla mira el REALIZADO.")
print()
print("  Las dos lecturas dan respuestas opuestas:")
print("     por EQUITY    -> el trend aporta los dias de la tabla 3 y resuelve")
print("                      el problema; pero tambien infla el 'mejor dia' y")
print("                      aprieta la regla del 20%.")
print("     por REALIZADO -> el trend NO aporta casi ningun dia cualificado,")
print("                      porque rebalancea una vez al mes, y la tabla 3 es")
print("                      papel mojado. Haria falta una familia que CIERRE")
print("                      operaciones a menudo, que es otro diseño.")
print()
print("  Es la leccion de la Fase 12 —'leelas, no las deduzcas'— y la de la")
print("  Fase 9 —'verifica solo contra puntos donde las hipotesis divergen'.")
print("  Se resuelve mirando el panel de la firma tras un dia con la equity")
print("  arriba y nada cerrado. Hasta entonces, no se sabe que EA hace falta.")
print()
print("  Y el TECHO de la rama por realizado, para dimensionar el riesgo de")
print("  equivocarse: el trend rebalancea UNA VEZ AL MES, asi que cierra")
print("  posiciones ~12 dias al año. Ese es el maximo absoluto de dias")
print("  cualificados que podria aportar, y solo los rebalanceos que realicen")
print("  >= +0,5% cuentan. O sea que la tabla 3 pasaria de ~9,4 dias/año a")
print("  algo entre 0 y 12, probablemente cerca de 2-3. La diferencia entre")
print("  5 meses y 17 depende enteramente de esa lectura.")

print()
print(E)
print("5. LO QUE ESTO NO DICE")
print(E)
print("  El 'neto' de la tabla 2 es retorno bruto del trend menos carry. NO")
print("  incluye la mecanica de cobro de la Fase 14, que se queda con el")
print("  80-82% del beneficio generado, ni el riesgo de quemar la cuenta.")
print("  La Fase 15 ya comparo las dos configuraciones con todo dentro:")
print()
print("     sin plata   : recibido a 4 años 233 $ · P(cobra) 50,0% · P(quema) 7,0%")
print("     solo el FOMC: recibido a 4 años 509 $ · P(cobra) 89,5% · P(quema) 0,0%")
print()
print("  Con el objetivo 'maximizar lo recibido a 4 años', el FOMC solo GANA y")
print("  la decision de la Fase 15 era correcta. Lo que cambia ahora es el")
print("  objetivo: si lo que aprieta es el TIEMPO hasta el primer cobro, la")
print("  pata de trend sin plata pasa de 17 meses a ~5, y eso la Fase 15 no lo")
print("  estaba optimizando. Es un intercambio real, no un almuerzo gratis:")
print("  se paga con 7 puntos de probabilidad de ruina.")
