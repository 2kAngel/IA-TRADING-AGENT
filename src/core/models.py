from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any
import datetime
import uuid


class BotStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DEAD = "DEAD"
    SUSPENDED = "SUSPENDED"


class LedgerEntryType(str, Enum):
    INITIAL_CAPITAL = "INITIAL_CAPITAL"
    TRADE_ALLOCATION = "TRADE_ALLOCATION"
    TRADE_RETURN = "TRADE_RETURN"
    COMMISSION = "COMMISSION"
    SLIPPAGE = "SLIPPAGE"
    REPRODUCTION_DEBIT = "REPRODUCTION_DEBIT"
    REPRODUCTION_CREDIT = "REPRODUCTION_CREDIT"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class TradeStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


@dataclass
class LedgerEntry:
    entry_id: Optional[int]
    bot_id: str
    entry_type: LedgerEntryType
    amount: float
    balance_after: float
    timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    reference_id: Optional[str] = None


@dataclass
class Position:
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    entry_time: str
    cost_basis: float  # Capital in cash allocated

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def unrealized_pnl(self) -> float:
        return self.market_value - self.cost_basis


@dataclass
class TradeRecord:
    trade_id: str
    bot_id: str
    symbol: str
    side: OrderSide
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    entry_time: str
    exit_time: Optional[str]
    commission: float
    slippage: float
    net_pnl: Optional[float]
    status: TradeStatus


@dataclass
class StrategyGenome:
    archetype: str
    parameters: Dict[str, Any]
    risk_reward_ratio: float = 2.0
    stop_loss_pct: float = 0.02
    trailing_stop: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "archetype": self.archetype,
            "parameters": self.parameters,
            "risk_reward_ratio": self.risk_reward_ratio,
            "stop_loss_pct": self.stop_loss_pct,
            "trailing_stop": self.trailing_stop,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StrategyGenome":
        return cls(
            archetype=data["archetype"],
            parameters=data["parameters"],
            risk_reward_ratio=data.get("risk_reward_ratio", 2.0),
            stop_loss_pct=data.get("stop_loss_pct", 0.02),
            trailing_stop=data.get("trailing_stop", False),
        )


@dataclass
class ReproductionRecord:
    reproduction_id: str
    parent_bot_id: str
    child_bot_id: str
    capital_transferred: float
    mutation_type: str
    mutation_summary: str
    timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
