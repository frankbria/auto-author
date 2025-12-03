"""
Redis client setup for distributed rate limiting and caching.

This module provides a Redis connection pool and health check functionality
for use across the application. It supports graceful degradation if Redis
is unavailable.
"""

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool
from typing import Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis connection pool
_redis_pool: Optional[ConnectionPool] = None
_redis_client: Optional[redis.Redis] = None


async def get_redis_pool() -> Optional[ConnectionPool]:
    """
    Get or create the Redis connection pool.

    Returns:
        ConnectionPool instance or None if Redis is disabled/unavailable
    """
    global _redis_pool

    if not settings.REDIS_ENABLED:
        logger.info("Redis is disabled in configuration")
        return None

    if _redis_pool is None:
        try:
            _redis_pool = ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=settings.REDIS_SOCKET_TIMEOUT,
                decode_responses=True,  # Automatically decode responses to strings
            )
            logger.info(
                f"Redis connection pool created: {settings.REDIS_URL} "
                f"(max_connections={settings.REDIS_MAX_CONNECTIONS})"
            )
        except Exception as e:
            logger.error(f"Failed to create Redis connection pool: {e}")
            return None

    return _redis_pool


async def get_redis_client() -> Optional[redis.Redis]:
    """
    Get or create the Redis client.

    Returns:
        Redis client instance or None if Redis is disabled/unavailable
    """
    global _redis_client

    if not settings.REDIS_ENABLED:
        return None

    if _redis_client is None:
        pool = await get_redis_pool()
        if pool is None:
            return None

        try:
            _redis_client = redis.Redis(connection_pool=pool)
            logger.info("Redis client created successfully")
        except Exception as e:
            logger.error(f"Failed to create Redis client: {e}")
            return None

    return _redis_client


async def check_redis_health() -> bool:
    """
    Check if Redis is available and responding.

    Returns:
        True if Redis is healthy, False otherwise
    """
    if not settings.REDIS_ENABLED:
        return False

    try:
        client = await get_redis_client()
        if client is None:
            return False

        # Try to ping Redis
        await client.ping()
        return True
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        return False


async def close_redis_connection():
    """
    Close the Redis connection pool and client.
    Should be called on application shutdown.
    """
    global _redis_pool, _redis_client

    if _redis_client is not None:
        try:
            await _redis_client.aclose()
            logger.info("Redis client closed")
        except Exception as e:
            logger.error(f"Error closing Redis client: {e}")
        finally:
            _redis_client = None

    if _redis_pool is not None:
        try:
            await _redis_pool.aclose()
            logger.info("Redis connection pool closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection pool: {e}")
        finally:
            _redis_pool = None


# Convenience function for testing
async def flush_redis():
    """
    Flush all Redis data. ONLY FOR TESTING.

    Raises:
        RuntimeError if called in production environment
    """
    if settings.DATABASE_NAME == "auto_author_production":
        raise RuntimeError("Cannot flush Redis in production!")

    client = await get_redis_client()
    if client is not None:
        await client.flushdb()
        logger.warning("Redis database flushed (TEST ENVIRONMENT ONLY)")
