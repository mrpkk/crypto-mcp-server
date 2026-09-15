"""S2 tests: analysis tools use live prices only — no hardcoded 2024 values."""
import inspect

import pytest

import tools.analysis as analysis_module
from tools.analysis import analyze_token, portfolio_health

HARDCODED_MARKERS = ("65000", "3_500", "_ath_mult", "_atl_mult", "2.5e12", "19_700_000")


def test_no_hardcoded_prices_in_source():
    source = inspect.getsource(analysis_module)
    for marker in HARDCODED_MARKERS:
        assert marker not in source, f"hardcoded marker '{marker}' still present"


@pytest.fixture
def live(monkeypatch):
    async def _price(price_map):
        async def _fetch(symbol):
            return price_map.get(symbol.upper())

        return _fetch

    return _price


@pytest.fixture(autouse=True)
def _global_mc(monkeypatch):
    async def _fetch():
        return 2.5e12

    monkeypatch.setattr(analysis_module, "_fetch_global_market_cap", _fetch)


@pytest.mark.asyncio
async def test_analyze_token_live_price_minimal(monkeypatch):
    async def _fetch(symbol):
        return {"BTC": 42000.0}.get(symbol)

    monkeypatch.setattr(analysis_module, "_fetch_price", _fetch)

    out = await analyze_token("BTC")

    assert out["data"]["price_usd"] == 42000.0
    assert out["data"]["market_cap"] is None
    assert out["data"]["risk_assessment"]["score"] is None
    assert any("market_cap not provided" in w for w in out["meta"]["warnings"])


@pytest.mark.asyncio
async def test_analyze_token_price_unavailable(monkeypatch):
    async def _fetch(symbol):
        return None

    monkeypatch.setattr(analysis_module, "_fetch_price", _fetch)

    out = await analyze_token("NOSUCHCOIN")

    assert out["error"]["code"] == "PRICE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_analyze_token_full_metrics(monkeypatch):
    async def _fetch(symbol):
        return 42000.0

    monkeypatch.setattr(analysis_module, "_fetch_price", _fetch)

    out = await analyze_token("BTC", market_cap=800e9, volume_24h=30e9, ath=70000)

    data = out["data"]
    assert data["from_ath_pct"] == pytest.approx(-40.0)
    assert data["market_dominance_pct"] == pytest.approx(32.0)
    assert data["risk_assessment"]["score"] == 75
    assert data["risk_assessment"]["level"] == "low"
    assert "not investment advice" in data["risk_assessment"]["methodology"]


@pytest.mark.asyncio
async def test_portfolio_health_amounts(monkeypatch):
    async def _fetch(symbol):
        return {"ETH": 2500.0, "BTC": 60000.0}.get(symbol)

    monkeypatch.setattr(analysis_module, "_fetch_price", _fetch)

    out = await portfolio_health([{"symbol": "ETH", "amount": 1}, {"symbol": "BTC", "amount": 0.5}])

    data = out["data"]
    assert data["total_value_usd"] == 32500.0
    top = max(data["assets"], key=lambda a: a["weight_pct"])
    assert top["symbol"] == "BTC"
    assert data["concentration_risk"] == "high"
    assert data["diversity_score"] < 30
    assert any("Top position" in s for s in data["suggestions"])


@pytest.mark.asyncio
async def test_portfolio_health_value_usd_compat():
    out = await portfolio_health([{"symbol": "BTC", "value_usd": 1000}, {"symbol": "ETH", "value_usd": 3000}])

    assert out["data"]["total_value_usd"] == 4000.0
    assert out["data"]["assets"][1]["weight_pct"] == 75.0


@pytest.mark.asyncio
async def test_portfolio_health_empty():
    out = await portfolio_health([])
    assert out["error"]["code"] == "EMPTY_PORTFOLIO"


@pytest.mark.asyncio
async def test_portfolio_health_unpriced_skipped(monkeypatch):
    async def _fetch(symbol):
        return None

    monkeypatch.setattr(analysis_module, "_fetch_price", _fetch)

    out = await portfolio_health([{"symbol": "WIF", "amount": 1000}])

    assert out["error"]["code"] == "ZERO_VALUE"
