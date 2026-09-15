//+------------------------------------------------------------------+
//|  EA_FOMC_Gap.mq5                                                 |
//|  Estrategia #1: prima nocturna previa al anuncio del FOMC        |
//|                                                                  |
//|  QUE HACE                                                        |
//|    Compra al cierre del contado (16:00 hora de Nueva York) del   |
//|    dia de mercado ANTERIOR a un anuncio del FOMC, y cierra a la  |
//|    apertura del contado (09:30 NY) del dia del anuncio.          |
//|                                                                  |
//|  EVIDENCIA QUE LO SOSTIENE                                       |
//|    212 eventos, 2000-2026, indice de contado y CFD:              |
//|      efecto +22 a +25 bp brutos  ·  t = 3,76 (4,04 desde 2012)   |
//|      estable en tres subperiodos: +24,2 / +23,0 / +20,2 bp       |
//|      controles (oro, EUR/USD) NO lo muestran                     |
//|      NO generaliza al BoJ, al IPC ni al empleo -> es de la Fed    |
//|    El efecto vive en el HUECO nocturno; la sesion del dia del    |
//|    FOMC es negativa por la mañana, asi que no se opera intradia. |
//|                                                                  |
//|  POR QUE EL STOP ES 80 bp Y EL TAKE PROFIT 50                    |
//|    No es gestion de riesgo convencional: es para satisfacer la   |
//|    regla de consistencia de la prop firm (el mejor dia no puede  |
//|    pasar del 20% del beneficio total).                           |
//|                                                                  |
//|    Primero se eligio +-80 SIMETRICO, truncando la serie DIARIA.  |
//|    Eso era la pregunta equivocada: un take profit se toca        |
//|    INTRADIA, y recortar el cierre del dia solo ve los eventos    |
//|    que CIERRAN por encima del TP. Medido sobre los M1 reales de  |
//|    117 eventos, barriendo el TP con el stop fijo en 80:          |
//|                                                                  |
//|      TP    media    mejor dia   liston 20%   P(cobro)   1er cobro |
//|      40  +15,7 bp      308 $       1.538 $     74,5%      196 d  |
//|      50  +15,4 bp      319 $       1.593 $     71,8%      212 d  |
//|      80  +19,4 bp      391 $       1.956 $     67,7%      241 d  |
//|     sin   +19,5 bp      543 $       2.714 $     47,7%      282 d  |
//|                                                                  |
//|    Un TP corto CUESTA ventaja (19,4 -> 15,4 bp) pero baja el     |
//|    liston que impone la regla del 20%, y eso pesa mas. Se elige  |
//|    50 y no 40 —que midio mejor— por no coger el argmax de una    |
//|    curva construida sobre 117 eventos: 30, 40, 50 y 60 forman    |
//|    una meseta y el pico exacto no es informacion fiable.         |
//|                                                                  |
//|    Consecuencia que hay que tener presente: en dinero el stop    |
//|    (1,44% de la equity) es 1,6 veces el take profit (0,90%). Se  |
//|    sostiene porque el 73,5% de los eventos son positivos.        |
//|                                                                  |
//|  LOS TRES BUGS QUE EL PROBADOR ENCONTRO EN EL EA ANTERIOR Y QUE  |
//|  AQUI ESTAN EVITADOS                                             |
//|    1. Spread medido en _Point con Digits=2 -> convertia 0,80 en  |
//|       80 y rechazaba todos los dias. AQUI el spread se mide en   |
//|       PUNTOS BASICOS DEL PRECIO, que es unidad-independiente.    |
//|    2. El cierre por hora no se disparaba porque el simbolo deja  |
//|       de cotizar antes. AQUI hay red de seguridad por duracion   |
//|       maxima y por cambio de dia.                                |
//|    3. Un filtro con datos insuficientes devolvia 0 y se saltaba  |
//|       solo. AQUI todo filtro que no puede evaluarse FALLA EN     |
//|       CERRADO y lo cuenta en un contador visible.                |
//+------------------------------------------------------------------+
#property copyright "Proyecto de auditoria cuantitativa"
#property version   "1.00"
#property strict

