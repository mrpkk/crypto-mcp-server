# USER FLOWS — Āgama v2

> 10 критических путей. Формат: START · GOAL · STEPS · RESPONSE · FAILURE · SUCCESS.
> Реализованы: 1–8, 10 (MCP/REST/Web). Flow 9 — через `meta.source` в каждом ответе.

## Flow 1 — Connect MCP
- **START:** разработчик ставит сервер (`pip install -r requirements.txt`), запускает `python main.py`.
- **GOAL:** подключить сервер к Claude/Cursor.
- **STEPS:** добавить сервер в конфиг клиента (stdio) → вызвать любой инструмент.
- **RESPONSE:** `mcp.list_tools()` → 14 инструментов с описаниями.
- **FAILURE:** SDK-несовместимость → смоук `main.py`, тест `test_registry.py` (14 tools).
- **SUCCESS:** агент видит инструменты и выполняет `get_price`.

## Flow 2 — Discover tools
- **START:** GET `/capabilities` или `tools/list` в MCP-клиенте.
- **GOAL:** понять, что доступно и с какими лимитами.
- **RESPONSE:** список 14 tools + провайдеры + версия; контракты — `docs/MCP_TOOL_CONTRACTS.md`.
- **SUCCESS:** разработчик выбирает 2–3 инструмента под задачу.

## Flow 3 — Agent asks BTC intelligence
- **START:** агент вызывает `get_price {symbol: "BTC/USDT"}`.
- **GOAL:** цена + источник + свежесть.
- **RESPONSE:** `{data:{price_usd,...}, meta:{source:"ccxt:binance", freshness_seconds, cached, disclaimer}}`.
- **FAILURE:** биржа недоступна → `FETCH_FAILED` (retryable) с подсказкой; агент переключает биржу.
- **SUCCESS:** цена с провенансом; повторный вызов в течение 10s — `cached: true`.

## Flow 4 — Investigate token
- **START:** `GET /analyze/BTC?price_usd=0` (или MCP `analyze_token`).
- **GOAL:** фундаментальный срез без выдуманных метрик.
- **RESPONSE:** живые цены; непереданные поля = `null` + warnings («market_cap not provided»).
- **FAILURE:** `PRICE_UNAVAILABLE` — символ не найден/биржа молчит.
- **SUCCESS:** понятно, какие данные реальные, какие нужно передать.

## Flow 5 — Unusual movement
- **START:** дашборд/агент смотрит top movers `GET /top?limit=8`.
- **GOAL:** увидеть аномалии.
- **RESPONSE:** таблица с ценами/изменениями, бейдж качества у блока.
- **FAILURE:** `COINGECKO_UNAVAILABLE` → блок показывает DEGRADED/UNAVAILABLE, а не плейсхолдеры.
- **SUCCESS:** трейдер видит движение и источник.

## Flow 6 — DeFi yield
- **START:** `GET /yields?min_apy=5&max_results=6`.
- **GOAL:** доходные пулы из живого DeFi Llama.
- **FAILURE:** недоступность — `DEFI_LLAMA_UNAVAILABLE` (никаких хардкод-APY — выпилено в S2).
- **SUCCESS:** топ-пулы с APY/TVL и фильтрами.

## Flow 7 — Gas check
- **START:** `GET /gas/ethereum` или MCP `gas_tracker`.
- **GOAL:** реальные base/priority fee + USD-стоимость типовых транзакций.
- **FAILURE:** все RPC недоступны → `RPC_UNAVAILABLE` (retryable); fallback-цепочка из 3 RPC на сеть.
- **SUCCESS:** кэш 15s, источник = использованный RPC.

## Flow 8 — Whale investigate
- **START:** `GET /whale/{address}` или `track_whale` / `whale_alerts`.
- **GOAL:** крупные реальные переводы.
- **FAILURE:** нет ключа → `MISSING_API_KEY`; пустой watchlist → `NOT_CONFIGURED` с подсказкой.
- **SUCCESS:** транзакции с USD-оценкой (live-цены) и честной пометкой про free-tier покрытие.

## Flow 9 — Understand data source
- **START:** пользователь смотрит на любую метрику.
- **GOAL:** узнать провенанс.
- **STEPS:** клик/чтение `meta.source` + `meta.timestamp` + `freshness_seconds`.
- **SUCCESS:** 100% ответов несут source+timestamp+freshness (инвариант, покрыт тестами).

## Flow 10 — Provider fails
- **START:** внешний провайдер не отвечает (биржи/RPC/DeFiLlama/LLM).
- **GOAL:** контролируемая деградация без выдуманных данных.
- **RESPONSE:** error contract `{code, message, retryable, suggested_action}` или `meta.degraded: true` с warnings.
- **SUCCESS:** агент видит причину и альтернативу; другие инструменты продолжают работать.
