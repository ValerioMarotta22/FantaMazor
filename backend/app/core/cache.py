"""Thin Redis wrapper. All server-side caching (per §51 TTL guidance) goes
through here so TTL policy stays in one place instead of scattered constants.

If no Redis server is reachable (e.g. local/offline single-user mode with
no Docker), this transparently falls back to an in-process in-memory store
with the same get/setex/delete surface. That's fine for a single admin
running one backend process locally; a real deployment with Redis just
works as normal since the check only trips when Redis is actually absent.
"""

import threading
import time
from functools import lru_cache

import redis

from app.core.config import get_settings

# TTL presets (seconds) per data category — see README "Caching" section.
TTL_LIVE = 30
TTL_LINEUPS = 180
TTL_INJURIES = 3600 * 2
TTL_HISTORICAL = 3600 * 24
TTL_NEWS = 600


class InMemoryCache:
    """Drop-in subset of the redis.Redis interface used when no Redis
    server is reachable. Not shared across processes — only appropriate for
    a single local backend process."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[bytes, float | None]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> bytes | None:
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            value, expires_at = item
            if expires_at is not None and time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    def setex(self, key: str, ttl_seconds: int, value: str | bytes) -> None:
        if isinstance(value, str):
            value = value.encode("utf-8")
        with self._lock:
            self._store[key] = (value, time.monotonic() + ttl_seconds)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)


@lru_cache
def get_redis() -> "redis.Redis | InMemoryCache":
    settings = get_settings()
    client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=1)
    try:
        client.ping()
        return client
    except redis.exceptions.RedisError:
        return InMemoryCache()
