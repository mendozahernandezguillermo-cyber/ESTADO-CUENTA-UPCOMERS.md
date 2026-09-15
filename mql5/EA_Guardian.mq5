//+------------------------------------------------------------------+
//|  EA_Guardian.mq5                                                 |
//|  Gestor del presupuesto de riesgo de la cuenta prop. NO OPERA.    |
//|                                                                  |
//|  QUE HACE, EN UNA FRASE                                          |
//|    Mide cuanto margen queda hasta el suelo del drawdown y publica |
//|    un FACTOR DE TAMAÑO que los demas EA aplican a su riesgo. Si   |
//|    el margen se estrecha, todo el mundo opera mas pequeño.        |
//|                                                                  |
//|  POR QUE ESCALA EL TAMAÑO EN VEZ DE CERRAR Y BLOQUEAR            |
//|    La primera version de este EA cerraba todo y bloqueaba la      |
//|    cuenta al acercarse al suelo. Al medirlo aparecio un fallo de  |
//|    diseño grave: si la equity queda POR DEBAJO del nivel de       |
//|    cierre, el bloqueo se levanta al dia siguiente pero la equity  |
//|    sigue debajo, asi que vuelve a disparar. Y otra vez. Es un     |
//|    ESTADO ABSORBENTE: la cuenta no se rompe pero no vuelve a      |
//|    operar, y cada intervencion cruza un spread que la empuja al   |
//|    suelo. Convertia un drawdown recuperable en una muerte lenta.  |
//|                                                                  |
//|    Medido sobre 20.000 caminos de 504 sesiones, cuenta de 50K,    |
//|    con el coste real de cerrar (3,5 bp) y con la #1 llegando      |
//|    como hueco nocturno:                                          |
//|                                                                  |
//|      diseño                          P(quema)  P(cobro)  EV/año   |
//|      sin Guardian                      11,4%     69,0%   1.619 $  |
//|      cierre duro 1,5% + bloqueo        21,6%     66,9%   1.577 $  |
//|      cierre duro 3,0% + bloqueo        41,3%     59,5%   1.419 $  |
//|      ESCALADO ref 5%, min 0,25          0,3%     66,1%   1.535 $  |
//|      escalado + cierre duro 0,5%        1,0%     66,2%   1.523 $  |
//|                                                                  |
//|    Dos lecturas que hay que tener claras:                         |
//|      · el escalado divide la probabilidad de quema por 38 y       |
//|        cuesta el 6% del valor esperado;                           |
//|      · añadir el cierre duro ENCIMA del escalado EMPEORA las      |
//|        cosas (0,3% -> 1,0% de quema) sin ganar nada de EV. Por    |
//|        eso viene desactivado. Cristaliza la perdida y paga el     |
//|        spread justo cuando la posicion pequeña habria aguantado.  |
//|                                                                  |
//|  LO QUE ESTE EA *NO* PUEDE HACER                                 |
//|    · No puede evitar un hueco que atraviese el suelo de un salto. |
//|      La #1 pre-FOMC se cobra ENTERA en el hueco de la apertura:   |
//|      cuando el mercado abre, el resultado ya esta ahi. Contra eso |
//|      solo sirve el tamaño, y de eso se encarga el factor.         |
//|    · No puede actuar con el mercado cerrado.                      |
//|    · No sustituye al stop loss de cada EA.                        |
//|    · No vigila la regla de consistencia ni los dias minimos.      |
//|                                                                  |
//|  LO QUE SI SIGUE CERRANDO A LO BRUTO                             |
//|    · Exceso de exposicion (un EA con un fallo abriendo en bucle). |
//|      Ahi si bloquea, porque eso no es un drawdown: es una averia. |
//|    · Una posicion suelta que pierde mas de lo que deberia, señal  |
//|      de que su stop no llego al servidor.                         |
//|                                                                  |
//|  COMO LO USAN LOS DEMAS EA                                       |
//|    Este EA publica variables globales del terminal:               |
//|      GUARDIAN_FACTOR   0..1  multiplicador del riesgo             |
//|      GUARDIAN_BLOQUEO  0 = se puede operar, >0 = averia           |
//|      GUARDIAN_MARGEN_PCT  margen hasta el suelo, en %             |
//|    EA_FOMC_Gap ya las lee. Cualquier EA nuevo debe hacer lo mismo.|
//+------------------------------------------------------------------+
#property copyright "Proyecto de auditoria cuantitativa"
#property version   "2.00"
#property strict

//--- entradas -------------------------------------------------------
input group           "=== Parametros de la cuenta prop ==="
input double          InpSaldoInicial      = 0.0;    // Saldo inicial de la cuenta (0 = usar el actual)
input double          InpPicoInicial       = 0.0;    // Pico de equity ya alcanzado (0 = deducir)
input double          InpTrailingPct       = 7.0;    // Drawdown trailing maximo, %
input double          InpDiarioPct         = 4.0;    // Perdida diaria maxima, %
input bool            InpDDRelativo        = true;   // Los % se aplican a la referencia, no al saldo inicial
input bool            InpTrailingSeBloquea = true;   // El suelo deja de subir al llegar al saldo inicial
input double          InpNivelBloqueoPct   = 0.0;    // Nivel en que se bloquea, % sobre el saldo inicial
input int             InpHoraResetUTC      = 0;      // Hora de reinicio del dia de riesgo (UTC)

input group           "=== Escalado del tamaño (mecanismo principal) ==="
input bool            InpEscalarTamano     = true;   // Publicar el factor de tamaño
input double          InpMargenPleno       = 5.0;    // Margen con el que se opera a tamaño pleno, %
input double          InpFactorMinimo      = 0.25;   // Suelo del factor de tamaño

input group           "=== Cierre de emergencia (desactivado por medicion) ==="
input double          InpColchonTrailingPct= 0.0;    // Cerrar a este % sobre el suelo trailing (0 = off)
input double          InpColchonDiarioPct  = 0.0;    // Cerrar a este % sobre el suelo diario (0 = off)
input double          InpMargenAlarmaPct   = 2.00;   // Avisar cuando el margen baje de este %

input group           "=== Vigilancia de averias ==="
input int             InpMaxPosiciones     = 12;     // Maximo de posiciones simultaneas (0 = sin limite)
input double          InpMaxVolumenLotes   = 0.0;    // Maximo de lotes sumados (0 = sin limite)
input double          InpMaxPerdidaPosPct  = 1.50;   // Cerrar una posicion suelta si pierde este % (limite Vanguard 2% = HARD BREACH)

input group           "=== Cobros y movimientos de saldo ==="
input bool            InpDetectarPagos     = true;   // Detectar cobros, depositos y correcciones
input bool            InpPagoReiniciaSuelo = false;  // Un cobro reinicia el pico y el suelo
input int             InpSegRevisarPagos   = 60;     // Cada cuantos segundos revisar el historial

input group           "=== Inactividad (la cuenta expira a los 35 dias) ==="
input bool            InpVigilarInactiv    = true;   // Vigilar el plazo de inactividad
input int             InpDiasSinCerrar     = 25;     // Actuar tras N dias sin CERRAR nada
input string          InpSimboloActividad  = "USDCHF"; // Latido: NO usar ninguno de los 8 del trend ni NACUSD.c (seria hedging)
input long            InpMagicActividad    = 20260909; // Magic del latido

