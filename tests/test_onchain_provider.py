"""S3 tests: RPCOneChainProvider — gas/balance via RPC, off-loop, honest errors."""
import pytest

import providers.onchain as onchain_module
from providers.base import OnChainProvider
from providers.onchain import RPCOneChainProvider


class FakeClient:
    rpc_url = "https://fake-rpc.example"

    def __init__(self, chain="ethereum", rpc_url=None):
        self.rpc_url = rpc_url or "https://fake-rpc.example"

    @classmethod
    def connect_with_fallback(cls, chain="ethereum", rpc_urls=None):
        return cls(chain)

    def get_gas_info(self):
        return {
            "gas_price_wei": 20_000_000_000,
            "base_fee_wei": 18_000_000_000,
            "priority_fee_wei": 1_500_000_000,
            "supports_eip1559": True,
            "rpc_url": self.rpc_url,
        }

    def get_balance(self, address):
        return {"address": address, "balance_eth": 1.5, "chain": "ethereum"}

    @property
    def is_connected(self):
        return True


def test_provider_is_onchain_provider():
    assert isinstance(RPCOneChainProvider(), OnChainProvider)


def test_capabilities_shape():
    caps = RPCOneChainProvider().capabilities()
    assert "gas" in caps
    assert any(c.startswith("chain:") for c in caps)


@pytest.mark.asyncio
async def test_fetch_gas_unsupported_chain():
    out = await RPCOneChainProvider().fetch_gas("dogechain")
    assert out["error"]["code"] == "UNSUPPORTED_CHAIN"


@pytest.mark.asyncio
async def test_fetch_gas_envelope(monkeypatch):
    monkeypatch.setattr(onchain_module, "Web3Client", FakeClient)

    out = await RPCOneChainProvider().fetch_gas("ethereum")

    data, meta = out["data"], out["meta"]
    assert data["chain"] == "ethereum"
    assert data["base_fee_gwei"] == 18.0
    assert data["priority_fee_gwei"] == 1.5
    assert data["supports_eip1559"] is True
    assert data["native_token"] == "ETH"
    assert meta["source"].startswith("web3:")


@pytest.mark.asyncio
async def test_fetch_gas_rpc_down(monkeypatch):
    class BrokenClient(FakeClient):
        @classmethod
        def connect_with_fallback(cls, chain="ethereum", rpc_urls=None):
            raise ConnectionError("all rpc failed")

    monkeypatch.setattr(onchain_module, "Web3Client", BrokenClient)

    out = await RPCOneChainProvider().fetch_gas("ethereum")

    assert out["error"]["code"] == "RPC_UNAVAILABLE"
    assert out["error"]["retryable"] is True


@pytest.mark.asyncio
async def test_fetch_balance_envelope(monkeypatch):
    monkeypatch.setattr(onchain_module, "Web3Client", FakeClient)

    out = await RPCOneChainProvider().fetch_balance("0x742d35Cc6634C0532925a3b844Bc454e4438f44e")

    assert out["data"]["balance_eth"] == 1.5
    assert out["meta"]["source"].startswith("web3:")


@pytest.mark.asyncio
async def test_health_ok(monkeypatch):
    monkeypatch.setattr(onchain_module, "Web3Client", FakeClient)

    health = await RPCOneChainProvider().health()

    assert health["status"] == "ok"
    assert "ethereum" in health["supported_chains"]
