import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.bot import Bot
from src.core.models import StrategyGenome
from src.engine.evolution_engine import EvolutionEngine
from src.engine.simulation_runner import SimulationRunner
from src.market.realistic_generator import generate_realistic_btc_market_cycles
from src.storage.db_manager import DatabaseManager


def execute_custom_simulation(num_candles: int = 400, split_ratio: float = 0.60):
    """
    Ejecuta una simulación completa con número de velas configurable
    y actualiza la base de datos para el Dashboard.
    """
    db_path = os.path.join("data", "evolution.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    db = DatabaseManager(db_path=db_path)
    engine = EvolutionEngine(
        reproduction_threshold=40.0,
        reproduction_cost=20.0,
        mutation_rate=0.45,
        speciation_rate=0.20,
    )
    runner = SimulationRunner(db=db, evolution_engine=engine)

    seeds = [
        Bot(
            bot_id="DONCHIAN-A_G0_M0_ROOT",
            generation=0,
            genome=StrategyGenome(
                archetype="donchian_breakout",
                parameters={"donchian_entry": 18, "donchian_exit": 9},
                stop_loss_pct=0.02,
            ),
            initial_capital=20.0,
            mutation_index=0,
        ),
        Bot(
            bot_id="RSI-B_G0_M0_ROOT",
            generation=0,
            genome=StrategyGenome(
                archetype="trend_pullback_rsi",
                parameters={"ema_trend": 30, "rsi_period": 14, "rsi_oversold": 32, "rsi_overbought": 68},
                stop_loss_pct=0.018,
            ),
            initial_capital=20.0,
            mutation_index=0,
        ),
        Bot(
            bot_id="BOLL-C_G0_M0_ROOT",
            generation=0,
            genome=StrategyGenome(
                archetype="bollinger_mean_reversion",
                parameters={"bb_period": 20, "bb_mult": 2.0},
                stop_loss_pct=0.015,
            ),
            initial_capital=20.0,
            mutation_index=0,
        ),
        Bot(
            bot_id="MACD-D_G0_M0_ROOT",
            generation=0,
            genome=StrategyGenome(
                archetype="macd_momentum",
                parameters={"macd_fast": 12, "macd_slow": 26, "macd_signal": 9},
                stop_loss_pct=0.02,
            ),
            initial_capital=20.0,
            mutation_index=0,
        ),
    ]

    for s in seeds:
        runner.add_bot(s)

    # Mercado con regímenes reales, caídas bruscas y trampas de volatilidad
    all_candles = generate_realistic_btc_market_cycles(count=num_candles, start_price=60000.0)

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

        # Si al liquidar su patrimonio queda por debajo del mínimo operativo (2.0 €), registrar defunción
        if bot.portfolio.cash_balance < 2.0:
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
    }
