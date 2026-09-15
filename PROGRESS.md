# PROGRESS — Crypto MCP Server v2 «ChainSight»

> Правило: каждый слайс = реализация + тест + зелёный прогон + commit + push + отметка здесь (с хэшем).
> SPEC: `~/Документы/work/projectBooks/CryptoMCPSPEC.md`. Ветка: `feature/v2-modernization`.
> Статус-легенда: `[ ]` todo · `[~]` in progress · `[x]` done (hash) · `[!]` blocked (причина).

## Текущий фокус
S5 — MCP & AI (следующий шаг: 19 MCP tool contracts)

---

## S1 — AUDIT (W1)
- [x] 01. Ветка + PROGRESS.md (255e271)
- [x] 02. `docs/AUDIT_REPORT.md` — Actual vs Claimed по 14 tools (каждая строка с file:line) (f7313b8)
  - [x] 2.1 Таблица реальности: 14 инструментов (claimed/actual/status/priority)
  - [x] 2.2 Dead code: `chain/client.py`, `db_path`, неиспользуемые env-ключи
  - [x] 2.3 Mocks/hardcode: конкретные file:line (`random.uniform`, цены 2024, whale-заглушки)
  - [x] 2.4 Security findings: CORS-дубли, версии, отсутствие health/rate-limit/дисклеймера
  - [x] 2.5 MCP schema problems: описания, defaults, error contract
  - [x] 2.6 Priority matrix P0–P3 + план исправления

## S2 — DATA REALITY (W1–2, P0)
- [x] 03. `tools/gas.py` (18f7f7a) → реальный gas через Web3Client (6 сетей, кэш 15с, EIP-1559, fallback RPC)
  - [x] 3.1 Тест: `tests/test_gas_tracker.py` (gas > 0, не random, meta есть)
  - [x] 3.2 Тест fallback RPC (мок отказа первого RPC)
- [x] 04. `providers/whale_provider.py` + `tools/whales.py` → Etherscan (ключ из env), >$1M, без хардкода
  - [x] 4.1 ABC WhaleProvider: health/capabilities/get_transactions/get_alerts
  - [x] 4.2 Тесты: `tests/test_whales_real_data.py` (не hardcoded, envelope)
- [x] 05. `tools/analysis.py` → убрать цены 2024; реальные входы или явная передача данных
  - [x] 5.1 `analyze_token`: цена через get_price()
  - [x] 5.2 `portfolio_health`: вход {symbol, amount}[], без выдуманных значений
  - [x] 5.3 Тесты: `tests/test_analysis_real_data.py`
- [x] 06. Regression: `tests/test_no_mocks_in_prod.py` (inspect.getsource: нет random/hardcode в прод-путях) (c8931b0)

## S3 — PROVIDERS (W3–4, P0)
- [x] 07. `providers/base.py` — ABC всех провайдеров + envelope helper
- [x] 08. `providers/market.py` — CCXT + CoinGecko fallback; ExchangePool (singleton, lifecycle) (425b372)
- [x] 09. `providers/onchain.py` — Web3Client wrapper (health/timeout/retry/cache) (3a7acd5)
- [x] 10. Envelope во все 14 tools (09f9aff + d32b5df: price/yield/signal; AI-группа отдаёт dict от analyst — обернуть в S5)
- [x] 11. `/health`, `/ready`, `/version`, `/capabilities` + единый version source (v2.0.0) (65b6866: MCP под mcp 2.0 починен!)
- [x] 12. Rate limiting (per-key/per-tier) + CORS-фикс (один middleware, allowlist) (5190d24)
- [x] 13. Тесты: test_providers.py, test_envelope.py, test_health.py (5190d24)

## S4 — SECURITY (W5, P1)
- [x] 14. RBAC per-tool (free/pro/enterprise) + `auth/rbac.py` (0a54053)
- [x] 15. API-ключи (`cms_` prefix, хеширование, ротация) + usage metering in-house (0a54053)
- [x] 16. Observability: structured JSON logs + request_id + метрики + /metrics (6088c28)
- [x] 17. `docs/SECURITY.md` — threat model T1–T8 (6088c28)
- [x] 18. Тесты: test_auth.py, test_api_keys_integration.py, test_security.py (6088c28)

## S5 — MCP & AI (W6, P1)
- [ ] 19. `docs/MCP_TOOL_CONTRACTS.md` — все tools по шаблону (PURPOSE≠INPUT/OUTPUT/SOURCE/FRESHNESS/COST/RATE/FAILURE/EXAMPLE)
- [ ] 20. Error contract `{error:{code,message,retryable,suggested_action}}` во всех tools
- [ ] 21. LLMProvider abstraction (primary/fallback/disabled, circuit breaker, timeout, retry)
- [ ] 22. Structured outputs (Pydantic) + confidence/assumptions/data_timestamp/sources
- [ ] 23. `docs/LLM_PROVIDER_BENCHMARK.md` (веса 20/20/20/15/10/10/5; GigaChat — после проверки лицензии, STOP-10)
- [ ] 24. `docs/MCP_VERSION_STRATEGY.md` (MCP 2026-07-28: stateless core, cache hints, Tasks, Apps)
- [ ] 25. Тесты: test_llm_structured.py, test_error_contract.py

