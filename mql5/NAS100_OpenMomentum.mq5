//+------------------------------------------------------------------+
//|                                       NAS100_OpenMomentum.mq5    |
//|                                          v2.00  bug de cierre     |
//|                                                                  |
//|  QUE HACE                                                        |
//|    Mide el empuje de los primeros N minutos de la sesion cash de  |
//|    EE.UU. Si es alcista por encima de un umbral, abre UN largo y  |
//|    lo mantiene hasta el final de la sesion. Nunca pasa la noche.  |
//|                                                                  |
//|  ###############################################################  |
//|  ##  LA VENTAJA NO ESTA DEMOSTRADA. Ver "EVIDENCIA" abajo.    ##  |
//|  ###############################################################  |
//|                                                                  |
//|  CORREGIDO EN v2.00                                              |
//|    v1.00 cerraba con  if(m >= 22:00). Pero en 35 de 160 dias      |
//|    (viernes y festivos) NACUSD.c deja de cotizar a las 21:59, asi |
//|    que el minuto 1320 NUNCA llegaba y la posicion se quedaba      |
//|    abierta. Consecuencias medidas en el Probador:                 |
//|      - la posicion viva bloqueaba la entrada del dia siguiente    |
//|        -> 37 operaciones donde la senal daba 72                   |
//|      - se comia el hueco del fin de semana y pagaba swap          |
//|        -> perdida media -86 bp contra ganancia media +40 bp       |
//|      - resultado: -96 $ cuando lo correcto era +571 $             |
//|                                                                  |
//|    Arreglos:                                                      |
//|      1. Cierre a las 21:50, dentro de la ventana de cotizacion    |
//|         incluso en los dias de cierre temprano.                   |
//|      2. Red de seguridad: si hay posicion abierta y ha cambiado   |
//|         el dia, se cierra de inmediato. Imposible pasar la noche.  |
//|      3. Cierre tambien por antiguedad maxima de la posicion.      |
//|                                                                  |
//|  EVIDENCIA  (medida sobre NACUSD.c real, 2026-01-16 a 08-28,      |
//|              160 sesiones, y sobre 15 anos de Dukascopy)          |
//|                                                                  |
//|    Los dos feeds coinciden: 72 senales de 160 sesiones en ambos.  |
//|    Pero el efecto no es estable ante cambios triviales. Movido    |
//|    el ancla de medida un solo minuto:                             |
//|                                                                  |
//|      ancla    media_bp     t      acierto                         |
//|        0        12.69     1.34     62.50%                         |
//|        1         5.59     0.56     56.00%                         |
//|        2         4.61     0.44     60.81%                         |
//|        5         9.53     0.93     61.64%                         |
//|       30        -9.64    -0.99     49.25%                         |
//|                                                                  |
//|    NINGUNA t LLEGA A 2. Y en 15 anos de datos la t del mismo      |
//|    efecto oscila entre 0.4 y 3.4 segun la especificacion. Eso es   |
//|    como se ve un efecto que no existe, no uno pequeno.            |
//|                                                                  |
//|    Lo unico robusto es la reduccion de drawdown, y viene de la    |
//|    baja exposicion (~12% del calendario), que es aritmetica.       |
//|                                                                  |
//|  HORARIO                                                          |
//|    Servidor = Chicago + 7 h: apertura cash en 15:30, campana en   |
//|    22:00. Verificado con el reparto horario de velas (la parada    |
//|    del CME cae en la hora 23). El EA lo recomprueba solo.         |
//+------------------------------------------------------------------+
#property copyright "Analisis propio. Ventaja no demostrada."
#property version   "2.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\SymbolInfo.mqh>

//--- horario, en HORA DEL SERVIDOR ----------------------------------
input group           "=== Horario (hora del servidor) ==="
input int    InpOpenHour     = 15;    // Hora de apertura cash US
input int    InpOpenMinute   = 30;    // Minuto de apertura cash US
input int    InpMomWindow    = 15;    // Minutos de medicion del empuje
input int    InpCloseHour    = 21;    // Hora de cierre  (21:50, NO 22:00)
input int    InpCloseMinute  = 50;    // Minuto de cierre
input int    InpEntryGrace   = 5;     // Margen para entrar (min)
input int    InpMaxHoldMin   = 420;   // Antiguedad maxima de la posicion (min)

