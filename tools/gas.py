import copy
import time
from datetime import datetime, timezone
from typing import Any

from chain.client import Web3Client

SUPPORTED_CHAINS = ("ethereum", "bsc", "polygon", "arbitrum", "optimism", "base")

NATIVE_SYMBOLS = {
    "ethereum": "ETH",
    "bsc": "BNB",
    "polygon": "POL",
    "arbitrum": "ETH",
    "optimism": "ETH",
    "base": "ETH",
}

GAS_LIMITS = {
    "transfer": 21_000,
    "erc20_transfer": 65_000,
    "swap": 150_000,
    "deploy": 800_000,
}

CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
CACHE_TTL = 15


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
    data: dict[str, Any], source: str, warnings: list[str] | None = None
) -> dict[str, Any]:
    return {
        "data": data,
        "meta": {
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "freshness_seconds": 0,
            "cached": False,
            "degraded": bool(warnings),
            "warnings": warnings or [],
        },
    }


def _gas_levels(base_gwei: float, priority_gwei: float) -> dict[str, dict[str, Any]]:
    return {
        "slow": {"gwei": round(base_gwei * 0.9 + priority_gwei * 0.5, 4), "est_time": "5-10 min"},
        "standard": {"gwei": round(base_gwei + priority_gwei, 4), "est_time": "2-5 min"},
        "fast": {"gwei": round(base_gwei * 1.15 + priority_gwei * 1.5, 4), "est_time": "<2 min"},
        "urgent": {"gwei": round(base_gwei * 1.3 + priority_gwei * 2.0, 4), "est_time": "<30 sec"},
    }


async def _native_price_usd(chain: str) -> tuple[float | None, list[str]]:
    symbol = f"{NATIVE_SYMBOLS[chain]}/USDT"
    try:
        from tools.price import get_price

        result = await get_price(symbol)
        if isinstance(result, dict) and result.get("price_usd"):
            return float(result["price_usd"]), []
    except Exception as exc:
        return None, [f"native price unavailable for {symbol}: {exc}"]
    return None, [f"USD estimates skipped — no live price for {symbol}"]


async def gas_tracker(chain: str = "ethereum") -> dict[str, Any]:
    chain = (chain or "ethereum").lower()
    if chain not in SUPPORTED_CHAINS:
        return _error(
            "UNSUPPORTED_CHAIN",
            f"Unsupported chain: {chain}",
            f"Use one of: {', '.join(SUPPORTED_CHAINS)}",
        )

    now = time.time()
    if chain in CACHE:
        ts, payload = CACHE[chain]
        if (now - ts) < CACHE_TTL:
            cached_payload = copy.deepcopy(payload)
            cached_payload["meta"]["cached"] = True
            cached_payload["meta"]["freshness_seconds"] = round(now - ts, 1)
            return cached_payload

    try:
        client = Web3Client.connect_with_fallback(chain)
        info = client.get_gas_info()
    except Exception as exc:
        return _error(
            "RPC_UNAVAILABLE",
            f"All RPC endpoints failed for {chain}: {exc}",
            "Retry in a few seconds or pick another chain",
            retryable=True,
        )

    base_gwei = info["base_fee_wei"] / 1e9
    priority_gwei = info["priority_fee_wei"] / 1e9
    gas_price_gwei = info["gas_price_wei"] / 1e9

    native_usd, warnings = await _native_price_usd(chain)

    cost_usd = None
    if native_usd is not None:
        cost_usd = {
            name: round(units * info["gas_price_wei"] / 1e18 * native_usd, 4)
            for name, units in GAS_LIMITS.items()
        }

    data = {
        "chain": chain,
        "gas_price_gwei": round(gas_price_gwei, 4),
        "base_fee_gwei": round(base_gwei, 4),
        "priority_fee_gwei": round(priority_gwei, 4),
        "supports_eip1559": info["supports_eip1559"],
        "gas_levels": _gas_levels(base_gwei, priority_gwei),
        "recommendation": "standard" if base_gwei < 30 else "slow",
        "native_token": NATIVE_SYMBOLS[chain],
        "native_price_usd": native_usd,
        "estimated_tx_cost_usd": cost_usd,
    }
    payload = _envelope(data, source=f"web3:{info['rpc_url']}", warnings=warnings)
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
        return _error(
            "BAD_SPEED",
            f"Unknown speed: {speed}",
            f"Use one of: {', '.join(levels.keys())}",
        )

    gwei = levels[speed]["gwei"]
    native_cost = gas_units * gwei * 1e-9
    usd_price = gas["data"].get("native_price_usd")
    cost_usd = round(native_cost * usd_price, 4) if usd_price else None

    native_symbol = gas["data"]["native_token"]
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
        "native_token": native_symbol,
        "cost_in_usd": cost_usd,
        "operation_examples": operation_examples,
    }
    meta = copy.deepcopy(gas["meta"])
    meta["warnings"] = list(meta.get("warnings", [])) + [
        "cost derived from live gas; USD uses current native price"
    ]
    meta["degraded"] = bool(meta["warnings"])
    return {"data": data, "meta": meta}
