# BITCOIN EVOLUTION TRADING SYSTEM (IA-TRADING-AGENT)
## DOCUMENTO MAESTRO DE ARQUITECTURA TÉCNICA - FASE 0

---

## 1. INFORME DE VIABILIDAD Y LIMITACIONES DE PLATAFORMA

### 1.1 TradingView vs. Motor de Ejecución Local
TradingView es una plataforma líder para visualización y análisis de mercado, pero presenta limitaciones fundamentales para sistemas evolutivos multibot:

1. **Monocuenta y Monolítico:**
   - TradingView Paper Trading opera sobre una única cuenta global por usuario.
   - Pine Script no dispone de APIs ni mecanismos internos para segregar saldos o crear carteras virtuales aisladas.
   - Es imposible ejecutar 10, 50 o 100 bots simultáneos con carteras independientes de 20 € de forma nativa en TradingView.

2. **Restricciones del Plan Gratuito (Basic):**
   - Máximo 1 a 2 indicadores/estrategias activas simultáneas en el gráfico.
   - Solo 1 alerta activa en tiempo real.
   - Las alertas vía **Webhook** (necesarias para comunicación directa máquina a máquina) requieren planes de suscripción de pago (Essential, Plus o Premium). El plan gratuito solo soporta ventanas emergentes, sonidos y emails.
   - El probador de estrategias (Strategy Tester) limita el histórico a ~5.000 - 10.000 barras en temporalidades cortas.

3. **Arquitectura de Integración Decidida:**
   - **Python como Motor Central y Broker Virtual:** Python asume la contabilidad, la gestión del ciclo de vida de los bots, la ejecución de señales, la simulación de deslizamientos/comisiones, la reproducción evolutiva y la persistencia en base de datos.
   - **TradingView como Consola de Validación y Análisis Canónico:** Pine Script v6 se utiliza como estándar de referencia para verificar estrategias individuales, visualización técnica y auditoría manual de los progenitores más exitosos.
   - **Ingesta de Datos Independiente:** El motor Python obtiene datos de mercado en tiempo real e históricos mediante APIs públicas de exchanges Spot (ej. Binance / Kraken vía WebSocket y REST) sin coste y sin las restricciones del plan gratuito de TradingView.

---

## 2. ARQUITECTURA DEL SISTEMA

El sistema se estructura en una arquitectura modular orientada a eventos (*Event-Driven Simulation Architecture*):

```
                       ┌────────────────────────────────────────┐
                       │      Market Data Provider (BTC)        │
                       │    (Binance / Kraken REST & WS)        │
                       └──────────────────┬─────────────────────┘
                                          │ Velas OHLCV / Ticks
                                          ▼
                       ┌────────────────────────────────────────┐
                       │           Strategy Engine              │
                       │  (Ejecuta estrategias de bots activos) │
                       └──────────────────┬─────────────────────┘
                                          │ Señales (Buy / Sell / Flat)
                                          ▼
                       ┌────────────────────────────────────────┐
                       │            Risk Manager                │
                       │ (Límites de exposición, orden mínima)  │
                       └──────────────────┬─────────────────────┘
                                          │ Órdenes Validadas
                                          ▼
                       ┌────────────────────────────────────────┐
                       │      Virtual Portfolio & Ledger        │
                       │ (Contabilidad por partida doble, fees) │
                       └───────────┬────────────────┬───────────┘
                                   │                │
            Evaluación Equity >= 40€                │ Evaluación Equity <= 0€
                                   ▼                ▼
                       ┌────────────────┐      ┌────────────────┐
                       │Evolution Engine│      │  Death Record  │
                       │ (Reproducción) │      │  (Desactivar)  │
                       └───────┬────────┘      └────────────────┘
                               │
                               ▼
                       ┌────────────────────────────────────────┐
                       │       Database Manager (SQLite)        │
                       │   (Persistencia completa y ACID)       │
                       └──────────────────┬─────────────────────┘
                                          │
                                          ▼
                       ┌────────────────────────────────────────┐
                       │        Streamlit Dashboard UI          │
                       │ (Árbol genealógico, métricas, ranking) │
                       └────────────────────────────────────────┘
```

---

## 3. TECNOLOGÍAS SELECCIONADAS