//--- fechas de ANUNCIO del FOMC (segundo dia de reunion), hora de NY.
//    Fuente: federalreserve.gov/monetarypolicy/fomccalendars.htm
//    Formato AAAAMMDD. Ampliar cuando la Fed publique 2028.
int FECHAS_FOMC[] =
  {
   20000202, 20000321, 20000516, 20000628, 20000822, 20001003, 20001115, 20001219,
   20010131, 20010320, 20010515, 20010627, 20010821, 20011002, 20011106, 20011211,
   20020130, 20020319, 20020507, 20020626, 20020813, 20020924, 20021106, 20021210,
   20030129, 20030318, 20030506, 20030625, 20030812, 20030916, 20031028, 20031209,
   20040128, 20040316, 20040504, 20040630, 20040810, 20040921, 20041110, 20041214,
   20050202, 20050322, 20050503, 20050630, 20050809, 20050920, 20051101, 20051213,
   20060131, 20060328, 20060510, 20060629, 20060808, 20060920, 20061025, 20061212,
   20070131, 20070321, 20070509, 20070628, 20070807, 20070918, 20071031, 20071211,
   20080130, 20080318, 20080430, 20080625, 20080805, 20080916, 20081029, 20081216,
   20090128, 20090318, 20090429, 20090624, 20090812, 20090923, 20091104, 20091216,
   20100127, 20100316, 20100428, 20100623, 20100810, 20100921, 20101103, 20101214,
   20110126, 20110315, 20110427, 20110622, 20110809, 20110921, 20111102, 20111213,
   20120125, 20120313, 20120425, 20120620, 20120801, 20120913, 20121024, 20121212,
   20130130, 20130320, 20130501, 20130619, 20130731, 20130918, 20131030, 20131218,
   20140129, 20140319, 20140430, 20140618, 20140730, 20140917, 20141029, 20141217,
   20150128, 20150318, 20150429, 20150617, 20150729, 20150917, 20151028, 20151216,
   20160127, 20160316, 20160427, 20160615, 20160727, 20160921, 20161102, 20161214,
   20170201, 20170315, 20170503, 20170614, 20170726, 20170920, 20171101, 20171213,
   20180131, 20180321, 20180502, 20180613, 20180801, 20180926, 20181108, 20181219,
   20190130, 20190320, 20190501, 20190619, 20190731, 20190918, 20191030, 20191211,
   20200129, 20200429, 20200610, 20200729, 20200916, 20201105, 20201216, 20210127,
   20210317, 20210428, 20210616, 20210728, 20210922, 20211103, 20211215, 20220126,
   20220316, 20220504, 20220615, 20220727, 20220921, 20221102, 20221214, 20230201,
   20230322, 20230503, 20230614, 20230726, 20230920, 20231101, 20231213, 20240131,
   20240320, 20240501, 20240612, 20240731, 20240918, 20241107, 20241218, 20250129,
   20250319, 20250507, 20250618, 20250730, 20250917, 20251029, 20251210, 20260128,
   20260318, 20260429, 20260617, 20260729, 20260916, 20261028, 20261209, 20270127,
   20270317, 20270428, 20270609, 20270728, 20270915, 20271027, 20271208
  };

//--- entradas -------------------------------------------------------
input group           "=== Instrumento y horario ==="
input string          InpSimbolo          = "";     // Simbolo ("" = el del grafico)
input bool            InpAutoHoraNY       = true;   // Calcular la hora de NY automaticamente
input int             InpBrokerGMT        = 2;      // Offset GMT del servidor del broker
input int             InpOffsetServidorNY = 6;      // Offset manual (solo si Auto = false)
input int             InpHoraEntradaNY    = 16;     // Hora de entrada (NY)
input int             InpMinEntradaNY     = 0;      // Minuto de entrada (NY)
input int             InpMinutosAntes     = 3;      // Minutos ANTES de la hora en que ya se admite entrar
input int             InpVentanaEntradaMin= 45;     // Ventana para entrar si no hay precio (min)
input int             InpHoraSalidaNY     = 9;      // Hora de salida (NY)
input int             InpMinSalidaNY      = 30;     // Minuto de salida (NY)

input group           "=== Riesgo y dimensionado ==="
input double          InpRiesgoPorEvento  = 1.44;   // Perdida en el stop, % de la equity
input double          InpStopBp           = 80.0;   // Stop loss en puntos basicos
input double          InpTakeProfitBp     = 40.0;   // Take profit en puntos basicos (40 trunca la cola: 1,95% vs 2,41% con 50)
input double          InpLotesMax         = 0.0;    // Tope de lotes (0 = sin tope)

input group           "=== Filtros de ejecucion ==="
input double          InpSpreadMaxBp      = 3.0;    // Spread maximo admitido, en bp
input int             InpDuracionMaxMin   = 1200;   // Red de seguridad: duracion maxima (min)
input int             InpDeslizamiento    = 20;     // Deslizamiento permitido (puntos)

input group           "=== Coordinacion con el Guardian ==="
input bool            InpRespetarGuardian = true;   // No abrir si EA_Guardian senala averia
input bool            InpUsarFactorGuard  = true;   // Multiplicar el riesgo por el factor del Guardian
input bool            InpExigirGuardian   = false;  // No operar si el Guardian no esta publicando
input int             InpFrescuraGuardMin = 10;     // El dato del Guardian caduca a los N minutos

