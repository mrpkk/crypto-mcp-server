"""Contract tests: every tool returns the documented keys; price tool behaves."""
import importlib

import pytest

from tools.price import get_price


@pytest.fixture(autouse=True)
def _clear_price_cache():
    from tools import price
    price.FETCH_CACHE.clear()
    yield


@pytest.mark.asyncio
async def test_get_price_happy_path(monkeypatch):
    class FakeEx:
        async def fetch_ticker(self, symbol):
            return {
                "last": 65000.0, "percentage": 2.5, "high": 66000.0,
                "low": 64000.0, "quoteVolume": 1_000_000_000.0,
                "bid": 64999.0, "ask": 65001.0,
                "timestamp": 1724200000000,
            }
        async def close(self):
            pass

    monkeypatch.setattr("tools.price._get_exchange", lambda name: FakeEx())
    out = await get_price("BTC/USDT", "binance")
    for key in ["symbol", "exchange", "price_usd", "change_24h", "high_24h",
                "low_24h", "volume_24h_usd", "bid", "ask", "timestamp"]:
        assert key in out, f"missing contract key: {key}"
    assert out["price_usd"] == 65000.0
    assert isinstance(out["timestamp"], str)


@pytest.mark.asyncio
async def test_get_price_unsupported_exchange():
    out = await get_price("BTC/USDT", "hitbtc")
    assert "error" in out


@pytest.mark.asyncio
async def test_get_price_exchange_failure(monkeypatch):
    class BrokenEx:
        async def fetch_ticker(self, symbol):
            raise RuntimeError("network down")
        async def close(self):
            pass
    monkeypatch.setattr("tools.price._get_exchange", lambda name: BrokenEx())
    out = await get_price("BTC/USDT", "binance")
    assert "error" in out


def test_all_tool_modules_importable():
    """Каждый инструментальный модуль должен импортироваться без сети/ключей."""
    for mod in ["tools.price", "tools.yield_tools", "tools.signal",
                "tools.analysis", "tools.gas", "tools.whales"]:
        try:
            importlib.import_module(mod)
        except Exception as e:  # pragma: no cover
            pytest.fail(f"{mod} import failed: {e}")
