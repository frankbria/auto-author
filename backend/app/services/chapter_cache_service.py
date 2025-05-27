"""
Chapter Metadata Caching Service
================================

This service provides caching functionality for chapter metadata to improve
performance of the chapter tabs interface. It uses Redis for caching with
intelligent cache invalidation strategies.
"""

import json
import hashlib
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """Configuration for cache TTL and behavior."""

    chapter_metadata_ttl: int = 300  # 5 minutes
    tab_state_ttl: int = 3600  # 1 hour
    analytics_ttl: int = 1800  # 30 minutes
    book_toc_ttl: int = 600  # 10 minutes
    max_retries: int = 3
    retry_delay: float = 1.0


class ChapterMetadataCache:
    """
    Handles caching of chapter metadata for improved performance.

    This service caches:
    - Chapter metadata lists
    - Individual chapter content
    - Tab states
    - Analytics data
    - Book TOC structures
    """

    def __init__(
        self, redis_url: Optional[str] = None, config: Optional[CacheConfig] = None
    ):
        self.config = config or CacheConfig()
        self.redis_client: Optional[redis.Redis] = None
        self.enabled = False

        if REDIS_AVAILABLE and (redis_url or settings.REDIS_URL):
            self.redis_url = redis_url or settings.REDIS_URL
            self._initialize_redis()
        else:
            logger.warning("Redis not available or not configured. Cache disabled.")

    def _initialize_redis(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                health_check_interval=30,
            )
            self.enabled = True
            logger.info("Chapter metadata cache initialized with Redis")
        except Exception as e:
            logger.error(f"Failed to initialize Redis cache: {e}")
            self.enabled = False

    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """Generate a consistent cache key from parameters."""
        # Sort kwargs for consistent key generation
        key_parts = [prefix]
        for key, value in sorted(kwargs.items()):
            if value is not None:
                key_parts.append(f"{key}:{value}")

        key_string = ":".join(key_parts)

        # Hash long keys to avoid Redis key length limits
        if len(key_string) > 250:
            hash_obj = hashlib.md5(key_string.encode())
            return f"{prefix}:hash:{hash_obj.hexdigest()}"

        return key_string

    async def _execute_with_retry(self, operation, *args, **kwargs):
        """Execute Redis operation with retry logic."""
        if not self.enabled:
            return None

        for attempt in range(self.config.max_retries):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Cache operation failed (attempt {attempt + 1}): {e}")
                if attempt == self.config.max_retries - 1:
                    logger.error("Cache operation failed after all retries")
                    return None
                await asyncio.sleep(self.config.retry_delay * (attempt + 1))

        return None

    async def get_chapter_metadata(self, book_id: str, user_id: str) -> Optional[Dict]:
        """Get cached chapter metadata for a book."""
        cache_key = self._generate_cache_key(
            "chapter_metadata", book_id=book_id, user_id=user_id
        )

        async def get_operation():
            data = await self.redis_client.get(cache_key)
            return json.loads(data) if data else None

        return await self._execute_with_retry(get_operation)

    async def set_chapter_metadata(self, book_id: str, user_id: str, metadata: Dict):
        """Cache chapter metadata for a book."""
        cache_key = self._generate_cache_key(
            "chapter_metadata", book_id=book_id, user_id=user_id
        )

        async def set_operation():
            await self.redis_client.setex(
                cache_key,
                self.config.chapter_metadata_ttl,
                json.dumps(metadata, default=str),
            )

        await self._execute_with_retry(set_operation)

    async def get_chapter_content(
        self, book_id: str, chapter_id: str, user_id: str
    ) -> Optional[Dict]:
        """Get cached chapter content."""
        cache_key = self._generate_cache_key(
            "chapter_content", book_id=book_id, chapter_id=chapter_id, user_id=user_id
        )

        async def get_operation():
            data = await self.redis_client.get(cache_key)
            return json.loads(data) if data else None

        return await self._execute_with_retry(get_operation)

    async def set_chapter_content(
        self, book_id: str, chapter_id: str, user_id: str, content: Dict
    ):
        """Cache chapter content."""
        cache_key = self._generate_cache_key(
            "chapter_content", book_id=book_id, chapter_id=chapter_id, user_id=user_id
        )

        async def set_operation():
            await self.redis_client.setex(
                cache_key,
                self.config.chapter_metadata_ttl,
                json.dumps(content, default=str),
            )

        await self._execute_with_retry(set_operation)

    async def get_tab_state(self, book_id: str, user_id: str) -> Optional[Dict]:
        """Get cached tab state."""
        cache_key = self._generate_cache_key(
            "tab_state", book_id=book_id, user_id=user_id
        )

        async def get_operation():
            data = await self.redis_client.get(cache_key)
            return json.loads(data) if data else None

        return await self._execute_with_retry(get_operation)

    async def set_tab_state(self, book_id: str, user_id: str, tab_state: Dict):
        """Cache tab state."""
        cache_key = self._generate_cache_key(
            "tab_state", book_id=book_id, user_id=user_id
        )

        async def set_operation():
            await self.redis_client.setex(
                cache_key, self.config.tab_state_ttl, json.dumps(tab_state, default=str)
            )

        await self._execute_with_retry(set_operation)

    async def get_analytics_data(
        self, book_id: str, chapter_id: str, user_id: str, days: int
    ) -> Optional[Dict]:
        """Get cached analytics data."""
        cache_key = self._generate_cache_key(
            "analytics",
            book_id=book_id,
            chapter_id=chapter_id,
            user_id=user_id,
            days=days,
        )

        async def get_operation():
            data = await self.redis_client.get(cache_key)
            return json.loads(data) if data else None

        return await self._execute_with_retry(get_operation)

    async def set_analytics_data(
        self, book_id: str, chapter_id: str, user_id: str, days: int, analytics: Dict
    ):
        """Cache analytics data."""
        cache_key = self._generate_cache_key(
            "analytics",
            book_id=book_id,
            chapter_id=chapter_id,
            user_id=user_id,
            days=days,
        )

        async def set_operation():
            await self.redis_client.setex(
                cache_key, self.config.analytics_ttl, json.dumps(analytics, default=str)
            )

        await self._execute_with_retry(set_operation)

    async def invalidate_book_cache(self, book_id: str, user_id: Optional[str] = None):
        """Invalidate all cache entries for a specific book."""
        patterns = [
            f"chapter_metadata:book_id:{book_id}*",
            f"chapter_content:book_id:{book_id}*",
            f"book_toc:book_id:{book_id}*",
        ]

        if user_id:
            patterns.extend(
                [
                    f"tab_state:book_id:{book_id}:user_id:{user_id}*",
                    f"analytics:book_id:{book_id}:*:user_id:{user_id}*",
                ]
            )

        async def invalidate_operation():
            for pattern in patterns:
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
                    logger.debug(
                        f"Invalidated {len(keys)} cache entries for pattern: {pattern}"
                    )

        await self._execute_with_retry(invalidate_operation)

    async def invalidate_chapter_cache(
        self, book_id: str, chapter_id: str, user_id: Optional[str] = None
    ):
        """Invalidate cache entries for a specific chapter."""
        patterns = [
            f"chapter_content:book_id:{book_id}:chapter_id:{chapter_id}*",
            f"chapter_metadata:book_id:{book_id}*",  # Chapter metadata affects the whole book
        ]

        if user_id:
            patterns.extend(
                [
                    f"analytics:book_id:{book_id}:chapter_id:{chapter_id}:*:user_id:{user_id}*"
                ]
            )

        async def invalidate_operation():
            for pattern in patterns:
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
                    logger.debug(
                        f"Invalidated {len(keys)} cache entries for pattern: {pattern}"
                    )

        await self._execute_with_retry(invalidate_operation)

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics and health information."""
        if not self.enabled:
            return {"enabled": False, "message": "Cache is disabled"}

        async def stats_operation():
            info = await self.redis_client.info()

            # Get cache key counts by type
            key_counts = {}
            for prefix in [
                "chapter_metadata",
                "chapter_content",
                "tab_state",
                "analytics",
                "book_toc",
            ]:
                keys = await self.redis_client.keys(f"{prefix}:*")
                key_counts[prefix] = len(keys)

            return {
                "enabled": True,
                "connected": True,
                "memory_usage": info.get("used_memory_human", "unknown"),
                "total_keys": info.get("db0", {}).get("keys", 0),
                "key_counts_by_type": key_counts,
                "config": {
                    "chapter_metadata_ttl": self.config.chapter_metadata_ttl,
                    "tab_state_ttl": self.config.tab_state_ttl,
                    "analytics_ttl": self.config.analytics_ttl,
                },
            }

        try:
            return await self._execute_with_retry(stats_operation) or {
                "enabled": True,
                "connected": False,
                "error": "Unable to connect to Redis",
            }
        except Exception as e:
            return {"enabled": True, "connected": False, "error": str(e)}

    async def warm_cache_for_book(self, book_id: str, user_id: str, book_data: Dict):
        """Pre-populate cache with book data to improve initial load performance."""
        if not self.enabled:
            return

        try:
            # Extract and cache chapter metadata
            toc = book_data.get("table_of_contents", {})
            chapters = toc.get("chapters", [])

            if chapters:
                # Create metadata for caching
                chapter_metadata = []

                def extract_metadata(chapter_list, level=1):
                    for chapter in chapter_list:
                        metadata = {
                            "id": chapter.get("id"),
                            "title": chapter.get("title"),
                            "status": chapter.get("status", "draft"),
                            "word_count": chapter.get("word_count", 0),
                            "last_modified": chapter.get("last_modified"),
                            "estimated_reading_time": chapter.get(
                                "estimated_reading_time", 0
                            ),
                            "level": level,
                            "has_content": chapter.get("word_count", 0) > 0,
                        }
                        chapter_metadata.append(metadata)

                        if chapter.get("subchapters"):
                            extract_metadata(chapter["subchapters"], level + 1)

                extract_metadata(chapters)

                # Cache the metadata
                await self.set_chapter_metadata(
                    book_id,
                    user_id,
                    {
                        "chapters": chapter_metadata,
                        "total_chapters": len(chapter_metadata),
                        "cached_at": datetime.now().isoformat(),
                    },
                )

                logger.debug(
                    f"Warmed cache for book {book_id} with {len(chapter_metadata)} chapters"
                )

        except Exception as e:
            logger.error(f"Failed to warm cache for book {book_id}: {e}")

    async def cleanup_expired_cache(self):
        """Clean up expired cache entries (useful for debugging/maintenance)."""
        if not self.enabled:
            return

        async def cleanup_operation():
            # Redis automatically handles TTL cleanup, but we can provide stats
            info = await self.redis_client.info()
            expired_keys = info.get("expired_keys", 0)
            return {"expired_keys_cleaned": expired_keys}

        return await self._execute_with_retry(cleanup_operation)

    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()


# Global cache instance
chapter_cache = ChapterMetadataCache()


# Cache decorators for easy integration
def cache_chapter_metadata(ttl: Optional[int] = None):
    """Decorator to cache chapter metadata results."""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract cache parameters from function arguments
            # This is a simplified version - actual implementation would need
            # to parse function arguments to extract book_id, user_id, etc.

            if not chapter_cache.enabled:
                return await func(*args, **kwargs)

            # Try cache first
            # cached_result = await chapter_cache.get_chapter_metadata(book_id, user_id)
            # if cached_result:
            #     return cached_result

            # Call original function
            result = await func(*args, **kwargs)

            # Cache the result
            # await chapter_cache.set_chapter_metadata(book_id, user_id, result)

            return result

        return wrapper

    return decorator


# Cache invalidation hooks
async def invalidate_cache_on_chapter_update(
    book_id: str, chapter_id: str, user_id: str
):
    """Hook to invalidate cache when chapter is updated."""
    await chapter_cache.invalidate_chapter_cache(book_id, chapter_id, user_id)


async def invalidate_cache_on_book_update(book_id: str, user_id: str):
    """Hook to invalidate cache when book structure changes."""
    await chapter_cache.invalidate_book_cache(book_id, user_id)


# Cache initialization for startup
async def initialize_cache():
    """Initialize cache service on application startup."""
    global chapter_cache

    # Re-initialize if needed
    if not chapter_cache.enabled and REDIS_AVAILABLE:
        chapter_cache._initialize_redis()

    if chapter_cache.enabled:
        stats = await chapter_cache.get_cache_stats()
        logger.info(f"Chapter metadata cache initialized: {stats}")
    else:
        logger.warning("Chapter metadata cache is disabled")


# Cache cleanup for shutdown
async def cleanup_cache():
    """Clean up cache connections on application shutdown."""
    if chapter_cache:
        await chapter_cache.close()
        logger.info("Chapter metadata cache connections closed")


# Export service instance
chapter_cache_service = ChapterCacheService()
