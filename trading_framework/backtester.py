"""Event-style backtester for the intraday futures strategy."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Dict, List

import pandas as pd

from .data_loader import compute_session_levels, resample_timeframe
from .execution_engine import ExecutionEngine, RiskManager
from .indicators import add_indicators
from .strategy import IntradayFuturesStrategy, TradeSignal


@dataclass
class BacktestResult:
    trades: pd.DataFrame
    metrics: Dict[str, float]


class IntradayBacktester:
    def __init__(self, strategy: IntradayFuturesStrategy, risk_manager: RiskManager):
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.engine = ExecutionEngine(risk_manager)

    def _resolve_trade_outcome(self, trade, future_bars: pd.DataFrame) -> float:
        """Resolve PnL by checking first hit between stop and target."""
        for _, bar in future_bars.iterrows():
            if trade.side == "LONG":
                if bar["low"] <= trade.stop:
                    return (trade.stop - trade.entry) * trade.quantity
                if bar["high"] >= trade.target:
                    return (trade.target - trade.entry) * trade.quantity
            else:
                if bar["high"] >= trade.stop:
                    return (trade.entry - trade.stop) * trade.quantity
                if bar["low"] <= trade.target:
                    return (trade.entry - trade.target) * trade.quantity

        # Exit at end of test window if neither stop nor target was hit.
        last_close = future_bars.iloc[-1]["close"]
        if trade.side == "LONG":
            return (last_close - trade.entry) * trade.quantity
        return (trade.entry - last_close) * trade.quantity

    def run(self, symbol: str, df_1m: pd.DataFrame, decision_hour: int = 9) -> BacktestResult:
        data_1m = add_indicators(df_1m)
        data_5m = add_indicators(resample_timeframe(df_1m, "5min"))
        data_15m = add_indicators(resample_timeframe(df_1m, "15min"))

        records: List[dict] = []
        for ts in data_5m.index[40:-12]:
            if ts.hour != decision_hour or ts.minute not in {0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}:
                continue
            if not self.risk_manager.can_trade():
                break

            try:
                levels = compute_session_levels(data_1m, ts)
            except ValueError:
                continue

            window_5m = data_5m.loc[:ts]
            window_15m = data_15m.loc[:ts]
            signal: TradeSignal = self.strategy.generate_signal(
                symbol=symbol,
                data_5m=window_5m,
                data_15m=window_15m,
                levels=levels,
            )

            trade = self.engine.execute_signal(signal)
            if trade is None:
                continue

            future = data_5m.loc[ts:].iloc[1:13]
            if future.empty:
                continue
            trade.pnl = self._resolve_trade_outcome(trade, future)

            records.append(
                {
                    "timestamp": ts,
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "entry": trade.entry,
                    "stop": trade.stop,
                    "target": trade.target,
                    "qty": trade.quantity,
                    "pnl": trade.pnl,
                }
            )

        trades_df = pd.DataFrame.from_records(records)
        metrics = self._compute_metrics(trades_df)
        return BacktestResult(trades=trades_df, metrics=metrics)

    def _compute_metrics(self, trades_df: pd.DataFrame) -> Dict[str, float]:
        if trades_df.empty:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "net_pnl": 0.0,
                "max_drawdown": 0.0,
                "sharpe": 0.0,
            }

        pnl = trades_df["pnl"]
        eq = pnl.cumsum()
        running_max = eq.cummax()
        drawdown = (eq - running_max).min()
        returns = pnl / max(self.risk_manager.account_size, 1)

        sharpe = 0.0
        if returns.std(ddof=0) > 0:
            sharpe = (returns.mean() / returns.std(ddof=0)) * sqrt(252)

        return {
            "total_trades": float(len(trades_df)),
            "win_rate": float((pnl > 0).mean()),
            "net_pnl": float(pnl.sum()),
            "max_drawdown": float(drawdown),
            "sharpe": float(sharpe),
        }
