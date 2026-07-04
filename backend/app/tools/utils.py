"""Shared utility functions for tools and agents."""

import json
import logging
from typing import TypeVar

import redis.asyncio as redis
from redis.exceptions import RedisError

from app.config import settings

T = TypeVar("T")
logger = logging.getLogger(__name__)

# Redis client singleton
_redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    """Get or create the Redis client singleton."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
    return _redis_client


async def cache_get(key: str) -> dict | None:
    """Retrieve a cached value from Redis.

    Args:
        key: Cache key.

    Returns:
        Cached dictionary or None if not found.
    """
    try:
        client = await get_redis()
        value = await client.get(key)
    except (OSError, RedisError) as e:
        logger.warning("Redis cache read failed for key %s: %s", key, str(e))
        return None

    if value is None:
        return None

    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        logger.warning("Redis cache value for key %s is invalid JSON: %s", key, str(e))
        return None


async def cache_set(key: str, value: dict, ttl_seconds: int = 3600) -> None:
    """Store a value in Redis cache.

    Args:
        key: Cache key.
        value: Dictionary to cache.
        ttl_seconds: Time-to-live in seconds (default: 1 hour).
    """
    try:
        client = await get_redis()
        await client.set(key, json.dumps(value), ex=ttl_seconds)
    except (OSError, RedisError) as e:
        logger.warning("Redis cache write failed for key %s: %s", key, str(e))


async def cache_delete(key: str) -> None:
    """Delete a cached value from Redis.

    Args:
        key: Cache key to delete.
    """
    try:
        client = await get_redis()
        await client.delete(key)
    except (OSError, RedisError) as e:
        logger.warning("Redis cache delete failed for key %s: %s", key, str(e))


def truncate_text(text: str, max_length: int = 200) -> str:
    """Truncate text to a maximum length with ellipsis.

    Args:
        text: Text to truncate.
        max_length: Maximum character length.

    Returns:
        Truncated text.
    """
    if len(text) <= max_length:
        return text
    return text[:max_length].rsplit(" ", 1)[0] + "..."
