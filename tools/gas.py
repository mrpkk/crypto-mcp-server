import random
from datetime import datetime, timezone
from typing import Any


async def gas_tracker(chain: str = "ethereum") -> dict[str, Any]:
    chains_info = {
        "ethereum": {"base_fee": random.uniform(15, 60), "priority_fee": random.uniform(1, 5), "unit": "gwei"},
        "bsc": {"base_fee": random.uniform(2, 8), "priority_fee": random.uniform(0.1, 0.5), "unit": "gwei"},
        "polygon": {"base_fee": random.uniform(30, 120), "priority_fee": random.uniform(1, 10), "unit": "gwei"},
        "arbitrum": {"base_fee": random.uniform(0.1, 0.5), "priority_fee": random.uniform(0.01, 0.1), "unit": "gwei"},
        "optimism": {"base_fee": random.uniform(0.01, 0.1), "priority_fee": random.uniform(0.001, 0.01), "unit": "gwei"},
        "base": {"base_fee": random.uniform(0.01, 0.1), "priority_fee": random.uniform(0.001, 0.01), "unit": "gwei"},
    }

    chain = chain.lower()
    if chain not in chains_info:
        return {"error": f"Unsupported chain: {chain}. Supported: {', '.join(chains_info.keys())}"}

    info = chains_info[chain]
    base = info["base_fee"]
    priority = info["priority_fee"]

    return {
        "chain": chain,
        "gas_levels": {
            "slow": {"gwei": round(base * 0.9, 2), "est_time": "5-10 min"},
            "standard": {"gwei": round(base, 2), "est_time": "2-5 min"},
            "fast": {"gwei": round(base * 1.2 + priority, 2), "est_time": "<2 min"},
            "urgent": {"gwei": round(base * 1.5 + priority * 2, 2), "est_time": "<30 sec"},
        },
        "base_fee_gwei": round(base, 2),
        "priority_fee_gwei": round(priority, 2),
        "recommendation": "standard" if base < 30 else "slow",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def estimate_tx_cost(
    chain: str = "ethereum",
    gas_units: int = 21000,
    speed: str = "standard",
) -> dict[str, Any]:
    gas = await gas_tracker(chain)
    if "error" in gas:
        return gas

    price = gas["gas_levels"][speed]["gwei"] if speed in gas["gas_levels"] else gas["gas_levels"]["standard"]["gwei"]
    eth_cost = gas_units * price * 1e-9
    usd_per_eth = {"ethereum": 3500, "bsc": 580, "polygon": 0.45, "arbitrum": 1.2, "optimism": 2.8, "base": 2.8}

    return {
        "chain": chain,
        "gas_units": gas_units,
        "gas_price_gwei": price,
        "cost_in_native": round(eth_cost, 6),
        "cost_in_usd": round(eth_cost * usd_per_eth.get(chain, 100), 2),
        "speed": speed,
        "operation_examples": {
            "eth_transfer_21k": round(21000 * price * 1e-9 * usd_per_eth.get(chain, 100), 2),
            "erc20_transfer_65k": round(65000 * price * 1e-9 * usd_per_eth.get(chain, 100), 2),
            "swap_150k": round(150000 * price * 1e-9 * usd_per_eth.get(chain, 100), 2),
            "complex_tx_300k": round(300000 * price * 1e-9 * usd_per_eth.get(chain, 100), 2),
        },
    }
