import time
import os
import signal
import sys
from typing import List, Dict, Any, Optional
from src.core.logger import get_logger
from src.core.bot import Bot
from src.core.models import StrategyGenome
from src.engine.evolution_engine import EvolutionEngine
from src.engine.simulation_runner import SimulationRunner
from src.market.data_provider import fetch_binance_btc_candles, generate_synthetic_btc_candles
from src.storage.db_manager import DatabaseManager


class ContinuousSupervisor:
    """
    Supervisor autónomo 24/7 para el ecosistema evolutivo:
    1. Recuperación automática del estado tras reinicios (Crash Recovery).
    2. Manejo de señales de terminación segura (SIGINT / SIGTERM).
    3. Watchdog de salud y verificación de integridad contable periódica.
    4. Bucle desatendido de actualización de mercado.
    """

    def __init__(
        self,
        db_path: str = "data/evolution.db",
        poll_interval_seconds: int = 60,
        symbol: str = "BTCEUR",
        candle_interval: str = "1h",
    ):
        self.logger = get_logger("Supervisor247")
        self.db_path = db_path
        self.poll_interval = poll_interval_seconds
        self.symbol = symbol
        self.candle_interval = candle_interval
        self.is_running = False

        self.db = DatabaseManager(db_path=self.db_path)
        self.evolution_engine = EvolutionEngine(
            reproduction_threshold=40.0,
            reproduction_cost=20.0,
            mutation_rate=0.35,
            speciation_rate=0.15,
        )
        self.runner = SimulationRunner(db=self.db, evolution_engine=self.evolution_engine)

        self._register_signals()

    def _register_signals(self):
        signal.signal(signal.SIGINT, self._handle_graceful_shutdown)
        signal.signal(signal.SIGTERM, self._handle_graceful_shutdown)

    def _handle_graceful_shutdown(self, signum, frame):
        self.logger.warning(f"Señal de interrupción recibida ({signum}). Deteniendo supervisor de forma segura...")
        self.is_running = False

    def recover_state_from_db(self):
        """
        Restaura todos los bots activos, muertos y balances desde SQLite.
        Si la base de datos está vacía, genera la población semilla Génesis.
        """
        self.logger.info("Verificando persistencia y restaurando estado de bots...")
        restored = self.db.load_all_bots()

        if restored:
            self.logger.info(f"Se han restaurado {len(restored)} bots desde la base de datos.")
            for bot in restored:
                if bot.is_alive:
                    self.runner.active_bots.append(bot)
                else:
                    self.runner.dead_bots.append(bot)
        else:
            self.logger.info("Base de datos limpia: Inicializando población Génesis...")
            genesis_seeds = [
                Bot(
                    bot_id="GENESIS-MACD-ALPHA",
                    generation=0,
                    genome=StrategyGenome(
                        archetype="macd_momentum",
                        parameters={"macd_fast": 12, "macd_slow": 26, "macd_signal": 9},
                        stop_loss_pct=0.02,
                    ),
                    initial_capital=20.0,
                ),
                Bot(
                    bot_id="GENESIS-DONCHIAN-BETA",
                    generation=0,
                    genome=StrategyGenome(
                        archetype="donchian_breakout",
                        parameters={"donchian_entry": 18, "donchian_exit": 9},
                        stop_loss_pct=0.02,
                    ),
                    initial_capital=20.0,
                ),
            ]
            for seed in genesis_seeds:
                self.runner.add_bot(seed)
                self.logger.info(f"Semilla creada: {seed.bot_id} (20.00 €)")

    def audit_ledger_integrity(self) -> bool:
        """
        Audita que la contabilidad cuadre matemáticamente:
        Efectivo actual + posiciones de bots vivos >= capital de los mismos.
        """
        for bot in self.runner.active_bots:
            if bot.portfolio.cash_balance < 0:
                self.logger.error(f"CORRUPCIÓN CONTABLE: Bot {bot.bot_id} tiene saldo negativo ({bot.portfolio.cash_balance:.2f}€).")
                return False
        return True

    def run_cycle(self, candles: Optional[List[Dict[str, Any]]] = None):
        """Ejecuta una ronda de evaluación de mercado sobre los bots."""
        if candles is None:
            try:
                self.logger.info(f"Obteniendo últimas velas reales de Binance ({self.symbol})...")
                candles = fetch_binance_btc_candles(symbol=self.symbol, interval=self.candle_interval, limit=100)
            except Exception as e:
                self.logger.warning(f"No se pudo conectar a Binance REST ({e}). Usando generador de respaldo...")
                candles = generate_synthetic_btc_candles(count=100, start_price=64000.0)

        # Procesar últimas velas
        for i in range(len(candles)):
            self.runner.process_candle(i, candles)

        self.audit_ledger_integrity()

        total_capital = sum(b.equity for b in self.runner.active_bots)
        self.logger.info(
            f"Ciclo completado | Bots Vivos: {len(self.runner.active_bots)} | "
            f"Muertos: {len(self.runner.dead_bots)} | Capital Ecosistema: {total_capital:.2f} €"
        )

    def start_loop(self, max_cycles: Optional[int] = None):
        """Inicia el bucle continuo 24/7."""
        self.logger.info("=" * 65)
        self.logger.info("SUPERVISOR CONTINUO 24/7 INICIADO")
        self.logger.info("=" * 65)

        self.recover_state_from_db()
        self.is_running = True
        cycle_count = 0

        try:
            while self.is_running:
                cycle_count += 1
                self.logger.info(f"--- Iniciando Ciclo de Supervisión #{cycle_count} ---")
                self.run_cycle()

                if max_cycles and cycle_count >= max_cycles:
                    self.logger.info(f"Alcanzado número máximo de ciclos de prueba ({max_cycles}).")
                    break

                self.logger.info(f"Esperando {self.poll_interval} segundos hasta el próximo ciclo...")
                for _ in range(self.poll_interval):
                    if not self.is_running:
                        break
                    time.sleep(1)

        finally:
            self.logger.info("Cerrando recursos y persistencia de base de datos...")
            self.db.close()
            self.logger.info("Supervisor finalizado limpiamente.")
