"""
Simple in-memory cache for API responses.
Prevents hammering Okta's API on every frontend poll.
Week 3 will replace this with DynamoDB-backed caching.
"""

import time
import asyncio
import functools
from typing import Any

_cache: dict[str, tuple[Any, float]] = {}


def cached(ttl_seconds: int = 60):
    """
    Decorator that caches async function results in memory.
    Cache key = function name + stringified arguments.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key from function name + args
            key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"

            # Check if cached and not expired
            if key in _cache:
                value, expires_at = _cache[key]
                if time.time() < expires_at:
                    return value

            # Call the actual function
            result = await func(*args, **kwargs)

            # Store in cache
            _cache[key] = (result, time.time() + ttl_seconds)
            return result

        return wrapper
    return decorator


def invalidate_cache(prefix: str = ""):
    """Clear all cache entries, or those matching a prefix"""
    global _cache
    if prefix:
        _cache = {k: v for k, v in _cache.items() if not k.startswith(prefix)}
    else:
        _cache = {}


def cache_stats() -> dict:
    """Debug endpoint — show cache hit counts and sizes"""
    now = time.time()
    active = {k: v for k, v in _cache.items() if v[1] > now}
    expired = {k: v for k, v in _cache.items() if v[1] <= now}
    return {
        "active_entries": len(active),
        "expired_entries": len(expired),
        "keys": list(active.keys()),
    }
