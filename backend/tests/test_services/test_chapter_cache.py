"""
Comprehensive tests for chapter_cache_service.py.

Tests cover:
- Chapter content caching with TTL
- Cache retrieval (hit/miss)
- Cache invalidation on updates
- Cache warming for book
- Cache TTL expiration
- Cache statistics and health
- Concurrent cache access
- Cache key generation
- Edge cases (null content, large content, disabled cache)
"""

import pytest
import pytest_asyncio
import asyncio
import json
from typing import Dict, Any
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from app.services.chapter_cache_service import (
    ChapterMetadataCache,
    CacheConfig,
    chapter_cache,
    initialize_cache,
    cleanup_cache,
    invalidate_cache_on_chapter_update,
    invalidate_cache_on_book_update,
)


@pytest.fixture
def cache_config():
    """Create a test cache configuration."""
    return CacheConfig(
        chapter_metadata_ttl=60,
        tab_state_ttl=120,
        analytics_ttl=90,
        book_toc_ttl=100,
        max_retries=2,
        retry_delay=0.1,
    )


@pytest_asyncio.fixture
async def mock_redis_client():
    """Create a mock Redis client for testing."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=None)
    mock_client.setex = AsyncMock()
    mock_client.keys = AsyncMock(return_value=[])
    mock_client.delete = AsyncMock()
    mock_client.ping = AsyncMock()
    mock_client.info = AsyncMock(return_value={
        "used_memory_human": "1M",
        "db0": {"keys": 10}
    })
    mock_client.close = AsyncMock()
    return mock_client


@pytest_asyncio.fixture
async def cache_service(cache_config, mock_redis_client):
    """Create a cache service instance with mocked Redis."""
    with patch('app.services.chapter_cache_service.redis') as mock_redis_module:
        mock_redis_module.from_url = Mock(return_value=mock_redis_client)

        service = ChapterMetadataCache(
            redis_url="redis://localhost:6379/0",
            config=cache_config
        )
        service.enabled = True
        service.redis_client = mock_redis_client

        yield service

        await service.close()


@pytest_asyncio.fixture
async def disabled_cache_service(cache_config):
    """Create a disabled cache service for testing fallback behavior."""
    service = ChapterMetadataCache(redis_url=None, config=cache_config)
    service.enabled = False
    return service


class TestCacheInitialization:
    """Test suite for cache initialization."""

    def test_cache_disabled_when_redis_not_available(self):
        """Test that cache is disabled when Redis is not available."""
        with patch('app.services.chapter_cache_service.REDIS_AVAILABLE', False):
            cache = ChapterMetadataCache(redis_url="redis://localhost:6379/0")
            assert cache.enabled is False

    def test_cache_disabled_when_no_url_provided(self):
        """Test that cache is disabled when no URL is provided."""
        with patch('app.services.chapter_cache_service.settings') as mock_settings:
            mock_settings.REDIS_URL = None
            cache = ChapterMetadataCache()
            assert cache.enabled is False

    @pytest.mark.asyncio
    async def test_cache_initialization_success(self, cache_service):
        """Test successful cache initialization."""
        assert cache_service.enabled is True
        assert cache_service.redis_client is not None


class TestCacheKeyGeneration:
    """Test suite for cache key generation."""

    def test_generate_simple_key(self, cache_config):
        """Test generating simple cache key."""
        cache = ChapterMetadataCache(config=cache_config)
        cache.enabled = False  # Don't need Redis for this test

        key = cache._generate_cache_key("test_prefix", book_id="123", user_id="456")

        assert "test_prefix" in key
        assert "book_id:123" in key
        assert "user_id:456" in key

    def test_generate_key_with_sorted_params(self, cache_config):
        """Test that keys are consistent regardless of parameter order."""
        cache = ChapterMetadataCache(config=cache_config)
        cache.enabled = False

        key1 = cache._generate_cache_key("prefix", a="1", b="2", c="3")
        key2 = cache._generate_cache_key("prefix", c="3", a="1", b="2")

        assert key1 == key2

    def test_generate_key_hash_for_long_keys(self, cache_config):
        """Test that very long keys are hashed."""
        cache = ChapterMetadataCache(config=cache_config)
        cache.enabled = False

        long_value = "x" * 300
        key = cache._generate_cache_key("prefix", long_param=long_value)

        # Should contain hash indicator
        assert "hash:" in key
        # Should be shorter than 300 characters
        assert len(key) < 100

    def test_generate_key_ignores_none_values(self, cache_config):
        """Test that None values are ignored in key generation."""
        cache = ChapterMetadataCache(config=cache_config)
        cache.enabled = False

        key = cache._generate_cache_key("prefix", book_id="123", user_id=None)

        assert "book_id:123" in key
        assert "user_id" not in key


class TestChapterMetadataCaching:
    """Test suite for chapter metadata caching."""

    @pytest.mark.asyncio
    async def test_set_chapter_metadata(self, cache_service, mock_redis_client):
        """Test caching chapter metadata."""
        metadata = {
            "chapters": [{"id": "ch1", "title": "Chapter 1"}],
            "total_chapters": 1
        }

        await cache_service.set_chapter_metadata("book123", "user456", metadata)

        mock_redis_client.setex.assert_called_once()
        call_args = mock_redis_client.setex.call_args
        assert cache_service.config.chapter_metadata_ttl in call_args[0]

    @pytest.mark.asyncio
    async def test_get_chapter_metadata_hit(self, cache_service, mock_redis_client):
        """Test retrieving cached chapter metadata (cache hit)."""
        metadata = {
            "chapters": [{"id": "ch1", "title": "Chapter 1"}],
            "total_chapters": 1
        }
        mock_redis_client.get.return_value = json.dumps(metadata)

        result = await cache_service.get_chapter_metadata("book123", "user456")

        assert result == metadata
        mock_redis_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_chapter_metadata_miss(self, cache_service, mock_redis_client):
        """Test retrieving chapter metadata (cache miss)."""
        mock_redis_client.get.return_value = None

        result = await cache_service.get_chapter_metadata("book123", "user456")

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_disabled_returns_none(self, disabled_cache_service):
        """Test that disabled cache returns None for all operations."""
        result = await disabled_cache_service.get_chapter_metadata("book123", "user456")
        assert result is None

        # Should not raise exception
        await disabled_cache_service.set_chapter_metadata("book123", "user456", {})


class TestChapterContentCaching:
    """Test suite for chapter content caching."""

    @pytest.mark.asyncio
    async def test_set_chapter_content(self, cache_service, mock_redis_client):
        """Test caching chapter content."""
        content = {
            "title": "Chapter 1",
            "content": "This is the chapter content."
        }

        await cache_service.set_chapter_content("book123", "ch1", "user456", content)

        mock_redis_client.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_chapter_content_hit(self, cache_service, mock_redis_client):
        """Test retrieving cached chapter content."""
        content = {"title": "Chapter 1", "content": "Content here"}
        mock_redis_client.get.return_value = json.dumps(content)

        result = await cache_service.get_chapter_content("book123", "ch1", "user456")

        assert result == content

    @pytest.mark.asyncio
    async def test_cache_large_content(self, cache_service, mock_redis_client):
        """Test caching very large chapter content."""
        large_content = {
            "title": "Large Chapter",
            "content": "x" * 100000  # 100KB of content
        }

        await cache_service.set_chapter_content("book123", "ch1", "user456", large_content)

        # Should not crash
        mock_redis_client.setex.assert_called_once()


class TestTabStateCaching:
    """Test suite for tab state caching."""

    @pytest.mark.asyncio
    async def test_set_tab_state(self, cache_service, mock_redis_client):
        """Test caching tab state."""
        tab_state = {
            "active_chapter_id": "ch1",
            "open_tab_ids": ["ch1", "ch2"],
            "tab_order": ["ch1", "ch2"]
        }

        await cache_service.set_tab_state("book123", "user456", tab_state)

        mock_redis_client.setex.assert_called_once()
        call_args = mock_redis_client.setex.call_args
        assert cache_service.config.tab_state_ttl in call_args[0]

    @pytest.mark.asyncio
    async def test_get_tab_state(self, cache_service, mock_redis_client):
        """Test retrieving cached tab state."""
        tab_state = {"active_chapter_id": "ch1"}
        mock_redis_client.get.return_value = json.dumps(tab_state)

        result = await cache_service.get_tab_state("book123", "user456")

        assert result == tab_state


class TestAnalyticsCaching:
    """Test suite for analytics caching."""

    @pytest.mark.asyncio
    async def test_set_analytics_data(self, cache_service, mock_redis_client):
        """Test caching analytics data."""
        analytics = {
            "total_edits": 10,
            "word_count_changes": [100, 150, 200]
        }

        await cache_service.set_analytics_data("book123", "ch1", "user456", 7, analytics)

        mock_redis_client.setex.assert_called_once()
        call_args = mock_redis_client.setex.call_args
        assert cache_service.config.analytics_ttl in call_args[0]

    @pytest.mark.asyncio
    async def test_get_analytics_data(self, cache_service, mock_redis_client):
        """Test retrieving cached analytics."""
        analytics = {"total_edits": 10}
        mock_redis_client.get.return_value = json.dumps(analytics)

        result = await cache_service.get_analytics_data("book123", "ch1", "user456", 7)

        assert result == analytics


class TestCacheInvalidation:
    """Test suite for cache invalidation."""

    @pytest.mark.asyncio
    async def test_invalidate_book_cache(self, cache_service, mock_redis_client):
        """Test invalidating all cache entries for a book."""
        mock_redis_client.keys.return_value = [
            "chapter_metadata:book_id:book123:user_id:user456",
            "chapter_content:book_id:book123:chapter_id:ch1",
        ]

        await cache_service.invalidate_book_cache("book123", "user456")

        # Should call keys() with patterns
        assert mock_redis_client.keys.call_count >= 1
        # Should delete found keys
        mock_redis_client.delete.assert_called()

    @pytest.mark.asyncio
    async def test_invalidate_chapter_cache(self, cache_service, mock_redis_client):
        """Test invalidating cache entries for a specific chapter."""
        mock_redis_client.keys.return_value = [
            "chapter_content:book_id:book123:chapter_id:ch1:user_id:user456",
        ]

        await cache_service.invalidate_chapter_cache("book123", "ch1", "user456")

        assert mock_redis_client.keys.call_count >= 1
        mock_redis_client.delete.assert_called()

    @pytest.mark.asyncio
    async def test_invalidate_cache_with_no_matching_keys(self, cache_service, mock_redis_client):
        """Test invalidation when no keys match."""
        mock_redis_client.keys.return_value = []

        await cache_service.invalidate_book_cache("book123")

        # Should not call delete if no keys found
        assert mock_redis_client.delete.call_count == 0

    @pytest.mark.asyncio
    async def test_invalidate_cache_hooks(self):
        """Test cache invalidation hooks."""
        with patch('app.services.chapter_cache_service.chapter_cache') as mock_cache:
            mock_cache.invalidate_chapter_cache = AsyncMock()
            mock_cache.invalidate_book_cache = AsyncMock()

            # Test chapter update hook
            await invalidate_cache_on_chapter_update("book123", "ch1", "user456")

            # Test book update hook
            await invalidate_cache_on_book_update("book123", "user456")

            # Should have called invalidation methods
            mock_cache.invalidate_chapter_cache.assert_called_once_with("book123", "ch1", "user456")
            mock_cache.invalidate_book_cache.assert_called_once_with("book123", "user456")


class TestCacheWarming:
    """Test suite for cache warming."""

    @pytest.mark.asyncio
    async def test_warm_cache_for_book(self, cache_service, mock_redis_client):
        """Test warming cache with book data."""
        book_data = {
            "table_of_contents": {
                "chapters": [
                    {
                        "id": "ch1",
                        "title": "Chapter 1",
                        "status": "draft",
                        "word_count": 1000,
                        "last_modified": "2024-01-01T00:00:00"
                    },
                    {
                        "id": "ch2",
                        "title": "Chapter 2",
                        "status": "published",
                        "word_count": 1500
                    }
                ]
            }
        }

        await cache_service.warm_cache_for_book("book123", "user456", book_data)

        # Should have cached the metadata
        mock_redis_client.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_warm_cache_with_nested_chapters(self, cache_service, mock_redis_client):
        """Test warming cache with nested chapter structure."""
        book_data = {
            "table_of_contents": {
                "chapters": [
                    {
                        "id": "ch1",
                        "title": "Chapter 1",
                        "subchapters": [
                            {"id": "ch1.1", "title": "Section 1.1"},
                            {"id": "ch1.2", "title": "Section 1.2"}
                        ]
                    }
                ]
            }
        }

        await cache_service.warm_cache_for_book("book123", "user456", book_data)

        # Should have processed nested chapters
        mock_redis_client.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_warm_cache_with_empty_toc(self, cache_service, mock_redis_client):
        """Test warming cache when TOC is empty."""
        book_data = {"table_of_contents": {"chapters": []}}

        await cache_service.warm_cache_for_book("book123", "user456", book_data)

        # Should not crash
        assert True

    @pytest.mark.asyncio
    async def test_warm_cache_disabled(self, disabled_cache_service):
        """Test that warming cache when disabled doesn't crash."""
        book_data = {"table_of_contents": {"chapters": [{"id": "ch1"}]}}

        await disabled_cache_service.warm_cache_for_book("book123", "user456", book_data)

        # Should not crash
        assert True


