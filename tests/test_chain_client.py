"""S2 tests: Web3Client RPC fallback behaviour."""

import pytest

from chain.client import CHAIN_RPC_FALLBACKS, Web3Client


def test_connect_with_fallback_picks_second(monkeypatch):
    good = CHAIN_RPC_FALLBACKS["ethereum"][1]
    monkeypatch.setattr(Web3Client, "is_connected", property(lambda self: self.rpc_url == good))

    client = Web3Client.connect_with_fallback(
        "ethereum", rpc_urls=["https://bad-rpc.example", good]
    )

    assert client.rpc_url == good


def test_connect_with_fallback_all_fail(monkeypatch):
    monkeypatch.setattr(Web3Client, "is_connected", property(lambda self: False))

    with pytest.raises(ConnectionError):
        Web3Client.connect_with_fallback(
            "ethereum", rpc_urls=["https://bad-1.example", "https://bad-2.example"]
        )


def test_fallback_lists_cover_all_supported_chains():
    for chain, urls in CHAIN_RPC_FALLBACKS.items():
        assert len(urls) >= 2, f"{chain} must have at least 2 RPC fallbacks"
