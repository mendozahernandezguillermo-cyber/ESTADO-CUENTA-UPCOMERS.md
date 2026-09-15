#!/usr/bin/env python3
"""
¿MERECE LA PENA MONTAR ESTA CARTERA EN DARWINEX ZERO?

Hay dos preguntas distintas y conviene no mezclarlas:

  1. ¿Es un vehiculo de INGRESOS competitivo contra la cuenta prop?
  2. ¿Es un vehiculo de VALIDACION que aporte algo que la prop no aporta?

Para la primera hacen falta las condiciones comerciales (verificadas por web
en agosto de 2026):
  · suscripcion CFD ~50 $/mes, ~35-40 $/mes en plan anual
  · pagos mensuales: 65 $ una vez + 13 $/mes adicionales
  · comision de exito: 20% del beneficio del inversor, de los cuales
    15% para el proveedor del DARWIN y 5% para Darwinex
  · el motor de riesgo del DARWIN estandariza la exposicion a un VaR
    mensual del 6,5%
  · las asignaciones se compran (25k / 50k / 100k) o se ganan por ranking

Para la segunda hace falta algo que NO he medido nunca en todo el proyecto:
la CORRELACION DE LA CARTERA CON EL MERCADO. Y es decisiva, porque:
  · el D-Score de Darwinex penaliza explicitamente la correlacion con el
    mercado (un inversor no paga un 20% por beta que puede comprar gratis);
  · las DOS patas de esta cartera son estructuralmente LARGAS de acciones:
    la #1 compra NAS100 siempre, y la #2 lleva momentum de 12 meses en
    SPY y QQQ, que en un mercado alcista esta largo casi siempre.
Si la correlacion es alta, el DARWIN puntuara mal por construccion y todo
el analisis de ingresos sobra.
"""
import numpy as np
import pandas as pd

# ------------------------------------------------------- datos
A = pd.read_csv("../trend/serie_cfd.csv", index_col=0, parse_dates=True)
SPY = pd.read_csv("../trend/datos/SPY.csv", index_col=0, parse_dates=True)
spy = pd.to_numeric(SPY["Close"], errors="coerce").dropna().pct_change()

w2 = 0.30
w1 = 1.0 - w2
A["cartera"] = w1 * A["s1"] + w2 * A["s2"]
D = pd.DataFrame({"s1": A["s1"], "s2": A["s2"], "cartera": A["cartera"],
                  "spy": spy}).dropna()

E = "=" * 86
print(E)
print("LO QUE NUNCA HABIA MEDIDO: CORRELACION CON EL MERCADO")
print(E)
print(f"  {len(D):,} dias comunes   {D.index.min().date()} -> {D.index.max().date()}")
print()
print(f"  {'serie':<24}{'corr con SPY':>14}{'beta':>9}{'R2':>8}"
      f"{'% dias largo':>14}")
print("  " + "-" * 69)
for c, nom in (("s1", "#1 pre-FOMC"), ("s2", "#2 trend"),
               ("cartera", "CARTERA 70/30")):
    r = D[c].corr(D["spy"])
    beta = np.polyfit(D["spy"], D[c], 1)[0]
    act = D[D[c] != 0]
    # signo de la exposicion aproximado por el signo del retorno frente al SPY
    print(f"  {nom:<24}{r:>+14.3f}{beta:>9.3f}{r*r:>8.3f}", end="")
    if c == "s1":
        print(f"{'100% (siempre largo)':>14}")
    else:
        # el trend: se estima el signo con la regresion movil de 63 dias
        cov = D[c].rolling(63).cov(D["spy"])
        print(f"{(cov > 0).mean():>13.0%}")

# correlacion condicional: solo los dias malos del mercado
print()
mal = D[D["spy"] < D["spy"].quantile(0.05)]
print(f"  En el 5% de dias PEORES del SPY ({len(mal)} dias):")
for c, nom in (("s1", "#1 pre-FOMC"), ("s2", "#2 trend"),
               ("cartera", "CARTERA")):
    print(f"    {nom:<22}media {mal[c].mean():>+8.3%}   "
          f"contra su media normal {D[c].mean():>+8.4%}")

print()
print("  Lectura: lo que importa para el D-Score no es solo la correlacion")
print("  media, es si la estrategia acompaña al mercado cuando cae.")

# ------------------------------------------------------- el DARWIN
print()
print(E)
print("EL DARWIN: RETORNO ESPERADO TRAS LA ESTANDARIZACION DE RIESGO")
print(E)
vol_cart = D["cartera"].std() * np.sqrt(252)
sharpe = D["cartera"].mean() / D["cartera"].std() * np.sqrt(252)
RECORTE = 0.252            # recorte de Sharpe por costes, del marco general
sharpe_neto = sharpe - RECORTE

# VaR mensual 6,5% al 95% -> vol mensual = 6,5/1,645
vol_mes_darwin = 6.5 / 1.645
vol_darwin = vol_mes_darwin * np.sqrt(12) / 100.0