input group           "=== Comportamiento ==="
input bool            InpSoloAvisar        = false;  // Modo ensayo: avisa pero NO cierra
input bool            InpReiniciarPico     = false;  // Olvidar el pico guardado y empezar de cero
input int             InpDeslizamiento     = 50;     // Deslizamiento permitido al cerrar (puntos)
input int             InpSegundosLog       = 900;    // Cada cuantos segundos registrar el estado

input group           "=== Horario del servidor ==="
input bool            InpAutoHoraNY        = true;   // Calcular la hora de NY automaticamente
input int             InpBrokerGMT         = 2;      // Offset GMT del servidor del broker
input int             InpOffsetServidorNY  = 6;      // Offset manual (solo si Auto = false)

//--- variables globales del terminal que este EA publica -------------
#define GV_PICO      "GUARDIAN_PICO"
#define GV_BLOQUEO   "GUARDIAN_BLOQUEO"
#define GV_FACTOR    "GUARDIAN_FACTOR"
#define GV_MARGEN    "GUARDIAN_MARGEN_PCT"
#define GV_DIA       "GUARDIAN_DIA_RIESGO"
#define GV_BASEDIA   "GUARDIAN_BASE_DIA"
#define GV_SALDOINI  "GUARDIAN_SALDO_INICIAL"
#define GV_ULTDEAL   "GUARDIAN_ULT_DEAL_SALDO"
#define GV_CUENTA    "GUARDIAN_CUENTA"
#define GV_LATIDO    "GUARDIAN_LATIDO"

//--- estado ---------------------------------------------------------
double   g_saldoIni      = 0.0;
double   g_pico          = 0.0;
double   g_baseDia       = 0.0;
int      g_diaRiesgo     = 0;
bool     g_bloqueado     = false;   // solo por AVERIA, no por drawdown
string   g_motivoBloqueo = "";
datetime g_ultimoLog     = 0;
double   g_margenMinimo  = 999.0;
double   g_factorMinVisto= 1.0;
double   g_ultimoFactor  = 1.0;
bool     g_avisoOffset   = false;
bool     g_avisoAlarma   = false;

int      g_cCierresOk    = 0;
int      g_cCierresFallo = 0;
int      g_cEmergencia   = 0;
int      g_cPosSueltas   = 0;
int      g_cAverias      = 0;
int      g_cPagos        = 0;
int      g_cActividad    = 0;
datetime g_ultActividad  = 0;
datetime g_ultCierreVisto= 0;

ulong    g_ultDealSaldo  = 0;      // ultimo apunte de saldo ya procesado
datetime g_ultRevision   = 0;
datetime g_arranqueEA    = 0;
bool     g_pagoSinResolver = false;

//--- declaraciones adelantadas --------------------------------------
bool     EsVeranoEEUU(const datetime utc);
datetime AhoraUTC();
datetime AhoraNY();
int      DiaDeRiesgo();
void     AbrirDiaDeRiesgo();
double   SueloTrailing();
double   SueloDiario();
double   SueloEfectivo();
double   NivelEmergencia();
double   MargenPct();
double   FactorTamano();
bool     CerrarTodo(const string motivo);
void     Bloquear(const string motivo);
void     Desbloquear(const string motivo);
ulong    UltimoApunteDeSaldo();
datetime UltimoCierre();
void     VigilarInactividad();
void     RevisarMovimientosDeSaldo();

