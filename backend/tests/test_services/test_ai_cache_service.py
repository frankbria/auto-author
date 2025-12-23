"""
Tests for AI Cache Service
===========================

Tests the AI response caching service with Redis.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.ai_cache_service import (
    AICacheService,
    CacheConfig,
    get_toc_generation_cache,
    set_toc_generation_cache,
    get_questions_cache,
    set_questions_cache
)


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.setex = AsyncMock()
    mock.keys = AsyncMock(return_value=[])
    mock.delete = AsyncMock()
    mock.info = AsyncMock(return_value={
        "used_memory_human": "1.5M",
        "db0": {"keys": 10}
    })
    return mock


@pytest.fixture
def cache_service_with_redis(mock_redis):
    """Create a cache service with mocked Redis."""
    with patch('app.services.ai_cache_service.REDIS_AVAILABLE', True):
        with patch('app.services.ai_cache_service.redis') as mock_redis_module:
            mock_redis_module.from_url = MagicMock(return_value=mock_redis)

            service = AICacheService(
                redis_url="redis://localhost:6379/0",
                config=CacheConfig(ai_response_ttl=3600)
            )
            service.redis_client = mock_redis
            service.enabled = True

            return service


@pytest.fixture
def cache_service_disabled():
    """Create a disabled cache service."""
    with patch('app.services.ai_cache_service.REDIS_AVAILABLE', False):
        service = AICacheService()
        return service


class TestAICacheServiceInitialization:
    """Test cache service initialization."""

    def test_initialization_with_redis_available(self):
        """Test initialization when Redis is available."""
        with patch('app.services.ai_cache_service.REDIS_AVAILABLE', True):
            with patch('app.services.ai_cache_service.redis') as mock_redis_module:
                mock_client = AsyncMock()
                mock_redis_module.from_url = MagicMock(return_value=mock_client)

                service = AICacheService(redis_url="redis://localhost:6379/0")

                assert service.enabled is True
                mock_redis_module.from_url.assert_called_once()

    def test_initialization_without_redis(self):
        """Test initialization when Redis is not available."""
        with patch('app.services.ai_cache_service.REDIS_AVAILABLE', False):
            with patch('app.services.ai_cache_service.settings.AI_CACHE_ENABLED', True):
                service = AICacheService()

                # Should be disabled because Redis is not available
                assert service.enabled is False or service.redis_client is None

    def test_initialization_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = CacheConfig(ai_response_ttl=7200, max_retries=5)

        with patch('app.services.ai_cache_service.REDIS_AVAILABLE', False):
            service = AICacheService(config=config)

            assert service.config.ai_response_ttl == 7200
            assert service.config.max_retries == 5


class TestCacheKeyGeneration:
    """Test cache key generation."""

    def test_generate_simple_key(self, cache_service_with_redis):
        """Test generating a simple cache key."""
        key = cache_service_with_redis._generate_cache_key(
            "test_prefix",
            param1="value1",
            param2="value2"
        )

        assert key.startswith("ai_cache:test_prefix:")
        assert isinstance(key, str)

    def test_generate_key_with_dict_param(self, cache_service_with_redis):
        """Test generating key with dictionary parameter."""
        key = cache_service_with_redis._generate_cache_key(
            "test_prefix",
            metadata={"title": "Test", "genre": "Fiction"}
        )

        assert key.startswith("ai_cache:test_prefix:")

    def test_generate_key_with_list_param(self, cache_service_with_redis):
        """Test generating key with list parameter."""
        key = cache_service_with_redis._generate_cache_key(
            "test_prefix",
            items=["item1", "item2", "item3"]
        )

        assert key.startswith("ai_cache:test_prefix:")

    def test_generate_key_consistency(self, cache_service_with_redis):
        """Test that same parameters generate same key."""
        key1 = cache_service_with_redis._generate_cache_key(
            "test",
            param1="value1",
            param2="value2"
        )
        key2 = cache_service_with_redis._generate_cache_key(
            "test",
            param2="value2",
            param1="value1"
        )

        assert key1 == key2

    def test_generate_key_ignores_none_values(self, cache_service_with_redis):
        """Test that None values are ignored in key generation."""
        key1 = cache_service_with_redis._generate_cache_key(
            "test",
            param1="value1",
            param2=None
        )
        key2 = cache_service_with_redis._generate_cache_key(
            "test",
            param1="value1"
        )

        assert key1 == key2


class TestGetCachedResponse:
    """Test getting cached responses."""

    @pytest.mark.asyncio
    async def test_get_cached_response_hit(self, cache_service_with_redis, mock_redis):
        """Test cache hit."""
        cached_data = {"result": "cached value", "status": "success"}
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_data))

        key = "ai_cache:test:key123"
        result = await cache_service_with_redis.get_cached_response(key)

        assert result == cached_data
        mock_redis.get.assert_called_once_with(key)

    @pytest.mark.asyncio
    async def test_get_cached_response_miss(self, cache_service_with_redis, mock_redis):
        """Test cache miss."""
        mock_redis.get = AsyncMock(return_value=None)

        key = "ai_cache:test:key123"
        result = await cache_service_with_redis.get_cached_response(key)

        assert result is None
        mock_redis.get.assert_called_once_with(key)

    @pytest.mark.asyncio
    async def test_get_cached_response_when_disabled(self, cache_service_disabled):
        """Test getting response when cache is disabled."""
        result = await cache_service_disabled.get_cached_response("any_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_cached_response_with_retry(self, cache_service_with_redis, mock_redis):
        """Test retry logic on failure."""
        # First call fails, second succeeds
        cached_data = {"result": "cached value"}
        mock_redis.get = AsyncMock(
            side_effect=[Exception("Connection error"), json.dumps(cached_data)]
        )

        key = "ai_cache:test:key123"
        result = await cache_service_with_redis.get_cached_response(key)

        assert result == cached_data
        assert mock_redis.get.call_count == 2


class TestSetCachedResponse:
    """Test setting cached responses."""

    @pytest.mark.asyncio
    async def test_set_cached_response(self, cache_service_with_redis, mock_redis):
        """Test caching a response."""
        key = "ai_cache:test:key123"
        response_data = {"result": "test value", "status": "success"}

        await cache_service_with_redis.set_cached_response(key, response_data)

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args

        assert call_args[0][0] == key
        assert call_args[0][1] == 3600  # Default TTL from fixture

        # Verify cached data includes metadata
        cached_data = json.loads(call_args[0][2])
        assert cached_data["result"] == "test value"
        assert "_cached_at" in cached_data
        assert cached_data["_from_cache"] is True

    @pytest.mark.asyncio
    async def test_set_cached_response_custom_ttl(self, cache_service_with_redis, mock_redis):
        """Test caching with custom TTL."""
        key = "ai_cache:test:key123"
        response_data = {"result": "test value"}
        custom_ttl = 7200

        await cache_service_with_redis.set_cached_response(
            key,
            response_data,
            ttl=custom_ttl
        )

        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == custom_ttl

    @pytest.mark.asyncio
    async def test_set_cached_response_when_disabled(self, cache_service_disabled):
        """Test setting response when cache is disabled."""
        # Should not raise exception
        await cache_service_disabled.set_cached_response(
            "any_key",
            {"data": "value"}
        )


class TestInvalidateCache:
    """Test cache invalidation."""

    @pytest.mark.asyncio
    async def test_invalidate_cache_pattern(self, cache_service_with_redis, mock_redis):
        """Test invalidating cache by pattern."""
        mock_redis.keys = AsyncMock(return_value=[
            "ai_cache:toc:key1",
            "ai_cache:toc:key2",
            "ai_cache:toc:key3"
        ])

        await cache_service_with_redis.invalidate_cache("ai_cache:toc:*")

        mock_redis.keys.assert_called_once_with("ai_cache:toc:*")
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_cache_no_matching_keys(self, cache_service_with_redis, mock_redis):
        """Test invalidating when no keys match."""
        mock_redis.keys = AsyncMock(return_value=[])

        await cache_service_with_redis.invalidate_cache("ai_cache:nonexistent:*")

        mock_redis.keys.assert_called_once()
        mock_redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalidate_cache_when_disabled(self, cache_service_disabled):
        """Test invalidating when cache is disabled."""
        # Should not raise exception
        await cache_service_disabled.invalidate_cache("any_pattern")


class TestCacheStats:
    """Test cache statistics."""

    @pytest.mark.asyncio
    async def test_get_cache_stats_enabled(self, cache_service_with_redis, mock_redis):
        """Test getting stats when cache is enabled."""
        mock_redis.keys = AsyncMock(side_effect=[
            ["key1", "key2"],  # toc_generation
            ["key3"],  # clarifying_questions
            [],  # summary_analysis
            ["key4"],  # chapter_questions
            []  # chapter_draft
        ])

        stats = await cache_service_with_redis.get_cache_stats()

        assert stats["enabled"] is True
        assert stats["connected"] is True
        assert "memory_usage" in stats
        assert "key_counts_by_type" in stats
        assert stats["key_counts_by_type"]["toc_generation"] == 2
        assert stats["key_counts_by_type"]["clarifying_questions"] == 1

    @pytest.mark.asyncio
    async def test_get_cache_stats_disabled(self):
        """Test getting stats when cache is disabled."""
        with patch('app.services.ai_cache_service.REDIS_AVAILABLE', False):
            with patch('app.services.ai_cache_service.settings.AI_CACHE_ENABLED', False):
                service = AICacheService()
                stats = await service.get_cache_stats()

                assert stats["enabled"] is False
                assert "message" in stats


class TestHelperFunctions:
    """Test cache helper functions."""

    @pytest.mark.asyncio
    async def test_get_toc_generation_cache(self, cache_service_with_redis, mock_redis):
        """Test TOC generation cache helper."""
        cached_data = {"toc": {"chapters": []}}
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_data))

        result = await get_toc_generation_cache(
            cache_service_with_redis,
            summary="Test summary",
            question_responses=[{"q": "test", "a": "answer"}]
        )

        assert result == cached_data

    @pytest.mark.asyncio
    async def test_set_toc_generation_cache(self, cache_service_with_redis, mock_redis):
        """Test TOC generation cache setter."""
        toc_data = {"toc": {"chapters": []}}

        await set_toc_generation_cache(
            cache_service_with_redis,
            summary="Test summary",
            question_responses=[{"q": "test", "a": "answer"}],
            response=toc_data
        )

        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_questions_cache(self, cache_service_with_redis, mock_redis):
        """Test questions cache helper."""
        cached_data = {"questions": ["Q1?", "Q2?", "Q3?"]}
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_data))

        result = await get_questions_cache(
            cache_service_with_redis,
            summary="Test summary"
        )

        assert result == ["Q1?", "Q2?", "Q3?"]

    @pytest.mark.asyncio
    async def test_set_questions_cache(self, cache_service_with_redis, mock_redis):
        """Test questions cache setter."""
        questions = ["Q1?", "Q2?", "Q3?"]

        await set_questions_cache(
            cache_service_with_redis,
            summary="Test summary",
            questions=questions
        )

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        cached_data = json.loads(call_args[0][2])
        assert cached_data["questions"] == questions


class TestCacheServiceClose:
    """Test cache service cleanup."""

    @pytest.mark.asyncio
    async def test_close_redis_connection(self, cache_service_with_redis, mock_redis):
        """Test closing Redis connection."""
        await cache_service_with_redis.close()

        mock_redis.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_when_no_connection(self, cache_service_disabled):
        """Test closing when there's no connection."""
        # Should not raise exception
        await cache_service_disabled.close()
