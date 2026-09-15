//+------------------------------------------------------------------+
//|                                            NAS_MedirSenal.mq5    |
//|                                                                  |
//|  Mide la senal de momentum de apertura sobre TU instrumento, para  |
//|  compararla con lo que dan mis datos de Dukascopy.                |
//|                                                                  |
//|  Existe una discrepancia sin explicar: sobre 2026-01-16..08-28,   |
//|  mis datos dan 72 dias con empuje > 5 bp y tu Probador dio 37.    |
//|  Hasta saber de donde sale esa diferencia no se puede construir   |
//|  nada encima.                                                     |
//|                                                                  |
//|  Ejecutar como SCRIPT sobre un grafico M1 de NACUSD.c             |
//|  Salida: MQL5\Files\NAS_senal.csv    (~10 filas)                 |
//|          MQL5\Files\NAS_calidad.csv  (~8 filas)                  |
//+------------------------------------------------------------------+
#property script_show_inputs
#property strict

input int    InpOpenMin     = 930;   // Apertura cash, minutos desde medianoche (15:30)
input int    InpCloseMin    = 1320;  // Cierre, minutos desde medianoche (22:00)
input int    InpWindow      = 15;    // Ventana de medida del empuje (min)
input double InpPushBp      = 5.0;   // Umbral de empuje (bp)
input double InpCostBp      = 0.40;  // Coste ida+vuelta (bp)
input int    InpMaxBars     = 600000;
input string InpOutSenal    = "NAS_senal.csv";
input string InpOutCalidad  = "NAS_calidad.csv";

MqlRates g_r[];
int      g_n = 0;

int      g_ini[];   // indice de primera vela de cada dia
int      g_fin[];
int      g_key[];
int      g_dow[];
int      g_nd = 0;

//+------------------------------------------------------------------+
int MinDia(const datetime t)
{
   MqlDateTime d; TimeToStruct(t, d);
   return(d.hour * 60 + d.min);
}
int Clave(const datetime t)
{
   MqlDateTime d; TimeToStruct(t, d);
   return(d.year * 10000 + d.mon * 100 + d.day);
}
int Dow(const datetime t)
{
   MqlDateTime d; TimeToStruct(t, d);
   return(d.day_of_week);
}

//+------------------------------------------------------------------+
void IndexarDias()
{
   int cap = 4096;
   ArrayResize(g_ini, cap); ArrayResize(g_fin, cap);
   ArrayResize(g_key, cap); ArrayResize(g_dow, cap);
   g_nd = 0;
   int prev = -1;
   for(int i = 0; i < g_n; i++)
   {
      int k = Clave(g_r[i].time);
      if(k != prev)
      {
         if(g_nd > 0) g_fin[g_nd - 1] = i - 1;
         if(g_nd >= cap)
         {
            cap *= 2;
            ArrayResize(g_ini, cap); ArrayResize(g_fin, cap);
            ArrayResize(g_key, cap); ArrayResize(g_dow, cap);
         }
         g_ini[g_nd] = i;
         g_key[g_nd] = k;
         g_dow[g_nd] = Dow(g_r[i].time);
         g_nd++;
         prev = k;
      }
   }
   if(g_nd > 0) g_fin[g_nd - 1] = g_n - 1;
}

//+------------------------------------------------------------------+
//| Busca en el dia d la vela cuyo minuto sea exactamente 'minuto'.  |
//| Devuelve -1 si no existe (hueco en el feed).                     |
//+------------------------------------------------------------------+
int VelaEn(int d, int minuto)
{
   for(int i = g_ini[d]; i <= g_fin[d]; i++)
      if(MinDia(g_r[i].time) == minuto) return(i);
   return(-1);
}

//| Primera vela con minuto >= 'minuto' (tolerante a huecos)         |
int VelaDesde(int d, int minuto)
{
   for(int i = g_ini[d]; i <= g_fin[d]; i++)
      if(MinDia(g_r[i].time) >= minuto) return(i);
   return(-1);
}

//| Ultima vela con minuto <= 'minuto'                                |
int VelaHasta(int d, int minuto)
{
   int r = -1;
   for(int i = g_ini[d]; i <= g_fin[d]; i++)
      if(MinDia(g_r[i].time) <= minuto) r = i; else break;
   return(r);
}

