//+------------------------------------------------------------------+
//|                                    THL_SessionFingerprint.mq5    |
//|  Exporta una fila por sesion con la "forma" del dia.             |
//|  ~161 filas x 26 columnas  ->  ~25 KB                            |
//|                                                                  |
//|  Tambien exporta THL_calibration.csv (24 filas) para deducir     |
//|  el desfase entre la hora del servidor y CET.                    |
//+------------------------------------------------------------------+
#property script_show_inputs
#property strict

input int    InpCETOffset   = 0;                    // Horas a SUMAR al tiempo del servidor para obtener CET
input int    InpMaxBars     = 600000;               // Maximo de velas M1 a leer
input string InpOutSessions = "THL_sessions.csv";   // Fichero de salida (sesiones)
input string InpOutCalib    = "THL_calibration.csv";// Fichero de salida (calibracion horaria)

//--- ventanas horarias en MINUTOS desde medianoche CET
#define ASIA_INI    120   // 02:00
#define ASIA_FIN    479   // 07:59
#define EU_INI      540   // 09:00
#define EU_FIN      929   // 15:29
#define PRE_INI     840   // 14:00
#define PRE_FIN     929   // 15:29
#define OPEN_MIN    930   // 15:30  apertura cash US
#define SESS_FIN    1320  // 22:00  cierre cash US

MqlRates g_r[];
int      g_n = 0;

//--- indice de dias
int  g_dayIni[];
int  g_dayFin[];
int  g_dayKey[];
int  g_dayDow[];
int  g_days = 0;

//+------------------------------------------------------------------+
int CetMin(const datetime t)
  {
   MqlDateTime d;
   TimeToStruct(t + (long)InpCETOffset*3600, d);
   return(d.hour*60 + d.min);
  }
//+------------------------------------------------------------------+
int CetKey(const datetime t)
  {
   MqlDateTime d;
   TimeToStruct(t + (long)InpCETOffset*3600, d);
   return(d.year*10000 + d.mon*100 + d.day);
  }
//+------------------------------------------------------------------+
int CetDow(const datetime t)
  {
   MqlDateTime d;
   TimeToStruct(t + (long)InpCETOffset*3600, d);
   return(d.day_of_week);
  }
//+------------------------------------------------------------------+
void BuildDayIndex()
  {
   ArrayResize(g_dayIni, 4096); ArrayResize(g_dayFin, 4096);
   ArrayResize(g_dayKey, 4096); ArrayResize(g_dayDow, 4096);
   g_days = 0;
   int prevKey = -1;
   for(int i=0; i<g_n; i++)
     {
      int k = CetKey(g_r[i].time);
      if(k != prevKey)
        {
         if(g_days > 0) g_dayFin[g_days-1] = i-1;
         if(g_days >= ArraySize(g_dayIni))
           {
            int ns = ArraySize(g_dayIni)*2;
            ArrayResize(g_dayIni,ns); ArrayResize(g_dayFin,ns);
            ArrayResize(g_dayKey,ns); ArrayResize(g_dayDow,ns);
           }
         g_dayIni[g_days] = i;
         g_dayKey[g_days] = k;
         g_dayDow[g_days] = CetDow(g_r[i].time);
         g_days++;
         prevKey = k;
        }
     }
   if(g_days > 0) g_dayFin[g_days-1] = g_n-1;
  }
