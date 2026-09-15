"""LLM provider chain: GigaChat → GitHub Models (+mini/llama), circuit breaker, timeouts.

Interpretation only: the LLM never produces market numbers — it receives
deterministic values from tools and returns structured JSON assessments.
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.expanduser("~/.env"), override=True)
except Exception as exc:  # pragma: no cover - env loading is best-effort
    logger.debug("dotenv not available: %s", exc)


class LLMUnavailable(Exception):
    """Raised when every provider in the chain failed."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("AI unavailable: " + "; ".join(errors[:3]))


class CircuitBreaker:
    """Skip a provider after repeated failures, retry after cooldown."""

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 120.0):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._failures: dict[str, int] = {}
        self._opened_at: dict[str, float] = {}

    def allow(self, provider_name: str, now: float | None = None) -> bool:
        now = now if now is not None else time.time()
        opened = self._opened_at.get(provider_name)
        if opened is None:
            return True
        if now - opened >= self.cooldown_seconds:
            self._opened_at.pop(provider_name, None)
            self._failures[provider_name] = 0
            return True
        return False

    def record_success(self, provider_name: str) -> None:
        self._failures[provider_name] = 0
        self._opened_at.pop(provider_name, None)

    def record_failure(self, provider_name: str, now: float | None = None) -> None:
        now = now if now is not None else time.time()
        count = self._failures.get(provider_name, 0) + 1
        self._failures[provider_name] = count
        if count >= self.failure_threshold:
            self._opened_at[provider_name] = now

    def snapshot(self) -> dict[str, Any]:
        return {
            "failures": dict(self._failures),
            "open": sorted(self._opened_at),
        }


def _build_providers() -> list[dict[str, Any]]:
    return [
        {
            "name": "GigaChat",
            "url": "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            "model": "GigaChat-Max",
            "giga": True,
            "oauth_url": "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            "scope": os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS"),
            "auth_key": os.getenv("GIGACHAT_AUTH_KEY", ""),
        },
        {"name": "GitHub Models", "url": "https://models.inference.ai.azure.com/chat/completions", "model": "gpt-4o"},
        {"name": "GitHub Models Mini", "url": "https://models.inference.ai.azure.com/chat/completions", "model": "gpt-4o-mini"},
        {
            "name": "GitHub Llama",
            "url": "https://models.inference.ai.azure.com/chat/completions",
            "model": "Meta-Llama-3.1-405B-Instruct",
        },
    ]


class LLMClient:
    """Sequential provider chain with breaker, timeouts and structured JSON parsing."""

    def __init__(self, api_key: str = "", fallback_key: str = "", timeout: float = 30.0):
        self.api_key = api_key
        self.fallback_key = fallback_key
        self.timeout = timeout
        self.providers = _build_providers()
        self.breaker = CircuitBreaker()
        self._giga_token: str | None = None
        self._giga_expires_at: float = 0.0

    @property
    def configured(self) -> bool:
        return bool(self.api_key or self.fallback_key or self.providers[0]["auth_key"])

    async def _giga_access_token(self) -> str | None:
        giga = self.providers[0]
        if not giga["auth_key"]:
            return None
        now = time.time()
        if self._giga_token and self._giga_expires_at > now + 60:
            return self._giga_token
        try:
            async with httpx.AsyncClient(timeout=15, verify=False) as client:
                resp = await client.post(
                    giga["oauth_url"],
                    data={"scope": giga["scope"]},
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                        "RqUID": "6f0b1291-c7f3-43c6-bb2e-9f3efb2dc98e",
                        "Authorization": f"Basic {giga['auth_key']}",
                    },
                )
            if resp.status_code >= 400:
                return None
            data = resp.json()
            token = data.get("access_token")
            if token:
                self._giga_token = token
                self._giga_expires_at = now + data.get("expires_in", 1800) - 60
                return token
        except Exception as exc:
            logger.debug("GigaChat token fetch failed: %s", exc)
        return None

    async def _call_provider(
        self, provider: dict[str, Any], system: str, user: str, temperature: float, max_tokens: int
    ) -> str:
        if provider.get("giga"):
            access_token = await self._giga_access_token()
            if not access_token:
                raise RuntimeError("no access token")
            auth_header = f"Bearer {access_token}"
            verify_ssl = False
        else:
            key = self.api_key or self.fallback_key
            if not key:
                raise RuntimeError("no API key")
            auth_header = f"Bearer {key}"
            verify_ssl = True
        async with httpx.AsyncClient(timeout=self.timeout, verify=verify_ssl) as client:
            resp = await client.post(
                provider["url"],
                headers={"Authorization": auth_header, "Content-Type": "application/json"},
                json={
                    "model": provider["model"],
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}")
        payload = resp.json()
        text = payload["choices"][0]["message"]["content"]
        if not text:
            raise RuntimeError("empty completion")
        return text

    async def complete(self, system: str, user: str, temperature: float = 0.3, max_tokens: int = 2000) -> dict[str, Any]:
        """Try providers in order. Returns {'text', 'provider', 'model'} or raises LLMUnavailable."""
        if not self.configured:
            raise LLMUnavailable(["no LLM credentials configured"])
        errors: list[str] = []
        for provider in self.providers:
            if not self.breaker.allow(provider["name"]):
                errors.append(f"{provider['name']}: circuit open")
                continue
            try:
                text = await self._call_provider(provider, system, user, temperature, max_tokens)
                self.breaker.record_success(provider["name"])
                return {"text": text, "provider": provider["name"], "model": provider["model"]}
            except Exception as exc:
                self.breaker.record_failure(provider["name"])
                errors.append(f"{provider['name']}: {exc}")
                continue
        raise LLMUnavailable(errors)

    async def complete_structured(
        self,
        system: str,
        user: str,
        schema: Any,
        temperature: float = 0.2,
        repair_attempts: int = 1,
    ) -> dict[str, Any]:
        """Ask the LLM for JSON matching a Pydantic schema; repair once, then fail."""
        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        instruction = f"{user}\n\nRespond with a single JSON object matching this schema (no markdown):\n{schema_json}"
        result = await self.complete(system, instruction, temperature=temperature)
        text = result["text"]
        try:
            parsed = schema.model_validate(_extract_json(text))
            return {"parsed": parsed, "provider": result["provider"], "model": result["model"]}
        except Exception as exc:
            if repair_attempts <= 0:
                raise LLMUnavailable([f"invalid structured output: {exc}"]) from exc
            repair_prompt = (
                f"Your previous output was not valid JSON for the schema ({exc}). "
                f"Return ONLY the JSON object matching the schema:\n{schema_json}"
            )
            repaired = await self.complete(system, repair_prompt, temperature=0.0)
            parsed = schema.model_validate(_extract_json(repaired["text"]))
            return {"parsed": parsed, "provider": repaired["provider"], "model": repaired["model"]}

    async def health(self) -> dict[str, Any]:
        return {
            "provider": "llm-chain",
            "status": "ok" if self.configured else "degraded",
            "configured": self.configured,
            "chain": [p["name"] for p in self.providers],
            "breaker": self.breaker.snapshot(),
        }


def _extract_json(text: str) -> Any:
    """Extract the first JSON object from raw LLM text (tolerates prose and code fences)."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("no JSON object found in LLM output")
    return json.loads(cleaned[start : end + 1])
