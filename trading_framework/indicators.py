"""Technical indicator utilities for intraday futures strategy."""

from __future__ import annotations

import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential moving average."""
    return series.ewm(span=period, adjust=False).mean()


def vwap(df: pd.DataFrame) -> pd.Series:
    """Session VWAP computed from typical price and volume.

    Assumes input is already filtered to a single session if session reset is required.
    """
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    cumulative_tpv = (typical_price * df["volume"]).cumsum()
    cumulative_volume = df["volume"].cumsum().replace(0, pd.NA)
    return cumulative_tpv / cumulative_volume


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index using Wilder smoothing."""
    delta = series.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    avg_gain = gains.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range using Wilder smoothing."""
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def volume_spike(volume: pd.Series, lookback: int = 20, multiplier: float = 1.5) -> pd.Series:
    """Flag candles with significantly above-average volume."""
    rolling_mean = volume.rolling(lookback).mean()
    return volume > (rolling_mean * multiplier)


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all indicators used by the strategy."""
    out = df.copy()
    out["ema_50"] = ema(out["close"], 50)
    out["ema_200"] = ema(out["close"], 200)
    out["vwap"] = vwap(out)
    out["rsi_14"] = rsi(out["close"], 14)
    out["atr_14"] = atr(out, 14)
    out["volume_spike"] = volume_spike(out["volume"], lookback=20, multiplier=1.5)
    return out
