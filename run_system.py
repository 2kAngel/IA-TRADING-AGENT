import os
import sys

# Asegurar path de importación
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.bot import Bot
from src.core.models import StrategyGenome
from src.engine.evolution_engine import EvolutionEngine
from src.engine.simulation_runner import SimulationRunner
from src.market.data_provider import generate_synthetic_btc_candles
from src.storage.db_manager import DatabaseManager


def main():
    print("=" * 60)
    print("INICIANDO BITCOIN EVOLUTION TRADING SYSTEM - FASE 1 MVP")
    print("=" * 60)

    db_path = os.path.join("data", "evolution.db")
    if os.path.exists(db_path):
        os.remove(db_path)  # Inicio limpio para el MVP

    db = DatabaseManager(db_path=db_path)
    engine = EvolutionEngine(reproduction_threshold=40.0, reproduction_cost=20.0)
    runner = SimulationRunner(db=db, evolution_engine=engine)

    # 1. Crear Bot Inicial (Generación 0 con 20.0 €)
    genesis_bot = Bot(
        bot_id="GENESIS-BOT-0",
        generation=0,
        genome=StrategyGenome(
            archetype="donchian_breakout",
            parameters={"donchian_entry": 15, "donchian_exit": 8, "atr_period": 14},
            risk_reward_ratio=2.5,
            stop_loss_pct=0.015,
        ),
        initial_capital=20.0,
    )
    runner.add_bot(genesis_bot)
    print(f"[+] Bot Génesis creado: {genesis_bot.bot_id} (Capital: {genesis_bot.equity:.2f} €)")

    # 2. Generar serie de velas sintéticas con tendencia para probar ciclo de vida
    print("[+] Generando 120 velas de mercado BTC/EUR...")
    candles = generate_synthetic_btc_candles(count=120, start_price=65000.0)

    # 3. Procesar mercado vela a vela
    for i in range(len(candles)):
        runner.process_candle(i, candles)

    # 4. Estado final del ecosistema
    print("\n" + "=" * 60)
    print("REPORTE FINAL DEL ECOSISTEMA TRAS SIMULACIÓN")
    print("=" * 60)

    total_equity = sum(b.equity for b in runner.active_bots)
    print(f"Bots Activos: {len(runner.active_bots)}")
    print(f"Bots Muertos: {len(runner.dead_bots)}")
    print(f"Capital Total del Ecosistema: {total_equity:.2f} €")

    for b in runner.active_bots:
        print(f" -> Bot: {b.bot_id} | Gen: {b.generation} | Capital: {b.equity:.2f} € | Reps: {b.reproduction_count} | Trades: {len(b.portfolio.trade_history)}")

    db.close()
    print("\n[OK] Simulación completada y persistida en SQLite con éxito.")


if __name__ == "__main__":
    main()
