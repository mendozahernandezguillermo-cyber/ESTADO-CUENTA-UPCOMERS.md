"""
FTMO 2-STEP CONTRA UPCOMERS: PIPELINE CONTINUO, UN SOLO RELOJ.

Corrige dos fallos de ftmo_2step.py:
  1. Alli use la MEDIANA de dias para pasar cada fase y le di a todos los
     caminos la misma ventana fondeada. Eso regala tiempo fondeado a los
     caminos lentos y sobreestima el EV. Aqui cada camino lleva su propio
     reloj: fase 1 -> fase 2 -> fondeada, sobre el mismo calendario.
  2. Alli no habia recompra tras romper la cuenta. Aqui, si se rompe, se paga
     otra cuota y se vuelve a la fase 1, que es lo que uno haria de verdad.

Y añade la variable que decide de verdad: los DIAS DE TRADING. FTMO pide 4 dias
con operaciones por fase, y nuestro sistema solo ABRE ordenes ~20 veces al año
(8 eventos FOMC + 12 rebalanceos + latidos). O sea 4 dias de trading tardan
~2-3 meses, no 4 dias. Se modela como un suelo de 50 dias de mercado por fase.

Escenario adicional obligatorio: la clausula de 'gap trading' de FTMO prohibe
abrir operaciones cuando hay eventos macro programados que puedan afectar al
mercado. La #1 abre NASDAQ la tarde antes de un FOMC. Si FTMO la considera
prohibida, solo queda la #2. Se mide ese mundo tambien, porque es el que decide.
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
EURUSD = 1.16227
CUOTA = 250.0 * EURUSD           # 290,57 $
OBJ = np.array([0.10, 0.05])
MAXLOSS, DAILY = 0.10, 0.05
MIN_MERCADO = 50                 # ~4 dias con ordenes a nuestro ritmo
SPLIT = 0.90
CICLO = 14
N = 20_000


def caminos(x1, x2, dias, n):
    nb = int(np.ceil(dias / BLOQUE))
    ini = RNG.integers(0, len(x1) - BLOQUE, size=(n, nb))
    idx = (ini[:, :, None] + np.arange(BLOQUE)[None, None, :]
           ).reshape(n, -1)[:, :dias]
    return x1[idx], x2[idx]


def pipeline(x1, x2, sd, dias, recomprar=True):
    """estado 0 = fase 1, 1 = fase 2, 2 = fondeada"""
    n = x1.shape[0]
    est = np.zeros(n, int)
    bal = np.full(n, CUENTA)
    piso = np.full(n, CUENTA * (1 - MAXLOSS))
    dfase = np.zeros(n, int)
    ult = np.zeros(n, int)
    recibido = np.zeros(n)
    pagado = np.full(n, CUOTA)
    nrotas = np.zeros(n, int)
    ncob = np.zeros(n, int)
    fuera = np.zeros(n, bool)          # rompio y no recompra
    d_fondeo = np.full(n, -1)
    paso0 = sd / np.sqrt(SUB)

    for d in range(dias):
        act = np.where(~fuera)[0]
        if act.size == 0:
            break
        ini = bal[act]
        pdia = np.maximum(piso[act], ini * (1 - DAILY))

        eq = ini + ini * x1[act, d]
        b = RNG.normal(0.0, paso0, size=(act.size, SUB)).cumsum(axis=1)
        k = np.arange(1, SUB + 1) / SUB
        br = (b - k[None, :] * b[:, -1:]) + k[None, :] * x2[act, d][:, None]
        cam = eq[:, None] + ini[:, None] * br
        rompe = (eq < pdia) | (cam < pdia[:, None]).any(1)

        idx_r = act[rompe]
        if idx_r.size:
            nrotas[idx_r] += 1
            if recomprar:
                est[idx_r] = 0
                bal[idx_r] = CUENTA
                piso[idx_r] = CUENTA * (1 - MAXLOSS)
                dfase[idx_r] = 0
                ult[idx_r] = d
                pagado[idx_r] += CUOTA
            else:
                fuera[idx_r] = True

        idx_v = act[~rompe]
        if idx_v.size == 0:
            continue
        bal[idx_v] = cam[~rompe, -1]
        dfase[idx_v] += 1

        en_reto = idx_v[est[idx_v] < 2]
        if en_reto.size:
            meta = CUENTA * (1 + OBJ[est[en_reto]])
            ok = en_reto[(bal[en_reto] >= meta)
                         & (dfase[en_reto] >= MIN_MERCADO)]
            if ok.size:
                est[ok] += 1
                bal[ok] = CUENTA
                piso[ok] = CUENTA * (1 - MAXLOSS)
                dfase[ok] = 0
                ult[ok] = d
                d_fondeo[ok] = np.where(est[ok] == 2, d, d_fondeo[ok])

        fon = idx_v[est[idx_v] == 2]
        if fon.size:
            pide = fon[(bal[fon] > CUENTA) & (d - ult[fon] >= CICLO)]
            if pide.size:
                recibido[pide] += (bal[pide] - CUENTA) * SPLIT
                bal[pide] = CUENTA
                ult[pide] = d
                ncob[pide] += 1

    # la cuota del 2-Step se reembolsa con la PRIMERA recompensa
    reemb = np.where(ncob > 0, CUOTA, 0.0)
    return dict(neto=recibido + reemb - pagado, recibido=recibido,
                pagado=pagado, ncob=ncob, nrotas=nrotas, est=est,
                d_fondeo=d_fondeo, fondeo=est >= 2)


E = "=" * 96
ANIOS = 3
print(E)
print(f"FTMO 2-STEP 25K · PIPELINE CONTINUO A {ANIOS} AÑOS · con recompra tras romper")
print(E)
print(f"  {'vol':>6}{'riesgo/ev':>11}{'P(fondea)':>11}{'mediana':>10}"
      f"{'cobros':>8}{'cuotas':>8}{'roturas':>9}{'EV neto':>10}{'EV/año':>9}{'mediana':>10}")
print(f"  {'':>6}{'':>11}{'':>11}{'fondeo':>10}{'':>8}{'pagadas':>8}"
      f"{'':>9}{'':>10}{'':>9}{'neto':>10}")
print("  " + "-" * 92)
best = None
for vol in (0.045, 0.06, 0.08, 0.10, 0.13, 0.17):
    x1, x2, rg = preparar(40.0, w2=0.30, vol=vol)
    g1, g2 = caminos(x1, x2, 252 * ANIOS, N)
    r = pipeline(g1, g2, x2.std(), 252 * ANIOS)
    df = r["d_fondeo"][r["d_fondeo"] >= 0]
    ev = r["neto"].mean()
    print(f"  {vol:>6.1%}{rg:>10.2f}%{r['fondeo'].mean():>11.1%}"
          f"{(np.median(df) if df.size else np.nan):>9.0f}d"
          f"{r['ncob'].mean():>8.2f}{r['pagado'].mean()/CUOTA:>8.2f}"
          f"{r['nrotas'].mean():>9.2f}{ev:>9,.0f}${ev/ANIOS:>8,.0f}$"
          f"{np.median(r['neto']):>9,.0f}$")
    if best is None or ev > best[0]:
        best = (ev, vol)

print()
print(f"  optimo de EV: vol {best[1]:.1%}  ->  {best[0]/ANIOS:,.0f} $/año")

print()
print(E)
print("EL MUNDO EN QUE FTMO PROHIBE LA #1 POR 'GAP TRADING' (solo queda el trend)")
print(E)
print(f"  {'vol':>6}{'P(fondea)':>11}{'cobros':>8}{'cuotas':>9}{'EV neto':>10}{'EV/año':>9}")
print("  " + "-" * 55)
for vol in (0.045, 0.08, 0.10, 0.13):
    x1, x2, _ = preparar(40.0, w2=1.00, vol=vol)   # w2=1 -> solo la #2
    g1, g2 = caminos(x1, x2, 252 * ANIOS, N)
    r = pipeline(g1, g2, x2.std(), 252 * ANIOS)
    ev = r["neto"].mean()
    print(f"  {vol:>6.1%}{r['fondeo'].mean():>11.1%}{r['ncob'].mean():>8.2f}"
          f"{r['pagado'].mean()/CUOTA:>9.2f}{ev:>9,.0f}${ev/ANIOS:>8,.0f}$")

print()
print(E)
print("SIN RECOMPRA: un solo intento, se pierde la cuota y se abandona")
print(E)
print(f"  {'vol':>6}{'P(fondea)':>11}{'EV neto':>10}{'EV/año':>9}{'P(acabar en perdida)':>22}")
print("  " + "-" * 60)
for vol in (0.045, 0.08, 0.10, 0.13):
    x1, x2, _ = preparar(40.0, w2=0.30, vol=vol)
    g1, g2 = caminos(x1, x2, 252 * ANIOS, N)
    r = pipeline(g1, g2, x2.std(), 252 * ANIOS, recomprar=False)
    ev = r["neto"].mean()
    print(f"  {vol:>6.1%}{r['fondeo'].mean():>11.1%}{ev:>9,.0f}${ev/ANIOS:>8,.0f}$"
          f"{(r['neto']<0).mean():>22.1%}")

print()
print(E)
print("VEREDICTO CONTRA UPCOMERS (3 años, misma estrategia, cuenta de 25K)")
print(E)
print(f"  {'vehiculo':<44}{'coste':>9}{'EV 3a':>10}{'EV/año':>9}")
print("  " + "-" * 72)
print(f"  {'Upcomers Vanguard 7% · vol 4,5% · TP 40 (en vivo)':<44}{'50 $':>9}"
      f"{808:>9,.0f}${269:>8,.0f}$")
