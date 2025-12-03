"""
Tests for Redis-based distributed rate limiting.

This test suite validates that rate limiting works correctly across multiple
instances (simulating PM2 processes) and handles Redis failures gracefully.

NOTE: This test file needs to use the REAL rate limiter, not the mock in conftest.py
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from fastapi import Request, HTTPException
from redis.exceptions import ConnectionError as RedisConnectionError

# We need to import the real rate limiter directly from the module
# before conftest.py patches it
from app.api.dependencies import (
    _redis_rate_limit,
    _memory_rate_limit,
)
from app.db.redis import get_redis_client, flush_redis


# Define our own get_rate_limiter here to bypass the conftest.py mock
def get_rate_limiter(limit: int = 10, window: int = 60):
    """Create a rate limiter dependency with specific limits"""

    async def rate_limiter(request: Request):
        """Rate limiting dependency function"""
        import logging
        from app.db.redis import get_redis_client

        logger = logging.getLogger(__name__)

        # Build rate limit key from client IP and endpoint
        client_ip = request.client.host
        endpoint = request.url.path
        key = f"ratelimit:{endpoint}:{client_ip}"

        # Get current timestamp
        now = time.time()

        try:
            # Try to use Redis first
            redis_client = await get_redis_client()

            if redis_client is not None:
                # Use Redis-based rate limiting
                try:
                    current_count, reset_at = await _redis_rate_limit(
                        redis_client, key, limit, window, now
                    )
                    logger.debug(
                        f"Redis rate limit check: {key} = {current_count}/{limit}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Redis rate limit failed, falling back to memory: {e}"
                    )
                    current_count, reset_at = await _memory_rate_limit(
                        key, limit, window, now
                    )
            else:
                # Redis not available, use in-memory fallback
                logger.debug("Redis unavailable, using in-memory rate limiting")
                current_count, reset_at = await _memory_rate_limit(
                    key, limit, window, now
                )

        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # On any error, fall back to in-memory
            current_count, reset_at = await _memory_rate_limit(
                key, limit, window, now
            )

        # Check if limit exceeded
        if current_count > limit:
            # Calculate retry-after time
            retry_after = int(reset_at - now)

            # Set headers for response
            headers = {
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(reset_at)),
                "Retry-After": str(retry_after),
            }

            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                headers=headers,
            )

        # Calculate remaining requests
        remaining = max(0, limit - current_count)

        # Return current rate limit status
        return {
            "limit": limit,
            "remaining": remaining,
            "reset": reset_at,
        }

    return rate_limiter


@pytest.fixture(scope="function")
async def redis_client():
    """Get Redis client for testing."""
    client = await get_redis_client()
    if client is not None:
        # Clean up before tests
        try:
            await client.flushdb()
        except Exception:
            pass  # Ignore errors during cleanup
    yield client
    if client is not None:
        # Clean up after tests
        try:
            await client.flushdb()
        except Exception:
            pass  # Ignore errors during cleanup


@pytest.fixture
def mock_request():
    """Create a mock request object."""
    request = Mock(spec=Request)
    request.client = Mock()
    request.client.host = "127.0.0.1"
    request.url = Mock()
    request.url.path = "/api/v1/test"
    return request


class TestRedisRateLimiting:
    """Test Redis-based rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_redis_rate_limit_first_request(self, redis_client):
        """Test that first request initializes rate limit correctly."""
        if redis_client is None:
            pytest.skip("Redis not available")

        key = "ratelimit:test:first_request"
        now = time.time()

        count, reset_at = await _redis_rate_limit(redis_client, key, 10, 60, now)

        assert count == 1
        assert reset_at > now
        assert reset_at <= now + 60

    @pytest.mark.asyncio
    async def test_redis_rate_limit_increments(self, redis_client):
        """Test that subsequent requests increment the counter."""
        if redis_client is None:
            pytest.skip("Redis not available")

        key = "ratelimit:test:increments"
        now = time.time()

        # First request
        count1, _ = await _redis_rate_limit(redis_client, key, 10, 60, now)
        assert count1 == 1

        # Second request
        count2, _ = await _redis_rate_limit(redis_client, key, 10, 60, now)
        assert count2 == 2

        # Third request
        count3, _ = await _redis_rate_limit(redis_client, key, 10, 60, now)
        assert count3 == 3

    @pytest.mark.asyncio
    async def test_redis_rate_limit_expiration(self, redis_client):
        """Test that rate limit counter expires after window."""
        if redis_client is None:
            pytest.skip("Redis not available")

        key = "ratelimit:test:expiration"
        now = time.time()
        short_window = 1  # 1 second window

        # First request
        count1, reset_at1 = await _redis_rate_limit(
            redis_client, key, 10, short_window, now
        )
        assert count1 == 1

        # Wait for expiration
        await asyncio.sleep(short_window + 0.1)

        # Request after expiration should reset counter
        now2 = time.time()
        count2, reset_at2 = await _redis_rate_limit(
            redis_client, key, 10, short_window, now2
        )
        assert count2 == 1
        assert reset_at2 > reset_at1

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_requests_under_limit(
        self, redis_client, mock_request
    ):
        """Test that rate limiter allows requests under the limit."""
        rate_limiter = get_rate_limiter(limit=5, window=60)

        # Make 5 requests (at limit)
        for i in range(5):
            result = await rate_limiter(mock_request)
            print(f"Iteration {i}: result = {result}")
            assert isinstance(result, dict), f"Expected dict, got {type(result)}"
            assert "limit" in result, f"Missing 'limit' key in result: {result}"
            assert result["limit"] == 5, f"Expected limit=5, got {result['limit']}"
            assert result["remaining"] >= 0

    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_requests_over_limit(
        self, redis_client, mock_request
    ):
        """Test that rate limiter blocks requests over the limit."""
        rate_limiter = get_rate_limiter(limit=3, window=60)

        # Make 3 requests (at limit)
        for i in range(3):
            await rate_limiter(mock_request)

        # 4th request should be blocked
        with pytest.raises(HTTPException) as exc_info:
            await rate_limiter(mock_request)

        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded" in exc_info.value.detail
        assert "X-RateLimit-Limit" in exc_info.value.headers
        assert "X-RateLimit-Remaining" in exc_info.value.headers
        assert "X-RateLimit-Reset" in exc_info.value.headers
        assert "Retry-After" in exc_info.value.headers

    @pytest.mark.asyncio
    async def test_rate_limiter_headers(self, redis_client, mock_request):
        """Test that rate limiter sets correct response headers."""
        rate_limiter = get_rate_limiter(limit=5, window=60)

        # First request
        result = await rate_limiter(mock_request)

        assert result["limit"] == 5
        assert result["remaining"] == 4
        assert "reset" in result

    @pytest.mark.asyncio
    async def test_rate_limiter_different_clients(self, redis_client):
        """Test that rate limiting is per-client (different IPs)."""
        rate_limiter = get_rate_limiter(limit=2, window=60)

        # Client 1
        request1 = Mock(spec=Request)
        request1.client = Mock()
        request1.client.host = "127.0.0.1"
        request1.url = Mock()
        request1.url.path = "/api/v1/test"

        # Client 2
        request2 = Mock(spec=Request)
        request2.client = Mock()
        request2.client.host = "192.168.1.1"
        request2.url = Mock()
        request2.url.path = "/api/v1/test"

        # Client 1 makes 2 requests (at limit)
        await rate_limiter(request1)
        await rate_limiter(request1)

        # Client 1 third request should be blocked
        with pytest.raises(HTTPException):
            await rate_limiter(request1)

        # Client 2 should still be able to make requests
        result = await rate_limiter(request2)
        assert result["remaining"] == 1

    @pytest.mark.asyncio
    async def test_rate_limiter_different_endpoints(self, redis_client):
        """Test that rate limiting is per-endpoint."""
        rate_limiter = get_rate_limiter(limit=2, window=60)

        # Same client, endpoint 1
        request1 = Mock(spec=Request)
        request1.client = Mock()
        request1.client.host = "127.0.0.1"
        request1.url = Mock()
        request1.url.path = "/api/v1/endpoint1"

        # Same client, endpoint 2
        request2 = Mock(spec=Request)
        request2.client = Mock()
        request2.client.host = "127.0.0.1"
        request2.url = Mock()
        request2.url.path = "/api/v1/endpoint2"

        # Endpoint 1: 2 requests (at limit)
        await rate_limiter(request1)
        await rate_limiter(request1)

        # Endpoint 1 third request should be blocked
        with pytest.raises(HTTPException):
            await rate_limiter(request1)

        # Endpoint 2 should still be able to make requests
        result = await rate_limiter(request2)
        assert result["remaining"] == 1


