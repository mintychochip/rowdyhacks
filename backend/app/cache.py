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
        """Initialize an empty in-memory TTL cache store.

        Behavior:
        1. Create an empty dict to hold key → (value, expires_at) pairs.

        Raises: None
        Side Effects: Allocates the internal store dict.
        Dependencies: None.
        Consumers: Module-level singleton ``_memory_cache``.
        """
        self._store: dict[str, tuple[Any, float]] = {}  # key → (value, expires_at)

    def get(self, key: str) -> Any | None:
        """Retrieve a value from the in-memory cache if it exists and has not expired.

        Behavior:
        1. Look up the key in the internal store.
        2. If missing, return None.
        3. If the TTL has expired, delete the stale entry and return None.
        4. Otherwise, return the stored value.

        Raises: None
        Side Effects: May delete an expired key from the internal store.
        Dependencies: time.monotonic.
        Consumers: app.cache.cache_get fallback path.
        """
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: int):
        """Store a value with a TTL in the in-memory cache.

        Behavior:
        1. Compute the expiration timestamp as ``time.monotonic() + ttl_seconds``.
        2. Insert the key → (value, expires_at) pair into the internal store.

        Raises: None
        Side Effects: Mutates the internal store dict.
        Dependencies: time.monotonic.
        Consumers: app.cache.cache_set fallback path, app.cache.cached decorator.
        """
        self._store[key] = (value, time.monotonic() + ttl_seconds)

    def delete(self, key: str):
        """Remove a single key from the in-memory cache.

        Behavior:
        1. Pop the key from the internal store if it exists.

        Raises: None
        Side Effects: Mutates the internal store dict.
        Dependencies: None.
        Consumers: app.cache.cache_delete fallback path.
        """
        self._store.pop(key, None)

    def delete_pattern(self, pattern: str):
        """Delete keys matching a simple prefix pattern from the in-memory cache.

        Behavior:
        1. Strip the trailing wildcard from the pattern to obtain a prefix.
        2. Find all keys in the store that start with the prefix.
        3. Delete each matching key.

        Raises: None
        Side Effects: Mutates the internal store dict.
        Dependencies: None.
        Consumers: app.cache.cache_delete_pattern fallback path.
        """
        prefix = pattern.rstrip("*")
        to_delete = [k for k in self._store if k.startswith(prefix)]
        for k in to_delete:
            del self._store[k]

    def clear(self):
        """Clear all entries from the in-memory cache.

        Behavior:
        1. Empty the internal store dict.

        Raises: None
        Side Effects: Mutates the internal store dict.
        Dependencies: None.
        Consumers: Internal testing and cache eviction routines.
        """
        self._store.clear()


_memory_cache = _MemoryCache()


_redis_available = None  # Cache the availability check


async def get_redis():
    """Get or create the shared Redis async client.

    Behavior:
    1. Return None immediately if a prior connectivity check marked Redis unavailable.
    2. If the client is None and a Redis URL is configured, import ``redis.asyncio``.
    3. Create a pooled client from the configured Redis URL with UTF-8 decoding.
    4. Ping the server to confirm connectivity and mark availability True.
    5. On any failure, mark availability False and return None.

    Raises: None (exceptions are caught and swallowed).
    Side Effects: Mutates the global ``_redis_client`` and ``_redis_available`` variables.
    Dependencies: app.config.settings.redis_url.
    Consumers: app.cache.cache_get, app.cache.cache_set, app.cache.cache_delete, app.cache.cache_delete_pattern, app.cache.close_redis.
    """
    global _redis_client, _redis, _redis_available

    # If we already know Redis is unavailable, don't retry
    if _redis_available is False:
        return None

    if _redis_client is None and settings.redis_url:
        try:
            if _redis is None:
                import redis.asyncio as _redis
            _redis_client = _redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
                socket_connect_timeout=1,  # Quick timeout - fail fast
                socket_timeout=1,
                health_check_interval=30,
            )
            # Test the connection immediately
            await _redis_client.ping()
            _redis_available = True
        except Exception:
            _redis_available = False
            _redis_client = None
            return None
    return _redis_client


async def close_redis():
    """Close the shared Redis connection and clear the global client reference.

    Behavior:
    1. If a Redis client exists, await its close method.
    2. Set the global client reference to None.

    Raises: None
    Side Effects: Closes the Redis connection; mutates ``_redis_client``.
    Dependencies: None.
    Consumers: app.main.lifespan shutdown sequence.
    """
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


async def cache_get(key: str) -> Any | None:
    """Retrieve a value from the cache tier (Redis first, in-memory fallback).

    Behavior:
    1. Obtain the Redis client.
    2. If connected, read the key, deserialize JSON, and return the value.
    3. On any Redis failure, silently fall through.
    4. Query the in-memory TTL cache as a fallback.

    Raises: None (exceptions are caught and swallowed).
    Side Effects: None (read-only).
    Dependencies: app.cache.get_redis, app.cache._memory_cache, json.loads.
    Consumers: Read-heavy route handlers and internal services.
    """
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
    """Store a value in both cache tiers (in-memory and Redis).

    Behavior:
    1. Always write the value to the in-memory TTL cache.
    2. Obtain the Redis client.
    3. If connected, serialize the value to JSON and write with SETEX.
    4. On any Redis failure, silently swallow the exception.

    Raises: None (exceptions are caught and swallowed).
    Side Effects: Mutates the in-memory cache and optionally the Redis keyspace.
    Dependencies: app.cache.get_redis, app.cache._memory_cache, json.dumps.
    Consumers: Route handlers and the ``cached`` decorator.
    """
    # Always write to in-memory
    _memory_cache.set(key, value, ttl_seconds)

    r = await get_redis()
    if r:
        try:
            await r.setex(key, ttl_seconds, json.dumps(value))
        except Exception:
            pass


