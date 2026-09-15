# MCP TOOL CONTRACTS — v2

> Каждый инструмент возвращает canonical envelope `{data, meta}` или error contract `{error:{code,message,retryable,suggested_action}}`.
> Обновляется вместе с реестром; источник истины — `mcp_server.py`.

## Tool: `get_price`
**Purpose:** Get the latest price for a crypto pair on an exchange (CCXT).
**Input:** `symbol`='BTC/USDT', `exchange`='binance'
**Output:** envelope `{data, meta}` (или error contract)
**Source:** CCXT pooled
**Freshness:** 10s cache
**Cost class:** free
**Rate limit:** 100/h free
**Failure modes:** UNSUPPORTED_EXCHANGE, NO_DATA, FETCH_FAILED

## Tool: `compare_prices`
**Purpose:** Compare a pair across exchanges and compute the arbitrage spread.
**Input:** `symbol`='BTC/USDT'
**Output:** envelope `{data, meta}` (или error contract)
**Source:** CCXT pooled
**Freshness:** 10s cache
**Cost class:** free
**Rate limit:** 100/h free
**Failure modes:** NO_DATA

## Tool: `get_top_crypto`
**Purpose:** Top cryptocurrencies by 24h volume with price, change and market cap.
**Input:** `limit`=10
**Output:** envelope `{data, meta}` (или error contract)
**Source:** CoinGecko
**Freshness:** 300s
**Cost class:** free
**Rate limit:** 100/h free
**Failure modes:** COINGECKO_UNAVAILABLE

## Tool: `get_yields`
**Purpose:** DeFi yield pools from DeFi Llama filtered by chain and minimum APY.
**Input:** `min_apy`=0, `chain`='all', `max_results`=20
**Output:** envelope `{data, meta}` (или error contract)
**Source:** DeFi Llama
**Freshness:** 300s
**Cost class:** free
**Rate limit:** 100/h free
**Failure modes:** DEFI_LLAMA_UNAVAILABLE

## Tool: `technical_analysis`
**Purpose:** Technical indicators (RSI-14 Wilder, MACD, MA50/200, support/resistance) from real OHLCV.
**Input:** `symbol`='BTC/USDT', `price`=0, `exchange`='binance'
**Output:** envelope `{data, meta}` (или error contract)
**Source:** CCXT OHLCV
**Freshness:** 1d candles
**Cost class:** free
**Rate limit:** 100/h free
**Failure modes:** OHLCV_UNAVAILABLE

## Tool: `analyze_token`
**Purpose:** Token fundamentals with live price; metrics you did not provide are returned as null with warnings.
**Input:** `symbol`='BTC', `price_usd`=0, `market_cap`=0
**Output:** envelope `{data, meta}` (или error contract)
**Source:** CCXT + CoinGecko global
**Freshness:** 10s
**Cost class:** free
**Rate limit:** 100/h free
**Failure modes:** PRICE_UNAVAILABLE, BAD_SYMBOL

## Tool: `portfolio_health`
**Purpose:** Portfolio concentration/diversification from real holdings: [{symbol, amount} or {symbol, value_usd}].
**Input:** `holdings`=None
**Output:** envelope `{data, meta}` (или error contract)
**Source:** CCXT live valuation
**Freshness:** 10s
**Cost class:** free
**Rate limit:** 100/h free
**Failure modes:** EMPTY_PORTFOLIO, ZERO_VALUE

## Tool: `gas_tracker`
**Purpose:** Live gas prices for 6 EVM chains (Ethereum, BSC, Polygon, Arbitrum, Optimism, Base) with USD cost estimates.
**Input:** `chain`='ethereum'
**Output:** envelope `{data, meta}` (или error contract)
**Source:** Web3 RPC x3 fallback
**Freshness:** 15s cache
**Cost class:** free
**Rate limit:** 100/h free
**Failure modes:** UNSUPPORTED_CHAIN, RPC_UNAVAILABLE

## Tool: `estimate_tx_cost`
**Purpose:** Estimate transaction cost in native token and USD for a gas amount and speed.
**Input:** `chain`='ethereum', `gas_units`=21000, `speed`='standard'
**Output:** envelope `{data, meta}` (или error contract)
**Source:** gas + live native price
**Freshness:** 15s
**Cost class:** free
**Rate limit:** 100/h free
**Failure modes:** BAD_SPEED

## Tool: `market_sentiment`
**Purpose:** AI interpretation of market sentiment from the provided real inputs (LLM interpretation, not data).
**Input:** `symbol`='BTC', `price_change_24h`=0, `volume_usd`=0
**Output:** envelope `{data, meta}` (или error contract)
**Source:** LLM chain
**Freshness:** n/a
**Cost class:** llm
**Rate limit:** 100/h free
**Failure modes:** AI_UNAVAILABLE

## Tool: `yield_assessment`
**Purpose:** AI assessment of a DeFi pool's risk/reward given protocol, APY, TVL and risk factors.
**Input:** `protocol`='unknown', `apy`=0, `tvl`=0, `risk_factors`=None
**Output:** envelope `{data, meta}` (или error contract)
**Source:** LLM chain
**Freshness:** n/a
**Cost class:** llm
**Rate limit:** 100/h free
**Failure modes:** AI_UNAVAILABLE

## Tool: `trading_signal`
**Purpose:** AI trading signal interpretation from indicators you provide (LLM interpretation, not financial advice).
**Input:** `symbol`='BTC/USDT', `price`=0, `rsi`=50, `macd`='neutral', `volume_trend`='stable'
**Output:** envelope `{data, meta}` (или error contract)
**Source:** LLM chain
**Freshness:** n/a
**Cost class:** llm
**Rate limit:** 100/h free
**Failure modes:** AI_UNAVAILABLE

## Tool: `track_whale`
**Purpose:** Recent large transfers for an EVM address via Etherscan V2 (free tier: latest transactions only).
**Input:** `address`, `chain`='ethereum', `min_value_usd`=100000, `limit`=25
**Output:** envelope `{data, meta}` (или error contract)
**Source:** Etherscan V2
**Freshness:** 60s cache
**Cost class:** free
**Rate limit:** 100/h free
**Failure modes:** BAD_ADDRESS, MISSING_API_KEY, PROVIDER_UNAVAILABLE

## Tool: `whale_alerts`
**Purpose:** Large transfers across watchlist addresses (set WHALE_WATCHLIST in ~/.env or pass addresses).
**Input:** `min_value_usd`=1000000, `timeframe_hours`=24, `addresses`=None, `chain`='ethereum'
**Output:** envelope `{data, meta}` (или error contract)
**Source:** Etherscan V2 + watchlist
**Freshness:** 60s cache
**Cost class:** free
**Rate limit:** 100/h free
**Failure modes:** NOT_CONFIGURED, BAD_ADDRESS
