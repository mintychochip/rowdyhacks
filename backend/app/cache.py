"""Redis caching layer for HackVerify."""
import json
from functools import wraps
from typing import Any, Callable, TypeVar, ParamSpec

import redis.asyncio as redis
from app.config import settings

T = TypeVar("T")
P = ParamSpec("P")

# Global Redis client
_redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis | None:
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None and settings.redis_url:
        try:
            _redis_client = redis.from_url(
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
    """Get value from cache."""
    r = await get_redis()
    if not r:
        return None
    try:
        value = await r.get(key)
        if value:
            return json.loads(value)
    except Exception:
        pass
    return None


async def cache_set(key: str, value: Any, ttl_seconds: int = 3600):
    """Set value in cache with TTL."""
    r = await get_redis()
    if not r:
        return
    try:
        await r.setex(key, ttl_seconds, json.dumps(value))
    except Exception:
        pass


async def cache_delete(key: str):
    """Delete key from cache."""
    r = await get_redis()
    if not r:
        return
    try:
        await r.delete(key)
    except Exception:
        pass


async def cache_delete_pattern(pattern: str):
    """Delete all keys matching pattern."""
    r = await get_redis()
    if not r:
        return
    try:
        keys = await r.keys(pattern)
        if keys:
            await r.delete(*keys)
    except Exception:
        pass


def cached(ttl_seconds: int = 3600, key_prefix: str = ""):
    """Decorator to cache function results."""
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Build cache key
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args))}:{hash(str(kwargs))}"
            
            # Try cache first
            cached = await cache_get(cache_key)
            if cached is not None:
                return cached
            
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
