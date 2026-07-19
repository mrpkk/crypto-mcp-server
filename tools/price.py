import ccxt.async_support as ccxt
import httpx
from typing import Any
from datetime import datetime


EXCHANGE_NAMES = ["binance", "coinbase", "kraken", "bybit"]

FETCH_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def _get_exchange(name: str):
    cls = getattr(ccxt, name, None)
    if cls is None:
        return None
    return cls({"enableRateLimit": True, "options": {"defaultType": "spot"}})


async def get_price(symbol: str = "BTC/USDT", exchange: str = "binance") -> dict[str, Any]:
    if exchange not in EXCHANGE_NAMES:
        return {"error": f"Unsupported exchange: {exchange}. Use: {', '.join(EXCHANGE_NAMES)}"}

    now = datetime.utcnow()
    cache_key = f"{exchange}:{symbol}"

    if cache_key in FETCH_CACHE:
        ts, data = FETCH_CACHE[cache_key]
        if (now.timestamp() - ts) < 10:
            return data

    ex = _get_exchange(exchange)
    if ex is None:
        return {"error": f"Cannot create exchange client for {exchange}"}

    try:
        ticker = await ex.fetch_ticker(symbol)
        if ticker and ticker.get("last"):
            result = {
                "symbol": symbol,
                "exchange": exchange,
                "price_usd": ticker["last"],
                "change_24h": ticker.get("percentage"),
                "high_24h": ticker.get("high"),
                "low_24h": ticker.get("low"),
                "volume_24h_usd": ticker.get("quoteVolume"),
                "bid": ticker.get("bid"),
                "ask": ticker.get("ask"),
                "timestamp": datetime.fromtimestamp(ticker["timestamp"] / 1000).isoformat() if ticker.get("timestamp") else now.isoformat(),
            }
            FETCH_CACHE[cache_key] = (now.timestamp(), result)
            return result
        return {"error": f"No price data for {symbol} on {exchange}"}
    except Exception as e:
        return {"error": f"Failed to fetch {symbol}: {e}"}
    finally:
        await ex.close()


async def get_top_crypto(limit: int = 10) -> list[dict[str, Any]]:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                params={"vs_currency": "usd", "order": "volume_desc", "per_page": limit, "sparkline": "false"},
            )
            if resp.status_code != 200:
                raise Exception(f"CoinGecko returned {resp.status_code}")
            data = resp.json()
            return [
                {
                    "symbol": c["symbol"].upper() + "/USD",
                    "name": c["name"],
                    "price_usd": c["current_price"],
                    "change_24h": c["price_change_percentage_24h"],
                    "volume_24h_usd": c["total_volume"],
                    "market_cap": c["market_cap"],
                }
                for c in data
            ]
    except Exception as e:
        return [{"error": f"CoinGecko: {e}"}]


async def compare_prices(symbol: str = "BTC/USDT") -> list[dict[str, Any]]:
    results = []
    for name in ["binance", "coinbase", "kraken", "bybit"]:
        ex = _get_exchange(name)
        try:
            t = await ex.fetch_ticker(symbol)
            if t and t.get("last"):
                results.append({"exchange": name, "price": t["last"], "bid": t.get("bid"), "ask": t.get("ask")})
        except Exception:
            pass
        finally:
            await ex.close()

    if not results:
        return [{"error": f"No data for {symbol} on any exchange"}]
    results.append({
        "arbitrage": round(max(r["price"] for r in results) - min(r["price"] for r in results), 2),
        "best_bid": min((r for r in results if r.get("bid")), key=lambda r: r["bid"], default={}).get("bid"),
        "best_ask": min((r for r in results if r.get("ask")), key=lambda r: r["ask"], default={}).get("ask"),
    })
    return results
