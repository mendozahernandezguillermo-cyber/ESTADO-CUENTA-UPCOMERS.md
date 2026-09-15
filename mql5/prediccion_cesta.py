#!/usr/bin/env python3
"""
CONTROL POSITIVO DEL CODIGO DE EA_Trend_Multi.

Calcula, con la misma aritmetica que el EA, lo que su informe de arranque
DEBE decir. Si el log del terminal no coincide, hay un bug en el EA (o los
datos del broker difieren de los de Yahoo, que tambien es informativo).

Se replica exactamente:
  · señal = cierre del mes -1 / cierre del mes -13  - 1
  · vol   = desviacion de los retornos diarios de las ultimas 252 barras D1
            cerradas, anualizada por raiz(252)
  · exposicion = signo x recorte(7,23% / vol, +-5) / max(activos, 8)
  · nocional   = exposicion x equity
  · lotes      = exposicion x equity x tickSize / (precio x tickValue)

AVISO SOBRE LOS DATOS: aqui se usan los sustitutos con los que se midio la
estrategia (SPY, QQQ, GLD, SLV y divisas al contado de Yahoo), no los CFD del
broker. Dos diferencias esperables:
  · SPY y QQQ vienen ajustados por dividendos y los CFD sobre indice no, asi
    que el retorno de 12 meses difiere en el dividendo (~1,3% en el S&P).
    Solo cambiaria la SEÑAL si el retorno estuviera a menos de eso de cero.
  · el nivel de precio del CFD puede llevar prima de rollover, lo que afecta
    a los lotes pero no a la señal ni a la volatilidad.
"""
import numpy as np
import pandas as pd

EQUITY = 24759.77
VOL_OBJ = 7.23 / 100.0
MIRADA = 12
TOPE = 5.0
DIAS_VOL = 252
MERCADOS_REF = 8

#  nombre CFD     fichero            contrato   precio aprox   lote min
CESTA = [
    ("SPX500", "../trend/datos/SPY.csv",     1.0,   None, 0.01),
    ("NAS100", "../trend/datos/QQQ.csv",     1.0,   None, 0.01),
    ("XAUUSD", "../trend/datos/GLD.csv",   100.0,   None, 0.01),
    ("XAGUSD", "../trend/datos/SLV.csv",  5000.0,   None, 0.01),
    ("EURUSD", "../trend/datos/EURUSDX.csv", 1e5,   None, 0.01),
    ("USDJPY", "../trend/datos/USDJPYX.csv", 1e5,   None, 0.01),
    ("GBPUSD", "../trend/datos/GBPUSDX.csv", 1e5,   None, 0.01),
    ("AUDUSD", "../trend/datos/AUDUSDX.csv", 1e5,   None, 0.01),
]

# nivel de precio real aproximado del CFD, para estimar lotes. El ETF NO vale
# como precio: SPY cotiza ~1/10 del S&P y GLD ~1/10 de la onza de oro.
PRECIO_CFD = {"SPX500": 6500.0, "NAS100": 24000.0, "XAUUSD": 3400.0,
              "XAGUSD": 39.0, "EURUSD": 1.16, "USDJPY": 148.0,
              "GBPUSD": 1.34, "AUDUSD": 0.65}


def analizar(path, mes_ref):
    """mes_ref = -1 usa el ultimo mes cerrado; -2 el anterior."""
    d = pd.read_csv(path, index_col=0, parse_dates=True)
    s = pd.to_numeric(d["Close"], errors="coerce").dropna()
    s = s[s > 0]
    m = s.resample("ME").last().dropna()

    # el mes en curso puede estar incompleto: se descarta si no ha cerrado
    ultimo = m.index[-1]
    if ultimo.month == s.index[-1].month and ultimo.year == s.index[-1].year:
        # el ultimo punto mensual corresponde al mes en curso
        cerrados = m.iloc[:-1] if s.index[-1].day < 28 else m
    else:
        cerrados = m

    i = len(cerrados) + mes_ref          # mes_ref = -1 -> ultimo cerrado
    if i - MIRADA < 0:
        return None
    p1 = cerrados.iloc[i]
    p13 = cerrados.iloc[i - MIRADA]
    r12 = p1 / p13 - 1.0
    fecha1, fecha13 = cerrados.index[i], cerrados.index[i - MIRADA]

    # volatilidad: 252 retornos diarios hasta la fecha del mes -1
    hasta = s[s.index <= fecha1]
    r_d = hasta.pct_change().dropna().iloc[-DIAS_VOL:]
    vol = r_d.std(ddof=1) * np.sqrt(252)
    return dict(r12=r12, vol=vol, p1=p1, p13=p13,
                f1=fecha1.date(), f13=fecha13.date(), n=len(r_d))


