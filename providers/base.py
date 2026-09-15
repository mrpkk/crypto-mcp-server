"""Base provider abstractions + canonical envelope/error contracts (S3).

Single source of truth for response shapes:
  success -> {"data": {...}, "meta": {source, timestamp, freshness_seconds, cached, degraded, warnings}}
  failure -> {"error": {code, message, retryable, suggested_action}}
Every provider implements: capabilities(), health(), and a fetch operation with
timeout/retry/fallback policies handled by the implementation or its callers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

FRESHNESS_LIVE = 0


def make_envelope(
    data: dict[str, Any],
    source: str,
    warnings: list[str] | None = None,
    cached: bool = False,
    freshness: float = FRESHNESS_LIVE,
) -> dict[str, Any]:
    """Canonical success envelope. Every data tool must return this shape."""
    return {
        "data": data,
        "meta": {
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "freshness_seconds": freshness,
            "cached": cached,
            "degraded": bool(warnings),
            "warnings": warnings or [],
            "disclaimer": "Not financial advice.",
        },
    }


def make_error(code: str, message: str, suggestion: str, retryable: bool = False) -> dict[str, Any]:
    """Canonical error contract. Never raise raw exceptions to MCP/REST clients."""
    return {
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
            "suggested_action": suggestion,
        }
    }


class Provider(ABC):
    """Common provider surface: identity, capabilities, health."""

    name: str = "provider"

    @abstractmethod
    def capabilities(self) -> list[str]:
        """Machine-readable list of features this provider supports."""

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        """Availability info: at minimum {"provider", "status"} where status is ok|degraded|down."""


class MarketDataProvider(Provider):
    """Prices, tickers, OHLCV."""

    @abstractmethod
    async def fetch_price(self, symbol: str, exchange: str = "binance") -> dict[str, Any]:
        """Return a canonical envelope with the latest price."""


class OnChainProvider(Provider):
    """Gas, balances, blocks, transactions via RPC."""

    @abstractmethod
    async def fetch_gas(self, chain: str = "ethereum") -> dict[str, Any]:
        """Return a canonical envelope with gas info."""


class DefiProvider(Provider):
    """Yields, pools, protocol stats."""

    @abstractmethod
    async def fetch_yields(self, min_apy: float = 0, chain: str = "all") -> dict[str, Any]:
        """Return a canonical envelope with yield pools."""


class LLMProvider(ABC):
    """Interpretation layer. LLM is never a data source — only an interpreter."""

    name: str = "llm"

    @abstractmethod
    async def complete(self, system: str, user: str, temperature: float = 0.7) -> dict[str, Any]:
        """Return {"text": ..., "model": ...} or raise; callers apply fallback chain."""

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        """Availability info for the provider chain."""


class CacheProvider(ABC):
    """Hot/warm cache policy abstraction."""

    @abstractmethod
    def get(self, key: str) -> dict[str, Any] | None:
        """Return cached payload if fresh, else None."""

    @abstractmethod
    def set(self, key: str, payload: dict[str, Any], ttl: float) -> None:
        """Store payload with TTL."""
