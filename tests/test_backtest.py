"""S8 tests: backtest simulation on real-shaped OHLCV (paper trading, no execution)."""
import pytest

import tools.backtest as backtest_module
from tools.backtest import backtest_strategy, simulate


def test_simulate_long_uptrend_profits():
    closes = [100 * (1.01**i) for i in range(60)]
    signals = [1] * len(closes)
    result = simulate(closes, signals, initial_usd=1000.0)
    assert result["final_value_usd"] > 1000.0
    assert result["pnl_pct"] > 0
    assert result["trades"] == 1  # один вход, позиция не закрывалась


def test_simulate_max_drawdown_on_v_shape():
    closes = [100, 110, 120, 90, 80, 95, 105]
    signals = [1] * len(closes)
    result = simulate(closes, signals, initial_usd=1000.0)
    assert result["max_drawdown_pct"] == pytest.approx(33.3, abs=1.0)


def _candles_from_closes(closes):
    return [[i, c, c, c, c, 1.0] for i, c in enumerate(closes)]


@pytest.mark.asyncio
async def test_backtest_sma_cross_envelope(monkeypatch):
    closes = [100 + i * 0.5 for i in range(120)] + [160 - i * 0.4 for i in range(80)]
    candles = _candles_from_closes(closes)

    async def fake_ohlcv(symbol, exchange_name, timeframe, limit):
        return candles

    monkeypatch.setattr(backtest_module, "_fetch_ohlcv", fake_ohlcv)
    out = await backtest_strategy("TEST/USDT", strategy="sma_cross", fast=5, slow=20)

    data = out["data"]
    assert data["mode"].startswith("paper simulation")
    assert "buy_and_hold_pct" in data
    assert data["params"]["candles"] == len(closes)
    assert out["meta"]["source"].startswith("ohlcv:")


@pytest.mark.asyncio
async def test_backtest_rsi_reversion(monkeypatch):
    closes = [100 + (i % 10) * 2 for i in range(200)]

    async def fake_ohlcv(symbol, exchange_name, timeframe, limit):
        return _candles_from_closes(closes)

    monkeypatch.setattr(backtest_module, "_fetch_ohlcv", fake_ohlcv)
    out = await backtest_strategy("TEST/USDT", strategy="rsi_reversion", slow=5)
    assert "error" not in out


@pytest.mark.asyncio
async def test_backtest_unknown_strategy(monkeypatch):
    async def fake_ohlcv(symbol, exchange_name, timeframe, limit):
        return _candles_from_closes([100.0] * 100)

    monkeypatch.setattr(backtest_module, "_fetch_ohlcv", fake_ohlcv)
    out = await backtest_strategy("TEST/USDT", strategy="magic")
    assert out["error"]["code"] == "UNKNOWN_STRATEGY"


@pytest.mark.asyncio
async def test_backtest_insufficient_data(monkeypatch):
    async def fake_ohlcv(symbol, exchange_name, timeframe, limit):
        return None

    monkeypatch.setattr(backtest_module, "_fetch_ohlcv", fake_ohlcv)
    out = await backtest_strategy("TEST/USDT")
    assert out["error"]["code"] == "OHLCV_UNAVAILABLE"
