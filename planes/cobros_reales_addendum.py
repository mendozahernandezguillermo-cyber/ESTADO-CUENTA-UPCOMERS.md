"""
ADDENDUM A cobros_reales.py — dos cosas que el script principal dejo mal.

(A) LA PINZA. El EV no se hunde solo porque el tope sea bajo. Se hunde porque
    la regla del mejor dia y el tope tiran en direcciones opuestas:
      - el mejor dia <= 20% del beneficio del ciclo OBLIGA a acumular un
        segmento grande antes de poder pedir (unas 5 veces el dia mas grande),
      - el tope solo libera tope/SPLIT de ese segmento,
      - el resto queda atrapado PARA SIEMPRE.
    Se mide el beneficio del segmento en el momento de pedir y que fraccion
    de el sale de verdad.

(B) EL "COLCHON" NO ESTA MEDIDO. En el script principal compare
    P(quema | npag>0) contra P(quema | npag==0). Eso NO mide ningun colchon:
    condiciona sobre el resultado. Las cuentas sin cobro son, en su mayoria,
    las que se quemaron antes de poder cobrar. Es causalidad invertida.
    El test correcto es contrafactual, mismos caminos, misma semilla:
      real   : el atrapado se queda en el saldo
      barrido: el atrapado se retira del saldo y se pierde
    La diferencia de P(quema) entre esos dos SI es el valor del colchon.
"""
import importlib.util, sys
import numpy as np

# se reutiliza todo el aparato del script principal sin re-ejecutar sus prints
src = open("cobros_reales.py", encoding="utf-8").read()
src = src.split('E = "=" * 92')[0]
mod = {}
exec(compile(src, "cobros_reales.py", "exec"), mod)

RNG = mod["RNG"]; CUENTA = mod["CUENTA"]; DD = mod["DD"]; DD_DIA = mod["DD_DIA"]
SPLIT = mod["SPLIT"]; MIN_DIAS = mod["MIN_DIAS"]; MIN_BEN = mod["MIN_BEN"]
BEST = mod["BEST"]; MIN_SEGMENTO = mod["MIN_SEGMENTO"]; REF = mod["REF"]
FMIN = mod["FMIN"]; DIAS_REBAL = mod["DIAS_REBAL"]; CUOTA = mod["CUOTA"]
FEE_FIJA = mod["FEE_FIJA"]; FEE_PCT = mod["FEE_PCT"]; TOPES = mod["TOPES"]
N = mod["N"]
preparar = mod["preparar"]; bootstrap_par = mod["bootstrap_par"]


