"""
Integration Tests for AI Service Error Handling
===============================================

Tests the AI service with comprehensive error handling and caching.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import openai
import httpx
from app.services.ai_service import AIService
from app.services.ai_cache_service import AICacheService
from app.services.ai_errors import (
    AIServiceError,
    AIRateLimitError,
    AINetworkError,
    AIServiceUnavailableError,
    AIInvalidRequestError
)


@pytest.fixture
def mock_cache_service():
    """Create a mock cache service."""
    mock = AsyncMock(spec=AICacheService)
    mock.enabled = True
    mock.get_cached_response = AsyncMock(return_value=None)
    mock.set_cached_response = AsyncMock()
    return mock


@pytest.fixture
def ai_service_with_mock_cache(mock_cache_service):
    """Create AI service with mocked cache."""
    service = AIService(cache_service=mock_cache_service)
    return service


class TestAIServiceRateLimitHandling:
    """Test rate limit error handling."""

    @pytest.mark.asyncio
    async def test_rate_limit_error_raised(self, ai_service_with_mock_cache):
        """Test that rate limit errors are properly raised."""
        with patch.object(
            ai_service_with_mock_cache.client.chat.completions,
            'create',
            side_effect=openai.RateLimitError("Rate limit exceeded", response=httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com")), body=None)
        ):
            with pytest.raises(AIRateLimitError) as exc_info:
                await ai_service_with_mock_cache.generate_clarifying_questions(
                    summary="Test summary",
                    num_questions=3
                )

            error = exc_info.value
            assert error.error_code == "AI_RATE_LIMIT"
            assert error.retryable is True
            assert error.retry_after is not None
            assert error.correlation_id is not None

    @pytest.mark.asyncio
    async def test_rate_limit_with_cached_fallback(self, ai_service_with_mock_cache, mock_cache_service):
        """Test rate limit error returns cached content when available."""
        # Mock cache to return fallback content after initial miss
        cached_questions = ["Q1?", "Q2?", "Q3?"]

        async def mock_get_cache(*args, **kwargs):
            # First call returns None, second call returns cached data
            if mock_get_cache.call_count == 1:
                mock_get_cache.call_count += 1
                return None
            return cached_questions

        mock_get_cache.call_count = 1

        # Patch the helper function directly
        with patch('app.services.ai_service.get_questions_cache', side_effect=mock_get_cache):
            with patch.object(
                ai_service_with_mock_cache.client.chat.completions,
                'create',
                side_effect=openai.RateLimitError("Rate limit exceeded", response=httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com")), body=None)
            ):
                # Should return cached questions instead of raising error
                result = await ai_service_with_mock_cache.generate_clarifying_questions(
                    summary="Test summary",
                    num_questions=3
                )

                assert result == cached_questions


class TestAIServiceNetworkErrorHandling:
    """Test network error handling."""

    @pytest.mark.asyncio
    async def test_network_error_raised(self, ai_service_with_mock_cache):
        """Test that network errors are properly raised."""
        with patch.object(
            ai_service_with_mock_cache.client.chat.completions,
            'create',
            side_effect=openai.APIConnectionError(message="Connection failed", request=httpx.Request("POST", "https://api.openai.com"))
        ):
            with pytest.raises(AINetworkError) as exc_info:
                await ai_service_with_mock_cache.generate_clarifying_questions(
                    summary="Test summary"
                )

            error = exc_info.value
            assert error.error_code == "AI_NETWORK_ERROR"
            assert error.retryable is True
            assert error.correlation_id is not None

    @pytest.mark.asyncio
    async def test_timeout_error_raised(self, ai_service_with_mock_cache):
        """Test that timeout errors are properly raised."""
        with patch.object(
            ai_service_with_mock_cache.client.chat.completions,
            'create',
            side_effect=openai.APITimeoutError(request=httpx.Request("POST", "https://api.openai.com"))
        ):
            with pytest.raises(AINetworkError) as exc_info:
                await ai_service_with_mock_cache.generate_clarifying_questions(
                    summary="Test summary"
                )

            assert exc_info.value.error_code == "AI_NETWORK_ERROR"


class TestAIServiceUnavailableErrorHandling:
    """Test service unavailable error handling."""

    @pytest.mark.asyncio
    async def test_server_error_raised(self, ai_service_with_mock_cache):
        """Test that server errors are properly raised."""
        with patch.object(
            ai_service_with_mock_cache.client.chat.completions,
            'create',
            side_effect=openai.InternalServerError("Internal server error", response=MagicMock(), body=None)
        ):
            with pytest.raises(AIServiceUnavailableError) as exc_info:
                await ai_service_with_mock_cache.generate_clarifying_questions(
                    summary="Test summary"
                )

            error = exc_info.value
            assert error.error_code == "AI_SERVICE_UNAVAILABLE"
            assert error.retryable is True
            assert error.retry_after is not None


class TestAIServiceInvalidRequestHandling:
    """Test invalid request error handling."""

    @pytest.mark.asyncio
    async def test_bad_request_error_raised(self, ai_service_with_mock_cache):
        """Test that bad request errors are properly raised."""
        with patch.object(
            ai_service_with_mock_cache.client.chat.completions,
            'create',
            side_effect=openai.BadRequestError("Invalid request", response=MagicMock(), body=None)
        ):
            with pytest.raises(AIInvalidRequestError) as exc_info:
                await ai_service_with_mock_cache.generate_clarifying_questions(
                    summary="Test summary"
                )

            error = exc_info.value
            assert error.error_code == "AI_INVALID_REQUEST"
            assert error.retryable is False
            assert error.retry_after is None


class TestAIServiceCachingBehavior:
    """Test caching behavior in AI service."""

    @pytest.mark.asyncio
    async def test_cache_hit_skips_api_call(self, ai_service_with_mock_cache):
        """Test that cache hits skip API calls."""
        cached_questions = ["Cached Q1?", "Cached Q2?"]

        with patch('app.services.ai_service.get_questions_cache', return_value=cached_questions):
            result = await ai_service_with_mock_cache.generate_clarifying_questions(
                summary="Test summary"
            )

            assert result == cached_questions

    @pytest.mark.asyncio
    async def test_successful_response_cached(self, ai_service_with_mock_cache):
        """Test that successful responses are cached."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "1. Question 1?\n2. Question 2?\n3. Question 3?"

        with patch('app.services.ai_service.get_questions_cache', return_value=None):
            with patch('app.services.ai_service.set_questions_cache') as mock_set_cache:
                with patch.object(
                    ai_service_with_mock_cache.client.chat.completions,
                    'create',
                    return_value=mock_response
                ):
                    await ai_service_with_mock_cache.generate_clarifying_questions(
                        summary="Test summary",
                        num_questions=3
                    )

                    # Verify cache was called
                    mock_set_cache.assert_called_once()