input group           "=== Identificacion ==="
input long            InpMagic            = 20260101;
input bool            InpLogDetallado     = true;

//--- variables globales del terminal que publica EA_Guardian.
//    GUARDIAN_BLOQUEO vale 0 si se puede operar y la marca de tiempo de la
//    averia si no. GUARDIAN_FACTOR es el multiplicador del riesgo, entre
//    InpFactorMinimo y 1.
#define GV_BLOQUEO   "GUARDIAN_BLOQUEO"
#define GV_FACTOR    "GUARDIAN_FACTOR"
#define GV_LATIDO    "GUARDIAN_LATIDO"

//--- estado ---------------------------------------------------------
string   g_sim;
int      g_cRechazoSpread   = 0;   // veces que el spread impidio entrar
int      g_cSinPrecio       = 0;   // veces que no habia precio valido
int      g_cVentanaPerdida  = 0;   // eventos en que no se logro entrar
int      g_cEntradas        = 0;
int      g_cSalidasHora     = 0;
int      g_cSalidasRed      = 0;   // salidas por red de seguridad
int      g_ultimoEventoInt  = 0;   // AAAAMMDD del ultimo evento operado
bool     g_avisoOffset      = false;
int      g_cBloqueoGuardian = 0;   // eventos no operados por el Guardian
bool     g_avisoSinGuardian = false;

//+------------------------------------------------------------------+
int OnInit()
  {
   g_sim = (InpSimbolo == "" ? _Symbol : InpSimbolo);

   if(!SymbolSelect(g_sim, true))
     {
      Print("ERROR: no se puede seleccionar el simbolo ", g_sim);
      return(INIT_FAILED);
     }
   if(InpStopBp <= 0.0 || InpRiesgoPorEvento <= 0.0)
     {
      Print("ERROR: el stop y el riesgo deben ser positivos");
      return(INIT_FAILED);
     }
   if(ArraySize(FECHAS_FOMC) == 0)
     {
      Print("ERROR: la tabla de fechas del FOMC esta vacia");
      return(INIT_FAILED);
     }

   //--- DIAGNOSTICO DE HORARIO. El desfase servidor-NY es el parametro
   //    que mas facil se equivoca, asi que se imprime para verificarlo
   //    a ojo en el primer arranque.
   datetime ahora   = TimeCurrent();
   datetime utc     = TimeGMT();
   datetime ahoraNY = AhoraNY();
   MqlDateTime s, u, n;
   TimeToStruct(ahora, s);
   TimeToStruct(utc, u);
   TimeToStruct(ahoraNY, n);
   Print("=== EA_FOMC_Gap iniciado ===");
   Print("  simbolo            : ", g_sim,
         "   digits=", (int)SymbolInfoInteger(g_sim, SYMBOL_DIGITS));
   PrintFormat("  hora del SERVIDOR  : %04d.%02d.%02d %02d:%02d",
               s.year, s.mon, s.day, s.hour, s.min);
   //--- REDONDEAR, no truncar. 'ahora' y 'utc' se muestrean con fracciones
   //    de segundo de diferencia, asi que la resta puede salir un segundo
   //    corta: 7199 s truncado da 1 h en vez de 2. Este bloque existe para
   //    detectar errores de horario y con el truncamiento los INVENTABA.
   PrintFormat("  hora UTC (TimeGMT) : %04d.%02d.%02d %02d:%02d   "
               "(servidor esta en GMT%+d)",
               u.year, u.mon, u.day, u.hour, u.min,
               (int)MathRound((double)((long)ahora - (long)utc) / 3600.0));
   PrintFormat("  hora de NUEVA YORK : %04d.%02d.%02d %02d:%02d",
               n.year, n.mon, n.day, n.hour, n.min);
   Print("  modo de hora       : ",
         (InpAutoHoraNY ? "AUTOMATICO" : "MANUAL con offset de " +
                          IntegerToString(InpOffsetServidorNY) + " h"));
   if(InpAutoHoraNY)
      Print("  horario de verano EE.UU.: ",
            (EsVeranoEEUU(utc) ? "SI (NY = UTC-4)" : "NO (NY = UTC-5)"));

   //--- LA LINEA QUE DELATA UN ERROR DE HORARIO AL INSTANTE.
   //    El desfase actual servidor-NY se deduce de AhoraNY(), asi que se
   //    imprime a que hora del SERVIDOR caen la entrada y la salida. Eso
   //    es comparable directamente con el log de operaciones.
   int desfase = (int)MathRound((double)((long)ahora - (long)ahoraNY)
                                / 3600.0);
   int entSrv  = (InpHoraEntradaNY + desfase + 24) % 24;
   int salSrv  = (InpHoraSalidaNY  + desfase + 24) % 24;
   Print("  desfase servidor-NY: ", desfase, " h");
   PrintFormat("  >>> La entrada de las %02d:%02d NY cae a las %02d:%02d del "
               "SERVIDOR", InpHoraEntradaNY, InpMinEntradaNY, entSrv,
               InpMinEntradaNY);
   PrintFormat("  >>> La salida  de las %02d:%02d NY cae a las %02d:%02d del "
               "SERVIDOR", InpHoraSalidaNY, InpMinSalidaNY, salSrv,
               InpMinSalidaNY);
   Print("  >>> COMPARA esas horas con el log de operaciones. Si no cuadran,");
   Print("  >>> el EA esta operando la ventana equivocada.");
   PrintFormat("  entrada %02d:%02d NY -> salida %02d:%02d NY",
               InpHoraEntradaNY, InpMinEntradaNY, InpHoraSalidaNY, InpMinSalidaNY);
   PrintFormat("  eventos en la tabla: %d   (primero %d, ultimo %d)",
               ArraySize(FECHAS_FOMC), FECHAS_FOMC[0],
               FECHAS_FOMC[ArraySize(FECHAS_FOMC) - 1]);
   PrintFormat("  stop %.1f bp · TP %.1f bp · riesgo %.2f%% de la equity",
               InpStopBp, InpTakeProfitBp, InpRiesgoPorEvento);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   Print("=== EA_FOMC_Gap detenido (motivo ", reason, ") ===");
   PrintFormat("  entradas realizadas      : %d", g_cEntradas);
   PrintFormat("  salidas por hora         : %d", g_cSalidasHora);
   PrintFormat("  salidas por red seguridad: %d", g_cSalidasRed);
   PrintFormat("  rechazos por spread      : %d", g_cRechazoSpread);
   PrintFormat("  ticks sin precio valido  : %d", g_cSinPrecio);
   PrintFormat("  ventanas de entrada perdidas: %d", g_cVentanaPerdida);
   PrintFormat("  entradas vetadas por Guardian: %d", g_cBloqueoGuardian);
   if(g_cVentanaPerdida > 0)
      Print("  AVISO: se perdieron entradas. Revisa el spread maximo, la ",
            "ventana de entrada y el offset horario.");
  }