//+------------------------------------------------------------------+
int OnInit()
  {
   //--- ¿HEMOS CAMBIADO DE CUENTA?
   //
   //    Las variables globales del terminal son DEL TERMINAL, no de la
   //    cuenta. Al iniciar sesion en otra cuenta con el mismo terminal, el
   //    Guardian se encontraria el pico, la base diaria y el bloqueo de la
   //    cuenta ANTERIOR, y calcularia los suelos de una cuenta que ya no es
   //    esta. Sin ningun aviso, porque los numeros pareceran validos.
   //
   //    Se guarda el numero de cuenta y, si cambia, se borra todo el estado.
   //    Es el unico caso en que reiniciar el pico es lo correcto.
   long cuentaActual = AccountInfoInteger(ACCOUNT_LOGIN);
   bool cuentaNueva  = false;
   if(GlobalVariableCheck(GV_CUENTA))
     {
      long guardada = (long)GlobalVariableGet(GV_CUENTA);
      if(guardada != cuentaActual && guardada != 0)
        {
         cuentaNueva = true;
         Print("**********************************************************");
         Print("GUARDIAN: la cuenta ha cambiado (",
               IntegerToString(guardada), " -> ",
               IntegerToString(cuentaActual), ").");
         Print("  Se BORRA todo el estado guardado: pico, base diaria,");
         Print("  bloqueo y apuntes de saldo. Los suelos se recalculan desde");
         Print("  cero para esta cuenta.");
         Print("  COMPRUEBA que InpSaldoInicial corresponde a ESTA cuenta.");
         Print("**********************************************************");
         GlobalVariableDel(GV_PICO);
         GlobalVariableDel(GV_BASEDIA);
         GlobalVariableDel(GV_DIA);
         GlobalVariableDel(GV_BLOQUEO);
         GlobalVariableDel(GV_ULTDEAL);
         GlobalVariableDel(GV_SALDOINI);
         GlobalVariableDel(GV_FACTOR);
         GlobalVariableDel(GV_MARGEN);
        }
     }
   GlobalVariableSet(GV_CUENTA, (double)cuentaActual);

   //--- El saldo inicial es el numero del que cuelga TODO lo demas. Si no
   //    se puede determinar, el EA no arranca: un guardian que vigila
   //    contra una referencia equivocada es peor que ninguno.
   if(InpSaldoInicial > 0.0)
      g_saldoIni = InpSaldoInicial;
   else if(GlobalVariableCheck(GV_SALDOINI) && GlobalVariableGet(GV_SALDOINI) > 0.0)
      g_saldoIni = GlobalVariableGet(GV_SALDOINI);
   else
      g_saldoIni = AccountInfoDouble(ACCOUNT_BALANCE);

   if(g_saldoIni <= 0.0)
     {
      Print("ERROR: no se puede determinar el saldo inicial. ",
            "Rellena InpSaldoInicial a mano.");
      return(INIT_FAILED);
     }
   if(InpTrailingPct <= 0.0 || InpDiarioPct <= 0.0)
     {
      Print("ERROR: los limites de drawdown deben ser positivos.");
      return(INIT_FAILED);
     }
   if(InpEscalarTamano &&
      (InpMargenPleno <= 0.0 || InpMargenPleno > InpTrailingPct))
     {
      Print("ERROR: InpMargenPleno debe estar entre 0 y InpTrailingPct.");
      return(INIT_FAILED);
     }
   if(InpEscalarTamano &&
      (InpFactorMinimo <= 0.0 || InpFactorMinimo > 1.0))
     {
      Print("ERROR: InpFactorMinimo debe estar entre 0 y 1.");
      return(INIT_FAILED);
     }
   if(InpColchonTrailingPct >= InpTrailingPct ||
      InpColchonDiarioPct >= InpDiarioPct)
     {
      Print("ERROR: un colchon no puede ser mayor que su propio limite. ",
            "Cerraria siempre.");
      return(INIT_FAILED);
     }

   GlobalVariableSet(GV_SALDOINI, g_saldoIni);

   //--- El pico de equity sobrevive al reinicio del terminal, porque un
   //    pico olvidado SUBE el suelo real sin que el EA lo sepa: la firma
   //    no lo olvida.
   //    Y hay un caso que NO se puede deducir: si la cuenta ya estuvo por
   //    encima de su saldo inicial ANTES de instalar el Guardian, ese pico
   //    existe para la firma pero no para mi. Deducirlo del saldo inicial
   //    da un suelo mas BAJO del real, que es el sentido peligroso del
   //    error. Para eso esta InpPicoInicial: se saca del panel de la firma.
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double base   = MathMax(equity, g_saldoIni);
   if(InpPicoInicial > 0.0)
      base = MathMax(base, InpPicoInicial);

   if(InpReiniciarPico || cuentaNueva || !GlobalVariableCheck(GV_PICO))
      g_pico = base;
   else
      g_pico = MathMax(GlobalVariableGet(GV_PICO), base);
   GlobalVariableSet(GV_PICO, g_pico);

   if(InpPicoInicial <= 0.0 && equity < g_saldoIni * 0.999)
     {
      Print("  AVISO: la equity esta POR DEBAJO del saldo inicial y no has");
      Print("  dado InpPicoInicial. Asumo que la cuenta nunca subio por");
      Print("  encima del saldo inicial. Si SI subio, el suelo real de la");
      Print("  firma esta mas ARRIBA que el que calculo yo, y creeras tener");
      Print("  mas margen del que hay. Mira el nivel de drawdown en tu panel");
      Print("  y, si no coincide, pon el pico a mano en InpPicoInicial.");
     }

   g_diaRiesgo = DiaDeRiesgo();
   if(GlobalVariableCheck(GV_DIA) &&
      (int)GlobalVariableGet(GV_DIA) == g_diaRiesgo &&
      GlobalVariableCheck(GV_BASEDIA) && GlobalVariableGet(GV_BASEDIA) > 0.0)
      g_baseDia = GlobalVariableGet(GV_BASEDIA);
   else
      AbrirDiaDeRiesgo();

   //--- un bloqueo por averia heredado NO se levanta solo: una averia hay
   //    que mirarla antes de volver a operar
   g_bloqueado = (GlobalVariableCheck(GV_BLOQUEO) &&
                  GlobalVariableGet(GV_BLOQUEO) > 0.0);
   if(g_bloqueado)
     {
      g_motivoBloqueo = "averia heredada de una sesion anterior";
      Print("AVISO: el Guardian arranca BLOQUEADO por una averia previa.");
      Print("       Revisa el historial y borra la variable global ",
            GV_BLOQUEO, " a mano cuando sepas que paso.");
     }

   //--- Apuntes de saldo ya existentes: se marcan como vistos para no
   //    reaccionar a un cobro de la semana pasada al reiniciar el terminal.
   if(GlobalVariableCheck(GV_ULTDEAL) && GlobalVariableGet(GV_ULTDEAL) > 0.0)
      g_ultDealSaldo = (ulong)GlobalVariableGet(GV_ULTDEAL);
   else
     {
      g_ultDealSaldo = UltimoApunteDeSaldo();
      GlobalVariableSet(GV_ULTDEAL, (double)g_ultDealSaldo);
     }
   g_ultRevision = TimeCurrent();
   g_arranqueEA  = TimeCurrent();

   //--- Un tick por segundo aunque el mercado este quieto. Sin esto el
   //    Guardian solo miraria cuando llega precio, y en los ratos de poca
   //    liquidez es justo cuando hace falta.
   EventSetTimer(1);

   double f = FactorTamano();
   GlobalVariableSet(GV_FACTOR, f);
   g_ultimoFactor = f;

   Print("=== EA_Guardian v2 activo ",
         (InpSoloAvisar ? "(MODO ENSAYO: no cierra)" : ""), " ===");
   Print("  cuenta                      : ", IntegerToString(cuentaActual),
         (cuentaNueva ? "   (NUEVA: estado reiniciado)" : ""));
   PrintFormat("  saldo inicial de referencia : %.2f %s",
               g_saldoIni, AccountInfoString(ACCOUNT_CURRENCY));
   PrintFormat("  equity ahora / pico         : %.2f / %.2f", equity, g_pico);
   PrintFormat("  suelo trailing (%.1f%%)      : %.2f",
               InpTrailingPct, SueloTrailing());
   PrintFormat("  suelo diario   (%.1f%%)      : %.2f   "
               "(base = MAYOR de saldo/equity a las %02d:00 UTC)",
               InpDiarioPct, SueloDiario(), InpHoraResetUTC);
   PrintFormat("  margen disponible           : %.2f%% del saldo inicial",
               MargenPct());
   if(InpEscalarTamano)
      PrintFormat("  FACTOR DE TAMAÑO publicado  : %.3f  "
                  "(pleno con %.1f%% de margen, suelo %.2f)",
                  f, InpMargenPleno, InpFactorMinimo);
   else
      Print("  escalado DESACTIVADO: el factor se publica siempre a 1,000.");
   if(InpColchonTrailingPct > 0.0 || InpColchonDiarioPct > 0.0)
      PrintFormat("  cierre de emergencia ACTIVADO en %.2f "
                  "(medido: empeora la quema, usalo solo si no te fias)",
                  NivelEmergencia());
   else
      Print("  cierre de emergencia por equity DESACTIVADO (asi debe estar).");
   if(InpSaldoInicial <= 0.0)
     {
      Print("  AVISO IMPORTANTE: InpSaldoInicial = 0, se ha tomado el saldo");
      Print("  actual (", DoubleToString(g_saldoIni, 2), ") como inicial. Si la");
      Print("  cuenta ya acumula beneficio o perdida, esto esta MAL y todos");
      Print("  los suelos saldran desplazados. Pon el numero a mano.");
     }
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   Print("=== EA_Guardian detenido (motivo ", reason, ") ===");
   PrintFormat("  bloqueos por averia           : %d", g_cAverias);
   PrintFormat("  cierres de emergencia         : %d", g_cEmergencia);
   PrintFormat("  posiciones cerradas (sueltas) : %d", g_cPosSueltas);
   PrintFormat("  cierres correctos / fallidos  : %d / %d",
               g_cCierresOk, g_cCierresFallo);
   PrintFormat("  movimientos de saldo vistos   : %d", g_cPagos);
   PrintFormat("  latidos de actividad           : %d", g_cActividad);
   PrintFormat("  peor margen visto             : %.2f%%", g_margenMinimo);
   PrintFormat("  factor de tamaño minimo visto : %.3f", g_factorMinVisto);
   if(g_pagoSinResolver)
      Print("  AVISO: hubo un cobro y NO se reinicio el pico. Comprueba el ",
            "margen contra el panel de la firma antes de seguir operando.");
   if(g_cCierresFallo > 0)
      Print("  AVISO: hubo cierres fallidos. Revisa si el mercado estaba ",
            "cerrado o si el modo de llenado del simbolo es el correcto.");
   if(g_cAverias == 0 && g_cEmergencia == 0 && g_cPosSueltas == 0)
      Print("  El Guardian no tuvo que cerrar nada.");
  }

