"""Tests for the caching layer (in-memory fallback when Redis is unavailable)."""

import pytest

from app.cache import _MemoryCache, cache_delete, cache_get, cache_set


class TestMemoryCache:
    """Unit tests for the in-memory fallback cache."""

    def test_set_and_get(self):
        cache = _MemoryCache()
        cache.set("key1", {"data": "value"}, ttl_seconds=60)
        assert cache.get("key1") == {"data": "value"}

    def test_get_missing_key(self):
        cache = _MemoryCache()
        assert cache.get("nonexistent") is None

    def test_delete(self):
        cache = _MemoryCache()
        cache.set("key1", "value", ttl_seconds=60)
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_delete_pattern(self):
        cache = _MemoryCache()
        cache.set("hackathon:1:data", "a", ttl_seconds=60)
        cache.set("hackathon:1:stats", "b", ttl_seconds=60)
        cache.set("hackathon:2:data", "c", ttl_seconds=60)
        cache.delete_pattern("hackathon:1:*")
        assert cache.get("hackathon:1:data") is None
        assert cache.get("hackathon:1:stats") is None
        assert cache.get("hackathon:2:data") == "c"

    def test_clear(self):
        cache = _MemoryCache()
        cache.set("a", 1, ttl_seconds=60)
        cache.set("b", 2, ttl_seconds=60)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None


@pytest.mark.asyncio
async def test_cache_set_and_get_without_redis():
    """cache_set/cache_get should work via in-memory fallback when Redis is down."""
    await cache_set("test:integration:key", {"hello": "world"}, ttl_seconds=60)
    result = await cache_get("test:integration:key")
    assert result == {"hello": "world"}

    await cache_delete("test:integration:key")
    result = await cache_get("test:integration:key")
    assert result is None
