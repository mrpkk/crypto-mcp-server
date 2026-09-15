"""Pydantic schemas for structured LLM outputs (validated, no free-form numbers)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SentimentResult(BaseModel):
    sentiment: Literal["bullish", "bearish", "neutral"]
    score: int = Field(ge=0, le=100, description="0 = extreme fear, 100 = extreme greed")
    key_factors: list[str] = Field(default_factory=list, description="Up to 5 factors")
    outlook: str = Field(description="One-two sentence short-term outlook")


class YieldAssessmentResult(BaseModel):
    score: int = Field(ge=1, le=10, description="Risk-adjusted attractiveness 1-10")
    recommendation: Literal["avoid", "caution", "neutral", "attractive"]
    risks: list[str] = Field(default_factory=list)
    reasoning: str


class TradingSignalResult(BaseModel):
    action: Literal["buy", "sell", "hold"]
    confidence: int = Field(ge=0, le=100)
    reasoning: str
    stop_loss: float | None = None
    take_profit: float | None = None