//+------------------------------------------------------------------+
void OnStart()
  {
   ArraySetAsSeries(g_r, false);
   g_n = CopyRates(_Symbol, PERIOD_M1, 0, InpMaxBars, g_r);
   if(g_n <= 0)
     {
      Print("ERROR: CopyRates devolvio ", g_n, " (err=", GetLastError(),
            "). Abre un grafico M1 de ", _Symbol, " y desplazalo al inicio del historico.");
      return;
     }
   Print("Velas M1 leidas: ", g_n,
         "  |  desde ", TimeToString(g_r[0].time),
         "  hasta ", TimeToString(g_r[g_n-1].time));

   BuildDayIndex();
   Print("Dias detectados (CET): ", g_days);

   //================ 1. CALIBRACION HORARIA ========================
   long cntBars[24], cntGapIni[24];
   ArrayInitialize(cntBars, 0);
   ArrayInitialize(cntGapIni, 0);
   int  maxGap = 0; datetime maxGapAt = 0;

   for(int i=0; i<g_n; i++)
     {
      int h = CetMin(g_r[i].time)/60;
      cntBars[h]++;
      if(i>0)
        {
         int gap = (int)((g_r[i].time - g_r[i-1].time)/60);
         if(gap >= 20)                       // hueco relevante
           {
            cntGapIni[CetMin(g_r[i-1].time)/60]++;
            if(gap > maxGap && gap < 400) { maxGap = gap; maxGapAt = g_r[i-1].time; }
           }
        }
     }

   int fc = FileOpen(InpOutCalib, FILE_WRITE|FILE_CSV|FILE_ANSI, ';');
   if(fc == INVALID_HANDLE) { Print("ERROR abriendo ", InpOutCalib); return; }
   FileWrite(fc, "hora_cet", "n_velas", "n_huecos_que_empiezan_esta_hora");
   for(int h=0; h<24; h++) FileWrite(fc, h, cntBars[h], cntGapIni[h]);
   FileClose(fc);
   Print("Hueco diario mas frecuente: revisa THL_calibration.csv. ",
         "Hueco maximo=", maxGap, " min tras ", TimeToString(maxGapAt));

   //================ 2. HUELLA POR SESION ==========================
   int fh = FileOpen(InpOutSessions, FILE_WRITE|FILE_CSV|FILE_ANSI, ';');
   if(fh == INVALID_HANDLE) { Print("ERROR abriendo ", InpOutSessions); return; }

   FileWrite(fh,
      "fecha","dow","n_velas","primera_cet","ultima_cet",
      "prev_close","asia_hi","asia_lo","eu_hi","eu_lo",
      "pre_hi","pre_lo","pre_rango","open_1530","gap_pts",
      "c_1545","c_1600","c_1630","c_1700",
      "sess_hi","sess_lo","sess_close_2200",
      "mfe_up","mfe_dn","min_hasta_hi","min_hasta_lo","rango_dia");

   int emitidas = 0;

   for(int d=0; d<g_days; d++)
     {
      int a = g_dayIni[d], b = g_dayFin[d];
      if(g_dayDow[d]==0 || g_dayDow[d]==6) continue;   // fuera fin de semana

      double asiaHi=0, asiaLo=0, euHi=0, euLo=0, preHi=0, preLo=0;
      double open1530=0, sessHi=0, sessLo=0, close2200=0;
      double c1545=0, c1600=0, c1630=0, c1700=0;
      double dayHi=g_r[a].high, dayLo=g_r[a].low;
      int    minHi=-1, minLo=-1, openIdx=-1;

      for(int i=a; i<=b; i++)
        {
         int m = CetMin(g_r[i].time);
         double hi=g_r[i].high, lo=g_r[i].low;
         if(hi>dayHi) dayHi=hi;
         if(lo<dayLo) dayLo=lo;

         if(m>=ASIA_INI && m<=ASIA_FIN)
           { if(asiaHi==0||hi>asiaHi) asiaHi=hi; if(asiaLo==0||lo<asiaLo) asiaLo=lo; }
         if(m>=EU_INI && m<=EU_FIN)
           { if(euHi==0||hi>euHi) euHi=hi;       if(euLo==0||lo<euLo) euLo=lo; }
         if(m>=PRE_INI && m<=PRE_FIN)
           { if(preHi==0||hi>preHi) preHi=hi;    if(preLo==0||lo<preLo) preLo=lo; }

         if(openIdx<0 && m>=OPEN_MIN) { openIdx=i; open1530=g_r[i].open; }

         if(openIdx>=0 && m>=OPEN_MIN && m<=SESS_FIN)
           {
            if(sessHi==0 || hi>sessHi) { sessHi=hi; minHi=m-OPEN_MIN; }
            if(sessLo==0 || lo<sessLo) { sessLo=lo; minLo=m-OPEN_MIN; }
            close2200 = g_r[i].close;
            if(c1545==0 && m>=945)  c1545=g_r[i].close;
            if(c1600==0 && m>=960)  c1600=g_r[i].close;
            if(c1630==0 && m>=990)  c1630=g_r[i].close;
            if(c1700==0 && m>=1020) c1700=g_r[i].close;
           }
        }

      if(openIdx<0 || preHi==0) continue;               // sesion incompleta

      double prevClose = (a>0 ? g_r[a-1].close : 0.0);

      FileWrite(fh,
        g_dayKey[d], g_dayDow[d], (b-a+1),
        CetMin(g_r[a].time), CetMin(g_r[b].time),
        DoubleToString(prevClose,2),
        DoubleToString(asiaHi,2), DoubleToString(asiaLo,2),
        DoubleToString(euHi,2),   DoubleToString(euLo,2),
        DoubleToString(preHi,2),  DoubleToString(preLo,2),
        DoubleToString(preHi-preLo,2),
        DoubleToString(open1530,2),
        DoubleToString(prevClose>0 ? open1530-prevClose : 0.0, 2),
        DoubleToString(c1545,2), DoubleToString(c1600,2),
        DoubleToString(c1630,2), DoubleToString(c1700,2),
        DoubleToString(sessHi,2), DoubleToString(sessLo,2),
        DoubleToString(close2200,2),
        DoubleToString(sessHi-open1530,2),
        DoubleToString(open1530-sessLo,2),
        minHi, minLo,
        DoubleToString(dayHi-dayLo,2));
      emitidas++;
     }

   FileClose(fh);
   Print("LISTO. Sesiones exportadas: ", emitidas);
   Print("Ficheros en: <carpeta de datos MT5>\\MQL5\\Files\\");
  }
//+------------------------------------------------------------------+
