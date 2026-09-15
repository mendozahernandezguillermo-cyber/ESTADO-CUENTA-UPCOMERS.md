//+------------------------------------------------------------------+
//|                                            THL_TriggerBench2.mq5 |
//|                                                                  |
//|  v2 del banco de pruebas. Cambios frente a v1:                   |
//|                                                                  |
//|   1. Salida PRINCIPAL por tiempo (169 min = media de THL).       |
//|      El nivel tp_sl = 0 desactiva TP y SL por completo: es la    |
//|      medicion limpia del edge direccional de cada disparador.    |
//|   2. Escalera de TP/SL simetricos (50..300 pts) para ver como    |
//|      cambia acierto y duracion con el tamano del objetivo.       |
//|   3. H1 entra al CIERRE de la vela que rompe (fill realista) y   |
//|      la simulacion arranca en la vela SIGUIENTE.                 |
//|   4. Columna n_ambig: trades en que TP y SL caben en la misma    |
//|      vela M1. Es el sesgo que contamino la v1; ahora se ve.      |
//|   5. Percentiles de MFE/MAE para dimensionar objetivos con       |
//|      datos en vez de a ojo.                                      |
//|                                                                  |
//|  Ejecutar sobre grafico M1 de NACUSD.c                           |
//|  Salida: MQL5\Files\THL_ladder.csv    (22 filas)                 |
//|          MQL5\Files\THL_context.csv   ( 6 filas)                 |
//+------------------------------------------------------------------+
#property script_show_inputs
#property strict

input int    InpCETOffset = 0;      // Horas a SUMAR al tiempo del servidor -> CET (calibrado: 0)
input int    InpMaxBars   = 600000; // Maximo de velas M1 a cargar
input double InpSpreadPts = 0.70;   // Coste ida+vuelta, en puntos de indice
input int    InpMaxMin    = 169;    // Salida por tiempo, en minutos (media de THL)
input double InpH1Buffer  = 2.0;    // H1: margen sobre el extremo del rango
input int    InpMomWin    = 15;     // H2: minutos de momentum tras la apertura
input double InpMomMin    = 8.0;    // H2: empuje minimo para validar la senal
input double InpGapMin    = 15.0;   // H3: gap minimo (abs) para operar
input string InpOutLadder = "THL_ladder.csv";
input string InpOutContext = "THL_context.csv";

//--- ventanas en minutos desde medianoche CET
#define PRE_INI   840   // 14:00
#define PRE_FIN   929   // 15:29
#define OPEN_MIN  930   // 15:30  apertura cash US
#define VOL_FIN  1020   // 17:00  fin de la ventana de volatilidad medida
#define SESS_FIN 1320   // 22:00  cierre cash US (plano overnight)

//--- motivos de salida
#define MOT_TP    1
#define MOT_SL    2
#define MOT_TIME  3
#define MOT_CLOSE 4
#define MOT_EOD   5

//--- escalera de TP/SL. 0 = sin TP ni SL, solo salida por tiempo.
double g_lad[7] = {0.0, 50.0, 100.0, 150.0, 200.0, 250.0, 300.0};

//--- datos de mercado
MqlRates g_r[];
int      g_n = 0;

//--- indice de dias CET
int    g_dayIni[];
int    g_dayFin[];
int    g_dayKey[];
int    g_dayDow[];
int    g_days = 0;

//+------------------------------------------------------------------+
//| Una sesion util, precalculada una sola vez                        |
//+------------------------------------------------------------------+
struct Sess
{
   int    ini, fin, openIdx;
   int    dow, key;
   double preHi, preLo, openPx, gap;
   double rng1min;    // rango medio de vela M1 entre 15:30 y 17:00
   double rngPre;     // rango 14:00-15:29
   double rngSess;    // rango 15:30-22:00
   double mfeUp;      // sessHi - open1530
   double mfeDn;      // open1530 - sessLo
};
Sess g_s[];
int   g_ns = 0;

//+------------------------------------------------------------------+
//| Un trade simulado                                                 |
//+------------------------------------------------------------------+
struct Tr
{
   int    hip;
   double neto;
   int    dur;
   int    mot;
   double mfe, mae;
   bool   ambig;
};
Tr   g_t[];
int  g_nt = 0;

//+------------------------------------------------------------------+
//| Tiempo CET                                                        |
//+------------------------------------------------------------------+
int CetMin(const datetime t)
{
   MqlDateTime d;
   TimeToStruct(t + (long)InpCETOffset * 3600, d);
   return(d.hour * 60 + d.min);
}

