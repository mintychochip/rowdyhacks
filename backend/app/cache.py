"""Caching layer for HackVerify (Redis + in-memory fallback)."""

import json
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from app.config import settings

T = TypeVar("T")
P = ParamSpec("P")

# Lazy-loaded Redis client (only if redis is installed)
_redis_client = None
_redis = None


class _MemoryCache:
    """Simple TTL cache that works without Redis."""

    def __init__(self):
        self._store: dict[str, tuple[Any, float]] = {}  # key → (value, expires_at)

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: int):
        self._store[key] = (value, time.monotonic() + ttl_seconds)

    def delete(self, key: str):
        self._store.pop(key, None)

    def delete_pattern(self, pattern: str):
        """Delete keys matching a simple prefix pattern."""
        prefix = pattern.rstrip("*")
        to_delete = [k for k in self._store if k.startswith(prefix)]
        for k in to_delete:
            del self._store[k]

    def clear(self):
        self._store.clear()


_memory_cache = _MemoryCache()


async def get_redis():
    """Get or create Redis client (returns None if redis not installed)."""
    global _redis_client, _redis
    if _redis_client is None and settings.redis_url:
        try:
            if _redis is None:
                import redis.asyncio as _redis
            _redis_client = _redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
            )
        except Exception:
            return None
    return _redis_client


async def close_redis():
    """Close Redis connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


async def cache_get(key: str) -> Any | None:
    """Get value from cache (tries Redis first, falls back to memory)."""
    r = await get_redis()
    if r:
        try:
            value = await r.get(key)
            if value:
                return json.loads(value)
        except Exception:
            pass

    # Fall back to in-memory cache
    return _memory_cache.get(key)


async def cache_set(key: str, value: Any, ttl_seconds: int = 3600):
    """Set value in cache (Redis + in-memory)."""
    # Always write to in-memory
    _memory_cache.set(key, value, ttl_seconds)

    r = await get_redis()
    if r:
        try:
            await r.setex(key, ttl_seconds, json.dumps(value))
        except Exception:
            pass


async def cache_delete(key: str):
    """Delete key from all cache layers."""
    _memory_cache.delete(key)

    r = await get_redis()
    if r:
        try:
            await r.delete(key)
        except Exception:
            pass


async def cache_delete_pattern(pattern: str):
    """Delete all keys matching pattern from all cache layers."""
    _memory_cache.delete_pattern(pattern)

    r = await get_redis()
    if r:
        try:
            keys = await r.keys(pattern)
            if keys:
                await r.delete(*keys)
        except Exception:
            pass


def cached(ttl_seconds: int = 300, key_prefix: str = ""):
    """Decorator to cache function results (auto-fallback to memory).
    Default TTL is 5 minutes (300s) for read-heavy endpoints."""

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Build cache key
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args))}:{hash(str(kwargs))}"

            # Try cache first
            cached_val = await cache_get(cache_key)
            if cached_val is not None:
                return cached_val

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            await cache_set(cache_key, result, ttl_seconds)

            return result

        return wrapper

    return decorator


# Cache key patterns
CACHE_KEYS = {
    "hackathon": "hackathon:{id}",
    "hackathon_list": "hackathons:list",
    "submission": "submission:{id}",
    "submission_results": "submission:{id}:results",
    "check_result": "check:{submission_id}:{check_name}",
    "user": "user:{id}",
    "registrations": "hackathon:{id}:registrations",
    "stats": "hackathon:{id}:stats",
    "crawled_projects": "crawled:{hackathon_id}",
}


async def invalidate_hackathon_cache(hackathon_id: str):
    """Invalidate all cache entries for a hackathon."""
    await cache_delete(CACHE_KEYS["hackathon"].format(id=hackathon_id))
    await cache_delete(CACHE_KEYS["stats"].format(id=hackathon_id))
    await cache_delete(CACHE_KEYS["registrations"].format(id=hackathon_id))
    await cache_delete_pattern(f"hackathon:{hackathon_id}:*")


async def invalidate_submission_cache(submission_id: str):
    """Invalidate all cache entries for a submission."""
    await cache_delete(CACHE_KEYS["submission"].format(id=submission_id))
    await cache_delete(CACHE_KEYS["submission_results"].format(id=submission_id))
    await cache_delete_pattern(f"check:{submission_id}:*")
