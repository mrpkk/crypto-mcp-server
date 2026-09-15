"""Whale tracking providers. FREE implementation: Etherscan V2 multichain API.

Coverage note (honest limitations, per SPEC): the free tier indexes only the most
recent transactions per queried address — it is NOT a full-market whale feed.
"""

from __future__ import annotations

import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

ETHERSCAN_V2_URL = "https://api.etherscan.io/v2/api"

CHAIN_IDS = {
    "ethereum": 1,
    "bsc": 56,
    "polygon": 137,
    "arbitrum": 42161,
    "optimism": 10,
    "base": 8453,
}

NATIVE_SYMBOLS = {
    "ethereum": "ETH",
    "bsc": "BNB",
    "polygon": "POL",
    "arbitrum": "ETH",
    "optimism": "ETH",
    "base": "ETH",
}

ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")


@dataclass
class WhaleTransaction:
    tx_hash: str
    chain: str
    from_address: str
    to_address: str
    token_symbol: str
    amount: float
    amount_usd: float | None
    timestamp: str
    block_number: int
    source: str = "etherscan-v2"


class WhaleProvider(ABC):
    """Abstract interface for whale transaction data providers."""

    @abstractmethod
    async def get_transactions(
        self, address: str, chain: str = "ethereum", limit: int = 50
    ) -> list[WhaleTransaction]:
        """Recent native + token transfers for the address."""

    @abstractmethod
    async def get_alerts(
        self,
        addresses: list[str],
        chain: str = "ethereum",
        min_value_usd: float = 1_000_000,
        limit: int = 50,
    ) -> list[WhaleTransaction]:
        """Large transfers across the given addresses."""

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        """Provider availability info."""


class EtherscanWhaleProvider(WhaleProvider):
    """Free-tier provider backed by Etherscan V2 multichain API (one key, chainid param)."""

    def __init__(self, api_key: str | None = None, timeout: float = 10.0):
        self._api_key = api_key if api_key is not None else self._resolve_key()
        self._timeout = timeout

    @staticmethod
    def _resolve_key() -> str:
        try:
            from config import settings

            if settings.etherscan_api_key:
                return settings.etherscan_api_key
        except Exception as exc:
            logger.debug("config settings unavailable, falling back to env: %s", exc)
        return os.getenv("ETHERSCAN_API_KEY", "")

    @property
    def has_key(self) -> bool:
        return bool(self._api_key)

    async def _fetch(
        self, chain: str, action: str, address: str, limit: int
    ) -> list[dict[str, Any]]:
        if chain not in CHAIN_IDS:
            raise ValueError(f"Unsupported chain: {chain}. Use one of: {', '.join(CHAIN_IDS)}")
        params: dict[str, Any] = {
            "chainid": CHAIN_IDS[chain],
            "module": "account",
            "action": action,
            "address": address,
            "page": 1,
            "offset": max(1, min(limit, 100)),
            "sort": "desc",
        }
        if self._api_key:
            params["apikey"] = self._api_key
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(ETHERSCAN_V2_URL, params=params)
            resp.raise_for_status()
            payload = resp.json()
        result = payload.get("result")
        return result if isinstance(result, list) else []

    @staticmethod
    def _to_tx(item: dict[str, Any], chain: str, kind: str) -> WhaleTransaction | None:
        try:
            if kind == "native":
                symbol = NATIVE_SYMBOLS.get(chain, "ETH")
                decimals = 18
            else:
                symbol = item.get("tokenSymbol") or "?"
                decimals = int(item.get("tokenDecimal") or 18)
            raw_value = int(item.get("value") or 0)
            amount = raw_value / (10**decimals)
            ts = int(item.get("timeStamp") or 0)
            return WhaleTransaction(
                tx_hash=item.get("hash", ""),
                chain=chain,
                from_address=item.get("from", ""),
                to_address=item.get("to", ""),
                token_symbol=symbol.upper(),
                amount=amount,
                amount_usd=None,
                timestamp=datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else "",
                block_number=int(item.get("blockNumber") or 0),
            )
        except (TypeError, ValueError):
            return None

    async def get_transactions(
        self, address: str, chain: str = "ethereum", limit: int = 50
    ) -> list[WhaleTransaction]:
        native = await self._fetch(chain, "txlist", address, limit)
        tokens = await self._fetch(chain, "tokentx", address, limit)
        txs: list[WhaleTransaction] = []
        for item in native:
            tx = self._to_tx(item, chain, "native")
            if tx:
                txs.append(tx)
        for item in tokens:
            tx = self._to_tx(item, chain, "token")
            if tx:
                txs.append(tx)
        txs.sort(key=lambda t: t.block_number, reverse=True)
        return txs

    async def get_alerts(
        self,
        addresses: list[str],
        chain: str = "ethereum",
        min_value_usd: float = 1_000_000,
        limit: int = 50,
    ) -> list[WhaleTransaction]:
        collected: list[WhaleTransaction] = []
        for addr in addresses:
            collected.extend(await self.get_transactions(addr, chain, limit))
        return collected

    async def health(self) -> dict[str, Any]:
        return {
            "provider": "etherscan-v2",
            "status": "ok" if self.has_key else "degraded",
            "api_key_configured": self.has_key,
            "chains": sorted(CHAIN_IDS.keys()),
            "limitations": [
                "free tier: latest transactions per queried address only",
                "no full-market coverage: results depend on the addresses you query",
            ],
        }
