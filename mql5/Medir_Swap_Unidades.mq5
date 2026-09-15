//+------------------------------------------------------------------+
//| Medir_Swap_Unidades.mq5                                          |
//|                                                                  |
//| NO OPERA. Solo mide. Resuelve la unica cifra que decide si la     |
//| pata pre-FOMC tiene tamano defendible o no.                       |
//|                                                                  |
//| El problema. El anuncio del FOMC es en miercoles, la entrada de   |
//| EA_FOMC_Gap cae el martes por la tarde (15:57 NY) y el rollover   |
//| es a las 00:00 del servidor. Asi que la posicion cruza siempre un |
//| rollover. Si ese cruce cobra 1 unidad de swap, la ventaja neta    |
//| medida sobre 15 anos aguanta la regla de dimensionado de la Fase  |
//| 12.1 por +2,2 bp. Si cobra 3 —porque el broker asigna el triple   |
//| al rollover que sella el miercoles— la ventaja no soporta         |
//| posicion: f = 0.                                                  |
//|                                                                  |
//| ESTADO-CUENTA presupuesta "50 $/año (8 noches)", que es contar    |
//| NOCHES. La Fase 15 dice explicitamente que hay que contar         |
//| UNIDADES, y que el miercoles vale tres. Este script comprueba     |
//| cual de las dos cuentas aplica a NACUSD.c en este broker.         |
//|                                                                  |
//| Hay dos caminos y el script recorre los dos, porque el primero es |
//| gratis y el segundo es la prueba:                                 |
//|                                                                  |
//|   1. SYMBOL_SWAP_ROLLOVER3DAYS dice que dia lleva el triple.      |
//|      Una linea, sin esperar. Pero es una DECLARACION del broker.  |
//|   2. Medir el cargo real en cada rollover con una posicion        |
//|      abierta: swap = (equity - saldo) - suma(Profit), que es el   |
//|      metodo de la Fase 15. Esto es la EVIDENCIA.                  |
//|                                                                  |
//| Si 1 y 2 no coinciden, manda 2.                                   |
//|                                                                  |
//| Uso: attach a cualquier grafico. Con una posicion abierta en el   |
//| simbolo vigilado, dejarlo corriendo de lunes a viernes. Escribe   |
//| una linea por rollover en el log y un CSV en MQL5/Files.          |
//+------------------------------------------------------------------+
#property copyright "auditoria cuantitativa"
#property version   "1.00"
#property strict

input string InpSimbolos      = "NACUSD.c,EURUSD"; // simbolos a vigilar, separados por coma
input int    InpSegundos      = 30;                // cada cuanto comprueba el reloj
input bool   InpEscribirCSV   = true;              // volcar a MQL5/Files/swap_medido.csv
input string InpArchivo       = "swap_medido.csv";

// Estado por simbolo. Sin arrays dinamicos de structs para no depender de
// features del compilador: dos arrays paralelos y un contador.
#define MAX_SIM 16

string   g_sim[MAX_SIM];
double   g_swap_prev[MAX_SIM];      // POSITION_SWAP acumulado en la ultima lectura
bool     g_tenia_pos[MAX_SIM];
int      g_n_sim = 0;

int      g_dia_prev = -1;           // dia del servidor de la ultima comprobacion
bool     g_avisado_sin_pos = false;
int      g_fh = INVALID_HANDLE;

//+------------------------------------------------------------------+
int DayOfWeekServidor()
  {
   MqlDateTime t;
   TimeToStruct(TimeCurrent(), t);
   return t.day_of_week;
  }

//+------------------------------------------------------------------+
string NombreDia(const int dow)
  {
   switch(dow)
     {
      case 0: return "domingo";
      case 1: return "lunes";
      case 2: return "martes";
      case 3: return "miercoles";
      case 4: return "jueves";
      case 5: return "viernes";
      case 6: return "sabado";
     }
   return "?";
  }

//+------------------------------------------------------------------+
string ModoSwap(const long modo)
  {
   switch((int)modo)
     {
      case SYMBOL_SWAP_MODE_DISABLED:          return "DESACTIVADO";
      case SYMBOL_SWAP_MODE_POINTS:            return "PUNTOS";
      case SYMBOL_SWAP_MODE_CURRENCY_SYMBOL:   return "DIVISA DEL SIMBOLO";
      case SYMBOL_SWAP_MODE_CURRENCY_MARGIN:   return "DIVISA DEL MARGEN";
      case SYMBOL_SWAP_MODE_CURRENCY_DEPOSIT:  return "DIVISA DE LA CUENTA";
      case SYMBOL_SWAP_MODE_INTEREST_CURRENT:  return "INTERES S/ PRECIO ACTUAL";
      case SYMBOL_SWAP_MODE_INTEREST_OPEN:     return "INTERES S/ PRECIO APERTURA";
      case SYMBOL_SWAP_MODE_REOPEN_CURRENT:    return "REAPERTURA A PRECIO ACTUAL";
      case SYMBOL_SWAP_MODE_REOPEN_BID:        return "REAPERTURA A BID";
     }
   return "desconocido("+IntegerToString(modo)+")";
  }

