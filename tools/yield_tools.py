"""DeFi yields — real DeFi Llama data only. Unavailable provider = honest error (no fabricated fallback)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from providers.base import make_envelope, make_error

DEFI_LLAMA_POOLS = "https://yields.llama.fi/pools"

DEFI_PROTOCOLS = [
    {"name": "Lido", "url": "https://api.lido.fi", "type": "liquid_staking"},
    {"name": "Aave", "url": "https://aave-api-v2.aave.com/data", "type": "lending"},
    {"name": "Uniswap", "url": "https://api.uniswap.org/v1", "type": "dex"},
    {"name": "Curve", "url": "https://api.curve.fi/api", "type": "stable_swap"},
    {"name": "Yearn", "url": "https://api.yearn.finance", "type": "yield_aggregator"},
    {"name": "Morpho", "url": "https://api.morpho.org", "type": "lending"},
    {"name": "EigenLayer", "url": "https://api.eigenlayer.xyz", "type": "restaking"},
]


async def get_yields(min_apy: float = 0, chain: str = "all", max_results: int = 20) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(DEFI_LLAMA_POOLS)
            if resp.status_code != 200:
                raise RuntimeError(f"DeFi Llama returned {resp.status_code}")
            payload = resp.json()
    except Exception as exc:
        return make_error(
            "DEFI_LLAMA_UNAVAILABLE",
            f"DeFi Llama pools request failed: {exc}",
            "Retry shortly — DeFi Llama is rate limited sometimes",
            retryable=True,
        )

    opportunities: list[dict[str, Any]] = []
    for pool in payload.get("data", [])[:100]:
        apy = pool.get("apy", 0) or pool.get("apyBase", 0) or 0
        pool_chain = pool.get("chain", "unknown").lower()

        if apy < min_apy:
            continue
        if chain != "all" and pool_chain != chain.lower():
            continue

        opportunities.append(
            {
                "protocol": pool.get("project", "unknown"),
                "pool": pool.get("symbol", pool.get("pool", "unknown")),
                "chain": pool_chain,
                "apy": round(apy, 2),
                "tvl_usd": round(pool.get("tvlUsd", 0) or 0),
                "apy_base": round(pool.get("apyBase", 0) or 0, 2),
                "apy_reward": round(pool.get("apyReward", 0) or 0, 2),
            }
        )

    opportunities.sort(key=lambda item: item["apy"], reverse=True)
    items = opportunities[:max_results]
    data = {
        "items": items,
        "count": len(items),
        "filters": {"min_apy": min_apy, "chain": chain},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return make_envelope(data, source="defillama")


async def get_protocol_info(name: str) -> dict[str, Any]:
    protocols_map = {p["name"].lower(): p for p in DEFI_PROTOCOLS}
    protocol = protocols_map.get(name.lower())
    if not protocol:
        return make_error(
            "PROTOCOL_NOT_FOUND",
            f"Protocol '{name}' not found",
            f"Available: {', '.join(p['name'] for p in DEFI_PROTOCOLS)}",
        )
    return make_envelope(protocol, source="static protocol registry")