async def cache_delete(key: str):
    """Delete a key from both cache tiers (in-memory and Redis).

    Behavior:
    1. Remove the key from the in-memory TTL cache.
    2. Obtain the Redis client.
    3. If connected, issue a Redis DEL command.
    4. On any Redis failure, silently swallow the exception.

    Raises: None (exceptions are caught and swallowed).
    Side Effects: Mutates the in-memory cache and optionally the Redis keyspace.
    Dependencies: app.cache.get_redis, app.cache._memory_cache.
    Consumers: Cache invalidation helpers and route handlers after mutations.
    """
    _memory_cache.delete(key)

    r = await get_redis()
    if r:
        try:
            await r.delete(key)
        except Exception:
            pass


async def cache_delete_pattern(pattern: str):
    """Delete all keys matching a prefix pattern from both cache tiers.

    Behavior:
    1. Remove matching keys from the in-memory TTL cache.
    2. Obtain the Redis client.
    3. If connected, run KEYS to find matches and then DEL them in bulk.
    4. On any Redis failure, silently swallow the exception.

    Raises: None (exceptions are caught and swallowed).
    Side Effects: Mutates the in-memory cache and optionally the Redis keyspace.
    Dependencies: app.cache.get_redis, app.cache._memory_cache.
    Consumers: app.cache.invalidate_hackathon_cache, app.cache.invalidate_submission_cache.
    """
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
    """Decorator that caches the result of an async function with automatic fallback.

    Behavior:
    1. Build a deterministic cache key from the function name, prefix, and arguments.
    2. Try to read a cached value; if present, return it immediately.
    3. Otherwise, await the original function.
    4. Store the result in both cache tiers with the specified TTL.
    5. Return the result.

    Raises: None
    Side Effects: Reads from and writes to the cache tier.
    Dependencies: app.cache.cache_get, app.cache.cache_set.
    Consumers: Read-heavy route handlers and service methods.
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        """Wrap an async function with result caching.

        Behavior:
        1. Preserve the original function's metadata via ``functools.wraps``.
        2. Return the wrapper coroutine that performs cache lookup and storage.

        Raises: None
        Side Effects: None at decoration time.
        Dependencies: functools.wraps.
        Consumers: Internal decorator factory used by ``cached()``.
        """

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            """Execute the wrapped function with caching.

            Behavior:
            1. Build a cache key from prefix, function name, and hashed arguments.
            2. Attempt to retrieve a cached value; return it if found.
            3. Await the original function to compute the result.
            4. Write the result to the cache tier with the decorator's TTL.
            5. Return the computed result.

            Raises: None (propagates exceptions from the wrapped function).
            Side Effects: Reads from and writes to the cache tier.
            Dependencies: app.cache.cache_get, app.cache.cache_set.
            Consumers: Runtime invocations of decorated functions.
            """
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
    """Invalidate all cache entries associated with a specific hackathon.

    Behavior:
    1. Delete the hackathon detail cache key.
    2. Delete the hackathon stats cache key.
    3. Delete the hackathon registrations cache key.
    4. Delete any keys matching the hackathon prefix pattern.

    Raises: None
    Side Effects: Removes keys from both cache tiers.
    Dependencies: app.cache.cache_delete, app.cache.cache_delete_pattern, app.cache.CACHE_KEYS.
    Consumers: Route handlers that mutate hackathon data (e.g., update, delete, registration changes).
    """
    await cache_delete(CACHE_KEYS["hackathon"].format(id=hackathon_id))
    await cache_delete(CACHE_KEYS["stats"].format(id=hackathon_id))
    await cache_delete(CACHE_KEYS["registrations"].format(id=hackathon_id))
    await cache_delete_pattern(f"hackathon:{hackathon_id}:*")


async def invalidate_submission_cache(submission_id: str):
    """Invalidate all cache entries associated with a specific submission.

    Behavior:
    1. Delete the submission detail cache key.
    2. Delete the submission results cache key.
    3. Delete any check-result keys matching the submission prefix pattern.

    Raises: None
    Side Effects: Removes keys from both cache tiers.
    Dependencies: app.cache.cache_delete, app.cache.cache_delete_pattern, app.cache.CACHE_KEYS.
    Consumers: Route handlers that mutate submission data (e.g., check re-run, status updates).
    """
    await cache_delete(CACHE_KEYS["submission"].format(id=submission_id))
    await cache_delete(CACHE_KEYS["submission_results"].format(id=submission_id))
    await cache_delete_pattern(f"check:{submission_id}:*")
