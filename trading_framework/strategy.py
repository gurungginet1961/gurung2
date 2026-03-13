"""Core intraday futures strategy logic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import pandas as pd

from .data_loader import SessionLevels


@dataclass
class TradeSignal:
    symbol: str
    decision: str  # LONG / SHORT / NO TRADE
    bias: str
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reason: str = ""


class IntradayFuturesStrategy:
    """Rule-based strategy for MYM, MES, MNQ, and MGC."""

    def __init__(self, risk_reward: float = 2.0, atr_trailing_mult: float = 1.0):
        self.risk_reward = risk_reward
        self.atr_trailing_mult = atr_trailing_mult

    def determine_bias(
        self,
        latest_15m: pd.Series,
        levels: SessionLevels,
    ) -> str:
        """Step 1: Determine LONG/SHORT/NEUTRAL market bias."""
        score = 0

        if latest_15m["close"] > latest_15m["ema_200"]:
            score += 1
        else:
            score -= 1

        if latest_15m["close"] > latest_15m["vwap"]:
            score += 1
        else:
            score -= 1

        if latest_15m["rsi_14"] >= 55:
            score += 1
        elif latest_15m["rsi_14"] <= 45:
            score -= 1

        # Position vs overnight and previous-day structure
        if latest_15m["close"] > levels.overnight_high and latest_15m["close"] > levels.previous_day_high:
            score += 1
        elif latest_15m["close"] < levels.overnight_low and latest_15m["close"] < levels.previous_day_low:
            score -= 1

        if score >= 2:
            return "LONG"
        if score <= -2:
            return "SHORT"
        return "NEUTRAL"

    def detect_setup(
        self,
        bias: str,
        latest_5m: pd.Series,
        prev_5m: pd.Series,
        levels: SessionLevels,
    ) -> Optional[str]:
        """Step 3: Detect long/short setup confirmation."""
        bullish_confirmation = latest_5m["close"] > latest_5m["open"] and latest_5m["close"] > prev_5m["high"]
        bearish_confirmation = latest_5m["close"] < latest_5m["open"] and latest_5m["close"] < prev_5m["low"]

        pullback_to_value = (
            abs(latest_5m["low"] - latest_5m["vwap"]) / latest_5m["close"] < 0.0015
            or abs(latest_5m["low"] - latest_5m["ema_50"]) / latest_5m["close"] < 0.0015
        )
        rejection_at_value = (
            abs(latest_5m["high"] - latest_5m["vwap"]) / latest_5m["close"] < 0.0015
            or abs(latest_5m["high"] - latest_5m["ema_50"]) / latest_5m["close"] < 0.0015
            or abs(latest_5m["high"] - levels.previous_day_high) / latest_5m["close"] < 0.0015
        )

        has_volume = bool(latest_5m["volume_spike"])

        if bias == "LONG" and pullback_to_value and bullish_confirmation and has_volume:
            return "LONG"
        if bias == "SHORT" and rejection_at_value and bearish_confirmation and has_volume:
            return "SHORT"
        return None

    def build_trade_signal(
        self,
        symbol: str,
        setup: Optional[str],
        latest_5m: pd.Series,
        lookback_5m: pd.DataFrame,
    ) -> TradeSignal:
        """Step 4: Convert setup into executable trade plan."""
        if setup is None:
            return TradeSignal(symbol=symbol, decision="NO TRADE", bias="NEUTRAL", reason="No setup confirmation")

        atr_val = float(latest_5m["atr_14"])
        if pd.isna(atr_val) or atr_val <= 0:
            return TradeSignal(symbol=symbol, decision="NO TRADE", bias=setup, reason="ATR unavailable")

        swing_low = float(lookback_5m["low"].tail(5).min())
        swing_high = float(lookback_5m["high"].tail(5).max())

        if setup == "LONG":
            entry = float(latest_5m["high"] + 0.25 * atr_val)
            stop = min(swing_low, float(latest_5m["low"] - 0.5 * atr_val))
            risk = entry - stop
            tp = entry + self.risk_reward * risk
            return TradeSignal(symbol=symbol, decision="LONG", bias="LONG", entry_price=entry, stop_loss=stop, take_profit=tp)

        entry = float(latest_5m["low"] - 0.25 * atr_val)
        stop = max(swing_high, float(latest_5m["high"] + 0.5 * atr_val))
        risk = stop - entry
        tp = entry - self.risk_reward * risk
        return TradeSignal(symbol=symbol, decision="SHORT", bias="SHORT", entry_price=entry, stop_loss=stop, take_profit=tp)

    def generate_signal(
        self,
        symbol: str,
        data_5m: pd.DataFrame,
        data_15m: pd.DataFrame,
        levels: SessionLevels,
    ) -> TradeSignal:
        """Primary strategy API: produce LONG/SHORT/NO TRADE + levels."""
        if len(data_5m) < 30 or len(data_15m) < 30:
            return TradeSignal(symbol=symbol, decision="NO TRADE", bias="NEUTRAL", reason="Insufficient bars")

        latest_15m = data_15m.iloc[-1]
        latest_5m = data_5m.iloc[-1]
        prev_5m = data_5m.iloc[-2]

        bias = self.determine_bias(latest_15m=latest_15m, levels=levels)
        if bias == "NEUTRAL":
            return TradeSignal(symbol=symbol, decision="NO TRADE", bias=bias, reason="No directional bias")

        setup = self.detect_setup(bias=bias, latest_5m=latest_5m, prev_5m=prev_5m, levels=levels)
        signal = self.build_trade_signal(symbol=symbol, setup=setup, latest_5m=latest_5m, lookback_5m=data_5m)
        signal.bias = bias
        if signal.decision == "NO TRADE" and not signal.reason:
            signal.reason = "Setup invalid"
        return signal


def compute_index_correlation(recent_returns: Dict[str, pd.Series]) -> pd.DataFrame:
    """Optional feature: correlation matrix for MNQ/MES/MYM."""
    df = pd.DataFrame(recent_returns).dropna()
    if df.empty:
        return pd.DataFrame()
    return df.corr()
