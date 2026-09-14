"""S2 tests: gas_tracker/estimate_tx_cost use real RPC data (no random, envelope, fallback)."""

import inspect

import pytest

import tools.gas as gas_module
from tools.gas import estimate_tx_cost, gas_tracker


@pytest.fixture(autouse=True)
def _clear_gas_cache():
    gas_module.CACHE.clear()
    yield
    gas_module.CACHE.clear()


class FakeWeb3Client:
    rpc_url = "https://fake-rpc.example"

    @classmethod
    def connect_with_fallback(cls, chain="ethereum", rpc_urls=None):
        return cls()

    def get_gas_info(self):
        return {
            "gas_price_wei": 30_000_000_000,
            "base_fee_wei": 25_000_000_000,
            "priority_fee_wei": 2_000_000_000,
            "supports_eip1559": True,
            "rpc_url": self.rpc_url,
        }


async def _fake_native_price(chain):
    return 3000.0, []


def test_no_random_in_source():
    source = inspect.getsource(gas_module)
    assert "random" not in source, "gas module must not use random"


@pytest.mark.asyncio
async def test_gas_tracker_envelope_and_values(monkeypatch):
    monkeypatch.setattr(gas_module, "Web3Client", FakeWeb3Client)
    monkeypatch.setattr(gas_module, "_native_price_usd", _fake_native_price)

    out = await gas_tracker("ethereum")

    assert "error" not in out
    data, meta = out["data"], out["meta"]
    assert data["chain"] == "ethereum"
    assert data["gas_price_gwei"] > 0
    assert data["base_fee_gwei"] == 25.0
    assert data["priority_fee_gwei"] == 2.0
    assert data["supports_eip1559"] is True
    assert set(data["gas_levels"]) == {"slow", "standard", "fast", "urgent"}
    assert data["estimated_tx_cost_usd"]["transfer"] > 0
    assert meta["source"].startswith("web3:")
    assert meta["cached"] is False
    assert meta["freshness_seconds"] == 0


@pytest.mark.asyncio
async def test_gas_tracker_cached_second_call(monkeypatch):
    monkeypatch.setattr(gas_module, "Web3Client", FakeWeb3Client)
    monkeypatch.setattr(gas_module, "_native_price_usd", _fake_native_price)

    first = await gas_tracker("base")
    second = await gas_tracker("base")

    assert first["meta"]["cached"] is False
    assert second["meta"]["cached"] is True
    assert second["meta"]["freshness_seconds"] >= 0


@pytest.mark.asyncio
async def test_gas_tracker_rpc_unavailable(monkeypatch):
    def _boom(chain="ethereum", rpc_urls=None):
        raise ConnectionError("all rpc failed")

    monkeypatch.setattr(gas_module.Web3Client, "connect_with_fallback", staticmethod(_boom))

    out = await gas_tracker("ethereum")

    assert out["error"]["code"] == "RPC_UNAVAILABLE"
    assert out["error"]["retryable"] is True
    assert "suggested_action" in out["error"]


@pytest.mark.asyncio
async def test_gas_tracker_unsupported_chain():
    out = await gas_tracker("dogechain")
    assert out["error"]["code"] == "UNSUPPORTED_CHAIN"
    assert "ethereum" in out["error"]["suggested_action"]


@pytest.mark.asyncio
async def test_estimate_tx_cost_uses_live_gas(monkeypatch):
    monkeypatch.setattr(gas_module, "Web3Client", FakeWeb3Client)
    monkeypatch.setattr(gas_module, "_native_price_usd", _fake_native_price)

    out = await estimate_tx_cost("ethereum", gas_units=21000, speed="standard")

    assert "error" not in out
    data = out["data"]
    assert data["gas_units"] == 21000
    assert data["cost_in_native"] > 0
    assert data["cost_in_usd"] > 0
    assert data["operation_examples"]["swap"]["gas_units"] == 150000
    assert out["meta"]["degraded"] is True


@pytest.mark.asyncio
async def test_estimate_tx_cost_bad_speed(monkeypatch):
    monkeypatch.setattr(gas_module, "Web3Client", FakeWeb3Client)
    monkeypatch.setattr(gas_module, "_native_price_usd", _fake_native_price)

    out = await estimate_tx_cost("ethereum", speed="rocket")

    assert out["error"]["code"] == "BAD_SPEED"


@pytest.mark.asyncio
async def test_gas_tracker_without_native_price(monkeypatch):
    async def _no_price(chain):
        return None, ["USD estimates skipped — no live price for ETH/USDT"]

    monkeypatch.setattr(gas_module, "Web3Client", FakeWeb3Client)
    monkeypatch.setattr(gas_module, "_native_price_usd", _no_price)

    out = await gas_tracker("ethereum")

    assert out["data"]["estimated_tx_cost_usd"] is None
    assert out["meta"]["degraded"] is True
    assert out["meta"]["warnings"]
