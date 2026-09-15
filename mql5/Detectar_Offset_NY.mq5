//+------------------------------------------------------------------+
//|  Detectar_Offset_NY.mq5                                          |
//|                                                                  |
//|  SCRIPT (no es un EA). Se ejecuta una vez sobre el grafico del   |
//|  simbolo que vayas a operar y te dice cuanto vale               |
//|  InpOffsetServidorNY del EA_FOMC_Gap.                            |
//|                                                                  |
//|  COMO LO HACE, y por que es fiable                               |
//|    La apertura del contado (09:30 en Nueva York) produce un      |
//|    salto de actividad inconfundible: el rango de las velas M1 y  |
//|    el numero de ticks se multiplican de golpe. El script mide la |
//|    actividad media de cada minuto del dia EN HORA DEL SERVIDOR,  |
//|    localiza ese salto, y deduce el desfase.                      |
//|                                                                  |
//|    Es el mismo metodo con el que localizamos la publicacion del  |
//|    IPC a las 8:30 en los datos: se identifica el evento por su   |
//|    firma en los precios, no por un supuesto.                     |
//|                                                                  |
//|  COMO USARLO                                                     |
//|    1. Abre un grafico del simbolo (NAS100 o el que corresponda)  |
//|    2. Arrastra este script sobre el grafico                      |
//|    3. Mira el resultado en la pestaña "Expertos" del Terminal    |
//|       (si no la ves: menu Ver -> Terminal, o Ctrl+T)             |
//+------------------------------------------------------------------+
#property copyright "Proyecto de auditoria cuantitativa"
#property version   "1.00"
#property script_show_inputs
#property strict

input int InpBarras = 200000;   // Velas M1 a analizar (200000 = ~140 dias)

