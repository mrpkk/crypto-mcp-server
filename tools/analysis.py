from typing import Any


async def analyze_token(
    symbol: str = "BTC",
    price_usd: float = 0,
    market_cap: float = 0,
    volume_24h: float = 0,
    supply: float = 0,
    ath: float = 0,
    atl: float = 0,
) -> dict[str, Any]:
    if price_usd <= 0:
        price_usd = _price(symbol)

    if market_cap <= 0:
        market_cap = _mc(symbol, price_usd)

    ath_val = ath or price_usd * _ath_mult(symbol)
    atl_val = atl or price_usd * _atl_mult(symbol)
    from_ath = ((price_usd - ath_val) / ath_val) * 100

    risk_score = _calc_risk(symbol, price_usd, market_cap)

    return {
        "symbol": symbol,
        "price_usd": price_usd,
        "market_cap": market_cap,
        "volume_24h": volume_24h or market_cap * 0.05,
        "circulating_supply": supply or _supply(symbol),
        "all_time_high": ath_val,
        "all_time_low": atl_val,
        "from_ath_pct": round(from_ath, 1),
        "market_dominance": round(_dominance(market_cap), 3),
        "risk_assessment": {
            "score": risk_score,
            "level": "low" if risk_score > 70 else "medium" if risk_score > 40 else "high",
            "factors": _risk_factors(symbol, risk_score),
        },
        "category": _category(symbol),
    }


async def portfolio_health(holdings: list[dict[str, float]]) -> dict[str, Any]:
    if not holdings:
        return {"error": "No holdings provided"}

    total_value = sum(h.get("value_usd", 0) for h in holdings)
    if total_value <= 0:
        return {"error": "Total portfolio value is 0"}

    asset_details = []
    for h in holdings:
        weight = (h.get("value_usd", 0) / total_value) * 100
        asset_details.append({
            "symbol": h.get("symbol", "unknown"),
            "value_usd": h.get("value_usd", 0),
            "weight_pct": round(weight, 1),
        })

    concentration = max(a["weight_pct"] for a in asset_details) if asset_details else 100
    diversity_score = min(100, len(holdings) * 15)

    return {
        "total_value_usd": round(total_value, 2),
        "assets": asset_details,
        "diversity_score": min(100, diversity_score),
        "concentration_risk": "high" if concentration > 50 else "medium" if concentration > 25 else "low",
        "top_holding_pct": round(concentration, 1),
        "suggested_allocation": _suggest_split(total_value),
    }


def _price(symbol: str) -> float:
    prices = {
        "BTC": 65000, "ETH": 3500, "SOL": 145, "BNB": 580,
        "XRP": 0.52, "ADA": 0.45, "DOGE": 0.12, "AVAX": 28,
        "DOT": 6.5, "LINK": 14, "ARB": 1.2, "OP": 2.8,
    }
    return prices.get(symbol.upper(), 10)

def _mc(symbol: str, price: float) -> float:
    supply_map = {"BTC": 19.7e6, "ETH": 120e6, "SOL": 440e6, "BNB": 155e6}
    s = supply_map.get(symbol.upper(), 1e9)
    return price * s

def _supply(symbol: str) -> float:
    return {"BTC": 19_700_000, "ETH": 120_000_000, "SOL": 440_000_000}.get(symbol.upper(), 1_000_000_000)

def _ath_mult(symbol: str) -> float:
    return {"BTC": 1.8, "ETH": 2.2, "SOL": 4.0, "BNB": 1.5}.get(symbol.upper(), 3.0)

def _atl_mult(symbol: str) -> float:
    return {"BTC": 0.02, "ETH": 0.01, "SOL": 0.005, "BNB": 0.01}.get(symbol.upper(), 0.05)

def _calc_risk(symbol: str, price: float, mc: float) -> int:
    base = {"ETH": 65, "BTC": 75, "SOL": 50, "BNB": 55}.get(symbol.upper(), 40)
    if mc > 10e9:
        base += 15
    elif mc > 1e9:
        base += 5
    return min(95, max(10, base))

def _risk_factors(symbol: str, score: int) -> list[str]:
    factors = []
    if score < 40:
        factors.append("Low liquidity")
        factors.append("High volatility")
    if symbol.upper() not in ("BTC", "ETH"):
        factors.append("Lower market cap")
    if score > 70:
        factors.append("Top 10 crypto by market cap")
    return factors if factors else ["Standard market risks"]

def _category(symbol: str) -> str:
    categories = {
        "BTC": "Store of Value / Layer 1",
        "ETH": "Smart Contract Platform",
        "SOL": "Smart Contract Platform",
        "BNB": "Exchange Token / Layer 1",
        "XRP": "Payment / Settlement",
        "LINK": "Oracle Network",
        "ARB": "Layer 2 Scaling",
        "OP": "Layer 2 Scaling",
    }
    return categories.get(symbol.upper(), "Token")

def _dominance(mc: float) -> float:
    total_mc = 2.5e12
    return (mc / total_mc) * 100

def _suggest_split(total: float) -> dict[str, float]:
    return {
        "btc_pct": 40,
        "eth_pct": 25,
        "large_cap_pct": 20,
        "defi_pct": 10,
        "stablecoins_pct": 5,
    }
