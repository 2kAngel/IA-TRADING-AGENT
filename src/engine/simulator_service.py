import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.bot import Bot
from src.core.models import StrategyGenome, BotStatus
from src.engine.evolution_engine import EvolutionEngine
from src.engine.simulation_runner import SimulationRunner
from src.market.realistic_generator import generate_realistic_btc_market_cycles
from src.storage.db_manager import DatabaseManager


def generate_seed_genome(archetype_code: str, seed_index: int) -> StrategyGenome:
    """
    Genera genomas semilla con hipótesis técnicas variadas:
    - Donchian: ventanas de ruptura rápidas (10-15) vs lentas (20-35), salidas ceñidas vs amplias.
    - MACD: configuraciones de momentum reactivas vs filtradas.
    - RSI: niveles de sobreventa y periodos adaptados a distintos ritmos de rebote.
    - Bollinger: multiplicadores estrechos (1.6) a amplios (2.4) para atrapar extremos de volatilidad.
    """
    rng = random.Random(seed_index * 137 + 42)
    if archetype_code == "DONCHIAN":
        return StrategyGenome(
            archetype="donchian_breakout",
            parameters={
                "donchian_entry": rng.randint(12, 32),
                "donchian_exit": rng.randint(6, 16),
            },
            stop_loss_pct=round(rng.uniform(0.015, 0.035), 4),
        )
    elif archetype_code == "MACD":
        fast = rng.randint(8, 16)
        slow = rng.randint(22, 35)
        signal = rng.randint(7, 12)
        return StrategyGenome(
            archetype="macd_momentum",
            parameters={"macd_fast": fast, "macd_slow": slow, "macd_signal": signal},
            stop_loss_pct=round(rng.uniform(0.015, 0.032), 4),
        )
    elif archetype_code == "RSI":
        return StrategyGenome(
            archetype="trend_pullback_rsi",
            parameters={
                "rsi_period": rng.randint(10, 16),
                "rsi_oversold": rng.randint(30, 42),
                "rsi_overbought": rng.randint(65, 76),
            },
            stop_loss_pct=round(rng.uniform(0.015, 0.030), 4),
        )
    elif archetype_code == "BOLL":
        return StrategyGenome(
            archetype="bollinger_mean_reversion",
            parameters={
                "bb_period": rng.randint(14, 25),
                "bb_mult": round(rng.uniform(1.6, 2.3), 2),
            },
            stop_loss_pct=round(rng.uniform(0.012, 0.025), 4),
        )
    else:
        return StrategyGenome(
            archetype="donchian_breakout",
            parameters={"donchian_entry": 20, "donchian_exit": 10},
            stop_loss_pct=0.02,
        )


def execute_custom_simulation(num_candles: int = 800, capital_inicial: float = 80.0):
    """
    Ejecuta una simulación completa:
    - capital_inicial: Cada 20.0 € crea 1 semilla Génesis con su propia hipótesis genética.
    - num_candles: Número de velas de mercado.
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
    runner = SimulationRunner(db=db, evolution_engine=engine)

    # Catálogo de arquetipos base para rotación de semillas
    archetype_codes = ["DONCHIAN", "MACD", "RSI", "BOLL"]

    # Calcular número exacto de semillas (mínimo 1)
    num_seeds = max(1, int(capital_inicial // 20.0))
    lineage_letters = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T"]

    seeds = []
    for i in range(num_seeds):
        code = archetype_codes[i % len(archetype_codes)]
        lin_letter = lineage_letters[i % len(lineage_letters)]
        suffix = f"SEED{i+1}" if num_seeds > 4 else "ROOT"
        bot_id = f"{code}-{lin_letter}_G0_M0_{suffix}"

        genome = generate_seed_genome(code, i)
        
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
