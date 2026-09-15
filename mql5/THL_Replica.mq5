//+------------------------------------------------------------------+
//|                                              THL_Replica.mq5     |
//|                                                                  |
//|  REPLICA DE LA REGLA DE ENTRADA DE joxemi (DARWIN THL / ZJM)      |
//|                                                                  |
//|  ###############################################################  |
//|  ##  PROPOSITO: VALIDACION FORENSE, NO RENTABILIDAD.          ##  |
//|  ##  Esta regla, probada sobre 15 anos de NASDAQ, da          ##  |
//|  ##  t = 0.52 y +0.65% anual. NO tiene ventaja demostrada.    ##  |
//|  ###############################################################  |
//|                                                                  |
//|  PARA QUE SIRVE                                                  |
//|    Ponerlo en DEMO y comparar su curva con la cotizacion del      |
//|    DARWIN THL. Si siguen la misma forma, la ingenieria inversa    |
//|    fue correcta y el edge de joxemi esta en la seleccion que      |
//|    hace DENTRO de estas oportunidades (toma ~230/ano de las       |
//|    ~490/ano que la regla identifica). Si divergen, algo esta      |
//|    mal especificado.                                             |
//|                                                                  |
//|  DE DONDE SALE LA REGLA                                          |
//|    De 936 timestamps de entrada reales de THL, obtenidos del      |
//|    endpoint publico de journal, contrastados contra controles     |
//|    emparejados por hora del dia:                                 |
//|                                                                  |
//|      posicion en el rango del dia, sus LARGOS: 0.87 vs 0.56      |
//|                                                    t = +34.7      |
//|      posicion en el rango del dia, sus CORTOS: 0.14 vs 0.57      |
//|                                                    t = -37.0      |
//|      mediana de la posicion: 0.904 largos / 0.110 cortos          |
//|      79.9% de sus largos entran entre 0.80 y 1.00                |
//|      75.8% de sus cortos entran entre 0.00 y 0.20                |
//|      95.3% de sus entradas tienen segundo = 00                   |
//|      92% caen en multiplos de 5 min -> evalua en cierres M5      |
//|      rango del dia en sus CORTOS: 184 bp vs 132 en controles      |
//|                                    t = +7.7 (sus largos: t=2.99) |
//|      duracion mediana: 65-82 min                                 |
//|      1.83 entradas por dia operado, 318 dias de ~420             |
//|      64% largos / 36% cortos                                     |
//|      18% de sus posiciones terminan en otro dia natural           |
//|                                                                  |
//|  CORREGIDO EN v1.02  (dos errores de fidelidad, encadenados)      |
//|    v1.00 disparaba SIEMPRE entre las 01:00 y 06:00 del servidor,   |
//|    o sea 19:00-00:00 NY, sobre rangos de 14-44 bp. joxemi tiene su |
//|    pico en las 11:00 NY con rangos de 140-184 bp.                 |
//|                                                                  |
//|    1. ANCLA DEL RANGO. El analisis forense midio el rango desde    |
//|       las 00:00 de Nueva York. El EA lo anclaba en 00:00 del       |
//|       servidor, seis horas antes, metiendo la tarde-noche previa   |
//|       en el rango. Corregido con InpRangoDesdeHora = 6 y un dia    |
//|       operativo que rueda a esa hora (ClaveDiaOp).                |
//|                                                                  |
//|    2. SUELO DE RANGO. Con tope de 2 entradas por dia y orden de    |
//|       llegada, el EA las gastaba en el primer rango estrecho de la |
//|       madrugada. InpSueloRango = 0.60 exige que el rango llegue    |
//|       al 60% de la mediana de 20 dias antes de operar.            |
//|                                                                  |
//|    Calibracion del suelo sobre 15 anos, frente a sus observables:  |
//|      suelo   %09-16h NY   %11h    rango medio                     |
//|       0.40      55.7%     13.6%      82 bp                        |
//|       0.60      ~72%      ~17%      ~110 bp                       |
//|       0.80      79.6%     17.7%     140 bp                        |
//|      joxemi     62.3%     18.9%   140-184 bp                      |
//|                                                                  |
//|    Se ajustan DOS de las tres observables, no las tres: un suelo   |
//|    alto mata sus entradas de madrugada (17% antes de la apertura)  |
//|    y conserva las nocturnas (27% tras el cierre). Eso indica que    |
//|    su referencia de rango no es exactamente la nuestra. Queda      |
//|    como limitacion conocida.                                      |
//|                                                                  |
//|  FIEL A EL                                                        |
//|    - Banda 0.80 / 0.20 del rango del dia acumulado               |
//|    - Evaluacion SOLO en cierres de vela M5                       |
//|    - Opera las 24 h, no solo la sesion cash (17% de sus          |
//|      entradas son antes de la apertura, 27% tras el cierre)      |
//|    - Cortos exigen dia ancho; largos no                          |
//|    - Salida por tiempo a los 75 min                              |
//|    - Permite pasar la noche (el 18% de las suyas lo hace)        |
//|    - Maximo 2 entradas por dia                                   |
//|                                                                  |
//|  DONDE ME DESVIO A PROPOSITO                                      |
//|    1. Sizing por % de equity fijo. El va a D-Leverage 2.38 medio  |
//|       pero pica a 30.66. No replico eso: es riesgo sin ventaja    |
//|       conocida.                                                   |
//|    2. Una posicion a la vez. El promedia 1.41 simultaneas y llega |
//|       a 7. Mas de una exige cuenta de cobertura (hedging); en     |
//|       cuenta de neteo se fusionarian y cambiaria el riesgo.       |
//|    3. Solo NASDAQ. El reparte ~85% NASDAQ, ~8% Germany 30 y algo  |
//|       de FX. Para aproximarlo, adjunta otra instancia a un        |
//|       grafico de DAX con InpRiskPct proporcionalmente menor.      |
//|    4. Stop de catastrofe al 2%. El no parece usar stop duro.      |
//|                                                                  |
//|  AVISO SOBRE EL SWAP                                              |
//|    Al permitir pasar la noche, este EA SI paga swap (~4.56%       |
//|    anual en tu CFD segun medimos). v2 lo evitaba cerrando a las   |
//|    21:40. Aqui se acepta por fidelidad. Si prefieres no pagarlo,  |
//|    pon InpCerrarAntesDe = 1310 (21:50) y perderas fidelidad en    |
//|    ese 18%.                                                      |
//+------------------------------------------------------------------+
#property copyright "Replica forense. Sin ventaja demostrada."
#property version   "1.03"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\SymbolInfo.mqh>

