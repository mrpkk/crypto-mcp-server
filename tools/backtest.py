"""Backtest v1 — paper-trading simulation on REAL historical OHLCV.

No execution, no orders: a virtual portfolio simulates a simple strategy
(SMA crossover or RSI mean-reversion) with fees, and reports honest metrics
including buy-and-hold comparison. Results are simulations, not predictions.
"""
from __future__ import annotations

from typing import Any

from providers.base import make_envelope, make_error
from providers.market import ExchangePool
from tools.signal import rsi_wilder, sma

FEE_RATE = 0.001  # 0.1% per trade (conservative spot taker)


async def _fetch_ohlcv(symbol: str, exchange_name: str, timeframe: str, limit: int) -> list[list[float]] | None:
    exchange = ExchangePool.get(exchange_name)
    if exchange is None:
        return None
    try:
        return await exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    except Exception:
        return None


def _sma_cross_signals(closes: list[float], fast: int, slow: int) -> list[int]:
    """1 = long, 0 = flat. Long while fast SMA > slow SMA."""
    signals = [0] * len(closes)
    for i in range(len(closes)):
        fast_ma = sma(closes[: i + 1], fast)
        slow_ma = sma(closes[: i + 1], slow)
        if fast_ma is not None and slow_ma is not None:
            signals[i] = 1 if fast_ma > slow_ma else 0
    return signals


def _rsi_reversion_signals(closes: list[float], low: float = 30, high: float = 70) -> list[int]:
    """Enter long when RSI < low, exit when RSI > high."""
    signals = [0] * len(closes)
    position = 0
    for i in range(len(closes)):
        rsi = rsi_wilder(closes[: i + 1])
        if rsi is None:
            continue
        if position == 0 and rsi < low:
            position = 1
        elif position == 1 and rsi > high:
            position = 0
        signals[i] = position
    return signals


def simulate(closes: list[float], signals: list[int], initial_usd: float) -> dict[str, Any]:
    cash = initial_usd
    position = 0.0
    trades = 0
    wins = 0
    entry_price = 0.0
    equity_curve: list[float] = []
    for close, signal in zip(closes, signals):
        if signal == 1 and position == 0.0:
            position = (cash * (1 - FEE_RATE)) / close
            cash = 0.0
            trades += 1
            entry_price = close
        elif signal == 0 and position > 0.0:
            cash = position * close * (1 - FEE_RATE)
            position = 0.0
            trades += 1
            if close > entry_price:
                wins += 1
        equity_curve.append(cash + position * close)
    final_value = equity_curve[-1] if equity_curve else initial_usd
    peak = equity_curve[0] if equity_curve else initial_usd
    max_drawdown = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - value) / peak)
    closed_trades = trades // 2
    return {
        "final_value_usd": round(final_value, 2),
        "pnl_pct": round((final_value / initial_usd - 1) * 100, 2),
        "max_drawdown_pct": round(max_drawdown * 100, 2),
        "trades": trades,
        "win_rate_pct": round(wins / closed_trades * 100, 1) if closed_trades else None,
    }


async def backtest_strategy(
    symbol: str = "BTC/USDT",
    strategy: str = "sma_cross",
    fast: int = 10,
    slow: int = 30,
    initial_usd: float = 10_000,
    timeframe: str = "1d",
    limit: int = 365,
    exchange: str = "binance",
) -> dict[str, Any]:
    ohlcv = await _fetch_ohlcv(symbol, exchange, timeframe, limit)
    if not ohlcv or len(ohlcv) < slow + 5:
        return make_error(
            "OHLCV_UNAVAILABLE",
            f"Not enough candle data for {symbol} on {exchange}",
            "Retry shortly, reduce slow period, or switch exchange",
            retryable=True,
        )

    closes = [candle[4] for candle in ohlcv]
    if strategy == "sma_cross":
        signals = _sma_cross_signals(closes, fast, slow)
    elif strategy == "rsi_reversion":
        signals = _rsi_reversion_signals(closes)
    else:
        return make_error(
            "UNKNOWN_STRATEGY",
            f"Unknown strategy: {strategy}",
            "Use sma_cross or rsi_reversion",
        )

    result = simulate(closes, signals, initial_usd)
    buy_hold_pct = round((closes[-1] / closes[0] - 1) * 100, 2)
    data = {
        "symbol": symbol,
        "strategy": strategy,
        "params": {"fast": fast, "slow": slow, "timeframe": timeframe, "candles": len(closes)},
        "initial_usd": initial_usd,
        **result,
        "buy_and_hold_pct": buy_hold_pct,
        "fees_pct_per_trade": FEE_RATE * 100,
        "mode": "paper simulation on historical data — not a prediction, not investment advice",
    }
    warnings = [f"simulation over {len(closes)} {timeframe} candles; results depend on period choice"]
    return make_envelope(data, source=f"ohlcv:{exchange} (paper trading)", warnings=warnings)