int CetKey(const datetime t)
{
   MqlDateTime d;
   TimeToStruct(t + (long)InpCETOffset * 3600, d);
   return(d.year * 10000 + d.mon * 100 + d.day);
}

int CetDow(const datetime t)
{
   MqlDateTime d;
   TimeToStruct(t + (long)InpCETOffset * 3600, d);
   return(d.day_of_week);
}

//+------------------------------------------------------------------+
//| Percentil (0.0 - 1.0) sobre los n primeros elementos              |
//+------------------------------------------------------------------+
double Pctl(double &a[], int n, double p)
{
   if(n <= 0) return(0.0);
   double tmp[];
   ArrayResize(tmp, n);
   ArrayCopy(tmp, a, 0, 0, n);
   ArraySort(tmp);
   int idx = (int)MathRound(p * (n - 1));
   if(idx < 0)     idx = 0;
   if(idx > n - 1) idx = n - 1;
   return(tmp[idx]);
}

//+------------------------------------------------------------------+
//| Indice de dias                                                    |
//+------------------------------------------------------------------+
void BuildDayIndex()
{
   int cap = 4096;
   ArrayResize(g_dayIni, cap); ArrayResize(g_dayFin, cap);
   ArrayResize(g_dayKey, cap); ArrayResize(g_dayDow, cap);
   g_days = 0;
   int prevKey = -1;

   for(int i = 0; i < g_n; i++)
   {
      int k = CetKey(g_r[i].time);
      if(k != prevKey)
      {
         if(g_days > 0) g_dayFin[g_days - 1] = i - 1;
         if(g_days >= cap)
         {
            cap *= 2;
            ArrayResize(g_dayIni, cap); ArrayResize(g_dayFin, cap);
            ArrayResize(g_dayKey, cap); ArrayResize(g_dayDow, cap);
         }
         g_dayIni[g_days] = i;
         g_dayKey[g_days] = k;
         g_dayDow[g_days] = CetDow(g_r[i].time);
         g_days++;
         prevKey = k;
      }
   }
   if(g_days > 0) g_dayFin[g_days - 1] = g_n - 1;
}

//+------------------------------------------------------------------+
//| Precalculo de sesiones utiles                                     |
//+------------------------------------------------------------------+
void BuildSessions()
{
   ArrayResize(g_s, g_days);
   g_ns = 0;
   double prevSessClose = 0.0;

   for(int d = 0; d < g_days; d++)
   {
      if(g_dayDow[d] == 0 || g_dayDow[d] == 6) continue;

      int a = g_dayIni[d], b = g_dayFin[d];

      double preHi = 0.0, preLo = 0.0;
      double sHi = 0.0, sLo = 0.0, sClose = 0.0;
      double sumRng = 0.0; int nRng = 0;
      int    openIdx = -1;

      for(int i = a; i <= b; i++)
      {
         int    m  = CetMin(g_r[i].time);
         double hi = g_r[i].high, lo = g_r[i].low;

         if(m >= PRE_INI && m <= PRE_FIN)
         {
            if(preHi == 0.0) { preHi = hi; preLo = lo; }
            else { if(hi > preHi) preHi = hi; if(lo < preLo) preLo = lo; }
         }
         if(openIdx < 0 && m >= OPEN_MIN) openIdx = i;
         if(m >= OPEN_MIN && m <= SESS_FIN)
         {
            if(sHi == 0.0) { sHi = hi; sLo = lo; }
            else { if(hi > sHi) sHi = hi; if(lo < sLo) sLo = lo; }
            sClose = g_r[i].close;
         }
         if(m >= OPEN_MIN && m <= VOL_FIN) { sumRng += (hi - lo); nRng++; }
      }

      if(openIdx < 0 || preHi == 0.0 || nRng == 0)
      {
         if(sClose > 0.0) prevSessClose = sClose;
         continue;
      }

      double openPx = g_r[openIdx].open;

      g_s[g_ns].ini     = a;
      g_s[g_ns].fin     = b;
      g_s[g_ns].openIdx = openIdx;
      g_s[g_ns].dow     = g_dayDow[d];
      g_s[g_ns].key     = g_dayKey[d];
      g_s[g_ns].preHi   = preHi;
      g_s[g_ns].preLo   = preLo;
      g_s[g_ns].openPx  = openPx;
      g_s[g_ns].gap     = (prevSessClose > 0.0) ? (openPx - prevSessClose) : 0.0;
      g_s[g_ns].rng1min = sumRng / nRng;
      g_s[g_ns].rngPre  = preHi - preLo;
      g_s[g_ns].rngSess = sHi - sLo;
      g_s[g_ns].mfeUp   = sHi - openPx;
      g_s[g_ns].mfeDn   = openPx - sLo;
      g_ns++;

      if(sClose > 0.0) prevSessClose = sClose;
   }
}