//+------------------------------------------------------------------+
//| ¿esta la costa este de EE.UU. en horario de verano en ese UTC?     |
//| Mismas reglas que EA_FOMC_Gap: el servidor esta en GMT+2 FIJO y    |
//| Nueva York no, asi que el desfase cambia de 6 a 7 horas.           |
//+------------------------------------------------------------------+
bool EsVeranoEEUU(const datetime utc)
  {
   MqlDateTime t;
   TimeToStruct(utc, t);
   int anio = t.year;

   MqlDateTime m;  ZeroMemory(m);
   m.year = anio;  m.mon = 3;  m.day = 1;
   datetime mar1 = StructToTime(m);
   TimeToStruct(mar1, m);
   int primerDomMar  = 1 + ((7 - m.day_of_week) % 7);
   int segundoDomMar = primerDomMar + 7;
   MqlDateTime ini;  ZeroMemory(ini);
   ini.year = anio;  ini.mon = 3;  ini.day = segundoDomMar;  ini.hour = 7;
   datetime inicio = StructToTime(ini);

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
//| UTC. Se extrae aparte porque el dia de riesgo de la firma se define |
//| en UTC y no en hora de Nueva York: la documentacion de Upcomers dice |
//| que el limite diario se reinicia a las 00:00 UTC.                    |
//|                                                                     |
//| Con InpAutoHoraNY = false no se puede usar InpOffsetServidorNY, que  |
//| es un desfase a NUEVA YORK. Para UTC hay que usar InpBrokerGMT.      |
//+------------------------------------------------------------------+
datetime AhoraUTC()
  {
   datetime servidor = TimeCurrent();
   if(!InpAutoHoraNY)
      return(servidor - (datetime)(InpBrokerGMT * 3600));

   datetime g        = TimeGMT();
   long     dif      = (long)servidor - (long)g;
   datetime utc;

   //--- En el Probador TimeGMT() devuelve lo mismo que TimeCurrent(), asi
   //    que un desfase de CERO no significa "servidor en UTC": significa
   //    que la funcion no esta informada.
   bool fiable = (g > 0 && dif != 0 && MathAbs(dif) <= 14 * 3600);

   if(fiable)
      utc = g;
   else
     {
      utc = servidor - (datetime)(InpBrokerGMT * 3600);
      if(!g_avisoOffset)
        {
         Print("AVISO: TimeGMT() no informado. Se reconstruye UTC como hora ",
               "del servidor menos GMT", (InpBrokerGMT >= 0 ? "+" : ""),
               InpBrokerGMT, ".");
         g_avisoOffset = true;
        }
     }

   return(utc);
  }

//+------------------------------------------------------------------+
datetime AhoraNY()
  {
   if(!InpAutoHoraNY)
      return(TimeCurrent() - (datetime)(InpOffsetServidorNY * 3600));
   datetime utc = AhoraUTC();
   return(utc - (datetime)((EsVeranoEEUU(utc) ? 4 : 5) * 3600));
  }

//+------------------------------------------------------------------+
//| Identificador del dia de riesgo (AAAAMMDD), definido en UTC.       |
//|                                                                  |
//| La documentacion de Upcomers es explicita: el limite diario se     |
//| reinicia a las 00:00 UTC. Yo lo tenia a las 17:00 de Nueva York,   |
//| que son las 20:00 UTC en verano y las 19:00 en invierno: reiniciaba |
//| dos o tres horas antes que la firma, con una base distinta de la    |
//| suya durante esa ventana.                                          |
//+------------------------------------------------------------------+
int DiaDeRiesgo()
  {
   datetime t = AhoraUTC() - (datetime)(InpHoraResetUTC * 3600);
   MqlDateTime d;
   TimeToStruct(t, d);
   return(d.year * 10000 + d.mon * 100 + d.day);
  }

//+------------------------------------------------------------------+
void AbrirDiaDeRiesgo()
  {
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double eq  = AccountInfoDouble(ACCOUNT_EQUITY);

   //--- EL MAYOR de los dos. Esto lo tenia AL REVES, y era el error mas
   //    grave del EA.
   //
   //    Documentacion de Upcomers, literal en su formula:
   //       limite diario = MAYOR de (equity, balance) a las 00:00 UTC
   //                       x (1 - porcentaje)
   //
   //    Yo tomaba el MENOR, razonando que era "la lectura estricta". La
   //    direccion es la contraria: una base menor da un SUELO MENOR, o sea
   //    MAS margen del que hay de verdad. Su ejemplo 3 lo enseña: con saldo
   //    105.000 y equity 102.000 el suelo real es 99.750 y quedan 2.250; mi
   //    version calculaba 97.920 y habria anunciado 4.080. Un 81% de margen
   //    inventado, justo en el sentido que mata cuentas.
   //
   //    Y no lo detecto la comparacion con el panel: en ese momento el P/G
   //    flotante era 0, asi que balance y equity coincidian y las dos
   //    formulas daban lo mismo. Verifique contra el unico punto que no
   //    distingue las hipotesis.
   g_baseDia   = MathMax(bal, eq);
   g_diaRiesgo = DiaDeRiesgo();

   GlobalVariableSet(GV_DIA, (double)g_diaRiesgo);
   GlobalVariableSet(GV_BASEDIA, g_baseDia);
   g_avisoAlarma = false;

   PrintFormat("--- dia de riesgo %d (UTC) | base diaria %.2f = MAYOR de "
               "saldo %.2f y equity %.2f | suelo diario %.2f | "
               "suelo trailing %.2f | factor %.3f",
               g_diaRiesgo, g_baseDia, bal, eq, SueloDiario(),
               SueloTrailing(), FactorTamano());
   if(MathAbs(bal - eq) > 0.01)
      Print("    OJO: habia posiciones abiertas en el reinicio. La base sale "
            "del MAYOR de los dos, asi que si esa posicion se gira te queda "
            "menos margen del que sugiere la equity de ahora.");
  }

//+------------------------------------------------------------------+
//| Suelo del drawdown trailing. Persigue al pico de equity a una       |
//| distancia fija en dinero y deja de subir al alcanzar el nivel de    |
//| bloqueo (por defecto el saldo inicial).                             |
//+------------------------------------------------------------------+
double SueloTrailing()
  {
   //--- RELATIVO al pico, que es lo que hace Upcomers. Verificado contra su
   //    panel: marca de agua alta 25.003,10 y limite 23.752,95, y
   //    25.003,10 x 0,95 = 23.752,945. Con la version absoluta (5% del
   //    saldo inicial) saldria 23.753,10: coincide de casualidad porque la
   //    cuenta esta pegada a su saldo inicial. En cuanto acumulas beneficio
   //    las dos formulas se separan, y la absoluta es la MAS estricta.
   double suelo = (InpDDRelativo
                   ? g_pico * (1.0 - InpTrailingPct / 100.0)
                   : g_pico - g_saldoIni * InpTrailingPct / 100.0);
   if(InpTrailingSeBloquea)
      suelo = MathMin(suelo,
                      g_saldoIni * (1.0 + InpNivelBloqueoPct / 100.0));
   return(suelo);
  }

//+------------------------------------------------------------------+
double SueloDiario()
  {
   if(g_baseDia <= 0.0)
      return(0.0);
   //--- Tambien RELATIVO, y aqui la prueba es concluyente: el panel da
   //    23.769,38 y 24.759,77 x 0,96 = 23.769,3792. La version absoluta
   //    (4% de 25.000) daria 23.759,77, casi 10 $ mas abajo.
   return(InpDDRelativo
          ? g_baseDia * (1.0 - InpDiarioPct / 100.0)
          : g_baseDia - g_saldoIni * InpDiarioPct / 100.0);
  }

//+------------------------------------------------------------------+
double SueloEfectivo()
  {
   return(MathMax(SueloTrailing(), SueloDiario()));
  }

//+------------------------------------------------------------------+
double NivelEmergencia()
  {
   double a = -1e18, b = -1e18;
   if(InpColchonTrailingPct > 0.0)
      a = SueloTrailing() + g_saldoIni * InpColchonTrailingPct / 100.0;
   if(InpColchonDiarioPct > 0.0)
      b = SueloDiario() + g_saldoIni * InpColchonDiarioPct / 100.0;
   return(MathMax(a, b));
  }

//+------------------------------------------------------------------+
//| Margen hasta el suelo efectivo, en % del saldo inicial.            |
//+------------------------------------------------------------------+
double MargenPct()
  {
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   return((eq - SueloEfectivo()) / g_saldoIni * 100.0);
  }

//+------------------------------------------------------------------+
//| EL FACTOR DE TAMAÑO. Es la pieza central de este EA.               |
//|                                                                    |
//| Se mide contra el suelo TRAILING, no contra el efectivo, a         |
//| proposito: el suelo diario se reinicia cada dia y meterlo aqui     |
//| haria saltar el factor al reinicio, cambiando el tamaño de las     |
//| posiciones por un motivo que no es riesgo real acumulado.          |
//|                                                                    |
//| El resultado se recorta por abajo para no dejar de operar del todo: |
//| una cuenta que no opera no puede recuperarse, y ese fue justo el   |
//| fallo de la version 1.                                             |
//+------------------------------------------------------------------+
double FactorTamano()
  {
   if(!InpEscalarTamano)
      return(1.0);

   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(eq <= 0.0 || g_saldoIni <= 0.0)
      return(InpFactorMinimo);         // sin dato fiable, el minimo

   double margen = (eq - SueloTrailing()) / g_saldoIni * 100.0;
   double f      = margen / InpMargenPleno;
   if(f > 1.0)
      f = 1.0;
   if(f < InpFactorMinimo)
      f = InpFactorMinimo;
   return(f);
  }

//+------------------------------------------------------------------+
//| Ticket del apunte de saldo mas reciente que ya existe en el        |
//| historial. Se usa al arrancar para NO reaccionar a cobros viejos.  |
//+------------------------------------------------------------------+
ulong UltimoApunteDeSaldo()
  {
   ulong maxTk = 0;
   if(!HistorySelect(0, TimeCurrent() + 86400))
      return(0);
   int n = HistoryDealsTotal();
   for(int i = 0; i < n; i++)
     {
      ulong tk = HistoryDealGetTicket(i);
      if(tk == 0)
         continue;
      long tipo = HistoryDealGetInteger(tk, DEAL_TYPE);
      if(tipo != DEAL_TYPE_BALANCE && tipo != DEAL_TYPE_CREDIT &&
         tipo != DEAL_TYPE_CORRECTION && tipo != DEAL_TYPE_BONUS)
         continue;
      if(tk > maxTk)
         maxTk = tk;
     }
   return(maxTk);
  }

//+------------------------------------------------------------------+
//| Momento del ultimo CIERRE de operacion. Devuelve 0 si no hay.      |
//|                                                                  |
//| Ojo: se buscan deals de SALIDA (DEAL_ENTRY_OUT / INOUT / OUT_BY),  |
//| no de entrada. La regla de inactividad de la firma se reinicia al  |
//| CERRAR, no al abrir: mantener siete posiciones un mes no cuenta    |
//| como actividad.                                                   |
//+------------------------------------------------------------------+
datetime UltimoCierre()
  {
   if(!HistorySelect(0, TimeCurrent() + 86400))
      return(0);
   datetime ult = 0;
   int n = HistoryDealsTotal();
   for(int i = 0; i < n; i++)
     {
      ulong tk = HistoryDealGetTicket(i);
      if(tk == 0)
         continue;
      long entrada = HistoryDealGetInteger(tk, DEAL_ENTRY);
      if(entrada != DEAL_ENTRY_OUT && entrada != DEAL_ENTRY_INOUT &&
         entrada != DEAL_ENTRY_OUT_BY)
         continue;
      datetime t = (datetime)HistoryDealGetInteger(tk, DEAL_TIME);
      if(t > ult)
         ult = t;
     }
   return(ult);
  }

//+------------------------------------------------------------------+
//| VIGILANCIA DE INACTIVIDAD.                                        |
//|                                                                  |
//| Upcomers expira y marca como FALLIDA cualquier cuenta CFD que pase |
//| 35 dias naturales sin actividad, y el contador se reinicia al      |
//| CERRAR una operacion. Esto no es un detalle administrativo: medido |
//| sobre el calendario real, es el riesgo DOMINANTE del sistema.      |
//|                                                                  |
//|   · el 97% de los huecos entre anuncios del FOMC pasan de 35 dias  |
//|     (mediana 43, maximo 91): la estrategia de eventos NO puede     |
//|     mantener la cuenta viva ni en teoria                          |
//|   · el rebalanceo mensual cierra algo solo el 79,5% de las veces,  |
//|     porque el umbral del 20% mantiene las posiciones               |
//|   · combinando ambos: 80,8% de probabilidad de expirar en un año   |
//|                                                                  |
//| La solucion es un LATIDO DE ACTIVIDAD: abrir el lote minimo en el  |
//| simbolo mas barato de la cesta y cerrarlo acto seguido. Con EURUSD |
//| a 0,26 bp de spread y 0,01 lotes, cuesta unos 3 centimos.          |
//|                                                                  |
//| Se actua a los 25 dias, no a los 34: diez dias de margen para que  |
//| un terminal apagado o un fin de semana largo no se lo coman.       |
//+------------------------------------------------------------------+
void VigilarInactividad()
  {
   if(!InpVigilarInactiv)
      return;

   //--- ¿hay un latido a medio hacer? cerrarlo antes que nada
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0)
         continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagicActividad)
         continue;
      if(CerrarPosicion(tk, "latido de actividad"))
        {
         g_cActividad++;
         g_ultActividad = TimeCurrent();
         Print("GUARDIAN: latido de actividad completado. El plazo de "
               "inactividad queda reiniciado.");
        }
      return;                     // una cosa por pasada
     }

   //--- referencia: ultimo cierre; si no hay ninguno, el primer deal de la
   //    cuenta; si tampoco, el arranque de este EA. Nunca se asume que hay
   //    mas margen del que se puede demostrar.
   datetime ref = UltimoCierre();
   if(ref <= 0)
     {
      if(HistorySelect(0, TimeCurrent() + 86400) && HistoryDealsTotal() > 0)
        {
         ulong tk = HistoryDealGetTicket(0);
         if(tk > 0)
            ref = (datetime)HistoryDealGetInteger(tk, DEAL_TIME);
        }
     }
   if(ref <= 0)
      ref = g_arranqueEA;

   long dias = ((long)TimeCurrent() - (long)ref) / 86400;
   if(dias < (long)InpDiasSinCerrar)
      return;

   //--- enfriamiento: no reintentar mas de una vez cada 12 horas
   if(g_ultActividad > 0 &&
      ((long)TimeCurrent() - (long)g_ultActividad) < 12 * 3600)
      return;

   if(InpSoloAvisar)
     {
      PrintFormat("GUARDIAN [ENSAYO]: %d dias sin cerrar nada. Aqui abriria y "
                  "cerraria %s al lote minimo para reiniciar el plazo.",
                  (int)dias, InpSimboloActividad);
      g_ultActividad = TimeCurrent();
      return;
     }

   string sim = InpSimboloActividad;
   if(!SymbolSelect(sim, true))
     {
      PrintFormat("GUARDIAN: no existe el simbolo de actividad '%s'. "
                  "CORRIGELO: la cuenta expira a los 35 dias.", sim);
      g_ultActividad = TimeCurrent();
      return;
     }

   MqlTick tk;
   double minL = SymbolInfoDouble(sim, SYMBOL_VOLUME_MIN);
   if(!SymbolInfoTick(sim, tk) || tk.ask <= 0.0 || minL <= 0.0)
      return;                     // sin precio no se abre; se reintenta

   MqlTradeRequest  req;  ZeroMemory(req);
   MqlTradeResult   res;  ZeroMemory(res);
   req.action       = TRADE_ACTION_DEAL;
   req.symbol       = sim;
   req.volume       = minL;
   req.type         = ORDER_TYPE_BUY;
   req.price        = tk.ask;
   req.deviation    = InpDeslizamiento;
   req.magic        = InpMagicActividad;
   req.type_filling = LlenadoDe(sim);
   req.comment      = "actividad";

   bool ok = OrderSend(req, res);
   if(!ok || (res.retcode != TRADE_RETCODE_DONE &&
              res.retcode != TRADE_RETCODE_PLACED))
     {
      req.type_filling = (req.type_filling == ORDER_FILLING_FOK
                          ? ORDER_FILLING_IOC : ORDER_FILLING_FOK);
      ZeroMemory(res);
      ok = OrderSend(req, res);
     }

   if(!ok || (res.retcode != TRADE_RETCODE_DONE &&
              res.retcode != TRADE_RETCODE_PLACED))
     {
      PrintFormat("GUARDIAN: FALLO al abrir el latido de actividad en %s: "
                  "retcode=%d %s", sim, res.retcode, res.comment);
      g_ultActividad = TimeCurrent();
      return;
     }

   PrintFormat("GUARDIAN: %d dias sin cerrar nada (limite de la firma 35). "
               "Abierto latido de actividad: %s %.2f lotes. Se cierra en la "
               "siguiente pasada.", (int)dias, sim, minL);
  }

