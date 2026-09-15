//+------------------------------------------------------------------+
//|  EA_Trend_Multi.mq5                                              |
//|  Estrategia #2: momentum de series temporales multi-activo         |
//|                                                                  |
//|  QUE HACE                                                        |
//|    Una vez al mes, para cada mercado de la cesta:                 |
//|      · mira el retorno de los ULTIMOS 12 MESES cerrados;          |
//|      · se pone largo si fue positivo y corto si fue negativo;     |
//|      · dimensiona la posicion para que ese mercado aporte una     |
//|        volatilidad objetivo fija, usando su volatilidad realizada |
//|        de los ultimos 252 dias.                                   |
//|    Y no hace nada mas hasta el mes siguiente.                     |
//|                                                                  |
//|  POR QUE ESTA ESTRATEGIA EXISTE EN ESTE SISTEMA                  |
//|    No es un añadido para ganar mas. Es lo que hace la cuenta      |
//|    COBRABLE. La regla de consistencia de Upcomers exige que el    |
//|    mejor dia no pase del 20% del beneficio total, y la #1         |
//|    pre-FOMC opera 8 veces al año: un solo dia es siempre mas del  |
//|    20%. Medido sobre 15.000 caminos de 504 sesiones:              |
//|                                                                  |
//|      cartera            dias activos  P(cobro)  EV anual          |
//|      solo #1 pre-FOMC              8     19,4%     666 $          |
//|      solo #2 trend               252     60,5%   1.077 $          |
//|      las dos                     252     63,9%   1.364 $          |
//|                                                                  |
//|    La #1 sola, sin la regla del 20%, cobraria el 82,3% de las     |
//|    veces. Con la regla, el 19,4%. La regla se come 63 puntos.     |
//|    Esta estrategia es lo que los recupera.                        |
//|                                                                  |
//|  LA CESTA, Y POR QUE ES ESTA                                     |
//|    La especificacion original usaba 12 mercados, y cuatro no      |
//|    existen como CFD: EFA, EEM, TLT e IEF. Se midieron tres        |
//|    universos con la MISMA especificacion:                         |
//|                                                                  |
//|      universo                     2010-2026        2018-2026      |
//|      A original (12)          Sh 0,53 t 2,15   Sh 0,45 t 1,33     |
//|      B solo quitar (8)        Sh 0,56 t 2,29   Sh 0,51 t 1,51     |
//|      C quitar y sustituir(12) Sh 0,42 t 1,71   Sh 0,30 t 0,87     |
//|                                                                  |
//|    Se eligio B: quitar los cuatro y NO poner nada en su lugar.    |
//|    Dos razones medidas, no opinadas:                              |
//|      1. Los bonos aportaban Sharpe 0,20 con t=0,80 despues de     |
//|         2010. Quitarlos no cuesta nada porque no daban nada.      |
//|      2. Rellenar los huecos con DAX, FTSE, Nikkei y ASX EMPEORA   |
//|         el resultado reciente (0,56 -> 0,42). Era la decision     |
//|         que parecia obvia y la medicion la descarta.              |
//|    B es ademas el unico universo que no añade ningun grado de     |
//|    libertad: la eliminacion la impuso el broker, no yo.           |
//|                                                                  |
//|  EL PESO DEL 30%, Y POR QUE NO ES LA VOLATILIDAD INVERSA          |
//|    El reparto por volatilidad inversa daria 18,9% a esta pata.    |
//|    Pero el objetivo no es maximizar el Sharpe, es cobrar, y cada  |
//|    punto de peso que pasa aqui compra dias activos:               |
//|                                                                  |
//|      peso #2   P(cobro)   EV anual   lo que cuesta la regla 20%   |
//|       10,0%      36,3%     1.097 $        -50,5 puntos            |
//|       18,9%      54,5%     1.345 $        -35,5 puntos            |
//|       25,0%      61,1%     1.381 $        -28,3 puntos            |
//|       30,0%      63,9%     1.364 $        -24,0 puntos            |
//|       40,0%      64,3%     1.284 $        -21,1 puntos            |
//|                                                                  |
//|    El maximo de EV esta en 25% pero la curva es plana hasta 30%,   |
//|    y en 30% la probabilidad de cobrar es 2,8 puntos mayor. Se     |
//|    elige el centro de la meseta, no su pico.                      |
//|                                                                  |
//|  DE DONDE SALE InpVolPorMercado = 7,23                            |
//|    La cesta de 8 mercados con vol objetivo del 10% por mercado    |
//|    produce una serie con 5,41% de volatilidad anual. La pata debe |
//|    aportar 3,91% (el 30% del riesgo de una cartera al 4,5%), asi  |
//|    que 10% x 3,91/5,41 = 7,23%.                                  |
//|                                                                  |
//|  LO QUE ESTE EA NO HACE                                          |
//|    · No busca periodos de mirada atras ni tenencias alternativas. |
//|      Una sola especificacion, la canonica. Buscar parametros es   |
//|      lo que hundio todo lo demas de este proyecto.                |
//|    · No opera un mercado sin datos suficientes. FALLA EN CERRADO  |
//|      y lo cuenta.                                                 |
//|    · No opera nada si quedan menos de InpMinMercados disponibles. |
//+------------------------------------------------------------------+
#property copyright "Proyecto de auditoria cuantitativa"
#property version   "1.00"
#property strict

#define MAX_MERCADOS 32

//--- Cierres mensuales de REFERENCIA para empalmar la señal.
//    Generado por trend/generar_referencia.py.
//    33 meses x 8 mercados. Solo se usan COCIENTES, asi que el
//    nivel de precio de la fuente es irrelevante.
#define REF_MESES     33
#define REF_MERCADOS  8

int REF_ANIOMES[REF_MESES] =
  {
   202312, 202401, 202402, 202403, 202404, 202405, 202406, 202407, 202408, 202409, 202410, 202411,
   202412, 202501, 202502, 202503, 202504, 202505, 202506, 202507, 202508, 202509, 202510, 202511,
   202512, 202601, 202602, 202603, 202604, 202605, 202606, 202607, 202608
  };

string REF_SIMBOLO[REF_MERCADOS] =
  {
   "SPCUSD.c", "NACUSD.c", "XAUUSD", "XAGUSD", "EURUSD", "USDJPY", "GBPUSD", "AUDUSD"
  };

