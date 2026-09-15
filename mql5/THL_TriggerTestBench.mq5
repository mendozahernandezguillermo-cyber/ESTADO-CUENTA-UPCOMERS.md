//+------------------------------------------------------------------+
//|                                          THL_TriggerTestBench.mq5 |
//|  Banco de pruebas de las 3 hipotesis de disparador de THL         |
//|                                                                   |
//|  H1 = ruptura del rango pre-apertura 14:00-15:29 CET              |
//|  H2 = momentum de los primeros N minutos tras la apertura cash US |
//|  H3 = reversion del gap de apertura                               |
//|                                                                   |
//|  Ejecutar sobre un grafico M1 de NACUSD.c                         |
//|  Salida: MQL5\Files\THL_trigger_trades.csv  (1 fila / trade)      |
//|          MQL5\Files\THL_trigger_summary.csv (1 fila / hipotesis)  |
//+------------------------------------------------------------------+
#property script_show_inputs
#property strict

//--- desfase horario ------------------------------------------------
input int    InpCETOffset  = 0;     // Horas a SUMAR al tiempo del servidor para obtener CET
input int    InpMaxBars    = 600000;// Maximo de velas M1 a cargar

//--- costes y gestion -----------------------------------------------
input double InpSpreadPts  = 0.70;  // Coste ida+vuelta, en puntos de indice
input double InpTP         = 30.0;  // Objetivo, en puntos de indice
input double InpSL         = 30.0;  // Stop, en puntos de indice
input int    InpMaxMin     = 170;   // Duracion maxima en minutos (THL = 169)

//--- parametros de cada hipotesis -----------------------------------
input double InpH1Buffer   = 2.0;   // H1: margen sobre el extremo del rango
input int    InpMomWin     = 15;    // H2: minutos de momentum tras la apertura
input double InpMomMin     = 8.0;   // H2: movimiento minimo para validar la senal
input double InpGapMin     = 15.0;  // H3: gap minimo (abs) para operar

//--- salida ---------------------------------------------------------
input string InpOutTrades  = "THL_trigger_trades.csv";
input string InpOutSummary = "THL_trigger_summary.csv";

//--- ventanas en minutos desde medianoche CET -----------------------
#define PRE_INI   840   // 14:00
#define PRE_FIN   929   // 15:29
#define OPEN_MIN  930   // 15:30  apertura cash US
#define SESS_FIN 1320   // 22:00  cierre de sesion (plano overnight)

//--- estado global --------------------------------------------------
MqlRates g_r[];
int      g_n = 0;

int      g_dayIni[];
int      g_dayFin[];
string   g_dayKey[];
int      g_dayDow[];
int      g_days = 0;

//--- registro de un trade simulado ----------------------------------
struct Trade
{
   int    hip;
   string fecha;
   int    dow;
   int    dir;
   int    entryMin;
   double entryPx;
   int    exitMin;
   double exitPx;
   double bruto;
   double neto;
   int    dur;
   string motivo;
   double mfe;
   double mae;
   double ctx1;      // H1/H3: rango pre-apertura | H2: empuje de los N min
   double ctx2;      // gap de apertura
};

Trade g_t[];
int   g_nt = 0;

//+------------------------------------------------------------------+
//| Conversion a CET                                                  |
//+------------------------------------------------------------------+
int CetMin(const datetime tServer)
{
   MqlDateTime d;
   TimeToStruct(tServer + (long)InpCETOffset * 3600, d);
   return(d.hour * 60 + d.min);
}

string CetKey(const datetime tServer)
{
   MqlDateTime d;
   TimeToStruct(tServer + (long)InpCETOffset * 3600, d);
   return(StringFormat("%04d-%02d-%02d", d.year, d.mon, d.day));
}

int CetDow(const datetime tServer)
{
   MqlDateTime d;
   TimeToStruct(tServer + (long)InpCETOffset * 3600, d);
   return(d.day_of_week);
}

