"""Observability: structured JSON logs + in-process Prometheus-style metrics.

No external dependencies: metrics are held in a thread-safe registry and
rendered in the Prometheus text exposition format at /metrics.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from collections import defaultdict
from typing import Any


class JsonLogFormatter(logging.Formatter):
    """One JSON object per log line: timestamp, level, logger, message, extras."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field_name in ("request_id", "tool", "path", "latency_ms", "status"):
            value = getattr(record, field_name, None)
            if value is not None:
                entry[field_name] = value
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def configure_json_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


class MetricsRegistry:
    """Minimal counters/histogram-summary store with Prometheus text rendering."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
        self._latency_sums: dict[tuple[str, tuple[tuple[str, str], ...]], tuple[float, int]] = {}

    @staticmethod
    def _labels_key(labels: dict[str, str] | None) -> tuple[tuple[str, str], ...]:
        return tuple(sorted((labels or {}).items()))

    def inc(self, name: str, labels: dict[str, str] | None = None, value: float = 1.0) -> None:
        with self._lock:
            self._counters[(name, self._labels_key(labels))] += value

    def observe_latency(self, name: str, seconds: float, labels: dict[str, str] | None = None) -> None:
        key = (name, self._labels_key(labels))
        with self._lock:
            total, count = self._latency_sums.get(key, (0.0, 0))
            self._latency_sums[key] = (total + seconds, count + 1)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            counters = dict(self._counters)
            latencies = dict(self._latency_sums)
        return {"counters": counters, "latencies": latencies}

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._latency_sums.clear()

    def render_prometheus(self) -> str:
        lines: list[str] = []
        with self._lock:
            counters = dict(self._counters)
            latencies = dict(self._latency_sums)
        for (name, label_items), value in sorted(counters.items()):
            labels = _format_labels(label_items)
            lines.append(f"{name}{labels} {value:g}")
        for (name, label_items), (total, count) in sorted(latencies.items()):
            labels = _format_labels(label_items)
            lines.append(f"{name}_count{labels} {count}")
            lines.append(f"{name}_sum{labels} {total:g}")
        return "\n".join(lines) + ("\n" if lines else "")


def _format_labels(label_items: tuple[tuple[str, str], ...]) -> str:
    if not label_items:
        return ""
    inner = ",".join(f'{key}="{value}"' for key, value in label_items)
    return "{" + inner + "}"


metrics = MetricsRegistry()
