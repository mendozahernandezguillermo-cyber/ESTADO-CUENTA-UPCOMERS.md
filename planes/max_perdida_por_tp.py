"""
¿DE DONDE SALIA EL -133,4 bp Y CUANTO MARGEN TENEMOS DE VERDAD?

En el protocolo consta "peor evento con relleno real -133,4 bp". Con TP 40 bp
la medicion da 99,0 bp cerrada y 108,2 flotante. No cuadra, y la diferencia
decide si estamos rompiendo un limite duro o no.

Hipotesis: el take profit TRUNCA los caminos malos. Un evento que primero sube
40 bp cierra en beneficio y nunca llega a caer 133. Con un TP mas ancho la
posicion sigue abierta y queda expuesta mas tiempo. Si es asi, el TP no solo
sube el EV: REDUCE LA COLA, y el usuario esta ahora mismo en la configuracion
mas expuesta de las dos.

Se mide el peor caso por TP, contra el limite duro de perdida por operacion.
"""
import numpy as np

ns = {"__name__": "addendum"}
exec(compile(open("cobros_reales_addendum.py", encoding="utf-8")
             .read().split("# ---8<--- INFORME")[0],
             "cobros_reales_addendum.py", "exec"), ns)
mod = ns["mod"]
EVENTOS = mod["EVENTOS"]; STOP_BP = mod["STOP_BP"]
preparar = mod["preparar"]


def peores(tp_bp):
    cer, flo = [], []
    for anuncio, p_ent, seq in EVENTOS:
        sl = p_ent * (1 - STOP_BP / 1e4)
        tp = p_ent * (1 + tp_bp / 1e4) if tp_bp else None
        peor = 0.0
        sal = None
        for (t, o, h, l, c) in seq:
            peor = max(peor, (p_ent - l) / p_ent * 1e4)
            if l <= sl:
                sal = o if o <= sl else sl
                break
            if tp is not None and h >= tp:
                sal = tp
                break
        if sal is None:
            sal = seq[-1][4]
        cer.append(max((p_ent - sal) / p_ent * 1e4, 0.0))
        flo.append(peor)
    return np.array(cer), np.array(flo)


E = "=" * 94
print(E)
print("PEOR CASO POR TAKE PROFIT  ·  limite duro de Vanguard CFD = 2% (por confirmar)")
print(E)
print(f"  {'TP':>7}{'riesgo':>9}{'peor cerr':>11}{'peor flot':>11}"
      f"{'% cuenta':>11}{'margen al 2%':>14}{'ratio':>8}")
print("  " + "-" * 74)
for tp in (30.0, 40.0, 50.0, 60.0, 80.0, None):
    _, _, rg = preparar(tp if tp else 80.0)
    cer, flo = peores(tp)
    pct = flo.max() / STOP_BP * rg
    print(f"  {(str(int(tp)) if tp else 'sin TP'):>7}{rg:>8.2f}%"
          f"{cer.max():>11.1f}{flo.max():>11.1f}{pct:>10.2f}%"
          f"{2.0-pct:>13.2f}%{2.0/pct:>8.2f}x")

print()
print("  ratio = cuantas veces cabe el peor caso historico dentro del limite.")
print("  Por debajo de 1,00 la cuenta MUERE por hard breach en ese evento.")

print()
print(E)
print("EL PROBLEMA DE FONDO: ESTO NO SE PUEDE VIGILAR, SOLO DIMENSIONAR")
print(E)
print("  El limite se rompe EN EL TICK, no al cerrar. En un hueco el precio pasa")
print("  por encima del stop y del umbral del Guardian a la vez. Ningun software")
print("  puede evitarlo: cuando el EA reacciona, el breach ya esta registrado.")
print("  La unica defensa real es el TAMAÑO.")
print()
print("  Y el peor de 117 eventos es un mal estimador de la cola. Con margen:")
print(f"  {'factor de seguridad':<24}{'riesgo permitido':>18}{'EV/año aprox':>16}")
print("  " + "-" * 58)
_, flo50 = peores(50.0)
_, _, rg50 = preparar(50.0)
peor_bp = flo50.max()
for fac, nom in ((1.00, "ninguno (al filo)"), (1.25, "25%"),
                 (1.50, "50%"), (2.00, "100%")):
    r = 2.0 * STOP_BP / peor_bp / fac
    print(f"  {nom:<24}{r:>17.2f}%{332*r/1.44:>15,.0f}$")
print()
print("  (EV escalado linealmente desde los 332 $/año medidos a 1,44% de riesgo)")