//+------------------------------------------------------------------+
//| ¿esta la costa este de EE.UU. en horario de verano en ese UTC?    |
//|                                                                  |
//| Reglas vigentes: empieza el SEGUNDO domingo de marzo a las 07:00  |
//| UTC (02:00 EST) y acaba el PRIMER domingo de noviembre a las      |
//| 06:00 UTC (02:00 EDT).                                           |
//|                                                                  |
//| Esto existe porque el servidor del broker esta en GMT+2 FIJO y no |
//| sigue el horario de verano, mientras Nueva York si. El desfase    |
//| entre los dos cambia de 6 a 7 horas el 1 de noviembre. Un offset  |
//| fijo entraria una hora tarde media temporada, sin dar ninguna     |
//| señal en los resultados.                                         |
//+------------------------------------------------------------------+
bool EsVeranoEEUU(const datetime utc)
  {
   MqlDateTime t;
   TimeToStruct(utc, t);
   int anio = t.year;

   //--- segundo domingo de marzo
   MqlDateTime m;  ZeroMemory(m);
   m.year = anio;  m.mon = 3;  m.day = 1;
   datetime mar1 = StructToTime(m);
   TimeToStruct(mar1, m);
   int primerDomMar = 1 + ((7 - m.day_of_week) % 7);
   int segundoDomMar = primerDomMar + 7;
   MqlDateTime ini;  ZeroMemory(ini);
   ini.year = anio;  ini.mon = 3;  ini.day = segundoDomMar;  ini.hour = 7;
   datetime inicio = StructToTime(ini);

   //--- primer domingo de noviembre
   MqlDateTime n;  ZeroMemory(n);
   n.year = anio;  n.mon = 11;  n.day = 1;
   datetime nov1 = StructToTime(n);
   TimeToStruct(nov1, n);
   int primerDomNov = 1 + ((7 - n.day_of_week) % 7);
   MqlDateTime fn;  ZeroMemory(fn);
   fn.year = anio;  fn.mon = 11;  fn.day = primerDomNov;  fn.hour = 6;
   datetime finVerano = StructToTime(fn);

   return(utc >= inicio && utc < finVerano);
  }