print(f"  Sharpe bruto de la cartera        : {sharpe:>7.2f}")
print(f"  menos el recorte por costes       : {-RECORTE:>7.2f}")
print(f"  Sharpe neto que uso               : {sharpe_neto:>7.2f}")
print(f"  vol de la cartera tal cual        : {vol_cart:>7.2%}")
print(f"  vol a la que Darwinex la escala   : {vol_darwin:>7.2%}"
      f"   (VaR mensual 6,5% al 95%)")
print(f"  -> retorno anual esperado del DARWIN: {sharpe_neto*vol_darwin:>6.2%}")
ret_darwin = sharpe_neto * vol_darwin

print()
print("  OJO: escalar de %.1f%% a %.1f%% de volatilidad multiplica la"
      % (vol_cart * 100, vol_darwin * 100))
print("  exposicion por %.2f. El peor dia historico de la cartera pasa de"
      % (vol_darwin / vol_cart))
print("  %.2f%% a %.2f%%." % (D["cartera"].min() * 100,
                              D["cartera"].min() * vol_darwin / vol_cart * 100))

# ------------------------------------------------------- economia
print()
print(E)
print("ECONOMIA: INGRESO ANUAL SEGUN EL CAPITAL ASIGNADO")
print(E)
FEE = 0.15                      # 15% para el proveedor del DARWIN
coste_mes = 50.0 + 13.0         # suscripcion + modulo de pagos mensuales
coste_ano_mensual = coste_mes * 12
coste_ano_anual = (40.0 + 13.0) * 12

print(f"  comision para el proveedor    : {FEE:.0%} del beneficio del inversor")
print(f"  coste con plan mensual        : {coste_ano_mensual:>8,.0f} $/año")
print(f"  coste con plan anual          : {coste_ano_anual:>8,.0f} $/año")
print(f"  retorno del DARWIN            : {ret_darwin:>8.2%}")
print()
print(f"  {'AUM asignado':>14}{'beneficio inversor':>20}{'tu 15%':>12}"
      f"{'neto plan anual':>18}")
print("  " + "-" * 64)
for aum in (0, 25_000, 50_000, 100_000, 250_000, 500_000, 1_000_000):
    ben = aum * ret_darwin
    tuyo = ben * FEE
    print(f"  {aum:>14,}{ben:>20,.0f}{tuyo:>12,.0f}"
          f"{tuyo - coste_ano_anual:>18,.0f}")

be = coste_ano_anual / (ret_darwin * FEE)
print(f"\n  AUM de EQUILIBRIO (plan anual): {be:>11,.0f} $")
print(f"  AUM de equilibrio (plan mensual): {coste_ano_mensual/(ret_darwin*FEE):>10,.0f} $")

# ------------------------------------------------------- comparativa
print()
print(E)
print("CONTRA LA CUENTA PROP, EN EFECTIVO DESEMBOLSADO")
print(E)
EV_UPCOMERS = 765.0     # 25K, DD 7%, con el escalado del Guardian
print(f"  {'vehiculo':<34}{'coste año 1':>13}{'EV año 1':>11}{'ratio':>9}")
print("  " + "-" * 67)
print(f"  {'Upcomers 25K (cuota unica 50 $)':<34}{50:>13,.0f}"
      f"{EV_UPCOMERS:>11,.0f}{EV_UPCOMERS/50:>8.1f}x")
print(f"  {'Upcomers x8 con los mismos 400 $':<34}{400:>13,.0f}"
      f"{8*EV_UPCOMERS:>11,.0f}{8*EV_UPCOMERS/400:>8.1f}x")
for aum, etq in ((0, "sin asignacion"), (50_000, "con 50k asignados"),
                 (100_000, "con 100k asignados")):
    ing = aum * ret_darwin * FEE
    print(f"  {'Darwinex Zero, ' + etq:<34}{coste_ano_anual:>13,.0f}"
          f"{ing:>11,.0f}{ing/coste_ano_anual:>8.1f}x")

print()
print("  Y la diferencia que no sale en la tabla: la cuenta prop se reinicia")
print("  al saldo inicial en cada cobro, asi que NUNCA COMPONE. Los 765 $ son")
print("  765 $ para siempre. El AUM de un DARWIN si puede crecer.")

# ------------------------------------------------------- valor de validacion
print()
print(E)
print("EL OTRO LADO: ¿CUANTO TARDA EN DECIR ALGO?")
print(E)
print("  Con Sharpe neto %.2f, el error estandar del Sharpe estimado en T años" % sharpe_neto)
print("  es aprox. raiz((1+s^2/2)/T). Meses hasta poder distinguirlo de cero:")
print()
print(f"  {'meses':>7}{'SE del Sharpe':>16}{'t esperado':>13}{'¿t>2?':>8}")
print("  " + "-" * 44)
for meses in (6, 12, 18, 24, 36, 48, 60):
    T = meses / 12.0
    se = np.sqrt((1 + sharpe_neto**2 / 2) / T)
    t = sharpe_neto / se
    print(f"  {meses:>7}{se:>16.2f}{t:>13.2f}{'SI' if t > 2 else 'no':>8}")
print()
print("  Esto vale para CUALQUIER vehiculo: es el tiempo que tarda el mercado")
print("  en confirmar o refutar la ventaja, y no se puede acelerar con dinero.")