//--- la regla ---------------------------------------------------------
input group           "=== Regla (medida en THL) ==="
input double InpBandaLarga    = 0.80;  // Posicion minima del rango para LARGO
input double InpBandaCorta    = 0.20;  // Posicion maxima del rango para CORTO
input int    InpHoldMin       = 75;    // Salida por tiempo (min). Mediana de THL: 65-82
input int    InpMaxPorDia     = 2;     // Maximo de entradas por dia (THL: 1.83)
input int    InpMinMinDia     = 60;    // No operar hasta N min de dia transcurridos
input double InpFactorCorto   = 0.35;  // Cortos: rango >= factor x mediana20d x sqrt(t/1440)
input double InpSueloRango    = 0.60;  // Suelo: rango >= suelo x mediana20d (ambas direcciones)
input int    InpLookbackDias  = 20;    // Dias para la mediana de rango
input int    InpRangoDesdeHora = 6;    // Hora del SERVIDOR en que arranca el dia operativo
                                       // 6 = 00:00 Nueva York (servidor = NY + 6)

//--- ventana y overnight ---------------------------------------------
input group           "=== Horario ==="
input int    InpCerrarAntesDe = 0;     // Cierre forzoso en min desde medianoche (0 = permitir overnight)
input int    InpMaxHoldMin    = 1440;  // Antiguedad maxima absoluta (red de seguridad)

//--- riesgo -----------------------------------------------------------
input group           "=== Riesgo (desviacion deliberada) ==="
input double InpRiskPct       = 0.50;  // % de equity en riesgo por operacion
input double InpStopPctPrice  = 2.00;  // Stop de catastrofe, % del precio
input double InpMaxLots       = 0.0;   // Tope de lotes (0 = sin tope)
input double InpMaxSpreadBp   = 1.00;  // Spread maximo para entrar, en bp
input double InpDailyLossPct  = 3.00;  // Corte del dia si se pierde este %

