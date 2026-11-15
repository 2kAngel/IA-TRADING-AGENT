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
        commission_rate: float = 0.0,
        slippage_rate: float = 0.0002,
        leverage: float = 1.0,
    ):
        self.db = db
        self.evolution_engine = evolution_engine or EvolutionEngine()
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.leverage = leverage
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
        high_price = current_candle["high"]
        low_price = current_candle["low"]
        closes = [c["close"] for c in candles[: candle_index + 1]]

        # 0. Limpieza previa: Si un bot sin posición tiene capital <= 4.5 EUR, registrar su defunción
        for bot in list(self.active_bots):
            if bot.portfolio.open_position is None and bot.portfolio.cash_balance <= 4.5:
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

                # Comprobación de Stop Loss y liquidación por margen intra-barra
                if pos.side == OrderSide.BUY:
                    sl_target = pos.entry_price * (1.0 - bot.genome.stop_loss_pct)
                    hit_stop_loss = low_price <= sl_target
                    max_loss_intra = (pos.entry_price - low_price) * pos.quantity
                    is_liquidated = (pos.cost_basis - max_loss_intra) <= 4.5
                else:
                    sl_target = pos.entry_price * (1.0 + bot.genome.stop_loss_pct)
                    hit_stop_loss = high_price >= sl_target
                    max_loss_intra = (high_price - pos.entry_price) * pos.quantity
                    is_liquidated = (pos.cost_basis - max_loss_intra) <= 4.5

                should_exit_indicator = StrategyEvaluator.evaluate_exit(
                    genome=bot.genome,
                    candle_idx=candle_index,
                    candles=candles,
                    closes=closes,
                    entry_price=pos.entry_price,
                )

                if hit_stop_loss or is_liquidated or should_exit_indicator:
                    exit_exec_price = sl_target if (hit_stop_loss or is_liquidated) else close_price
                    target_trade_id = bot.portfolio.trade_history[-1].trade_id
                    closed_t = bot.portfolio.close_trade(
                        trade_id=target_trade_id,
                        exit_price=exit_exec_price,
                        commission_rate=self.commission_rate,
                        slippage_rate=self.slippage_rate,
                    )
                    self.db.save_trade(closed_t)
                    for e in bot.portfolio.ledger[-2:]:
                        self.db.save_ledger_entry(e)

                    # Evaluar muerte por quiebra técnica (capital <= 4.5 EUR)
                    if not bot.evaluate_life_or_death(death_threshold=4.5):
                        if bot in self.active_bots:
                            self.active_bots.remove(bot)
                        self.dead_bots.append(bot)
                        self.db.save_bot(bot)
                        continue

            # 2. Evaluar entradas para bots sin posición (y vivos con fondos operativos)
            if bot.is_alive and bot.portfolio.open_position is None:
                if bot.portfolio.cash_balance <= 4.5:
                    bot.status = BotStatus.DEAD
                    bot.death_at = str(current_candle["timestamp"])
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
                    allocated = bot.portfolio.cash_balance

                    if allocated >= 2.0:
                        trade = bot.portfolio.open_trade(
                            trade_id=trade_id,
                            symbol="CFD",
                            price=close_price,
                            capital_to_invest=allocated,
                            commission_rate=self.commission_rate,
                            slippage_rate=self.slippage_rate,
                            side=OrderSide.BUY,
                            leverage=self.leverage,
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