def tabla(mes_ref, titulo):
    datos = {}
    for nom, path, contrato, _, minl in CESTA:
        a = analizar(path, mes_ref)
        if a:
            datos[nom] = a

    f1 = list(datos.values())[0]["f1"]
    print("=" * 92)
    print(f"{titulo}  ->  mes -1 = {f1}")
    print("=" * 92)
    activos = len(datos)
    divisor = max(activos, MERCADOS_REF)
    print(f"  equity {EQUITY:,.2f}   mercados con datos {activos}   "
          f"divisor {divisor}")
    print(f"  señal = cierre {list(datos.values())[0]['f1']} / "
          f"cierre {list(datos.values())[0]['f13']} - 1")
    print()
    print(f"  {'simbolo':<9}{'ret 12m':>10}{'señal':>7}{'vol':>8}"
          f"{'exposic.':>10}{'nocional':>11}{'lotes est.':>12}{'estado':>12}")
    print("  " + "-" * 79)

    suma_bruta = 0.0
    for nom, path, contrato, _, minl in CESTA:
        if nom not in datos:
            print(f"  {nom:<9}{'sin datos':>10}")
            continue
        a = datos[nom]
        senal = 1.0 if a["r12"] >= 0 else -1.0
        e = senal * min(VOL_OBJ / a["vol"], TOPE)
        expo = e / divisor
        nocional = abs(expo) * EQUITY
        precio = PRECIO_CFD[nom]
        # Si la divisa BASE del par es el dolar (USDJPY), un lote son
        # 100.000 USD y NO 100.000 x precio. Es el error clasico del
        # nocional en FX y me lo acababa de comer.
        if nom.startswith("USD"):
            nocional_lote = contrato
        else:
            nocional_lote = contrato * precio
        lotes = nocional / nocional_lote
        suma_bruta += abs(expo)
        est = "OK" if lotes >= minl else "NO LLEGA"
        print(f"  {nom:<9}{a['r12']:>+9.1%}{senal:>7.0f}{a['vol']:>7.1%}"
              f"{expo:>+9.2%}{nocional:>11,.0f}{lotes:>12.4f}{est:>12}")

    print("  " + "-" * 79)
    print(f"  exposicion bruta total: {suma_bruta:.1%} de la equity")
    print(f"  (lotes estimados con precios aproximados del CFD: "
          f"{', '.join(f'{k} {v:g}' for k, v in PRECIO_CFD.items())})")
    print()


# Si lo pegas HOY (finales de agosto), la barra MN1 indice 1 de MT5 es JULIO,
# porque agosto todavia esta en curso. En el rebalanceo de septiembre pasara a
# ser agosto. Se dan las dos.
tabla(-2, "A) LO QUE DEBE DECIR TU LOG SI LO PEGAS HOY")
tabla(-1, "B) LO QUE USARA EN EL REBALANCEO DE SEPTIEMBRE")

print("=" * 92)
print("QUE COMPARAR CON TU LOG, Y QUE SIGNIFICA CADA DISCREPANCIA")
print("=" * 92)
print("""
  1. LA COLUMNA 'vol'  -> debe coincidir con un margen de 1-2 puntos. Si el
     broker da una vol muy distinta, o su historial D1 es corto o su serie
     tiene huecos. Es el numero mas fiable para detectar datos malos.

  2. LA COLUMNA 'señal' -> tiene que coincidir EXACTAMENTE, salvo que el
     retorno de 12 meses este muy cerca de cero. Si un signo no coincide y
     el retorno es grande, hay un bug en el indexado de las barras MN1.

  3. LA COLUMNA 'exposic.' -> debe coincidir a la centesima si vol y señal
     coinciden, porque es aritmetica pura.

  4. LA COLUMNA 'lotes'  -> aqui SI espero diferencias, porque he supuesto
     los precios y los tamaños de contrato. Lo que importa no es el numero
     exacto sino QUE SIMBOLOS SALEN COMO 'NO LLEGA AL LOTE MINIMO'.

  5. LAS COLUMNAS 'MN1' y 'D1' del log -> necesita 14 barras MN1 y 254 D1.
     Cualquier simbolo por debajo queda fuera de la cartera, y si quedan
     menos de 6 el EA no opera ningun mes.
""")