//+------------------------------------------------------------------+
//| Indice de dias CET                                                |
//+------------------------------------------------------------------+
void BuildDayIndex()
{
   int cap = 4096;
   ArrayResize(g_dayIni, cap);
   ArrayResize(g_dayFin, cap);
   ArrayResize(g_dayKey, cap);
   ArrayResize(g_dayDow, cap);
   g_days = 0;

   string cur = "";
   for(int i = 0; i < g_n; i++)
   {
      string k = CetKey(g_r[i].time);
      if(k != cur)
      {
         if(g_days >= cap)
         {
            cap *= 2;
            ArrayResize(g_dayIni, cap);
            ArrayResize(g_dayFin, cap);
            ArrayResize(g_dayKey, cap);
            ArrayResize(g_dayDow, cap);
         }
         g_dayIni[g_days] = i;
         g_dayFin[g_days] = i;
         g_dayKey[g_days] = k;
         g_dayDow[g_days] = CetDow(g_r[i].time);
         g_days++;
         cur = k;
      }
      else
         g_dayFin[g_days - 1] = i;
   }
}

//+------------------------------------------------------------------+
//| Simula una posicion desde fromIdx. Devuelve false si no cierra.   |
//| Regla conservadora: si TP y SL caben en la misma vela, gana SL.   |
//+------------------------------------------------------------------+
bool Simulate(int fromIdx, int dayFin, int dir, double entryPx, int entryMin,
              double &outPx, int &outMin, int &outDur, string &outMotivo,
              double &outMfe, double &outMae)
{
   double tp = (dir > 0) ? entryPx + InpTP : entryPx - InpTP;
   double sl = (dir > 0) ? entryPx - InpSL : entryPx + InpSL;

   outMfe = 0.0;
   outMae = 0.0;

   for(int i = fromIdx; i <= dayFin; i++)
   {
      int m = CetMin(g_r[i].time);

      double up = (dir > 0) ? (g_r[i].high - entryPx) : (entryPx - g_r[i].low);
      double dn = (dir > 0) ? (g_r[i].low  - entryPx) : (entryPx - g_r[i].high);
      if(up > outMfe) outMfe = up;
      if(dn < outMae) outMae = dn;

      bool hitSl = (dir > 0) ? (g_r[i].low  <= sl) : (g_r[i].high >= sl);
      bool hitTp = (dir > 0) ? (g_r[i].high >= tp) : (g_r[i].low  <= tp);

      if(hitSl)
      {
         outPx     = sl;
         outMin    = m;
         outDur    = m - entryMin;
         outMotivo = "SL";
         return(true);
      }
      if(hitTp)
      {
         outPx     = tp;
         outMin    = m;
         outDur    = m - entryMin;
         outMotivo = "TP";
         return(true);
      }
      if(m >= SESS_FIN)
      {
         outPx     = g_r[i].close;
         outMin    = m;
         outDur    = m - entryMin;
         outMotivo = "CIERRE2200";
         return(true);
      }
      if((m - entryMin) >= InpMaxMin)
      {
         outPx     = g_r[i].close;
         outMin    = m;
         outDur    = m - entryMin;
         outMotivo = "TIEMPO";
         return(true);
      }
   }

   // se acabo el dia sin llegar a 22:00: cerramos en la ultima vela
   int last = dayFin;
   outPx     = g_r[last].close;
   outMin    = CetMin(g_r[last].time);
   outDur    = outMin - entryMin;
   outMotivo = "FINDATOS";
   return(true);
}