class TestCacheStatistics:
    """Test suite for cache statistics."""

    @pytest.mark.asyncio
    async def test_get_cache_stats_enabled(self, cache_service, mock_redis_client):
        """Test getting cache statistics when cache is enabled."""
        mock_redis_client.info.return_value = {
            "used_memory_human": "5M",
            "db0": {"keys": 50}
        }
        mock_redis_client.keys.return_value = ["key1", "key2", "key3"]

        stats = await cache_service.get_cache_stats()

        assert stats["enabled"] is True
        assert stats["connected"] is True
        assert "memory_usage" in stats
        assert "total_keys" in stats
        assert "key_counts_by_type" in stats

    @pytest.mark.asyncio
    async def test_get_cache_stats_disabled(self, disabled_cache_service):
        """Test getting cache statistics when cache is disabled."""
        stats = await disabled_cache_service.get_cache_stats()

        assert stats["enabled"] is False
        assert "message" in stats

    @pytest.mark.asyncio
    async def test_get_cache_stats_connection_failure(self, cache_service, mock_redis_client):
        """Test cache stats when Redis connection fails."""
        mock_redis_client.info.side_effect = Exception("Connection failed")

        stats = await cache_service.get_cache_stats()

        assert stats["enabled"] is True
        assert stats["connected"] is False
        assert "error" in stats


