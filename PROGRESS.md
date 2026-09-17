# PROGRESS — Crypto MCP Server v2 «Āgama»

> Правило: каждый слайс = реализация + тест + зелёный прогон + commit + push + отметка здесь (с хэшем).
> SPEC: `~/Документы/work/projectBooks/CryptoMCPSPEC.md`. Ветка: `feature/v2-modernization`.
> Статус-легенда: `[ ]` todo · `[~]` in progress · `[x]` done (hash) · `[!]` blocked (причина).

---

## 🎯 МЕГА-КОНТЕКСТ (читать первым в каждой сессии)

**Проект:** Crypto MCP Server v2 — «Crypto Intelligence Infrastructure for AI Agents and Humans». Read-only по умолчанию; execution-boundary отсутствует by design (STOP-05).
**Бренд: ĀGAMA** (आगम — «пришедшее/дошедшее знание, авторитетное свидетельство»; в ньяе — шабда-прамана). Выбран владельцем 18.09.2026. Пара к KARTA: «Āgama знает — KARTA делает». Коллизии (проверено 18.09): openSUSE Agama (инсталлятор), AGAMA astro-библиотека, PyPI-пакет `agama` занят → имя пакета при публикации решить отдельно (кандидат `agama-mcp`), UNVERIFIED до проверки.
**Ценность:** надёжный context layer, дающий AI-агентам проверяемые market/DeFi/on-chain данные с provenance (source/freshness/confidence) и без фейков (0 моков в prod-путях — регрессионный тест).

**Ключевые договорённости с владельцем:**
1. **Правило старта:** слайс — только по прямой команде; обсуждение ≠ команда (прецедент 16.09).
2. **Реальный data reality:** никаких random/хардкод-цен под видом live; нет данных → UNAVAILABLE/DEGRADED, не выдумка.
3. **Бюджет:** без платных провайдеров; GigaChat — только после бенчмарка и юр-проверки лицензии (STOP-10).
4. **Санкции РФ:** крипто-выплаты/маркетплейсы — только non-RF юрисдикция; фиат B2B — основной канал (STOP-04).
5. **Backup/Obsidian:** вести daily notes + бэкап локальный и GDrive (в конце сессий).

**Текущее состояние (18.09.2026):**
- S1–S7 закрыты полностью; S8 (лаунч) — 39/40 закрыто, пункт 40 «готовность к beta 100%» подтверждён.
- **148 тестов зелёные** (проверено повторно 18.09, system python3: `148 passed in 3.46s`).
- Осталось: **публикация/финальный бренд (STOP-01)** и ответы на APPROVAL GATE (§11 SPEC): бренд A/B/C, LLM-политика, сетка монетизации, фиат-режим, площадки (Dealwork P1), GigaChat-лицензия, FUTURE-выбор, SQLite, scope.
- Артефакты: README (честный), ARCHITECTURE, SECURITY (T1–T8), API, MCP, DEPLOYMENT, CONFIGURATION, CHANGELOG, DESIGN_SYSTEM, MCP_VERSION_STRATEGY, LLM_PROVIDER_BENCHMARK, MARKETPLACE_PACK, USER_FLOWS, PROGRESS.

**Открытые STOP GATES (из SPEC §2.2):** STOP-01 бренд/публикация · STOP-04 крипто-платежи (x402, non-RF only) · STOP-10 GigaChat в продажном продукте (лицензия).
Плюс ждут решения: A2A-упаковка (remote MCP + manifest — дизайн готов, включать после STOP-04), сетка тарифов FREE/PRO/Enterprise, выбор FUTURE-прототипа (x402 / Paper-Trading Sandbox / Agent Marketplace).

**Синергия с KARTA (onchain-ai-agent):** ChainSight = intelligence-слой (цены/газ/киты/DeFi, готов), KARTA = execution-слой (policy/simulation/audit). Композиция через MCP/REST даёт продукт 1+1>2 — вынести на обсуждение.

---

## Текущий фокус
S8 — Launch: 40 — готовность к beta подтверждена; бренд **Āgama** решён (18.09). Осталось: слайс 41 — ребрендинг ChainSight→Āgama, публикация/листинг — решение владельца.

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
- [x] 19. `docs/MCP_TOOL_CONTRACTS.md` (145aa0c: 14 tools) — все tools по шаблону (PURPOSE≠INPUT/OUTPUT/SOURCE/FRESHNESS/COST/RATE/FAILURE/EXAMPLE)
- [x] 20. Error contract (145aa0c: единый make_error во всех tools) `{error:{code,message,retryable,suggested_action}}` во всех tools
- [x] 21. LLMProvider abstraction (145aa0c: ai/llm.py, circuit breaker) (primary/fallback/disabled, circuit breaker, timeout, retry)
- [x] 22. Structured outputs (145aa0c: Pydantic, repair-once) (Pydantic) + confidence/assumptions/data_timestamp/sources
- [x] 23. `docs/LLM_PROVIDER_BENCHMARK.md` (145aa0c) (веса 20/20/20/15/10/10/5; GigaChat — после проверки лицензии, STOP-10)
- [x] 24. `docs/MCP_VERSION_STRATEGY.md` (145aa0c: mcp 2.0 уже внедрён) (MCP 2026-07-28: stateless core, cache hints, Tasks, Apps)
- [x] 25. Тесты: test_llm_structured.py (15 тестов) (145aa0c)