//+------------------------------------------------------------------+
//| Registra un trade                                                 |
//+------------------------------------------------------------------+
void AddTrade(int hip, string fecha, int dow, int dir,
              int entryMin, double entryPx,
              int exitMin, double exitPx, int dur, string motivo,
              double mfe, double mae, double ctx1, double ctx2)
{
   if(g_nt >= ArraySize(g_t))
      ArrayResize(g_t, MathMax(1024, g_nt * 2));

   double bruto = (dir > 0) ? (exitPx - entryPx) : (entryPx - exitPx);

   g_t[g_nt].hip      = hip;
   g_t[g_nt].fecha    = fecha;
   g_t[g_nt].dow      = dow;
   g_t[g_nt].dir      = dir;
   g_t[g_nt].entryMin = entryMin;
   g_t[g_nt].entryPx  = entryPx;
   g_t[g_nt].exitMin  = exitMin;
   g_t[g_nt].exitPx   = exitPx;
   g_t[g_nt].bruto    = bruto;
   g_t[g_nt].neto     = bruto - InpSpreadPts;
   g_t[g_nt].dur      = dur;
   g_t[g_nt].motivo   = motivo;
   g_t[g_nt].mfe      = mfe;
   g_t[g_nt].mae      = mae;
   g_t[g_nt].ctx1     = ctx1;
   g_t[g_nt].ctx2     = ctx2;
   g_nt++;
}

//+------------------------------------------------------------------+
//| Hora CET formateada                                               |
//+------------------------------------------------------------------+
string HM(int m)
{
   if(m < 0) return("");
   return(StringFormat("%02d:%02d", m / 60, m % 60));
}

//+------------------------------------------------------------------+
//| Resumen por hipotesis                                             |
//+------------------------------------------------------------------+
void WriteSummary(int fh, int hip, int nMeses)
{
   int    n = 0, nWin = 0, nLoss = 0;
   double sumWin = 0.0, sumLoss = 0.0, sumDur = 0.0, total = 0.0;
   double eq = 0.0, peak = 0.0, maxDd = 0.0;
   int    nSl = 0, nTp = 0, nTime = 0, nClose = 0;

   for(int i = 0; i < g_nt; i++)
   {
      if(g_t[i].hip != hip) continue;
      n++;
      total  += g_t[i].neto;
      sumDur += g_t[i].dur;

      if(g_t[i].neto > 0) { nWin++;  sumWin  += g_t[i].neto; }
      else                { nLoss++; sumLoss += g_t[i].neto; }

      eq += g_t[i].neto;
      if(eq > peak) peak = eq;
      double dd = peak - eq;
      if(dd > maxDd) maxDd = dd;

      if(g_t[i].motivo == "SL")         nSl++;
      else if(g_t[i].motivo == "TP")    nTp++;
      else if(g_t[i].motivo == "TIEMPO")nTime++;
      else                              nClose++;
   }

   if(n == 0)
   {
      FileWrite(fh, hip, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);
      return;
   }

   double wr      = 100.0 * nWin / n;
   double avgWin  = (nWin  > 0) ? sumWin / nWin   : 0.0;
   double avgLoss = (nLoss > 0) ? sumLoss / nLoss : 0.0;
   double esp     = total / n;
   double avgDur  = sumDur / n;
   double pf      = (sumLoss != 0.0) ? (sumWin / MathAbs(sumLoss)) : 0.0;
   double perMes  = (nMeses > 0) ? (double)n / nMeses : 0.0;

   FileWrite(fh,
             hip,
             n,
             DoubleToString(perMes, 1),
             DoubleToString(wr, 2),
             DoubleToString(avgWin, 2),
             DoubleToString(avgLoss, 2),
             DoubleToString(esp, 3),
             DoubleToString(avgDur, 1),
             DoubleToString(pf, 3),
             DoubleToString(total, 1),
             DoubleToString(maxDd, 1),
             nTp, nSl, nTime, nClose);
}

