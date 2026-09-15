"""S4 tests: RBAC permissions + SQLite-backed API key store (hashed at rest)."""
import sqlite3
import time

import pytest

from auth.keys import KEY_PREFIX, APIKeyStore, hash_key
from auth.rbac import TOOL_TO_PERMISSION, check_permission, permission_for_tool, tools_for_tier

# ---------- RBAC ----------

def test_free_tier_can_use_market_and_defi():
    assert check_permission("get_price", "free")
    assert check_permission("get_yields", "free")


def test_free_tier_cannot_use_onchain():
    assert not check_permission("gas_tracker", "free")
    assert not check_permission("track_whale", "free")


def test_pro_tier_can_use_onchain_and_intelligence():
    assert check_permission("gas_tracker", "pro")
    assert check_permission("trading_signal", "pro")


def test_enterprise_has_every_tool():
    for tool in TOOL_TO_PERMISSION:
        assert check_permission(tool, "enterprise"), f"enterprise denied {tool}"


def test_unknown_tool_and_tier_denied():
    assert not check_permission("nonexistent_tool", "enterprise")
    assert not check_permission("get_price", "hacker")


def test_tools_for_tier_lists():
    free_tools = tools_for_tier("free")
    assert "get_price" in free_tools
    assert "gas_tracker" not in free_tools
    assert "gas_tracker" in tools_for_tier("pro")


def test_permission_lookup():
    assert permission_for_tool("track_whale").value == "read:onchain"
    assert permission_for_tool("unknown") is None


# ---------- API key store ----------

@pytest.fixture()
def store(tmp_path):
    return APIKeyStore(str(tmp_path / "keys.db"))


def test_create_and_verify(store):
    key = store.create_key("pro", "test-key")
    assert key.startswith(KEY_PREFIX)
    verified = store.verify(key)
    assert verified == {"tier": "pro", "prefix": key[:8]}


def test_key_stored_hashed_not_plaintext(store):
    key = store.create_key("free", "hashed-check")
    with sqlite3.connect(store.db_path) as conn:
        stored_hash = conn.execute("SELECT key_hash FROM api_keys").fetchone()[0]
    assert stored_hash == hash_key(key)
    assert key not in stored_hash


def test_invalid_keys_rejected(store):
    assert store.verify("cms_bogus") is None
    assert store.verify("plain-key") is None
    assert store.verify("") is None


def test_revoke_key(store):
    key = store.create_key("free")
    assert store.verify(key) is not None
    assert store.revoke(key) is True
    assert store.verify(key) is None


def test_usage_metering(store):
    key = store.create_key("pro")
    store.record_usage(key, "get_price")
    store.record_usage(key, "get_price")
    assert store.usage_count(key) == 2
    assert store.usage_count(key, since=time.time() + 60) == 0


def test_invalid_tier_raises(store):
    with pytest.raises(ValueError):
        store.create_key("godmode")


def test_list_keys_metadata_only(store):
    store.create_key("free", "first")
    store.create_key("pro", "second")
    keys = store.list_keys()
    assert {k["tier"] for k in keys} == {"free", "pro"}
    for entry in keys:
        assert "key" not in entry and "key_hash" not in entry
