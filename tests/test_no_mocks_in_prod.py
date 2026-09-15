"""Regression guard: fabricated/demo data cannot reach production output paths.

These tests enforce the SPEC absolute rule: never substitute real data with mocks,
never return random values as market data. They fail if someone reintroduces them.
"""
import importlib
import inspect

import pytest

PRODUCTION_MODULES = (
    "tools.gas",
    "tools.whales",
    "tools.analysis",
    "tools.price",
    "providers.whale_provider",
    "chain.client",
)

FORBIDDEN_RANDOM = ("random.uniform", "random.randint", "random.random", "random.choice")
LEGACY_MOCK_MARKERS = (
    "WHALE_WALLETS",
    "Unknown Whale",
    "875_000_000",
    "1_040_000_000",
)
ERROR_CONTRACT_KEYS = {"code", "message", "retryable", "suggested_action"}


def test_no_random_in_production_sources():
    for module_name in PRODUCTION_MODULES:
        module = importlib.import_module(module_name)
        source = inspect.getsource(module)
        for marker in FORBIDDEN_RANDOM:
            assert marker not in source, f"{module_name} uses {marker} — random cannot be market data"


def test_no_legacy_mock_markers():
    for module_name in PRODUCTION_MODULES:
        module = importlib.import_module(module_name)
        source = inspect.getsource(module)
        for marker in LEGACY_MOCK_MARKERS:
            assert marker not in source, f"{module_name} still contains legacy mock marker '{marker}'"


@pytest.mark.asyncio
async def test_error_contract_is_uniform(monkeypatch):
    from tools.analysis import analyze_token
    from tools.gas import gas_tracker
    from tools.whales import track_whale

    results = [
        await gas_tracker("dogechain"),
        await track_whale("not-an-address"),
        await analyze_token(""),
    ]
    for result in results:
        assert "error" in result
        assert ERROR_CONTRACT_KEYS <= set(result["error"]), result


@pytest.mark.asyncio
async def test_envelope_structure_is_uniform(monkeypatch):
    import tools.analysis as analysis_module
    import tools.gas as gas_module
    from tests.test_gas_tracker import FakeProvider
    from tools.analysis import analyze_token
    from tools.gas import gas_tracker

    def _fake_provider():
        return FakeProvider()

    async def _price(symbol):
        return 100.0

    async def _no_native_price(chain):
        return None, ["no live price"]

    monkeypatch.setattr(gas_module, "_get_onchain_provider", _fake_provider)
    monkeypatch.setattr(gas_module, "_native_price_usd", _no_native_price)
    monkeypatch.setattr(analysis_module, "_fetch_price", _price)

    gas = await gas_tracker("ethereum")
    token = await analyze_token("SOL")

    for result in (gas, token):
        assert set(result) == {"data", "meta"}
        meta = result["meta"]
        assert {"source", "timestamp", "freshness_seconds", "cached", "degraded", "warnings"} <= set(meta)
