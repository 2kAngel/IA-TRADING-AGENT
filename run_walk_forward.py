import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.bot import Bot
from src.core.models import StrategyGenome
from src.engine.evolution_engine import EvolutionEngine
from src.engine.simulation_runner import SimulationRunner
from src.market.data_provider import generate_synthetic_btc_candles
from src.storage.db_manager import DatabaseManager


def run_walk_forward_evaluation():
    print("=" * 70)
    print("VALIDACIÓN CUANTITATIVA AVANZADA: WALK-FORWARD TESTING (FASE 3)")
    print("=" * 70)

    db_path = os.path.join("data", "evolution.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    db = DatabaseManager(db_path=db_path)
    engine = EvolutionEngine(
        reproduction_threshold=40.0,
        reproduction_cost=20.0,
        mutation_rate=0.45,
        speciation_rate=0.20,  # Permitir mutación de arquetipos
    )
    runner = SimulationRunner(db=db, evolution_engine=engine)

    # 4 Arquetipos Semilla Representativos de Generación 0 (Taxonomía Formal)
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
        print(f"[+] Semilla Génesis: {s.bot_id} | Arquetipo: {s.genome.archetype} (20.00 €)")

    # Dataset completo de 400 velas
    all_candles = generate_synthetic_btc_candles(count=400, start_price=60000.0)

    # División Walk-Forward: 60% Entrenamiento / In-Sample y 40% Validación / Out-of-Sample
    split_idx = int(len(all_candles) * 0.60)
    print(f"\n[1] FASE IN-SAMPLE (Entrenamiento): Velas 0 a {split_idx}...")
    for i in range(split_idx):
        runner.process_candle(i, all_candles)

    in_sample_active = len(runner.active_bots)
    in_sample_equity = sum(b.equity for b in runner.active_bots)
    print(f" -> Fin In-Sample: {in_sample_active} bots activos | Capital acumulado: {in_sample_equity:.2f} €")

    print(f"\n[2] FASE OUT-OF-SAMPLE (Prueba de Robustez Ciega): Velas {split_idx} a {len(all_candles)}...")
    for i in range(split_idx, len(all_candles)):
        runner.process_candle(i, all_candles)

    print("\n" + "=" * 70)
    print("REPORTE FINAL WALK-FORWARD COMPLETO")
    print("=" * 70)

    total_bots = len(runner.active_bots) + len(runner.dead_bots)
    total_equity = sum(b.equity for b in runner.active_bots)
    print(f"Total Población Generada: {total_bots} bots")
    print(f"Bots Supervivientes al Out-of-Sample: {len(runner.active_bots)}")
    print(f"Capital Final del Ecosistema: {total_equity:.2f} € (Inversión inicial: {len(seeds) * 20.0} €)")

    print("\nRanking de Linajes y Arquetipos Dominantes:")
    sorted_bots = sorted(runner.active_bots, key=lambda b: b.equity, reverse=True)
    for b in sorted_bots[:6]:
        print(f"  * {b.bot_id[:25]} | Gen: {b.generation} | Arquetipo: {b.genome.archetype:22} | Capital: {b.equity:.2f} € | Hijos: {b.reproduction_count}")

    db.close()


if __name__ == "__main__":
    run_walk_forward_evaluation()
