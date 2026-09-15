# ChainSight (Crypto MCP Server v2)

**Crypto intelligence for AI agents and humans.** 16 MCP tools + REST API:
real market data, on-chain, DeFi and honest AI interpretation — every response
carries its source, timestamp and freshness. No fabricated data, ever.

## What you get

| Group | Tools | Data source |
|---|---|---|
| Market | `get_price`, `compare_prices`, `get_top_crypto` | CCXT (Binance/Coinbase/Kraken/Bybit), CoinGecko |
| DeFi | `get_yields`, `yield_assessment` | DeFi Llama, LLM interpretation |
| Technical | `technical_analysis`, `backtest_strategy` | Real OHLCV (RSI Wilder, MACD, SMA, paper-trading) |
| On-chain | `gas_tracker`, `estimate_tx_cost`, `track_whale`, `whale_alerts` | Web3 RPC (6 chains, fallback), Etherscan V2 |
| Portfolio | `analyze_token`, `portfolio_health`, `portfolio_doctor` | Live prices, HHI metrics, risk scenarios |
| Intelligence | `market_sentiment`, `trading_signal` | LLM chain (GigaChat → GitHub Models), structured JSON |

Each response: `{"data": {...}, "meta": {"source", "timestamp", "freshness_seconds", "cached", "degraded", "warnings", "disclaimer"}}`
or a typed error: `{"error": {"code", "message", "retryable", "suggested_action"}}`.

## Quick start (MCP)

```bash
pip install -r requirements.txt
cp .env.example .env        # optional: ETHERSCAN_API_KEY, GIGACHAT_AUTH_KEY, GITHUB_TOKEN
python main.py              # stdio MCP server
```

Claude / Cursor / VS Code:

```json
{ "mcpServers": { "chainsight": { "command": "python", "args": ["/path/to/main.py"] } } }
```

## Quick start (REST + dashboard)

```bash
python api_server.py 8006
# dashboard:  http://127.0.0.1:8006/
# swagger:    http://127.0.0.1:8006/docs
# health:     http://127.0.0.1:8006/health   metrics: /metrics
```

## Data honesty (what differs from v1)

- All previously fake tools are now real: gas via Web3 RPC, whales via Etherscan V2.
- No hardcoded prices, no random values, no fabricated APY fallbacks.
- Missing inputs are returned as `null` + warnings; unavailable providers → typed errors.
- Regression tests prevent mocks from reaching production paths (`tests/test_no_mocks_in_prod.py`).

## Features

- **Data-quality badges** (LIVE/CACHED/STALE/DEGRADED/UNAVAILABLE) across API and dashboard.
- **Watchlists & smart alerts**: rules (`price_move`, `gas_below`, `whale_above`) evaluated against live tools with "why it matters".
- **SSE stream**: `/stream/prices` for real-time price updates.
- **Security**: RBAC per tool (free/pro/enterprise), `cms_` API keys (SHA-256 at rest), rate limiting, threat model in `docs/SECURITY.md`.
- **Observability**: structured JSON logs, Prometheus-style `/metrics`, `X-Request-ID`.

## Limits (honest)

- Whale tracking: Etherscan free tier covers the latest transactions per queried address — not a full-market feed.
- AI tools require credentials (GigaChat or GitHub Models); without them they return `AI_UNAVAILABLE`.
- Rate limits: 100 req/h anonymous (free), 1000 req/h with a pro key.
- Not financial advice: every envelope carries a disclaimer.

## Docs

`docs/MCP_TOOL_CONTRACTS.md` · `docs/USER_FLOWS.md` · `docs/SECURITY.md` ·
`docs/LLM_PROVIDER_BENCHMARK.md` · `docs/MCP_VERSION_STRATEGY.md` ·
`ARCHITECTURE.md` · `DESIGN_SYSTEM.md` · `CHANGELOG.md` · `PROGRESS.md`

MIT License.
