"""Whale tracking tools — real on-chain data via WhaleProvider (Etherscan V2). No mocks."""

from __future__ import annotations

import copy
import os
import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any

from providers.whale_provider import (
    ADDRESS_RE,
    EtherscanWhaleProvider,
    WhaleProvider,
    WhaleTransaction,
)

CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
CACHE_TTL = 60

STABLES = {"USDT": 1.0, "USDC": 1.0, "DAI": 1.0, "FDUSD": 1.0}

FREE_TIER_NOTE = (
    "etherscan free tier: latest transactions per queried address only — not a full-market feed"
)


def _get_provider() -> WhaleProvider:
    return EtherscanWhaleProvider()


def _error(code: str, message: str, suggestion: str, retryable: bool = False) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
            "suggested_action": suggestion,
        }
    }


def _envelope(
    data: dict[str, Any],
    source: str,
    warnings: list[str] | None = None,
    cached: bool = False,
    freshness: float = 0,
) -> dict[str, Any]:
    return {
        "data": data,
        "meta": {
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "freshness_seconds": freshness,
            "cached": cached,
            "degraded": bool(warnings),
            "warnings": warnings or [],
        },
    }


def _cache_lookup(key: str) -> dict[str, Any] | None:
    now = time.time()
    if key in CACHE:
        ts, payload = CACHE[key]
        if (now - ts) < CACHE_TTL:
            cached_payload = copy.deepcopy(payload)
            cached_payload["meta"]["cached"] = True
            cached_payload["meta"]["freshness_seconds"] = round(now - ts, 1)
            return cached_payload
    return None


def _cache_store(key: str, payload: dict[str, Any]) -> None:
    CACHE[key] = (time.time(), payload)


async def _symbol_price_usd(symbol: str) -> float | None:
    if symbol in STABLES:
        return STABLES[symbol]
    try:
        from tools.price import get_price

        result = await get_price(f"{symbol}/USDT")
        if isinstance(result, dict) and result.get("price_usd"):
            return float(result["price_usd"])
    except Exception:
        return None
    return None


async def _convert_usd(txs: list[WhaleTransaction]) -> list[str]:
    warnings: list[str] = []
    symbols = sorted({t.token_symbol for t in txs})
    prices: dict[str, float | None] = {}
    for sym in symbols:
        prices[sym] = await _symbol_price_usd(sym)
    missing = sorted(sym for sym, price in prices.items() if price is None)
    if missing:
        warnings.append(
            f"no live USD price for: {', '.join(missing)} — amount_usd is null for those"
        )
    for tx in txs:
        price = prices.get(tx.token_symbol)
        if price is not None:
            tx.amount_usd = round(tx.amount * price, 2)
    return warnings


def _provider_or_error() -> WhaleProvider | dict[str, Any]:
    provider = _get_provider()
    if not provider.has_key:
        return _error(
            "MISSING_API_KEY",
            "ETHERSCAN_API_KEY is not configured",
            "Add a free ETHERSCAN_API_KEY to ~/.env — without it Etherscan V2 returns no data",
        )
    return provider


async def track_whale(
    address: str = "",
    chain: str = "ethereum",
    min_value_usd: float = 100_000,
    limit: int = 25,
) -> dict[str, Any]:
    if not ADDRESS_RE.match(address or ""):
        return _error(
            "BAD_ADDRESS",
            f"Invalid EVM address: {address!r}",
            "Pass a 0x-prefixed 40-hex address, e.g. 0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        )

    provider = _provider_or_error()
    if isinstance(provider, dict):
        return provider

    cache_key = f"track:{chain}:{address.lower()}:{limit}"
    cached = _cache_lookup(cache_key)
    if cached:
        return cached

    try:
        txs = await provider.get_transactions(address, chain, limit)
    except Exception as exc:
        return _error(
            "PROVIDER_UNAVAILABLE",
            f"Etherscan request failed: {exc}",
            "Retry shortly — free tier is rate limited (~5 req/s)",
            retryable=True,
        )

    warnings = await _convert_usd(txs)
    kept = [t for t in txs if (t.amount_usd or 0) >= min_value_usd]
    skipped = len(txs) - len(kept)
    if skipped:
        warnings.append(f"{skipped} transfers below ${min_value_usd:,.0f} filtered out")
    warnings.append(FREE_TIER_NOTE)

    data = {
        "address": address,
        "chain": chain,
        "min_value_usd": min_value_usd,
        "transactions": [asdict(t) for t in kept],
        "count": len(kept),
    }
    payload = _envelope(data, source="etherscan-v2", warnings=warnings)
    _cache_store(cache_key, payload)
    return payload


async def whale_alerts(
    min_value_usd: float = 1_000_000,
    timeframe_hours: int = 24,
    addresses: list[str] | None = None,
    chain: str = "ethereum",
    limit: int = 25,
) -> dict[str, Any]:
    watchlist = addresses or [
        a.strip() for a in os.getenv("WHALE_WATCHLIST", "").split(",") if a.strip()
    ]
    if not watchlist:
        return _error(
            "NOT_CONFIGURED",
            "No watchlist addresses provided",
            "Pass addresses=[...] or set WHALE_WATCHLIST=0x...,0x... in ~/.env",
        )

    bad = [a for a in watchlist if not ADDRESS_RE.match(a)]
    if bad:
        return _error(
            "BAD_ADDRESS",
            f"Invalid EVM address(es): {', '.join(bad)}",
            "All addresses must be 0x-prefixed 40-hex",
        )

    provider = _provider_or_error()
    if isinstance(provider, dict):
        return provider

    cache_key = (
        f"alerts:{chain}:{','.join(a.lower() for a in watchlist)}:{min_value_usd}:{timeframe_hours}"
    )
    cached = _cache_lookup(cache_key)
    if cached:
        return cached

    try:
        txs = await provider.get_alerts(watchlist, chain, min_value_usd, limit)
    except Exception as exc:
        return _error(
            "PROVIDER_UNAVAILABLE",
            f"Etherscan request failed: {exc}",
            "Retry shortly — free tier is rate limited (~5 req/s)",
            retryable=True,
        )

    warnings = await _convert_usd(txs)
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=timeframe_hours)).isoformat()
    filtered = [
        t for t in txs if (t.timestamp or "") >= cutoff and (t.amount_usd or 0) >= min_value_usd
    ]
    filtered.sort(key=lambda t: t.amount_usd or 0, reverse=True)
    warnings.append(FREE_TIER_NOTE)

    data = {
        "chain": chain,
        "window_hours": timeframe_hours,
        "min_value_usd": min_value_usd,
        "addresses_checked": len(watchlist),
        "alerts": [asdict(t) for t in filtered[:limit]],
        "count": len(filtered[:limit]),
    }
    payload = _envelope(data, source="etherscan-v2", warnings=warnings)
    _cache_store(cache_key, payload)
    return payload
