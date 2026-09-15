"""Role-based access control: tool-level permissions per tier (S4).

Tier model (SPEC): free (market+defi read), pro (+onchain read),
enterprise (+alerts write, admin). Enforcement is centralized here so
MCP/REST surfaces share one source of truth.
"""
from __future__ import annotations

from enum import Enum


class ToolPermission(Enum):
    READ_MARKET = "read:market"
    READ_DEFI = "read:defi"
    READ_ONCHAIN = "read:onchain"
    READ_INTELLIGENCE = "read:intelligence"
    WRITE_ALERT = "write:alert"
    ADMIN = "admin"


TOOL_TO_PERMISSION: dict[str, ToolPermission] = {
    # market
    "get_price": ToolPermission.READ_MARKET,
    "compare_prices": ToolPermission.READ_MARKET,
    "get_top_crypto": ToolPermission.READ_MARKET,
    # defi
    "get_yields": ToolPermission.READ_DEFI,
    "yield_assessment": ToolPermission.READ_DEFI,
    # market intelligence (reads market data + LLM)
    "technical_analysis": ToolPermission.READ_MARKET,
    "analyze_token": ToolPermission.READ_MARKET,
    "portfolio_health": ToolPermission.READ_MARKET,
    "trading_signal": ToolPermission.READ_INTELLIGENCE,
    "market_sentiment": ToolPermission.READ_INTELLIGENCE,
    # on-chain
    "gas_tracker": ToolPermission.READ_ONCHAIN,
    "estimate_tx_cost": ToolPermission.READ_ONCHAIN,
    "track_whale": ToolPermission.READ_ONCHAIN,
    "whale_alerts": ToolPermission.READ_ONCHAIN,
}

TIER_PERMISSIONS: dict[str, set[ToolPermission]] = {
    "free": {ToolPermission.READ_MARKET, ToolPermission.READ_DEFI},
    "pro": {
        ToolPermission.READ_MARKET,
        ToolPermission.READ_DEFI,
        ToolPermission.READ_ONCHAIN,
        ToolPermission.READ_INTELLIGENCE,
    },
    "enterprise": set(ToolPermission),  # всё, включая WRITE_ALERT/ADMIN
}


def permission_for_tool(tool_name: str) -> ToolPermission | None:
    return TOOL_TO_PERMISSION.get(tool_name)


def check_permission(tool_name: str, tier: str) -> bool:
    """True if the tier may call the tool. Unknown tools are denied."""
    permission = permission_for_tool(tool_name)
    if permission is None:
        return False
    return permission in TIER_PERMISSIONS.get(tier, set())


def tools_for_tier(tier: str) -> list[str]:
    allowed = TIER_PERMISSIONS.get(tier, set())
    return sorted(name for name, perm in TOOL_TO_PERMISSION.items() if perm in allowed)
