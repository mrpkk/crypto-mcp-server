# AUDIT REPORT — Crypto MCP Server (реальность vs заявления)

> Слайс 02 (S1). Каждый вывод подтверждён кодом (file:line). Дата: 2026-09-15. Ветка: `feature/v2-modernization`.
> Метод: построчное чтение `tools/`, `chain/`, `ai/`, `api_server.py`, `mcp_server.py`, `config.py` + baseline `pytest` (13 passed).

## 1. Executive Summary

Проект — образцовый по упаковке (README/MIT/CI/PyPI), но data-слой неполный: **4 инструмента из 14 — моки/хардкод** (`gas_tracker`, `estimate_tx_cost`, `track_whale`, `whale_alerts`), **2 — с захардкоженными ценами 2024** (`analyze_token`, частично `portfolio_health`). Готовый on-chain модуль `chain/client.py` (98 строк) **не вызывается нигде**. Заявленная SQLite (`config.db_path`) не реализована. Есть дубликат CORS-middleware с `allow_origins=["*"]` и тройное рассогласование версий (1.4.0 / 1.3.0 / 0.1.0). README заявляет «real-time» для моков — критичный риск для продаж.

## 2. Actual vs Claimed (14 инструментов)

| # | Tool | Claimed (README) | Actual (код) | Реальность | Priority |
|---|---|---|---|---|---|
| 1 | `get_price` | Real-time | CCXT, кэш 10с (`tools/price.py:27-64`) | ✅ REAL | — |
| 2 | `compare_prices` | Multi-exchange | CCXT 4 биржи (`tools/price.py:92-104`) | ✅ REAL | — |
| 3 | `get_top_crypto` | Real-time | CoinGecko (`tools/price.py:67`) | ✅ REAL | — |
| 4 | `get_yields` | Real-time | DeFi Llama + fallback (`tools/yield_tools.py`) | ✅ REAL | — |
| 5 | `yield_assessment` | AI-powered | LLM (`ai/analyst.py:130+`) | ✅ REAL | — |
| 6 | `technical_analysis` | Real-time | OHLCV, RSI/EMA/MACD (`tools/signal.py`) | ✅ REAL | — |
| 7 | `trading_signal` | AI-powered | LLM (`ai/analyst.py`) | ✅ REAL | — |
| 8 | `analyze_token` | Real-time | Hardcoded prices 2024 (`tools/analysis.py:74-80`, `:90-94`, `:128-130`) | ⚠️ HARDCODED | **P0** |
| 9 | `portfolio_health` | Real-time | Формулы от входа ок, но `diversity_score = len*15` (`tools/analysis.py:62`), `_suggest_split` фикс (`:132-139`) | ⚠️ PARTIAL | P1 |
| 10 | `gas_tracker` | Real-time | `random.uniform` ×12 (`tools/gas.py:8-13`) | ❌ MOCK | **P0** |
| 11 | `estimate_tx_cost` | Based on gas | Производный от random + хардкод цен (`tools/gas.py:50`) | ❌ MOCK | **P0** |
| 12 | `market_sentiment` | AI-powered | LLM (`ai/analyst.py`) | ✅ REAL | — |
| 13 | `track_whale` | Real-time | Полный хардкод адресов/сумм (`tools/whales.py:8-24`) | ❌ MOCK | **P0** |
| 14 | `whale_alerts` | Real-time | Полный хардкод tx (`tools/whales.py:27-65`) | ❌ MOCK | **P0** |

**Итог:** 6 живых data-tools, 3 AI, 3 мока, 2 хардкод. Расхождение README↔код — по 5 позициям.

## 3. Dead Code / Unused Infrastructure

| Артефакт | Факт | Следствие |
|---|---|---|
| `chain/client.py` (Web3Client, 98 строк) | Не импортируется ни в `tools/`, ни в `mcp_server.py`, ни в `api_server.py` | P0: подключить к gas/whales (S2) |
| `config.py:13` `db_path` | `data/` отсутствует, SQLite не используется | P1: реализовать или удалить из конфига |
| `config.py:9-11` etherscan/alchemy/infura | Не используются в коде | P0: Etherscan → WhaleProvider (S2) |
| `tools/whales.py:3-5` `WHALE_WALLETS` | Константа-заглушка с фейковым адресом | Удалить при рефакторинге |

## 4. Mocks / Hardcoded (file:line)

