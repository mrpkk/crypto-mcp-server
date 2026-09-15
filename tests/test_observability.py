"""S4 tests: observability — JSON logs, metrics registry, /metrics endpoint."""
import json
import logging

from fastapi.testclient import TestClient

import api_server
from observability import JsonLogFormatter, MetricsRegistry


def test_json_formatter_basic():
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        name="test.logger", level=logging.INFO, pathname=__file__, lineno=1,
        msg="hello %s", args=("world",), exc_info=None,
    )
    record.request_id = "abc123"
    record.latency_ms = 12.5

    payload = json.loads(formatter.format(record))

    assert payload["level"] == "INFO"
    assert payload["message"] == "hello world"
    assert payload["request_id"] == "abc123"
    assert payload["latency_ms"] == 12.5


def test_metrics_counters_and_latency():
    registry = MetricsRegistry()
    registry.inc("tool_calls_total", {"tool": "get_price"})
    registry.inc("tool_calls_total", {"tool": "get_price"})
    registry.observe_latency("tool_latency_seconds", 0.25, {"tool": "get_price"})

    text = registry.render_prometheus()

    assert 'tool_calls_total{tool="get_price"} 2' in text
    assert 'tool_latency_seconds_count{tool="get_price"} 1' in text
    assert 'tool_latency_seconds_sum{tool="get_price"} 0.25' in text


def test_metrics_reset():
    registry = MetricsRegistry()
    registry.inc("x_total")
    registry.reset()
    assert registry.render_prometheus() == ""


def test_metrics_endpoint_and_request_id():
    api_server.rate_limiter.reset()
    client = TestClient(api_server.app)

    response = client.get("/version")

    assert response.headers.get("X-Request-ID")

    metrics_response = client.get("/metrics")
    assert metrics_response.status_code == 200
    assert "http_requests_total" in metrics_response.text
