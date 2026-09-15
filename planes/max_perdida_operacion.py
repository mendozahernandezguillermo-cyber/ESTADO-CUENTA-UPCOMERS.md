"""
LA TERCERA REGLA DE MUERTE QUE NO HABIAMOS MODELADO: MAX SINGLE TRADE LOSS.

Todo mi analisis supone que la cuenta solo puede morir por dos vias: el
trailing del 7% y el diario del 4%. La documentacion de Upcomers dice que hay
una TERCERA, y es de tipo HARD BREACH:

  "Which Instant Funding Program Should I Choose": Vanguard = "2% single trade
   loss, 7% max drawdown"
  "Soft breach vs hard breach": la cuenta falla y se cierra en el momento en que
   una sola operacion supera el limite, aunque la cuenta sea rentable.

Y nuestro Guardian esta configurado con InpMaxPerdidaPosPct = 3.0, que NO
protegeria de un limite del 2%.

El problema concreto: la #1 se dimensiona a 1,47% de riesgo para un stop de
80 bp. Pero el stop NO se respeta en los huecos. El peor relleno historico fue
-133,4 bp, que a esa escala son 2,45% de la cuenta. O sea HARD BREACH.

Se mide sobre los 117 eventos reales en M1, de dos formas, porque no esta claro
si el limite se evalua sobre la perdida CERRADA o sobre la flotante maxima:
  (a) perdida al cerrar  -> lectura benigna
  (b) perdida flotante maxima durante la vida de la operacion -> lectura dura
      ("1.5% per OPEN trade" sugiere esta)
"""
import numpy as np

ns = {"__name__": "addendum"}
exec(compile(open("cobros_reales_addendum.py", encoding="utf-8")
             .read().split("# ---8<--- INFORME")[0],
             "cobros_reales_addendum.py", "exec"), ns)
mod = ns["mod"]
EVENTOS = mod["EVENTOS"]; STOP_BP = mod["STOP_BP"]

TP_BP = 40.0          # el cambio que se va a aplicar
RIESGO = 1.47         # % de cuenta que cuesta un movimiento de 80 bp
LIMITES = (2.0, 3.0)

filas = []
for anuncio, p_ent, seq in EVENTOS:
    sl = p_ent * (1 - STOP_BP / 1e4)
    tp = p_ent * (1 + TP_BP / 1e4)
    peor = 0.0                     # excursion adversa maxima, en bp
    sal = None
    for (t, o, h, l, c) in seq:
        peor = max(peor, (p_ent - l) / p_ent * 1e4)
        if l <= sl:
            sal = o if o <= sl else sl
            break
        if h >= tp:
            sal = tp
            break
    if sal is None:
        sal = seq[-1][4]
    cerrada_bp = max((p_ent - sal) / p_ent * 1e4, 0.0)
    filas.append((anuncio, cerrada_bp, peor))

cer = np.array([f[1] for f in filas])
flo = np.array([f[2] for f in filas])
# conversion a % de cuenta
cer_pct = cer / STOP_BP * RIESGO
flo_pct = flo / STOP_BP * RIESGO

E = "=" * 92
print(E)
print(f"LOS 117 EVENTOS CONTRA EL LIMITE DE PERDIDA POR OPERACION")
print(f"(TP {TP_BP:.0f} bp · stop {STOP_BP:.0f} bp · riesgo {RIESGO:.2f}% de la cuenta)")
print(E)
print(f"  {'medida':<34}{'peor bp':>10}{'peor % cuenta':>15}")
print("  " + "-" * 60)
print(f"  {'perdida al CERRAR':<34}{cer.max():>10.1f}{cer_pct.max():>14.2f}%")
print(f"  {'perdida FLOTANTE maxima':<34}{flo.max():>10.1f}{flo_pct.max():>14.2f}%")

print()
print(f"  {'limite':<10}{'umbral bp':>11}{'eventos que lo rompen':>24}"
      f"{'% de eventos':>14}")
print("  " + "-" * 60)
for lim in LIMITES:
    umbral = STOP_BP * lim / RIESGO
    n_cer = int((cer > umbral).sum())
    n_flo = int((flo > umbral).sum())
    print(f"  {'%.1f%% cerrada' % lim:<10}{umbral:>11.1f}{n_cer:>24}"
          f"{n_cer/len(cer):>13.1%}")
    print(f"  {'%.1f%% flotante' % lim:<10}{umbral:>11.1f}{n_flo:>24}"
          f"{n_flo/len(flo):>13.1%}")

print()
print(E)
print("PROBABILIDAD DE HARD BREACH POR ESTA VIA")
print(E)
EV_ANIO = 8.0          # eventos FOMC por año
print(f"  {'limite':<18}{'P(por evento)':>15}{'P(en 1 año)':>14}"
      f"{'P(en 4 años)':>15}")
print("  " + "-" * 62)
for lim in LIMITES:
    umbral = STOP_BP * lim / RIESGO
    for nom, arr in (("cerrada", cer), ("flotante", flo)):
        p = (arr > umbral).mean()
        print(f"  {'%.1f%% · %s' % (lim, nom):<18}{p:>15.2%}"
              f"{1-(1-p)**EV_ANIO:>14.1%}{1-(1-p)**(EV_ANIO*4):>15.1%}")

print()
print(E)
print("¿A QUE RIESGO HAY QUE BAJAR PARA QUE NINGUN EVENTO HISTORICO ROMPA?")
print(E)
print(f"  {'limite':<10}{'riesgo max':>12}{'contra 1,47% actual':>22}"
      f"{'EV/año estimado':>18}")
print("  " + "-" * 64)
for lim in LIMITES:
    for nom, arr in (("cerrada", cer), ("flotante", flo)):
        r_max = lim * STOP_BP / arr.max()
        factor = r_max / RIESGO
        print(f"  {'%.1f%% %s' % (lim, nom):<10}{r_max:>11.2f}%"
              f"{factor:>21.2f}x{332*factor:>17,.0f}$")
print()
print("  (el EV se escala aprox. lineal con el riesgo a estos niveles; es una")
print("   estimacion de orden de magnitud, no una medicion del pipeline)")

print()
print(E)
print("LOS PEORES 8 EVENTOS HISTORICOS")
print(E)
orden = sorted(filas, key=lambda f: -f[2])[:8]
print(f"  {'fecha':<14}{'cerrada bp':>12}{'flotante bp':>13}"
      f"{'% cuenta cerr':>15}{'% cuenta flot':>15}")
print("  " + "-" * 70)
for a, c, f_ in orden:
    print(f"  {str(a):<14}{c:>12.1f}{f_:>13.1f}"
          f"{c/STOP_BP*RIESGO:>14.2f}%{f_/STOP_BP*RIESGO:>14.2f}%")