//+------------------------------------------------------------------+
//| COBROS Y MOVIMIENTOS DE SALDO. Esto faltaba y era grave.          |
//|                                                                  |
//| El dia que pidas un payout, el saldo baja. El pico de equity, en  |
//| cambio, se queda donde estaba, asi que el suelo del trailing se   |
//| queda arriba y el margen calculado sale CERO o negativo: el       |
//| factor de tamaño cae a su minimo y la cuenta se queda operando    |
//| en miniatura sin que nada explique por que.                       |
//|                                                                  |
//| Ejemplo con numeros: pico 53.500, suelo bloqueado en 50.000. Pides|
//| el cobro, el saldo vuelve a 50.000. Margen = 50.000 - 50.000 = 0. |
//| Factor = 0,25 para siempre.                                       |
//|                                                                  |
//| Que hacer al detectarlo depende de una regla de la firma que yo   |
//| NO puedo verificar: si un cobro reinicia tambien el suelo del     |
//| drawdown. Por eso no lo decido yo:                                |
//|                                                                  |
//|   InpPagoReiniciaSuelo = false (defecto)                          |
//|     No toca nada y AVISA a gritos en el log. El fallo va del lado |
//|     seguro: operarias pequeño de mas, que es molesto pero no mata.|
//|                                                                  |
//|   InpPagoReiniciaSuelo = true                                     |
//|     Reinicia el pico al saldo nuevo, con lo que el suelo vuelve a |
//|     quedar un 7% por debajo. Activalo SOLO cuando hayas visto en  |
//|     el panel de Upcomers que despues de un cobro el suelo baja.   |
//|     Si te equivocas en este sentido, te crees con mas margen del  |
//|     que tienes y puedes romper el limite sin aviso previo.        |
//+------------------------------------------------------------------+
void RevisarMovimientosDeSaldo()
  {
   if(!InpDetectarPagos)
      return;
   if(((long)TimeCurrent() - (long)g_ultRevision) < (long)InpSegRevisarPagos)
      return;
   g_ultRevision = TimeCurrent();

   if(!HistorySelect(TimeCurrent() - 30 * 86400, TimeCurrent() + 86400))
      return;

   int    n       = HistoryDealsTotal();
   double suma    = 0.0;
   ulong  maxTk   = g_ultDealSaldo;
   int    cuantos = 0;

   for(int i = 0; i < n; i++)
     {
      ulong tk = HistoryDealGetTicket(i);
      if(tk == 0 || tk <= g_ultDealSaldo)
         continue;
      long tipo = HistoryDealGetInteger(tk, DEAL_TYPE);
      if(tipo != DEAL_TYPE_BALANCE && tipo != DEAL_TYPE_CREDIT &&
         tipo != DEAL_TYPE_CORRECTION && tipo != DEAL_TYPE_BONUS)
         continue;
      suma += HistoryDealGetDouble(tk, DEAL_PROFIT);
      if(tk > maxTk)
         maxTk = tk;
      cuantos++;
     }

   if(cuantos == 0)
      return;

   g_ultDealSaldo = maxTk;
   GlobalVariableSet(GV_ULTDEAL, (double)maxTk);
   g_cPagos += cuantos;

   double bal = AccountInfoDouble(ACCOUNT_BALANCE);

   Print("**********************************************************");
   PrintFormat("GUARDIAN: detectados %d movimientos de saldo por %+.2f %s",
               cuantos, suma, AccountInfoString(ACCOUNT_CURRENCY));
   PrintFormat("  saldo ahora %.2f | pico registrado %.2f | "
               "suelo trailing %.2f", bal, g_pico, SueloTrailing());

   if(InpPagoReiniciaSuelo)
     {
      g_pico = MathMax(bal, AccountInfoDouble(ACCOUNT_EQUITY));
      GlobalVariableSet(GV_PICO, g_pico);
      Print("  InpPagoReiniciaSuelo = true -> pico reiniciado a ",
            DoubleToString(g_pico, 2), ", suelo trailing ahora ",
            DoubleToString(SueloTrailing(), 2), ".");
      Print("  COMPRUEBA que el panel de Upcomers dice lo mismo. Si su ",
            "suelo NO baja, esta opcion te da un margen que no tienes.");
      AbrirDiaDeRiesgo();
     }
   else
     {
      g_pagoSinResolver = true;
      Print("  InpPagoReiniciaSuelo = false -> NO se toca el pico.");
      PrintFormat("  Con este pico el margen es %.2f%% y el factor de tamaño "
                  "%.3f. Si eso es mucho menos de lo que dice tu panel, el "
                  "cobro SI reinicia el suelo: activa InpPagoReiniciaSuelo.",
                  MargenPct(), FactorTamano());
     }
   Print("**********************************************************");
  }