//--- indice = mercado * REF_MESES + mes
double REF_CIERRE[REF_MERCADOS * REF_MESES] =
  {
   // SPCUSD.c
   461.3913, 468.7397, 493.2017, 509.3303, 488.7944, 513.5173, 531.6344, 538.0720,
   550.6443, 562.2104, 557.1935, 590.4209, 576.2152, 591.6904, 584.1789, 551.6290,
   546.8462, 581.2128, 611.0790, 625.1531, 637.9810, 660.7061, 676.4557, 677.7747,
   678.3152, 688.3121, 682.3637, 648.6689, 716.8133, 754.5361, 746.7700, 747.0300,
   769.3500,
   // NACUSD.c
   404.0923, 411.4436, 433.1816, 438.7046, 419.5166, 445.3245, 474.1376, 466.1810,
   471.3270, 483.6833, 479.5013, 505.1586, 507.4521, 518.4304, 504.4147, 466.1489,
   472.6602, 516.0423, 548.9959, 562.3019, 567.6661, 598.1850, 626.7806, 616.9963,
   612.8629, 620.4050, 605.8594, 576.5464, 667.0070, 737.4995, 736.4000, 687.9900,
   716.4300,
   // XAUUSD
   191.1700, 188.4500, 189.3100, 205.7200, 211.8700, 215.3000, 215.0100, 226.5500,
   231.2900, 243.0600, 253.5100, 245.5900, 242.1300, 258.5600, 263.2700, 288.1400,
   303.7700, 303.6000, 304.8300, 302.9600, 318.0700, 355.4700, 368.1200, 387.8800,
   396.3100, 444.9500, 483.7500, 430.2900, 423.6600, 417.1200, 368.3800, 371.5400,
   408.8900,
   // XAGUSD
   21.7800, 20.9100, 20.7300, 22.7500, 24.0500, 27.7600, 26.5700, 26.3900,
   26.3500, 28.4100, 29.8100, 27.9200, 26.3300, 28.5100, 28.3100, 30.9900,
   29.6000, 30.0000, 32.8100, 33.3200, 36.1900, 42.3700, 44.0100, 51.2100,
   64.4200, 75.4400, 84.9900, 68.1400, 66.6600, 68.3300, 53.4700, 52.3600,
   60.0200,
   // EURUSD
   1.1068, 1.0843, 1.0839, 1.0794, 1.0716, 1.0835, 1.0708, 1.0816,
   1.1080, 1.1170, 1.0859, 1.0563, 1.0406, 1.0397, 1.0395, 1.0824,
   1.1389, 1.1378, 1.1727, 1.1429, 1.1682, 1.1731, 1.1572, 1.1600,
   1.1747, 1.1966, 1.1803, 1.1460, 1.1685, 1.1653, 1.1422, 1.1524,
   1.1590,
   // USDJPY
   141.4300, 147.3690, 150.6560, 151.4400, 156.3140, 156.9530, 160.6870, 152.6700,
   144.8900, 142.7830, 153.2040, 151.1740, 156.9950, 154.0970, 150.0120, 149.6170,
   142.2990, 143.7790, 144.5170, 149.2260, 146.7900, 148.5950, 153.9000, 156.2840,
   156.4130, 153.1620, 155.8590, 159.8410, 160.1840, 159.2700, 161.9230, 160.1830,
   159.9200,
   // GBPUSD
   1.2734, 1.2696, 1.2663, 1.2626, 1.2560, 1.2730, 1.2646, 1.2837,
   1.3166, 1.3383, 1.2960, 1.2697, 1.2549, 1.2424, 1.2599, 1.2938,
   1.3411, 1.3499, 1.3720, 1.3258, 1.3511, 1.3437, 1.3159, 1.3241,
   1.3467, 1.3806, 1.3491, 1.3173, 1.3489, 1.3444, 1.3254, 1.3461,
   1.3540,
   // AUDUSD
   0.6826, 0.6595, 0.6495, 0.6517, 0.6562, 0.6630, 0.6651, 0.6542,
   0.6796, 0.6919, 0.6573, 0.6507, 0.6220, 0.6215, 0.6232, 0.6283,
   0.6387, 0.6446, 0.6533, 0.6447, 0.6532, 0.6582, 0.6559, 0.6536,
   0.6698, 0.7047, 0.7102, 0.6846, 0.7131, 0.7164, 0.6882, 0.7025,
   0.7164
  };

//--- entradas -------------------------------------------------------
input group           "=== La cesta ==="
//--- La lista se deduce del unico nombre que conocemos con certeza:
//    NACUSD.c, que es el NASDAQ de este broker. Pertenece a la convencion
//    NACUSD / SPXUSD / GRXEUR / UKXGBP, y el sufijo ".c" es de la casa.
//    Si algun nombre no existe, el informe de arranque lo dira y basta con
//    corregir esta cadena en la pestaña Inputs: no hay que recompilar.
input string          InpSimbolos        = "SPCUSD.c,NACUSD.c,XAUUSD,XAGUSD,EURUSD,USDJPY,GBPUSD,AUDUSD"; // Lista separada por comas
input int             InpMinMercados     = 6;      // Minimo de mercados con datos para operar
input bool            InpEmpalmarSenal   = true;   // Empalmar con cierres de referencia si falta historial
input int             InpMercadosRef     = 8;      // Divisor de referencia (mantiene la vol si falta alguno)

input group           "=== Señal y dimensionado ==="
input int             InpMesesMirada     = 12;     // Meses de retorno para la señal
input double          InpVolPorMercado   = 7.23;   // Vol objetivo por mercado, % anual
input int             InpDiasVol         = 150;    // Dias para estimar la volatilidad
input double          InpTopeExposicion  = 5.0;    // Tope de exposicion por mercado (multiplos)

input group           "=== Rebalanceo ==="
input int             InpHoraRebalanceoNY= 10;     // Hora de rebalanceo (NY)
input int             InpMinRebalanceoNY = 0;      // Minuto de rebalanceo (NY)
input double          InpUmbralCambio    = 20.0;   // Solo ajustar si el cambio supera este % del objetivo
input int             InpVentanaRebalMin = 240;    // Ventana para completar el rebalanceo (min)
input int             InpDiasEsperaVentana= 3;     // Dias del mes en que se ESPERA a la ventana

input group           "=== Ejecucion ==="
input double          InpSpreadMaxBp     = 30.0;   // Spread maximo admitido, en bp
input int             InpDeslizamiento   = 200;    // Deslizamiento permitido (puntos)
input bool            InpUsarLoteMinimo  = false;  // Si el objetivo no llega al lote minimo, usar el minimo

input group           "=== Coordinacion con el Guardian ==="
input bool            InpRespetarGuardian= true;   // No abrir si EA_Guardian senala averia
input bool            InpUsarFactorGuard = true;   // Multiplicar la exposicion por el factor del Guardian
input bool            InpExigirGuardian  = false;  // No operar si el Guardian no esta publicando
input int             InpFrescuraGuardMin= 10;     // El dato del Guardian caduca a los N minutos

input group           "=== Diagnostico ==="
input bool            InpSoloDiagnostico = true;   // NO OPERA: solo escribe el informe de la cesta
input bool            InpDiagnostico     = true;   // Informe completo de la cesta al arrancar
input bool            InpLogDetallado    = true;

input group           "=== Identificacion ==="
input long            InpMagic           = 20260202;

