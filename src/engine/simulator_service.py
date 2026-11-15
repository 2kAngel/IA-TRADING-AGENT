import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.bot import Bot
from src.core.models import StrategyGenome, BotStatus
from src.engine.evolution_engine import EvolutionEngine
from src.engine.simulation_runner import SimulationRunner
from src.market.market_data_provider import get_market_candles, ASSET_CONFIGS, TIMEFRAME_CONFIGS
from src.storage.db_manager import DatabaseManager


CHAMPION_CATALOG = [
    # Semilla 1: Estrategia Invertida (Breakout de Rango + Volumen POC)
    {
        "code": "INVERTIDA",
        "family": "INVERTIDA",
        "name": "Estrategia Invertida (Breakout Rango + Volumen POC)",
        "year": "2024",
        "archetype": "inverted_range_breakout",
        "parameters": {"periodo_rango": 15, "pct_zona": 0.15, "vol_mult": 1.1},
        "stop_loss_pct": 0.020,
    },
    # Semillas 2 a 5: Los 4 arquetipos técnicos fundacionales desplazados una posición
    {
        "code": "DONCHIAN",
        "family": "DONCHIAN",
        "name": "Richard Dennis (Turtles)",
        "year": "1983",
        "archetype": "donchian_breakout",
        "parameters": {"donchian_entry": 20, "donchian_exit": 10},
        "stop_loss_pct": 0.025,
    },
    {
        "code": "MACD",
        "family": "MACD",
        "name": "Gerald Appel (Momentum)",
        "year": "1979",
        "archetype": "macd_momentum",
        "parameters": {"macd_fast": 12, "macd_slow": 26, "macd_signal": 9},
        "stop_loss_pct": 0.022,
    },
    {
        "code": "RSI",
        "family": "RSI",
        "name": "J. Welles Wilder (RSI)",
        "year": "1978",
        "archetype": "trend_pullback_rsi",
        "parameters": {"rsi_period": 14, "rsi_oversold": 35, "rsi_overbought": 70},
        "stop_loss_pct": 0.020,
    },
    {
        "code": "BOLL",
        "family": "BOLL",
        "name": "John Bollinger (Mean Reversion)",
        "year": "1983",
        "archetype": "bollinger_mean_reversion",
        "parameters": {"bb_period": 20, "bb_mult": 2.0},
        "stop_loss_pct": 0.018,
    },
    # A partir de la 5ª semilla: Campeones Mundiales de Trading (World Cup Trading Championship)
    # Ordenados estrictamente de MÁS RECIENTE a MENOS RECIENTE (Año Descendente):
    {
        "code": "SCHERMAN",
        "family": "SCHERMAN",
        "name": "Ivan Scherman (World Champion)",
        "year": "2023",
        "archetype": "scherman_volatility_divergence",
        "parameters": {"bb_period": 20, "bb_mult": 2.0},
        "stop_loss_pct": 0.020,
    },
    {
        "code": "SEIBERT",
        "family": "SEIBERT",
        "name": "Stefan Seibert (World Champion)",
        "year": "2022",
        "archetype": "seibert_zeno_price_action",
        "parameters": {"period": 20},
        "stop_loss_pct": 0.022,
    },
    {
        "code": "MCCORMICK",
        "family": "MCCORMICK",
        "name": "Kevin McCormick (World Champion)",
        "year": "2021",
        "archetype": "mccormick_td_exhaustion",
        "parameters": {"lookback": 4},
        "stop_loss_pct": 0.020,
    },
    {
        "code": "SEIBERT",
        "family": "SEIBERT",
        "name": "Stefan Seibert (World Champion 342.3%)",
        "year": "2020",
        "archetype": "seibert_zeno_price_action",
        "parameters": {"period": 22},
        "stop_loss_pct": 0.021,
    },
    {
        "code": "HOFFMAN",
        "family": "HOFFMAN",
        "name": "Rob Hoffman (IRB Champion)",
        "year": "2015",
        "archetype": "hoffman_irb_bounce",
        "parameters": {"ema_trend": 20},
        "stop_loss_pct": 0.018,
    },
    {
        "code": "HUGHES",
        "family": "HUGHES",
        "name": "Chuck Hughes (World Champion 309.1%)",
        "year": "2015",
        "archetype": "hughes_keltner_trend",
        "parameters": {"k_period": 20, "k_mult": 1.5},
        "stop_loss_pct": 0.020,
    },
    {
        "code": "UNGER",
        "family": "UNGER",
        "name": "Andrea Unger (4x World Champion)",
        "year": "2012",
        "archetype": "unger_session_breakout",
        "parameters": {"lookback": 12, "exit_lookback": 6},
        "stop_loss_pct": 0.020,
    },
    {
        "code": "UNGER",
        "family": "UNGER",
        "name": "Andrea Unger (World Champion 239.6%)",
        "year": "2010",
        "archetype": "unger_session_breakout",
        "parameters": {"lookback": 16, "exit_lookback": 8},
        "stop_loss_pct": 0.022,
    },
    {
        "code": "UNGER",
        "family": "UNGER",
        "name": "Andrea Unger (World Champion 671.9%)",
        "year": "2008",
        "archetype": "unger_session_breakout",
        "parameters": {"lookback": 14, "exit_lookback": 7},
        "stop_loss_pct": 0.021,
    },
    {
        "code": "DAVEY",
        "family": "DAVEY",
        "name": "Kevin Davey (World Champion 107%)",
        "year": "2006",
        "archetype": "bollinger_mean_reversion",
        "parameters": {"bb_period": 22, "bb_mult": 2.1},
        "stop_loss_pct": 0.020,
    },
    {
        "code": "HUGHES",
        "family": "HUGHES",
        "name": "Chuck Hughes (World Cup 315.6%)",
        "year": "1999",
        "archetype": "hughes_keltner_trend",
        "parameters": {"k_period": 22, "k_mult": 1.7},
        "stop_loss_pct": 0.022,
    },
    {
        "code": "WILLIAMS",
        "family": "WILLIAMS",
        "name": "Michelle Williams (World Cup 1,001%)",
        "year": "1997",
        "archetype": "williams_r_momentum",
        "parameters": {"wr_period": 14, "wr_oversold": -80.0},
        "stop_loss_pct": 0.020,
    },
    {
        "code": "WILLIAMS",
        "family": "WILLIAMS",
        "name": "Larry Williams (All-Time Record 11,376%)",
        "year": "1987",
        "archetype": "williams_r_momentum",
        "parameters": {"wr_period": 10, "wr_oversold": -78.0},
        "stop_loss_pct": 0.024,
    },
]