//+------------------------------------------------------------------+
//| hora de NY. Si InpAutoHoraNY, se calcula desde UTC con las reglas |
//| de horario de verano de EE.UU. y no hace falta ningun offset.     |
//| Si TimeGMT() no es fiable (puede pasar en el Probador), se avisa  |
//| y se cae al offset manual.                                       |
//+------------------------------------------------------------------+
datetime AhoraNY()
  {
   if(!InpAutoHoraNY)
      return(TimeCurrent() - (datetime)(InpOffsetServidorNY * 3600));

   datetime servidor = TimeCurrent();
   datetime g        = TimeGMT();
   long     dif      = (long)servidor - (long)g;
   datetime utc;

   //--- ¿es fiable TimeGMT()?
   //    En el PROBADOR devuelve lo mismo que TimeCurrent(), asi que un
   //    desfase de CERO no significa "servidor en UTC": significa que la
   //    funcion no esta informada. Mi comprobacion anterior solo miraba
   //    que el desfase no fuera absurdo, no que EXISTIERA, y por eso el
   //    EA entro dos horas antes en el primer backtest.
   bool fiable = (g > 0 && dif != 0 && MathAbs(dif) <= 14 * 3600);

   if(fiable)
      utc = g;
   else
     {
      //--- se reconstruye UTC desde la hora del servidor y su offset GMT
      utc = servidor - (datetime)(InpBrokerGMT * 3600);
      if(!g_avisoOffset)
        {
         Print("AVISO: TimeGMT() no informado (dif servidor-UTC = ",
               (int)(dif / 3600), " h, tipico del Probador).");
         Print("       Se reconstruye UTC como hora del servidor menos GMT",
               (InpBrokerGMT >= 0 ? "+" : ""), InpBrokerGMT,
               ". El horario de verano se sigue respetando.");
         g_avisoOffset = true;
        }
     }

   int horasNY = (EsVeranoEEUU(utc) ? 4 : 5);
   return(utc - (datetime)(horasNY * 3600));
  }

int FechaInt(const MqlDateTime &t)
  {
   return(t.year * 10000 + t.mon * 100 + t.day);
  }

//+------------------------------------------------------------------+
//| ¿es 'f' (AAAAMMDD) un dia de anuncio del FOMC?                   |
//+------------------------------------------------------------------+
bool EsDiaAnuncio(const int f)
  {
   for(int i = 0; i < ArraySize(FECHAS_FOMC); i++)
      if(FECHAS_FOMC[i] == f)
         return(true);
   return(false);
  }

//+------------------------------------------------------------------+
//| Devuelve el AAAAMMDD del anuncio si HOY (en NY) es el dia previo |
//| de mercado. Se resuelve mirando hacia delante hasta 4 dias       |
//| naturales y saltando fines de semana: si el siguiente dia de     |
//| mercado es un anuncio, hoy es dia de entrada.                    |
//| Devuelve 0 si hoy no es dia de entrada.                          |
//+------------------------------------------------------------------+
int AnuncioManana(const datetime ahoraNY)
  {
   MqlDateTime t;
   for(int d = 1; d <= 4; d++)
     {
      datetime cand = ahoraNY + (datetime)(d * 86400);
      TimeToStruct(cand, t);
      if(t.day_of_week == 0 || t.day_of_week == 6)   // domingo o sabado
         continue;
      //--- el primer dia de semana que aparece es el siguiente de mercado
      if(EsDiaAnuncio(FechaInt(t)))
         return(FechaInt(t));
      return(0);
     }
   return(0);
  }

//+------------------------------------------------------------------+
//| Spread actual en PUNTOS BASICOS DEL PRECIO.                      |
//| Esto es lo que evita el bug numero 1: no se usa _Point, que con  |
//| Digits=2 convertia 0,80 puntos de indice en "80".                |
//| Devuelve -1 si no hay precio valido (y entonces se falla cerrado)|
//+------------------------------------------------------------------+
double SpreadBp()
  {
   MqlTick tk;
   if(!SymbolInfoTick(g_sim, tk))
      return(-1.0);
   if(tk.bid <= 0.0 || tk.ask <= 0.0 || tk.ask < tk.bid)
      return(-1.0);
   return((tk.ask - tk.bid) / tk.bid * 10000.0);
  }

