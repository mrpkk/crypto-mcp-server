# MARKETPLACE PACK — ChainSight v2

> Листинг-кит для A2A-площадок. Приоритет по SPEC: **Dealwork.ai (P1, USD-выплаты)**,
> затем OKX.AI / x402 (P2, санкционные ограничения РФ), остальные — по матрице.

## Короткий оффер (EN, для листинга)

**ChainSight — real crypto intelligence for AI agents.**
16 MCP tools + REST API: live prices, arbitrage, DeFi yields, gas (6 chains),
whale tracking (Etherscan), technical analysis, paper-trading backtests and
honest AI interpretation. Every response includes its source, timestamp and
freshness — no fabricated data, typed errors when a provider is down.

- Free tier: 100 requests/hour, no key required.
- Pro: 1000 req/h + portfolio doctor + intelligence tools.
- Integration: one command (`python main.py`) for MCP; REST at `/docs`.

## Что входит (deliverables)

| Артефакт | Путь |
|---|---|
| MCP-сервер (16 tools) | `main.py` → `mcp_server.py` |
| REST API + Swagger + dashboard | `api_server.py`, `web/` |
| Контракты инструментов | `docs/MCP_TOOL_CONTRACTS.md` |
| Манифест для площадки | `marketplace/manifest.json` |
| Безопасность | `docs/SECURITY.md` (RBAC, ключи, лимиты) |

## Цены (рекомендация, финальное решение — владелец)

| Tier | Условия |
|---|---|
| Free | 100 req/h, market+defi, анонимно |
| Pro | 1000 req/h, on-chain + intelligence + Portfolio Doctor |
| Enterprise / деплой под ключ | White-label, dedicated, SLA — B2B-договор (РФ, фиат) |

## Чек-лист публикации на площадке

- [ ] Подтвердить способ выплат площадки (Dealwork: USD/USDC; OKX: USDT X Layer — санкционные риски)
- [ ] Зарегистрировать агент-профиль и приложить `manifest.json`
- [ ] Demo-запуск: анонимный free tier + `DEMO` бейдж в UI
- [ ] Приложить 2–3 реальных примера ответов (envelope с source/freshness)
- [ ] Указать ограничения честно (whale free-tier, AI-ключи)

## FAQ (для карточки)

**Есть ли фейковые данные?** Нет. Моки выпилены; регрессионные тесты следят за этим.
**Что если провайдер недоступен?** Ответ приходит с `degraded`/`UNAVAILABLE` и причиной — без выдуманных чисел.
**Можно ли торговать через вас?** Нет. Платформа read-only: аналитика и интерпретация, без исполнения сделок.
**Нужен ли API-ключ?** Для free tier — нет. Для whale-инструментов — бесплатный Etherscan-ключ.