//+------------------------------------------------------------------+
//| Simula una posicion. tpPts <= 0 -> sin TP ni SL.                  |
//+------------------------------------------------------------------+
void Sim(int simFrom, int dayFin, int dir, double entryPx, int entryMin,
         double tpPts, double slPts,
         double &oNet, int &oDur, int &oMot,
         double &oMfe, double &oMae, bool &oAmb)
{
   bool   useTs = (tpPts > 0.0);
   double tp = (dir > 0) ? entryPx + tpPts : entryPx - tpPts;
   double sl = (dir > 0) ? entryPx - slPts : entryPx + slPts;

   oMfe = 0.0; oMae = 0.0; oAmb = false;

   for(int i = simFrom; i <= dayFin; i++)
   {
      int    m  = CetMin(g_r[i].time);
      double hi = g_r[i].high, lo = g_r[i].low, cl = g_r[i].close;

      double up = (dir > 0) ? (hi - entryPx) : (entryPx - lo);
      double dn = (dir > 0) ? (lo - entryPx) : (entryPx - hi);
      if(up > oMfe) oMfe = up;
      if(dn < oMae) oMae = dn;

      if(useTs)
      {
         bool hitSl = (dir > 0) ? (lo <= sl) : (hi >= sl);
         bool hitTp = (dir > 0) ? (hi >= tp) : (lo <= tp);

         if(hitSl && hitTp)
         {
            // ambos niveles dentro de la misma vela M1: no se puede
            // resolver el orden. Se asigna SL y se MARCA el trade.
            oAmb = true;
            oNet = -slPts - InpSpreadPts;
            oDur = m - entryMin;
            oMot = MOT_SL;
            return;
         }
         if(hitSl)
         {
            oNet = -slPts - InpSpreadPts;
            oDur = m - entryMin;
            oMot = MOT_SL;
            return;
         }
         if(hitTp)
         {
            oNet = tpPts - InpSpreadPts;
            oDur = m - entryMin;
            oMot = MOT_TP;
            return;
         }
      }

      if(m >= SESS_FIN)
      {
         oNet = ((dir > 0) ? (cl - entryPx) : (entryPx - cl)) - InpSpreadPts;
         oDur = m - entryMin;
         oMot = MOT_CLOSE;
         return;
      }
      if((m - entryMin) >= InpMaxMin)
      {
         oNet = ((dir > 0) ? (cl - entryPx) : (entryPx - cl)) - InpSpreadPts;
         oDur = m - entryMin;
         oMot = MOT_TIME;
         return;
      }
   }

   double clast = g_r[dayFin].close;
   oNet = ((dir > 0) ? (clast - entryPx) : (entryPx - clast)) - InpSpreadPts;
   oDur = CetMin(g_r[dayFin].time) - entryMin;
   oMot = MOT_EOD;
}

//+------------------------------------------------------------------+
void AddTr(int hip, double net, int dur, int mot, double mfe, double mae, bool amb)
{
   if(g_nt >= ArraySize(g_t)) ArrayResize(g_t, MathMax(2048, g_nt * 2));
   g_t[g_nt].hip   = hip;
   g_t[g_nt].neto  = net;
   g_t[g_nt].dur   = dur;
   g_t[g_nt].mot   = mot;
   g_t[g_nt].mfe   = mfe;
   g_t[g_nt].mae   = mae;
   g_t[g_nt].ambig = amb;
   g_nt++;
}

