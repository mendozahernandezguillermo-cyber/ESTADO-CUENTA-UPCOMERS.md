"""
"SI ME QUEDO COMO ESTOY AHORA, ¿ME DEJA DINERO EL AÑO 1?"

Configuracion EXACTA que esta corriendo: Upcomers Vanguard 25K, DD 7% trailing,
w2 30%, vol objetivo 4,5%, TP 50 bp (todavia no se ha cambiado a 40).

Cambio de marco importante: la cuota de 50 $ ya esta PAGADA. Es coste hundido.
La pregunta util no es el neto (que le resta esos 50 $ otra vez) sino cuanto
DINERO LLEGA AL BOLSILLO en los proximos 12 meses. Se reportan los dos.

Se da tambien la probabilidad acumulada de cobrar mes a mes, que es lo que de
verdad se quiere saber: no "cuanto en media" sino "para cuando".
"""
import numpy as np

ns = {"__name__": "addendum"}
exec(compile(open("cobros_reales_addendum.py", encoding="utf-8")
             .read().split("# ---8<--- INFORME")[0],
             "cobros_reales_addendum.py", "exec"), ns)
simular2 = ns["simular2"]; mod = ns["mod"]
preparar = mod["preparar"]; CUOTA = mod["CUOTA"]

N = 40_000
DIAS = 252
E = "=" * 92

print(E)
print("AÑO 1 CON LA CONFIGURACION QUE ESTA CORRIENDO  (TP 50 bp)")
print(E)
salida = {}
for tp, etiq in ((50.0, "tal cual (TP 50)"), (40.0, "si cambias a TP 40")):
    x1, x2, rg = preparar(tp)
    g1, g2 = mod["bootstrap_par"](x1, x2, DIAS, N)
    r = simular2(g1, g2, x2.std(), traza=True)
    salida[tp] = r
    bruto = r["recibido"]
    neto = r["neto"]
    print(f"\n  {etiq}")
    print(f"     dinero que LLEGA al bolsillo (media) : {bruto.mean():>8,.0f} $")
    print(f"     neto contando la cuota ya pagada     : {neto.mean():>8,.0f} $")
    print(f"     probabilidad de cobrar algo          : {(r['npag']>0).mean():>8.1%}")
    print(f"     probabilidad de NO cobrar nada       : {(r['npag']==0).mean():>8.1%}")
    print(f"     si cobras, cuanto (mediana)          : "
          f"{np.median(bruto[bruto>0]):>8,.0f} $")

print()
print(E)
print("¿PARA CUANDO?  probabilidad acumulada de haber cobrado (TP 50 tal cual)")
print(E)
r = salida[50.0]
d1 = r["d1"]
print(f"  {'mes':>5}{'dia de mercado':>17}{'P(ya cobraste)':>17}")
print("  " + "-" * 38)
for mes in range(1, 13):
    dd = int(mes * 21)
    p = ((d1 >= 0) & (d1 <= dd)).mean()
    print(f"  {mes:>5}{dd:>17}{p:>17.1%}")

print()
print(E)
print("REPARTO DEL RESULTADO A 12 MESES (TP 50, dinero al bolsillo)")
print(E)
b = r["recibido"]
for lo, hi, etiq in ((-1, 1, "nada, 0 $"),
                     (1, 300, "un cobro (~224 $)"),
                     (300, 800, "dos cobros (~692 $)"),
                     (800, 1e9, "tres o mas")):
    m = (b > lo) & (b <= hi) if lo >= 0 else (b <= hi)
    print(f"  {etiq:<22}{m.mean():>8.1%}")

print()
print(E)
print("Y LO QUE NO ES DINERO PERO ES EL RESULTADO PRINCIPAL DEL AÑO 1")
print(E)
print(f"  probabilidad de QUEMAR la cuenta en el año 1 : {r['quemada'].mean():>7.2%}")
print(f"  beneficio atrapado al cabo del año (media)   : {r['atrapado'].mean():>6,.0f} $")
print(f"  saldo medio al cabo del año                  : {r['bal'].mean():>6,.0f} $")
print()
print("  El año 1 no es el año de cobrar: es el año de LLEGAR VIVO con el saldo")
print("  arriba, porque los topes de los tramos 2 y 3 (500 y 750 $) ya valen mas")
print("  que el del primero y se cobran en los años 2 y 3.")
