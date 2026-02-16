from __future__ import annotations

import time

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

REQUEST_LATENCY = Histogram("gateway_request_latency_seconds", "Latency per request", ["path"])
REQUEST_COUNT = Counter("gateway_requests_total", "Total requests", ["path", "status"])
CACHE_HITS = Counter("gateway_cache_hits_total", "Cache hits", ["path"])
ERROR_COUNT = Counter("gateway_errors_total", "Errors", ["path"])
TOKENS_TOTAL = Counter("gateway_tokens_total", "Tokens generated", ["path"])
TOKENS_PER_SECOND = Gauge("gateway_tokens_per_second", "Tokens per second", ["path"])


def record_latency(path: str, start_time: float) -> None:
    REQUEST_LATENCY.labels(path=path).observe(time.time() - start_time)


def record_request(path: str, status: str) -> None:
    REQUEST_COUNT.labels(path=path, status=status).inc()


def record_cache_hit(path: str) -> None:
    CACHE_HITS.labels(path=path).inc()


def record_error(path: str) -> None:
    ERROR_COUNT.labels(path=path).inc()


def record_tokens(path: str, tokens: int, latency_s: float) -> None:
    TOKENS_TOTAL.labels(path=path).inc(tokens)
    if latency_s > 0:
        TOKENS_PER_SECOND.labels(path=path).set(tokens / latency_s)


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST


def aggregate_tokens(usage: dict[str, int] | None) -> int:
    if not usage:
        return 0
    return sum(value for value in usage.values() if isinstance(value, int))
