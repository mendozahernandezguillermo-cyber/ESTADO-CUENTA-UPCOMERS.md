#!/usr/bin/env python3
"""
Verifica la logica de horario de verano de EE.UU. que lleva el EA.

Un error aqui haria que el EA entrara una hora tarde durante media temporada,
y el resultado saldria plano sin ninguna pista del motivo. Asi que se replica
el algoritmo del EA en Python y se contrasta contra las fechas reales de
cambio de horario y contra los propios anuncios del FOMC.

Reglas vigentes en EE.UU.:
   empieza el SEGUNDO domingo de marzo a las 02:00 locales (07:00 UTC)
   acaba   el PRIMER domingo de noviembre a las 02:00 locales (06:00 UTC)
"""
import datetime as dt

FECHAS_FOMC = [
    20260916, 20261028, 20261209,
    20270127, 20270317, 20270428, 20270609,
    20270728, 20270915, 20271027, 20271208,
]


def es_verano_eeuu(utc):
    """Replica exacta de EsVeranoEEUU() del EA."""
    anio = utc.year
    # segundo domingo de marzo
    mar1 = dt.date(anio, 3, 1)
    dow = (mar1.weekday() + 1) % 7          # MQL5: domingo=0
    primer_dom_mar = 1 + ((7 - dow) % 7)
    segundo_dom_mar = primer_dom_mar + 7
    inicio = dt.datetime(anio, 3, segundo_dom_mar, 7, 0)
    # primer domingo de noviembre
    nov1 = dt.date(anio, 11, 1)
    dow = (nov1.weekday() + 1) % 7
    primer_dom_nov = 1 + ((7 - dow) % 7)
    final = dt.datetime(anio, 11, primer_dom_nov, 6, 0)
    return inicio <= utc < final


print("=" * 78)
print("1. FECHAS DE CAMBIO CALCULADAS POR EL ALGORITMO DEL EA")
print("=" * 78)
# valores reales conocidos
REALES = {
    2026: ("2026-03-08", "2026-11-01"),
    2027: ("2027-03-14", "2027-11-07"),
    2028: ("2028-03-12", "2028-11-05"),
}
print(f"{'año':<7}{'inicio calculado':<20}{'inicio real':<16}"
      f"{'fin calculado':<20}{'fin real':<14}")
print("-" * 78)
ok = True
for anio in (2026, 2027, 2028):
    mar1 = dt.date(anio, 3, 1)
    dow = (mar1.weekday() + 1) % 7
    ini = dt.date(anio, 3, 1 + ((7 - dow) % 7) + 7)
    nov1 = dt.date(anio, 11, 1)
    dow = (nov1.weekday() + 1) % 7
    fin = dt.date(anio, 11, 1 + ((7 - dow) % 7))
    ri, rf = REALES[anio]
    bien = (str(ini) == ri and str(fin) == rf)
    ok = ok and bien
    print(f"{anio:<7}{str(ini):<20}{ri:<16}{str(fin):<20}{rf:<14}"
          f"{'' if bien else '  <-- ERROR'}")
print()
print("  -> %s" % ("las tres coinciden: algoritmo CORRECTO" if ok
                   else "hay discrepancias, revisar"))

print()
print("=" * 78)
print("2. DESFASE SERVIDOR(GMT+2) -> NY EN CADA ANUNCIO DEL FOMC")
print("=" * 78)
print("  El servidor del broker esta en GMT+2 fijo. Se comprueba a que hora")
print("  del servidor cae la entrada (16:00 NY) en cada evento.")
print()
print(f"{'anuncio':<12}{'entrada NY':<14}{'verano?':<10}{'desfase':<10}"
      f"{'hora servidor':<15}")
print("-" * 78)
cambios = set()
for n in FECHAS_FOMC:
    anuncio = dt.date(n // 10000, (n // 100) % 100, n % 100)
    entrada = anuncio - dt.timedelta(days=1)          # martes
    # 16:00 NY -> UTC
    utc_aprox = dt.datetime.combine(entrada, dt.time(21, 0))  # tanteo
    verano = es_verano_eeuu(utc_aprox)
    off_ny_utc = 4 if verano else 5
    utc_real = dt.datetime.combine(entrada, dt.time(16, 0)) + \
        dt.timedelta(hours=off_ny_utc)
    servidor = utc_real + dt.timedelta(hours=2)       # GMT+2
    desfase = 2 + off_ny_utc
    cambios.add(desfase)
    print(f"{str(anuncio):<12}{'16:00':<14}{'si' if verano else 'NO':<10}"
          f"{str(desfase) + ' h':<10}{servidor.strftime('%H:%M'):<15}")

print()
print("=" * 78)
print("3. CONCLUSION")
print("=" * 78)
print("  desfases distintos que aparecen en los 11 eventos: %s"
      % sorted(cambios))
if len(cambios) > 1:
    print()
    print("  CONFIRMADO: el desfase NO es constante. Un offset fijo entraria")
    print("  a la hora equivocada en parte de los eventos. Por eso el EA")
    print("  calcula la hora de NY desde UTC con las reglas de horario de")
    print("  verano, en vez de usar un numero fijo.")
    print()
    print("  Con offset fijo de 6 h se equivocarian los eventos de desfase 7:")
    for n in FECHAS_FOMC:
        a = dt.date(n // 10000, (n // 100) % 100, n % 100)
        e = a - dt.timedelta(days=1)
        v = es_verano_eeuu(dt.datetime.combine(e, dt.time(21, 0)))
        if not v:
            print("     %s  (entraria a las 15:00 NY en vez de 16:00)" % a)
else:
    print("  el desfase es constante, un offset fijo bastaria")