| Место | Что | Замена |
|---|---|---|
| `tools/gas.py:8-13` | `random.uniform` для base/priority fee 6 сетей | Web3Client: `w3.eth.gas_price` + EIP-1559 base fee из блока |
| `tools/gas.py:50` | `usd_per_eth = {ethereum: 3500, bsc: 580...}` | Реальная цена ETH/BNB/MATIC через `tools/price.py` |
| `tools/whales.py:8-24` | `track_whale`: хардкод balance 250000 ETH, 3 holdings, 2 tx | Etherscan API (ключ `ETHERSCAN_API_KEY` из env) |
| `tools/whales.py:27-65` | `whale_alerts`: 3 фейковые транзакции | Etherscan tokentx/txlist + фильтр >$1M |
| `tools/analysis.py:74-80` | `_price`: BTC=65000, ETH=3500 (2024) | `get_price()` из `tools/price.py` |
| `tools/analysis.py:82-88` | `_mc`, `_supply`: статические supply | CoinGecko markets (supply из API) |
| `tools/analysis.py:90-94` | `_ath_mult`/`_atl_mult`: синтетические ATH/ATL | CoinGecko `ath`/`atl` |
| `tools/analysis.py:128-130` | `_dominance`: total_mc = 2.5e12 (хардкод) | CoinGecko global data |

## 5. Security Findings

| ID | Находка | File:line | Priority |
|---|---|---|---|
| SEC-1 | **CORS-дубликат**: `add_middleware(CORSMiddleware)` вызван дважды с `allow_origins=["*"]` | `api_server.py:44-45` | P1 |
| SEC-2 | Нет rate limiting (любой может исчерпать лимиты бирж) | `api_server.py` (весь) | P1 |
| SEC-3 | Нет API-ключей/RBAC | — | P2 |
| SEC-4 | Нет `/health` `/ready` `/version` (невозможен мониторинг) | `api_server.py` | P1 |
| SEC-5 | Нет дисклеймера «не является финансовой рекомендацией» на выводах | все tools | P1 |
| SEC-6 | AI-fallback возвращает строку-заглушку вместо честного UNAVAILABLE | `ai/analyst.py:115-117` | P1 |
| SEC-7 | Версии рассогласованы: API 1.4.0 / дашборд v1.3.0 / pyproject 0.1.0 | `api_server.py:42,108`, `pyproject.toml:8` | P2 |
| SEC-8 | Секреты в `.env` не логируются (проверено: логирование ключей отсутствует) — ок, закрепить тестом | — | P2 |

## 6. Performance

| ID | Находка | File:line | Fix |
|---|---|---|---|
| PERF-1 | CCXT-клиент создаётся и закрывается на **каждый** вызов биржи (нет pooling) | `tools/price.py:64,104` | ExchangePool singleton (S3) |
| PERF-2 | Кэш только in-memory dict, TTL 10с, без метрик hit/miss | `tools/price.py:13,34` | CacheProvider + метрики (S3–S4) |
| PERF-3 | Нет timeout/retry/circuit breaker на внешних вызовах (только CCXT internal) | `tools/*` | Provider layer (S3) |

## 7. MCP Schema Problems

| ID | Находка | File:line |
|---|---|---|
| MCP-1 | Описания инструментов не по принципу «verb + resource + purpose» (смешанные стили) | `mcp_server.py:24-160+` |
| MCP-2 | Нет error contract: ошибки возвращаются как `{"error": "..."}` без code/retryable/suggestion | `mcp_server.py` (`_safe_call`) |
| MCP-3 | Нет envelope `{data, meta}`: выходы инструментов не содержат source/timestamp/freshness | все `tools/*` |
| MCP-4 | Нет группировки инструментов (MARKET/DEFI/TECHNICAL/ONCHAIN/PORTFOLIO/INTELLIGENCE) | `mcp_server.py` |

## 8. Priority Matrix (план исправления)

| Priority | Пункты | Спринт |
|---|---|---|
| **P0** | gas/estimate (моки), track_whale/whale_alerts (моки), analyze_token (цены 2024), подключить Web3Client/Etherscan, regression-тест «мок не в прод» | S2 |
| **P1** | Provider layer + envelope, /health /ready /version, CORS-фикс, rate-limit, дисклеймеры, PERF-1 (pooling) | S3–S5 |
| **P2** | Единая версия v2.0.0, API-ключи/RBAC, метрики, docs | S4–S5, S8 |
| **P3** | MCP-описания/группировка, DB для watchlists/alerts | S5, S7 |

## 9. Acceptance Criteria (этого слайса)

- [x] Каждый вывод имеет file:line
- [x] Все моки найдены (4 инструмента + 2 хардкод-места)
- [x] Dead code инвентаризирован (chain/client.py, db_path, env-ключи)
- [x] Security findings (8 позиций) и perf (3 позиции)
- [x] Priority matrix связана со спринтами SPEC
