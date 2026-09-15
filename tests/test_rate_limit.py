"""S3 tests: sliding-window rate limiter + FastAPI middleware integration."""
import pytest

import api_server
from rate_limit import (
    FREE_LIMIT_PER_HOUR,
    PRO_LIMIT_PER_HOUR,
    RateLimiter,
    client_identity,
    limit_for_tier,
    resolve_tier,
)


def test_limiter_allows_under_limit():
    limiter = RateLimiter()
    for i in range(3):
        decision = limiter.check("k", limit=3, now=1000.0 + i)
        assert decision.allowed
        assert decision.remaining == 3 - (i + 1)


def test_limiter_blocks_over_limit():
    limiter = RateLimiter()
    for i in range(3):
        limiter.check("k", limit=3, now=1000.0 + i)
    decision = limiter.check("k", limit=3, now=1003.0)
    assert not decision.allowed
    assert decision.remaining == 0
    assert decision.reset_after > 0


def test_limiter_window_expires():
    limiter = RateLimiter()
    for i in range(3):
        limiter.check("k", limit=3, now=1000.0 + i)
    decision = limiter.check("k", limit=3, now=1000.0 + 3601)
    assert decision.allowed


def test_limiter_per_key_isolation():
    limiter = RateLimiter()
    for i in range(3):
        limiter.check("key-a", limit=3, now=1000.0 + i)
    decision = limiter.check("key-b", limit=3, now=1004.0)
    assert decision.allowed


def test_tier_resolution_and_limits():
    assert resolve_tier(None, set()) == "free"
    assert resolve_tier("unknown", {"pro1"}) == "free"
    assert resolve_tier("pro1", {"pro1"}) == "pro"
    assert limit_for_tier("free") == FREE_LIMIT_PER_HOUR
    assert limit_for_tier("pro") == PRO_LIMIT_PER_HOUR


def test_client_identity():
    assert client_identity({"x-api-key": "abc"}, "1.2.3.4") == "key:abc"
    assert client_identity({}, "1.2.3.4") == "ip:1.2.3.4"


@pytest.fixture()
def client(monkeypatch):
    from fastapi.testclient import TestClient

    api_server.rate_limiter.reset()
    monkeypatch.setattr("api_server.limit_for_tier", lambda tier: 2)
    yield TestClient(api_server.app)
    api_server.rate_limiter.reset()


def test_middleware_blocks_third_request(client):
    assert client.get("/version").status_code == 200
    assert client.get("/version").status_code == 200
    response = client.get("/version")
    assert response.status_code == 429
    body = response.json()
    assert body["error"]["code"] == "RATE_LIMITED"
    assert response.headers["Retry-After"]


def test_middleware_headers(client):
    response = client.get("/version")
    assert response.headers["X-RateLimit-Limit"] == "2"
    assert response.headers["X-RateLimit-Remaining"] == "1"


def test_health_is_exempt(client):
    for _ in range(5):
        assert client.get("/health").status_code == 200
