"""Gas tracker — real on-chain gas via RPCOneChainProvider (no mocks).

Provider supplies raw RPC values; this tool adds live USD conversion
(via tools.price) and gas levels, then wraps everything in the canonical envelope.
"""
from __future__ import annotations

import copy
import time
from typing import Any

from providers.base import make_envelope, make_error
from providers.onchain import NATIVE_SYMBOLS, RPCOneChainProvider

GAS_LIMITS = {
    "transfer": 21_000,
    "erc20_transfer": 65_000,
    "swap": 150_000,
    "deploy": 800_000,
}

CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
CACHE_TTL = 15


def _get_onchain_provider() -> RPCOneChainProvider:
    return RPCOneChainProvider()


def _gas_levels(base_gwei: float, priority_gwei: float) -> dict[str, dict[str, Any]]:
    return {
        "slow": {"gwei": round(base_gwei * 0.9 + priority_gwei * 0.5, 4), "est_time": "5-10 min"},
        "standard": {"gwei": round(base_gwei + priority_gwei, 4), "est_time": "2-5 min"},
        "fast": {"gwei": round(base_gwei * 1.15 + priority_gwei * 1.5, 4), "est_time": "<2 min"},
        "urgent": {"gwei": round(base_gwei * 1.3 + priority_gwei * 2.0, 4), "est_time": "<30 sec"},
    }


async def _native_price_usd(chain: str) -> tuple[float | None, list[str]]:
    symbol = f"{NATIVE_SYMBOLS.get(chain, 'ETH')}/USDT"
    try:
        from tools.price import get_price

        result = await get_price(symbol)
        if isinstance(result, dict) and result.get("data", {}).get("price_usd"):
            return float(result["data"]["price_usd"]), []
    except Exception as exc:
        return None, [f"native price unavailable for {symbol}: {exc}"]
    return None, [f"USD estimates skipped — no live price for {symbol}"]


async def gas_tracker(chain: str = "ethereum") -> dict[str, Any]:
    chain = (chain or "ethereum").lower()

    now = time.time()
    if chain in CACHE:
        ts, cached_payload = CACHE[chain]
        if (now - ts) < CACHE_TTL:
            payload = copy.deepcopy(cached_payload)
            payload["meta"]["cached"] = True
            payload["meta"]["freshness_seconds"] = round(now - ts, 1)
            return payload

    result = await _get_onchain_provider().fetch_gas(chain)
    if "error" in result:
        return result

    data, meta = result["data"], result["meta"]
    base_gwei = data["base_fee_gwei"]
    priority_gwei = data["priority_fee_gwei"]

    native_usd, usd_warnings = await _native_price_usd(chain)
    data["gas_levels"] = _gas_levels(base_gwei, priority_gwei)
    data["recommendation"] = "standard" if base_gwei < 30 else "slow"
    data["native_price_usd"] = native_usd
    data["estimated_tx_cost_usd"] = (
        {
            name: round(units * data["gas_price_gwei"] * 1e-9 * native_usd, 4)
            for name, units in GAS_LIMITS.items()
        }
        if native_usd is not None
        else None
    )

    meta["warnings"] = list(meta.get("warnings", [])) + usd_warnings
    meta["degraded"] = bool(meta["warnings"])

    payload = make_envelope(data, source=meta["source"], warnings=meta["warnings"])
    CACHE[chain] = (now, payload)
    return payload


async def estimate_tx_cost(
    chain: str = "ethereum",
    gas_units: int = 21000,
    speed: str = "standard",
) -> dict[str, Any]:
    gas = await gas_tracker(chain)
    if "error" in gas:
        return gas

    levels = gas["data"]["gas_levels"]
    if speed not in levels:
        return make_error(
            "BAD_SPEED",
            f"Unknown speed: {speed}",
            f"Use one of: {', '.join(levels.keys())}",
        )

    gwei = levels[speed]["gwei"]
    native_cost = gas_units * gwei * 1e-9
    usd_price = gas["data"].get("native_price_usd")
    cost_usd = round(native_cost * usd_price, 4) if usd_price else None

    operation_examples = {
        name: {
            "gas_units": units,
            "native": round(units * gwei * 1e-9, 8),
            "usd": round(units * gwei * 1e-9 * usd_price, 4) if usd_price else None,
        }
        for name, units in GAS_LIMITS.items()
    }

    data = {
        "chain": gas["data"]["chain"],
        "gas_units": gas_units,
        "gas_price_gwei": gwei,
        "speed": speed,
        "cost_in_native": round(native_cost, 8),
        "native_token": gas["data"]["native_token"],
        "cost_in_usd": cost_usd,
        "operation_examples": operation_examples,
    }
    meta = copy.deepcopy(gas["meta"])
    meta["warnings"] = list(meta.get("warnings", [])) + ["cost derived from live gas; USD uses current native price"]
    meta["degraded"] = bool(meta["warnings"])
    return {"data": data, "meta": meta}