//+------------------------------------------------------------------+
//| Ejecuta las 3 hipotesis sobre todas las sesiones, a un nivel dado |
//+------------------------------------------------------------------+
void RunLevel(double lvl)
{
   g_nt = 0;
   double net, mfe, mae;
   int    dur, mot;
   bool   amb;

   for(int k = 0; k < g_ns; k++)
   {
      int    fin     = g_s[k].fin;
      int    openIdx = g_s[k].openIdx;
      double openPx  = g_s[k].openPx;

      //--- H1: ruptura del rango pre-apertura, entrada al cierre ----
      double lvlUp = g_s[k].preHi + InpH1Buffer;
      double lvlDn = g_s[k].preLo - InpH1Buffer;

      for(int i = openIdx; i <= fin; i++)
      {
         int m = CetMin(g_r[i].time);
         if(m >= SESS_FIN - InpMaxMin) break;

         int dir = 0;
         if(g_r[i].high >= lvlUp)     dir =  1;
         else if(g_r[i].low <= lvlDn) dir = -1;

         if(dir != 0)
         {
            if(i + 1 <= fin)
            {
               Sim(i + 1, fin, dir, g_r[i].close, m, lvl, lvl,
                   net, dur, mot, mfe, mae, amb);
               AddTr(1, net, dur, mot, mfe, mae, amb);
            }
            break;   // una sola entrada por sesion
         }
      }

      //--- H2: momentum de los primeros InpMomWin minutos -----------
      int momIdx = -1;
      for(int i = openIdx; i <= fin; i++)
      {
         if(CetMin(g_r[i].time) >= OPEN_MIN + InpMomWin) { momIdx = i; break; }
      }
      if(momIdx >= 0)
      {
         double push = g_r[momIdx].open - openPx;
         if(MathAbs(push) >= InpMomMin)
         {
            int dir = (push > 0) ? 1 : -1;
            Sim(momIdx, fin, dir, g_r[momIdx].open, CetMin(g_r[momIdx].time),
                lvl, lvl, net, dur, mot, mfe, mae, amb);
            AddTr(2, net, dur, mot, mfe, mae, amb);
         }
      }

      //--- H3: reversion del gap ------------------------------------
      double gap = g_s[k].gap;
      if(gap != 0.0 && MathAbs(gap) >= InpGapMin)
      {
         int dir = (gap > 0) ? -1 : 1;
         Sim(openIdx, fin, dir, openPx, CetMin(g_r[openIdx].time),
             lvl, lvl, net, dur, mot, mfe, mae, amb);
         AddTr(3, net, dur, mot, mfe, mae, amb);
      }
   }
}

//+------------------------------------------------------------------+
//| Vuelca una fila de resumen                                        |
//+------------------------------------------------------------------+
void WriteRow(int fh, int hip, double lvl, int nMeses)
{
   int    n = 0, nWin = 0, nLoss = 0, nAmb = 0;
   int    nTp = 0, nSl = 0, nTime = 0, nClose = 0;
   double sumWin = 0.0, sumLoss = 0.0, sumDur = 0.0, total = 0.0;
   double eq = 0.0, peak = 0.0, maxDd = 0.0;

   double mfeArr[], maeArr[];
   ArrayResize(mfeArr, g_nt);
   ArrayResize(maeArr, g_nt);

   for(int i = 0; i < g_nt; i++)
   {
      if(g_t[i].hip != hip) continue;

      mfeArr[n] = g_t[i].mfe;
      maeArr[n] = g_t[i].mae;
      n++;

      total  += g_t[i].neto;
      sumDur += g_t[i].dur;
      if(g_t[i].ambig) nAmb++;

      if(g_t[i].neto > 0.0) { nWin++;  sumWin  += g_t[i].neto; }
      else                  { nLoss++; sumLoss += g_t[i].neto; }

      eq += g_t[i].neto;
      if(eq > peak) peak = eq;
      if(peak - eq > maxDd) maxDd = peak - eq;

      if(g_t[i].mot == MOT_TP)        nTp++;
      else if(g_t[i].mot == MOT_SL)   nSl++;
      else if(g_t[i].mot == MOT_TIME) nTime++;
      else                            nClose++;
   }

   if(n == 0)
   {
      FileWrite(fh, hip, DoubleToString(lvl, 0), 0, 0, 0, 0, 0, 0, 0, 0,
                0, 0, 0, 0, 0, 0, 0, 0);
      return;
   }

   double wr  = 100.0 * nWin / n;
   double esp = total / n;
   double pf  = (sumLoss != 0.0) ? (sumWin / MathAbs(sumLoss)) : 0.0;

   FileWrite(fh,
             hip,
             DoubleToString(lvl, 0),
             n,
             DoubleToString((nMeses > 0) ? (double)n / nMeses : 0.0, 1),
             DoubleToString(wr, 2),
             DoubleToString(esp, 2),
             DoubleToString(sumDur / n, 1),
             DoubleToString(pf, 3),
             DoubleToString(total, 0),
             DoubleToString(maxDd, 0),
             nTp, nSl, nTime, nClose, nAmb,
             DoubleToString(Pctl(mfeArr, n, 0.50), 1),
             DoubleToString(Pctl(maeArr, n, 0.50), 1),
             DoubleToString(Pctl(mfeArr, n, 0.90), 1));
}

