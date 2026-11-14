import uuid
from typing import List, Dict, Any, Optional
from src.core.bot import Bot
from src.core.models import OrderSide
from src.engine.evolution_engine import EvolutionEngine
from src.engine.strategy_evaluator import StrategyEvaluator
from src.storage.db_manager import DatabaseManager


class SimulationRunner:
    """
    Motor de simulación multi-estrategia optimizado para la Fase 3.
    Delega la lógica técnica en StrategyEvaluator para soportar
    múltiples familias técnicas (Donchian, RSI Pullback, Bollinger, MACD).
    """

    def __init__(
        self,
        db: DatabaseManager,
        evolution_engine: Optional[EvolutionEngine] = None,
        commission_rate: float = 0.00075,
        slippage_rate: float = 0.0002,
    ):
        self.db = db
        self.evolution_engine = evolution_engine or EvolutionEngine()
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.active_bots: List[Bot] = []
        self.dead_bots: List[Bot] = []

    def add_bot(self, bot: Bot):
        self.active_bots.append(bot)
        self.db.save_bot(bot)
        for e in bot.portfolio.ledger:
            self.db.save_ledger_entry(e)

    def process_candle(self, candle_index: int, candles: List[Dict[str, Any]]):
        if candle_index < 10:
            return

        current_candle = candles[candle_index]
        close_price = current_candle["close"]
        low_price = current_candle["low"]
        closes = [c["close"] for c in candles[: candle_index + 1]]

        # 0. Limpieza previa: Si un bot sin posición tiene capital < 2.0 EUR, registrar su defunción
        for bot in list(self.active_bots):
            if bot.portfolio.open_position is None and bot.portfolio.cash_balance < 2.0:
                bot.status = BotStatus.DEAD
                bot.death_at = str(current_candle["timestamp"])
                self.active_bots.remove(bot)
                self.dead_bots.append(bot)
                self.db.save_bot(bot)

        # 1. Gestionar salidas de bots con posición abierta
        for bot in list(self.active_bots):
            if bot.portfolio.open_position is not None:
                pos = bot.portfolio.open_position
                pos.current_price = close_price

                # Evaluar salida técnica o Stop Loss
                should_exit = StrategyEvaluator.evaluate_exit(
                    genome=bot.genome,
                    candle_idx=candle_index,
                    candles=candles,
                    closes=closes,
                    entry_price=pos.entry_price,
                )

                if should_exit:
                    target_trade_id = bot.portfolio.trade_history[-1].trade_id
                    closed_t = bot.portfolio.close_trade(
                        trade_id=target_trade_id,
                        exit_price=close_price,
                        commission_rate=self.commission_rate,
                        slippage_rate=self.slippage_rate,
                    )
                    self.db.save_trade(closed_t)
                    for e in bot.portfolio.ledger[-2:]:
                        self.db.save_ledger_entry(e)

                    # Evaluar muerte por quiebra técnica (capital <= 2.0 EUR)
                    if not bot.evaluate_life_or_death(death_threshold=2.0):
                        if bot in self.active_bots:
                            self.active_bots.remove(bot)
                        self.dead_bots.append(bot)
                        self.db.save_bot(bot)
                        continue

            # 2. Evaluar entradas para bots sin posición (y vivos con fondos operativos)
            if bot.is_alive and bot.portfolio.open_position is None:
                # Comprobar si quedó incapacitado de operar por falta de saldo mínimo
                if bot.portfolio.cash_balance < 2.0:
                    bot.status = BotStatus.DEAD
                    bot.death_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    if bot in self.active_bots:
                        self.active_bots.remove(bot)
                    self.dead_bots.append(bot)
                    self.db.save_bot(bot)
                    continue

                should_enter = StrategyEvaluator.evaluate_entry(
                    genome=bot.genome,
                    candle_idx=candle_index,
                    candles=candles,
                    closes=closes,
                )

                if should_enter:
                    trade_id = str(uuid.uuid4())
                    
                    # REGLA BUFÓN O LEYENDA:
                    # Si el bot está en peligro crítico de quiebra técnica (<= 4.5 €),
                    # arriesga el 100% absoluto de sus últimos céntimos en un 'All-in' desesperado.
                    # Si tiene saldo normal (> 4.5 €), invierte su capital regular.
                    allocated = bot.portfolio.cash_balance
                    if bot.is_in_bufon_o_leyenda():
                        allocated = bot.portfolio.cash_balance  # Todo lo que queda, sin miramientos

                    if allocated >= 2.0:
                        trade = bot.portfolio.open_trade(
                            trade_id=trade_id,
                            symbol="BTC/EUR",
                            price=close_price,
                            capital_to_invest=allocated,
                            commission_rate=self.commission_rate,
                            slippage_rate=self.slippage_rate,
                        )
                        self.db.save_trade(trade)
                        for e in bot.portfolio.ledger[-2:]:
                            self.db.save_ledger_entry(e)

            # 3. Evaluar reproducción
            if bot.can_reproduce(threshold=self.evolution_engine.reproduction_threshold):
                child, rep_record = self.evolution_engine.reproduce(bot)
                self.add_bot(child)
                self.db.save_reproduction(rep_record)
                self.db.save_bot(bot)
                for e in bot.portfolio.ledger[-1:]:
                    self.db.save_ledger_entry(e)
