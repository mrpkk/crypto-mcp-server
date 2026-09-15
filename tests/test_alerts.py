"""S7 tests: alert engine — fires on live data, explains why, never fabricates."""
import pytest

from alerts import evaluate_rules


@pytest.mark.asyncio
async def test_price_move_fires(monkeypatch):
    async def fake_price(symbol, exchange="binance"):
        return {
            "data": {"symbol": symbol, "price_usd": 100.0, "change_24h": -7.5},
            "meta": {"source": "ccxt:test", "timestamp": "2026-09-15T00:00:00+00:00"},
        }

    monkeypatch.setattr("tools.price.get_price", fake_price)
    env = await evaluate_rules([{"id": 1, "kind": "price_move", "params": {"symbol": "BTC", "threshold_pct": 5}}])

    assert env["data"]["count"] == 1
    alert = env["data"]["alerts"][0]
    assert "BTC" in alert["message"]
    assert alert["why_it_matters"]
    assert alert["values"]["change_24h"] == -7.5


@pytest.mark.asyncio
async def test_price_move_below_threshold_silent(monkeypatch):
    async def fake_price(symbol, exchange="binance"):
        return {"data": {"change_24h": 1.0}, "meta": {"source": "ccxt:test", "timestamp": ""}}

    monkeypatch.setattr("tools.price.get_price", fake_price)
    env = await evaluate_rules([{"id": 1, "kind": "price_move", "params": {"symbol": "BTC", "threshold_pct": 5}}])

    assert env["data"]["count"] == 0


@pytest.mark.asyncio
async def test_gas_below_fires(monkeypatch):
    async def fake_gas(chain="ethereum"):
        return {
            "data": {"chain": chain, "gas_price_gwei": 3.2},
            "meta": {"source": "web3:test", "timestamp": "2026-09-15T00:00:00+00:00"},
        }

    monkeypatch.setattr("tools.gas.gas_tracker", fake_gas)
    env = await evaluate_rules([{"id": 2, "kind": "gas_below", "params": {"chain": "ethereum", "gwei_below": 5}}])

    assert env["data"]["count"] == 1
    assert "3.2" in env["data"]["alerts"][0]["message"]


@pytest.mark.asyncio
async def test_whale_above_fires(monkeypatch):
    async def fake_alerts(min_value_usd=1_000_000, timeframe_hours=24, addresses=None, chain="ethereum", limit=25):
        return {
            "data": {
                "alerts": [
                    {"token_symbol": "USDT", "amount": 2_000_000.0, "amount_usd": 2_000_000.0, "chain": chain, "timestamp": "t"}
                ]
            },
            "meta": {"source": "etherscan-v2", "timestamp": ""},
        }

    monkeypatch.setattr("tools.whales.whale_alerts", fake_alerts)
    env = await evaluate_rules([{"id": 3, "kind": "whale_above", "params": {"min_usd": 1000000}}])

    assert env["data"]["count"] == 1
    assert "USDT" in env["data"]["alerts"][0]["message"]


@pytest.mark.asyncio
async def test_provider_error_becomes_warning(monkeypatch):
    async def broken_price(symbol, exchange="binance"):
        return {"error": {"code": "FETCH_FAILED", "message": "down", "retryable": True, "suggested_action": "retry"}}

    monkeypatch.setattr("tools.price.get_price", broken_price)
    env = await evaluate_rules([{"id": 1, "kind": "price_move", "params": {"symbol": "BTC"}}])

    assert env["data"]["count"] == 0
    assert any("FETCH_FAILED" in w for w in env["meta"]["warnings"])