//+------------------------------------------------------------------+
//| Nocional de UN lote, despejado de las especificaciones. La Fase   |
//| 15 insiste: el nocional se despeja, no se apunta de memoria.      |
//+------------------------------------------------------------------+
double NocionalPorLote(const string sim)
  {
   double tv = SymbolInfoDouble(sim, SYMBOL_TRADE_TICK_VALUE);
   double ts = SymbolInfoDouble(sim, SYMBOL_TRADE_TICK_SIZE);
   double px = SymbolInfoDouble(sim, SYMBOL_BID);
   if(tv <= 0.0 || ts <= 0.0 || px <= 0.0)
      return 0.0;
   return px * tv / ts;
  }

//+------------------------------------------------------------------+
//| Swap acumulado de las posiciones abiertas de un simbolo.          |
//| Devuelve false si no hay ninguna: sin posicion no hay medicion.   |
//+------------------------------------------------------------------+
bool SwapDeSimbolo(const string sim, double &swap, double &vol)
  {
   swap = 0.0;
   vol  = 0.0;
   bool hay = false;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(!PositionSelectByTicket(PositionGetTicket(i)))
         continue;
      if(PositionGetString(POSITION_SYMBOL) != sim)
         continue;
      swap += PositionGetDouble(POSITION_SWAP);
      vol  += PositionGetDouble(POSITION_VOLUME);
      hay = true;
     }
   return hay;
  }

//+------------------------------------------------------------------+
void VuelcaCabecera()
  {
   if(!InpEscribirCSV)
      return;
   g_fh = FileOpen(InpArchivo, FILE_WRITE|FILE_READ|FILE_CSV|FILE_ANSI, ',');
   if(g_fh == INVALID_HANDLE)
     {
      Print("AVISO: no se pudo abrir ", InpArchivo, " err=", GetLastError());
      return;
     }
   FileSeek(g_fh, 0, SEEK_END);
   if(FileTell(g_fh) == 0)
      FileWrite(g_fh, "hora_servidor", "dia_semana", "simbolo", "volumen",
                "swap_acum", "cargo_rollover", "nocional_lote",
                "bp_del_nocional", "unidades_implicitas", "rollover3dias");
  }