//+------------------------------------------------------------------+
void OnStart()
{
   ArraySetAsSeries(g_r, false);
   g_n = CopyRates(_Symbol, PERIOD_M1, 0, InpMaxBars, g_r);
   if(g_n <= 0)
   {
      Print("ERROR: CopyRates fallo (", GetLastError(),
            "). Abre el grafico M1, pulsa Inicio y reintenta.");
      return;
   }
   Print("Velas M1: ", g_n, "  de ",
         TimeToString(g_r[0].time, TIME_DATE|TIME_MINUTES), " a ",
         TimeToString(g_r[g_n - 1].time, TIME_DATE|TIME_MINUTES));

   IndexarDias();
   Print("Dias indexados: ", g_nd);

   //================================================================
   //  BLOQUE 1: calidad de los datos alrededor de la apertura
   //================================================================
   int fc = FileOpen(InpOutCalidad, FILE_WRITE|FILE_CSV|FILE_ANSI, ';');
   if(fc == INVALID_HANDLE) { Print("ERROR abriendo ", InpOutCalidad); return; }
   FileWrite(fc, "metrica", "n", "media_bp", "abs_media_bp");

   // salto open[apertura] vs close[apertura-1]
   double s1 = 0, a1 = 0; int c1 = 0;
   for(int d = 0; d < g_nd; d++)
   {
      if(g_dow[d] == 0 || g_dow[d] == 6) continue;
      int iA = VelaEn(d, InpOpenMin);
      int iB = VelaEn(d, InpOpenMin - 1);
      if(iA < 0 || iB < 0) continue;
      double v = (g_r[iA].open / g_r[iB].close - 1.0) * 10000.0;
      s1 += v; a1 += MathAbs(v); c1++;
   }
   if(c1 > 0)
      FileWrite(fc, "salto_open_vs_close_previo", c1,
                DoubleToString(s1 / c1, 3), DoubleToString(a1 / c1, 3));

   // tamano del movimiento en cada uno de los 6 primeros minutos
   for(int k = 0; k <= 5; k++)
   {
      double s = 0, a = 0; int c = 0;
      for(int d = 0; d < g_nd; d++)
      {
         if(g_dow[d] == 0 || g_dow[d] == 6) continue;
         int i = VelaEn(d, InpOpenMin + k);
         if(i < 0) continue;
         double v = (g_r[i].close / g_r[i].open - 1.0) * 10000.0;
         s += v; a += MathAbs(v); c++;
      }
      if(c > 0)
         FileWrite(fc, "mov_minuto_+" + IntegerToString(k), c,
                   DoubleToString(s / c, 3), DoubleToString(a / c, 3));
   }

   // cuantos dias tienen la vela exacta de apertura (test de huecos)
   int conVela = 0, laborables = 0;
   for(int d = 0; d < g_nd; d++)
   {
      if(g_dow[d] == 0 || g_dow[d] == 6) continue;
      laborables++;
      if(VelaEn(d, InpOpenMin) >= 0) conVela++;
   }
   FileWrite(fc, "dias_laborables", laborables, "", "");
   FileWrite(fc, "con_vela_exacta_apertura", conVela, "", "");
   FileClose(fc);

   //================================================================
   //  BLOQUE 2: la senal, barriendo el ancla
   //================================================================
   int fs = FileOpen(InpOutSenal, FILE_WRITE|FILE_CSV|FILE_ANSI, ';');
   if(fs == INVALID_HANDLE) { Print("ERROR abriendo ", InpOutSenal); return; }
   FileWrite(fs, "ancla_min", "n_sesiones", "n_ops", "pct_ops",
             "media_bp", "sd_bp", "t", "acierto_pct");

   int anclas[8] = {0, 1, 2, 3, 5, 10, 15, 30};

   for(int q = 0; q < 8; q++)
   {
      int off = anclas[q];
      double sum = 0, sum2 = 0;
      int nops = 0, nwin = 0, nses = 0;

      for(int d = 0; d < g_nd; d++)
      {
         if(g_dow[d] == 0 || g_dow[d] == 6) continue;

         int iSal = VelaHasta(d, InpCloseMin);
         if(iSal < 0) continue;
         if(MinDia(g_r[iSal].time) < InpOpenMin + 120) continue;  // sesion corta
         nses++;

         int iA = VelaDesde(d, InpOpenMin + off);
         int iB = VelaDesde(d, InpOpenMin + off + InpWindow);
         if(iA < 0 || iB < 0 || iB <= iA) continue;

         double p0 = g_r[iA].open;
         double p1 = g_r[iB].open;
         if(p0 <= 0.0) continue;

         double push = (p1 / p0 - 1.0) * 10000.0;
         if(push <= InpPushBp) continue;

         double res = (g_r[iSal].close / p1 - 1.0) * 10000.0 - InpCostBp;
         sum += res; sum2 += res * res; nops++;
         if(res > 0) nwin++;
      }

      if(nops < 5)
      {
         FileWrite(fs, off, nses, nops, "", "", "", "", "");
         continue;
      }
      double media = sum / nops;
      double var = (sum2 - nops * media * media) / (nops - 1);
      double sd = (var > 0 ? MathSqrt(var) : 0.0);
      double t = (sd > 0 ? media / (sd / MathSqrt((double)nops)) : 0.0);

      FileWrite(fs, off, nses, nops,
                DoubleToString(100.0 * nops / nses, 1),
                DoubleToString(media, 2),
                DoubleToString(sd, 1),
                DoubleToString(t, 2),
                DoubleToString(100.0 * nwin / nops, 2));
   }
   FileClose(fs);

   Print("LISTO. ", InpOutSenal, " y ", InpOutCalidad,
         " en <carpeta de datos>\\MQL5\\Files\\");
}
//+------------------------------------------------------------------+