//--- variables globales del terminal que publica EA_Guardian ---------
#define GV_BLOQUEO   "GUARDIAN_BLOQUEO"
#define GV_FACTOR    "GUARDIAN_FACTOR"
#define GV_LATIDO    "GUARDIAN_LATIDO"

//--- estado ---------------------------------------------------------
string   g_sim[MAX_MERCADOS];
bool     g_ok[MAX_MERCADOS];        // el simbolo existe en el broker
int      g_n              = 0;
int      g_ultimoMesRebal = 0;      // AAAAMM del ultimo rebalanceo
bool     g_avisoOffset      = false;
bool     g_avisoSinGuardian = false;
bool     g_diagPendiente    = false;
bool     g_avisoEspera      = false;
bool     g_silenciarEmpalme = false;   // evita repetir el log 3 veces
int      g_intentosDiag     = 0;
datetime g_arranque         = 0;

int      g_cRebalanceos   = 0;
int      g_cOrdenes       = 0;
int      g_cFallos        = 0;
int      g_cSinDatos      = 0;      // veces que un mercado se salto por datos
int      g_cSinLote       = 0;      // veces que el objetivo no llego al minimo
int      g_cRechazoSpread = 0;
int      g_cMesesSaltados = 0;      // meses sin operar por falta de mercados
int      g_cBloqueoGuard  = 0;

//--- declaraciones adelantadas --------------------------------------
bool     EsVeranoEEUU(const datetime utc);
datetime AhoraNY();
double   FactorGuardian();
double   SpreadBp(const string sim);
bool     SenalYVol(const string sim, double &retorno12m, double &vol,
                   int &nMN1, int &nD1);
double   ExposicionObjetivo(const string sim, const int nActivos,
                            double &senal, double &vol);
double   LotesDe(const string sim, const double exposicion);
double   NocionalPorLote(const string sim);
double   PosicionActual(const string sim);
bool     CerrarSimbolo(const string sim, const string motivo);
bool     AbrirSimbolo(const string sim, const double lotes, const bool largo);
bool     Rebalancear();
void     Diagnostico();
void     SondarHistorial(const string sim, int &barrasD1, int &barrasMN1,
                         datetime &primeraD1, datetime &primeraMN1,
                         bool &sincronizado);

//+------------------------------------------------------------------+
int OnInit()
  {
   //--- parsear la cesta
   string partes[];
   int np = StringSplit(InpSimbolos, StringGetCharacter(",", 0), partes);
   if(np <= 0)
     {
      Print("ERROR: InpSimbolos esta vacio.");
      return(INIT_FAILED);
     }

   g_n = 0;
   for(int i = 0; i < np && g_n < MAX_MERCADOS; i++)
     {
      string s = partes[i];
      StringTrimLeft(s);
      StringTrimRight(s);
      if(s == "")
         continue;
      g_sim[g_n] = s;
      g_ok[g_n]  = SymbolSelect(s, true);
      g_n++;
     }

   if(g_n == 0)
     {
      Print("ERROR: no se reconocio ningun simbolo en InpSimbolos.");
      return(INIT_FAILED);
     }
   if(InpMesesMirada < 1 || InpVolPorMercado <= 0.0 || InpDiasVol < 30)
     {
      Print("ERROR: parametros de señal o dimensionado invalidos.");
      return(INIT_FAILED);
     }

   Print("=== EA_Trend_Multi activo ",
         (InpSoloDiagnostico ? "(SOLO DIAGNOSTICO: no operara)" : ""), " ===");
   PrintFormat("  cesta declarada: %d simbolos", g_n);

   int existen = 0;
   for(int i = 0; i < g_n; i++)
     {
      if(g_ok[i])
         existen++;
      else
         Print("  NO EXISTE en este broker: ", g_sim[i],
               "  <- hay que darle el nombre correcto");
     }
   PrintFormat("  simbolos que EXISTEN: %d de %d", existen, g_n);

   if(existen < InpMinMercados)
     {
      PrintFormat("AVISO: solo %d simbolos existen y el minimo es %d. "
                  "El EA arranca pero NO operara hasta que se corrijan "
                  "los nombres.", existen, InpMinMercados);
     }

   //--- CALENTAMIENTO. MT5 descarga el historial de forma ASINCRONA: la
   //    primera llamada a CopyClose sobre un simbolo que no esta en cache
   //    devuelve 0 barras y dispara la descarga en segundo plano. Si el
   //    diagnostico corriera aqui mismo, diria que ningun mercado tiene
   //    datos y seria mentira. Asi que aqui solo se pide, y el informe se
   //    hace desde el timer cuando los datos hayan llegado.
   for(int i = 0; i < g_n; i++)
     {
      if(!g_ok[i])
         continue;
      int bD1, bMN1;
      datetime pD1, pMN1;
      bool sinc;
      SondarHistorial(g_sim[i], bD1, bMN1, pD1, pMN1, sinc);
     }
   g_arranque      = TimeCurrent();
   g_diagPendiente = InpDiagnostico;
   if(InpDiagnostico)
      Print("  (el informe de la cesta sale en unos segundos, cuando el ",
            "terminal termine de descargar el historial)");

   //--- El rebalanceo es mensual, asi que no hace falta mirar cada tick.
   //    Un timer de 30 s basta y sobra, y garantiza que se revise aunque
   //    el simbolo del grafico no cotice.
   EventSetTimer(30);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   Print("=== EA_Trend_Multi detenido (motivo ", reason, ") ===");
   PrintFormat("  rebalanceos realizados        : %d", g_cRebalanceos);
   PrintFormat("  ordenes enviadas              : %d", g_cOrdenes);
   PrintFormat("  ordenes fallidas              : %d", g_cFallos);
   PrintFormat("  mercados saltados por datos   : %d", g_cSinDatos);
   PrintFormat("  mercados saltados por lote    : %d", g_cSinLote);
   PrintFormat("  rechazos por spread           : %d", g_cRechazoSpread);
   PrintFormat("  meses sin operar (pocos mdos) : %d", g_cMesesSaltados);
   PrintFormat("  rebalanceos vetados por Guard : %d", g_cBloqueoGuard);
   if(InpSoloDiagnostico)
      Print("  (estaba en modo SOLO DIAGNOSTICO: no se envio ninguna orden)");
   if(g_cSinLote > 0)
      Print("  AVISO: algun mercado no alcanza el lote minimo con esta ",
            "equity. La cartera esta operando incompleta.");
  }

