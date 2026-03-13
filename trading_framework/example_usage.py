"""Example workflow for signal generation and backtesting."""

from __future__ import annotations

import random
import pandas as pd

from trading_framework.backtester import IntradayBacktester
from trading_framework.data_loader import compute_session_levels, resample_timeframe
from trading_framework.execution_engine import RiskManager
from trading_framework.indicators import add_indicators
from trading_framework.strategy import IntradayFuturesStrategy, compute_index_correlation


def make_sample_data(start: str = "2025-01-06 00:00:00+00:00", periods: int = 60 * 24 * 4) -> pd.DataFrame:
    """Generate synthetic 1-minute OHLCV data for demos/tests."""
    idx = pd.date_range(start, periods=periods, freq="1min", tz="UTC")

    rng = random.Random(7)
    prices = []
    px = 21000.0
    for _ in range(periods):
        px += rng.gauss(0.05, 2.5)
        prices.append(px)

    close = pd.Series(prices, index=idx)
    open_ = close.shift(1).fillna(close.iloc[0])

    high = pd.Series(index=idx, dtype=float)
    low = pd.Series(index=idx, dtype=float)
    volume = []

    for t in idx:
        o = float(open_.loc[t])
        c = float(close.loc[t])
        wiggle = abs(rng.gauss(0.6, 0.35))
        high.loc[t] = max(o, c) + wiggle
        low.loc[t] = min(o, c) - wiggle
        volume.append(rng.randint(20, 300))

    return pd.DataFrame(
        {
            "open": open_.values,
            "high": high.values,
            "low": low.values,
            "close": close.values,
            "volume": volume,
        },
        index=idx.tz_convert("America/New_York"),
    )


def run_demo() -> None:
    symbol = "MNQ"
    df_1m = make_sample_data()

    data_1m = add_indicators(df_1m)
    data_5m = add_indicators(resample_timeframe(df_1m, "5min"))
    data_15m = add_indicators(resample_timeframe(df_1m, "15min"))

    decision_time = data_5m.index[-1]
    levels = compute_session_levels(data_1m, decision_time)

    strategy = IntradayFuturesStrategy(risk_reward=2.0)
    signal = strategy.generate_signal(symbol=symbol, data_5m=data_5m, data_15m=data_15m, levels=levels)

    print("Latest trade decision")
    print(
        {
            "decision": signal.decision,
            "bias": signal.bias,
            "entry_price": signal.entry_price,
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
            "reason": signal.reason,
        }
    )

    # Optional correlation check for index micros
    ret_dict = {
        "MNQ": data_5m["close"].pct_change().tail(100),
        "MES": data_5m["close"].pct_change().tail(100) * 0.85,
        "MYM": data_5m["close"].pct_change().tail(100) * 0.7,
    }
    print("\nCorrelation matrix (demo):")
    print(compute_index_correlation(ret_dict))

    risk = RiskManager(account_size=25_000, risk_per_trade=0.01)
    backtester = IntradayBacktester(strategy=strategy, risk_manager=risk)
    result = backtester.run(symbol=symbol, df_1m=df_1m)

    print("\nBacktest metrics")
    print(result.metrics)
    print("\nRecent trades")
    print(result.trades.tail(5).to_string(index=False) if not result.trades.empty else "No trades")


if __name__ == "__main__":
    run_demo()
