import uuid
import datetime
from typing import Optional, Dict, Any
from src.core.models import BotStatus, StrategyGenome
from src.core.portfolio import BotPortfolio


class Bot:
    """
    Entidad fundamental del ecosistema evolutivo.
    Representa un agente de trading autónomo con su propio genoma, cartera y ciclo de vida.
    """

    def __init__(
        self,
        bot_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        generation: int = 0,
        genome: Optional[StrategyGenome] = None,
        initial_capital: float = 20.0,
        status: BotStatus = BotStatus.ACTIVE,
        created_at: Optional[str] = None,
        mutation_index: int = 0,
    ):
        self.bot_id = bot_id or str(uuid.uuid4())
        self.parent_id = parent_id
        self.generation = generation
        self.mutation_index = mutation_index
        self.genome = genome or StrategyGenome(
            archetype="donchian_breakout",
            parameters={"donchian_entry": 20, "donchian_exit": 10, "atr_period": 14},
            risk_reward_ratio=2.0,
            stop_loss_pct=0.02,
        )
        self.status = status
        self.created_at = created_at or datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.death_at: Optional[str] = None

        self.portfolio = BotPortfolio(bot_id=self.bot_id, initial_capital=initial_capital)
        self.reproduction_count: int = 0

    @property
    def equity(self) -> float:
        return self.portfolio.total_equity

    @property
    def is_alive(self) -> bool:
        return self.status == BotStatus.ACTIVE

    def evaluate_life_or_death(self, death_threshold: float = 0.0) -> bool:
        """Determina si el bot ha quebrado matemáticamente."""
        if self.is_alive and self.equity <= death_threshold:
            self.status = BotStatus.DEAD
            self.death_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
            return False
        return self.is_alive

    def can_reproduce(self, threshold: float = 40.0) -> bool:
        """
        Regla inquebrantable de reproducción:
        Solo puede reproducirse si su efectivo libre realizado es >= 40.0 €
        y no tiene posiciones en riesgo.
        """
        return self.is_alive and (self.portfolio.cash_balance >= threshold) and (self.portfolio.open_position is None)