//--- operativa --------------------------------------------------------
input group           "=== Operativa ==="
input long   InpMagic         = 20260830;
input int    InpSlippagePts   = 20;
input bool   InpVerbose       = true;

//--- estado -----------------------------------------------------------
CTrade      g_trade;
CSymbolInfo g_sym;

datetime g_lastM5     = 0;
int      g_lastDayKey = -1;
int      g_entradasHoy = 0;
bool     g_blocked    = false;
double   g_eqDayIni   = 0.0;

//--- contadores de diagnostico ---------------------------------------
int g_cVelas5 = 0, g_cLargo = 0, g_cCorto = 0, g_cSinRango = 0;
int g_cSpread = 0, g_cTope = 0, g_cLotes = 0, g_cEstrecho = 0;
int g_cSinMediana = 0;

//+------------------------------------------------------------------+
int MinutosDia(const datetime t)
{
   MqlDateTime d; TimeToStruct(t, d);
   return(d.hour * 60 + d.min);
}
int ClaveDia(const datetime t)
{
   MqlDateTime d; TimeToStruct(t, d);
   return(d.year * 10000 + d.mon * 100 + d.day);
}

// Clave del DIA OPERATIVO: rueda a las InpRangoDesdeHora del servidor.
// El analisis forense midio el rango desde las 00:00 de Nueva York, que
// con servidor = NY + 6 son las 06:00 del servidor. Anclar en 00:00 del
// servidor metia las seis horas de la tarde-noche anterior en el rango y
// hacia que el EA gastara sus dos entradas de madrugada sobre rangos de
// 20 bp, cuando las entradas de joxemi tienen 140-184 bp.
int ClaveDiaOp(const datetime t)
{
   return(ClaveDia(t - (long)InpRangoDesdeHora * 3600));
}

//+------------------------------------------------------------------+
int OnInit()
{
   if(InpBandaLarga <= InpBandaCorta)
   {
      Print("ERROR: la banda larga debe estar por encima de la corta.");
      return(INIT_PARAMETERS_INCORRECT);
   }
   if(InpRiskPct <= 0.0 || InpStopPctPrice <= 0.0 || InpHoldMin <= 0)
   {
      Print("ERROR: riesgo, stop y hold deben ser > 0.");
      return(INIT_PARAMETERS_INCORRECT);
   }
   if(!g_sym.Name(_Symbol)) return(INIT_FAILED);
   g_sym.RefreshRates();

   double tv = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tv <= 0.0 || ts <= 0.0)
   {
      Print("ERROR: Tick value=", tv, " Tick size=", ts,
            ". Simbolo no suscrito. En Market Watch pulsa 'Mostrar simbolo' ",
            "sobre ", _Symbol, ", cierra y reabre el dialogo, reinicia el EA.");
      return(INIT_FAILED);
   }

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints((ulong)InpSlippagePts);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.LogLevel(LOG_LEVEL_ERRORS);

   g_lastDayKey = ClaveDiaOp(TimeCurrent());
   g_eqDayIni   = AccountInfoDouble(ACCOUNT_EQUITY);

   PrintFormat("THL_Replica | %s | banda %.2f/%.2f | hold %d min | "
               "max %d/dia | riesgo %.2f%%",
               _Symbol, InpBandaLarga, InpBandaCorta, InpHoldMin,
               InpMaxPorDia, InpRiskPct);
   Print("PROPOSITO: validacion forense. Esta regla dio t=0.52 y +0.65% ",
         "anual sobre 15 anos. NO tiene ventaja demostrada. Comparar su ",
         "curva con la cotizacion del DARWIN THL.");
   if(InpCerrarAntesDe <= 0)
      Print("AVISO: overnight permitido (fiel a THL: 18% de sus posiciones). ",
            "Esto SI paga swap, ~4.56% anual.");
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Rango del dia en curso, EXCLUYENDO la vela M1 actual.             |
//| Devuelve false si aun no hay rango utilizable.                    |
//+------------------------------------------------------------------+
bool RangoDia(double &hi, double &lo, int &minTranscurridos)
{
   MqlRates r[];
   ArraySetAsSeries(r, false);
   int n = CopyRates(_Symbol, PERIOD_M1, 0, 1600, r);
   if(n < 10) return(false);

   int hoyOp = ClaveDiaOp(TimeCurrent());
   hi = 0.0; lo = 0.0;
   int cuenta = 0;
   datetime primera = 0;

   // r[n-1] es la vela en formacion: se excluye
   for(int i = 0; i <= n - 2; i++)
   {
      if(ClaveDiaOp(r[i].time) != hoyOp) continue;   // mismo dia OPERATIVO
      if(primera == 0) primera = r[i].time;
      if(hi == 0.0) { hi = r[i].high; lo = r[i].low; }
      else
      {
         if(r[i].high > hi) hi = r[i].high;
         if(r[i].low  < lo) lo = r[i].low;
      }
      cuenta++;
   }
   if(cuenta < 10 || hi <= lo || primera == 0) return(false);
   minTranscurridos = (int)((TimeCurrent() - primera) / 60);
   return(true);
}