## S6 — DESIGN & WEB (W7–8, P1)
- [x] 26. `DESIGN_SYSTEM.md` (889e65f) + токены (TypeScript/CSS) — quiet confidence
- [x] 27. Компоненты (889e65f: web/styles.css — все состояния) (Button/Input/Card/Modal/Toast/Table/Chart/Sparkline/Heatmap/Badge/Skeleton/Tooltip/Tabs)
- [x] 28. Dashboard «Market Pulse» (889e65f: web/index.html + app.js, бейджи LIVE/CACHED/STALE/DEGRADED/UNAVAILABLE) (COMMAND CENTER + data-quality бейджи LIVE/CACHED/STALE/DEGRADED/UNAVAILABLE)
- [x] 29. Onboarding: Explore Live Data + DEMO-бейдж (889e65f) / Explore Live Data + Demo Mode (бейдж DEMO)
- [x] 30. `docs/USER_FLOWS.md` (889e65f: 10 флоу) — 10 флоу (START/GOAL/STEPS/RESPONSE/FAILURE/SUCCESS)

## S7 — FEATURES (W9–10, P1)
- [x] 31. Watchlists + persistence SQLite (01dcd16)
- [x] 32. Smart alerts-движок (price_move/gas_below/whale_above + WHY IT MATTERS) (01dcd16)
- [x] 33. SSE-стриминг цен (/stream/prices) + UI (01dcd16)
- [x] 34. Тесты: 13 новых (watchlists/alerts/streaming) (01dcd16)

## S8 — LAUNCH (W11–12, P2)
- [x] 35. AI Portfolio Doctor v1 (diversification/concentration/rebalance; без «гарантий прибыли»)
- [x] 36. Paper-trading backtest v1 (реальные OHLCV + виртуальный портфель)
- [x] 37. Docs-пакет: README (честный), ARCHITECTURE, API, MCP, DEPLOYMENT, CONFIGURATION, CHANGELOG
- [x] 38. CI/CD: ruff → pytest → pip-audit → build (починить согласование версий)
- [x] 39. Marketplace pack (Dealwork P1-площадка) + remote MCP/A2A manifest (FR-34/36)
- [~] 40. Готовность к beta: 100% (чек-лист ниже). Публикация/бренд — решение владельца (STOP-01)
- [ ] 41. Ребрендинг ChainSight → **Āgama**: README, ARCHITECTURE, DEPLOYMENT, DESIGN_SYSTEM, MARKETPLACE_PACK, USER_FLOWS, web/ (index.html, app.js), marketplace/manifest.json, api_server.py, tests/test_web.py (по команде владельца)

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
| 19-25 | 2026-09-15 | LLM-цепочка (breaker) + structured outputs + контракты/бенчмарк/MCP-стратегия | 145aa0c | 121 passed + live GigaChat | S5 закрыт: sentiment bullish 60 |
| 26-30 | 2026-09-15 | Market Pulse дашборд (static web/), дизайн-система, онбординг+DEMO, user flows; legacy HTML удалён (−214 строк) | 889e65f | 126 passed + live smoke | S6 закрыт |
| 31-34 | 2026-09-15 | Watchlists + smart alerts (WHY IT MATTERS) + SSE-стрим + UI-панели | 01dcd16 | 139 passed + live smoke | S7 закрыт: alert сработал на gas 0.29 gwei |
| 35-36 | 2026-09-15 | Portfolio Doctor v1 + backtest_strategy (paper trading на реальных свечах) | f5d4320 | 148 passed | реестр 16 tools |
| 37-39 | 2026-09-15 | README честный, CHANGELOG, ARCHITECTURE, DEPLOYMENT, CI (ruff+pytest+build+pip-audit), marketplace pack | (коммит) | 148 passed | готово к листингу Dealwork |


---

## v2.0 ACCEPTANCE (по SPEC §10)

- [x] 0 моков в production path (регрессионный тест зелёный)
- [x] 100% ответов с `meta.source + timestamp + freshness`
- [x] FR-8/9 без хардкод-цен (analysis live)
- [x] Единая версия v2.0.0; `/health` живой
- [x] API-ключи + RBAC + rate limiting + threat model T1–T8 (`docs/SECURITY.md`)
- [x] Дашборд: Market Pulse + data-quality бейджи + onboarding (web/)
- [x] Дисклеймер на всех выводах (`meta.disclaimer`)
- [x] Пирамида тестов: unit/integration/contract; 148 тестов; CI зелёный
- [x] Доки: README, CHANGELOG, ARCHITECTURE, DEPLOYMENT, SECURITY, MCP_TOOL_CONTRACTS, USER_FLOWS, LLM_PROVIDER_BENCHMARK, MCP_VERSION_STRATEGY, MARKETPLACE_PACK
- [x] Метрики: latency-метрика в /metrics (p95 контроль — при нагрузке), uptime-цель 99.9%
- [ ] Публичная beta и финальный бренд — STOP-01/решение владельца (ChainSight = рабочее имя)