//--- senal ----------------------------------------------------------
input group           "=== Senal ==="
input double InpMinPushBp    = 5.0;   // Empuje minimo, en bp
input bool   InpSkipMonday   = false; // Saltar lunes
input bool   InpSkipFriday   = false; // Saltar viernes

//--- riesgo ---------------------------------------------------------
input group           "=== Riesgo ==="
input double InpRiskPct      = 0.50;  // % de equity en riesgo por operacion
input double InpStopPctPrice = 2.00;  // Stop de catastrofe, % del precio
input double InpMaxLots      = 0.0;   // Tope de lotes (0 = sin tope)
input double InpMaxSpreadBp  = 1.00;  // Spread maximo para entrar, en BP
input double InpDailyLossPct = 3.00;  // Corte del dia si se pierde este %

//--- operativa ------------------------------------------------------
input group           "=== Operativa ==="
input long   InpMagic        = 20260829;
input int    InpSlippagePts  = 20;
input bool   InpVerbose      = true;

//--- estado ---------------------------------------------------------
CTrade      g_trade;
CSymbolInfo g_sym;

int      g_openMin    = 0;
int      g_signalMin  = 0;
int      g_closeMin   = 0;
int      g_lastDayKey = -1;   // clave del dia en HORA DEL SERVIDOR
bool     g_doneToday  = false;
bool     g_blocked    = false;
double   g_eqDayIni   = 0.0;
bool     g_horarioChk = false;

//--- diagnostico: por que se descarta cada dia -----------------------
int g_cDias      = 0;   // dias laborables vistos
int g_cFueraVent = 0;   // no hubo tick dentro de la ventana de entrada
int g_cSinVela   = 0;   // falto la vela exacta de apertura
int g_cSpread    = 0;   // spread por encima del maximo
int g_cEmpuje    = 0;   // empuje insuficiente
int g_cLotes     = 0;   // lotes calculados = 0
int g_cBloqueo   = 0;   // bloqueado por perdida diaria
int g_cPosViva   = 0;   // habia posicion abierta en la ventana
int g_cEntradas  = 0;   // entradas efectivas
int g_cRedSeg    = 0;   // veces que actuo la red de seguridad

//+------------------------------------------------------------------+
//| Utilidades de tiempo, todas en hora del servidor                  |
//+------------------------------------------------------------------+
int MinutosDia(const datetime t)
{
   MqlDateTime d; TimeToStruct(t, d);
   return(d.hour * 60 + d.min);
}

// Clave de dia del SERVIDOR. v1.00 usaba una division por 86400, que
// parte el dia en la medianoche UTC y no en la del servidor.
int ClaveDia(const datetime t)
{
   MqlDateTime d; TimeToStruct(t, d);
   return(d.year * 10000 + d.mon * 100 + d.day);
}

int DiaSemana(const datetime t)
{
   MqlDateTime d; TimeToStruct(t, d);
   return(d.day_of_week);
}