//+------------------------------------------------------------------+
//| Factor de tamaño publicado por EA_Guardian.                      |
//|                                                                  |
//| Medido sobre 20.000 caminos: escalar el tamaño con el margen que |
//| queda hasta el suelo del trailing baja la probabilidad de quemar |
//| la cuenta del 11,4% al 0,3% y cuesta el 6% del valor esperado.   |
//| Es la mejor relacion de todo el sistema.                         |
//|                                                                  |
//| Se comprueba la FRESCURA del dato: si el Guardian se ha caido, su |
//| ultimo factor sigue en memoria y seria una lectura fantasma.      |
//| Sin dato fresco:                                                 |
//|   InpExigirGuardian = true  -> no se opera (fallar en cerrado)    |
//|   InpExigirGuardian = false -> factor 1,0 y aviso. Tiene que ser  |
//|     el defecto porque en el Probador solo corre UN EA, asi que    |
//|     alli el Guardian nunca esta y el backtest debe funcionar.     |
//+------------------------------------------------------------------+
double FactorGuardian()
  {
   if(!InpUsarFactorGuard)
      return(1.0);

   //--- FRESCURA. Se prefiere el latido del Guardian, que viene en hora de
   //    servidor igual que TimeCurrent(), asi que la resta es limpia.
   //    GlobalVariableTime() queda como respaldo, pero su base horaria no
   //    esta garantizada y puede desplazar la edad varias horas.
   bool hay = GlobalVariableCheck(GV_FACTOR);
   long edad = -1;
   string via = "ninguna";

   if(hay && InpFrescuraGuardMin > 0)
     {
      if(GlobalVariableCheck(GV_LATIDO))
        {
         edad = (long)TimeCurrent() - (long)GlobalVariableGet(GV_LATIDO);
         via  = "latido";
        }
      else
        {
         datetime t = GlobalVariableTime(GV_FACTOR);
         edad = (t <= 0 ? -1 : (long)TimeCurrent() - (long)t);
         via  = "GlobalVariableTime";
        }
      if(edad < 0 || edad > (long)InpFrescuraGuardMin * 60)
         hay = false;
     }

   if(!hay)
     {
      if(!g_avisoSinGuardian)
        {
         g_avisoSinGuardian = true;
         PrintFormat("AVISO: no hay factor fresco de EA_Guardian "
                     "(existe=%s, via=%s, edad=%d s, limite=%d s). %s",
                     (GlobalVariableCheck(GV_FACTOR) ? "si" : "NO"), via,
                     (int)edad, InpFrescuraGuardMin * 60,
                     (InpExigirGuardian ? "NO SE OPERA."
                                        : "Se opera a tamaño pleno."));
        }
      return(InpExigirGuardian ? 0.0 : 1.0);
     }

   double f = GlobalVariableGet(GV_FACTOR);
   if(f <= 0.0 || f > 1.0)
     {
      PrintFormat("AVISO: factor del Guardian fuera de rango (%.3f). "
                  "Se opera a tamaño pleno.", f);
      return(1.0);
     }
   return(f);
  }

//+------------------------------------------------------------------+
//| Lotes para que la perdida en el stop sea InpRiesgoPorEvento % de |
//| la equity. Se calcula con tick value y tick size del simbolo, no |
//| con constantes: asi funciona en cualquier instrumento y divisa.  |
//| Devuelve 0 si no se puede calcular -> FALLA EN CERRADO.          |
//+------------------------------------------------------------------+
double CalcularLotes(const double precioEntrada, const double precioStop)
  {
   double dist = MathAbs(precioEntrada - precioStop);
   if(dist <= 0.0)
      return(0.0);

   double tickValue = SymbolInfoDouble(g_sim, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(g_sim, SYMBOL_TRADE_TICK_SIZE);
   if(tickValue <= 0.0 || tickSize <= 0.0)
     {
      Print("AVISO: tick value o tick size no disponibles -> no se opera");
      return(0.0);
     }

   double perdidaPorLote = dist / tickSize * tickValue;
   if(perdidaPorLote <= 0.0)
      return(0.0);

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double factor = FactorGuardian();
   double riesgo = equity * InpRiesgoPorEvento / 100.0 * factor;
   double lotes  = riesgo / perdidaPorLote;

   if(factor < 0.999)
      PrintFormat("dimensionado reducido por EA_Guardian: factor %.3f "
                  "-> riesgo efectivo %.2f%% en vez de %.2f%%",
                  factor, InpRiesgoPorEvento * factor, InpRiesgoPorEvento);

   double minL  = SymbolInfoDouble(g_sim, SYMBOL_VOLUME_MIN);
   double maxL  = SymbolInfoDouble(g_sim, SYMBOL_VOLUME_MAX);
   double paso  = SymbolInfoDouble(g_sim, SYMBOL_VOLUME_STEP);
   if(paso > 0.0)
      lotes = MathFloor(lotes / paso) * paso;
   if(InpLotesMax > 0.0)
      lotes = MathMin(lotes, InpLotesMax);
   lotes = MathMax(lotes, 0.0);
   lotes = MathMin(lotes, maxL);

   if(lotes < minL)
     {
      PrintFormat("AVISO: los lotes calculados (%.4f) son menores que el "
                  "minimo (%.4f). Riesgo %.2f%% de %.2f de equity con stop "
                  "de %.1f bp. No se opera.",
                  lotes, minL, InpRiesgoPorEvento, equity, InpStopBp);
      return(0.0);
     }
   return(NormalizeDouble(lotes, 2));
  }

//+------------------------------------------------------------------+
//| ¿hay posicion abierta de este EA en este simbolo?                |
//+------------------------------------------------------------------+
bool TengoPosicion(ulong &ticket, datetime &apertura)
  {
   ticket = 0;
   apertura = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sim)
         continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;
      ticket   = tk;
      apertura = (datetime)PositionGetInteger(POSITION_TIME);
      return(true);
     }
   return(false);
  }