//+------------------------------------------------------------------+
//| Informe de arranque. Esto es lo que nos va a decir de verdad que  |
//| se puede operar en este broker y que no: nombres de simbolo,      |
//| historial disponible, tamaño de contrato y lote minimo.           |
//+------------------------------------------------------------------+
void Diagnostico()
  {
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   int nActivos  = 0;
   g_silenciarEmpalme = true;         // el conteo no debe ensuciar el log
   for(int i = 0; i < g_n; i++)
     {
      double r12, vol;
      int nMN1, nD1;
      if(g_ok[i] && SenalYVol(g_sim[i], r12, vol, nMN1, nD1))
         nActivos++;
     }
   g_silenciarEmpalme = false;
   if(nActivos < 1)
      nActivos = 1;

   Print("--- DIAGNOSTICO DE LA CESTA ---");
   PrintFormat("  equity %.2f %s  ·  mercados con datos: %d  ·  divisor %d",
               equity, AccountInfoString(ACCOUNT_CURRENCY), nActivos,
               MathMax(nActivos, InpMercadosRef));
   Print("  simbolo        MN1    D1  desde D1     desde MN1   sinc   vol"
         "   señal  objetivo    lotes  lote min  nocional/lote  real   error");

   for(int i = 0; i < g_n; i++)
     {
      if(!g_ok[i])
        {
         PrintFormat("  %-11s %s", g_sim[i], "                       "
                     "                        NO EXISTE");
         continue;
        }

      int bD1, bMN1;
      datetime pD1, pMN1;
      bool sinc;
      SondarHistorial(g_sim[i], bD1, bMN1, pD1, pMN1, sinc);

      double r12 = 0.0, vol = 0.0;
      int    nMN1 = 0, nD1 = 0;
      bool   hay = SenalYVol(g_sim[i], r12, vol, nMN1, nD1);
      double minL = SymbolInfoDouble(g_sim[i], SYMBOL_VOLUME_MIN);

      string fD1  = (pD1  > 0 ? TimeToString(pD1,  TIME_DATE) : "   -      ");
      string fMN1 = (pMN1 > 0 ? TimeToString(pMN1, TIME_DATE) : "   -      ");

      if(!hay)
        {
         PrintFormat("  %-13s %5d %5d  %s  %s   %s   FALTAN DATOS "
                     "(necesita %d MN1 y %d D1)",
                     g_sim[i], bMN1, bD1, fD1, fMN1,
                     (sinc ? "si " : "NO "), InpMesesMirada + 2,
                     InpDiasVol + 2);
         continue;
        }

      double senal, v2;
      g_silenciarEmpalme = true;      // ya se registro arriba
      double expo = ExposicionObjetivo(g_sim[i], nActivos, senal, v2);
      g_silenciarEmpalme = false;
      double lot  = LotesDe(g_sim[i], expo);
      string est = "OK";
      if(MathAbs(lot) < minL)
         est = (InpUsarLoteMinimo ? "USARA EL MINIMO (sobreexpone)"
                                  : "NO LLEGA -> se omite");

      //--- nocional que mueve UN lote, y exposicion que de verdad queda
      //    tras el redondeo. Es el numero que faltaba: sin el estaba
      //    ESTIMANDO el error de granularidad en vez de medirlo.
      double nocLote = NocionalPorLote(g_sim[i]);
      double real    = (nocLote > 0.0 && equity > 0.0
                        ? lot * nocLote / equity : 0.0);
      double err     = (expo != 0.0 ? real / expo - 1.0 : 0.0);

      PrintFormat("  %-13s %5d %5d  %s  %s   %s  %5.1f%%  %+5.0f  %+7.2f%%"
                  " %+8.4f %8.2f %13.0f %+6.2f%% %+6.0f%%  %s",
                  g_sim[i], bMN1, bD1, fD1, fMN1, (sinc ? "si " : "NO "),
                  vol * 100.0, senal, expo * 100.0, lot, minL, nocLote,
                  real * 100.0, err * 100.0, est);
     }
   Print("  ('señal' es +1 largo / -1 corto; 'exposic.' es % de la equity)");
   Print("-------------------------------");
  }

//+------------------------------------------------------------------+
//| SONDA DE HISTORIAL.                                               |
//|                                                                  |
//| Esto existe porque mi primer diagnostico no sabia distinguir dos  |
//| cosas muy distintas:                                              |
//|   a) el broker solo tiene 9 meses de historial   -> no hay arreglo |
//|      posible desde MT5, hay que traer los datos de fuera;         |
//|   b) MT5 aun no ha descargado el historial       -> se arregla    |
//|      pidiendolo bien y esperando.                                 |
//|                                                                  |
//| CopyClose(sim, tf, 0, N, arr) pide por POSICION y NO fuerza una    |
//| descarga profunda: si el terminal no tiene esas barras en cache,   |
//| devuelve 0 y se queda tan ancho. Pedir por RANGO DE FECHAS si la   |
//| dispara. Ese era el error.                                        |
//|                                                                  |
//| Bars() y SeriesInfoInteger() dicen la verdad: cuantas barras hay   |
//| de verdad y desde que fecha.                                      |
//+------------------------------------------------------------------+
void SondarHistorial(const string sim, int &barrasD1, int &barrasMN1,
                     datetime &primeraD1, datetime &primeraMN1,
                     bool &sincronizado)
  {
   //--- peticion por RANGO, que es la que fuerza la descarga
   datetime hasta = TimeCurrent();
   datetime desde = hasta - (datetime)(600 * 86400);   // ~20 meses
   double tmp[];
   CopyClose(sim, PERIOD_D1,  desde, hasta, tmp);
   CopyClose(sim, PERIOD_MN1, desde, hasta, tmp);

   barrasD1   = Bars(sim, PERIOD_D1);
   barrasMN1  = Bars(sim, PERIOD_MN1);
   primeraD1  = (datetime)SeriesInfoInteger(sim, PERIOD_D1,  SERIES_FIRSTDATE);
   primeraMN1 = (datetime)SeriesInfoInteger(sim, PERIOD_MN1, SERIES_FIRSTDATE);
   sincronizado =
      (SeriesInfoInteger(sim, PERIOD_D1, SERIES_SYNCHRONIZED) != 0);
  }

//+------------------------------------------------------------------+
//| Horario de verano de EE.UU. Igual que en los otros dos EA: el     |
//| servidor esta en GMT+2 fijo y Nueva York no, asi que el desfase   |
//| cambia de 6 a 7 horas y un offset fijo entraria mal media         |
//| temporada sin dar ninguna señal.                                 |
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
   int segundoDomMar = 1 + ((7 - m.day_of_week) % 7) + 7;
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
datetime AhoraNY()
  {
   datetime servidor = TimeCurrent();
   datetime g        = TimeGMT();
   long     dif      = (long)servidor - (long)g;
   datetime utc;

   //--- En el Probador TimeGMT() devuelve lo mismo que TimeCurrent(). Un
   //    desfase de CERO no significa "servidor en UTC": significa que la
   //    funcion no esta informada. Ese fue el bug 4 del EA del FOMC.
   bool fiable = (g > 0 && dif != 0 && MathAbs(dif) <= 14 * 3600);
   if(fiable)
      utc = g;
   else
     {
      utc = servidor - (datetime)(2 * 3600);   // servidor en GMT+2
      if(!g_avisoOffset)
        {
         Print("AVISO: TimeGMT() no informado. Se asume servidor en GMT+2.");
         g_avisoOffset = true;
        }
     }
   return(utc - (datetime)((EsVeranoEEUU(utc) ? 4 : 5) * 3600));
  }