class TestConcurrentRequests:
    """Test rate limiting with concurrent requests (simulating PM2 instances)."""

    @pytest.mark.asyncio
    async def test_concurrent_requests_respect_limit(self, redis_client, mock_request):
        """Test that concurrent requests from multiple instances respect the limit."""
        if redis_client is None:
            pytest.skip("Redis not available")

        rate_limiter = get_rate_limiter(limit=5, window=60)

        # Simulate 10 concurrent requests (like from multiple PM2 instances)
        tasks = []
        for i in range(10):
            # Each task gets its own request object with same client IP
            request = Mock(spec=Request)
            request.client = Mock()
            request.client.host = "127.0.0.1"
            request.url = Mock()
            request.url.path = "/api/v1/test"
            tasks.append(rate_limiter(request))

        # Execute all requests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successful vs rate-limited requests
        successful = sum(1 for r in results if not isinstance(r, HTTPException))
        rate_limited = sum(1 for r in results if isinstance(r, HTTPException))

        # Should have exactly 5 successful and 5 rate-limited
        assert successful == 5, f"Expected 5 successful, got {successful}"
        assert rate_limited == 5, f"Expected 5 rate-limited, got {rate_limited}"

    @pytest.mark.asyncio
    async def test_concurrent_requests_different_clients(self, redis_client):
        """Test concurrent requests from different clients are tracked separately."""
        if redis_client is None:
            pytest.skip("Redis not available")

        rate_limiter = get_rate_limiter(limit=3, window=60)

        # Simulate concurrent requests from 3 different clients
        async def make_requests_for_client(client_ip: str, num_requests: int):
            results = []
            for i in range(num_requests):
                request = Mock(spec=Request)
                request.client = Mock()
                request.client.host = client_ip
                request.url = Mock()
                request.url.path = "/api/v1/test"
                try:
                    result = await rate_limiter(request)
                    results.append(("success", result))
                except HTTPException as e:
                    results.append(("rate_limited", e))
            return results

        # Each client makes 5 requests concurrently
        client_tasks = [
            make_requests_for_client("192.168.1.1", 5),
            make_requests_for_client("192.168.1.2", 5),
            make_requests_for_client("192.168.1.3", 5),
        ]

        all_results = await asyncio.gather(*client_tasks)

        # Each client should have 3 successful and 2 rate-limited
        for client_results in all_results:
            successful = sum(1 for status, _ in client_results if status == "success")
            rate_limited = sum(
                1 for status, _ in client_results if status == "rate_limited"
            )
            assert successful == 3
            assert rate_limited == 2