//+------------------------------------------------------------------+
//| Mediana del rango diario de los ultimos N dias, en bp             |
//+------------------------------------------------------------------+
double MedianaRangoBp()
{
   MqlRates d[];
   ArraySetAsSeries(d, false);
   int n = CopyRates(_Symbol, PERIOD_D1, 0, InpLookbackDias + 3, d);
   // Degradar con gracia: si no hay 20 dias todavia, usar los que haya.
   // La version anterior exigia 21 barras y devolvia 0, lo que hacia que
   // el suelo de rango y el filtro de cortos se saltaran por completo
   // durante el primer mes de cualquier historico corto. Un filtro que
   // falla en ABIERTO es el peor modo de fallo posible.
   if(n < 6) return(0.0);

   double v[];
   ArrayResize(v, 0);
   int k = 0;
   // se excluye el dia en curso (el ultimo)
   for(int i = n - 2; i >= 0 && k < InpLookbackDias; i--)
   {
      if(d[i].open <= 0.0) continue;
      ArrayResize(v, k + 1);
      v[k++] = 1e4 * (d[i].high - d[i].low) / d[i].open;
   }
   if(k < 5) return(0.0);
   ArraySort(v);
   return(k % 2 ? v[k / 2] : 0.5 * (v[k / 2 - 1] + v[k / 2]));
}

//+------------------------------------------------------------------+
long BuscarPosicion()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      return((long)tk);
   }
   return(0);
}

bool Cerrar(long tk, string motivo)
{
   if(tk == 0) return(true);
   if(g_trade.PositionClose((ulong)tk))
   {
      if(InpVerbose) Print("Cerrado: ", motivo);
      return(true);
   }
   Print("ERROR al cerrar (", motivo, "): ", g_trade.ResultRetcode(), " ",
         g_trade.ResultRetcodeDescription());
   return(false);
}

//+------------------------------------------------------------------+
double NormalizarLotes(double lots)
{
   double mn = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double mx = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double st = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(st <= 0.0) st = 0.01;
   lots = MathFloor(lots / st) * st;
   if(InpMaxLots > 0.0 && lots > InpMaxLots) lots = InpMaxLots;
   if(lots > mx) lots = mx;
   if(lots < mn) return(0.0);
   return(NormalizeDouble(lots, 2));
}

double CalcularLotes(double stopDist)
{
   if(stopDist <= 0.0) return(0.0);
   double tv = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tv <= 0.0 || ts <= 0.0) return(0.0);
   double perLote = (stopDist / ts) * tv;
   if(perLote <= 0.0) return(0.0);
   return(NormalizarLotes(AccountInfoDouble(ACCOUNT_EQUITY)
                          * InpRiskPct / 100.0 / perLote));
}

