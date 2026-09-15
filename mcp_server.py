"""Crypto MCP Server — 14 tools for any MCP-compatible AI agent (mcp>=2.0 API).

All tools return canonical envelopes (data + meta) serialized as JSON text,
or honest error contracts. No fabricated data anywhere in the tool chain.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from mcp.server.mcpserver import MCPServer

from ai.analyst import CryptoAnalyst
from config import settings
from providers.base import make_error
from tools.analysis import analyze_token, portfolio_health
from tools.gas import estimate_tx_cost, gas_tracker
from tools.price import compare_prices, get_price, get_top_crypto
from tools.signal import technical_indicators
from tools.whales import track_whale, whale_alerts
from tools.yield_tools import get_yields

logger = logging.getLogger(__name__)

analyst = CryptoAnalyst(api_key=settings.github_token)
analyst.fallback_key = settings.mistral_api_key

mcp = MCPServer("crypto-mcp", version="2.0.0")


def _dumps(payload: Any) -> str:
    return json.dumps(payload, indent=2, default=str)


async def _safe(coro) -> str:
    try:
        return _dumps(await coro)
    except Exception as exc:  # never leak raw exceptions to agents
        logger.exception("tool call failed")
        return _dumps(make_error("INTERNAL", str(exc), "Check the input parameters and retry"))


@mcp.tool(name="get_price", description="Get the latest price for a crypto pair on an exchange (CCXT).")
async def tool_get_price(symbol: str = "BTC/USDT", exchange: str = "binance") -> str:
    return await _safe(get_price(symbol=symbol, exchange=exchange))


@mcp.tool(name="compare_prices", description="Compare a pair across exchanges and compute the arbitrage spread.")
async def tool_compare_prices(symbol: str = "BTC/USDT") -> str:
    return await _safe(compare_prices(symbol=symbol))


@mcp.tool(name="get_top_crypto", description="Top cryptocurrencies by 24h volume with price, change and market cap.")
async def tool_get_top_crypto(limit: int = 10) -> str:
    return await _safe(get_top_crypto(limit=limit))


@mcp.tool(name="get_yields", description="DeFi yield pools from DeFi Llama filtered by chain and minimum APY.")
async def tool_get_yields(min_apy: float = 0, chain: str = "all", max_results: int = 20) -> str:
    return await _safe(get_yields(min_apy=min_apy, chain=chain, max_results=max_results))


@mcp.tool(name="technical_analysis", description="Technical indicators (RSI-14 Wilder, MACD, MA50/200, support/resistance) from real OHLCV.")
async def tool_technical_analysis(symbol: str = "BTC/USDT", price: float = 0, exchange: str = "binance") -> str:
    return await _safe(technical_indicators(symbol=symbol, price=price, exchange=exchange))


@mcp.tool(name="analyze_token", description="Token fundamentals with live price; metrics you did not provide are returned as null with warnings.")
async def tool_analyze_token(symbol: str = "BTC", price_usd: float = 0, market_cap: float = 0) -> str:
    return await _safe(analyze_token(symbol=symbol, price_usd=price_usd, market_cap=market_cap))


@mcp.tool(name="portfolio_health", description="Portfolio concentration/diversification from real holdings: [{symbol, amount} or {symbol, value_usd}].")
async def tool_portfolio_health(holdings: list[dict[str, Any]] | None = None) -> str:
    return await _safe(portfolio_health(holdings=holdings or []))


@mcp.tool(name="gas_tracker", description="Live gas prices for 6 EVM chains (Ethereum, BSC, Polygon, Arbitrum, Optimism, Base) with USD cost estimates.")
async def tool_gas_tracker(chain: str = "ethereum") -> str:
    return await _safe(gas_tracker(chain=chain))


@mcp.tool(name="estimate_tx_cost", description="Estimate transaction cost in native token and USD for a gas amount and speed.")
async def tool_estimate_tx_cost(chain: str = "ethereum", gas_units: int = 21000, speed: str = "standard") -> str:
    return await _safe(estimate_tx_cost(chain=chain, gas_units=gas_units, speed=speed))


@mcp.tool(name="market_sentiment", description="AI interpretation of market sentiment from the provided real inputs (LLM interpretation, not data).")
async def tool_market_sentiment(symbol: str = "BTC", price_change_24h: float = 0, volume_usd: float = 0) -> str:
    return await _safe(analyst.market_sentiment(symbol=symbol, price_change_24h=price_change_24h, volume_usd=volume_usd))


@mcp.tool(name="yield_assessment", description="AI assessment of a DeFi pool's risk/reward given protocol, APY, TVL and risk factors.")
async def tool_yield_assessment(protocol: str = "unknown", apy: float = 0, tvl: float = 0, risk_factors: list[str] | None = None) -> str:
    return await _safe(analyst.yield_assessment(protocol=protocol, apy=apy, tvl=tvl, risk_factors=risk_factors or []))


@mcp.tool(name="trading_signal", description="AI trading signal interpretation from indicators you provide (LLM interpretation, not financial advice).")
async def tool_trading_signal(symbol: str = "BTC/USDT", price: float = 0, rsi: float = 50, macd: str = "neutral", volume_trend: str = "stable") -> str:
    return await _safe(
        analyst.trading_signal(symbol=symbol, price=price, rsi=rsi, macd=macd, volume_trend=volume_trend)
    )


@mcp.tool(name="track_whale", description="Recent large transfers for an EVM address via Etherscan V2 (free tier: latest transactions only).")
async def tool_track_whale(address: str, chain: str = "ethereum", min_value_usd: float = 100000, limit: int = 25) -> str:
    return await _safe(track_whale(address=address, chain=chain, min_value_usd=min_value_usd, limit=limit))


@mcp.tool(name="whale_alerts", description="Large transfers across watchlist addresses (set WHALE_WATCHLIST in ~/.env or pass addresses).")
async def tool_whale_alerts(
    min_value_usd: float = 1000000,
    timeframe_hours: int = 24,
    addresses: list[str] | None = None,
    chain: str = "ethereum",
) -> str:
    return await _safe(
        whale_alerts(min_value_usd=min_value_usd, timeframe_hours=timeframe_hours, addresses=addresses, chain=chain)
    )


async def main() -> None:
    await mcp.run_stdio_async()


if __name__ == "__main__":
    asyncio.run(main())
