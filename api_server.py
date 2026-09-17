#!/usr/bin/env python3
"""Crypto MCP Server — REST API wrapper with Swagger UI."""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ai.analyst import CryptoAnalyst
from alerts import evaluate_rules
from auth.keys import APIKeyStore
from config import settings
from observability import configure_json_logging, metrics
from providers.base import make_error
from rate_limit import EXEMPT_PATHS, RateLimiter, client_identity, limit_for_tier
from tools.analysis import analyze_token, portfolio_health
from tools.gas import estimate_tx_cost, gas_tracker
from tools.price import compare_prices, get_price, get_top_crypto
from tools.signal import technical_indicators
from tools.whales import track_whale, whale_alerts
from tools.yield_tools import get_yields
from watchlists import WatchlistStore


def _read_version() -> str:
    """Single source of truth: pyproject.toml (fallback: installed metadata)."""
    try:
        import tomllib

        pyproject = Path(__file__).parent / "pyproject.toml"
        if pyproject.exists():
            with pyproject.open("rb") as fh:
                return tomllib.load(fh)["project"]["version"]
    except Exception as exc:
        logging.getLogger(__name__).debug("pyproject version read failed: %s", exc)
    try:
        return pkg_version("crypto-mcp-server")
    except PackageNotFoundError:
        return "unknown"


APP_VERSION = _read_version()

analyst = CryptoAnalyst(api_key=settings.github_token)
analyst.fallback_key = settings.mistral_api_key

app = FastAPI(
    title="💰 Crypto & DeFi Intelligence Server",
    description=(
        "**14 инструментов для крипто-аналитики**\n\n"
        "**Возможности:**\n"
        "• 💰 Real-time цены с бирж (Binance, Coinbase, Kraken, Bybit)\n"
        "• ⚖️ Сравнение цен между биржами (арбитраж)\n"
        "• 📊 Технический анализ (RSI, MACD, скользящие средние)\n"
        "• 📈 DeFi Yields (Aave, Compound, Lido, Curve, и др.)\n"
        "• ⛽ Gas tracker (Ethereum, BSC, Polygon, Arbitrum, Optimism, Base)\n"
        "• 🐋 Whale alerts (крупные транзакции)\n"
        "• 🧠 AI сентимент и торговые сигналы через Mistral AI\n"
        "• 🔍 Глубокий анализ токенов\n\n"
        "🔌 REST API + MCP Protocol + Swagger UI"
    ),
    version=APP_VERSION,
)
_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

WEB_DIR = Path(__file__).parent / "web"

app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

rate_limiter = RateLimiter()
api_key_store = APIKeyStore(settings.db_path)
watchlist_store = WatchlistStore(settings.db_path)


@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    if request.url.path in EXEMPT_PATHS:
        return await call_next(request)
    api_key = request.headers.get("x-api-key")
    identity = client_identity(dict(request.headers), request.client.host if request.client else None)
    if api_key:
        key_info = api_key_store.verify(api_key)
        if key_info is None:
            return JSONResponse(
                make_error(
                    "INVALID_API_KEY",
                    "The provided API key is unknown or revoked",
                    "Create a new key via /admin/keys (owner) or drop the x-api-key header for free anonymous access",
                ),
                status_code=401,
            )
        tier = key_info["tier"]
        api_key_store.record_usage(api_key, request.url.path)
    else:
        tier = "free"
    limit = limit_for_tier(tier)
    decision = rate_limiter.check(identity, limit)
    if not decision.allowed:
        return JSONResponse(
            make_error(
                "RATE_LIMITED",
                f"Rate limit exceeded ({limit} requests/hour, tier '{tier}')",
                "Retry after the window resets or use a higher tier key",
                retryable=True,
            ),
            status_code=429,
            headers={
                "Retry-After": str(int(decision.reset_after) + 1),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
            },
        )
    start = time.perf_counter()
    response = await call_next(request)
    latency = time.perf_counter() - start
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    response.headers["X-Request-ID"] = request_id
    metrics.inc("http_requests_total", {"path": request.url.path, "status": str(response.status_code)})
    metrics.observe_latency("http_request_latency_seconds", latency, {"path": request.url.path})
    return response


# LEGACY_DASHBOARD_REMOVED: replaced by web/ static dashboard (S6)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Āgama dashboard (static web/ app)."""
    return FileResponse(WEB_DIR / "index.html")





