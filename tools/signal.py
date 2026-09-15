"""Real technical indicators computed from OHLCV candles (pooled CCXT clients).

Replaces the previous random-based stub. Formulas (standard definitions):
- RSI-14: Wilder smoothing (J. Welles Wilder Jr., "New Concepts in Technical Trading Systems", 1978)
- MACD: EMA(12) - EMA(26), signal = EMA(9) of MACD line (Gerald Appel)
- MA50/MA200: simple moving averages on daily closes
- Support/resistance: swing lows/highs of the lookback window

No fabricated fallbacks: if candles are unavailable and no price was provided,
the tool returns an honest UNAVAILABLE error; if a price was provided, metrics
are returned as null with a warning instead of invented values.
"""
from __future__ import annotations

from typing import Any

from providers.base import make_envelope, make_error
from providers.market import ExchangePool

LOOKBACK = 200
MIN_CANDLES = 35


def ema(values: list[float], period: int) -> list[float]:
    """Exponential moving average; seeded with SMA of first `period` values."""
    if len(values) < period:
        return []
    k = 2 / (period + 1)
    out = [sum(values[:period]) / period]
    for v in values[period:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def rsi_wilder(closes: list[float], period: int = 14) -> float | None:
    """RSI with Wilder smoothing. Returns None when data is insufficient."""
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - 100 / (1 + rs), 1)


def sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


async def _fetch_closes(symbol: str, exchange_name: str) -> list[float] | None:
    exchange = ExchangePool.get(exchange_name)
    if exchange is None:
        return None
    try:
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe="1d", limit=LOOKBACK)
        closes = [c[4] for c in ohlcv if c and c[4]]
        return closes or None
    except Exception:
        return None


def _empty_metrics(symbol: str, price: float, warnings: list[str]) -> dict[str, Any]:
    data = {
        "symbol": symbol,
        "price_usd": price,
        "rsi_14": None,
        "macd": None,
        "moving_averages": {"ma_50": None, "ma_200": None, "trend": None},
        "support_resistance": {"support_1": None, "resistance_1": None},
        "candles_used": 0,
    }
    return make_envelope(data, source="price-only (candles unavailable)", warnings=warnings)


async def technical_indicators(symbol: str = "BTC/USDT", price: float = 0, exchange: str = "binance") -> dict[str, Any]:
    closes = await _fetch_closes(symbol, exchange)

    if not closes or len(closes) < MIN_CANDLES:
        if price <= 0:
            return make_error(
                "OHLCV_UNAVAILABLE",
                f"No candle data for {symbol} on {exchange} and no price provided",
                "Retry shortly, switch exchange, or pass price explicitly",
                retryable=True,
            )
        warnings = [f"candles unavailable for {symbol} on {exchange} — indicators skipped, price returned as provided"]
        return _empty_metrics(symbol, price, warnings)

    last = closes[-1]
    r = rsi_wilder(closes)
    e12 = ema(closes, 12)
    e26 = ema(closes, 26)
    macd_series = [a - b for a, b in zip(e12[len(e12) - len(e26):], e26)] if e12 and e26 else []
    sig = ema(macd_series, 9) if macd_series else []
    macd_line = macd_series[-1] if macd_series else None
    signal_line = sig[-1] if sig else None
    win = min(len(closes), 90)
    segment = closes[-win:]

    data = {
        "symbol": symbol,
        "price_usd": round(last, 2),
        "rsi_14": r,
        "macd": {
            "macd_line": round(macd_line, 4) if macd_line is not None else None,
            "signal_line": round(signal_line, 4) if signal_line is not None else None,
            "histogram": round(macd_line - signal_line, 4)
            if macd_line is not None and signal_line is not None
            else None,
            "crossover": ("bullish" if macd_line > signal_line else "bearish")
            if macd_line is not None and signal_line is not None
            else None,
        },
        "moving_averages": {
            "ma_50": round(sma(closes, 50), 2) if sma(closes, 50) else None,
            "ma_200": round(sma(closes, 200), 2) if sma(closes, 200) else None,
            "trend": ("up" if (sma(closes, 50) or 0) > (sma(closes, 200) or 0) else "down")
            if sma(closes, 200)
            else None,
        },
        "support_resistance": {
            "support_1": round(min(segment), 2),
            "resistance_1": round(max(segment), 2),
        },
        "candles_used": len(closes),
    }
    return make_envelope(data, source=f"ohlcv:{exchange}")
