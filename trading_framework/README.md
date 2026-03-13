# Intraday Futures Trading Framework

This package implements a systematic intraday futures strategy for **MYM, MES, MNQ, and MGC**.

## Modules

- `data_loader.py`: data ingestion, timeframe resampling, session level extraction.
- `indicators.py`: 200 EMA, 50 EMA, VWAP, RSI(14), ATR, and volume spike detection.
- `strategy.py`: market bias engine + setup/entry/exit logic.
- `execution_engine.py`: risk checks and position sizing (1% risk, max 3 trades/day, stop after 2 losses, max daily loss 3%).
- `backtester.py`: historical simulation with trade outcome logic and performance metrics.
- `example_usage.py`: synthetic data demo showing decisioning and backtest output.

## Run Example

```bash
python -m trading_framework.example_usage
```

## Strategy Workflow (summary)

1. **Bias (LONG/SHORT/NEUTRAL)** via 15m trend + structure:
   - close vs 200 EMA
   - close vs VWAP
   - RSI momentum
   - position versus overnight and previous-day levels
2. **Institutional levels**:
   - previous day high/low/close
   - overnight high/low
   - intraday session high/low
3. **Setup detection (5m)**:
   - LONG: pullback to VWAP/EMA50 + bullish confirmation candle + volume spike
   - SHORT: rejection at VWAP/resistance + bearish confirmation candle + volume spike
4. **Execution plan**:
   - LONG entry above confirmation high; stop below swing low
   - SHORT entry below confirmation low; stop above swing high
   - take profit at minimum 1:2 RR
5. **Risk controls**:
   - 1% account risk per trade
   - max 3 trades/day
   - stop trading after 2 losses
   - max daily loss 3%