class WatchlistItemIn(BaseModel):
    kind: str
    value: str
    label: str = ""


class AlertRuleIn(BaseModel):
    kind: str
    params: dict


@app.get("/watchlist")
async def watchlist_list():
    return {"items": watchlist_store.list()}


@app.post("/watchlist", status_code=201)
async def watchlist_add(item: WatchlistItemIn):
    try:
        item_id = watchlist_store.add(item.kind, item.value, item.label)
    except ValueError as exc:
        return make_error("BAD_KIND", str(exc), "kind must be asset|wallet|protocol")
    return {"id": item_id}


@app.delete("/watchlist/{item_id}", status_code=204)
async def watchlist_remove(item_id: int):
    if not watchlist_store.remove(item_id):
        return make_error("NOT_FOUND", f"watchlist item {item_id} not found", "List items via GET /watchlist")
    return None


@app.get("/alerts")
async def alerts_list():
    return {"rules": watchlist_store.list_rules()}


@app.post("/alerts", status_code=201)
async def alerts_add(rule: AlertRuleIn):
    try:
        rule_id = watchlist_store.add_rule(rule.kind, rule.params)
    except ValueError as exc:
        return make_error("BAD_KIND", str(exc), "kind must be price_move|gas_below|whale_above")
    return {"id": rule_id}


@app.delete("/alerts/{rule_id}", status_code=204)
async def alerts_remove(rule_id: int):
    if not watchlist_store.remove_rule(rule_id):
        return make_error("NOT_FOUND", f"rule {rule_id} not found", "List rules via GET /alerts")
    return None


@app.post("/alerts/check")
async def alerts_check():
    """Evaluate enabled rules against LIVE tools. Every alert explains WHY IT MATTERS."""
    return await evaluate_rules(watchlist_store.list_rules())


@app.get("/stream/prices")
async def stream_prices(symbols: str = "BTC/USDT,ETH/USDT,SOL/USDT", interval: float = 15, once: int = 0):
    """Server-Sent Events stream of live prices. `once=1` returns a single batch (for tests/scripts)."""
    from fastapi.responses import StreamingResponse

    async def generator():
        while True:
            for symbol in [s.strip() for s in symbols.split(",") if s.strip()]:
                envelope = await get_price(symbol=symbol)
                yield f"event: price\ndata: {json.dumps(envelope, default=str)}\n\n"
            if once:
                break
            await asyncio.sleep(interval)

    return StreamingResponse(generator(), media_type="text/event-stream")


@app.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    """Prometheus-compatible metrics (text exposition format)."""
    return metrics.render_prometheus()


@app.get("/health")
async def health():
    """Liveness probe: process is up."""
    return {"status": "ok", "version": APP_VERSION, "timestamp": datetime.now(timezone.utc).isoformat()}


async def _collect_provider_health() -> dict:
    from providers.market import CCXTMarketProvider
    from providers.onchain import RPCOneChainProvider

    checks: dict = {}
    try:
        checks["market"] = await CCXTMarketProvider().health()
    except Exception as exc:
        checks["market"] = {"provider": "ccxt", "status": "down", "error": str(exc)}
    try:
        checks["onchain"] = await RPCOneChainProvider().health()
    except Exception as exc:
        checks["onchain"] = {"provider": "web3", "status": "down", "error": str(exc)}
    llm_configured = bool(analyst.api_key or analyst.fallback_key)
    checks["llm"] = {"provider": "github_models+mistral", "status": "ok" if llm_configured else "degraded"}
    return checks