//+------------------------------------------------------------------+
//| Modo de llenado admitido por el simbolo. Cerrar con un modo que el |
//| simbolo no acepta devuelve "invalid fill" y la posicion se queda   |
//| abierta: exactamente lo que no puede pasar aqui.                   |
//+------------------------------------------------------------------+
ENUM_ORDER_TYPE_FILLING LlenadoDe(const string sim)
  {
   long modos = SymbolInfoInteger(sim, SYMBOL_FILLING_MODE);
   if((modos & SYMBOL_FILLING_FOK) != 0)
      return(ORDER_FILLING_FOK);
   if((modos & SYMBOL_FILLING_IOC) != 0)
      return(ORDER_FILLING_IOC);
   return(ORDER_FILLING_RETURN);
  }

//+------------------------------------------------------------------+
bool CerrarPosicion(const ulong ticket, const string motivo)
  {
   if(!PositionSelectByTicket(ticket))
      return(false);

   string sim  = PositionGetString(POSITION_SYMBOL);
   double vol  = PositionGetDouble(POSITION_VOLUME);
   long   tipo = PositionGetInteger(POSITION_TYPE);

   MqlTick tk;
   if(!SymbolInfoTick(sim, tk) || tk.bid <= 0.0 || tk.ask <= 0.0)
     {
      g_cCierresFallo++;
      return(false);
     }

   MqlTradeRequest  req;  ZeroMemory(req);
   MqlTradeResult   res;  ZeroMemory(res);
   req.action       = TRADE_ACTION_DEAL;
   req.symbol       = sim;
   req.volume       = vol;
   req.position     = ticket;
   req.deviation    = InpDeslizamiento;
   req.type_filling = LlenadoDe(sim);
   req.comment      = motivo;

   if(tipo == POSITION_TYPE_BUY)
     {
      req.type  = ORDER_TYPE_SELL;
      req.price = tk.bid;
     }
   else
     {
      req.type  = ORDER_TYPE_BUY;
      req.price = tk.ask;
     }

   bool ok = OrderSend(req, res);
   if(!ok || (res.retcode != TRADE_RETCODE_DONE &&
              res.retcode != TRADE_RETCODE_PLACED))
     {
      //--- segundo intento con el otro modo de llenado
      req.type_filling = (req.type_filling == ORDER_FILLING_FOK
                          ? ORDER_FILLING_IOC : ORDER_FILLING_FOK);
      ZeroMemory(res);
      ok = OrderSend(req, res);
     }

   if(!ok || (res.retcode != TRADE_RETCODE_DONE &&
              res.retcode != TRADE_RETCODE_PLACED))
     {
      g_cCierresFallo++;
      PrintFormat("GUARDIAN: FALLO al cerrar %s #%s (%.2f lotes): "
                  "retcode=%d %s", sim, IntegerToString(ticket), vol,
                  res.retcode, res.comment);
      return(false);
     }

   g_cCierresOk++;
   PrintFormat("GUARDIAN: cerrada %s #%s  %.2f lotes  (%s)",
               sim, IntegerToString(ticket), vol, motivo);
   return(true);
  }

