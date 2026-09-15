"""
¿QUE CUESTA SACAR EL NASDAQ DE LA CESTA DEL TREND?

MOTIVO, QUE NO ES ESTADISTICO SINO DE CUMPLIMIENTO
NACUSD.c esta en la lista del trend Y es el simbolo de la estrategia #1. Si el
trend se pone CORTO en NACUSD.c y llega un evento FOMC, la #1 abre un LARGO en
el mismo instrumento: posiciones opuestas en el mismo simbolo, que es
exactamente lo que Upcomers prohibe incluso dentro de una sola cuenta. Serian
~17 horas, 8 veces al año, de forma repetida. Un patron, no un accidente.

Hoy no ocurre porque NACUSD.c se omite por granularidad (nocional/lote 291.886,
entra a partir de ~36.000 de equity). O sea que sacarlo de la lista HOY no
cambia una sola posicion: solo impide que entre en el futuro.

Lo que hay que medir es el coste de excluirlo PARA SIEMPRE, sabiendo que el
S&P 500 ya esta en la cesta y correlaciona mucho con el Nasdaq. Misma
metodologia que valido el universo B, sin tocar un solo parametro.
"""
import numpy as np
import pandas as pd
from scipy import stats

src = open("trend_cfd.py", encoding="utf-8").read().split('E = "=" * 86')[0]
ns = {"__name__": "cfd"}
exec(compile(src, "trend_cfd.py", "exec"), ns)
construir = ns["construir"]; resumen = ns["resumen"]
UNIV_B = ns["UNIV_B"]

UNIV_B7 = [m for m in UNIV_B if m != "Nasdaq 100"]

E = "=" * 88
print(E)
print("UNIVERSO B (8) CONTRA B SIN NASDAQ (7)")
print(E)
print(f"  B  ({len(UNIV_B)}): {', '.join(UNIV_B)}")
print(f"  B7 ({len(UNIV_B7)}): {', '.join(UNIV_B7)}")

series = {}
for etq, u in (("B", UNIV_B), ("B7", UNIV_B7)):
    T, sd = construir(u)
    series[etq] = sd

print()
print(f"  {'periodo':<14}{'universo':<10}{'dias':>7}{'vol':>8}"
      f"{'retorno':>10}{'Sharpe':>9}{'t':>8}")
print("  " + "-" * 68)
for nom, desde in (("2010-2026", "2010-01-01"), ("2018-2026", "2018-01-01"),
                   ("todo", "1900-01-01")):
    for etq in ("B", "B7"):
        s = series[etq]
        s = s[s.index >= desde]
        r = resumen(s, per=252)
        if r is None:
            continue
        print(f"  {nom if etq=='B' else '':<14}{etq:<10}{r['n']:>7}"
              f"{r['sd']:>7.1%}{r['mu']:>9.1%}{r['sh']:>9.2f}{r['t']:>8.2f}")
    print()

print(E)
print("¿SE PIERDE DIVERSIFICACION DE VERDAD?")
print(E)
a, b = series["B"].align(series["B7"], join="inner")
print(f"  correlacion entre las dos series diarias : {a.corr(b):>8.4f}")
d = (a - b).dropna()
print(f"  diferencia media diaria (B menos B7)     : {d.mean()*252:>8.2%} anual")
print(f"  t de esa diferencia                      : "
      f"{d.mean()/d.std()*np.sqrt(len(d)):>8.2f}")

sp = ns["PRECIOS"]["S&P 500"].pct_change().dropna()
nq = ns["PRECIOS"]["Nasdaq 100"].pct_change().dropna()
x, y = sp.align(nq, join="inner")
print(f"  correlacion diaria S&P 500 / Nasdaq 100  : {x.corr(y):>8.4f}")
print()
print("  Si las dos series de cartera correlacionan >0,99 y la diferencia no")
print("  tiene t, el Nasdaq no aportaba diversificacion: el S&P ya cubria ese")
print("  factor. Sacarlo seria gratis y ademas resuelve el problema de hedging.")
