"""
¿CONVIENE MAS FTMO 2-STEP QUE LA CUENTA UPCOMERS?

Reglas confirmadas en ftmo.com (2-Step, 25K = 250 EUR reembolsables):
  Fase 1  objetivo +10%   ·   Fase 2  objetivo +5%
  perdida diaria maxima      5%
  perdida maxima maxima     10% ESTATICA sobre el saldo inicial  <-- no es trailing
  dias minimos de trading    4 por fase (sin exigir +0,5% en cada uno)
  periodo de trading         ilimitado
  reembolso de la cuota      100% con la primera recompensa
  reparto                    hasta el 90%
  SIN TOPES DE COBRO y SIN regla del mejor dia en el 2-Step

Las tres diferencias que importan contra Upcomers:
  (+) desaparece la PINZA. Sin tope y sin regla del mejor dia, el 82% que se
      confiscaba se cobra. Este es el punto a favor y es enorme.
  (+) el limite maximo es ESTATICO al 90% del inicial, no un trailing del 7%
      sobre el pico. No hay ratchet: si subes un 5%, tienes un 15% de aire.
  (-) hay que ganar +10% y luego +5% ANTES de cobrar un dolar. Con una
      estrategia de 4,5% de vol anual y Sharpe ~1, eso es el coste dominante.

Se mide el pipeline completo: fase 1 -> fase 2 -> cuenta fondeada con cobros,
barriendo la vol objetivo, porque en el reto la vol optima NO es la misma que
en una cuenta ya fondeada: ahi hay una meta que alcanzar, no solo un suelo que
esquivar.
"""
import numpy as np

ns = {"__name__": "addendum"}
exec(compile(open("cobros_reales_addendum.py", encoding="utf-8")
             .read().split("# ---8<--- INFORME")[0],
             "cobros_reales_addendum.py", "exec"), ns)
mod = ns["mod"]
preparar = mod["preparar"]; RNG = mod["RNG"]
BLOQUE, SUB = mod["BLOQUE"], mod["SUB"]

CUENTA = 25_000.0
EURUSD = 1.16227                 # tipo real del broker, no una estimacion
CUOTA = 250.0 * EURUSD           # 290,57 $
OBJ = (0.10, 0.05)
MAXLOSS, DAILY = 0.10, 0.05
MIN_DIAS_FASE = 4
SPLIT = 0.90
CICLO_COBRO = 14                 # dias de mercado minimos entre recompensas
TOPE_DIAS = 252 * 12             # corte tecnico del "tiempo ilimitado"
N = 20_000


def caminos(x1, x2, dias, n):
    nb = int(np.ceil(dias / BLOQUE))
    ini = RNG.integers(0, len(x1) - BLOQUE, size=(n, nb))
    idx = (ini[:, :, None] + np.arange(BLOQUE)[None, None, :]
           ).reshape(n, -1)[:, :dias]
    return x1[idx], x2[idx]


def correr(x1, x2, sd, dias, modo, objetivo=None):
    """modo='reto'    -> devuelve (pasa, dia_en_que_paso, roto)
       modo='fondeada'-> devuelve (recibido, roto, n_cobros)
    Suelo ESTATICO al 90% del inicial en los dos modos."""
    n = x1.shape[0]
    bal = np.full(n, CUENTA)
    piso = np.full(n, CUENTA * (1 - MAXLOSS))     # estatico, nunca se mueve
    vivo = np.ones(n, bool)
    hecho = np.zeros(n, bool)
    dia_fin = np.full(n, -1)
    ndias = np.zeros(n, int)
    recibido = np.zeros(n); ncob = np.zeros(n, int)
    ult_cobro = np.zeros(n, int)
    paso0 = sd / np.sqrt(SUB)

    for d in range(dias):
        act = np.where(vivo & ~hecho)[0]
        if act.size == 0:
            break
        ini = bal.copy()
        pdia = np.maximum(piso, ini * (1 - DAILY))

        eq = ini.copy()
        eq[act] = ini[act] + ini[act] * x1[act, d]
        malo = act[eq[act] < pdia[act]]
        vivo[malo] = False
        act = np.array([i for i in act if vivo[i]], dtype=int)
        if act.size == 0:
            continue

        b = RNG.normal(0.0, paso0, size=(act.size, SUB)).cumsum(axis=1)
        k = np.arange(1, SUB + 1) / SUB
        br = (b - k[None, :] * b[:, -1:]) + k[None, :] * x2[act, d][:, None]
        cam = eq[act][:, None] + ini[act][:, None] * br
        lim = np.maximum(piso[act], pdia[act])[:, None]
        rompe = (cam < lim).any(1)
        vivo[act[rompe]] = False
        fin = act[~rompe]
        bal[fin] = cam[~rompe, -1]
        ndias[fin] += 1

        if modo == "reto":
            ok = fin[(bal[fin] >= CUENTA * (1 + objetivo))
                     & (ndias[fin] >= MIN_DIAS_FASE)]
            hecho[ok] = True
            dia_fin[ok] = d
        else:
            # cobro a demanda: todo el beneficio, sin tope, cada CICLO_COBRO
            pide = fin[(bal[fin] > CUENTA)
                       & (d - ult_cobro[fin] >= CICLO_COBRO)]
            if pide.size:
                ben = bal[pide] - CUENTA
                recibido[pide] += ben * SPLIT
                bal[pide] = CUENTA
                ult_cobro[pide] = d
                ncob[pide] += 1

    if modo == "reto":
        return hecho, dia_fin, ~vivo
    return recibido, ~vivo, ncob