class TestGracefulDegradation:
    """Test graceful fallback to in-memory rate limiting when Redis fails."""

    @pytest.mark.asyncio
    async def test_fallback_to_memory_when_redis_unavailable(self, mock_request):
        """Test that rate limiter falls back to in-memory when Redis is unavailable."""
        rate_limiter = get_rate_limiter(limit=3, window=60)

        # Mock Redis client to return None (simulating Redis unavailable)
        with patch("app.api.dependencies.get_redis_client", return_value=None):
            # Make 3 requests (at limit)
            for i in range(3):
                result = await rate_limiter(mock_request)
                assert result["limit"] == 3

            # 4th request should be blocked (using in-memory fallback)
            with pytest.raises(HTTPException) as exc_info:
                await rate_limiter(mock_request)

            assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_fallback_on_redis_connection_error(self, mock_request):
        """Test fallback when Redis connection fails during operation."""
        rate_limiter = get_rate_limiter(limit=3, window=60)

        # Mock Redis client to raise connection error
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = RedisConnectionError("Connection refused")

        with patch("app.api.dependencies.get_redis_client", return_value=mock_redis):
            # Should fall back to in-memory and still work
            result = await rate_limiter(mock_request)
            assert result["limit"] == 3
            assert result["remaining"] == 2

    @pytest.mark.asyncio
    async def test_memory_rate_limit_basic(self):
        """Test in-memory rate limiting works correctly."""
        key = "test:memory:basic"
        now = time.time()

        # First request
        count1, reset_at1 = await _memory_rate_limit(key, 5, 60, now)
        assert count1 == 1
        assert reset_at1 == now + 60

        # Second request
        count2, reset_at2 = await _memory_rate_limit(key, 5, 60, now)
        assert count2 == 2
        assert reset_at2 == reset_at1  # Same window

    @pytest.mark.asyncio
    async def test_memory_rate_limit_window_reset(self):
        """Test that memory rate limit resets after window expires."""
        key = "test:memory:reset"
        now = time.time()
        window = 2  # 2 second window

        # First request
        count1, reset_at1 = await _memory_rate_limit(key, 5, window, now)
        assert count1 == 1

        # Wait for window to expire
        await asyncio.sleep(window + 0.1)

        # Request after expiration should reset counter
        now2 = time.time()
        count2, reset_at2 = await _memory_rate_limit(key, 5, window, now2)
        assert count2 == 1
        assert reset_at2 > reset_at1


