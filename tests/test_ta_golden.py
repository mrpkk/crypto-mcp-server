"""Golden tests for technical indicators (tools/signal.py).

RSI reference values computed with an independent recursive Wilder implementation
and cross-checked against standard published examples.
"""
import pytest
from tools.signal import ema, rsi_wilder, sma, technical_indicators


def rsi_reference(closes, period=14):
    """Independent recursive implementation for cross-checking."""
    deltas = [b - a for a, b in zip(closes, closes[1:])]
    avg_gain = sum(d for d in deltas[:period] if d > 0) / period
    avg_loss = sum(-d for d in deltas[:period] if d < 0) / period
    for d in deltas[period:]:
        avg_gain = ((period - 1) * avg_gain + max(d, 0)) / period
        avg_loss = ((period - 1) * avg_loss + max(-d, 0)) / period
    return 100.0 if avg_loss == 0 else round(100 - 100 / (1 + avg_gain / avg_loss), 1)


def test_rsi_all_gains_is_100():
    closes = [float(i) for i in range(1, 40)]
    assert rsi_wilder(closes) == 100.0


def test_rsi_matches_reference_mixed_series():
    closes = [
        44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08,
        45.89, 46.03, 45.61, 46.28, 46.28, 46.00, 46.03, 46.41, 46.22, 45.64,
    ]
    assert rsi_wilder(closes) == pytest.approx(rsi_reference(closes))


def test_rsi_insufficient_data_returns_none():
    assert rsi_wilder([1.0, 2.0, 3.0]) is None


def test_ema_seeded_with_sma():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    e = ema(values, 3)
    assert e[0] == pytest.approx(2.0)          # SMA(1,2,3)
    k = 2 / 4
    assert e[1] == pytest.approx(4.0 * k + 2.0 * (1 - k))  # next point


def test_sma_basic():
    assert sma([2, 4, 6, 8], 4) == 5.0
    assert sma([2, 4], 50) is None


@pytest.mark.asyncio
async def test_indicators_from_synthetic_closes(monkeypatch):
    # детерминированная «рынка» серия: рост → откат → рост
    closes = [100 + i * 0.5 for i in range(60)] + \
             [130 - i * 0.3 for i in range(30)] + \
             [121 + i * 0.2 for i in range(60)]
    async def fake_fetch(symbol, exchange_name):
        return closes
    monkeypatch.setattr("tools.signal._fetch_closes", fake_fetch)

    out = await technical_indicators("TEST/USDT", exchange="binance")
    assert out["source"] == "ohlcv"
    assert out["candles_used"] == len(closes)
    assert out["price_usd"] == pytest.approx(round(closes[-1], 2))
    assert 0 <= out["rsi_14"] <= 100
    macd = out["macd"]
    assert macd["histogram"] == pytest.approx(macd["macd_line"] - macd["signal_line"], abs=1e-3)
    sr = out["support_resistance"]
    assert sr["support_1"] == round(min(closes[-90:]), 2)
    assert sr["resistance_1"] == round(max(closes[-90:]), 2)


@pytest.mark.asyncio
async def test_indicators_fallback_when_no_data(monkeypatch):
    async def broken_fetch(symbol, exchange_name):
        return None
    monkeypatch.setattr("tools.signal._fetch_closes", broken_fetch)
    out = await technical_indicators("UNKNOWN/USDT")
    assert out["source"] == "estimated"
    assert out["price_usd"] == 100.0