//+------------------------------------------------------------------+
//| Evaluacion de entrada. Se llama SOLO al cerrar una vela M5.       |
//+------------------------------------------------------------------+
void EvaluarEntrada()
{
   g_cVelas5++;

   if(g_entradasHoy >= InpMaxPorDia) { g_cTope++; return; }

   double hi = 0.0, lo = 0.0;
   int transcurridos = 0;
   if(!RangoDia(hi, lo, transcurridos)) { g_cSinRango++; return; }
   if(transcurridos < InpMinMinDia) return;

   if(!g_sym.RefreshRates()) return;
   double ask = g_sym.Ask(), bid = g_sym.Bid();
   if(ask <= 0.0 || bid <= 0.0) return;

   double px  = 0.5 * (ask + bid);

   // El precio actual forma parte del rango. RangoDia excluye la vela en
   // formacion, asi que en una ruptura el precio queda por encima de 'hi'
   // y pos_rango salia >1 (se vieron valores de 1.558). El analisis
   // forense incluia la vela en curso, de modo que sus posiciones nunca
   // pasaban de 1.0. Igualamos la semantica.
   if(px > hi) hi = px;
   if(px < lo) lo = px;

   double rng = hi - lo;
   if(rng <= 0.0) { g_cSinRango++; return; }
   double pos = (px - lo) / rng;
   double rngBp = 1e4 * rng / px;

   // SUELO DE RANGO, ambas direcciones. Sin esto el EA gasta sus dos
   // entradas diarias en la sesion asiatica sobre rangos de 20-40 bp,
   // cuando las entradas reales de joxemi tienen 140-184 bp. Con 0.60
   // el reparto horario se aproxima al suyo (ver encabezado).
   double medSuelo = 0.0;
   if(InpSueloRango > 0.0)
   {
      medSuelo = MedianaRangoBp();
      if(medSuelo <= 0.0)
      {
         // FALLA EN CERRADO: sin referencia de rango no se opera.
         g_cSinMediana++;
         return;
      }
      if(rngBp < InpSueloRango * medSuelo)
      {
         g_cEstrecho++;
         return;
      }
   }

   int dir = 0;
   if(pos >= InpBandaLarga)       dir =  1;
   else if(pos <= InpBandaCorta)  dir = -1;
   if(dir == 0) return;

   // Los CORTOS de joxemi exigen dia ancho; sus largos no.
   //
   // NORMALIZADO POR TIEMPO TRANSCURRIDO. La primera version comparaba
   // el rango acumulado hasta ese momento contra medianas de DIA
   // COMPLETO, que no son magnitudes homologables: a media manana el
   // rango siempre es una fraccion del rango final, asi que el filtro
   // mataba el 96% de los cortos (3.2% del total frente al 36% real de
   // joxemi). El rango crece como sqrt(t), de ahi el escalado.
   //
   // Con factor 0.35 sobre 15 anos salen 35.9% de cortos, que es su
   // reparto medido (36%).
   if(dir < 0 && InpFactorCorto > 0.0)
   {
      double med = (medSuelo > 0.0 ? medSuelo : MedianaRangoBp());
      double frac = MathSqrt((double)MathMax(1, transcurridos) / 1440.0);
      double esperado = med * frac;
      if(med > 0.0 && rngBp < InpFactorCorto * esperado)
      {
         g_cEstrecho++;
         if(InpVerbose)
            PrintFormat("CORTO descartado: pos %.3f | rango %.0f bp < "
                        "%.2f x %.0f bp esperado (mediana20d %.0f, "
                        "transcurrido %d min)",
                        pos, rngBp, InpFactorCorto, esperado, med,
                        transcurridos);
         return;
      }
   }

   double spreadBp = (ask - bid) / bid * 10000.0;
   if(InpMaxSpreadBp > 0.0 && spreadBp > InpMaxSpreadBp)
   {
      g_cSpread++;
      if(InpVerbose)
         PrintFormat("Spread %.2f bp > %.2f. Sin entrada.", spreadBp,
                     InpMaxSpreadBp);
      return;
   }

   double entry    = (dir > 0) ? ask : bid;
   double stopDist = entry * InpStopPctPrice / 100.0;
   double sl = NormalizeDouble((dir > 0) ? entry - stopDist
                                         : entry + stopDist, _Digits);
   double lots = CalcularLotes(stopDist);
   if(lots <= 0.0)
   {
      g_cLotes++;
      Print("ERROR: lotes = 0. Revisa Tick value, volumen minimo y equity.");
      return;
   }

   bool ok = (dir > 0) ? g_trade.Buy(lots, _Symbol, 0.0, sl, 0.0, "THLrep")
                       : g_trade.Sell(lots, _Symbol, 0.0, sl, 0.0, "THLrep");
   if(ok)
   {
      g_entradasHoy++;
      if(dir > 0) g_cLargo++; else g_cCorto++;
      PrintFormat("%s %.2f lotes @ %.*f | pos_rango %.3f | rango %.0f bp | "
                  "SL %.*f | spread %.2f bp",
                  (dir > 0 ? "LARGO" : "CORTO"), lots, _Digits, entry,
                  pos, 1e4 * rng / px, _Digits, sl, spreadBp);
   }
   else
      Print("ERROR al abrir: ", g_trade.ResultRetcode(), " ",
            g_trade.ResultRetcodeDescription());
}