//+------------------------------------------------------------------+
//| Cierra TODAS las posiciones y borra TODAS las ordenes pendientes,  |
//| de cualquier magic y cualquier simbolo.                            |
//+------------------------------------------------------------------+
bool CerrarTodo(const string motivo)
  {
   if(InpSoloAvisar)
     {
      PrintFormat("GUARDIAN [ENSAYO]: aqui cerraria todo (%d posiciones, "
                  "%d ordenes). Motivo: %s",
                  PositionsTotal(), OrdersTotal(), motivo);
      return(false);
     }

   //--- primero las pendientes, para que no entre nada nuevo mientras se
   //    cierran las posiciones
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong tk = OrderGetTicket(i);
      if(tk == 0)
         continue;
      MqlTradeRequest  req;  ZeroMemory(req);
      MqlTradeResult   res;  ZeroMemory(res);
      req.action = TRADE_ACTION_REMOVE;
      req.order  = tk;
      if(OrderSend(req, res) && res.retcode == TRADE_RETCODE_DONE)
         PrintFormat("GUARDIAN: borrada orden pendiente #%s",
                     IntegerToString(tk));
      else
         PrintFormat("GUARDIAN: no se pudo borrar la orden #%s (retcode=%d)",
                     IntegerToString(tk), res.retcode);
     }

   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0)
         continue;
      CerrarPosicion(tk, motivo);
     }

   return(PositionsTotal() == 0 && OrdersTotal() == 0);
  }

//+------------------------------------------------------------------+
void Bloquear(const string motivo)
  {
   g_bloqueado     = true;
   g_motivoBloqueo = motivo;
   GlobalVariableSet(GV_BLOQUEO, (double)TimeCurrent());
  }

//+------------------------------------------------------------------+
void Desbloquear(const string motivo)
  {
   g_bloqueado     = false;
   g_motivoBloqueo = "";
   GlobalVariableSet(GV_BLOQUEO, 0.0);
   Print("GUARDIAN: bloqueo levantado (", motivo, ").");
  }

//+------------------------------------------------------------------+
//| Cierra una posicion concreta que pierde demasiado por si sola.     |
//| Cubre el caso de un EA cuyo stop fue rechazado por el servidor y   |
//| se quedo sin proteccion sin avisar a nadie.                        |
//+------------------------------------------------------------------+
void VigilarPosicionesSueltas()
  {
   if(InpMaxPerdidaPosPct <= 0.0)
      return;

   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(eq <= 0.0)
      return;
   double limite = -eq * InpMaxPerdidaPosPct / 100.0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0)
         continue;
      double pl = PositionGetDouble(POSITION_PROFIT) +
                  PositionGetDouble(POSITION_SWAP);
      if(pl > limite)
         continue;

      PrintFormat("GUARDIAN: la posicion %s #%s pierde %.2f, mas del %.2f%% "
                  "de la equity. Su stop no esta haciendo su trabajo.",
                  PositionGetString(POSITION_SYMBOL), IntegerToString(tk),
                  pl, InpMaxPerdidaPosPct);
      if(InpSoloAvisar)
         continue;
      if(CerrarPosicion(tk, "guardian: perdida individual"))
         g_cPosSueltas++;
     }
  }

