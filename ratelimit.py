"""Per-identity token bucket + inflight concurrency cap (in-memory).

Exact under a single worker; buckets for stale identities prune
lazily to bound memory. An LLM-backed inbox without this is a
wallet with a hole in it.

Deps: fastapi (for HTTPException — swap for your framework's 429).
"""
import time

from fastapi import HTTPException


class _Bucket:
    __slots__ = ("tokens", "ts")

    def __init__(self, burst: int):
        self.tokens = float(burst)
        self.ts = time.monotonic()


_buckets: dict[str, _Bucket] = {}
_inflight: dict[str, int] = {}
_PRUNE_AFTER_S = 600.0
_MAX_BUCKETS = 5000


def _prune(now: float) -> None:
    stale = [k for k, b in _buckets.items()
             if now - b.ts > _PRUNE_AFTER_S]
    for k in stale:
        _buckets.pop(k, None)


def check(key: str, burst: int, rps: float) -> None:
    """Consume one token or raise 429 with Retry-After."""
    now = time.monotonic()
    if len(_buckets) > _MAX_BUCKETS:
        _prune(now)
    bucket = _buckets.get(key)
    if bucket is None:
        bucket = _buckets[key] = _Bucket(burst)
    bucket.tokens = min(float(burst),
                        bucket.tokens + (now - bucket.ts) * rps)
    bucket.ts = now
    if bucket.tokens < 1.0:
        wait = (1.0 - bucket.tokens) / rps if rps > 0 else 60.0
        raise HTTPException(
            status_code=429, detail="Rate limited. Slow down.",
            headers={"Retry-After": f"{wait:.1f}"})
    bucket.tokens -= 1.0


def acquire(key: str, max_inflight: int) -> None:
    n = _inflight.get(key, 0)
    if n >= max_inflight:
        raise HTTPException(
            status_code=429,
            detail="Too many concurrent requests.")
    _inflight[key] = n + 1


def release(key: str) -> None:
    n = _inflight.get(key, 0)
    if n <= 1:
        _inflight.pop(key, None)
    else:
        _inflight[key] = n - 1