//+------------------------------------------------------------------+
bool AbrirLargo(const int fechaEvento)
  {
   MqlTick tk;
   if(!SymbolInfoTick(g_sim, tk) || tk.ask <= 0.0)
     {
      g_cSinPrecio++;
      return(false);
     }

   int    dg   = (int)SymbolInfoInteger(g_sim, SYMBOL_DIGITS);
   double sl   = NormalizeDouble(tk.ask * (1.0 - InpStopBp / 10000.0), dg);
   double tp   = NormalizeDouble(tk.ask * (1.0 + InpTakeProfitBp / 10000.0), dg);
   double lots = CalcularLotes(tk.ask, sl);
   if(lots <= 0.0)
      return(false);

   MqlTradeRequest  req;  ZeroMemory(req);
   MqlTradeResult   res;  ZeroMemory(res);
   req.action       = TRADE_ACTION_DEAL;
   req.symbol       = g_sim;
   req.volume       = lots;
   req.type         = ORDER_TYPE_BUY;
   req.price        = tk.ask;
   req.sl           = sl;
   req.tp           = tp;
   req.deviation    = InpDeslizamiento;
   req.magic        = InpMagic;
   req.type_filling = ORDER_FILLING_IOC;
   req.comment      = "FOMC " + IntegerToString(fechaEvento);

   if(!OrderSend(req, res))
     {
      PrintFormat("FALLO al abrir: retcode=%d  %s", res.retcode, res.comment);
      return(false);
     }
   if(res.retcode != TRADE_RETCODE_DONE && res.retcode != TRADE_RETCODE_PLACED)
     {
      PrintFormat("FALLO al abrir: retcode=%d  %s", res.retcode, res.comment);
      return(false);
     }

   g_cEntradas++;
   g_ultimoEventoInt = fechaEvento;
   MqlDateTime nyE;
   TimeToStruct(AhoraNY(), nyE);
   Print("ENTRADA #", g_cEntradas, "  evento ", fechaEvento,
         "  hora NY ", StringFormat("%02d:%02d", nyE.hour, nyE.min),
         "  ", DoubleToString(lots, 2), " lotes a ", DoubleToString(tk.ask, dg),
         "  sl ", DoubleToString(sl, dg), "  tp ", DoubleToString(tp, dg),
         "  spread ", DoubleToString(SpreadBp(), 2), " bp");
   return(true);
  }