## S6 — DESIGN & WEB (W7–8, P1)
- [ ] 26. `DESIGN_SYSTEM.md` + токены (TypeScript/CSS) — quiet confidence
- [ ] 27. Компоненты (Button/Input/Card/Modal/Toast/Table/Chart/Sparkline/Heatmap/Badge/Skeleton/Tooltip/Tabs)
- [ ] 28. Dashboard «Market Pulse» (COMMAND CENTER + data-quality бейджи LIVE/CACHED/STALE/DEGRADED/UNAVAILABLE)
- [ ] 29. Onboarding: Connect MCP / Explore Live Data + Demo Mode (бейдж DEMO)
- [ ] 30. `docs/USER_FLOWS.md` — 10 флоу (START/GOAL/STEPS/RESPONSE/FAILURE/SUCCESS)

## S7 — FEATURES (W9–10, P1)
- [ ] 31. Watchlists (assets/wallets) + persistence (SQLite — заявленную реализовать)
- [ ] 32. Smart alerts («unusual activity» + WHY IT MATTERS вместо «BTC +1%»)
- [ ] 33. WebSocket/SSE стриминг цен и алертов
- [ ] 34. Тесты: test_watchlists.py, test_alerts.py, test_streaming.py

## S8 — LAUNCH (W11–12, P2)
- [ ] 35. AI Portfolio Doctor v1 (diversification/concentration/rebalance; без «гарантий прибыли»)
- [ ] 36. Paper-trading backtest v1 (реальные OHLCV + виртуальный портфель)
- [ ] 37. Docs-пакет: README (честный), ARCHITECTURE, API, MCP, DEPLOYMENT, CONFIGURATION, CHANGELOG
- [ ] 38. CI/CD: ruff → pytest → pip-audit → build (починить согласование версий)
- [ ] 39. Marketplace pack (Dealwork P1-площадка) + remote MCP/A2A manifest (FR-34/36)
- [ ] 40. Публичный beta + чек-лист приёмки §10 SPEC

---

## Журнал слайсов (append-only)
| # | Дата | Слайс | Коммит | Тест | Примечание |
|---|---|---|---|---|---|
| 01 | 2026-09-15 | Ветка + PROGRESS.md | 255e271 | baseline 13 passed | Старт v2 |
| 02 | 2026-09-15 | AUDIT_REPORT.md (14 tools, file:line) | f7313b8 | — | 4 мока + 2 хардкод подтверждены |
| 03 | 2026-09-15 | Реальный gas: Web3 EIP-1559 + fallback + кэш 15с | 18f7f7a | 24 passed + live smoke | random удалён, живой RPC OK |
| 04 | 2026-09-15 | WhaleProvider (Etherscan V2) + фильтры + USD | 8bb3590, 97278b5 | 32 passed + live smoke | CRV $10.8k реальный; ruff 0 |
| 05 | 2026-09-15 | analysis.py: живые цены, HHI-диверсификация, честные null | 531a2e2 | 40 passed + live smoke | BTC $78167; цены 2024 удалены |
| 06 | 2026-09-15 | Regression guard: random/моки не в прод + контракты | c8931b0 | 44 passed | S2 закрыт: 0 моков |
| 07 | 2026-09-15 | providers/base.py: единые envelope/error + ABC | 01aa23d | 49 passed | рефактор gas/whales/analysis на base |
| 08 | 2026-09-15 | ExchangePool + CCXTMarketProvider (price.py без churn) | 425b372 | 59 passed + live | BTC $77992, пул 1 клиент |
| 09 | 2026-09-15 | RPCOneChainProvider (to_thread) + gas на провайдерах | 3a7acd5 | 66 passed + live | base 0.005 gwei, $0.0023 swap |
| 10 | 2026-09-15 | Envelope price-группы + api_server: CORS-fix, POST /portfolio, честные AI-ошибки | 09f9aff | 66 passed + REST smoke | BTC $77986 живой |
| 10c | 2026-09-15 | Envelope signal/yields; выпилены FALLBACK_YIELDS (APY-фейк) и цены 2024 в signal | d32b5df | 66 passed + live | RSI 61, MA50 $2210, DeFiLlama onre |
| 11 | 2026-09-15 | Health/version + ФИКС MCP 2.0 (сервер не запускался!) | 65b6866 | 66 passed + MCP smoke | /capabilities: 14 tools |
| 12-13 | 2026-09-15 | Rate limiter (429, per-key/tier) + health tests | 5190d24 | 80 passed | S3 закрыт |
| 14-15 | 2026-09-15 | RBAC + SQLite API-ключи (cms_, SHA-256, метеринг) + REST-интеграция | 0a54053 + 6088c28 | 98→106 passed | 401/ревокация работают |
| 16-18 | 2026-09-15 | Observability (JSON-логи, /metrics, X-Request-ID) + SECURITY.md (T1–T8) + дисклеймер | 6088c28 | 106 passed | S4 закрыт |