//+------------------------------------------------------------------+
//| Averia de exposicion. El caso real: un EA con un fallo que abre en |
//| bucle. Cuando eso pasa la equity aun no ha caido y ningun suelo se |
//| ha tocado, pero la cuenta ya esta muerta. Esto SI bloquea, porque  |
//| no es un drawdown: es algo roto que hay que mirar.                 |
//+------------------------------------------------------------------+
bool AveriaDeExposicion(string &motivo)
  {
   int n = PositionsTotal();

   if(InpMaxPosiciones > 0 && n > InpMaxPosiciones)
     {
      motivo = StringFormat("averia: %d posiciones abiertas, el maximo es %d",
                            n, InpMaxPosiciones);
      return(true);
     }

   if(InpMaxVolumenLotes > 0.0)
     {
      double vol = 0.0;
      for(int i = 0; i < n; i++)
        {
         if(PositionGetTicket(i) == 0)
            continue;
         vol += PositionGetDouble(POSITION_VOLUME);
        }
      if(vol > InpMaxVolumenLotes)
        {
         motivo = StringFormat("averia: %.2f lotes abiertos, el maximo es %.2f",
                               vol, InpMaxVolumenLotes);
         return(true);
        }
     }
   return(false);
  }

//+------------------------------------------------------------------+
//| El bucle de vigilancia. Se llama desde OnTick y desde OnTimer,     |
//| porque tiene que correr tambien cuando no llega precio.            |
//+------------------------------------------------------------------+
void Vigilar()
  {
   int hoy = DiaDeRiesgo();
   if(hoy != g_diaRiesgo)
      AbrirDiaDeRiesgo();

   //--- cobros, depositos y correcciones. Va ANTES de leer la equity
   //    porque puede mover el pico y con el todos los suelos.
   RevisarMovimientosDeSaldo();
   VigilarInactividad();

   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(eq <= 0.0)
      return;                         // sin dato fiable no se decide nada

   //--- El pico incluye el beneficio FLOTANTE. Esto no es una eleccion: es
   //    como funciona el trailing de la firma. Una posicion en verde que
   //    luego se gira SUBE el suelo y no vuelve a bajar.
   if(eq > g_pico)
     {
      g_pico = eq;
      GlobalVariableSet(GV_PICO, g_pico);
     }

   //--- publicar factor y margen para los demas EA
   double f      = FactorTamano();
   double margen = MargenPct();
   GlobalVariableSet(GV_FACTOR, f);
   GlobalVariableSet(GV_MARGEN, margen);

   //--- LATIDO en hora de SERVIDOR. Existe porque GlobalVariableTime()
   //    devuelve una marca de tiempo cuya base horaria no esta garantizada:
   //    si es hora local y el servidor esta en otra zona, la "antiguedad"
   //    del dato sale desplazada por la diferencia entre las dos. En esta
   //    instalacion son 8 horas, mas que suficiente para que el factor se
   //    declare caducado SIEMPRE y el escalado no se aplique nunca. Sin
   //    ningun sintoma salvo una linea de aviso.
   //    Publicando TimeCurrent() como VALOR, las dos partes comparan en la
   //    misma base y la ambiguedad desaparece.
   GlobalVariableSet(GV_LATIDO, (double)TimeCurrent());

   if(margen < g_margenMinimo)
      g_margenMinimo = margen;
   if(f < g_factorMinVisto)
      g_factorMinVisto = f;

   //--- avisar cuando el factor cambia de tramo, para tener rastro de por
   //    que las posiciones empezaron a ser mas pequeñas
   if(MathAbs(f - g_ultimoFactor) >= 0.10)
     {
      PrintFormat("GUARDIAN: factor de tamaño %.3f -> %.3f "
                  "(margen %.2f%%, equity %.2f, suelo %.2f)",
                  g_ultimoFactor, f, margen, eq, SueloTrailing());
      g_ultimoFactor = f;
     }

   if(!g_avisoAlarma && margen < InpMargenAlarmaPct)
     {
      g_avisoAlarma = true;
      PrintFormat("GUARDIAN AVISO: solo queda %.2f%% de margen hasta el suelo "
                  "(equity %.2f, suelo efectivo %.2f, factor %.3f).",
                  margen, eq, SueloEfectivo(), f);
     }

   //--- bloqueo por averia: la unica tarea es que no quede nada abierto
   if(g_bloqueado)
     {
      if(PositionsTotal() > 0 || OrdersTotal() > 0)
         CerrarTodo("guardian bloqueado: " + g_motivoBloqueo);
      return;
     }

   //--- averia de exposicion: cierra Y bloquea
   string motivoAv = "";
   if(AveriaDeExposicion(motivoAv))
     {
      Print("**********************************************************");
      Print("GUARDIAN: ", motivoAv);
      PrintFormat("  equity %.2f | posiciones %d | ordenes %d",
                  eq, PositionsTotal(), OrdersTotal());
      Print("  Se cierra todo y se BLOQUEA. Esto no es un drawdown: algo");
      Print("  esta roto. Mira el historial antes de reactivar.");
      Print("**********************************************************");
      g_cAverias++;
      CerrarTodo(motivoAv);
      if(!InpSoloAvisar)
         Bloquear(motivoAv);
      return;
     }

   //--- cierre de emergencia por equity. Desactivado por defecto: medido,
   //    empeora la probabilidad de quema del 0,3% al 1,0% sin ganar EV,
   //    porque cristaliza la perdida y paga el spread justo cuando la
   //    posicion ya reducida por el factor habria aguantado. NO bloquea.
   if((InpColchonTrailingPct > 0.0 || InpColchonDiarioPct > 0.0) &&
      eq <= NivelEmergencia() && (PositionsTotal() > 0 || OrdersTotal() > 0))
     {
      PrintFormat("GUARDIAN: cierre de emergencia. equity %.2f <= nivel %.2f "
                  "(suelo trailing %.2f, diario %.2f). NO se bloquea: el "
                  "factor de tamaño seguira gobernando.",
                  eq, NivelEmergencia(), SueloTrailing(), SueloDiario());
      g_cEmergencia++;
      CerrarTodo("guardian: cierre de emergencia");
      return;
     }

   VigilarPosicionesSueltas();

   //--- registro periodico, para tener rastro de que el Guardian vive
   if(InpSegundosLog > 0 &&
      (TimeCurrent() - g_ultimoLog) >= (datetime)InpSegundosLog)
     {
      g_ultimoLog = TimeCurrent();
      MqlDateTime ny;
      TimeToStruct(AhoraNY(), ny);
      PrintFormat("guardian %02d:%02d NY | equity %.2f | pico %.2f | "
                  "trailing %.2f | diario %.2f | margen %.2f%% | "
                  "factor %.3f | pos %d",
                  ny.hour, ny.min, eq, g_pico, SueloTrailing(), SueloDiario(),
                  margen, f, PositionsTotal());
     }
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   Vigilar();
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   Vigilar();
  }
//+------------------------------------------------------------------+