//+------------------------------------------------------------------+
void OnTick()
{
   datetime ahora = TimeCurrent();
   int m   = MinutosDia(ahora);
   int key = ClaveDiaOp(ahora);        // dia OPERATIVO, no natural
   long tk = BuscarPosicion();

   //--- cambio de dia operativo -------------------------------------
   if(key != g_lastDayKey)
   {
      g_lastDayKey   = key;
      g_entradasHoy  = 0;
      g_blocked      = false;
      g_eqDayIni     = AccountInfoDouble(ACCOUNT_EQUITY);
   }

   //--- 1. salida por TIEMPO: la regla principal de cierre ----------
   if(tk != 0 && PositionSelectByTicket((ulong)tk))
   {
      datetime abierta = (datetime)PositionGetInteger(POSITION_TIME);
      int vivos = (int)((ahora - abierta) / 60);
      if(vivos >= InpHoldMin)
      {
         Cerrar(tk, StringFormat("hold %d min", vivos));
         return;
      }
      if(InpMaxHoldMin > 0 && vivos >= InpMaxHoldMin)
      {
         Cerrar(tk, StringFormat("antiguedad maxima %d min", vivos));
         return;
      }
   }

   //--- 2. cierre forzoso por hora, si se ha configurado ------------
   if(tk != 0 && InpCerrarAntesDe > 0 && m >= InpCerrarAntesDe)
   {
      Cerrar(tk, "cierre horario configurado");
      return;
   }

   //--- 3. limite de perdida diaria ---------------------------------
   if(!g_blocked && g_eqDayIni > 0.0)
   {
      double dd = 100.0 * (g_eqDayIni - AccountInfoDouble(ACCOUNT_EQUITY))
                  / g_eqDayIni;
      if(dd >= InpDailyLossPct)
      {
         g_blocked = true;
         Print("Limite de perdida diaria (", DoubleToString(dd, 2),
               "%). Sin mas entradas hoy.");
         if(tk != 0) Cerrar(tk, "limite diario");
         return;
      }
   }

   //--- 4. entrada: SOLO al cerrar una vela M5 ----------------------
   //     (95.3% de las entradas de joxemi tienen segundo=00 y el 92%
   //      caen en multiplos de 5 min)
   datetime t5 = iTime(_Symbol, PERIOD_M5, 0);
   if(t5 == 0 || t5 == g_lastM5) return;
   g_lastM5 = t5;

   if(tk != 0)   return;      // una posicion a la vez (ver encabezado)
   if(g_blocked) return;

   EvaluarEntrada();
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print("=========== THL_Replica: RECUENTO ===========");
   PrintFormat("  velas M5 evaluadas ........... %d", g_cVelas5);
   PrintFormat("  ENTRADAS largas .............. %d", g_cLargo);
   PrintFormat("  ENTRADAS cortas .............. %d", g_cCorto);
   Print("  --- descartes ---");
   PrintFormat("  tope de entradas del dia ..... %d", g_cTope);
   PrintFormat("  sin rango utilizable ......... %d", g_cSinRango);
   PrintFormat("  rango por debajo del suelo ... %d", g_cEstrecho);
   PrintFormat("  sin mediana de rango ......... %d  <- si es alto, falta historico D1",
               g_cSinMediana);
   PrintFormat("  spread excesivo .............. %d", g_cSpread);
   PrintFormat("  lotes = 0 .................... %d", g_cLotes);
   Print("============================================");
   long tk = BuscarPosicion();
   PrintFormat("Detenido (motivo %d).%s", reason,
               (tk != 0 ? "  ATENCION: queda posicion abierta." : ""));
}
//+------------------------------------------------------------------+