class TestTOCGenerationWithErrorHandling:
    """Test TOC generation with error handling and caching."""

    @pytest.mark.asyncio
    async def test_toc_generation_with_cache_hit(self, ai_service_with_mock_cache):
        """Test TOC generation returns cached result."""
        cached_toc = {
            "toc": {"chapters": [{"id": "ch1", "title": "Chapter 1"}]},
            "success": True
        }

        with patch('app.services.ai_service.get_toc_generation_cache', return_value=cached_toc):
            result = await ai_service_with_mock_cache.generate_toc_from_summary_and_responses(
                summary="Test summary",
                question_responses=[{"question": "Q1?", "answer": "A1"}]
            )

            assert result == cached_toc

    @pytest.mark.asyncio
    async def test_toc_generation_error_with_fallback(self, ai_service_with_mock_cache):
        """Test TOC generation falls back to cache on error."""
        cached_toc = {
            "toc": {"chapters": [{"id": "ch1", "title": "Cached Chapter"}]},
            "success": True
        }

        async def mock_get_cache(*args, **kwargs):
            if mock_get_cache.call_count == 1:
                mock_get_cache.call_count += 1
                return None
            return cached_toc

        mock_get_cache.call_count = 1

        with patch('app.services.ai_service.get_toc_generation_cache', side_effect=mock_get_cache):
            with patch.object(
                ai_service_with_mock_cache.client.chat.completions,
                'create',
                side_effect=openai.RateLimitError("Rate limit", response=httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com")), body=None)
            ):
                result = await ai_service_with_mock_cache.generate_toc_from_summary_and_responses(
                    summary="Test summary",
                    question_responses=[{"question": "Q1?", "answer": "A1"}]
                )

                assert result == cached_toc

    @pytest.mark.asyncio
    async def test_toc_generation_error_no_cache(self, ai_service_with_mock_cache):
        """Test TOC generation raises error when no cache available."""
        with patch('app.services.ai_service.get_toc_generation_cache', return_value=None):
            with patch.object(
                ai_service_with_mock_cache.client.chat.completions,
                'create',
                side_effect=openai.RateLimitError("Rate limit", response=httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com")), body=None)
            ):
                with pytest.raises(AIRateLimitError):
                    await ai_service_with_mock_cache.generate_toc_from_summary_and_responses(
                        summary="Test summary",
                        question_responses=[{"question": "Q1?", "answer": "A1"}]
                    )


class TestCorrelationIDTracking:
    """Test correlation ID tracking in errors."""

    @pytest.mark.asyncio
    async def test_correlation_id_in_error(self, ai_service_with_mock_cache):
        """Test that errors include correlation IDs."""
        with patch.object(
            ai_service_with_mock_cache.client.chat.completions,
            'create',
            side_effect=openai.RateLimitError("Rate limit", response=httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com")), body=None)
        ):
            with pytest.raises(AIServiceError) as exc_info:
                await ai_service_with_mock_cache.generate_clarifying_questions(
                    summary="Test summary"
                )

            assert exc_info.value.correlation_id is not None
            assert isinstance(exc_info.value.correlation_id, str)
            assert len(exc_info.value.correlation_id) > 0


class TestRetryMechanism:
    """Test retry mechanism with backoff."""

    @pytest.mark.asyncio
    async def test_retry_succeeds_after_failure(self, ai_service_with_mock_cache):
        """Test that retry mechanism succeeds after initial failures."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "1. Question 1?\n2. Question 2?"

        call_count = 0

        def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise openai.APIConnectionError(message="Connection failed", request=httpx.Request("POST", "https://api.openai.com"))
            return mock_response

        with patch('app.services.ai_service.get_questions_cache', return_value=None):
            with patch('app.services.ai_service.set_questions_cache'):
                with patch.object(
                    ai_service_with_mock_cache.client.chat.completions,
                    'create',
                    side_effect=mock_create
                ):
                    result = await ai_service_with_mock_cache.generate_clarifying_questions(
                        summary="Test summary"
                    )

                    assert len(result) > 0
                    assert call_count == 2  # Failed once, succeeded on retry

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, ai_service_with_mock_cache):
        """Test that max retries is enforced."""
        # Set max retries to 2 for faster test
        ai_service_with_mock_cache.max_retries = 2

        with patch.object(
            ai_service_with_mock_cache.client.chat.completions,
            'create',
            side_effect=openai.APIConnectionError(message="Connection failed", request=httpx.Request("POST", "https://api.openai.com"))
        ):
            with pytest.raises(AINetworkError):
                await ai_service_with_mock_cache.generate_clarifying_questions(
                    summary="Test summary"
                )