//+------------------------------------------------------------------+
bool CerrarPosicion(const ulong ticket, const string motivo)
  {
   if(!PositionSelectByTicket(ticket))
      return(false);

   MqlTick tk;
   if(!SymbolInfoTick(g_sim, tk) || tk.bid <= 0.0)
     {
      g_cSinPrecio++;
      return(false);
     }

   MqlTradeRequest  req;  ZeroMemory(req);
   MqlTradeResult   res;  ZeroMemory(res);
   req.action       = TRADE_ACTION_DEAL;
   req.symbol       = g_sim;
   req.volume       = PositionGetDouble(POSITION_VOLUME);
   req.type         = ORDER_TYPE_SELL;
   req.position     = ticket;
   req.price        = tk.bid;
   req.deviation    = InpDeslizamiento;
   req.magic        = InpMagic;
   req.type_filling = ORDER_FILLING_IOC;
   req.comment      = motivo;

   if(!OrderSend(req, res) ||
      (res.retcode != TRADE_RETCODE_DONE && res.retcode != TRADE_RETCODE_PLACED))
     {
      PrintFormat("FALLO al cerrar (%s): retcode=%d  %s",
                  motivo, res.retcode, res.comment);
      return(false);
     }
   Print("SALIDA (", motivo, ") a ",
         DoubleToString(tk.bid, (int)SymbolInfoInteger(g_sim, SYMBOL_DIGITS)));
   return(true);
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   datetime ahoraNY = AhoraNY();
   MqlDateTime ny;
   TimeToStruct(ahoraNY, ny);
   int minutosNY = ny.hour * 60 + ny.min;

   ulong    ticket;
   datetime apertura;
   bool     enPosicion = TengoPosicion(ticket, apertura);

   //================================================================
   // GESTION DE SALIDA
   //================================================================
   if(enPosicion)
     {
      //--- salida normal: hora de apertura del contado
      int minSalida = InpHoraSalidaNY * 60 + InpMinSalidaNY;
      if(EsDiaAnuncio(FechaInt(ny)) && minutosNY >= minSalida)
        {
         if(CerrarPosicion(ticket, "salida 09:30 NY"))
            g_cSalidasHora++;
         return;
        }

      //--- RED DE SEGURIDAD 1: duracion maxima. Esto es lo que evita el
      //    bug numero 2: si el simbolo deja de cotizar a la hora exacta
      //    de salida, la posicion no se queda abierta indefinidamente.
      //    La edad se calcula en LONG con signo: restar datetime y comparar
      //    contra un datetime deja la puerta abierta a que una diferencia
      //    negativa se lea como enorme y cierre la posicion al instante.
      //    POSITION_TIME nunca esta en el futuro, asi que hoy no puede
      //    pasar, pero el patron es el del bug 4 y no lo dejo escrito.
      long edadPos = (apertura > 0 ? (long)TimeCurrent() - (long)apertura : 0);
      if(apertura > 0 && edadPos > (long)InpDuracionMaxMin * 60)
        {
         if(CerrarPosicion(ticket, "red de seguridad: duracion maxima"))
            g_cSalidasRed++;
         return;
        }

      //--- RED DE SEGURIDAD 2: si ya pasamos del dia del anuncio, fuera
      if(FechaInt(ny) > g_ultimoEventoInt && g_ultimoEventoInt > 0)
        {
         if(CerrarPosicion(ticket, "red de seguridad: evento pasado"))
            g_cSalidasRed++;
         return;
        }
      return;   // con posicion abierta no se hace nada mas
     }

   //================================================================
   // GESTION DE ENTRADA
   //================================================================
   int evento = AnuncioManana(ahoraNY);
   if(evento == 0)
      return;                               // hoy no es dia de entrada
   if(evento == g_ultimoEventoInt)
      return;                               // este evento ya se opero

   //--- ¿tiene el Guardian la cuenta bloqueada? Si la equity esta cerca
   //    del suelo del trailing, este evento se salta. Perder un evento
   //    cuesta 24 bp de esperanza; perder la cuenta cuesta la cuota y
   //    todo el beneficio futuro.
   if(InpRespetarGuardian && GlobalVariableCheck(GV_BLOQUEO) &&
      GlobalVariableGet(GV_BLOQUEO) > 0.0)
     {
      g_cBloqueoGuardian++;
      if(g_cBloqueoGuardian % 100 == 1)
         PrintFormat("evento %d NO se opera: EA_Guardian tiene la cuenta "
                     "bloqueada", evento);
      return;
     }

   //--- La ventana se abre unos minutos ANTES de la hora objetivo.
   //    Motivo medido: NACUSD.c deja de cotizar a las 21:59 del servidor
   //    (16:00 NY, el cierre del contado) en una parte importante de los
   //    dias. Con la ventana abriendo exactamente a las 16:00 NY se
   //    perdian entradas sin que ningun filtro lo explicara.
   //    Entrar 3 minutos antes añade una exposicion intradia minima frente
   //    al efecto de 24 bp que se busca, y recupera esos eventos.
   int minEntrada  = InpHoraEntradaNY * 60 + InpMinEntradaNY;
   int minApertura = minEntrada - InpMinutosAntes;
   if(minutosNY < minApertura)
      return;                               // aun no se abre la ventana
   if(minutosNY > minEntrada + InpVentanaEntradaMin)
     {
      //--- se cerro la ventana sin poder entrar
      if(g_ultimoEventoInt != evento)
        {
         g_cVentanaPerdida++;
         PrintFormat("VENTANA PERDIDA para el evento %d (spread o precio)",
                     evento);
         g_ultimoEventoInt = evento;        // no reintentar hoy
        }
      return;
     }

   //--- FILTRO DE SPREAD. Falla EN CERRADO si no hay precio: esto evita
   //    el bug numero 3, donde un filtro sin datos devolvia 0 y se
   //    saltaba solo.
   double sp = SpreadBp();
   if(sp < 0.0)
     {
      g_cSinPrecio++;
      return;
     }
   if(sp > InpSpreadMaxBp)
     {
      g_cRechazoSpread++;
      if(InpLogDetallado && g_cRechazoSpread % 50 == 1)
         PrintFormat("spread %.2f bp > limite %.2f bp, esperando",
                     sp, InpSpreadMaxBp);
      return;
     }

   AbrirLargo(evento);
  }
//+------------------------------------------------------------------+