- **Lenguaje:** Python 3.11+ (Tipado estático con `pydantic` y `dataclasses`).
- **Persistencia:** SQLite 3 con modo `WAL` (*Write-Ahead Logging*) y claves foráneas habilitadas para máxima velocidad y fiabilidad transaccional.
- **Cálculo Numérico y Técnico:** `pandas`, `numpy`, `numba` y funciones técnicas vectorizadas.
- **Conectividad de Mercado:** `ccxt` (soporte universal para exchanges spot) o `aiohttp` para endpoints públicos.
- **Dashboard Visual:** `Streamlit`, `Plotly` (curvas de capital interactivas) y `pyvis` / `graphviz` (árbol genealógico evolutivo).
- **Entorno TradingView:** Pine Script v6.

---

## 4. ESTRUCTURA DEL PROYECTO (`IA-TRADING-AGENT`)

```text
IA-TRADING-AGENT/
├── config/
│   ├── system_config.yaml          # Parámetros económicos, umbrales y comisiones
│   └── strategies_catalog.yaml     # Universo de indicadores y rangos de mutación
├── data/
│   ├── evolution.db                # Base de datos SQLite
│   └── cache/                      # Histórico de velas en caché
├── pine/
│   ├── evolution_bot_v6.pine       # Estrategia Pine Script v6 para TradingView
│   └── webhook_payload.json        # Esquema JSON de comunicación
├── src/
│   ├── core/                       # Modelos de dominio (Bot, Portfolio, Position, Trade)
│   ├── engine/                     # Motores (Strategy, Evolution, Risk)
│   ├── market/                     # Ingesta de datos de mercado (ccxt/ws)
│   ├── storage/                    # Capa de base de datos SQLite y migraciones
│   └── ui/                         # Streamlit Dashboard y visualizador de árboles
├── tests/                          # Suite de pruebas unitarias y de integración
│   ├── test_portfolio_ledger.py    # Validación de conservación de capital
│   ├── test_reproduction.py        # Validación de la mecánica de 20€ -> 40€
│   ├── test_death.py               # Validación de desconexión por balance 0
│   └── test_persistence.py         # Recuperación post-reinicio
├── README.md                       # Documentación general
└── run_system.py                   # Script de inicio del ecosistema
```

---

## 5. MODELO DE DATOS RELACIONAL (SQLITE)

El sistema se basa en un libro mayor (*ledger*) inmutable por partida doble:

```sql
-- Bots y Genealogía
CREATE TABLE bots (
    bot_id TEXT PRIMARY KEY,
    parent_id TEXT,
    generation INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('ACTIVE', 'DEAD', 'SUSPENDED')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    death_at TIMESTAMP,
    strategy_hash TEXT NOT NULL,
    FOREIGN KEY(parent_id) REFERENCES bots(bot_id)
);

-- Configuraciones de Estrategia (Genoma)
CREATE TABLE strategy_configurations (
    config_hash TEXT PRIMARY KEY,
    strategy_type TEXT NOT NULL,
    parameters_json TEXT NOT NULL,
    indicators_json TEXT NOT NULL,
    risk_rules_json TEXT NOT NULL
);

-- Libro Mayor Contable (Conservación de Capital)
CREATE TABLE ledger_entries (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_id TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    entry_type TEXT NOT NULL CHECK(entry_type IN (
        'INITIAL_CAPITAL', 
        'TRADE_ALLOCATION', 
        'TRADE_RETURN', 
        'COMMISSION', 
        'SLIPPAGE', 
        'REPRODUCTION_DEBIT', 
        'REPRODUCTION_CREDIT'
    )),
    amount REAL NOT NULL,
    balance_after REAL NOT NULL,
    reference_id TEXT,
    FOREIGN KEY(bot_id) REFERENCES bots(bot_id)
);

-- Posiciones y Operaciones
CREATE TABLE trades (
    trade_id TEXT PRIMARY KEY,
    bot_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK(side IN ('BUY', 'SELL')),
    entry_price REAL NOT NULL,
    exit_price REAL,
    quantity REAL NOT NULL,
    entry_time TIMESTAMP NOT NULL,
    exit_time TIMESTAMP,
    commission REAL NOT NULL DEFAULT 0.0,
    slippage REAL NOT NULL DEFAULT 0.0,
    net_pnl REAL,
    status TEXT NOT NULL CHECK(status IN ('OPEN', 'CLOSED')),
    FOREIGN KEY(bot_id) REFERENCES bots(bot_id)
);

-- Historial de Reproducciones y Mutaciones
CREATE TABLE reproductions (
    reproduction_id TEXT PRIMARY KEY,
    parent_bot_id TEXT NOT NULL,
    child_bot_id TEXT NOT NULL,
    capital_transferred REAL NOT NULL DEFAULT 20.0,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    mutation_type TEXT NOT NULL,
    mutation_summary TEXT NOT NULL,
    FOREIGN KEY(parent_bot_id) REFERENCES bots(bot_id),
    FOREIGN KEY(child_bot_id) REFERENCES bots(bot_id)
);
```