def execute_custom_simulation(
    num_candles: int = 800,
    capital_inicial: float = 80.0,
    asset: str = "BTC",
    timeframe: str = "1h",
    leverage: float = 1.0,
):
    """
    Ejecuta una simulación completa sobre datos de mercado reales o sintéticos:
    - asset: Clave del activo ('BTC', 'GOLD', 'SP500', 'IBERDROLA').
    - timeframe: Temporalidad de velas ('1m', '1h', '1w').
    - leverage: Apalancamiento por trade (1.0 = Spot, 2.0 = 2x, 5.0 = 5x).
    - Modelo Capital.com: 0% comisión fija directa + Spread real.
    - capital_inicial: Cada 20.0 € crea 1 semilla Génesis.
    - La 1ª semilla es la Estrategia Invertida (Breakout Rango + POC Volumen).
    - Las semillas 2 a 5 corresponden a los 4 arquetipos técnicos fundacionales.
    - A partir de la 6ª semilla, se asignan estrategias de campeones mundiales.
    """
    db_path = os.path.join("data", "evolution.db")
    db = DatabaseManager(db_path=db_path)
    db.clear_all_data()

    engine = EvolutionEngine(
        reproduction_threshold=40.0,
        reproduction_cost=20.0,
        mutation_rate=0.45,
        speciation_rate=0.20,
    )
    runner = SimulationRunner(
        db=db,
        evolution_engine=engine,
        commission_rate=0.0,    # Capital.com: 0% comisiones directas
        slippage_rate=0.0002,   # Capital.com: Spread ultrabajo
        leverage=leverage,
    )

    # Calcular número exacto de semillas (mínimo 1)
    num_seeds = max(1, int(capital_inicial // 20.0))
    lineage_letters = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T"]

    seeds = []
    for i in range(num_seeds):
        cfg = CHAMPION_CATALOG[i % len(CHAMPION_CATALOG)]
        code = cfg["code"]
        lin_letter = lineage_letters[i % len(lineage_letters)]
        year = cfg["year"]
        
        # Suffix con trazabilidad de campeón y año (ej: DONCHIAN-A_G0_M0_DENNIS83, UNGER-E_G0_M0_2012)
        if i < 5:
            suffix = f"ROOT_{code}" if num_seeds <= 5 else f"SEED{i+1}_{code}"
        else:
            suffix = f"SEED{i+1}_{year}"

        bot_id = f"{code}-{lin_letter}_G0_M0_{suffix}"

        genome = StrategyGenome(
            archetype=cfg["archetype"],
            parameters=cfg["parameters"].copy(),
            stop_loss_pct=cfg["stop_loss_pct"],
        )

        bot = Bot(
            bot_id=bot_id,
            generation=0,
            genome=genome,
            initial_capital=20.0,
            mutation_index=0,
        )
        seeds.append(bot)

    for s in seeds:
        runner.add_bot(s)

    # Obtener velas reales de mercado (o fallback estocástico) para el activo y temporalidad
    all_candles = get_market_candles(
        asset_key=asset,
        timeframe=timeframe,
        num_candles=num_candles,
    )

    for i in range(len(all_candles)):
        runner.process_candle(i, all_candles)

    # Liquidar forzosamente posiciones abiertas al finalizar la simulación para auditoría real
    last_candle = all_candles[-1]
    final_price = last_candle["close"]
    for bot in list(runner.active_bots):
        if bot.portfolio.open_position is not None:
            target_trade_id = bot.portfolio.trade_history[-1].trade_id
            closed_t = bot.portfolio.close_trade(
                trade_id=target_trade_id,
                exit_price=final_price,
                commission_rate=runner.commission_rate,
                slippage_rate=runner.slippage_rate,
            )
            runner.db.save_trade(closed_t)
            for e in bot.portfolio.ledger[-2:]:
                runner.db.save_ledger_entry(e)

        # Si al liquidar su patrimonio queda por debajo del mínimo operativo (<= 4.5 €), registrar defunción
        if bot.portfolio.cash_balance <= 4.5:
            bot.status = BotStatus.DEAD
            bot.death_at = str(last_candle["timestamp"])
            if bot in runner.active_bots:
                runner.active_bots.remove(bot)
            runner.dead_bots.append(bot)
            runner.db.save_bot(bot)

    db.close()
    return {
        "total_active": len(runner.active_bots),
        "total_dead": len(runner.dead_bots),
        "total_equity": sum(b.equity for b in runner.active_bots),
        "asset": asset,
        "timeframe": timeframe,
        "candles_processed": len(all_candles),
    }
