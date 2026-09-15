# MCP VERSION STRATEGY — v2

> Статус: миграция на mcp>=2.0 **уже выполнена** в слайсе 11 (сервер был сломан
> на старом API `@server.list_tools`). Документ фиксирует стратегию и дальнейшие шаги.

## Сделано (v2.0.0)

- `mcp_server.py` переписан на `mcp.server.mcpserver.MCPServer` (mcp 2.0 API).
- 14 tools зарегистрированы через `@mcp.tool(name=..., description=...)`; схемы генерируются
  из сигнатур функций (типы + дефолты) — вручную поддерживаемых JSON-схем больше нет.
- `handle_list_tools` → `mcp.list_tools()`; REST `/capabilities` использует тот же реестр.
- Smoke-проверка: `python3 main.py` стартует без ошибок, инструменты валидируются тестом реестра.

## Целевая архитектура MCP (ориентир 2026)

| Направление | Статус в проекте | Следующий шаг |
|---|---|---|
| stdio-транспорт | ✅ работает | — |
| Stateless core (2026 спецификация) | ⚠️ не применимо для stdio | remote/HTTP MCP — S8 (marketplace pack) |
| Cacheable list results | ⚠️ | рассмотреть cache hints при переходе на Streamable HTTP |
| Tasks (долгие операции) | ➖ | backtest/audit — кандидаты после S8 |
| MCP Apps (embedded UI) | ➖ | только после проверки совместимости клиентов |
| Authorization hardening | ✅ REST-часть (RBAC, ключи) | токены для remote MCP в S8 |

## Принципы совместимости

1. Имена инструментов и их входные параметры — **не изменяются** между минорными версиями.
2. Выходы обогащаются аддитивно (envelope уже введён; новые поля — только добавление).
3. Перед апгрейдом SDK — прогнать `tests/test_registry.py` и smoke `main.py`.

## Риски

- SDK 2.x молод: следить за changelog, пин версии в `requirements.txt`.
- При добавлении remote-транспорта — отдельный STOP GATE (сетевой доступ, авторизация).
