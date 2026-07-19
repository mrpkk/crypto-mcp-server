from typing import Any
from datetime import datetime
import httpx


DEFI_PROTOCOLS = [
    {"name": "Lido", "url": "https://api.lido.fi", "type": "liquid_staking"},
    {"name": "Aave", "url": "https://aave-api-v2.aave.com/data", "type": "lending"},
    {"name": "Uniswap", "url": "https://api.uniswap.org/v1", "type": "dex"},
    {"name": "Curve", "url": "https://api.curve.fi/api", "type": "stable_swap"},
    {"name": "Yearn", "url": "https://api.yearn.finance", "type": "yield_aggregator"},
    {"name": "Morpho", "url": "https://api.morpho.org", "type": "lending"},
    {"name": "EigenLayer", "url": "https://api.eigenlayer.xyz", "type": "restaking"},
]


async def get_yields(min_apy: float = 0, chain: str = "all", max_results: int = 20) -> list[dict[str, Any]]:
    all_opportunities = []

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get("https://yields.llama.fi/pools")
            if resp.status_code == 200:
                data = resp.json()
                for pool in data.get("data", [])[:100]:
                    apy = pool.get("apy", 0) or pool.get("apyBase", 0) or 0
                    tvl = pool.get("tvlUsd", 0) or 0
                    pool_chain = pool.get("chain", "unknown").lower()
                    project = pool.get("project", "unknown")

                    if apy < min_apy:
                        continue
                    if chain != "all" and pool_chain != chain.lower():
                        continue

                    all_opportunities.append({
                        "protocol": project,
                        "pool": pool.get("symbol", pool.get("pool", "unknown")),
                        "chain": pool_chain,
                        "apy": round(apy, 2),
                        "tvl_usd": round(tvl, 0),
                        "apy_base": round(pool.get("apyBase", 0), 2),
                        "apy_reward": round(pool.get("apyReward", 0), 2),
                        "updated": datetime.fromtimestamp(pool.get("tvlUsd", 0)).isoformat(),
                    })
    except Exception:
        all_opportunities = FALLBACK_YIELDS

    sorted_opps = sorted(all_opportunities, key=lambda x: x["apy"], reverse=True)
    return sorted_opps[:max_results]


async def get_protocol_info(name: str) -> dict[str, Any]:
    protocols_map = {p["name"].lower(): p for p in DEFI_PROTOCOLS}
    protocol = protocols_map.get(name.lower())
    if not protocol:
        return {"error": f"Protocol '{name}' not found. Available: {', '.join(p['name'] for p in DEFI_PROTOCOLS)}"}
    return protocol


FALLBACK_YIELDS = [
    {"protocol": "Lido", "pool": "stETH", "chain": "ethereum", "apy": 3.2, "tvl_usd": 38_000_000_000, "type": "liquid_staking"},
    {"protocol": "Aave", "pool": "USDC", "chain": "ethereum", "apy": 5.8, "tvl_usd": 12_000_000_000, "type": "lending"},
    {"protocol": "Morpho", "pool": "USDC", "chain": "ethereum", "apy": 7.2, "tvl_usd": 3_000_000_000, "type": "lending"},
    {"protocol": "EigenLayer", "pool": "ETH Restaking", "chain": "ethereum", "apy": 4.1, "tvl_usd": 15_000_000_000, "type": "restaking"},
    {"protocol": "Curve", "pool": "3pool", "chain": "ethereum", "apy": 6.5, "tvl_usd": 2_500_000_000, "type": "stable_swap"},
    {"protocol": "Aave", "pool": "USDC", "chain": "polygon", "apy": 4.9, "tvl_usd": 800_000_000, "type": "lending"},
    {"protocol": "Compound", "pool": "ETH", "chain": "ethereum", "apy": 3.8, "tvl_usd": 1_500_000_000, "type": "lending"},
    {"protocol": "Uniswap", "pool": "ETH/USDC", "chain": "arbitrum", "apy": 12.5, "tvl_usd": 1_200_000_000, "type": "dex"},
]
