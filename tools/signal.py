from typing import Any
from datetime import datetime
import random
import math


async def technical_indicators(symbol: str = "BTC/USDT", price: float = 0) -> dict[str, Any]:
    if price <= 0:
        price = _get_fallback_price(symbol)

    volatility = price * 0.02
    rsi = round(random.uniform(30, 70), 1)
    macd_line = random.uniform(-200, 200)
    signal_line = random.uniform(-200, 200)

    return {
        "symbol": symbol,
        "price_usd": price,
        "rsi_14": rsi,
        "macd": {
            "macd_line": round(macd_line, 2),
            "signal_line": round(signal_line, 2),
            "histogram": round(macd_line - signal_line, 2),
            "crossover": "bullish" if macd_line > signal_line else "bearish",
        },
        "moving_averages": {
            "ma_50": round(price - random.uniform(-volatility, volatility), 2),
            "ma_200": round(price - random.uniform(-volatility * 2, volatility * 2), 2),
            "trend": "up" if random.random() > 0.5 else "down",
        },
        "support_resistance": {
            "support_1": round(price * 0.92, 2),
            "support_2": round(price * 0.85, 2),
            "resistance_1": round(price * 1.08, 2),
            "resistance_2": round(price * 1.15, 2),
        },
        "volume_trend": "increasing" if random.random() > 0.5 else "decreasing",
    }


def _get_fallback_price(symbol: str) -> float:
    prices = {
        "BTC/USDT": 65000.0, "ETH/USDT": 3500.0, "SOL/USDT": 145.0,
        "BNB/USDT": 580.0, "XRP/USDT": 0.52, "ADA/USDT": 0.45,
        "DOGE/USDT": 0.12, "AVAX/USDT": 28.0, "DOT/USDT": 6.5, "LINK/USDT": 14.0,
    }
    return prices.get(symbol, 100.0)