def simular2(g1, g2, sd, barrer_atrapado=False, traza=False, snaps=None,
             cola=False):
    """barrer_atrapado=True quita del saldo el beneficio no retirable.
    traza=True devuelve, del PRIMER cobro, el beneficio del segmento y
    cuanto de el salio.
    snaps=[d1,d2,...] guarda el acumulado recibido en esos dias, para poder
    desglosar año por año SOBRE LOS MISMOS CAMINOS en vez de restar medias de
    simulaciones distintas (que mezclaria ruido Monte Carlo con la señal)."""
    foto = {}
    n, dias = g1.shape
    bal = np.full(n, CUENTA); hwm = np.full(n, CUENTA)
    piso = np.full(n, CUENTA * (1 - DD))
    lock = np.zeros(n, bool); vivo = np.ones(n, bool)
    cual = np.zeros(n, int); mejor = np.zeros(n)
    ref_seg = np.full(n, CUENTA)
    recibido = np.zeros(n); atrapado = np.zeros(n)
    npag = np.zeros(n, int); d1 = np.full(n, -1)
    seg1 = np.full(n, np.nan); sal1 = np.full(n, np.nan)
    mej1 = np.full(n, np.nan); dias_cual1 = np.full(n, np.nan)
    f_trend = np.ones(n)
    paso0 = sd / np.sqrt(mod["SUB"])
    SUB = mod["SUB"]

    maxbal = np.full(n, CUENTA)          # equity maxima alcanzada, para saber
                                         # si NACUSD.c llega a entrar nunca
    snapset = set(snaps or ())
    for d in range(dias):
        maxbal = np.maximum(maxbal, bal)
        if d in snapset:
            foto[d] = recibido.copy()
        if not vivo.any():
            break
        ini = bal.copy()
        pdd = ini * (1 - DD_DIA)
        pdia = np.maximum(piso, pdd)
        f_now = np.clip((ini - piso) / CUENTA / REF, FMIN, 1.0)
        if d % DIAS_REBAL == 0:
            f_trend = f_now.copy()

        eq = ini + ini * g1[:, d] * f_now
        vivo = vivo & ~(vivo & (eq < pdia))
        hwm = np.where(vivo, np.maximum(hwm, eq), hwm)

        act = np.where(vivo)[0]
        eqf = eq.copy()
        if act.size:
            fa = f_trend[act]
            b = RNG.normal(0.0, paso0, size=(act.size, SUB)).cumsum(axis=1)
            k = np.arange(1, SUB + 1) / SUB
            br = (b - k[None, :] * b[:, -1:]) * fa[:, None] \
                 + k[None, :] * (g2[act, d] * fa)[:, None]
            cam = eq[act][:, None] + ini[act][:, None] * br
            pico = np.maximum.accumulate(np.maximum(cam, hwm[act][:, None]), 1)
            pa = np.where(lock[act][:, None],
                          np.maximum(piso[act][:, None], CUENTA),
                          np.maximum(piso[act][:, None], pico * (1 - DD)))
            pa = np.maximum(pa, pdd[act][:, None])
            vivo[act] = ~(cam < pa).any(1)
            eqf[act] = cam[:, -1]
            hwm[act] = np.maximum(hwm[act], pico[:, -1])

        vivo = vivo & ~(vivo & (eqf < pdia))
        pnl = eqf - ini
        bal = np.where(vivo, eqf, bal)
        hwm = np.where(vivo, np.maximum(hwm, bal), hwm)
        lock = lock | (vivo & (hwm * (1 - DD) >= CUENTA))
        piso = np.where(vivo & lock, np.maximum(piso, CUENTA),
                        np.where(vivo, np.maximum(piso, hwm * (1 - DD)), piso))

        cual = cual + (vivo & (pnl >= MIN_BEN * CUENTA))
        mejor = np.where(vivo, np.maximum(mejor, pnl), mejor)

        seg = bal - ref_seg
        pide = (vivo & (seg >= MIN_SEGMENTO) & (cual >= MIN_DIAS)
                & (mejor <= BEST * np.maximum(seg, 1e-9)))
        if not pide.any():
            continue
        idx = np.where(pide)[0]

        tope = np.array([TOPES[min(npag[i], len(TOPES) - 1)]
                         if npag[i] < len(TOPES) else 1e12 for i in idx])
        bruto = np.minimum(seg[idx] * SPLIT, tope)
        neto = np.maximum(bruto - FEE_FIJA - bruto * FEE_PCT, 0.0)
        recibido[idx] += neto
        sacado = bruto / SPLIT
        atr = np.maximum(seg[idx] - sacado, 0.0)
        atrapado[idx] += atr

        if traza:
            pr = idx[npag[idx] == 0]
            if pr.size:
                seg1[pr] = seg[pr]
                sal1[pr] = sacado[npag[idx] == 0]
                mej1[pr] = mejor[pr]
                dias_cual1[pr] = cual[pr]

        bal[idx] -= sacado
        if barrer_atrapado:
            bal[idx] -= atr          # se lo lleva el viento
        # LA LINEA QUE DECIDE TODO EL ANALISIS:
        #   cola=False (lectura A) -> el nuevo segmento arranca en el saldo
        #      actual, asi que el beneficio por encima del tope pasa a ser
        #      BASE y no vuelve a ser cobrable nunca. ATRAPADO.
        #   cola=True  (lectura B) -> el segmento se mide siempre contra el
        #      saldo inicial, asi que lo no cobrado sigue siendo cobrable en
        #      los siguientes ciclos. EN COLA, no atrapado.
        ref_seg[idx] = CUENTA if cola else bal[idx]
        d1[idx] = np.where(d1[idx] < 0, d, d1[idx])
        npag[idx] += 1
        cual[idx] = 0
        mejor[idx] = 0.0

        res = idx[npag[idx] == len(TOPES)]
        if res.size:
            bal[res] = CUENTA; hwm[res] = CUENTA
            piso[res] = CUENTA * (1 - DD); lock[res] = False
            ref_seg[res] = CUENTA

    for s in snapset:                    # si todos murieron antes del corte
        foto.setdefault(s, recibido.copy())
    return dict(maxbal=maxbal, neto=recibido - CUOTA, npag=npag, quemada=~vivo,
                atrapado=atrapado, bal=bal, recibido=recibido, d1=d1,
                seg1=seg1, sal1=sal1, mej1=mej1, dc1=dias_cual1, foto=foto)