//+------------------------------------------------------------------+
//| Factor de tamaño del Guardian, con comprobacion de frescura. La    |
//| edad se calcula en LONG con signo: una marca de tiempo en el       |
//| futuro se declara caducada, que es la lectura segura.              |
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
      return(1.0);
   return(f);
  }

//+------------------------------------------------------------------+
//| Spread en puntos basicos DEL PRECIO. Medirlo en _Point fue el bug |
//| numero 1 del primer EA: con Digits=2 convertia 0,80 en 80.        |
//| Devuelve -1 si no hay precio valido -> se falla en cerrado.       |
//+------------------------------------------------------------------+
double SpreadBp(const string sim)
  {
   MqlTick tk;
   if(!SymbolInfoTick(sim, tk))
      return(-1.0);
   if(tk.bid <= 0.0 || tk.ask <= 0.0 || tk.ask < tk.bid)
      return(-1.0);
   return((tk.ask - tk.bid) / tk.bid * 10000.0);
  }

//+------------------------------------------------------------------+
//| EMPALME DE LA SEÑAL.                                             |
//|                                                                  |
//| Medido en el terminal: este broker no tiene NADA antes del 12 de  |
//| enero de 2026. Ocho meses. La señal necesita trece. Y no es un    |
//| problema de descarga: SERIES_SYNCHRONIZED devuelve verdadero y    |
//| SERIES_FIRSTDATE dice 2026.01.12 en los ocho simbolos, incluido   |
//| EURUSD, que tiene decadas de historia en cualquier otro sitio.    |
//|                                                                  |
//| Acortar la señal a ocho meses seria ajustar la estrategia a una   |
//| limitacion de datos. En su lugar se EMPALMAN dos series:          |
//|                                                                  |
//|    factor = cierre_broker[solape] / cierre_ref[solape]            |
//|    P[t] = cierre_broker[t]           si el broker lo tiene        |
//|    P[t] = cierre_ref[t] * factor     si no                        |
//|                                                                  |
//| donde 'solape' es el mes mas antiguo que el broker si tiene. Al   |
//| reescalar por ese factor, el NIVEL de precio de la referencia deja |
//| de importar: SPY cotiza a ~1/10 del S&P y da igual, porque solo    |
//| se usan cocientes.                                               |
//|                                                                  |
//| Y se apaga solo: cuando el broker acumule 14 barras MN1 (marzo de |
//| 2027) el empalme deja de usarse sin tocar nada.                   |
//|                                                                  |
//| LO QUE SE CONCEDE: la referencia son ETF ajustados por dividendo  |
//| y los CFD sobre indice no lo estan, asi que la pata antigua del   |
//| cociente lleva el dividendo dentro (~1,3% anual en el S&P). Solo  |
//| cambiaria el signo si el retorno de 12 meses estuviera a menos de |
//| eso de cero.                                                     |
//+------------------------------------------------------------------+
int AniomesMenos(const int aniomes, const int k)
  {
   int a = aniomes / 100;
   int m = aniomes % 100;
   int total = a * 12 + (m - 1) - k;
   //--- AAAAMM, no AAAAMM00. La primera version multiplicaba por 10000 y
   //    por 100, con lo que ningun mes coincidia con REF_ANIOMES y los ocho
   //    simbolos se omitian sin que nada lo explicara. Lo cazo el control
   //    en Python, no el compilador.
   return((total / 12) * 100 + (total % 12 + 1));
  }

//+------------------------------------------------------------------+
int IndiceRef(const string sim)
  {
   for(int i = 0; i < REF_MERCADOS; i++)
      if(REF_SIMBOLO[i] == sim)
         return(i);
   return(-1);
  }

//+------------------------------------------------------------------+
//| Cierre de referencia. Devuelve -1 si ese mes no esta en la tabla. |
//+------------------------------------------------------------------+
double CierreRef(const int idxMercado, const int aniomes)
  {
   if(idxMercado < 0)
      return(-1.0);
   for(int i = 0; i < REF_MESES; i++)
      if(REF_ANIOMES[i] == aniomes)
         return(REF_CIERRE[idxMercado * REF_MESES + i]);
   return(-1.0);
  }

//+------------------------------------------------------------------+
//| Señal y volatilidad de un mercado.                               |
//|                                                                  |
//| Señal: retorno del cierre del mes -1 contra el del mes -13. El    |
//|        indice 0 de MN1 es el mes EN CURSO y esta incompleto, asi   |
//|        que usar el 1 es lo que evita mirar el futuro.             |
//| Vol  : desviacion de los retornos diarios de las ultimas          |
//|        InpDiasVol barras D1 CERRADAS, anualizada.                 |
//|                                                                  |
//| Devuelve false si no se puede calcular ni con empalme.            |
//+------------------------------------------------------------------+
bool SenalYVol(const string sim, double &retorno12m, double &vol,
               int &nMN1, int &nD1)
  {
   retorno12m = 0.0;
   vol = 0.0;

   //--- barras mensuales disponibles (se piden de sobra a proposito)
   double cm[];
   datetime tm[];
   ArraySetAsSeries(cm, true);
   ArraySetAsSeries(tm, true);
   nMN1 = CopyClose(sim, PERIOD_MN1, 0, InpMesesMirada + 8, cm);
   int nt = CopyTime(sim, PERIOD_MN1, 0, InpMesesMirada + 8, tm);
   if(nMN1 < 2 || nt < 2 || cm[1] <= 0.0)
      return(false);

   int idxNecesario = InpMesesMirada + 1;      // 13 con mirada de 12

   //--- año-mes del mes en curso (indice 0)
   MqlDateTime t0;
   TimeToStruct(tm[0], t0);
   int aniomes0 = t0.year * 100 + t0.mon;

   double p13 = -1.0;

   if(nMN1 > idxNecesario && cm[idxNecesario] > 0.0)
     {
      //--- el broker llega solo: no hace falta empalmar
      p13 = cm[idxNecesario];
     }
   else if(InpEmpalmarSenal)
     {
      int k = IndiceRef(sim);
      if(k < 0)
        {
         if(InpLogDetallado)
            Print("  ", sim, ": falta historial y no esta en la tabla de "
                  "referencia -> se omite");
         return(false);
        }

      //--- mes de solape = el mas antiguo que el broker tiene
      int idxSolape = nMN1 - 1;
      if(idxSolape < 1 || cm[idxSolape] <= 0.0)
         return(false);
      int aniomesSolape = AniomesMenos(aniomes0, idxSolape);
      double refSolape  = CierreRef(k, aniomesSolape);
      if(refSolape <= 0.0)
        {
         PrintFormat("  %s: la tabla de referencia no cubre %d, que es el mes "
                     "de solape -> se omite", sim, aniomesSolape);
         return(false);
        }

      double factor = cm[idxSolape] / refSolape;
      int aniomes13 = AniomesMenos(aniomes0, idxNecesario);
      double ref13  = CierreRef(k, aniomes13);
      if(ref13 <= 0.0)
        {
         PrintFormat("  %s: la tabla de referencia no cubre %d -> se omite. "
                     "Hay que regenerarla con trend/generar_referencia.py",
                     sim, aniomes13);
         return(false);
        }
      p13 = ref13 * factor;

      if(InpLogDetallado && !g_silenciarEmpalme)
         PrintFormat("  %s empalme: solape %d (broker %.4f / ref %.4f = "
                     "factor %.4f)  ->  cierre %d reconstruido = %.4f",
                     sim, aniomesSolape, cm[idxSolape], refSolape, factor,
                     aniomes13, p13);
     }
   else
      return(false);

   if(p13 <= 0.0)
      return(false);
   retorno12m = cm[1] / p13 - 1.0;

   //--- volatilidad, de las barras diarias CERRADAS del propio broker
   int necD1 = InpDiasVol + 2;
   double cd[];
   ArraySetAsSeries(cd, true);
   nD1 = CopyClose(sim, PERIOD_D1, 0, necD1, cd);
   if(nD1 < necD1)
      return(false);

   double suma = 0.0, suma2 = 0.0;
   int    n = 0;
   for(int i = 1; i <= InpDiasVol; i++)
     {
      if(cd[i] <= 0.0 || cd[i + 1] <= 0.0)
         continue;
      double r = cd[i] / cd[i + 1] - 1.0;
      suma  += r;
      suma2 += r * r;
      n++;
     }
   if(n < InpDiasVol / 2)
      return(false);

   double media = suma / n;
   double var   = (suma2 - n * media * media) / (n - 1);
   if(var <= 0.0)
      return(false);
   vol = MathSqrt(var) * MathSqrt(252.0);
   return(vol > 0.0);
  }

