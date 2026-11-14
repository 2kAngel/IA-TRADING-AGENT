import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.bot import Bot
from src.core.models import StrategyGenome
from src.engine.evolution_engine import EvolutionEngine
from src.engine.simulation_runner import SimulationRunner
from src.market.data_provider import generate_synthetic_btc_candles
from src.storage.db_manager import DatabaseManager


def run_multibot_experiment(num_candles: int = 350):
    print("=" * 65)
    print("EJECUTANDO SIMULACIÓN MULTIBOT EVOLUTIVA - FASE 2")
    print("=" * 65)

    db_path = os.path.join("data", "evolution.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    db = DatabaseManager(db_path=db_path)
    engine = EvolutionEngine(
        reproduction_threshold=40.0,
        reproduction_cost=20.0,
        mutation_rate=0.40,
        param_mutation_std=0.20,
    )
    runner = SimulationRunner(db=db, evolution_engine=engine)

    # Población Inicial (Semillas Diversas de Generación 0 con 20.0 € cada una)
    seeds = [
        Bot(
            bot_id="GENESIS-DONCHIAN-FAST",
            generation=0,
            genome=StrategyGenome(
                archetype="donchian_breakout",
                parameters={"donchian_entry": 12, "donchian_exit": 6},
                risk_reward_ratio=2.5,
                stop_loss_pct=0.015,
            ),
            initial_capital=20.0,
        ),
        Bot(
            bot_id="GENESIS-DONCHIAN-STANDARD",
            generation=0,
            genome=StrategyGenome(
                archetype="donchian_breakout",
                parameters={"donchian_entry": 20, "donchian_exit": 10},
                risk_reward_ratio=2.0,
                stop_loss_pct=0.020,
            ),
            initial_capital=20.0,
        ),
        Bot(
            bot_id="GENESIS-DONCHIAN-SLOW",
            generation=0,
            genome=StrategyGenome(
                archetype="donchian_breakout",
                parameters={"donchian_entry": 30, "donchian_exit": 15},
                risk_reward_ratio=3.0,
                stop_loss_pct=0.025,
            ),
            initial_capital=20.0,
        ),
    ]

    for seed in seeds:
        runner.add_bot(seed)
        print(f"[+] Bot Génesis registrado: {seed.bot_id} (20.00 €)")

    print(f"\n[+] Generando dataset de {num_candles} velas para simular ciclos de tendencia y reproducción...")
    candles = generate_synthetic_btc_candles(count=num_candles, start_price=62000.0)

    for i in range(len(candles)):
        runner.process_candle(i, candles)

    print("\n" + "=" * 65)
    print("SIMULACIÓN MULTIBOT FINALIZADA")
    print("=" * 65)
    total_active = len(runner.active_bots)
    total_dead = len(runner.dead_bots)
    total_bots = total_active + total_dead
    total_equity = sum(b.equity for b in runner.active_bots)

    print(f"Total Población Histórica: {total_bots} bots")
    print(f"Bots Activos Supervivientes: {total_active}")
    print(f"Bots Fallecidos: {total_dead}")
    print(f"Capital Total en Ecosistema: {total_equity:.2f} €")

    # Muestra de bots destacados
    print("\nTop Bots en Cartera:")
    sorted_bots = sorted(runner.active_bots, key=lambda b: b.equity, reverse=True)
    for b in sorted_bots[:5]:
        print(f"  * {b.bot_id[:25]} | Gen: {b.generation} | Capital: {b.equity:.2f} € | Hijos: {b.reproduction_count}")

    db.close()
    print("\n[OK] Datos listos para visualizar en el Dashboard.")


if __name__ == "__main__":
    run_multibot_experiment()