//+------------------------------------------------------------------+
//| Script principal                                                  |
//+------------------------------------------------------------------+
void OnStart()
{
   if(_Period != PERIOD_M1)
      Print("AVISO: el grafico no es M1 (", EnumToString((ENUM_TIMEFRAMES)_Period),
            "). Los resultados solo son fiables en M1.");

   ArraySetAsSeries(g_r, false);
   g_n = CopyRates(_Symbol, PERIOD_M1, 0, InpMaxBars, g_r);
   if(g_n <= 0)
   {
      Print("ERROR: CopyRates fallo (", GetLastError(),
            "). Abre el grafico M1, desplazalo al inicio del historico y reintenta.");
      return;
   }
   Print("Velas M1 cargadas: ", g_n,
         "  desde ", TimeToString(g_r[0].time, TIME_DATE|TIME_MINUTES),
         "  hasta ", TimeToString(g_r[g_n - 1].time, TIME_DATE|TIME_MINUTES));

   BuildDayIndex();
   Print("Dias CET indexados: ", g_days);

   ArrayResize(g_t, 4096);
   g_nt = 0;

   int nSesiones = 0;

   // cierre de la sesion cash anterior (22:00 CET). Referencia real del gap:
   // el CFD cotiza ~22.4h, asi que entre 15:29 y 15:30 NO hay hueco ninguno.
   double prevSessClose = 0.0;

   for(int d = 0; d < g_days; d++)
   {
      int dow = g_dayDow[d];
      if(dow == 0 || dow == 6) continue;

      int ini = g_dayIni[d];
      int fin = g_dayFin[d];

      //--- rango pre-apertura 14:00-15:29, apertura y cierre 22:00 ---
      double preHi = 0.0, preLo = 0.0;
      int    openIdx  = -1;
      double sessClose = 0.0;

      for(int i = ini; i <= fin; i++)
      {
         int m = CetMin(g_r[i].time);
         if(m >= PRE_INI && m <= PRE_FIN)
         {
            if(preHi == 0.0) { preHi = g_r[i].high; preLo = g_r[i].low; }
            else
            {
               if(g_r[i].high > preHi) preHi = g_r[i].high;
               if(g_r[i].low  < preLo) preLo = g_r[i].low;
            }
         }
         if(openIdx < 0 && m >= OPEN_MIN) openIdx = i;
         if(m >= OPEN_MIN && m <= SESS_FIN) sessClose = g_r[i].close;
      }

      if(openIdx < 0 || preHi == 0.0) { if(sessClose > 0.0) prevSessClose = sessClose; continue; }
      nSesiones++;

      double openPx  = g_r[openIdx].open;
      double preRng  = preHi - preLo;
      double gap     = (prevSessClose > 0.0) ? (openPx - prevSessClose) : 0.0;
      string fecha   = g_dayKey[d];

      double px, mfe, mae;
      int    exMin, dur;
      string motivo;

      //=============================================================
      // H1  ruptura del rango pre-apertura
      //=============================================================
      double lvlUp = preHi + InpH1Buffer;
      double lvlDn = preLo - InpH1Buffer;

      for(int i = openIdx; i <= fin; i++)
      {
         int m = CetMin(g_r[i].time);
         if(m >= SESS_FIN - InpMaxMin) break;

         int dir = 0;
         double entry = 0.0;
         if(g_r[i].high >= lvlUp)      { dir =  1; entry = lvlUp; }
         else if(g_r[i].low <= lvlDn)  { dir = -1; entry = lvlDn; }

         if(dir != 0)
         {
            Simulate(i, fin, dir, entry, m, px, exMin, dur, motivo, mfe, mae);
            AddTrade(1, fecha, dow, dir, m, entry, exMin, px, dur, motivo,
                     mfe, mae, preRng, gap);
            break;   // una sola entrada por sesion
         }
      }

      //=============================================================
      // H2  momentum de los primeros InpMomWin minutos
      //=============================================================
      int momIdx = -1;
      for(int i = openIdx; i <= fin; i++)
      {
         int m = CetMin(g_r[i].time);
         if(m >= OPEN_MIN + InpMomWin) { momIdx = i; break; }
      }

      if(momIdx >= 0)
      {
         double push = g_r[momIdx].open - openPx;
         if(MathAbs(push) >= InpMomMin)
         {
            int    dir   = (push > 0) ? 1 : -1;
            double entry = g_r[momIdx].open;
            int    m     = CetMin(g_r[momIdx].time);
            Simulate(momIdx, fin, dir, entry, m, px, exMin, dur, motivo, mfe, mae);
            AddTrade(2, fecha, dow, dir, m, entry, exMin, px, dur, motivo,
                     mfe, mae, push, gap);
         }
      }

      //=============================================================
      // H3  reversion del gap de apertura
      //=============================================================
      if(prevSessClose > 0.0 && MathAbs(gap) >= InpGapMin)
      {
         int    dir   = (gap > 0) ? -1 : 1;   // contra el gap
         double entry = openPx;
         int    m     = CetMin(g_r[openIdx].time);
         Simulate(openIdx, fin, dir, entry, m, px, exMin, dur, motivo, mfe, mae);
         AddTrade(3, fecha, dow, dir, m, entry, exMin, px, dur, motivo,
                  mfe, mae, preRng, gap);
      }

      //--- esta sesion pasa a ser la referencia de la siguiente ------
      if(sessClose > 0.0) prevSessClose = sessClose;
   }

   Print("Sesiones validas: ", nSesiones, "   trades simulados: ", g_nt);

   //--- fichero de trades ---------------------------------------------
   int fh = FileOpen(InpOutTrades, FILE_WRITE | FILE_CSV | FILE_ANSI, ';');
   if(fh == INVALID_HANDLE)
   {
      Print("ERROR abriendo ", InpOutTrades, " (", GetLastError(), ")");
      return;
   }
   FileWrite(fh, "hip", "fecha", "dow", "dir", "entry_cet", "entry_px",
             "exit_cet", "exit_px", "pts_bruto", "pts_neto", "dur_min",
             "motivo", "mfe", "mae", "ctx1", "gap");

   for(int i = 0; i < g_nt; i++)
   {
      FileWrite(fh,
                g_t[i].hip,
                g_t[i].fecha,
                g_t[i].dow,
                g_t[i].dir,
                HM(g_t[i].entryMin),
                DoubleToString(g_t[i].entryPx, 2),
                HM(g_t[i].exitMin),
                DoubleToString(g_t[i].exitPx, 2),
                DoubleToString(g_t[i].bruto, 2),
                DoubleToString(g_t[i].neto, 2),
                g_t[i].dur,
                g_t[i].motivo,
                DoubleToString(g_t[i].mfe, 2),
                DoubleToString(g_t[i].mae, 2),
                DoubleToString(g_t[i].ctx1, 2),
                DoubleToString(g_t[i].gap, 2));
   }
   FileClose(fh);

   //--- fichero de resumen --------------------------------------------
   int nMeses = (int)MathMax(1, MathRound(nSesiones / 21.0));

   int fs = FileOpen(InpOutSummary, FILE_WRITE | FILE_CSV | FILE_ANSI, ';');
   if(fs == INVALID_HANDLE)
   {
      Print("ERROR abriendo ", InpOutSummary, " (", GetLastError(), ")");
      return;
   }
   FileWrite(fs, "hip", "n_trades", "trades_mes", "wr_pct", "medio_ganador",
             "medio_perdedor", "esperanza_neta", "dur_media_min", "profit_factor",
             "total_pts", "max_dd_pts", "n_tp", "n_sl", "n_tiempo", "n_cierre2200");

   WriteSummary(fs, 1, nMeses);
   WriteSummary(fs, 2, nMeses);
   WriteSummary(fs, 3, nMeses);

   // fila de referencia: la firma de THL que hay que igualar
   FileWrite(fs, "THL", 2400, "47.0", "65.83", "22.02", "-24.35", "6.18",
             "169.0", "1.741", "", "", "", "", "", "");
   FileClose(fs);

   Print("Escrito: ", InpOutTrades, " y ", InpOutSummary,
         "  en <carpeta de datos>\\MQL5\\Files\\");
   Print("Meses estimados: ", nMeses, " (", nSesiones, " sesiones / 21)");
}
//+------------------------------------------------------------------+
