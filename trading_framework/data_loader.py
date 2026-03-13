"""Data loading, resampling, and session-level feature preparation."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class SessionLevels:
    previous_day_high: float
    previous_day_low: float
    previous_day_close: float
    overnight_high: float
    overnight_low: float
    session_high: float
    session_low: float


def load_ohlcv_csv(path: str, tz: str = "America/New_York") -> pd.DataFrame:
    """Load OHLCV data with datetime index.

    Expected columns: timestamp, open, high, low, close, volume
    """
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp").sort_index()
    df = df.tz_convert(tz)
    required = ["open", "high", "low", "close", "volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return df[required]


def resample_timeframe(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Resample OHLCV to target timeframe, e.g. '5min', '15min'."""
    return (
        df.resample(timeframe)
        .agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        .dropna()
    )


def compute_session_levels(df_1m: pd.DataFrame, decision_time: pd.Timestamp) -> SessionLevels:
    """Compute previous-day and overnight institutional levels for intraday decisioning."""
    local_day = decision_time.normalize()
    previous_day = local_day - pd.Timedelta(days=1)

    prev_df = df_1m[(df_1m.index >= previous_day) & (df_1m.index < local_day)]
    if prev_df.empty:
        raise ValueError("No previous-day data available for level calculation")

    overnight_start = local_day - pd.Timedelta(hours=9, minutes=30)  # 18:30 previous day ET
    overnight_end = local_day + pd.Timedelta(hours=9, minutes=30)    # 09:30 current day ET
    overnight_df = df_1m[(df_1m.index >= overnight_start) & (df_1m.index < overnight_end)]

    intraday_df = df_1m[df_1m.index >= local_day]
    if intraday_df.empty:
        intraday_df = df_1m[df_1m.index >= local_day - pd.Timedelta(hours=1)]

    return SessionLevels(
        previous_day_high=float(prev_df["high"].max()),
        previous_day_low=float(prev_df["low"].min()),
        previous_day_close=float(prev_df["close"].iloc[-1]),
        overnight_high=float(overnight_df["high"].max()) if not overnight_df.empty else float("nan"),
        overnight_low=float(overnight_df["low"].min()) if not overnight_df.empty else float("nan"),
        session_high=float(intraday_df["high"].max()),
        session_low=float(intraday_df["low"].min()),
    )
