"""CryptoAnalyst — structured AI interpretation over real inputs.

Pipeline: REAL DATA (provided by callers/tools) → deterministic formatting →
LLM interpretation → Pydantic validation → canonical envelope.
The LLM is never a data source; unavailable AI yields an honest error contract.
"""
from __future__ import annotations

from typing import Any

from ai.llm import LLMClient, LLMUnavailable
from ai.schemas import SentimentResult, TradingSignalResult, YieldAssessmentResult
from providers.base import make_envelope, make_error

SENTIMENT_SYSTEM = (
    "You are a crypto market analyst. You interpret market data; you NEVER invent numbers. "
    "Use only the numbers provided. Be concise and objective."
)
YIELD_SYSTEM = (
    "You are a DeFi yield analyst. You assess risk/reward from the provided numbers only. "
    "Never invent APY, TVL or protocol facts."
)
SIGNAL_SYSTEM = (
    "You are a crypto trading analyst. Generate a concise signal from the provided indicators only. "
    "You are not a financial advisor; reasoning must reference only the given values."
)


class CryptoAnalyst:
    def __init__(self, api_key: str = "", fallback_key: str = ""):
        self.llm = LLMClient(api_key=api_key, fallback_key=fallback_key)

    # -- compatibility properties (used by api_server/mcp_server) --
    @property
    def api_key(self) -> str:
        return self.llm.api_key

    @api_key.setter
    def api_key(self, value: str) -> None:
        self.llm.api_key = value

    @property
    def fallback_key(self) -> str:
        return self.llm.fallback_key

    @fallback_key.setter
    def fallback_key(self, value: str) -> None:
        self.llm.fallback_key = value

    async def _structured(self, system: str, user: str, schema: Any) -> dict[str, Any]:
        try:
            result = await self.llm.complete_structured(system, user, schema)
        except LLMUnavailable as exc:
            return make_error(
                "AI_UNAVAILABLE",
                str(exc),
                "Retry shortly — deterministic tools keep working without AI",
                retryable=True,
            )
        parsed = result["parsed"]
        return make_envelope(
            parsed.model_dump(),
            source=f"llm:{result['provider']} ({result['model']})",
            warnings=["AI interpretation, not financial advice"],
        )

    async def market_sentiment(self, symbol: str, price_change_24h: float, volume_usd: float) -> dict[str, Any]:
        user = (
            f"Analyze {symbol} using ONLY these real inputs:\n"
            f"- 24h price change: {price_change_24h:+.2f}%\n"
            f"- 24h volume: ${volume_usd:,.0f}\n"
            "Return sentiment, a 0-100 greed/fear score, up to 5 key factors and a short outlook."
        )
        return await self._structured(SENTIMENT_SYSTEM, user, SentimentResult)

    async def yield_assessment(self, protocol: str, apy: float, tvl: float, risk_factors: list[str]) -> dict[str, Any]:
        user = (
            f"Assess {protocol} using ONLY these real inputs:\n"
            f"- APY: {apy:.2f}%\n"
            f"- TVL: ${tvl:,.0f}\n"
            f"- Known risk factors: {', '.join(risk_factors) or 'none provided'}\n"
            "Return a 1-10 score, a recommendation, risks and reasoning."
        )
        return await self._structured(YIELD_SYSTEM, user, YieldAssessmentResult)

    async def trading_signal(
        self,
        symbol: str,
        price: float,
        rsi: float,
        macd: str,
        volume_trend: str,
        news: list[str] | None = None,
    ) -> dict[str, Any]:
        user = (
            f"Generate a signal for {symbol} using ONLY these real inputs:\n"
            f"- Price: ${price}\n- RSI(14): {rsi}\n- MACD: {macd}\n- Volume trend: {volume_trend}\n"
            f"- Recent news: {'; '.join((news or [])[:3]) or 'none provided'}\n"
            "Return action (buy/sell/hold), confidence 0-100, reasoning, optional stop-loss and take-profit."
        )
        return await self._structured(SIGNAL_SYSTEM, user, TradingSignalResult)

    async def health(self) -> dict[str, Any]:
        return await self.llm.health()