//+------------------------------------------------------------------+
//| Exposicion objetivo de un mercado, como fraccion CON SIGNO de la  |
//| equity.                                                          |
//|                                                                  |
//|   exposicion = signo(retorno 12m) x (vol objetivo / vol realizada)|
//|                / divisor    x   factor del Guardian               |
//|                                                                  |
//| El divisor es max(mercados con datos, InpMercadosRef). Usar el    |
//| maximo y no el numero real es deliberado: si un mercado se cae de |
//| la cesta, la exposicion total BAJA en vez de subir. Repartir solo |
//| entre los que quedan concentraria el riesgo justo cuando hay      |
//| menos diversificacion.                                           |
//+------------------------------------------------------------------+
double ExposicionObjetivo(const string sim, const int nActivos,
                          double &senal, double &vol)
  {
   senal = 0.0;
   vol   = 0.0;
   double r12;
   int nMN1, nD1;
   if(!SenalYVol(sim, r12, vol, nMN1, nD1))
      return(0.0);

   senal = (r12 >= 0.0 ? 1.0 : -1.0);
   double e = senal * (InpVolPorMercado / 100.0) / vol;
   if(e > InpTopeExposicion)
      e = InpTopeExposicion;
   if(e < -InpTopeExposicion)
      e = -InpTopeExposicion;

   int divisor = MathMax(nActivos, InpMercadosRef);
   return(e / divisor * FactorGuardian());
  }

//+------------------------------------------------------------------+
//| Lotes para una exposicion dada, en fraccion de la equity.         |
//|                                                                  |
//| Se deriva del tick value, no del tamaño de contrato, porque el    |
//| tick value ya viene en la divisa de la cuenta y asi la formula    |
//| vale para indices, metales y divisas sin casos especiales:        |
//|                                                                  |
//|   un movimiento del 1% son  precio x 0,01  en unidades de precio  |
//|   eso vale por lote         (precio x 0,01 / tickSize) x tickValue|
//|   y queremos que valga      exposicion x equity x 0,01            |
//|   ->  lotes = exposicion x equity x tickSize / (precio x tickValue)|
//|                                                                  |
//| Devuelve 0 si no se puede calcular -> FALLA EN CERRADO.           |
//+------------------------------------------------------------------+
double LotesDe(const string sim, const double exposicion)
  {
   if(exposicion == 0.0)
      return(0.0);

   MqlTick tk;
   if(!SymbolInfoTick(sim, tk) || tk.bid <= 0.0)
      return(0.0);

   double tickValue = SymbolInfoDouble(sim, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(sim, SYMBOL_TRADE_TICK_SIZE);
   if(tickValue <= 0.0 || tickSize <= 0.0)
      return(0.0);

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity <= 0.0)
      return(0.0);

   double lotes = exposicion * equity * tickSize / (tk.bid * tickValue);

   double paso = SymbolInfoDouble(sim, SYMBOL_VOLUME_STEP);
   double maxL = SymbolInfoDouble(sim, SYMBOL_VOLUME_MAX);
   double sg   = (lotes >= 0.0 ? 1.0 : -1.0);
   double ab   = MathAbs(lotes);

   //--- Al paso MAS CERCANO, no hacia abajo. MathFloor parecia lo prudente
   //    pero introduce un SESGO sistematico: medido en el primer informe,
   //    la plata quedaba un 44% por debajo de su objetivo y el oro un 37%.
   //    Eso no es prudencia, es hundir la volatilidad de la pata entera por
   //    debajo del 3,91% que define la estrategia. Redondear al mas cercano
   //    deja el error centrado en cero.
   if(paso > 0.0)
      ab = MathRound(ab / paso) * paso;
   if(maxL > 0.0 && ab > maxL)
      ab = maxL;
   return(sg * NormalizeDouble(ab, 2));
  }

//+------------------------------------------------------------------+
//| Nocional en divisa de la cuenta que mueve UN lote.                |
//|                                                                  |
//| Se despeja de la misma identidad que usa LotesDe: un movimiento   |
//| del 1% vale (precio x 0,01 / tickSize) x tickValue por lote, y eso |
//| es el 1% del nocional. Por tanto:                                 |
//|      nocional por lote = precio x tickValue / tickSize            |
//|                                                                  |
//| Sirve para MEDIR el error de granularidad en vez de estimarlo.    |
//+------------------------------------------------------------------+
double NocionalPorLote(const string sim)
  {
   MqlTick tk;
   if(!SymbolInfoTick(sim, tk) || tk.bid <= 0.0)
      return(0.0);
   double tv = SymbolInfoDouble(sim, SYMBOL_TRADE_TICK_VALUE);
   double ts = SymbolInfoDouble(sim, SYMBOL_TRADE_TICK_SIZE);
   if(tv <= 0.0 || ts <= 0.0)
      return(0.0);
   return(tk.bid * tv / ts);
  }

