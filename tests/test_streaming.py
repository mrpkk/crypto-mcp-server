"""S7 tests: SSE price stream (single-batch mode)."""
import pytest
from fastapi.testclient import TestClient

import api_server


@pytest.fixture()
def client():
    api_server.rate_limiter.reset()
    yield TestClient(api_server.app)
    api_server.rate_limiter.reset()


def test_stream_single_batch(client, monkeypatch):
    async def fake_price(symbol, exchange="binance"):
        return {
            "data": {"symbol": symbol, "price_usd": 42000.0},
            "meta": {"source": "ccxt:test", "timestamp": "2026-09-15T00:00:00+00:00"},
        }

    monkeypatch.setattr("api_server.get_price", fake_price)
    response = client.get("/stream/prices?symbols=BTC/USDT,ETH/USDT&once=1")

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    body = response.text
    assert body.count("event: price") == 2
    assert "BTC/USDT" in body and "ETH/USDT" in body
    assert "\"price_usd\": 42000.0" in body
