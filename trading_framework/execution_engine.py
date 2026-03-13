"""Simple execution and risk controls for paper/live hooks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .strategy import TradeSignal


@dataclass
class ExecutedTrade:
    symbol: str
    side: str
    entry: float
    stop: float
    target: float
    quantity: int
    pnl: Optional[float] = None


@dataclass
class RiskManager:
    account_size: float
    risk_per_trade: float = 0.01
    max_trades_per_day: int = 3
    max_losses_per_day: int = 2
    max_daily_loss: float = 0.03
    trades_today: List[ExecutedTrade] = field(default_factory=list)

    def daily_realized_pnl(self) -> float:
        return sum(t.pnl for t in self.trades_today if t.pnl is not None)

    def losses_today(self) -> int:
        return sum(1 for t in self.trades_today if t.pnl is not None and t.pnl < 0)

    def can_trade(self) -> bool:
        if len(self.trades_today) >= self.max_trades_per_day:
            return False
        if self.losses_today() >= self.max_losses_per_day:
            return False
        if self.daily_realized_pnl() <= -(self.account_size * self.max_daily_loss):
            return False
        return True

    def position_size(self, entry: float, stop: float, point_value: float = 1.0) -> int:
        risk_budget = self.account_size * self.risk_per_trade
        per_contract_risk = abs(entry - stop) * point_value
        if per_contract_risk <= 0:
            return 0
        return max(1, int(risk_budget // per_contract_risk))


class ExecutionEngine:
    """Accepts strategy signals and enforces risk constraints before sending orders."""

    def __init__(self, risk_manager: RiskManager):
        self.risk_manager = risk_manager

    def execute_signal(self, signal: TradeSignal, point_value: float = 1.0) -> Optional[ExecutedTrade]:
        if signal.decision not in {"LONG", "SHORT"}:
            return None
        if not self.risk_manager.can_trade():
            return None

        qty = self.risk_manager.position_size(
            entry=signal.entry_price or 0,
            stop=signal.stop_loss or 0,
            point_value=point_value,
        )
        if qty <= 0:
            return None

        trade = ExecutedTrade(
            symbol=signal.symbol,
            side=signal.decision,
            entry=signal.entry_price or 0,
            stop=signal.stop_loss or 0,
            target=signal.take_profit or 0,
            quantity=qty,
        )
        self.risk_manager.trades_today.append(trade)
        return trade
