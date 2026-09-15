"""S5 tests: LLM chain (circuit breaker, fallback), structured outputs, analyst contracts."""
import json

import pytest

from ai.analyst import CryptoAnalyst
from ai.llm import CircuitBreaker, LLMClient, LLMUnavailable, _extract_json
from ai.schemas import SentimentResult

# ---------- Circuit breaker ----------

def test_breaker_allows_until_threshold():
    breaker = CircuitBreaker(failure_threshold=2, cooldown_seconds=60)
    assert breaker.allow("p", now=0)
    breaker.record_failure("p", now=0)
    assert breaker.allow("p", now=1)
    breaker.record_failure("p", now=1)
    assert not breaker.allow("p", now=2)  # open


def test_breaker_recovers_after_cooldown():
    breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=60)
    breaker.record_failure("p", now=0)
    assert not breaker.allow("p", now=30)
    assert breaker.allow("p", now=61)


def test_breaker_success_resets():
    breaker = CircuitBreaker(failure_threshold=2)
    breaker.record_failure("p", now=0)
    breaker.record_success("p")
    breaker.record_failure("p", now=1)
    assert breaker.allow("p", now=2)


# ---------- JSON extraction ----------

def test_extract_json_plain():
    assert _extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_code_fence():
    text = '```json\n{"sentiment": "bullish", "score": 70}\n```'
    assert _extract_json(text)["sentiment"] == "bullish"


def test_extract_json_with_prose():
    text = 'Here is the result: {"action": "hold"} — done.'
    assert _extract_json(text) == {"action": "hold"}


def test_extract_json_missing_raises():
    with pytest.raises(ValueError):
        _extract_json("no json here")


# ---------- Provider chain ----------

@pytest.mark.asyncio
async def test_chain_falls_back_to_second_provider(monkeypatch):
    client = LLMClient(api_key="test-key")
    calls = []

    async def fake_call(provider, system, user, temperature, max_tokens):
        calls.append(provider["name"])
        if provider["name"] == client.providers[0]["name"]:
            raise RuntimeError("first provider down")
        return "second provider answer"

    monkeypatch.setattr(client, "_call_provider", fake_call)
    result = await client.complete("sys", "user")

    assert result["text"] == "second provider answer"
    assert calls[0] == client.providers[0]["name"]
    assert result["provider"] == client.providers[1]["name"]


@pytest.mark.asyncio
async def test_chain_all_fail_raises(monkeypatch):
    client = LLMClient(api_key="test-key")

    async def fake_call(provider, system, user, temperature, max_tokens):
        raise RuntimeError("down")

    monkeypatch.setattr(client, "_call_provider", fake_call)
    with pytest.raises(LLMUnavailable):
        await client.complete("sys", "user")


# ---------- Structured outputs ----------

@pytest.mark.asyncio
async def test_complete_structured_valid(monkeypatch):
    client = LLMClient(api_key="test-key")

    async def fake_call(provider, system, user, temperature, max_tokens):
        return json.dumps({"sentiment": "bullish", "score": 72, "key_factors": ["volume"], "outlook": "up"})

    monkeypatch.setattr(client, "_call_provider", fake_call)
    result = await client.complete_structured("sys", "user", SentimentResult)

    assert isinstance(result["parsed"], SentimentResult)
    assert result["parsed"].score == 72


@pytest.mark.asyncio
async def test_complete_structured_repair_once(monkeypatch):
    client = LLMClient(api_key="test-key")
    responses = iter(["not json at all", json.dumps({"sentiment": "bearish", "score": 20, "outlook": "down"})])

    async def fake_call(provider, system, user, temperature, max_tokens):
        return next(responses)

    monkeypatch.setattr(client, "_call_provider", fake_call)
    result = await client.complete_structured("sys", "user", SentimentResult, repair_attempts=1)

    assert result["parsed"].sentiment == "bearish"


@pytest.mark.asyncio
async def test_complete_structured_invalid_after_repair(monkeypatch):
    client = LLMClient(api_key="test-key")
    real_complete = client.complete

    async def fake_complete(system, user, temperature=0.3, max_tokens=2000):
        return {"text": "still not json", "provider": "fake", "model": "fake-model"}

    monkeypatch.setattr(client, "complete", fake_complete)
    with pytest.raises(LLMUnavailable):
        await client.complete_structured("sys", "user", SentimentResult, repair_attempts=0)
    monkeypatch.setattr(client, "complete", real_complete)


# ---------- Analyst contracts ----------

@pytest.mark.asyncio
async def test_market_sentiment_returns_envelope(monkeypatch):
    analyst = CryptoAnalyst(api_key="test-key")
    parsed = SentimentResult(sentiment="neutral", score=50, key_factors=["flat"], outlook="sideways")

    async def fake_structured(system, user, schema, temperature=0.2, repair_attempts=1):
        return {"parsed": parsed, "provider": "TestProvider", "model": "test-model"}

    monkeypatch.setattr(analyst.llm, "complete_structured", fake_structured)
    out = await analyst.market_sentiment("BTC", -1.5, 1e9)

    assert set(out) == {"data", "meta"}
    assert out["data"]["sentiment"] == "neutral"
    assert out["meta"]["source"].startswith("llm:TestProvider")
    assert out["meta"]["disclaimer"] == "Not financial advice."


@pytest.mark.asyncio
async def test_market_sentiment_unavailable_is_error_contract(monkeypatch):
    analyst = CryptoAnalyst(api_key="test-key")

    async def failing(system, user, schema, temperature=0.2, repair_attempts=1):
        raise LLMUnavailable(["all providers down"])

    monkeypatch.setattr(analyst.llm, "complete_structured", failing)
    out = await analyst.market_sentiment("BTC", 0.0, 0.0)

    assert out["error"]["code"] == "AI_UNAVAILABLE"
    assert out["error"]["retryable"] is True


@pytest.mark.asyncio
async def test_analyst_health(monkeypatch):
    analyst = CryptoAnalyst(api_key="test-key")
    health = await analyst.health()
    assert health["provider"] == "llm-chain"
    assert health["configured"] is True
