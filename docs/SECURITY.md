# SECURITY — Crypto MCP Server v2

> Threat model and implemented controls. Read-only by default: the platform
> provides intelligence only. Any function that trades, transfers, signs or
> deploys is out of scope and requires explicit owner approval (STOP-05/06).

## Assets

1. API keys (Etherscan, LLM providers) and user API keys (hashed).
2. Usage data (metering) and audit trail.
3. Infrastructure access (RPC endpoints).
4. Reputation: trust in data quality.

## Threat model

| ID | Угроза | Атака | Контроль в коде |
|---|---|---|---|
| T1 | Secret leakage | Ключи в логах/репозитории | Секреты только в `~/.env`; redacted logging (JSON-форматтер не пишет заголовки); `rg 'ghp_\|sk-\|vk1.a.'` перед коммитом; `test_security.py::test_api_key_not_logged` |
| T2 | SSRF | Заставить сервер запросить внутренний URL | Нет user-controlled URL: все внешние адреса — константы (`providers/*`, `tools/*`). При добавлении fetch-функций — allowlist + запрет private IP (10/8, 192.168/16, localhost), только https |
| T3 | Prompt injection | Вредоносные инструкции через данные | LLM получает только структурированные числа из tools; внешние тексты — untrusted; числа никогда не генерирует LLM (`providers/base.py: LLMProvider` docstring) |
| T4 | Rate abuse / DoS | Флуд запросами | Sliding-window limiter: 100 req/h free, 1000 req/h pro; 429 + Retry-After (`rate_limit.py`); health/metrics exempt |
| T5 | Data poisoning | Провайдер отдаёт фейк | Multi-source envelopes с `meta.source`; `degraded` warnings; error contract вместо выдуманных значений; regression-тест `test_no_mocks_in_prod.py` |
| T6 | Неавторизованный доступ | Использование без ключа | Анонимный доступ = free tier (read-only); `cms_`-ключи: SHA-256 at rest, ревокация, 401 для невалидных (`auth/keys.py`) |
| T7 | Privilege escalation | Доступ к on-chain инструментам на free | RBAC per-tool: free = market+defi; pro = +onchain+intelligence; enterprise = всё (`auth/rbac.py`) |
| T8 | Supply chain | Вредоносные зависимости | Пин версий (`requirements.txt`), `pip-audit` в CI, проверка существования пакета до импорта |

## Implemented controls (сводка)

- **Secrets**: только `~/.env` (двойной env_file: проектный + домашний), никогда в git.
- **Keys**: `cms_`-префикс, SHA-256 хеш at rest, метеринг вызовов, ревокация (`auth/keys.py`).
- **RBAC**: Tier-модель free/pro/enterprise (`auth/rbac.py`).
- **Rate limiting**: per-identity (`key:` или `ip:`), 429, заголовки `X-RateLimit-*`.
- **CORS**: один middleware, allowlist из `CORS_ORIGINS` (по умолчанию `*` для локального read-only; в продакшене задать список).
- **Дисклеймер**: `meta.disclaimer = "Not financial advice."` в каждом envelope.
- **Error contract**: `{code, message, retryable, suggested_action}` — без утечки стектрейсов агентам.
- **Наблюдаемость**: `X-Request-ID` на каждом ответе, структурированные JSON-логи, `/metrics`.

## Logging policy

Никогда не логировать: API keys, private keys, токены, заголовки авторизации.
JSON-форматтер пишет только белый список полей (`request_id, tool, path, latency_ms, status`).

## Out of scope (v2.0)

Transaction execution, wallet custody, private keys, trading от имени пользователя,
Solana как обязательная зависимость, крипто-платежи без одобрения владельца.

## Reporting

При инциденте: ключи отзываются (`APIKeyStore.revoke`), секреты ротируются в `~/.env`,
инцидент фиксируется в дневнике Obsidian.