E = "=" * 96
print(E)
print("FASE 1 (+10%) Y FASE 2 (+5%): ¿cuanto se tarda y con que probabilidad?")
print(E)
print(f"  {'vol':>6}{'riesgo/ev':>11}{'P(pasa F1)':>12}{'mediana F1':>12}"
      f"{'P(pasa F2)':>12}{'mediana F2':>12}{'P(pasa las 2)':>15}{'total':>10}")
print("  " + "-" * 90)
res = {}
for vol in (0.045, 0.07, 0.10, 0.14, 0.20):
    x1, x2, rg = preparar(40.0, w2=0.30, vol=vol)
    sd = x2.std()
    g1, g2 = caminos(x1, x2, TOPE_DIAS, N)
    p1, d1, q1 = correr(g1, g2, sd, TOPE_DIAS, "reto", OBJ[0])
    g1b, g2b = caminos(x1, x2, TOPE_DIAS, N)
    p2, d2, q2 = correr(g1b, g2b, sd, TOPE_DIAS, "reto", OBJ[1])
    m1 = np.median(d1[p1]) if p1.any() else np.nan
    m2 = np.median(d2[p2]) if p2.any() else np.nan
    res[vol] = (p1.mean(), m1, p2.mean(), m2, p1.mean() * p2.mean(), rg,
                x1, x2, sd)
    print(f"  {vol:>6.1%}{rg:>10.2f}%{p1.mean():>12.1%}{m1:>11.0f}d"
          f"{p2.mean():>12.1%}{m2:>11.0f}d{p1.mean()*p2.mean():>15.1%}"
          f"{(m1+m2)/252:>9.1f}a")

print()
print(E)
print("PIPELINE COMPLETO A 3 AÑOS: reto + reto + fondeada, neto de la cuota")
print(E)
print(f"  {'vol':>6}{'P(fondea)':>11}{'dias hasta':>12}{'años que':>10}"
      f"{'EV 3 años':>11}{'EV/año':>9}{'P(quema tras':>14}")
print(f"  {'':>6}{'':>11}{'fondear':>12}{'quedan':>10}{'':>11}{'':>9}{'fondear)':>14}")
print("  " + "-" * 82)
for vol, (pp1, mm1, pp2, mm2, pboth, rg, x1, x2, sd) in res.items():
    if np.isnan(mm1) or np.isnan(mm2):
        continue
    dias_reto = int(mm1 + mm2)
    resto = max(252 * 3 - dias_reto, 0)
    if resto > 20:
        gg1, gg2 = caminos(x1, x2, resto, N)
        rec, roto, nc = correr(gg1, gg2, sd, resto, "fondeada")
        # solo cobra quien pasa las dos fases; la cuota se reembolsa al 1er cobro
        cobra = rec > 0
        ev = pboth * (rec.mean() + CUOTA * cobra.mean()) - CUOTA
        pq = roto.mean()
    else:
        ev, pq = -CUOTA, np.nan
    print(f"  {vol:>6.1%}{pboth:>11.1%}{dias_reto:>11}d{resto/252:>9.2f}a"
          f"{ev:>10,.0f}${ev/3:>8,.0f}${pq:>14.1%}")

print()
print(E)
print("COMPARACION DIRECTA CONTRA UPCOMERS (25K, ambos, 3 años)")
print(E)
print(f"  {'vehiculo':<34}{'coste inicial':>15}{'EV 3 años':>12}{'EV/año':>10}")
print("  " + "-" * 72)
print(f"  {'Upcomers Vanguard 7% (en vivo)':<34}{'50 $':>15}{808:>11,.0f}${808/3:>9,.0f}$")
print(f"  {'FTMO 2-Step 25K':<34}{CUOTA:>14,.0f}${'ver arriba':>12}{'':>10}")
