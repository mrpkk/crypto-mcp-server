# CHANGELOG

## [2.0.0] — 2026-09-15

### Data Reality (P0)
- `gas_tracker` / `estimate_tx_cost`: real Web3 RPC data (EIP-1559, 6 chains, RPC fallback, 15s cache). Removed `random.uniform`.
- `track_whale` / `whale_alerts`: real Etherscan V2 provider (hashed/limited free tier, USD filtering). Removed hardcoded mock transactions.
- `analyze_token` / `portfolio_health`: live prices; missing inputs returned as `null` with warnings. Removed 2024 hardcoded prices.
- `technical_analysis`: OHLCV from pooled clients; removed `_fallback_price` (2024 values) and invented support/resistance.
- `get_yields`: removed `FALLBACK_YIELDS` (fabricated APY/TVL) — provider errors are honest now.
- Regression guard: `tests/test_no_mocks_in_prod.py`.

### Architecture
- Provider layer: `providers/base.py` (canonical envelope/error), `providers/market.py` (ExchangePool, no per-call client churn), `providers/onchain.py` (`asyncio.to_thread`, RPC fallback).
- Unified response envelope `{data, meta}` across all tools; `meta.disclaimer`.

### MCP (breaking fix)
- Migrated to `mcp>=2.0` (`MCPServer` API). The server previously failed to import on mcp 2.x.
- Registry now 16 tools (added `portfolio_doctor`, `backtest_strategy`).
- Tool schemas are generated from function signatures.

### AI layer
- `ai/llm.py`: provider chain (GigaChat → GitHub Models ×3) with circuit breaker, timeouts, structured JSON outputs (Pydantic, repair-once).
- Honest `AI_UNAVAILABLE` errors instead of stub strings.

### Security
- RBAC per tool (free/pro/enterprise), `cms_` API keys (SHA-256 at rest, metering, revocation), sliding-window rate limiting (429 + headers).
- CORS single middleware with allowlist; secrets only in `~/.env`; redacted JSON logging.
- `docs/SECURITY.md` threat model (T1–T8).

### API & Observability
- New endpoints: `/health`, `/ready`, `/version`, `/capabilities`, `/metrics`, `/watchlist`, `/alerts`, `/alerts/check`, `/stream/prices`.
- Single version source (pyproject.toml = 2.0.0); removed version drift (1.4.0/1.3.0/0.1.0).
- Structured JSON logs, `X-Request-ID`, Prometheus-style metrics.

### Web
- New static dashboard (`web/`): Market Pulse, data-quality badges, watchlist/alerts panels, SSE updates, onboarding + DEMO badge. Legacy inline dashboard removed (−214 lines).

### Tests/CI
- 148 tests (from 13); CI: ruff + pytest + build (+ pip-audit job) on main and feature branches.
