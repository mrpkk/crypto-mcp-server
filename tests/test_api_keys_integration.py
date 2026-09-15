"""S4 tests: API key integration in REST middleware (401 for bad keys, metering)."""
import pytest
from fastapi.testclient import TestClient

import api_server
from auth.keys import APIKeyStore


@pytest.fixture()
def client(tmp_path, monkeypatch):
    store = APIKeyStore(str(tmp_path / "test_keys.db"))
    monkeypatch.setattr(api_server, "api_key_store", store)
    api_server.rate_limiter.reset()
    yield TestClient(api_server.app), store
    api_server.rate_limiter.reset()


def test_anonymous_free_access(client):
    test_client, _ = client
    assert test_client.get("/version").status_code == 200


def test_invalid_api_key_rejected(client):
    test_client, _ = client
    response = test_client.get("/version", headers={"x-api-key": "cms_not-a-real-key"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_API_KEY"


def test_valid_key_accepted_and_metered(client):
    test_client, store = client
    key = store.create_key("pro", "integration")

    response = test_client.get("/version", headers={"x-api-key": key})

    assert response.status_code == 200
    assert response.headers["X-RateLimit-Limit"] == str(1000)  # pro tier limit
    assert store.usage_count(key) == 1


def test_revoked_key_rejected(client):
    test_client, store = client
    key = store.create_key("free")
    store.revoke(key)
    response = test_client.get("/version", headers={"x-api-key": key})
    assert response.status_code == 401
