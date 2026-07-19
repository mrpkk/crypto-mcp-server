from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from typing import Any
import asyncio
import json

from config import settings
from ai.analyst import CryptoAnalyst
from chain.client import get_client
from tools.price import get_price, get_top_crypto, compare_prices
from tools.yield_tools import get_yields, get_protocol_info
from tools.signal import technical_indicators
from tools.analysis import analyze_token, portfolio_health
from tools.gas import gas_tracker, estimate_tx_cost
from tools.whales import track_whale, whale_alerts

analyst = CryptoAnalyst(api_key=settings.github_token)
analyst.fallback_key = settings.mistral_api_key

server = Server("crypto-mcp")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_price",
            description="Get real-time cryptocurrency price from major exchanges",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Trading pair (e.g. BTC/USDT, ETH/USDT)", "default": "BTC/USDT"},
                    "exchange": {"type": "string", "description": "Exchange (binance, coinbase, kraken)", "default": "binance"},
                },
            },
        ),
        Tool(
            name="compare_prices",
            description="Compare prices across multiple exchanges to find arbitrage opportunities",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Trading pair to compare", "default": "BTC/USDT"},
                },
            },
        ),
        Tool(
            name="get_top_crypto",
            description="Get top cryptocurrencies by volume",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "number", "description": "Number of results", "default": 10},
                },
            },
        ),
        Tool(
            name="get_yields",
            description="Find best DeFi yield opportunities across protocols and chains",
            inputSchema={
                "type": "object",
                "properties": {
                    "min_apy": {"type": "number", "description": "Minimum APY filter", "default": 0},
                    "chain": {"type": "string", "description": "Filter by chain (ethereum, bsc, polygon, arbitrum, or 'all')", "default": "all"},
                    "max_results": {"type": "number", "description": "Max results", "default": 20},
                },
            },
        ),
        Tool(
            name="technical_analysis",
            description="Get technical indicators (RSI, MACD, MA) for a trading pair",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Trading pair", "default": "BTC/USDT"},
                    "price": {"type": "number", "description": "Current price (optional)", "default": 0},
                },
            },
        ),
        Tool(
            name="analyze_token",
            description="Deep token analysis with risk assessment and market positioning",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Token symbol (e.g. BTC, ETH, SOL)", "default": "BTC"},
                    "price_usd": {"type": "number", "description": "Current price (optional)", "default": 0},
                    "market_cap": {"type": "number", "description": "Market cap (optional)", "default": 0},
                },
            },
        ),
        Tool(
            name="portfolio_health",
            description="Analyze portfolio health, diversity, and get allocation suggestions",
            inputSchema={
                "type": "object",
                "properties": {
                    "holdings": {
                        "type": "array",
                        "description": "List of holdings with symbol and value_usd",
                        "items": {
                            "type": "object",
                            "properties": {
                                "symbol": {"type": "string"},
                                "value_usd": {"type": "number"},
                            },
                        },
                    },
                },
            },
        ),
        Tool(
            name="gas_tracker",
            description="Get current gas prices for any EVM chain with recommendations",
            inputSchema={
                "type": "object",
                "properties": {
                    "chain": {"type": "string", "description": "Chain name (ethereum, bsc, polygon, arbitrum, optimism, base)", "default": "ethereum"},
                },
            },
        ),
        Tool(
            name="estimate_tx_cost",
            description="Estimate transaction cost in USD for different operation types",
            inputSchema={
                "type": "object",
                "properties": {
                    "chain": {"type": "string", "description": "Chain name", "default": "ethereum"},
                    "gas_units": {"type": "number", "description": "Gas units for the transaction", "default": 21000},
                    "speed": {"type": "string", "description": "Speed (slow, standard, fast, urgent)", "default": "standard"},
                },
            },
        ),
        Tool(
            name="market_sentiment",
            description="AI-powered market sentiment analysis with Mistral AI",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Token symbol", "default": "BTC"},
                    "price_change_24h": {"type": "number", "description": "24h price change percent", "default": 0},
                    "volume_usd": {"type": "number", "description": "24h volume in USD", "default": 0},
                },
            },
        ),
        Tool(
            name="yield_assessment",
            description="AI-powered DeFi yield opportunity assessment",
            inputSchema={
                "type": "object",
                "properties": {
                    "protocol": {"type": "string", "description": "Protocol name"},
                    "apy": {"type": "number", "description": "APY percentage"},
                    "tvl": {"type": "number", "description": "Total Value Locked in USD"},
                    "risk_factors": {"type": "array", "items": {"type": "string"}, "description": "Risk factors"},
                },
            },
        ),
        Tool(
            name="trading_signal",
            description="AI-generated trading signal with technical + sentiment analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Trading pair", "default": "BTC/USDT"},
                    "price": {"type": "number", "description": "Current price", "default": 0},
                    "rsi": {"type": "number", "description": "RSI value", "default": 50},
                    "macd": {"type": "string", "description": "MACD status", "default": "neutral"},
                    "volume_trend": {"type": "string", "description": "Volume trend", "default": "stable"},
                    "news": {"type": "array", "items": {"type": "string"}, "description": "Recent news headlines"},
                },
            },
        ),
        Tool(
            name="track_whale",
            description="Track a whale wallet's holdings and recent activity",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {"type": "string", "description": "Wallet address (optional)"},
                },
            },
        ),
        Tool(
            name="whale_alerts",
            description="Get recent large transactions and whale movements",
            inputSchema={
                "type": "object",
                "properties": {
                    "min_value_usd": {"type": "number", "description": "Minimum transaction value in USD", "default": 1_000_000},
                    "timeframe_hours": {"type": "number", "description": "Lookback period in hours", "default": 24},
                },
            },
        ),
    ]


