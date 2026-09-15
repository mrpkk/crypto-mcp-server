"""In-process sliding-window rate limiter (per API key / per client IP).

Tier-aware: free (100 req/h) and pro (1000 req/h) by default; tier is resolved
from the API key when the keying subsystem is enabled, otherwise `free`.
Health/readiness probes are exempt so monitoring never gets throttled.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

FREE_LIMIT_PER_HOUR = 100
PRO_LIMIT_PER_HOUR = 1000
WINDOW_SECONDS = 3600

EXEMPT_PATHS = {"/health", "/ready", "/metrics", "/docs", "/openapi.json", "/redoc", "/favicon.ico"}


@dataclass
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    reset_after: float


@dataclass
class RateLimiter:
    """Sliding-window log limiter. Thread/async safe enough for a single process."""

    window: int = WINDOW_SECONDS
    _hits: dict[str, deque[float]] = field(default_factory=dict)

    def check(self, key: str, limit: int, now: float | None = None) -> RateLimitDecision:
        now = now if now is not None else time.time()
        hits = self._hits.setdefault(key, deque())
        cutoff = now - self.window
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= limit:
            reset_after = round(hits[0] + self.window - now, 1)
            return RateLimitDecision(False, limit, 0, max(reset_after, 0.0))
        hits.append(now)
        return RateLimitDecision(True, limit, limit - len(hits), 0.0)

    def reset(self, key: str | None = None) -> None:
        if key is None:
            self._hits.clear()
        else:
            self._hits.pop(key, None)


def resolve_tier(api_key: str | None, pro_keys: set[str] | None = None) -> str:
    """Return 'pro' for known pro keys, otherwise 'free'. Real key registry arrives in S4."""
    if api_key and pro_keys and api_key in pro_keys:
        return "pro"
    return "free"


def limit_for_tier(tier: str) -> int:
    return PRO_LIMIT_PER_HOUR if tier == "pro" else FREE_LIMIT_PER_HOUR


def client_identity(headers: dict[str, Any], client_host: str | None) -> str:
    api_key = headers.get("x-api-key")
    if api_key:
        return f"key:{api_key}"
    return f"ip:{client_host or 'unknown'}"
