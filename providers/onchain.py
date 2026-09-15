"""On-chain provider: Web3 RPC access with fallback, run off the event loop.

Sync web3.py calls are dispatched via asyncio.to_thread so the async runtime
(and MCP/REST concurrency) is never blocked by RPC latency.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

from chain.client import CHAIN_RPC_FALLBACKS, CHAIN_RPCS, Web3Client
from providers.base import OnChainProvider, make_envelope, make_error

logger = logging.getLogger(__name__)

NATIVE_SYMBOLS: ClassVar[dict[str, str]] = {
    "ethereum": "ETH",
    "bsc": "BNB",
    "polygon": "POL",
    "arbitrum": "ETH",
    "optimism": "ETH",
    "base": "ETH",
}


class RPCOneChainProvider(OnChainProvider):
    name = "web3"

    def __init__(self, default_chain: str = "ethereum"):
        self.default_chain = default_chain

    def capabilities(self) -> list[str]:
        return ["gas", "balance", "block", *[f"chain:{c}" for c in CHAIN_RPC_FALLBACKS]]

    async def fetch_gas(self, chain: str = "ethereum") -> dict[str, Any]:
        chain = (chain or self.default_chain).lower()
        if chain not in CHAIN_RPC_FALLBACKS:
            return make_error(
                "UNSUPPORTED_CHAIN",
                f"Unsupported chain: {chain}",
                f"Use one of: {', '.join(CHAIN_RPC_FALLBACKS)}",
            )
        try:
            client = await asyncio.to_thread(Web3Client.connect_with_fallback, chain)
            info = await asyncio.to_thread(client.get_gas_info)
        except Exception as exc:
            return make_error(
                "RPC_UNAVAILABLE",
                f"All RPC endpoints failed for {chain}: {exc}",
                "Retry in a few seconds or pick another chain",
                retryable=True,
            )
        data = {
            "chain": chain,
            "gas_price_gwei": round(info["gas_price_wei"] / 1e9, 4),
            "base_fee_gwei": round(info["base_fee_wei"] / 1e9, 4),
            "priority_fee_gwei": round(info["priority_fee_wei"] / 1e9, 4),
            "supports_eip1559": info["supports_eip1559"],
            "native_token": NATIVE_SYMBOLS.get(chain, "ETH"),
        }
        return make_envelope(data, source=f"web3:{info['rpc_url']}")

    async def fetch_balance(self, address: str, chain: str = "ethereum") -> dict[str, Any]:
        chain = (chain or self.default_chain).lower()
        if chain not in CHAIN_RPC_FALLBACKS:
            return make_error(
                "UNSUPPORTED_CHAIN",
                f"Unsupported chain: {chain}",
                f"Use one of: {', '.join(CHAIN_RPC_FALLBACKS)}",
            )
        try:
            client = await asyncio.to_thread(Web3Client.connect_with_fallback, chain)
            result = await asyncio.to_thread(client.get_balance, address)
        except Exception as exc:
            return make_error(
                "RPC_UNAVAILABLE",
                f"Balance fetch failed for {address} on {chain}: {exc}",
                "Check the address and retry",
                retryable=True,
            )
        return make_envelope(result, source=f"web3:{client.rpc_url}")

    async def health(self) -> dict[str, Any]:
        try:
            client = Web3Client(rpc_url=CHAIN_RPCS[self.default_chain])
            connected = await asyncio.to_thread(lambda: client.is_connected)
        except Exception as exc:
            logger.debug("onchain health probe failed: %s", exc)
            connected = False
        return {
            "provider": self.name,
            "status": "ok" if connected else "degraded",
            "default_chain": self.default_chain,
            "supported_chains": sorted(CHAIN_RPC_FALLBACKS),
        }
