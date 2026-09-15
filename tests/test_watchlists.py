"""S7 tests: watchlist + alert rule stores and REST endpoints."""
import pytest
from fastapi.testclient import TestClient

import api_server
from watchlists import WatchlistStore


@pytest.fixture()
def store(tmp_path):
    return WatchlistStore(str(tmp_path / "wl.db"))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    store = WatchlistStore(str(tmp_path / "api_wl.db"))
    monkeypatch.setattr(api_server, "watchlist_store", store)
    api_server.rate_limiter.reset()
    yield TestClient(api_server.app), store
    api_server.rate_limiter.reset()


# ---------- store ----------

def test_watchlist_add_list_remove(store):
    item_id = store.add("asset", "BTC", "Bitcoin")
    items = store.list()
    assert len(items) == 1
    assert items[0]["kind"] == "asset" and items[0]["value"] == "BTC"
    assert store.remove(item_id) is True
    assert store.list() == []


def test_watchlist_unique_upsert(store):
    first = store.add("asset", "BTC", "old")
    second = store.add("asset", "BTC", "new")
    items = store.list()
    assert len(items) == 1
    assert items[0]["label"] == "new"
    assert first == second  # upsert keeps one row


def test_watchlist_bad_kind(store):
    with pytest.raises(ValueError):
        store.add("banana", "BTC")


def test_alert_rules_crud(store):
    rule_id = store.add_rule("gas_below", {"chain": "ethereum", "gwei_below": 5})
    rules = store.list_rules()
    assert len(rules) == 1
    assert rules[0]["kind"] == "gas_below"
    assert rules[0]["params"]["gwei_below"] == 5
    assert store.remove_rule(rule_id) is True
    assert store.list_rules() == []


# ---------- REST ----------

def test_watchlist_api_flow(client):
    test_client, _ = client
    response = test_client.post("/watchlist", json={"kind": "asset", "value": "ETH", "label": "Ethereum"})
    assert response.status_code == 201
    item_id = response.json()["id"]

    listing = test_client.get("/watchlist").json()
    assert listing["items"][0]["value"] == "ETH"

    assert test_client.delete(f"/watchlist/{item_id}").status_code == 204
    assert test_client.get("/watchlist").json()["items"] == []


def test_watchlist_api_bad_kind(client):
    test_client, _ = client
    response = test_client.post("/watchlist", json={"kind": "banana", "value": "X"})
    assert response.json()["error"]["code"] == "BAD_KIND"


def test_alerts_api_flow(client):
    test_client, _ = client
    response = test_client.post("/alerts", json={"kind": "price_move", "params": {"symbol": "BTC", "threshold_pct": 3}})
    assert response.status_code == 201
    rule_id = response.json()["id"]

    rules = test_client.get("/alerts").json()["rules"]
    assert rules[0]["params"]["threshold_pct"] == 3

    assert test_client.delete(f"/alerts/{rule_id}").status_code == 204
