"""S3 tests: ExchangePool singleton + CCXTMarketProvider (no per-call client churn)."""
import asyncio

import pytest

from providers.base import MarketDataProvider
from providers.market import CCXTMarketProvider, ExchangePool


class FakeExchange:
    def __init__(self, ticker=None, error=None):
        self._ticker = ticker
        self._error = error
        self.closed = False

    async def fetch_ticker(self, symbol):
        if self._error:
            raise self._error
        return self._ticker

    async def close(self):
        self.closed = True


@pytest.fixture(autouse=True)
async def _clean_pool():
    yield
    await ExchangePool.close_all()


def test_pool_returns_singleton(monkeypatch):
    class FakeCCXT:
        binance = FakeExchange

    monkeypatch.setattr("providers.market.ccxt", FakeCCXT)

    first = ExchangePool.get("binance")
    second = ExchangePool.get("binance")

    assert first is second
    assert ExchangePool.size() == 1


def test_pool_unknown_exchange(monkeypatch):
    class FakeCCXT:
        pass

    monkeypatch.setattr("providers.market.ccxt", FakeCCXT)
    assert ExchangePool.get("nosuchexchange") is None


async def test_pool_close_all(monkeypatch):
    class FakeCCXT:
        binance = FakeExchange

    monkeypatch.setattr("providers.market.ccxt", FakeCCXT)
    exchange = ExchangePool.get("binance")
    await ExchangePool.close_all()
    assert exchange.closed is True
    assert ExchangePool.size() == 0


def test_provider_is_market_data_provider():
    assert isinstance(CCXTMarketProvider(), MarketDataProvider)


@pytest.mark.asyncio
async def test_fetch_price_envelope():
    ExchangePool._instances["binance"] = FakeExchange(
        ticker={"last": 42000.0, "bid": 41999.0, "ask": 42001.0, "percentage": 1.5, "quoteVolume": 1e9}
    )
    provider = CCXTMarketProvider()

    out = await provider.fetch_price("BTC/USDT", "binance")

    assert out["data"]["price_usd"] == 42000.0
    assert out["meta"]["source"] == "ccxt:binance"
    assert out["meta"]["cached"] is False


@pytest.mark.asyncio
async def test_fetch_price_no_data():
    ExchangePool._instances["binance"] = FakeExchange(ticker={})
    provider = CCXTMarketProvider()

    out = await provider.fetch_price("BTC/USDT", "binance")

    assert out["error"]["code"] == "NO_DATA"


@pytest.mark.asyncio
async def test_fetch_price_timeout():
    ExchangePool._instances["binance"] = FakeExchange(error=asyncio.TimeoutError())
    provider = CCXTMarketProvider()

    out = await provider.fetch_price("BTC/USDT", "binance")

    assert out["error"]["code"] == "TIMEOUT"
    assert out["error"]["retryable"] is True


@pytest.mark.asyncio
async def test_fetch_price_unsupported_exchange():
    provider = CCXTMarketProvider()
    out = await provider.fetch_price("BTC/USDT", "ftx")
    assert out["error"]["code"] == "UNSUPPORTED_EXCHANGE"


@pytest.mark.asyncio
async def test_compare_prices_spread():
    ExchangePool._instances["binance"] = FakeExchange(ticker={"last": 42000.0, "bid": 41999, "ask": 42001})
    ExchangePool._instances["coinbase"] = FakeExchange(ticker={"last": 42150.0, "bid": 42149, "ask": 42151})
    provider = CCXTMarketProvider(exchanges=("binance", "coinbase"))

    out = await provider.compare("BTC/USDT")

    assert out["data"]["arbitrage_spread"] == 150.0
    assert len(out["data"]["prices"]) == 2


@pytest.mark.asyncio
async def test_health_reports_pool_size(monkeypatch):
    class FakeCCXT:
        binance = FakeExchange

    monkeypatch.setattr("providers.market.ccxt", FakeCCXT)
    ExchangePool.get("binance")
    provider = CCXTMarketProvider(exchanges=("binance",))

    health = await provider.health()

    assert health["status"] == "ok"
    assert health["pooled_clients"] == 1
