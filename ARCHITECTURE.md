# ARCHITECTURE — Āgama v2

```
[AI Agent] ←MCP stdio→ mcp_server.py ─┐
[Client]   ←REST /v2→  api_server.py ─┼→ tools/* → providers/* → внешние API
[Human]    ←Web→       web/ dashboard ─┘
```

## Layers

| Слой | Файлы | Ответственность |
|---|---|---|
| MCP | `mcp_server.py` | регистрация 16 tools (mcp≥2.0 `MCPServer`), JSON-сериализация |
| REST/Web | `api_server.py`, `web/` | FastAPI, RBAC-ключи, rate limit, health/metrics, SSE, статика |
| Tools | `tools/*.py` | канонический envelope `{data, meta}` и error contract |
| Providers | `providers/*.py` | `base` (контракты), `market` (CCXT pool), `onchain` (Web3), `whale_provider` (Etherscan V2) |
| AI | `ai/llm.py`, `ai/schemas.py`, `ai/analyst.py` | цепочка LLM + structured outputs; LLM не источник чисел |
| Security | `auth/keys.py`, `auth/rbac.py`, `rate_limit.py` | ключи, права, лимиты |
| Observability | `observability.py` | JSON-логи, метрики, /metrics |

## Ключевые инварианты

1. Любой data-tool возвращает `{data, meta}` с `source/timestamp/freshness` — или `{error: {code, message, retryable, suggested_action}}`.
2. LLM не генерирует числа: пайплайн — REAL DATA → детерминированный расчёт → LLM-интерпретация → Pydantic-валидация.
3. Провайдеры деградируют явно (`degraded`, `warnings`, `UNAVAILABLE`), а не выдумывают данные.
4. Регрессионный тест запрещает `random`/моки в прод-путях (`tests/test_no_mocks_in_prod.py`).

## Потоки данных

- Market: `tools/price.py` → `ExchangePool.get(exchange)` (singleton, без пересоздания клиентов).
- On-chain: `tools/gas.py` → `RPCOneChainProvider.fetch_gas` (`asyncio.to_thread`, fallback из 3 RPC на сеть).
- Whales: `tools/whales.py` → `EtherscanWhaleProvider` (V2 multichain, ключ из env).
- AI: `ai/analyst.py` → `LLMClient.complete_structured` (circuit breaker, repair-once).

## Конвенции

- Версия: единственный источник — `pyproject.toml` (`_read_version()` в api_server).
- Имена tools: `verb_resource`; REST: kebab-case; файлы: snake_case.
- Секреты: только `~/.env`; в коде — чтение через `config.settings` / `os.getenv`.