//+------------------------------------------------------------------+
void OnStart()
  {
   string sim = _Symbol;
   Print("=== Detectar_Offset_NY sobre ", sim, " ===");

   MqlRates r[];
   int n = CopyRates(sim, PERIOD_M1, 0, InpBarras, r);
   if(n <= 0)
     {
      Print("ERROR: no hay velas M1. Descarga el historial del simbolo",
            " (Herramientas -> Ventana de datos, o abre un grafico M1 y",
            " desplazate hacia atras).");
      return;
     }
   Print("velas M1 leidas: ", n);

   //--- actividad media por minuto del dia, en hora del SERVIDOR
   double sumaRango[1440];
   double sumaTicks[1440];
   long   cuenta[1440];
   ArrayInitialize(sumaRango, 0.0);
   ArrayInitialize(sumaTicks, 0.0);
   ArrayInitialize(cuenta, 0);

   MqlDateTime t;
   for(int i = 0; i < n; i++)
     {
      if(r[i].close <= 0.0)
         continue;
      TimeToStruct(r[i].time, t);
      //--- se excluyen sabados y domingos: distorsionan el perfil
      if(t.day_of_week == 0 || t.day_of_week == 6)
         continue;
      int m = t.hour * 60 + t.min;
      if(m < 0 || m > 1439)
         continue;
      sumaRango[m] += (r[i].high - r[i].low) / r[i].close * 10000.0;  // en bp
      sumaTicks[m] += (double)r[i].tick_volume;
      cuenta[m]    += 1;
     }

   //--- medias
   double rango[1440], ticks[1440];
   for(int m = 0; m < 1440; m++)
     {
      rango[m] = (cuenta[m] > 0 ? sumaRango[m] / cuenta[m] : 0.0);
      ticks[m] = (cuenta[m] > 0 ? sumaTicks[m] / cuenta[m] : 0.0);
     }

   //--- perfil por hora, para verlo a ojo
   Print("");
   Print("PERFIL DE ACTIVIDAD POR HORA (hora del SERVIDOR)");
   Print("  hora   rango medio M1 (bp)   ticks medios   grafico");
   double maxHora = 0.0;
   double rHora[24];
   for(int h = 0; h < 24; h++)
     {
      double s = 0.0;
      int    c = 0;
      for(int m = h * 60; m < (h + 1) * 60; m++)
         if(cuenta[m] > 0)
           {
            s += rango[m];
            c++;
           }
      rHora[h] = (c > 0 ? s / c : 0.0);
      if(rHora[h] > maxHora)
         maxHora = rHora[h];
     }
   for(int h = 0; h < 24; h++)
     {
      string barra = "";
      int len = (maxHora > 0.0 ? (int)MathRound(40.0 * rHora[h] / maxHora) : 0);
      for(int k = 0; k < len; k++)
         barra += "#";
      double tk = 0.0;
      int c2 = 0;
      for(int m = h * 60; m < (h + 1) * 60; m++)
         if(cuenta[m] > 0)
           {
            tk += ticks[m];
            c2++;
           }
      Print("  ", StringFormat("%02d", h), "h    ",
            DoubleToString(rHora[h], 2), "                ",
            DoubleToString(c2 > 0 ? tk / c2 : 0.0, 1), "        ", barra);
     }

   //--- localizar el SALTO: el minuto cuya actividad mas supera a la
   //    media de los 30 minutos anteriores
   int    mejorMin  = -1;
   double mejorSalto = 0.0;
   for(int m = 60; m < 1440; m++)
     {
      if(cuenta[m] < 20 || rango[m] <= 0.0)
         continue;
      double prev = 0.0;
      int    c = 0;
      for(int k = m - 30; k < m; k++)
         if(k >= 0 && cuenta[k] >= 20 && rango[k] > 0.0)
           {
            prev += rango[k];
            c++;
           }
      if(c < 15 || prev <= 0.0)
         continue;
      double media = prev / c;
      if(media <= 0.0)
         continue;
      double salto = rango[m] / media;
      if(salto > mejorSalto)
        {
         mejorSalto = salto;
         mejorMin   = m;
        }
     }

   Print("");
   Print("=== RESULTADO ===");
   if(mejorMin < 0)
     {
      Print("No se pudo localizar el salto de apertura. Descarga mas");
      Print("historial M1 y vuelve a ejecutar.");
      return;
     }

   int hS = mejorMin / 60, mS = mejorMin % 60;
   Print("  Mayor salto de actividad en la hora del servidor: ",
         StringFormat("%02d:%02d", hS, mS),
         "   (x", DoubleToString(mejorSalto, 1), " sobre los 30 min previos)");
   Print("  Ese salto deberia ser la apertura del contado, 09:30 en NY.");

   //--- offset: minutos del servidor menos 09:30 (=570 min)
   int offMin = mejorMin - 570;
   //--- se normaliza al rango [-12h, +12h]
   while(offMin > 720)
      offMin -= 1440;
   while(offMin < -720)
      offMin += 1440;

   Print("");
   if(offMin % 60 == 0)
     {
      Print("  >>> InpOffsetServidorNY = ", offMin / 60);
     }
   else
     {
      Print("  El desfase no es un numero entero de horas: ", offMin,
            " minutos.");
      Print("  Redondeando a la hora mas cercana: ",
            (int)MathRound(offMin / 60.0));
      Print("  >>> InpOffsetServidorNY = ", (int)MathRound(offMin / 60.0));
      Print("  AVISO: revisa el perfil de arriba a mano antes de fiarte.");
     }

   //--- comprobacion cruzada: la hora actual traducida
   datetime ahora   = TimeCurrent();
   datetime ahoraNY = ahora - (datetime)(offMin * 60);
   MqlDateTime s, ny;
   TimeToStruct(ahora, s);
   TimeToStruct(ahoraNY, ny);
   Print("");
   Print("  COMPROBACION CRUZADA");
   Print("    hora del servidor ahora : ",
         StringFormat("%04d.%02d.%02d %02d:%02d", s.year, s.mon, s.day,
                      s.hour, s.min));
   Print("    hora de NY con ese offset: ",
         StringFormat("%04d.%02d.%02d %02d:%02d", ny.year, ny.mon, ny.day,
                      ny.hour, ny.min));
   Print("    Si esa hora de NY es la real, el offset es correcto.");
   Print("");
   Print("  AVISO SOBRE EL HORARIO DE VERANO");
   Print("    Si el servidor de tu broker cambia de horario en las mismas");
   Print("    fechas que Nueva York, el offset es constante todo el año.");
   Print("    Si no, cambiara dos veces al año y habra que reejecutar este");
   Print("    script en marzo y en noviembre.");
  }
//+------------------------------------------------------------------+
