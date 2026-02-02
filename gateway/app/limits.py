from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass


@dataclass(slots=True)
class Bucket:
    tokens: float
    last_refill: float


class RateLimiter:
    def __init__(self, rate: float, burst: int) -> None:
        self._rate = rate
        self._burst = burst
        self._buckets: dict[str, Bucket] = {}
        self._lock = asyncio.Lock()

    async def allow(self, key: str) -> bool:
        async with self._lock:
            now = time.monotonic()
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = Bucket(tokens=float(self._burst), last_refill=now)
                self._buckets[key] = bucket
            elapsed = now - bucket.last_refill
            bucket.tokens = min(self._burst, bucket.tokens + elapsed * self._rate)
            bucket.last_refill = now
            if bucket.tokens >= 1:
                bucket.tokens -= 1
                return True
            return False