class TestRetryLogic:
    """Test suite for retry logic."""

    @pytest.mark.asyncio
    async def test_retry_on_transient_failure(self, cache_service, mock_redis_client):
        """Test that operations retry on transient failures."""
        # Fail once, succeed on second attempt (max_retries is 2 in test config)
        mock_redis_client.get.side_effect = [
            Exception("Network error"),
            json.dumps({"data": "value"})
        ]

        result = await cache_service.get_chapter_metadata("book123", "user456")

        # Should eventually succeed after one retry
        assert result == {"data": "value"}
        assert mock_redis_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_exhaustion(self, cache_service, mock_redis_client):
        """Test that retry logic gives up after max attempts."""
        mock_redis_client.get.side_effect = Exception("Persistent error")

        result = await cache_service.get_chapter_metadata("book123", "user456")

        # Should return None after all retries exhausted
        assert result is None
        assert mock_redis_client.get.call_count == cache_service.config.max_retries


class TestConcurrentAccess:
    """Test suite for concurrent cache access."""

    @pytest.mark.asyncio
    async def test_concurrent_reads(self, cache_service, mock_redis_client):
        """Test concurrent cache read operations."""
        mock_redis_client.get.return_value = json.dumps({"data": "value"})

        # Simulate concurrent reads
        tasks = [
            cache_service.get_chapter_metadata("book123", f"user{i}")
            for i in range(10)
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(r == {"data": "value"} for r in results)
        assert mock_redis_client.get.call_count == 10

    @pytest.mark.asyncio
    async def test_concurrent_writes(self, cache_service, mock_redis_client):
        """Test concurrent cache write operations."""
        metadata = {"chapters": []}

        # Simulate concurrent writes
        tasks = [
            cache_service.set_chapter_metadata("book123", f"user{i}", metadata)
            for i in range(10)
        ]

        await asyncio.gather(*tasks)

        # All should succeed
        assert mock_redis_client.setex.call_count == 10


class TestCacheCleanup:
    """Test suite for cache cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_expired_cache(self, cache_service, mock_redis_client):
        """Test cleaning up expired cache entries."""
        mock_redis_client.info.return_value = {"expired_keys": 42}

        result = await cache_service.cleanup_expired_cache()

        assert result["expired_keys_cleaned"] == 42

    @pytest.mark.asyncio
    async def test_close_connection(self, cache_service, mock_redis_client):
        """Test closing Redis connection."""
        await cache_service.close()

        mock_redis_client.close.assert_called_once()


class TestModuleFunctions:
    """Test suite for module-level functions."""

    @pytest.mark.asyncio
    async def test_initialize_cache(self):
        """Test cache initialization function."""
        with patch('app.services.chapter_cache_service.chapter_cache') as mock_cache:
            mock_cache.enabled = True
            mock_cache.get_cache_stats = AsyncMock(return_value={"status": "ok"})

            await initialize_cache()

            # Should have called get_cache_stats
            mock_cache.get_cache_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_cache(self):
        """Test cache cleanup function."""
        with patch('app.services.chapter_cache_service.chapter_cache') as mock_cache:
            mock_cache.close = AsyncMock()

            await cleanup_cache()

            mock_cache.close.assert_called_once()
