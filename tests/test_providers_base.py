"""S3 tests: canonical contracts live in providers.base and are reused by tools."""
import inspect

import pytest

import tools.analysis as analysis_module
import tools.gas as gas_module
import tools.whales as whales_module
from providers.base import (
    CacheProvider,
    MarketDataProvider,
    Provider,
    make_envelope,
    make_error,
)


def test_envelope_shape():
    env = make_envelope({"x": 1}, source="test")
    assert set(env) == {"data", "meta"}
    assert env["meta"]["source"] == "test"
    assert env["meta"]["cached"] is False
    assert env["meta"]["degraded"] is False
    assert env["meta"]["freshness_seconds"] == 0


def test_error_shape():
    err = make_error("CODE", "message", "do this", retryable=True)
    assert err["error"] == {
        "code": "CODE",
        "message": "message",
        "retryable": True,
        "suggested_action": "do this",
    }


def test_provider_is_abstract():
    with pytest.raises(TypeError):
        Provider()  # type: ignore[abstract]
    with pytest.raises(TypeError):
        MarketDataProvider()  # type: ignore[abstract]
    with pytest.raises(TypeError):
        CacheProvider()  # type: ignore[abstract]


def test_tools_no_longer_define_local_contracts():
    for module in (gas_module, whales_module, analysis_module):
        source = inspect.getsource(module)
        assert "def _error(" not in source, f"{module.__name__} must reuse make_error from providers.base"
        assert "def _envelope(" not in source, f"{module.__name__} must reuse make_envelope from providers.base"
        assert "from providers.base import" in source


def test_cache_provider_contract():
    class InMemoryCache(CacheProvider):
        def __init__(self):
            self._store = {}

        def get(self, key):
            return self._store.get(key)

        def set(self, key, payload, ttl):
            self._store[key] = payload

    cache = InMemoryCache()
    assert cache.get("missing") is None
    cache.set("k", {"v": 1}, ttl=10)
    assert cache.get("k") == {"v": 1}
