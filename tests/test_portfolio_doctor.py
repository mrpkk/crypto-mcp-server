"""S8 tests: Portfolio Doctor — concentration, risk, scenario, rebalance."""
import pytest

import tools.analysis as analysis_module
from tools.portfolio import portfolio_doctor


@pytest.fixture(autouse=True)
def _fake_prices(monkeypatch):
    async def _fetch(symbol):
        return {"ETH": 2500.0, "BTC": 60000.0, "USDT": 1.0}.get(symbol)

    monkeypatch.setattr(analysis_module, "_fetch_price", _fetch)


@pytest.mark.asyncio
async def test_doctor_flags_concentration_and_rebalance():
    out = await portfolio_doctor([{"symbol": "ETH", "amount": 1}, {"symbol": "BTC", "amount": 1}])

    data = out["data"]
    assert data["total_value_usd"] == 62500.0
    assert data["concentration"]["top_symbol"] == "BTC"
    assert data["concentration"]["risk"] == "high"
    assert data["risk_level"] in ("medium", "high")
    rebalance = data["rebalance_suggestions"]
    assert any(item.get("symbol") == "BTC" for item in rebalance)
    assert "not investment advice" in data["methodology"]
    assert out["meta"]["disclaimer"] == "Not financial advice."


@pytest.mark.asyncio
async def test_doctor_stable_buffer_reduces_risk():
    out = await portfolio_doctor(
        [{"symbol": "USDT", "amount": 8000}, {"symbol": "BTC", "amount": 0.02}]
    )

    data = out["data"]
    assert data["stablecoin_buffer_pct"] > 80
    assert data["risk_level"] == "low"
    scenario = data["scenario"]["market_drop_30pct"]
    assert scenario["estimated_value_usd"] > data["total_value_usd"] * 0.9


@pytest.mark.asyncio
async def test_doctor_empty_portfolio_error():
    out = await portfolio_doctor([])
    assert out["error"]["code"] == "EMPTY_PORTFOLIO"