---

## 6. REGLAS ECONÓMICAS: REPRODUCCIÓN, MUERTE Y GESTIÓN DE RIESGO

### 6.1 Ley de Conservación de Capital
El capital total del ecosistema en cualquier instante $t$ se define por la ecuación invariable:
$$\text{Capital Total Ecosistema} = \sum_{i=1}^{N_{activos}} \text{Patrimonio}_i + \sum_{j=1}^{M_{muertos}} \text{Capital Final}_j$$
- La reproducción **nunca crea dinero**.
- Cuando un bot alcanza un patrimonio neto liquidable $\ge 40,00\ \text{€}$:
  1. Si tiene una posición abierta, **no se permite la reproducción con ganancias no realizadas (flotantes)**. Se debe esperar al cierre ordenado de la posición para garantizar liquidez real.
  2. Al cerrar la operación con saldo $\ge 40,00\ \text{€}$ en efectivo, se debita exactamente $20,00\ \text{€}$ de la cuenta del progenitor.
  3. Se acredita exactamente $20,00\ \text{€}$ al nuevo bot recién instanciado.
  4. Ambos continúan con $20,00\ \text{€}$ cada uno.

### 6.2 Regla de Muerte
- Cuando el patrimonio neto liquidable de un bot llega a $\le 0,00\ \text{€}$ (o cae por debajo de la comisión mínima requerida para abrir una orden de satoshis), el bot pasa al estado `DEAD`.
- No puede volver a operar ni recibir transferencias. Sus datos, métricas y genoma quedan intactos para análisis genealógico e investigación de causas de quiebra.

---

## 7. MOTOR EVOLUTIVO Y TIPOS DE MUTACIÓN

Cuando un bot progenitor se reproduce, el **Evolution Engine** aplica una mutación acotada pero determinista a su genoma:

1. **Mutación Tipo A (Parámetros Numéricos):**
   - Ajuste gaussiano suave ($\pm 5\%$ a $\pm 15\%$) de periodos de medias, umbrales de RSI, longitud de canales Donchian o bandas de volatilidad.
2. **Mutación Tipo B (Condición y Filtros):**
   - Incorporación o eliminación de un filtro de régimen (ej. añadir filtro ADX $> 22$ para filtrar mercados laterales, o exigir filtro de volumen relativo $> 1.2$).
3. **Mutación Tipo C (Gestión de Riesgo y Asimetría):**
   - Modificación del multiplicador ATR para el Stop Loss o alteración del ratio Riesgo/Beneficio del Take Profit (ej. de 1:2.0 a 1:2.5).
4. **Mutación Tipo D (Catálogo de Indicadores):**
   - Sustitución de un oscilador secundario (ej. RSI por Estocástico, o MACD por Momentum).

---

## 8. PLAN DE IMPLEMENTACIÓN POR FASES

- **FASE 0:** Documentación de Arquitectura y Configuración del Entorno (Completada).
- **FASE 1: MVP Evolutivo en Python:**
  - Estructuración de `src/core` (Bot, Portfolio con Ledger).
  - Creación del archivo de configuración `system_config.yaml`.
  - Base de datos SQLite y esquema de migraciones.
  - Implementación de la suite de los 8 tests críticos obligatorios.
  - Ejecución de simulación con el primer bot en Bitcoin.
- **FASE 2: Multibot y Dashboard:**
  - Ejecución simultánea de bots concurrentes.
  - Dashboard Streamlit con árbol genealógico interactivo.
- **FASE 3: Optimización Avanzada y Prevención de Overfitting:**
  - Walk-forward testing y validación fuera de muestra.
- **FASE 4: Validador Pine Script v6:**
  - Sincronización con TradingView y exportación de genomas ganadores a Pine v6.