@app.get("/ready")
async def ready():
    """Readiness probe: critical dependencies reachable (degraded allowed)."""
    from fastapi.responses import JSONResponse

    checks = await _collect_provider_health()
    all_ok = all(check.get("status") in ("ok", "degraded") for check in checks.values())
    payload = {
        "status": "ready" if all_ok else "not_ready",
        "checks": checks,
        "version": APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return JSONResponse(payload, status_code=200 if all_ok else 503)


@app.get("/version")
async def version():
    return {"version": APP_VERSION, "api": "v2", "mcp": "mcp>=1.0"}


@app.get("/capabilities")
async def capabilities():
    from mcp_server import mcp

    tools = await mcp.list_tools()
    return {
        "version": APP_VERSION,
        "tools": [{"name": t.name, "description": t.description} for t in tools],
        "tool_count": len(tools),
        "providers": await _collect_provider_health(),
    }


@app.get("/price/compare/{symbol:path}")
async def api_compare_prices(symbol: str = "BTC/USDT"):
    return await compare_prices(symbol=symbol)


@app.get("/price/{symbol:path}")
async def api_get_price(symbol: str = "BTC/USDT", exchange: str = "binance"):
    result = await get_price(symbol=symbol, exchange=exchange)
    # Алиасы для дашборда — внутри envelope.data
    data = result.get("data") if isinstance(result, dict) else None
    if isinstance(data, dict):
        if "price_usd" in data and "price" not in data:
            data["price"] = data["price_usd"]
        if "volume_24h_usd" in data and "volume_24h" not in data:
            data["volume_24h"] = data["volume_24h_usd"]
    return result


@app.get("/top")
async def api_top_crypto(limit: int = 10):
    return await get_top_crypto(limit=limit)


@app.get("/yields")
async def api_yields(min_apy: float = 0, chain: str = "all", max_results: int = 20):
    return await get_yields(min_apy=min_apy, chain=chain, max_results=max_results)


@app.get("/technical/{symbol:path}")
async def api_technical(symbol: str = "BTC/USDT", price: float = 0,
                        exchange: str = "binance"):
    return await technical_indicators(symbol=symbol, price=price, exchange=exchange)


@app.get("/analyze/{symbol}")
async def api_analyze(symbol: str = "BTC", price_usd: float = 0, market_cap: float = 0):
    return await analyze_token(symbol=symbol, price_usd=price_usd, market_cap=market_cap)


class Holding(BaseModel):
    symbol: str
    amount: float | None = None
    value_usd: float | None = None


@app.post("/portfolio")
async def api_portfolio(holdings: list[Holding]):
    """Portfolio health from real user holdings: [{symbol, amount} or {symbol, value_usd}]."""
    return await portfolio_health(holdings=[h.model_dump(exclude_none=True) for h in holdings])


@app.get("/portfolio")
async def api_portfolio_get():
    return make_error(
        "METHOD_NOT_ALLOWED",
        "Portfolio requires real holdings input",
        "Use POST /portfolio with body: [{\"symbol\":\"ETH\",\"amount\":1}]",
    )


@app.get("/gas/{chain}")
async def api_gas(chain: str = "ethereum"):
    return await gas_tracker(chain=chain)


@app.get("/estimate-tx")
async def api_estimate_tx(chain: str = "ethereum", gas_units: int = 21000, speed: str = "standard"):
    return await estimate_tx_cost(chain=chain, gas_units=gas_units, speed=speed)


@app.get("/sentiment/{symbol}")
async def api_sentiment(symbol: str = "BTC", price_change_24h: float = 0, volume_usd: float = 0):
    try:
        return await analyst.market_sentiment(symbol=symbol, price_change_24h=price_change_24h, volume_usd=volume_usd)
    except Exception as e:
        return make_error("AI_UNAVAILABLE", f"LLM interpretation unavailable: {e!s}", "Retry shortly; deterministic tools still work", retryable=True)


@app.get("/signal/{symbol:path}")
async def api_signal(symbol: str = "BTC/USDT", price: float = 0, rsi: float = 50, macd: str = "neutral", volume_trend: str = "stable"):
    try:
        return await analyst.trading_signal(symbol=symbol, price=price, rsi=rsi, macd=macd, volume_trend=volume_trend)
    except Exception as e:
        return make_error("AI_UNAVAILABLE", f"LLM interpretation unavailable: {e!s}", "Retry shortly; deterministic tools still work", retryable=True)


@app.get("/whales")
async def api_whales(min_value_usd: float = 1_000_000, timeframe_hours: int = 24):
    return await whale_alerts(min_value_usd=min_value_usd, timeframe_hours=timeframe_hours)


@app.get("/whale/{address}")
async def api_track_whale(address: str):
    return await track_whale(address=address)


if __name__ == "__main__":
    configure_json_logging()
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8006
    print(f"🚀 Crypto MCP API running on http://127.0.0.1:{port}")
    print(f"📖 Swagger: http://127.0.0.1:{port}/docs")
    uvicorn.run(app, host="127.0.0.1", port=port)
