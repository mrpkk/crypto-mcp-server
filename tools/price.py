"""Market price tools — CCXT via pooled clients, canonical envelope responses."""
from __future__ import annotations

import asyncio
import copy
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from providers.base import make_envelope, make_error
from providers.market import ExchangePool

logger = logging.getLogger(__name__)

EXCHANGE_NAMES = ["binance", "coinbase", "kraken", "bybit"]

FETCH_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}

COINGECKO_MARKETS = "https://api.coingecko.com/api/v3/coins/markets"


def _get_exchange(name: str):
    """Pooled CCXT client (legacy hook kept for tests)."""
    return ExchangePool.get(name)


async def get_price(symbol: str = "BTC/USDT", exchange: str = "binance") -> dict[str, Any]:
    if exchange not in EXCHANGE_NAMES:
        return make_error(
            "UNSUPPORTED_EXCHANGE",
            f"Unsupported exchange: {exchange}",
            f"Use: {', '.join(EXCHANGE_NAMES)}",
        )

    now = datetime.now(timezone.utc)
    cache_key = f"{exchange}:{symbol}"

    if cache_key in FETCH_CACHE:
        ts, envelope = FETCH_CACHE[cache_key]
        if (now.timestamp() - ts) < 10:
            cached = copy.deepcopy(envelope)
            cached["meta"]["cached"] = True
            cached["meta"]["freshness_seconds"] = round(now.timestamp() - ts, 1)
            return cached

    ex = _get_exchange(exchange)
    if ex is None:
        return make_error(
            "UNSUPPORTED_EXCHANGE",
            f"Cannot create exchange client for {exchange}",
            f"Use: {', '.join(EXCHANGE_NAMES)}",
        )

    try:
        ticker = await ex.fetch_ticker(symbol)
    except Exception as exc:
        return make_error(
            "FETCH_FAILED",
            f"Failed to fetch {symbol}: {exc}",
            "Retry shortly or switch exchange",
            retryable=True,
        )

    if not ticker or not ticker.get("last"):
        return make_error(
            "NO_DATA",
            f"No price data for {symbol} on {exchange}",
            "Check the symbol spelling or pick another exchange",
        )

    data = {
        "symbol": symbol,
        "exchange": exchange,
        "price_usd": ticker["last"],
        "change_24h": ticker.get("percentage"),
        "high_24h": ticker.get("high"),
        "low_24h": ticker.get("low"),
        "volume_24h_usd": ticker.get("quoteVolume"),
        "bid": ticker.get("bid"),
        "ask": ticker.get("ask"),
        "timestamp": datetime.fromtimestamp(ticker["timestamp"] / 1000, tz=timezone.utc).isoformat()
        if ticker.get("timestamp")
        else now.isoformat(),
    }
    envelope = make_envelope(data, source=f"ccxt:{exchange}")
    FETCH_CACHE[cache_key] = (now.timestamp(), envelope)
    return envelope


async def get_top_crypto(limit: int = 10) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                COINGECKO_MARKETS,
                params={"vs_currency": "usd", "order": "volume_desc", "per_page": limit, "sparkline": "false"},
            )
            if resp.status_code != 200:
                raise RuntimeError(f"CoinGecko returned {resp.status_code}")
            payload = resp.json()
    except Exception as exc:
        return make_error(
            "COINGECKO_UNAVAILABLE",
            f"CoinGecko: {exc}",
            "Retry shortly — free API is rate limited",
            retryable=True,
        )

    items = [
        {
            "symbol": c["symbol"].upper() + "/USD",
            "name": c["name"],
            "price_usd": c["current_price"],
            "change_24h": c["price_change_percentage_24h"],
            "volume_24h_usd": c["total_volume"],
            "market_cap": c["market_cap"],
        }
        for c in payload
    ]
    return make_envelope({"items": items, "count": len(items)}, source="coingecko")


async def compare_prices(symbol: str = "BTC/USDT") -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    warnings: list[str] = []

    async def fetch_one(name: str):
        try:
            ex = _get_exchange(name)
            if ex is None:
                warnings.append(f"{name}: unsupported")
                return
            ticker = await asyncio.wait_for(ex.fetch_ticker(symbol), timeout=10)
            if ticker and ticker.get("last"):
                results.append(
                    {"exchange": name, "price": ticker["last"], "bid": ticker.get("bid"), "ask": ticker.get("ask")}
                )
            else:
                warnings.append(f"{name}: no data")
        except Exception as exc:
            logger.debug("ticker fetch failed for %s: %s", name, exc)
            warnings.append(f"{name}: {exc}")

    await asyncio.gather(*[fetch_one(n) for n in EXCHANGE_NAMES], return_exceptions=True)

    if not results:
        return make_error(
            "NO_DATA",
            f"No data for {symbol} on any exchange",
            "Retry later or check the symbol",
            retryable=True,
        )

    spread = round(max(r["price"] for r in results) - min(r["price"] for r in results), 2)
    bids = [r["bid"] for r in results if r.get("bid")]
    asks = [r["ask"] for r in results if r.get("ask")]
    data = {
        "symbol": symbol,
        "prices": results,
        "arbitrage_spread": spread,
        "best_bid": min(bids) if bids else None,
        "best_ask": min(asks) if asks else None,
    }
    return make_envelope(data, source="ccxt", warnings=warnings)
