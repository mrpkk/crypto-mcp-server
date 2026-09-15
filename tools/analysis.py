"""Token analysis & portfolio health — real inputs only, no hardcoded prices.

All market numbers come from live sources (CCXT via tools.price / CoinGecko global).
Missing inputs are reported as null with warnings instead of fabricated values.
"""

from __future__ import annotations

from typing import Any

import httpx

from providers.base import make_envelope, make_error

STABLES = {"USDT", "USDC", "DAI", "FDUSD", "TUSD"}

_CATEGORY = {
    "BTC": "Store of Value / Layer 1",
    "ETH": "Smart Contract Platform",
    "SOL": "Smart Contract Platform",
    "BNB": "Exchange Token / Layer 1",
    "XRP": "Payment / Settlement",
    "LINK": "Oracle Network",
    "ARB": "Layer 2 Scaling",
    "OP": "Layer 2 Scaling",
}


async def _fetch_price(symbol: str) -> float | None:
    try:
        from tools.price import get_price

        result = await get_price(f"{symbol.upper()}/USDT")
        if isinstance(result, dict) and result.get("data", {}).get("price_usd"):
            return float(result["data"]["price_usd"])
    except Exception:
        return None
    return None


async def _fetch_global_market_cap() -> float | None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get("https://api.coingecko.com/api/v3/global")
            if resp.status_code != 200:
                return None
            payload = resp.json()
        return float(payload["data"]["total_market_cap"]["usd"])
    except Exception:
        return None


def _risk_score(
    market_cap: float | None, volume_24h: float | None, from_ath: float | None
) -> int | None:
    if not market_cap:
        return None
    score = 40
    if market_cap > 100e9:
        score += 30
    elif market_cap > 10e9:
        score += 20
    elif market_cap > 1e9:
        score += 10
    if volume_24h:
        vol_ratio = volume_24h / market_cap
        if vol_ratio > 0.1:
            score += 10
        elif vol_ratio > 0.02:
            score += 5
        else:
            score -= 5
    if from_ath is not None and from_ath < -80:
        score -= 10
    return min(95, max(5, score))


async def analyze_token(
    symbol: str = "BTC",
    price_usd: float = 0,
    market_cap: float = 0,
    volume_24h: float = 0,
    supply: float = 0,
    ath: float = 0,
    atl: float = 0,
) -> dict[str, Any]:
    symbol = (symbol or "").upper()
    if not symbol:
        return make_error("BAD_SYMBOL", "Empty symbol", "Pass a token symbol, e.g. BTC")

    warnings: list[str] = []
    if price_usd <= 0:
        price_usd = await _fetch_price(symbol) or 0
        if price_usd <= 0:
            return make_error(
                "PRICE_UNAVAILABLE",
                f"No live price for {symbol}/USDT",
                "Check the symbol spelling or pass price_usd explicitly",
                retryable=True,
            )

    mc = market_cap if market_cap > 0 else None
    if mc is None:
        warnings.append("market_cap not provided — pass it or use a data provider for full metrics")

    volume = volume_24h if volume_24h > 0 else None
    if volume is None:
        warnings.append("volume_24h not provided")

    ath_val = ath if ath > 0 else None
    atl_val = atl if atl > 0 else None
    if ath_val is None:
        warnings.append("ath not provided — from_ath_pct unavailable")

    from_ath = round(((price_usd - ath_val) / ath_val) * 100, 1) if ath_val else None

    dominance = None
    if mc:
        total_mc = await _fetch_global_market_cap()
        if total_mc:
            dominance = round((mc / total_mc) * 100, 3)
        else:
            warnings.append("global market cap unavailable — dominance not computed")

    risk = _risk_score(mc, volume, from_ath)

    data = {
        "symbol": symbol,
        "price_usd": round(price_usd, 8),
        "market_cap": mc,
        "volume_24h": volume,
        "circulating_supply": supply if supply > 0 else None,
        "all_time_high": ath_val,
        "all_time_low": atl_val,
        "from_ath_pct": from_ath,
        "market_dominance_pct": dominance,
        "risk_assessment": {
            "score": risk,
            "level": None
            if risk is None
            else ("low" if risk > 70 else "medium" if risk > 40 else "high"),
            "factors": [] if risk is None else _risk_factors(symbol, risk),
            "methodology": "heuristic score from market cap, volume ratio and drawdown — not investment advice",
        },
        "category": _CATEGORY.get(symbol, "Token"),
    }
    return make_envelope(data, source="ccxt+coingecko", warnings=warnings)


def _risk_factors(symbol: str, score: int) -> list[str]:
    factors = []
    if score < 40:
        factors.append("Low liquidity")
        factors.append("High volatility")
    if symbol not in ("BTC", "ETH"):
        factors.append("Lower market cap")
    if score > 70:
        factors.append("Top 10 crypto by market cap")
    return factors if factors else ["Standard market risks"]


async def portfolio_health(holdings: list[dict[str, Any]]) -> dict[str, Any]:
    if not holdings:
        return make_error(
            "EMPTY_PORTFOLIO",
            "No holdings provided",
            "Pass holdings=[{symbol, amount} or {symbol, value_usd}]",
        )

    warnings: list[str] = []
    details: list[dict[str, Any]] = []
    for holding in holdings:
        symbol = str(holding.get("symbol") or "").upper()
        value = holding.get("value_usd")
        if value is None and holding.get("amount") and symbol:
            price = await _fetch_price(symbol)
            if price is None:
                warnings.append(
                    f"{symbol}: no live price — value skipped (pass value_usd to include it)"
                )
                continue
            value = float(holding["amount"]) * price
        if value is None:
            warnings.append(f"{symbol or '?'}: neither amount nor value_usd provided")
            continue
        details.append({"symbol": symbol or "?", "value_usd": round(float(value), 2)})

    total = sum(d["value_usd"] for d in details)
    if total <= 0:
        return make_error(
            "ZERO_VALUE",
            "Total portfolio value is 0",
            "Provide non-zero holdings with amount or value_usd",
        )

    for detail in details:
        detail["weight_pct"] = round(detail["value_usd"] / total * 100, 1)

    top = max(details, key=lambda d: d["weight_pct"])
    hhi = sum((d["weight_pct"] / 100) ** 2 for d in details)
    diversity = round(100 * (1 - hhi), 1)

    suggestions: list[str] = []
    if top["weight_pct"] > 50:
        suggestions.append(
            f"Top position {top['symbol']} is {top['weight_pct']}% — consider trimming for risk control"
        )
    if len(details) < 3:
        suggestions.append(f"Only {len(details)} asset(s) — diversification is limited")
    stable_pct = sum(d["weight_pct"] for d in details if d["symbol"] in STABLES)
    if stable_pct < 5:
        suggestions.append("Stablecoin buffer below 5% — consider dry powder for drawdowns")
    if not suggestions:
        suggestions.append("Allocation looks balanced by concentration metrics")

    data = {
        "total_value_usd": round(total, 2),
        "assets": details,
        "diversity_score": diversity,
        "concentration_risk": "high"
        if top["weight_pct"] > 50
        else "medium"
        if top["weight_pct"] > 25
        else "low",
        "top_holding_pct": top["weight_pct"],
        "suggestions": suggestions,
    }
    return make_envelope(data, source="live portfolio valuation", warnings=warnings)