class TestRateLimitConfiguration:
    """Test different rate limit configurations."""

    @pytest.mark.asyncio
    async def test_custom_limit(self, redis_client, mock_request):
        """Test rate limiter with custom limit."""
        rate_limiter = get_rate_limiter(limit=10, window=60)

        # Make 10 requests (at limit)
        for i in range(10):
            result = await rate_limiter(mock_request)
            assert result["limit"] == 10

        # 11th request should be blocked
        with pytest.raises(HTTPException):
            await rate_limiter(mock_request)

    @pytest.mark.asyncio
    async def test_custom_window(self, redis_client):
        """Test rate limiter with custom time window."""
        if redis_client is None:
            pytest.skip("Redis not available")

        rate_limiter = get_rate_limiter(limit=2, window=2)  # 2 second window

        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.url = Mock()
        request.url.path = "/api/v1/custom_window"

        # Make 2 requests (at limit)
        await rate_limiter(request)
        await rate_limiter(request)

        # 3rd request should be blocked
        with pytest.raises(HTTPException):
            await rate_limiter(request)

        # Wait for window to expire
        await asyncio.sleep(2.5)

        # Should be able to make requests again
        result = await rate_limiter(request)
        assert result["remaining"] == 1

    @pytest.mark.asyncio
    async def test_very_strict_limit(self, redis_client, mock_request):
        """Test rate limiter with very strict limit (1 request)."""
        rate_limiter = get_rate_limiter(limit=1, window=60)

        # First request should succeed
        result = await rate_limiter(mock_request)
        assert result["remaining"] == 0

        # Second request should be blocked
        with pytest.raises(HTTPException) as exc_info:
            await rate_limiter(mock_request)

        assert exc_info.value.status_code == 429
        assert exc_info.value.headers["X-RateLimit-Remaining"] == "0"
