from typing import Optional, Dict, Any, List
import datetime
from src.core.models import (
    LedgerEntry,
    LedgerEntryType,
    Position,
    OrderSide,
    TradeRecord,
    TradeStatus,
)


class BotPortfolio:
    """
    Gestiona el saldo, libro mayor (ledger) y posiciones de un bot individual.
    Garantiza contabilidad estricta por partida doble y conservación de capital.
    """

    def __init__(self, bot_id: str, initial_capital: float = 20.0):
        self.bot_id = bot_id
        self.cash_balance: float = initial_capital
        self.allocated_in_positions: float = 0.0
        self.open_position: Optional[Position] = None
        self.ledger: List[LedgerEntry] = []
        self.trade_history: List[TradeRecord] = []

        # Registrar el depósito inicial en el libro mayor
        self._record_ledger_entry(
            entry_type=LedgerEntryType.INITIAL_CAPITAL,
            amount=initial_capital,
            reference_id="GENESIS_DEPOSIT",
        )

    def _record_ledger_entry(
        self,
        entry_type: LedgerEntryType,
        amount: float,
        reference_id: Optional[str] = None,
    ) -> LedgerEntry:
        entry = LedgerEntry(
            entry_id=len(self.ledger) + 1,
            bot_id=self.bot_id,
            entry_type=entry_type,
            amount=amount,
            balance_after=round(self.cash_balance, 4),
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            reference_id=reference_id,
        )
        self.ledger.append(entry)
        return entry

    @property
    def total_equity(self) -> float:
        """Patrimonio neto liquidable (efectivo + valor de mercado de posiciones abiertas)"""
        pos_val = self.open_position.market_value if self.open_position else 0.0
        return round(self.cash_balance + pos_val, 4)

    def open_trade(
        self,
        trade_id: str,
        symbol: str,
        price: float,
        capital_to_invest: float,
        commission_rate: float = 0.00075,
        slippage_rate: float = 0.0002,
    ) -> TradeRecord:
        if self.open_position is not None:
            raise ValueError(f"Bot {self.bot_id} ya tiene una posición abierta.")

        if capital_to_invest > self.cash_balance:
            raise ValueError(
                f"Capital insuficiente. Requerido: {capital_to_invest:.2f}€, Disponible: {self.cash_balance:.2f}€"
            )

        # Aplicar slippage en la compra (precio ligeramente superior)
        effective_price = price * (1.0 + slippage_rate)
        commission = capital_to_invest * commission_rate
        net_investment = capital_to_invest - commission
        quantity = net_investment / effective_price

        # Descontar del efectivo
        self.cash_balance -= capital_to_invest
        self.allocated_in_positions = capital_to_invest

        self._record_ledger_entry(
            entry_type=LedgerEntryType.TRADE_ALLOCATION,
            amount=-capital_to_invest,
            reference_id=trade_id,
        )
        self._record_ledger_entry(
            entry_type=LedgerEntryType.COMMISSION,
            amount=-commission,
            reference_id=trade_id,
        )

        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.open_position = Position(
            symbol=symbol,
            quantity=quantity,
            entry_price=effective_price,
            current_price=effective_price,
            entry_time=now_str,
            cost_basis=capital_to_invest,
        )

        record = TradeRecord(
            trade_id=trade_id,
            bot_id=self.bot_id,
            symbol=symbol,
            side=OrderSide.BUY,
            entry_price=effective_price,
            exit_price=None,
            quantity=quantity,
            entry_time=now_str,
            exit_time=None,
            commission=commission,
            slippage=price * slippage_rate * quantity,
            net_pnl=None,
            status=TradeStatus.OPEN,
        )
        self.trade_history.append(record)
        return record

    def close_trade(
        self,
        trade_id: str,
        exit_price: float,
        commission_rate: float = 0.00075,
        slippage_rate: float = 0.0002,
    ) -> TradeRecord:
        if self.open_position is None:
            raise ValueError(f"Bot {self.bot_id} no tiene ninguna posición abierta para cerrar.")

        # Aplicar slippage en venta (precio ligeramente inferior)
        effective_exit = exit_price * (1.0 - slippage_rate)
        gross_return = self.open_position.quantity * effective_exit
        commission = gross_return * commission_rate
        net_return = gross_return - commission

        net_pnl = net_return - self.open_position.cost_basis

        # Retorno de capital a efectivo
        self.cash_balance += net_return
        self.allocated_in_positions = 0.0

        self._record_ledger_entry(
            entry_type=LedgerEntryType.TRADE_RETURN,
            amount=net_return,
            reference_id=trade_id,
        )
        self._record_ledger_entry(
            entry_type=LedgerEntryType.COMMISSION,
            amount=-commission,
            reference_id=trade_id,
        )

        # Actualizar historial
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        target_record = None
        for t in self.trade_history:
            if t.trade_id == trade_id:
                t.exit_price = effective_exit
                t.exit_time = now_str
                t.commission += commission
                t.net_pnl = round(net_pnl, 4)
                t.status = TradeStatus.CLOSED
                target_record = t
                break

        self.open_position = None
        return target_record

    def debit_for_reproduction(self, reproduction_cost: float = 20.0, reference_id: Optional[str] = None) -> float:
        """Extrae el capital exacto para financiar a un nuevo bot hijo."""
        if self.cash_balance < reproduction_cost:
            raise ValueError(
                f"Saldo en efectivo insuficiente para reproducir. Requerido: {reproduction_cost}€, Efectivo: {self.cash_balance}€"
            )
        self.cash_balance -= reproduction_cost
        self._record_ledger_entry(
            entry_type=LedgerEntryType.REPRODUCTION_DEBIT,
            amount=-reproduction_cost,
            reference_id=reference_id,
        )
        return reproduction_cost

    def credit_from_reproduction(self, capital: float = 20.0, reference_id: Optional[str] = None):
        """Acredita el capital inicial heredado por el bot hijo."""
        self.cash_balance += capital
        self._record_ledger_entry(
            entry_type=LedgerEntryType.REPRODUCTION_CREDIT,
            amount=capital,
            reference_id=reference_id,
        )