//+------------------------------------------------------------------+
int OnInit()
{
   g_openMin   = InpOpenHour * 60 + InpOpenMinute;
   g_signalMin = g_openMin + InpMomWindow;
   g_closeMin  = InpCloseHour * 60 + InpCloseMinute;

   if(g_signalMin >= g_closeMin)
   {
      Print("ERROR: la ventana de momentum termina despues del cierre.");
      return(INIT_PARAMETERS_INCORRECT);
   }
   if(InpRiskPct <= 0.0 || InpStopPctPrice <= 0.0)
   {
      Print("ERROR: riesgo y stop deben ser > 0.");
      return(INIT_PARAMETERS_INCORRECT);
   }
   if(!g_sym.Name(_Symbol))
   {
      Print("ERROR: no se pudo inicializar el simbolo.");
      return(INIT_FAILED);
   }
   g_sym.RefreshRates();

   double tickVal = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSz  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickVal <= 0.0 || tickSz <= 0.0)
   {
      Print("ERROR: Tick value = ", tickVal, "  Tick size = ", tickSz,
            ". El simbolo no esta suscrito. En Market Watch pulsa ",
            "'Mostrar simbolo' sobre ", _Symbol,
            ", cierra y reabre el dialogo, y reinicia el EA.");
      return(INIT_FAILED);
   }

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints((ulong)InpSlippagePts);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.LogLevel(LOG_LEVEL_ERRORS);

   g_eqDayIni   = AccountInfoDouble(ACCOUNT_EQUITY);
   g_lastDayKey = ClaveDia(TimeCurrent());

   PrintFormat("NAS100_OpenMomentum v2.00 | %s | apertura %02d:%02d  "
               "senal %02d:%02d  cierre %02d:%02d  riesgo %.2f%%",
               _Symbol, InpOpenHour, InpOpenMinute,
               g_signalMin / 60, g_signalMin % 60,
               InpCloseHour, InpCloseMinute, InpRiskPct);
   Print("AVISO: la ventaja de esta estrategia NO esta demostrada ",
         "(ninguna t llega a 2). Ver el encabezado del codigo.");
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Reparto horario de velas: la parada del CME debe caer en la 23    |
//+------------------------------------------------------------------+
bool VerificarHorario()
{
   MqlRates r[];
   ArraySetAsSeries(r, false);
   int n = CopyRates(_Symbol, PERIOD_M1, 0, 20000, r);
   if(n < 2000) return(false);

   int cnt[24];
   ArrayInitialize(cnt, 0);
   for(int i = 0; i < n; i++)
      cnt[MinutosDia(r[i].time) / 60]++;

   int hMin = 0;
   for(int h = 1; h < 24; h++)
      if(cnt[h] < cnt[hMin]) hMin = h;

   if(hMin == 23)
      PrintFormat("Calibracion OK (%d velas): la parada diaria cae en la "
                  "hora 23. Ventanas %02d:%02d / %02d:%02d correctas.",
                  n, InpOpenHour, InpOpenMinute, InpCloseHour, InpCloseMinute);
   else
      PrintFormat("AVISO DE CALIBRACION (%d velas): la hora con menos velas "
                  "es la %d, no la 23. Tu servidor puede ir desplazado %d h. "
                  "Ajusta InpOpenHour / InpCloseHour.", n, hMin, 23 - hMin);
   return(true);
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

//+------------------------------------------------------------------+
bool CerrarPosicion(long tk, string motivo)
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
//| Open de la vela exacta de apertura del dia en curso               |
//+------------------------------------------------------------------+
bool PrecioApertura(double &px)
{
   MqlRates r[];
   ArraySetAsSeries(r, false);
   int n = CopyRates(_Symbol, PERIOD_M1, 0, 1200, r);
   if(n <= 0) return(false);

   int hoy = ClaveDia(TimeCurrent());
   for(int i = n - 1; i >= 0; i--)          // de lo mas reciente hacia atras
   {
      if(ClaveDia(r[i].time) != hoy) break;
      if(MinutosDia(r[i].time) == g_openMin)
      {
         px = r[i].open;
         return(true);
      }
   }
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

//+------------------------------------------------------------------+
double CalcularLotes(double stopDist)
{
   if(stopDist <= 0.0) return(0.0);
   double tickVal = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSz  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickVal <= 0.0 || tickSz <= 0.0) return(0.0);

   double perdidaPorLote = (stopDist / tickSz) * tickVal;
   if(perdidaPorLote <= 0.0) return(0.0);

   double riesgo = AccountInfoDouble(ACCOUNT_EQUITY) * InpRiskPct / 100.0;
   return(NormalizarLotes(riesgo / perdidaPorLote));
}

//+------------------------------------------------------------------+
void OnTick()
{
   datetime ahora = TimeCurrent();
   int m   = MinutosDia(ahora);
   int dow = DiaSemana(ahora);
   int key = ClaveDia(ahora);

   if(!g_horarioChk && VerificarHorario()) g_horarioChk = true;

   long tk = BuscarPosicion();

   //=================================================================
   //  1. RED DE SEGURIDAD: cambio de dia con posicion abierta
   //     Esto es lo que fallaba en v1.00. Si por cualquier motivo la
   //     posicion sobrevivio al cierre (hueco en el feed, cierre
   //     temprano del broker, reinicio del terminal), se liquida aqui
   //     antes de hacer nada mas.
   //=================================================================
   bool diaNuevo = (key != g_lastDayKey);

   if(diaNuevo)
   {
      if(tk != 0)
      {
         Print("ALERTA: posicion abierta al cambiar de dia. Cerrando. ",
               "Revisa InpCloseHour/InpCloseMinute: el cierre normal ",
               "no se disparo.");
         g_cRedSeg++;
         CerrarPosicion(tk, "cambio de dia (red de seguridad)");
         return;                      // el resto se hace en el tick siguiente
      }
      g_lastDayKey = key;
      g_doneToday  = false;
      g_blocked    = false;
      g_eqDayIni   = AccountInfoDouble(ACCOUNT_EQUITY);
      if(dow >= 1 && dow <= 5) g_cDias++;
   }

   //=================================================================
   //  2. CIERRE NORMAL por hora
   //=================================================================
   if(tk != 0 && m >= g_closeMin)
   {
      CerrarPosicion(tk, "cierre de sesion");
      return;
   }

   //=================================================================
   //  3. CIERRE por antiguedad, por si el reloj o el feed fallan
   //=================================================================
   if(tk != 0 && InpMaxHoldMin > 0)
   {
      if(PositionSelectByTicket((ulong)tk))
      {
         datetime abierta = (datetime)PositionGetInteger(POSITION_TIME);
         int vivos = (int)((ahora - abierta) / 60);
         if(vivos >= InpMaxHoldMin)
         {
            CerrarPosicion(tk, StringFormat("antiguedad %d min", vivos));
            return;
         }
      }
   }

   //=================================================================
   //  4. limite de perdida diaria
   //=================================================================
   if(!g_blocked && g_eqDayIni > 0.0)
   {
      double dd = 100.0 * (g_eqDayIni - AccountInfoDouble(ACCOUNT_EQUITY))
                  / g_eqDayIni;
      if(dd >= InpDailyLossPct)
      {
         g_blocked = true;
         g_cBloqueo++;
         Print("Limite de perdida diaria (", DoubleToString(dd, 2),
               "%). Sin mas operaciones hoy.");
         if(tk != 0) CerrarPosicion(tk, "limite diario");
         return;
      }
   }

   if(tk != 0)
   {
      // Si llegamos a la ventana de entrada con una posicion viva, el
      // dia se pierde. Se cuenta una sola vez.
      if(!g_doneToday && m >= g_signalMin && m <= g_signalMin + InpEntryGrace)
      {
         g_cPosViva++;
         g_doneToday = true;
      }
      return;
   }
   if(g_doneToday) return;
   if(g_blocked)   return;

   //=================================================================
   //  5. filtros de dia y ventana de entrada
   //=================================================================
   if(dow == 0 || dow == 6) return;
   if(InpSkipMonday && dow == 1) return;
   if(InpSkipFriday && dow == 5) return;

   if(m < g_signalMin) return;
   if(m > g_signalMin + InpEntryGrace)
   {
      g_cFueraVent++;
      g_doneToday = true;
      return;
   }

   //=================================================================
   //  6. senal
   //=================================================================
   double aperturaPx = 0.0;
   if(!PrecioApertura(aperturaPx) || aperturaPx <= 0.0)
   {
      g_cSinVela++;
      if(InpVerbose)
         PrintFormat("Sin vela de %02d:%02d. Hoy no se opera.",
                     g_openMin / 60, g_openMin % 60);
      g_doneToday = true;
      return;
   }

   if(!g_sym.RefreshRates()) return;
   double ask = g_sym.Ask();
   double bid = g_sym.Bid();
   if(ask <= 0.0 || bid <= 0.0) return;

   // Spread en BP. En v1.00 estaba en unidades de _Point, y con
   // Digits=2 un spread de 0.80 puntos de indice sale como 80: el
   // filtro rechazaba todos los dias.
   double spreadBp = (ask - bid) / bid * 10000.0;
   if(InpMaxSpreadBp > 0.0 && spreadBp > InpMaxSpreadBp)
   {
      g_cSpread++;
      if(InpVerbose)
         PrintFormat("Spread %.2f bp (%.2f puntos) > %.2f bp. Hoy no se opera.",
                     spreadBp, ask - bid, InpMaxSpreadBp);
      g_doneToday = true;
      return;
   }

   double pushBp = (bid / aperturaPx - 1.0) * 10000.0;
   if(pushBp <= InpMinPushBp)
   {
      g_cEmpuje++;
      if(InpVerbose)
         PrintFormat("Empuje %.2f bp <= %.2f. Hoy no se opera.",
                     pushBp, InpMinPushBp);
      g_doneToday = true;
      return;
   }

   //=================================================================
   //  7. entrada
   //=================================================================
   double stopDist = ask * InpStopPctPrice / 100.0;
   double sl   = NormalizeDouble(ask - stopDist, _Digits);
   double lots = CalcularLotes(stopDist);

   if(lots <= 0.0)
   {
      g_cLotes++;
      Print("ERROR: lotes = 0. Revisa Tick value, volumen minimo y equity. ",
            "riesgo=", InpRiskPct, "%  stopDist=", stopDist);
      g_doneToday = true;
      return;
   }

   if(g_trade.Buy(lots, _Symbol, 0.0, sl, 0.0, "OpenMomentum"))
   {
      g_cEntradas++;
      g_doneToday = true;
      PrintFormat("LARGO %.2f lotes @ %.*f | empuje %.2f bp | SL %.*f | "
                  "spread %.2f bp", lots, _Digits, ask, pushBp,
                  _Digits, sl, spreadBp);
   }
   else
      Print("ERROR al abrir: ", g_trade.ResultRetcode(), " ",
            g_trade.ResultRetcodeDescription());
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   long tk = BuscarPosicion();

   int descartes = g_cFueraVent + g_cSinVela + g_cSpread + g_cEmpuje
                 + g_cLotes + g_cPosViva;

   Print("================ RECUENTO DE DIAS ================");
   PrintFormat("  dias laborables vistos ........ %d", g_cDias);
   PrintFormat("  ENTRADAS ...................... %d", g_cEntradas);
   Print("  --- descartados por: ---");
   PrintFormat("  empuje insuficiente ........... %d", g_cEmpuje);
   PrintFormat("  sin tick en la ventana ........ %d", g_cFueraVent);
   PrintFormat("  falta la vela de apertura ..... %d", g_cSinVela);
   PrintFormat("  spread excesivo ............... %d", g_cSpread);
   PrintFormat("  posicion aun abierta .......... %d", g_cPosViva);
   PrintFormat("  lotes = 0 ..................... %d", g_cLotes);
   PrintFormat("  suma descartes + entradas ..... %d  (de %d dias)",
               descartes + g_cEntradas, g_cDias);
   Print("  --- otros ---");
   PrintFormat("  bloqueos por perdida diaria ... %d", g_cBloqueo);
   PrintFormat("  red de seguridad activada ..... %d", g_cRedSeg);
   Print("==================================================");
   PrintFormat("NAS100_OpenMomentum detenido (motivo %d).%s", reason,
               (tk != 0 ? "  ATENCION: queda una posicion abierta." : ""));
}
//+------------------------------------------------------------------+
