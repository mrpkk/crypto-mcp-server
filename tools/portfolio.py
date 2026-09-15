"""Portfolio Doctor v1 — concentration/risk/scenario analysis on real valuations.

Heuristic, deterministic, honest: every metric is computed from the live
portfolio valuation provided by the caller; no guarantees, no advice.
"""
from __future__ import annotations

from typing import Any

from providers.base import make_envelope
from tools.analysis import portfolio_health

STABLES = {"USDT", "USDC", "DAI", "FDUSD", "TUSD"}
MAX_POSITION_PCT = 40.0


async def portfolio_doctor(holdings: list[dict[str, Any]]) -> dict[str, Any]:
    health = await portfolio_health(holdings)
    if "error" in health:
        return health

    assets = health["data"]["assets"]
    total = health["data"]["total_value_usd"]
    risky = [a for a in assets if a["symbol"] not in STABLES]
    top = max(risky, key=lambda a: a["weight_pct"]) if risky else max(assets, key=lambda a: a["weight_pct"])
    top_risky_pct = top["weight_pct"] if risky else 0.0
    stable_pct = round(sum(a["weight_pct"] for a in assets if a["symbol"] in STABLES), 1)

    risk_score = _risk_score(top_risky_pct, stable_pct, len(risky))
    scenario = {
        "market_drop_30pct": {
            "estimated_value_usd": round(total * (1 - 0.30 * (1 - stable_pct / 100)), 2),
            "note": "линейная оценка: стейблкоины считаются устойчивыми",
        }
    }

    data = {
        "total_value_usd": total,
        "assets": assets,
        "diversification_score": health["data"]["diversity_score"],
        "concentration": {
            "top_symbol": top["symbol"],
            "top_pct": top["weight_pct"],
            "risk": health["data"]["concentration_risk"],
        },
        "stablecoin_buffer_pct": stable_pct,
        "risk_score": risk_score,
        "risk_level": "high" if risk_score >= 70 else "medium" if risk_score >= 40 else "low",
        "scenario": scenario,
        "rebalance_suggestions": _rebalance(assets),
        "methodology": "heuristics over live portfolio weights (HHI, 40% position cap) — not investment advice",
    }
    return make_envelope(data, source="portfolio doctor (live valuation)", warnings=health["meta"].get("warnings"))


def _risk_score(top_pct: float, stable_pct: float, asset_count: int) -> int:
    score = 30
    score += min(40, int(top_pct * 0.6))  # концентрация
    score += 10 if asset_count < 3 else 0
    score -= min(20, int(stable_pct * 0.6))  # буфер стабиков снижает риск
    return max(5, min(95, score))


def _rebalance(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    losers = [a for a in assets if a["weight_pct"] > MAX_POSITION_PCT]
    if not losers:
        return [{"note": f"все позиции ≤ {MAX_POSITION_PCT:.0f}% — rebalance не требуется"}]
    suggestions = []
    for asset in losers:
        suggestions.append(
            {
                "symbol": asset["symbol"],
                "current_pct": asset["weight_pct"],
                "suggested_max_pct": MAX_POSITION_PCT,
                "trim_pct": round(asset["weight_pct"] - MAX_POSITION_PCT, 1),
            }
        )
    return suggestions
