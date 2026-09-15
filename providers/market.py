"""CCXT market data provider backed by a process-wide exchange pool.

Why: the legacy code created and closed a CCXT client on every call
(price.py:64,104) — connection churn, slower responses, rate-limit pressure.
The pool keeps one client per exchange alive and closes them on shutdown.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

import ccxt.async_support as ccxt

from providers.base import MarketDataProvider, make_envelope, make_error

logger = logging.getLogger(__name__)

DEFAULT_EXCHANGES: tuple[str, ...] = ("binance", "coinbase", "kraken", "bybit")

_EXCHANGE_OPTIONS: dict[str, Any] = {
    "enableRateLimit": True,
    "timeout": 8000,
    "options": {"defaultType": "spot"},
}


class ExchangePool:
    """Process-wide singleton pool of CCXT async clients."""

    _instances: ClassVar[dict[str, Any]] = {}

    @classmethod
    def get(cls, name: str) -> Any | None:
        if name not in cls._instances:
            exchange_cls = getattr(ccxt, name, None)
            if exchange_cls is None:
                return None
            cls._instances[name] = exchange_cls(dict(_EXCHANGE_OPTIONS))
        return cls._instances[name]

    @classmethod
    async def close_all(cls) -> None:
        for name, exchange in list(cls._instances.items()):
            try:
                await exchange.close()
            except Exception as exc:
                logger.debug("exchange pool: close failed for %s: %s", name, exc)
        cls._instances.clear()

    @classmethod
    def size(cls) -> int:
        return len(cls._instances)


class CCXTMarketProvider(MarketDataProvider):
    name = "ccxt"

    def __init__(self, exchanges: tuple[str, ...] = DEFAULT_EXCHANGES):
        self.exchanges = exchanges

    def capabilities(self) -> list[str]:
        return ["price", "ticker", "compare_prices", *[f"exchange:{name}" for name in self.exchanges]]

    async def _ticker(self, name: str, symbol: str) -> Any:
        exchange = ExchangePool.get(name)
        if exchange is None:
            return None
        return await asyncio.wait_for(exchange.fetch_ticker(symbol), timeout=10)

    async def fetch_price(self, symbol: str = "BTC/USDT", exchange: str = "binance") -> dict[str, Any]:
        if exchange not in self.exchanges:
            return make_error(
                "UNSUPPORTED_EXCHANGE",
                f"Unknown exchange: {exchange}",
                f"Use one of: {', '.join(self.exchanges)}",
            )
        try:
            ticker = await self._ticker(exchange, symbol)
        except asyncio.TimeoutError:
            return make_error(
                "TIMEOUT",
                f"{exchange} did not respond within 10s",
                "Retry or switch exchange",
                retryable=True,
            )
        except Exception as exc:
            return make_error(
                "FETCH_FAILED",
                f"Failed to fetch {symbol} on {exchange}: {exc}",
                "Retry or switch exchange",
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
            "bid": ticker.get("bid"),
            "ask": ticker.get("ask"),
            "change_24h": ticker.get("percentage"),
            "volume_24h_usd": ticker.get("quoteVolume"),
        }
        return make_envelope(data, source=f"ccxt:{exchange}")

    async def compare(self, symbol: str = "BTC/USDT") -> dict[str, Any]:
        prices: list[dict[str, Any]] = []
        warnings: list[str] = []
        for name in self.exchanges:
            try:
                ticker = await self._ticker(name, symbol)
                if ticker and ticker.get("last"):
                    prices.append({"exchange": name, "price": ticker["last"], "bid": ticker.get("bid"), "ask": ticker.get("ask")})
                else:
                    warnings.append(f"{name}: no data")
            except Exception as exc:
                warnings.append(f"{name}: {exc}")
        if not prices:
            return make_error("NO_DATA", f"No data for {symbol} on any exchange", "Retry later")
        spread = round(max(p["price"] for p in prices) - min(p["price"] for p in prices), 2)
        data = {"symbol": symbol, "prices": prices, "arbitrage_spread": spread}
        return make_envelope(data, source="ccxt", warnings=warnings)

    async def health(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "status": "ok",
            "exchanges": list(self.exchanges),
            "pooled_clients": ExchangePool.size(),
        }
