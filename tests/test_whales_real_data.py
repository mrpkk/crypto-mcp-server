"""S2 tests: whale tools use real provider data — no hardcoded mocks."""

import inspect
from datetime import datetime, timedelta, timezone
from typing import ClassVar

import pytest

import tools.whales as whales_module
from providers.whale_provider import WhaleTransaction
from tools.whales import track_whale, whale_alerts

VALID_ADDR = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
MOCK_MARKERS = ("WHALE_WALLETS", "balance_eth", "top_holdings", "Unknown Whale", "875_000_000")


def _tx(tx_hash, amount, symbol="ETH", hours_ago=1, block=100):
    ts = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()
    return WhaleTransaction(
        tx_hash=tx_hash,
        chain="ethereum",
        from_address="0x" + "1" * 40,
        to_address="0x" + "2" * 40,
        token_symbol=symbol,
        amount=amount,
        amount_usd=None,
        timestamp=ts,
        block_number=block,
    )


class FakeProvider:
    has_key = True
    _txs: ClassVar[list] = []

    async def get_transactions(self, address, chain="ethereum", limit=50):
        return list(self._txs)

    async def get_alerts(self, addresses, chain="ethereum", min_value_usd=1_000_000, limit=50):
        return list(self._txs)

    async def health(self):
        return {"provider": "fake", "status": "ok"}


class NoKeyProvider(FakeProvider):
    has_key = False


async def _fake_price(symbol):
    return {"ETH": 2500.0, "USDT": 1.0}.get(symbol)


@pytest.fixture(autouse=True)
def _clear_cache():
    whales_module.CACHE.clear()
    yield
    whales_module.CACHE.clear()


def test_no_mock_markers_in_source():
    source = inspect.getsource(whales_module)
    for marker in MOCK_MARKERS:
        assert marker not in source, f"mock marker '{marker}' still present"


@pytest.mark.asyncio
async def test_track_whale_bad_address():
    out = await track_whale("not-an-address")
    assert out["error"]["code"] == "BAD_ADDRESS"


@pytest.mark.asyncio
async def test_track_whale_missing_key(monkeypatch):
    monkeypatch.setattr(whales_module, "_get_provider", lambda: NoKeyProvider())
    out = await track_whale(VALID_ADDR)
    assert out["error"]["code"] == "MISSING_API_KEY"


@pytest.mark.asyncio
async def test_track_whale_real_data_and_filter(monkeypatch):
    big, dust = _tx("0xbig", 1500.0), _tx("0xdust", 0.001)
    fake = FakeProvider()
    fake._txs = [big, dust]
    monkeypatch.setattr(whales_module, "_get_provider", lambda: fake)
    monkeypatch.setattr(whales_module, "_symbol_price_usd", _fake_price)

    out = await track_whale(VALID_ADDR, min_value_usd=100_000)

    assert "error" not in out
    txs = out["data"]["transactions"]
    assert [t["tx_hash"] for t in txs] == ["0xbig"]
    assert txs[0]["amount_usd"] == 3_750_000.0
    assert out["meta"]["source"] == "etherscan-v2"
    assert out["meta"]["cached"] is False
    assert any("free tier" in w for w in out["meta"]["warnings"])


@pytest.mark.asyncio
async def test_track_whale_cached_second_call(monkeypatch):
    fake = FakeProvider()
    fake._txs = [_tx("0xbig", 1500.0)]
    monkeypatch.setattr(whales_module, "_get_provider", lambda: fake)
    monkeypatch.setattr(whales_module, "_symbol_price_usd", _fake_price)

    first = await track_whale(VALID_ADDR)
    second = await track_whale(VALID_ADDR)

    assert first["meta"]["cached"] is False
    assert second["meta"]["cached"] is True


@pytest.mark.asyncio
async def test_whale_alerts_not_configured(monkeypatch):
    monkeypatch.delenv("WHALE_WATCHLIST", raising=False)
    out = await whale_alerts()
    assert out["error"]["code"] == "NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_whale_alerts_filters_by_window_and_min(monkeypatch):
    fresh_big = _tx("0xfresh", 2_000_000.0, symbol="USDT", hours_ago=1)
    old_big = _tx("0xold", 3_000_000.0, symbol="USDT", hours_ago=50)
    fresh_small = _tx("0xsmall", 100.0, symbol="USDT", hours_ago=1)
    fake = FakeProvider()
    fake._txs = [fresh_big, old_big, fresh_small]
    monkeypatch.setattr(whales_module, "_get_provider", lambda: fake)
    monkeypatch.setattr(whales_module, "_symbol_price_usd", _fake_price)

    out = await whale_alerts(min_value_usd=1_000_000, timeframe_hours=24, addresses=[VALID_ADDR])

    assert "error" not in out
    hashes = [a["tx_hash"] for a in out["data"]["alerts"]]
    assert hashes == ["0xfresh"]


@pytest.mark.asyncio
async def test_whale_alerts_unpriced_token_warning(monkeypatch):
    unknown = _tx("0xunknown", 10_000_000.0, symbol="WIF", hours_ago=1)
    fake = FakeProvider()
    fake._txs = [unknown]
    monkeypatch.setattr(whales_module, "_get_provider", lambda: fake)
    monkeypatch.setattr(whales_module, "_symbol_price_usd", _fake_price)

    out = await whale_alerts(min_value_usd=1_000_000, addresses=[VALID_ADDR])

    assert out["data"]["count"] == 0
    assert any("no live USD price" in w for w in out["meta"]["warnings"])