# ---8<--- INFORME (todo lo de abajo son prints; otros scripts importan arriba)
E = "=" * 92
print(E)
print("(A) LA PINZA: la regla del mejor dia infla el segmento, el tope lo confisca")
print(E)
print(f"  {'TP':>5}{'mejor dia':>12}{'segmento':>11}{'x mejor dia':>13}"
      f"{'liberado':>11}{'atrapado':>11}{'% liberado':>12}")
print("  " + "-" * 80)
for tp in (30.0, 40.0, 50.0, 80.0):
    b1, b2, _ = preparar(tp)
    g1, g2 = bootstrap_par(b1, b2, 504, N)
    r = simular2(g1, g2, b2.std(), traza=True)
    m = ~np.isnan(r["seg1"])
    s, sa, mj = r["seg1"][m], r["sal1"][m], r["mej1"][m]
    print(f"  {tp:>4.0f}{np.median(mj):>11,.0f}${np.median(s):>10,.0f}$"
          f"{np.median(s/np.maximum(mj,1e-9)):>13.1f}"
          f"{np.median(sa):>10,.0f}${np.median(s-sa):>10,.0f}$"
          f"{np.median(sa/np.maximum(s,1e-9)):>11.0%}")
print()
print("  El tope del 1er tramo libera como maximo 250/0.90 = 277,8 $ de saldo.")
print("  Todo lo que el mejor dia obligue a acumular por encima de eso se pierde.")

print()
print(E)
print("(B) EL COLCHON, AHORA CONTRAFACTUAL (mismos caminos, misma semilla)")
print(E)
print(f"  {'horizonte':<12}{'variante':<26}{'P(quema)':>10}{'EV anual':>11}"
      f"{'saldo final':>13}")
print("  " + "-" * 74)
for anios in (2, 5):
    b1, b2, _ = preparar(50.0)
    est = RNG.bit_generator.state
    fila = []
    for barrer, etiq in ((False, "atrapado se queda"), (True, "atrapado se barre")):
        RNG.bit_generator.state = est
        g1, g2 = bootstrap_par(b1, b2, int(252 * anios), N)
        RNG.bit_generator.state = est
        r = simular2(g1, g2, b2.std(), barrer_atrapado=barrer)
        fila.append((etiq, r))
        print(f"  {(str(anios)+' años') if not barrer else '':<12}{etiq:<26}"
              f"{r['quemada'].mean():>10.1%}{r['neto'].mean()/anios:>10,.0f}$"
              f"{r['bal'].mean():>12,.0f}$")
    dq = fila[1][1]['quemada'].mean() - fila[0][1]['quemada'].mean()
    de = (fila[0][1]['neto'].mean() - fila[1][1]['neto'].mean()) / anios
    print(f"      -> el colchon vale {dq:+.1%} de P(quema) y {de:+,.0f} $/año de EV")
    print()

print("  Y el numero que di antes, para que quede tachado:")
b1, b2, _ = preparar(50.0)
g1, g2 = bootstrap_par(b1, b2, 252 * 5, N)
r = simular2(g1, g2, b2.std())
v = r["npag"] > 0
print(f"     P(quema | hubo cobro) = {r['quemada'][v].mean():.1%}   "
      f"P(quema | no hubo) = {r['quemada'][~v].mean():.1%}")
print("     Esa brecha es SELECCION, no proteccion: casi todas las cuentas")
print("     sin cobro son cuentas que se quemaron antes de poder pedirlo.")