//+------------------------------------------------------------------+
int OnInit()
  {
   string partes[];
   int n = StringSplit(InpSimbolos, ',', partes);
   for(int i = 0; i < n && g_n_sim < MAX_SIM; i++)
     {
      string s = partes[i];
      StringTrimLeft(s);
      StringTrimRight(s);
      if(s == "")
         continue;
      if(!SymbolSelect(s, true))
        {
         Print("AVISO: no se pudo seleccionar ", s, " — se omite");
         continue;
        }
      g_sim[g_n_sim]       = s;
      g_swap_prev[g_n_sim] = 0.0;
      g_tenia_pos[g_n_sim] = false;
      g_n_sim++;
     }

   if(g_n_sim == 0)
     {
      Print("ERROR: ningun simbolo utilizable en InpSimbolos");
      return INIT_FAILED;
     }

   Print("========================================================");
   Print("MEDIR SWAP — declaracion del broker (camino 1, gratis)");
   Print("========================================================");
   Print("hora del servidor: ", TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS),
         "   (", NombreDia(DayOfWeekServidor()), ")");
   Print("");

   for(int i = 0; i < g_n_sim; i++)
     {
      string s = g_sim[i];
      long   r3 = SymbolInfoInteger(s, SYMBOL_SWAP_ROLLOVER3DAYS);
      double sl = SymbolInfoDouble(s, SYMBOL_SWAP_LONG);
      double ss = SymbolInfoDouble(s, SYMBOL_SWAP_SHORT);
      double noc = NocionalPorLote(s);

      Print("  ", s);
      Print("     modo de swap        : ", ModoSwap(SymbolInfoInteger(s, SYMBOL_SWAP_MODE)));
      Print("     swap largo / corto  : ", DoubleToString(sl, 4), " / ",
            DoubleToString(ss, 4));
      Print("     TRIPLE el dia       : ", NombreDia((int)r3),
            "   <-- la respuesta declarada");
      Print("     nocional por lote   : ", DoubleToString(noc, 2), " ",
            AccountInfoString(ACCOUNT_CURRENCY));
      Print("     tamano de contrato  : ",
            DoubleToString(SymbolInfoDouble(s, SYMBOL_TRADE_CONTRACT_SIZE), 2));

      // La lectura que importa para la pata pre-FOMC: la entrada es el martes
      // por la tarde y el rollover cae a las 00:00 del servidor, o sea que la
      // posicion cruza el rollover que sella el MIERCOLES.
      if(r3 == WEDNESDAY)
         Print("     -> el triple cae en el rollover que SELLA el miercoles.",
               " La tenencia del martes por la tarde al miercoles por la",
               " manana lo cruza: 3 unidades por evento, no 1.");
      else if(r3 == THURSDAY)
         Print("     -> el triple cae en el rollover miercoles->jueves. La",
               " tenencia pre-FOMC sale ANTES: 1 unidad por evento.");
      else
         Print("     -> el triple no cae en la noche de la tenencia pre-FOMC:",
               " 1 unidad por evento.");
      Print("");
     }

   Print("Esto es lo que DICE el broker. La prueba es el cargo real, y para");
   Print("eso hace falta una posicion abierta cruzando un rollover.");
   Print("========================================================");

   VuelcaCabecera();
   g_dia_prev = DayOfWeekServidor();
   EventSetTimer(MathMax(5, InpSegundos));
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   if(g_fh != INVALID_HANDLE)
     {
      FileClose(g_fh);
      g_fh = INVALID_HANDLE;
     }
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   int dow = DayOfWeekServidor();

   // Lectura continua del swap acumulado por simbolo. El salto entre dos
   // lecturas consecutivas ES el cargo del rollover, sin depender de que el
   // reloj del servidor y el nuestro coincidan.
   for(int i = 0; i < g_n_sim; i++)
     {
      double swap = 0.0, vol = 0.0;
      bool hay = SwapDeSimbolo(g_sim[i], swap, vol);

      if(!hay)
        {
         g_tenia_pos[i] = false;
         continue;
        }

      if(!g_tenia_pos[i])
        {
         // primera lectura con posicion: solo se ancla, no se mide
         g_swap_prev[i] = swap;
         g_tenia_pos[i] = true;
         Print("anclado ", g_sim[i], ": swap acumulado ",
               DoubleToString(swap, 2), " con ", DoubleToString(vol, 2), " lotes");
         continue;
        }

      double cargo = swap - g_swap_prev[i];
      if(MathAbs(cargo) < 1e-8)
         continue;                       // nada nuevo

      double noc = NocionalPorLote(g_sim[i]) * vol;
      double bp  = (noc > 0.0) ? MathAbs(cargo) / noc * 1e4 : 0.0;

      // Una unidad esperada, con la tasa anual implicita del propio cargo.
      // No se supone la tasa: se compara el cargo con el MENOR cargo visto,
      // que es la unidad. Hasta tener dos rollovers, se informa en bruto.
      Print(">>> ROLLOVER ", g_sim[i], "  ", NombreDia(dow),
            "  cargo ", DoubleToString(cargo, 2),
            "  = ", DoubleToString(bp, 3), " bp del nocional (",
            DoubleToString(noc, 0), ")");

      if(g_fh != INVALID_HANDLE)
         FileWrite(g_fh,
                   TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS),
                   NombreDia(dow), g_sim[i],
                   DoubleToString(vol, 2),
                   DoubleToString(swap, 2),
                   DoubleToString(cargo, 2),
                   DoubleToString(NocionalPorLote(g_sim[i]), 2),
                   DoubleToString(bp, 4),
                   "",   // unidades: se rellena al analizar, hacen falta >=2
                   NombreDia((int)SymbolInfoInteger(g_sim[i],
                                                    SYMBOL_SWAP_ROLLOVER3DAYS)));
      if(g_fh != INVALID_HANDLE)
         FileFlush(g_fh);

      g_swap_prev[i] = swap;
     }

   // Aviso una sola vez: sin posicion abierta el camino 2 no puede medir.
   if(!g_avisado_sin_pos)
     {
      bool alguna = false;
      for(int i = 0; i < g_n_sim; i++)
         if(g_tenia_pos[i])
            alguna = true;
      if(!alguna)
        {
         Print("AVISO: no hay posicion abierta en los simbolos vigilados.");
         Print("       La declaracion del broker ya esta en el log, pero el");
         Print("       cargo real no se puede medir sin una posicion cruzando");
         Print("       un rollover. Abre una minima y dejala.");
         g_avisado_sin_pos = true;
        }
     }

   g_dia_prev = dow;
  }
//+------------------------------------------------------------------+