//+------------------------------------------------------------------+
//| Lotes netos que este EA tiene abiertos en un simbolo. Positivo    |
//| largo, negativo corto.                                           |
//+------------------------------------------------------------------+
double PosicionActual(const string sim)
  {
   double neto = 0.0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(PositionGetTicket(i) == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) != sim)
         continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;
      double v = PositionGetDouble(POSITION_VOLUME);
      neto += (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? v : -v);
     }
   return(neto);
  }

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
//| Cierra TODAS las posiciones de este EA en un simbolo.             |
//+------------------------------------------------------------------+
bool CerrarSimbolo(const string sim, const string motivo)
  {
   bool todo = true;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) != sim)
         continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;

      MqlTick t;
      if(!SymbolInfoTick(sim, t) || t.bid <= 0.0 || t.ask <= 0.0)
        {
         todo = false;
         g_cFallos++;
         continue;
        }
      bool esLargo = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);

      MqlTradeRequest  req;  ZeroMemory(req);
      MqlTradeResult   res;  ZeroMemory(res);
      req.action       = TRADE_ACTION_DEAL;
      req.symbol       = sim;
      req.volume       = PositionGetDouble(POSITION_VOLUME);
      req.position     = tk;
      req.type         = (esLargo ? ORDER_TYPE_SELL : ORDER_TYPE_BUY);
      req.price        = (esLargo ? t.bid : t.ask);
      req.deviation    = InpDeslizamiento;
      req.magic        = InpMagic;
      req.type_filling = LlenadoDe(sim);
      req.comment      = motivo;

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
         PrintFormat("FALLO al cerrar %s: retcode=%d %s",
                     sim, res.retcode, res.comment);
         g_cFallos++;
         todo = false;
        }
      else
        {
         g_cOrdenes++;
         if(InpLogDetallado)
            PrintFormat("  cerrada %s %.2f lotes (%s)", sim, req.volume, motivo);
        }
     }
   return(todo);
  }

//+------------------------------------------------------------------+
bool AbrirSimbolo(const string sim, const double lotes, const bool largo)
  {
   if(lotes <= 0.0)
      return(false);

   MqlTick t;
   if(!SymbolInfoTick(sim, t) || t.bid <= 0.0 || t.ask <= 0.0)
      return(false);

   MqlTradeRequest  req;  ZeroMemory(req);
   MqlTradeResult   res;  ZeroMemory(res);
   req.action       = TRADE_ACTION_DEAL;
   req.symbol       = sim;
   req.volume       = lotes;
   req.type         = (largo ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   req.price        = (largo ? t.ask : t.bid);
   req.deviation    = InpDeslizamiento;
   req.magic        = InpMagic;
   req.type_filling = LlenadoDe(sim);
   req.comment      = "trend";

   bool ok = OrderSend(req, res);
   //--- Segundo intento con el otro modo de llenado. LlenadoDe() lee lo que
   //    el simbolo declara soportar, pero algunos brokers rechazan de todas
   //    formas y devuelven 10030 (invalid fill). Sin este reintento, un
   //    rechazo dejaba la cartera VACIA hasta el mes siguiente, porque el
   //    mes se marca como rebalanceado aunque las ordenes individuales
   //    fallen. El Guardian ya lo tenia al cerrar; esto faltaba al abrir.
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
      PrintFormat("FALLO al abrir %s %.2f lotes: retcode=%d %s",
                  sim, lotes, res.retcode, res.comment);
      g_cFallos++;
      return(false);
     }
   g_cOrdenes++;
   PrintFormat("  %s %s %.2f lotes a %.5f", (largo ? "LARGO" : "CORTO"),
               sim, lotes, req.price);
   return(true);
  }

//+------------------------------------------------------------------+
//| El rebalanceo mensual.                                           |
//|                                                                  |
//| Para cada mercado se calcula el objetivo y se compara con lo que  |
//| hay. Solo se toca si el cambio supera InpUmbralCambio: sin ese    |
//| umbral se pagaria un spread cada mes por ajustes de un 2%, y el   |
//| coste de giro medido (0,294% anual a 2 bp sobre una vol del       |
//| 5,41%) se multiplicaria.                                         |
//|                                                                  |
//| Cuando hay que tocar, se CIERRA y se REABRE en vez de mandar solo |
//| la diferencia. Es mas caro, pero funciona igual en cuentas de     |
//| neteo y de cobertura, y deja como maximo UNA posicion por         |
//| simbolo: si acumulara posiciones, el contador de averias del      |
//| Guardian se dispararia solo.                                     |
//+------------------------------------------------------------------+
bool Rebalancear()
  {
   //--- ¿averia declarada por el Guardian?
   if(InpRespetarGuardian && GlobalVariableCheck(GV_BLOQUEO) &&
      GlobalVariableGet(GV_BLOQUEO) > 0.0)
     {
      g_cBloqueoGuard++;
      Print("REBALANCEO CANCELADO: EA_Guardian senala averia.");
      return(false);
     }

   //--- El factor del Guardian se lee UNA vez. Si vale 0 (no publica y
   //    InpExigirGuardian esta activo), toda exposicion saldria 0 y el bucle
   //    de abajo lo interpretaria como "sin datos": cerraria la cartera
   //    entera con un mensaje falso. Se corta aqui, con el motivo correcto.
   double fg = FactorGuardian();
   if(fg <= 0.0)
     {
      g_cBloqueoGuard++;
      Print("REBALANCEO NO EJECUTADO: se exige EA_Guardian y no publica un "
            "factor fresco. Las posiciones abiertas NO se tocan.");
      return(false);
     }

   //--- ¿cuantos mercados tienen datos?
   int nActivos = 0;
   g_silenciarEmpalme = true;
   for(int i = 0; i < g_n; i++)
     {
      double r12, v;
      int a, b;
      if(g_ok[i] && SenalYVol(g_sim[i], r12, v, a, b))
         nActivos++;
     }
   g_silenciarEmpalme = false;

   if(nActivos < InpMinMercados)
     {
      g_cMesesSaltados++;
      PrintFormat("REBALANCEO NO EJECUTADO: solo %d mercados con datos, el "
                  "minimo es %d. Se reintentara: MT5 descarga el historial "
                  "de forma asincrona y las primeras lecturas salen vacias.",
                  nActivos, InpMinMercados);
      return(false);
     }

   MqlDateTime ny;
   TimeToStruct(AhoraNY(), ny);
   g_cRebalanceos++;
   PrintFormat("=== REBALANCEO %d/%02d  (%02d:%02d NY)  ·  %d mercados  ·  "
               "factor Guardian %.3f ===",
               ny.year, ny.mon, ny.hour, ny.min, nActivos, FactorGuardian());

   for(int i = 0; i < g_n; i++)
     {
      if(!g_ok[i])
         continue;
      string sim = g_sim[i];

      double senal, vol;
      double expo = ExposicionObjetivo(sim, nActivos, senal, vol);
      if(expo == 0.0)
        {
         //--- sin datos: se cierra lo que hubiera y se cuenta
         g_cSinDatos++;
         if(PosicionActual(sim) != 0.0)
           {
            PrintFormat("  %s sin datos suficientes -> se cierra", sim);
            CerrarSimbolo(sim, "trend: sin datos");
           }
         continue;
        }

      double objetivo = LotesDe(sim, expo);
      double minL     = SymbolInfoDouble(sim, SYMBOL_VOLUME_MIN);
      double actual   = PosicionActual(sim);

      if(MathAbs(objetivo) < minL)
        {
         if(InpUsarLoteMinimo)
           {
            objetivo = (expo >= 0.0 ? minL : -minL);
            PrintFormat("  %s objetivo por debajo del lote minimo -> se usa "
                        "el minimo %.2f (SOBREEXPONE)", sim, minL);
           }
         else
           {
            g_cSinLote++;
            PrintFormat("  %s objetivo %.4f < lote minimo %.2f -> se OMITE "
                        "(exposicion deseada %+.2f%% de la equity)",
                        sim, MathAbs(objetivo), minL, expo * 100.0);
            if(actual != 0.0)
               CerrarSimbolo(sim, "trend: por debajo del lote minimo");
            continue;
           }
        }

      //--- ¿merece la pena tocarlo?
      double cambio = MathAbs(objetivo - actual);
      double umbral = MathAbs(objetivo) * InpUmbralCambio / 100.0;
      bool   mismoLado = (objetivo * actual > 0.0);
      if(actual != 0.0 && mismoLado && cambio < MathMax(umbral, minL))
        {
         if(InpLogDetallado)
            PrintFormat("  %-11s se mantiene  %+.2f lotes  "
                        "(objetivo %+.2f, cambio %.2f < umbral %.2f)",
                        sim, actual, objetivo, cambio, MathMax(umbral, minL));
         continue;
        }

      //--- filtro de spread. Falla EN CERRADO si no hay precio.
      double sp = SpreadBp(sim);
      if(sp < 0.0 || sp > InpSpreadMaxBp)
        {
         g_cRechazoSpread++;
         PrintFormat("  %s spread %.2f bp fuera de limite (%.2f) -> "
                     "no se toca este mes", sim, sp, InpSpreadMaxBp);
         continue;
        }

      PrintFormat("  %-11s vol %.1f%%  señal %+.0f  objetivo %+.2f lotes "
                  "(%+.2f%% equity)  actual %+.2f",
                  sim, vol * 100.0, senal, objetivo, expo * 100.0, actual);

      if(actual != 0.0 && !CerrarSimbolo(sim, "trend: rebalanceo"))
        {
         Print("  ", sim, ": no se pudo cerrar, se deja para el proximo tick");
         continue;
        }
      AbrirSimbolo(sim, MathAbs(objetivo), objetivo > 0.0);
     }
   Print("=== fin del rebalanceo ===");
   return(true);
  }

