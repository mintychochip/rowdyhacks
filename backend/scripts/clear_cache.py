"""Clear the in-memory cache to refresh hackathon data."""
import sys
sys.path.insert(0, '.')

from app.cache import _memory_cache

# Clear all in-memory cache
_memory_cache.clear()
print("In-memory cache cleared successfully!")

# Also clear any hackathon-specific patterns
try:
    import asyncio
    from app.cache import cache_delete_pattern

    async def clear_hackathon_cache():
        await cache_delete_pattern("hackathons:*")
        print("Hackathon cache pattern cleared!")

    asyncio.run(clear_hackathon_cache())
except Exception as e:
    print(f"Note: {e}")

print("\nThe updated schedule should now be visible on the frontend.")
