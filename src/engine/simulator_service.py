import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.bot import Bot
from src.core.models import StrategyGenome
from src.engine.evolution_engine import EvolutionEngine
from src.engine.simulation_runner import SimulationRunner
from src.market.realistic_generator import generate_realistic_btc_market_cycles
from src.storage.db_manager import DatabaseManager


def execute_custom_simulation(num_candles: int = 800, capital_inicial: float = 80.0):
    """
    Ejecuta una simulación completa:
    - capital_inicial: Cada 20.0 € crea 1 semilla Génesis (ej. 20€ = 1 semilla, 80€ = 4 semillas, 100€ = 5 semillas).
    - num_candles: Número de velas de mercado.
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

    # Catálogo de arquetipos base para repartir las semillas
    archetype_templates = [
        ("DONCHIAN", "donchian_breakout", {"donchian_entry": 18, "donchian_exit": 9}, 0.02),
        ("MACD", "macd_momentum", {"macd_fast": 12, "macd_slow": 26, "macd_signal": 9}, 0.02),
        ("RSI", "trend_pullback_rsi", {"ema_trend": 30, "rsi_period": 14, "rsi_oversold": 32, "rsi_overbought": 68}, 0.018),
        ("BOLL", "bollinger_mean_reversion", {"bb_period": 20, "bb_mult": 2.0}, 0.015),
    ]

    # Calcular número exacto de semillas (mínimo 1)
    num_seeds = max(1, int(capital_inicial // 20.0))
    lineage_letters = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M"]

    seeds = []
    for i in range(num_seeds):
        code, arch, params, sl = archetype_templates[i % len(archetype_templates)]
        lin_letter = lineage_letters[i % len(lineage_letters)]
        suffix = f"SEED{i+1}" if num_seeds > 4 else "ROOT"
        bot_id = f"{code}-{lin_letter}_G0_M0_{suffix}"
        
        bot = Bot(
            bot_id=bot_id,
            generation=0,
            genome=StrategyGenome(
                archetype=arch,
                parameters=params.copy(),
                stop_loss_pct=sl,
            ),
            initial_capital=20.0,
            mutation_index=0,
        )
        seeds.append(bot)

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
