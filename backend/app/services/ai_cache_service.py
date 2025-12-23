"""
AI Response Caching Service
============================

This service provides caching functionality for AI responses to improve
performance and reduce API costs. It uses Redis for caching with
intelligent cache invalidation strategies.
"""

import json
import hashlib
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
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
    """Configuration for AI response cache TTL and behavior."""

    ai_response_ttl: int = 86400  # 24 hours (from settings.AI_CACHE_TTL)
    max_retries: int = 3
    retry_delay: float = 1.0


class AICacheService:
    """
    Handles caching of AI responses for improved performance.

    This service caches:
    - TOC generation responses
    - Clarifying questions
    - Summary analysis results
    - Chapter questions
    - Chapter drafts
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        config: Optional[CacheConfig] = None
    ):
        self.config = config or CacheConfig(
            ai_response_ttl=settings.AI_CACHE_TTL,
            max_retries=settings.AI_MAX_RETRIES
        )
        self.redis_client: Optional[redis.Redis] = None
        self.enabled = settings.AI_CACHE_ENABLED

        if REDIS_AVAILABLE and self.enabled and (redis_url or settings.REDIS_URL):
            self.redis_url = redis_url or settings.REDIS_URL
            self._initialize_redis()
        else:
            if not REDIS_AVAILABLE:
                logger.warning("Redis not available. AI response cache disabled.")
            elif not self.enabled:
                logger.info("AI response cache disabled by configuration.")
            else:
                logger.warning("Redis URL not configured. AI response cache disabled.")

    def _initialize_redis(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                health_check_interval=30,
            )
            logger.info("AI response cache initialized with Redis")
        except Exception as e:
            logger.error(f"Failed to initialize Redis cache: {e}")
            self.enabled = False

    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """
        Generate a consistent cache key from parameters.

        Args:
            prefix: Key prefix (e.g., 'toc_generation', 'questions')
            **kwargs: Parameters to include in the key

        Returns:
            Cache key string
        """
        # Sort kwargs for consistent key generation
        key_parts = [prefix]
        sorted_params = []

        for key, value in sorted(kwargs.items()):
            if value is not None:
                # Convert complex types to JSON for hashing
                if isinstance(value, (dict, list)):
                    value_str = json.dumps(value, sort_keys=True)
                else:
                    value_str = str(value)
                sorted_params.append(f"{key}:{value_str}")

        # Create hash of parameters to keep key length manageable
        params_string = "|".join(sorted_params)
        params_hash = hashlib.md5(params_string.encode()).hexdigest()

        return f"ai_cache:{prefix}:{params_hash}"

    async def _execute_with_retry(self, operation, *args, **kwargs):
        """Execute Redis operation with retry logic."""
        if not self.enabled or not self.redis_client:
            return None

        import asyncio

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

    async def get_cached_response(self, cache_key: str) -> Optional[Dict]:
        """
        Get a cached AI response.

        Args:
            cache_key: The cache key to retrieve

        Returns:
            Cached response data or None if not found
        """
        if not self.enabled:
            return None

        async def get_operation():
            data = await self.redis_client.get(cache_key)
            if data:
                logger.debug(f"Cache hit for key: {cache_key}")
                return json.loads(data)
            logger.debug(f"Cache miss for key: {cache_key}")
            return None

        return await self._execute_with_retry(get_operation)

    async def set_cached_response(
        self,
        cache_key: str,
        response: Dict,
        ttl: Optional[int] = None
    ):
        """
        Cache an AI response.

        Args:
            cache_key: The cache key to use
            response: The response data to cache
            ttl: Time to live in seconds (default: from config)
        """
        if not self.enabled:
            return

        ttl = ttl or self.config.ai_response_ttl

        async def set_operation():
            # Add metadata to cached response
            cache_data = {
                **response,
                "_cached_at": datetime.now().isoformat(),
                "_from_cache": True
            }
            await self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(cache_data, default=str)
            )
            logger.debug(f"Cached response for key: {cache_key} (TTL: {ttl}s)")

        await self._execute_with_retry(set_operation)

    async def invalidate_cache(self, pattern: str):
        """
        Invalidate cache entries matching a pattern.

        Args:
            pattern: Redis key pattern (e.g., 'ai_cache:toc_*')
        """
        if not self.enabled:
            return

        async def invalidate_operation():
            keys = await self.redis_client.keys(pattern)
            if keys:
                await self.redis_client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache entries matching: {pattern}")

        await self._execute_with_retry(invalidate_operation)

    async def get_cache_stats(self) -> Dict:
        """Get cache statistics and health information."""
        if not self.enabled:
            return {"enabled": False, "message": "Cache is disabled"}

        async def stats_operation():
            info = await self.redis_client.info()

            # Get cache key counts by type
            key_counts = {}
            prefixes = [
                "toc_generation",
                "clarifying_questions",
                "summary_analysis",
                "chapter_questions",
                "chapter_draft"
            ]

            for prefix in prefixes:
                keys = await self.redis_client.keys(f"ai_cache:{prefix}:*")
                key_counts[prefix] = len(keys)

            return {
                "enabled": True,
                "connected": True,
                "memory_usage": info.get("used_memory_human", "unknown"),
                "total_keys": sum(key_counts.values()),
                "key_counts_by_type": key_counts,
                "config": {
                    "ai_response_ttl": self.config.ai_response_ttl,
                    "max_retries": self.config.max_retries
                }
            }

        try:
            return await self._execute_with_retry(stats_operation) or {
                "enabled": True,
                "connected": False,
                "error": "Unable to connect to Redis"
            }
        except Exception as e:
            return {
                "enabled": True,
                "connected": False,
                "error": str(e)
            }

    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("AI cache Redis connection closed")


# Helper methods for specific AI operations

async def get_toc_generation_cache(
    cache_service: AICacheService,
    summary: str,
    question_responses: List[Dict],
    book_metadata: Optional[Dict] = None
) -> Optional[Dict]:
    """Get cached TOC generation response."""
    cache_key = cache_service._generate_cache_key(
        "toc_generation",
        summary=summary,
        responses=question_responses,
        metadata=book_metadata
    )
    return await cache_service.get_cached_response(cache_key)


async def set_toc_generation_cache(
    cache_service: AICacheService,
    summary: str,
    question_responses: List[Dict],
    response: Dict,
    book_metadata: Optional[Dict] = None
):
    """Cache TOC generation response."""
    cache_key = cache_service._generate_cache_key(
        "toc_generation",
        summary=summary,
        responses=question_responses,
        metadata=book_metadata
    )
    await cache_service.set_cached_response(cache_key, response)


async def get_questions_cache(
    cache_service: AICacheService,
    summary: str,
    book_metadata: Optional[Dict] = None,
    num_questions: int = 4
) -> Optional[List[str]]:
    """Get cached clarifying questions."""
    cache_key = cache_service._generate_cache_key(
        "clarifying_questions",
        summary=summary,
        metadata=book_metadata,
        num_questions=num_questions
    )
    result = await cache_service.get_cached_response(cache_key)
    return result.get("questions") if result else None


async def set_questions_cache(
    cache_service: AICacheService,
    summary: str,
    questions: List[str],
    book_metadata: Optional[Dict] = None,
    num_questions: int = 4
):
    """Cache clarifying questions."""
    cache_key = cache_service._generate_cache_key(
        "clarifying_questions",
        summary=summary,
        metadata=book_metadata,
        num_questions=num_questions
    )
    await cache_service.set_cached_response(cache_key, {"questions": questions})


# Global cache instance
ai_cache_service = AICacheService()