//+------------------------------------------------------------------+
void Revisar()
  {
   //--- informe de arranque, en cuanto haya datos y como maximo 20 intentos
   if(g_diagPendiente && ((long)TimeCurrent() - (long)g_arranque) >= 10)
     {
      int conDatos = 0;
      g_silenciarEmpalme = true;
      for(int i = 0; i < g_n; i++)
        {
         double r12, v;
         int a, b;
         if(g_ok[i] && SenalYVol(g_sim[i], r12, v, a, b))
            conDatos++;
        }
      g_silenciarEmpalme = false;
      g_intentosDiag++;
      if(conDatos >= InpMinMercados || g_intentosDiag >= 20)
        {
         Diagnostico();
         g_diagPendiente = false;
         if(conDatos < InpMinMercados)
            Print("  AVISO: tras 20 intentos siguen faltando datos. Abre un ",
                  "grafico D1 de cada simbolo de la cesta y desplazate hacia ",
                  "atras para forzar la descarga del historial.");
        }
     }

   //--- Modo de solo diagnostico. Existe porque la primera vez que se pega
   //    este EA en un grafico, g_ultimoMesRebal vale 0 y el rebalanceo se
   //    dispara al instante: abriria ocho posiciones en una cuenta real
   //    antes de que nadie haya leido el informe de la cesta.
   if(InpSoloDiagnostico)
      return;

   datetime ahoraNY = AhoraNY();
   MqlDateTime ny;
   TimeToStruct(ahoraNY, ny);

   int mesActual = ny.year * 100 + ny.mon;
   if(mesActual == g_ultimoMesRebal)
      return;                          // este mes ya se rebalanceo

   int minutos    = ny.hour * 60 + ny.min;
   int minObjetivo = InpHoraRebalanceoNY * 60 + InpMinRebalanceoNY;
   if(minutos < minObjetivo)
     {
      g_avisoEspera = false;
      return;                          // aun no es la hora
     }

   if(minutos > minObjetivo + InpVentanaRebalMin)
     {
      //--- FUERA DE LA VENTANA. Hay dos situaciones y no son la misma:
      //
      //    a) Estamos en los primeros dias del mes. Entonces se ESPERA a la
      //       ventana del proximo dia de mercado, que cae en horario liquido.
      //       Esto existe porque en el primer arranque g_ultimoMesRebal vale
      //       0 y el rebalanceo se disparaba a cualquier hora, incluida la
      //       madrugada: los spreads se ensanchan y un mercado rechazado se
      //       queda plano UN MES ENTERO. Y sobre todo, obligaba a que un
      //       humano estuviera delante a las 10:00 de Nueva York. Un EA que
      //       necesita eso no sirve.
      //
      //    b) Ya vamos tarde en el mes (terminal apagado varios dias,
      //       festivos...). Entonces se rebalancea a la hora que sea: perder
      //       el mes es peor que pagar un spread ancho, porque la señal es
      //       mensual y la posicion del mes anterior puede tener el signo
      //       contrario.
      if(ny.day <= InpDiasEsperaVentana)
        {
         if(!g_avisoEspera)
           {
            g_avisoEspera = true;
            PrintFormat("Fuera de la ventana (%02d:%02d NY, dia %d del mes). "
                        "Se ESPERA a las %02d:%02d NY del proximo dia de "
                        "mercado: hay margen y los spreads son mejores. "
                        "No hace falta que nadie este delante.",
                        ny.hour, ny.min, ny.day, InpHoraRebalanceoNY,
                        InpMinRebalanceoNY);
           }
         return;
        }
      PrintFormat("AVISO: dia %d del mes y fuera de la ventana. Se rebalancea "
                  "IGUAL: perder el mes es peor que un spread ancho.", ny.day);
     }

   //--- El mes se marca SOLO si el rebalanceo se ejecuto. Marcarlo antes
   //    convertia un fallo transitorio de descarga de historial en un mes
   //    entero sin operar, y en silencio.
   if(Rebalancear())
     {
      g_ultimoMesRebal = mesActual;
      g_avisoEspera    = false;
     }
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   Revisar();
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   Revisar();
  }
//+------------------------------------------------------------------+
