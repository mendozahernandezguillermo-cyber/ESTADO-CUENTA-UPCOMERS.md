/*
 * Descarga M15 de varios instrumentos, AÑO A AÑO.
 *
 * La version anterior pedia 13 anos de golpe y Dukascopy respondia 429:
 * internamente genera cientos de peticiones en rafaga. Ahora:
 *   - un ano por peticion
 *   - pausa entre anos
 *   - reintento con espera creciente si aparece un 429
 *   - cada ano se guarda por separado -> totalmente reanudable
 *
 * Recortado a 2016-2026 (10 anos). Con ~2.500 sesiones por instrumento el
 * error estandar del Sharpe es ~0,32, suficiente para distinguir 0,71 de 0.
 * Si un instrumento pasa la prueba, se amplia su historial despues.
 */
const fs = require('fs');
const path = require('path');
const { getHistoricalRates } = require('dukascopy-node');

const DIR = path.join(__dirname, 'raw-multi');
if (!fs.existsSync(DIR)) fs.mkdirSync(DIR, { recursive: true });

const INSTRUMENTOS = [
  ['usa500idxusd',    'S&P 500       (EE.UU.)'],
  ['usa30idxusd',     'Dow 30        (EE.UU.)'],
  ['ussc2000idxusd',  'Russell 2000  (EE.UU. small)'],
  ['deuidxeur',       'DAX           (Alemania)'],
  ['gbridxgbp',       'FTSE 100      (Reino Unido)'],
  ['jpnidxjpy',       'Nikkei 225    (Japon)'],
  ['xauusd',          'ORO           (control negativo)'],
];

const ANIO_INI = 2016;
const ANIO_FIN = 2026;
const dormir = ms => new Promise(r => setTimeout(r, ms));

async function bajarAnio(instrument, anio, intento = 0) {
  const out = path.join(DIR, `${instrument}-m15-${anio}.csv`);
  if (fs.existsSync(out) && fs.statSync(out).size > 2000) return 'ya';

  const from = new Date(`${anio}-01-01T00:00:00Z`);
  const to = anio === ANIO_FIN ? new Date('2026-08-29T00:00:00Z')
                               : new Date(`${anio}-12-31T23:59:00Z`);
  try {
    const data = await getHistoricalRates({
      instrument, dates: { from, to }, timeframe: 'm15',
      priceType: 'bid', format: 'csv', utcOffset: 0,
      volumes: false, ignoreFlats: true,
      retryCount: 2, pauseBetweenRetriesMs: 4000,
    });
    if (!data || data.split('\n').length < 50) return 'vacio';
    fs.writeFileSync(out, data);
    return data.split('\n').length - 2;
  } catch (e) {
    if (/429/.test(e.message) && intento < 4) {
      const espera = 20000 * (intento + 1);
      process.stdout.write(` [429, espero ${espera / 1000}s]`);
      await dormir(espera);
      return bajarAnio(instrument, anio, intento + 1);
    }
    return 'FALLO:' + e.message.slice(0, 40);
  }
}

(async () => {
  for (const [inst, etq] of INSTRUMENTOS) {
    process.stdout.write(`${etq}  `);
    let tot = 0, saltados = 0, fallos = 0;
    for (let a = ANIO_INI; a <= ANIO_FIN; a++) {
      const r = await bajarAnio(inst, a);
      if (r === 'ya') { saltados++; process.stdout.write('.'); }
      else if (typeof r === 'number') { tot += r; process.stdout.write('#'); }
      else { fallos++; process.stdout.write('x'); }
      await dormir(2500);
    }
    console.log(`  -> ${tot} barras nuevas, ${saltados} años ya estaban,` +
                ` ${fallos} fallos`);
  }
  console.log('\nHecho.');
})();
