import httpx
from typing import Any
from datetime import datetime


PROVIDERS = [
    {"name": "GitHub Models", "url": "https://models.inference.ai.azure.com/chat/completions", "model": "gpt-4o"},
    {"name": "GitHub Models Mini", "url": "https://models.inference.ai.azure.com/chat/completions", "model": "gpt-4o-mini"},
    {"name": "GitHub Llama", "url": "https://models.inference.ai.azure.com/chat/completions", "model": "Meta-Llama-3.1-405B-Instruct"},
]


class CryptoAnalyst:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.fallback_key = ""

    @property
    def _active_key(self) -> str:
        return self.api_key or self.fallback_key

    async def analyze(self, system: str, prompt: str) -> str:
        key = self._active_key
        if not key:
            return self._fallback_analysis(prompt)

        errors = []
        for provider in PROVIDERS:
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(
                        provider["url"],
                        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                        json={
                            "model": provider["model"],
                            "messages": [
                                {"role": "system", "content": system},
                                {"role": "user", "content": prompt},
                            ],
                            "max_tokens": 2000,
                            "temperature": 0.3,
                        },
                    )
                    if resp.status_code != 200:
                        errors.append(f"{provider['name']}: {resp.status_code}")
                        continue
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                errors.append(f"{provider['name']}: {e}")
                continue

        return self._fallback_analysis(prompt, errors)

    def _fallback_analysis(self, prompt: str, errors: list[str] | None = None) -> str:
        err_msg = f" ({'; '.join(errors[:2])})" if errors else ""
        return f"AI analysis unavailable{err_msg}.\nRequested: {prompt[:100]}..."

    async def market_sentiment(self, symbol: str, price_change_24h: float, volume_usd: float) -> dict[str, Any]:
        system = "You are a crypto market analyst. Analyze market data and provide concise sentiment analysis."
        prompt = f"""Analyze {symbol}:
- 24h price change: {price_change_24h:+.2f}%
- 24h volume: ${volume_usd:,.0f}

Provide: sentiment (bullish/bearish/neutral: 0-100), key levels, short outlook."""
        text = await self.analyze(system, prompt)
        return {"symbol": symbol, "analysis": text, "timestamp": datetime.utcnow().isoformat()}

    async def yield_assessment(self, protocol: str, apy: float, tvl: float, risk_factors: list[str]) -> dict[str, Any]:
        system = "You are a DeFi yield analyst. Assess yield opportunities and risks."
        prompt = f"""Assess {protocol} yield opportunity:
- APY: {apy:.2f}%
- TVL: ${tvl:,.0f}
- Risks: {', '.join(risk_factors)}

Score 1-10 and provide recommendation."""
        text = await self.analyze(system, prompt)
        return {"protocol": protocol, "apy": apy, "assessment": text, "timestamp": datetime.utcnow().isoformat()}

    async def trading_signal(self, symbol: str, price: float, rsi: float, macd: str, volume_trend: str, news: list[str]) -> dict[str, Any]:
        system = "You are a crypto trading analyst. Generate concise trading signals based on technical analysis."
        prompt = f"""Generate signal for {symbol}:
- Price: ${price}
- RSI(14): {rsi}
- MACD: {macd}
- Volume trend: {volume_trend}
- Recent news: {'; '.join(news[:3])}

Provide: action (buy/sell/hold), confidence (0-100), reasoning, stop-loss, take-profit."""
        text = await self.analyze(system, prompt)
        return {"symbol": symbol, "price": price, "signal": text, "timestamp": datetime.utcnow().isoformat()}
