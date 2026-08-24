"""Thin Redis wrapper. All server-side caching (per §51 TTL guidance) goes
through here so TTL policy stays in one place instead of scattered constants."""

from functools import lru_cache

import redis

from app.core.config import get_settings

# TTL presets (seconds) per data category — see README "Caching" section.
TTL_LIVE = 30
TTL_LINEUPS = 180
TTL_INJURIES = 3600 * 2
TTL_HISTORICAL = 3600 * 24
TTL_NEWS = 600


@lru_cache
def get_redis() -> redis.Redis:
    settings = get_settings()
    return redis.Redis.from_url(settings.redis_url)
