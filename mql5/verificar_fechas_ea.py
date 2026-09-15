#!/usr/bin/env python3
"""
Verifica la logica de fechas del EA_FOMC_Gap replicandola en Python.

Un error aqui seria invisible en el Probador: el EA simplemente no operaria
algunos eventos, o operaria el dia equivocado, y el resultado saldria plano
sin dar ninguna pista del motivo.

Se comprueban tres cosas:
  1. que para cada anuncio exista exactamente UN dia de entrada
  2. que ese dia de entrada sea el dia de mercado inmediatamente anterior
  3. que ninguna posicion cruce un fin de semana
"""
import datetime as dt

# tabla embebida en el EA (AAAAMMDD)
FECHAS = [20260916, 20261028, 20261209,
          20270127, 20270317, 20270428, 20270609,
          20270728, 20270915, 20271027, 20271208]


def a_fecha(n):
    return dt.date(n // 10000, (n // 100) % 100, n % 100)


def es_anuncio(f):
    return int(f.strftime("%Y%m%d")) in FECHAS


def anuncio_manana(hoy):
    """Replica exacta de AnuncioManana() del EA."""
    for d in range(1, 5):
        cand = hoy + dt.timedelta(days=d)
        if cand.weekday() >= 5:          # sabado=5, domingo=6
            continue
        if es_anuncio(cand):
            return cand
        return None
    return None


DOW = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]

print("=" * 78)
print("VERIFICACION DE LA LOGICA DE FECHAS DEL EA")
print("=" * 78)
print(f"{'anuncio':<14}{'dia sem.':<12}{'entrada detectada':<20}"
      f"{'dia sem.':<12}{'gap dias':>9}")
print("-" * 78)

problemas = []
for n in FECHAS:
    anuncio = a_fecha(n)
    # se buscan todos los dias que detectarian este anuncio
    entradas = []
    for back in range(1, 7):
        cand = anuncio - dt.timedelta(days=back)
        if anuncio_manana(cand) == anuncio:
            entradas.append(cand)
    if len(entradas) != 1:
        problemas.append((anuncio, "detectan %d dias: %s"
                          % (len(entradas), entradas)))
        marca = "  <-- PROBLEMA"
        ent, dsem, gap = "-", "-", "-"
    else:
        ent = entradas[0]
        dsem = DOW[ent.weekday()]
        gap = (anuncio - ent).days
        marca = ""
        if gap > 1 and ent.weekday() != 4:
            problemas.append((anuncio, "gap de %d dias sin ser viernes" % gap))
            marca = "  <-- revisar"
        if ent.weekday() >= 5:
            problemas.append((anuncio, "entrada en fin de semana"))
            marca = "  <-- PROBLEMA"
    print(f"{str(anuncio):<14}{DOW[anuncio.weekday()]:<12}{str(ent):<20}"
          f"{str(dsem):<12}{str(gap):>9}{marca}")

print()
print("=" * 78)
print("¿CRUZA ALGUNA POSICION UN FIN DE SEMANA?")
print("=" * 78)
cruces = 0
for n in FECHAS:
    anuncio = a_fecha(n)
    ents = [anuncio - dt.timedelta(days=b) for b in range(1, 7)
            if anuncio_manana(anuncio - dt.timedelta(days=b)) == anuncio]
    if len(ents) == 1:
        ent = ents[0]
        # cruza fin de semana si entre entrada y anuncio hay sabado o domingo
        d = ent
        while d < anuncio:
            d += dt.timedelta(days=1)
            if d.weekday() >= 5:
                cruces += 1
                print("  %s -> %s cruza %s" % (ent, anuncio, DOW[d.weekday()]))
print("  cruces detectados: %d" % cruces)
if cruces == 0:
    print("  -> ninguna posicion cruza fin de semana, como predijo el analisis")

print()
print("=" * 78)
print("RESULTADO")
print("=" * 78)
if not problemas:
    print("  Los %d anuncios tienen exactamente un dia de entrada, todos en" %
          len(FECHAS))
    print("  dia de semana, y ninguno cruza fin de semana. Logica CORRECTA.")
else:
    print("  %d problemas encontrados:" % len(problemas))
    for a, p in problemas:
        print("     %s: %s" % (a, p))

print()
print("LIMITACION CONOCIDA, no un fallo:")
print("  la logica no conoce los FESTIVOS de EE.UU. Si el dia de mercado")
print("  anterior a un anuncio fuera festivo, el EA no detectaria la entrada.")
print("  La Fed evita programar reuniones junto a festivos, asi que el riesgo")
print("  es bajo, pero conviene revisar el calendario cada año al ampliar la")
print("  tabla de fechas.")