//+------------------------------------------------------------------+
//| Una linea de contexto de volatilidad                              |
//+------------------------------------------------------------------+
void WriteCtx(int fc, string nombre, double &src[], int n)
{
   FileWrite(fc, nombre,
             DoubleToString(Pctl(src, n, 0.10), 1),
             DoubleToString(Pctl(src, n, 0.25), 1),
             DoubleToString(Pctl(src, n, 0.50), 1),
             DoubleToString(Pctl(src, n, 0.75), 1),
             DoubleToString(Pctl(src, n, 0.90), 1));
}

//+------------------------------------------------------------------+
void OnStart()
{
   if(_Period != PERIOD_M1)
      Print("AVISO: el grafico no es M1. Los resultados solo valen en M1.");

   ArraySetAsSeries(g_r, false);
   g_n = CopyRates(_Symbol, PERIOD_M1, 0, InpMaxBars, g_r);
   if(g_n <= 0)
   {
      Print("ERROR: CopyRates fallo (", GetLastError(),
            "). Abre el grafico M1, pulsa Inicio y reintenta.");
      return;
   }
   Print("Velas M1: ", g_n,
         "  de ", TimeToString(g_r[0].time, TIME_DATE|TIME_MINUTES),
         " a ",  TimeToString(g_r[g_n - 1].time, TIME_DATE|TIME_MINUTES));

   BuildDayIndex();
   BuildSessions();
   Print("Dias: ", g_days, "   sesiones utiles: ", g_ns);

   if(g_ns == 0) { Print("ERROR: 0 sesiones utiles."); return; }

   int nMeses = (int)MathMax(1.0, MathRound(g_ns / 21.0));
   ArrayResize(g_t, 4096);

   //================ escalera ======================================
   int fh = FileOpen(InpOutLadder, FILE_WRITE | FILE_CSV | FILE_ANSI, ';');
   if(fh == INVALID_HANDLE)
   {
      Print("ERROR abriendo ", InpOutLadder, " (", GetLastError(), ")");
      return;
   }

   FileWrite(fh, "hip", "tp_sl", "n", "trades_mes", "wr_pct", "esp_neta",
             "dur_med", "pf", "total_pts", "maxdd_pts",
             "n_tp", "n_sl", "n_tiempo", "n_cierre", "n_ambig",
             "mfe_p50", "mae_p50", "mfe_p90");

   for(int L = 0; L < 7; L++)
   {
      RunLevel(g_lad[L]);
      WriteRow(fh, 1, g_lad[L], nMeses);
      WriteRow(fh, 2, g_lad[L], nMeses);
      WriteRow(fh, 3, g_lad[L], nMeses);
   }

   FileWrite(fh, "THL", "?", 2400, "47.0", "65.83", "?", "169.0", "1.741",
             "", "", "", "", "", "", "", "", "", "");
   FileClose(fh);

   //================ contexto de volatilidad =======================
   double a1[], a2[], a3[], a4[], a5[];
   ArrayResize(a1, g_ns); ArrayResize(a2, g_ns); ArrayResize(a3, g_ns);
   ArrayResize(a4, g_ns); ArrayResize(a5, g_ns);

   for(int k = 0; k < g_ns; k++)
   {
      a1[k] = g_s[k].rng1min;
      a2[k] = g_s[k].rngPre;
      a3[k] = g_s[k].rngSess;
      a4[k] = g_s[k].mfeUp;
      a5[k] = g_s[k].mfeDn;
   }

   int fc = FileOpen(InpOutContext, FILE_WRITE | FILE_CSV | FILE_ANSI, ';');
   if(fc == INVALID_HANDLE)
   {
      Print("ERROR abriendo ", InpOutContext, " (", GetLastError(), ")");
      return;
   }
   FileWrite(fc, "metrica", "p10", "p25", "p50", "p75", "p90");

   WriteCtx(fc, "rango_medio_vela_1min_1530_1700", a1, g_ns);
   WriteCtx(fc, "rango_pre_1400_1529",             a2, g_ns);
   WriteCtx(fc, "rango_sesion_1530_2200",          a3, g_ns);
   WriteCtx(fc, "mfe_alcista_desde_1530",          a4, g_ns);
   WriteCtx(fc, "mfe_bajista_desde_1530",          a5, g_ns);

   FileClose(fc);

   Print("LISTO. ", InpOutLadder, " (22 filas) y ", InpOutContext, " (6 filas)");
   Print("Meses estimados: ", nMeses);
}
//+------------------------------------------------------------------+