async def _safe_call(func, *args, **kwargs) -> str:
    try:
        result = await func(*args, **kwargs)
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent | ImageContent | EmbeddedResource]:
    args = arguments or {}

    handlers = {
        "get_price": lambda: get_price(
            symbol=args.get("symbol", "BTC/USDT"),
            exchange=args.get("exchange", "binance"),
        ),
        "compare_prices": lambda: compare_prices(symbol=args.get("symbol", "BTC/USDT")),
        "get_top_crypto": lambda: get_top_crypto(limit=int(args.get("limit", 10))),
        "get_yields": lambda: get_yields(
            min_apy=float(args.get("min_apy", 0)),
            chain=args.get("chain", "all"),
            max_results=int(args.get("max_results", 20)),
        ),
        "technical_analysis": lambda: technical_indicators(
            symbol=args.get("symbol", "BTC/USDT"),
            price=float(args.get("price", 0)),
        ),
        "analyze_token": lambda: analyze_token(
            symbol=args.get("symbol", "BTC"),
            price_usd=float(args.get("price_usd", 0)),
            market_cap=float(args.get("market_cap", 0)),
        ),
        "portfolio_health": lambda: portfolio_health(holdings=args.get("holdings", [])),
        "gas_tracker": lambda: gas_tracker(chain=args.get("chain", "ethereum")),
        "estimate_tx_cost": lambda: estimate_tx_cost(
            chain=args.get("chain", "ethereum"),
            gas_units=int(args.get("gas_units", 21000)),
            speed=args.get("speed", "standard"),
        ),
        "market_sentiment": lambda: analyst.market_sentiment(
            symbol=args.get("symbol", "BTC"),
            price_change_24h=float(args.get("price_change_24h", 0)),
            volume_usd=float(args.get("volume_usd", 0)),
        ),
        "yield_assessment": lambda: analyst.yield_assessment(
            protocol=args.get("protocol", "unknown"),
            apy=float(args.get("apy", 0)),
            tvl=float(args.get("tvl", 0)),
            risk_factors=args.get("risk_factors", []),
        ),
        "trading_signal": lambda: analyst.trading_signal(
            symbol=args.get("symbol", "BTC/USDT"),
            price=float(args.get("price", 0)),
            rsi=float(args.get("rsi", 50)),
            macd=args.get("macd", "neutral"),
            volume_trend=args.get("volume_trend", "stable"),
            news=args.get("news", []),
        ),
        "track_whale": lambda: track_whale(address=args.get("address", "")),
        "whale_alerts": lambda: whale_alerts(
            min_value_usd=float(args.get("min_value_usd", 1_000_000)),
            timeframe_hours=int(args.get("timeframe_hours", 24)),
        ),
    }

    handler = handlers.get(name)
    if not handler:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    text = await _safe_call(handler)
    return [TextContent(type="text", text=text)]


async def main():
    async with server.run_stdio() as running:
        await running.stopped


if __name__ == "__main__":
    asyncio.run(main())
