"""S3 tests: health/ready/version/capabilities endpoints (providers mocked)."""
import pytest
from fastapi.testclient import TestClient

import api_server


@pytest.fixture()
def client():
    api_server.rate_limiter.reset()
    yield TestClient(api_server.app)
    api_server.rate_limiter.reset()


def test_health_liveness(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == api_server.APP_VERSION


def test_version(client):
    body = client.get("/version").json()
    assert body["version"] == "2.0.0"
    assert body["api"] == "v2"


def test_ready_all_ok(client, monkeypatch):
    async def _fake_health():
        return {
            "market": {"provider": "ccxt", "status": "ok"},
            "onchain": {"provider": "web3", "status": "ok"},
            "llm": {"provider": "llm", "status": "ok"},
        }

    monkeypatch.setattr(api_server, "_collect_provider_health", _fake_health)
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_ready_when_provider_down(client, monkeypatch):
    async def _fake_health():
        return {
            "market": {"provider": "ccxt", "status": "down"},
            "onchain": {"provider": "web3", "status": "degraded"},
            "llm": {"provider": "llm", "status": "ok"},
        }

    monkeypatch.setattr(api_server, "_collect_provider_health", _fake_health)
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"


def test_capabilities_lists_14_tools(client, monkeypatch):
    async def _fake_health():
        return {"market": {"provider": "ccxt", "status": "ok"}}

    monkeypatch.setattr(api_server, "_collect_provider_health", _fake_health)
    body = client.get("/capabilities").json()
    assert body["tool_count"] == 14
    names = {tool["name"] for tool in body["tools"]}
    assert {"get_price", "gas_tracker", "track_whale", "portfolio_health"} <= names
