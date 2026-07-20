"""
Integration Tests for AI Service Error Handling
===============================================

Tests the AI service with comprehensive error handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import openai
import httpx
from app.services.ai_service import AIService
from app.services.ai_errors import (
    AIServiceError,
    AIRateLimitError,
    AINetworkError,
    AIServiceUnavailableError,
    AIInvalidRequestError
)


@pytest.fixture
def ai_service():
    """Create an AI service instance."""
    return AIService()


class TestAIServiceRateLimitHandling:
    """Test rate limit error handling."""

    @pytest.mark.asyncio
    async def test_rate_limit_error_raised(self, ai_service):
        """Test that rate limit errors are properly raised."""
        with patch.object(
            ai_service.client.chat.completions,
            'create',
            side_effect=openai.RateLimitError("Rate limit exceeded", response=httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com")), body=None)
        ):
            with pytest.raises(AIRateLimitError) as exc_info:
                await ai_service.generate_clarifying_questions(
                    summary="Test summary",
                    num_questions=3
                )

            error = exc_info.value
            assert error.error_code == "AI_RATE_LIMIT"
            assert error.retryable is True
            assert error.retry_after is not None
            assert error.correlation_id is not None


class TestAIServiceNetworkErrorHandling:
    """Test network error handling."""

    @pytest.mark.asyncio
    async def test_network_error_raised(self, ai_service):
        """Test that network errors are properly raised."""
        with patch.object(
            ai_service.client.chat.completions,
            'create',
            side_effect=openai.APIConnectionError(message="Connection failed", request=httpx.Request("POST", "https://api.openai.com"))
        ):
            with pytest.raises(AINetworkError) as exc_info:
                await ai_service.generate_clarifying_questions(
                    summary="Test summary"
                )

            error = exc_info.value
            assert error.error_code == "AI_NETWORK_ERROR"
            assert error.retryable is True
            assert error.correlation_id is not None

    @pytest.mark.asyncio
    async def test_timeout_error_raised(self, ai_service):
        """Test that timeout errors are properly raised."""
        with patch.object(
            ai_service.client.chat.completions,
            'create',
            side_effect=openai.APITimeoutError(request=httpx.Request("POST", "https://api.openai.com"))
        ):
            with pytest.raises(AINetworkError) as exc_info:
                await ai_service.generate_clarifying_questions(
                    summary="Test summary"
                )

            assert exc_info.value.error_code == "AI_NETWORK_ERROR"


class TestAIServiceUnavailableErrorHandling:
    """Test service unavailable error handling."""

    @pytest.mark.asyncio
    async def test_server_error_raised(self, ai_service):
        """Test that server errors are properly raised."""
        with patch.object(
            ai_service.client.chat.completions,
            'create',
            side_effect=openai.InternalServerError("Internal server error", response=MagicMock(), body=None)
        ):
            with pytest.raises(AIServiceUnavailableError) as exc_info:
                await ai_service.generate_clarifying_questions(
                    summary="Test summary"
                )

            error = exc_info.value
            assert error.error_code == "AI_SERVICE_UNAVAILABLE"
            assert error.retryable is True
            assert error.retry_after is not None


class TestAIServiceInvalidRequestHandling:
    """Test invalid request error handling."""

    @pytest.mark.asyncio
    async def test_bad_request_error_raised(self, ai_service):
        """Test that bad request errors are properly raised."""
        with patch.object(
            ai_service.client.chat.completions,
            'create',
            side_effect=openai.BadRequestError("Invalid request", response=MagicMock(), body=None)
        ):
            with pytest.raises(AIInvalidRequestError) as exc_info:
                await ai_service.generate_clarifying_questions(
                    summary="Test summary"
                )

            error = exc_info.value
            assert error.error_code == "AI_INVALID_REQUEST"
            assert error.retryable is False
            assert error.retry_after is None


class TestTOCGenerationWithErrorHandling:
    """Test TOC generation error handling."""

    @pytest.mark.asyncio
    async def test_toc_generation_error_propagates(self, ai_service):
        """Test TOC generation raises the classified error on failure."""
        with patch.object(
            ai_service.client.chat.completions,
            'create',
            side_effect=openai.RateLimitError("Rate limit", response=httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com")), body=None)
        ):
            with pytest.raises(AIRateLimitError):
                await ai_service.generate_toc_from_summary_and_responses(
                    summary="Test summary",
                    question_responses=[{"question": "Q1?", "answer": "A1"}]
                )


class TestCorrelationIDTracking:
    """Test correlation ID tracking in errors."""

    @pytest.mark.asyncio
    async def test_correlation_id_in_error(self, ai_service):
        """Test that errors include correlation IDs."""
        with patch.object(
            ai_service.client.chat.completions,
            'create',
            side_effect=openai.RateLimitError("Rate limit", response=httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com")), body=None)
        ):
            with pytest.raises(AIServiceError) as exc_info:
                await ai_service.generate_clarifying_questions(
                    summary="Test summary"
                )

            assert exc_info.value.correlation_id is not None
            assert isinstance(exc_info.value.correlation_id, str)
            assert len(exc_info.value.correlation_id) > 0


class TestRetryMechanism:
    """Test retry mechanism with backoff."""

    @pytest.mark.asyncio
    async def test_retry_succeeds_after_failure(self, ai_service):
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

        with patch.object(
            ai_service.client.chat.completions,
            'create',
            side_effect=mock_create
        ):
            result = await ai_service.generate_clarifying_questions(
                summary="Test summary"
            )

            assert len(result) > 0
            assert call_count == 2  # Failed once, succeeded on retry

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, ai_service):
        """Test that max retries is enforced."""
        # Set max retries to 2 for faster test
        ai_service.max_retries = 2

        with patch.object(
            ai_service.client.chat.completions,
            'create',
            side_effect=openai.APIConnectionError(message="Connection failed", request=httpx.Request("POST", "https://api.openai.com"))
        ):
            with pytest.raises(AINetworkError):
                await ai_service.generate_clarifying_questions(
                    summary="Test summary"
                )


class TestSingleRetryLayer:
    """Issue #188: retry must happen at exactly one layer.

    generate_clarifying_questions and generate_toc_from_summary_and_responses
    used to wrap _make_openai_request (which retries internally) in a second
    _retry_with_backoff. These tests pin single-layer behavior: a persistently
    failing call makes exactly AI_MAX_RETRIES real requests, logs one attempt
    line per request, and all attempt logs share one correlation id.

    NB: the two call-count tests pin the issue's AC but would also pass with
    the old double-wrap (the outer layer re-raised AIServiceError without
    retrying, so squaring never actually occurred). The log-based tests are
    the ones that fail if a second retry layer is reintroduced.
    """

    def _rate_limit_error(self):
        return openai.RateLimitError(
            "Rate limit exceeded",
            response=httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com")),
            body=None,
        )

    @pytest.mark.asyncio
    async def test_questions_persistent_failure_makes_at_most_max_retries_calls(
        self, ai_service
    ):
        """AC: persistently-failing call makes at most AI_MAX_RETRIES requests."""
        create_mock = MagicMock(side_effect=self._rate_limit_error())
        with patch.object(
            ai_service.client.chat.completions, 'create', create_mock
        ), patch('app.services.ai_service.asyncio.sleep', new=AsyncMock()):
            with pytest.raises(AIRateLimitError):
                await ai_service.generate_clarifying_questions(
                    summary="Test summary", num_questions=3
                )

        assert create_mock.call_count == ai_service.max_retries

    @pytest.mark.asyncio
    async def test_toc_persistent_failure_makes_at_most_max_retries_calls(
        self, ai_service
    ):
        """AC: persistently-failing TOC generation makes at most AI_MAX_RETRIES requests."""
        create_mock = MagicMock(side_effect=self._rate_limit_error())
        with patch.object(
            ai_service.client.chat.completions, 'create', create_mock
        ), patch('app.services.ai_service.asyncio.sleep', new=AsyncMock()):
            with pytest.raises(AIRateLimitError):
                await ai_service.generate_toc_from_summary_and_responses(
                    summary="Test summary",
                    question_responses=[{"question": "Q?", "answer": "A."}],
                )

        assert create_mock.call_count == ai_service.max_retries

    @pytest.mark.asyncio
    async def test_exactly_one_attempt_log_per_real_request(
        self, ai_service, caplog
    ):
        """A second retry layer logs its own extra 'Attempting API call' line."""
        import logging as _logging
        create_mock = MagicMock(side_effect=self._rate_limit_error())
        with caplog.at_level(_logging.INFO, logger="app.services.ai_service"):
            with patch.object(
                ai_service.client.chat.completions, 'create', create_mock
            ), patch('app.services.ai_service.asyncio.sleep', new=AsyncMock()):
                with pytest.raises(AIRateLimitError):
                    await ai_service.generate_clarifying_questions(
                        summary="Test summary", num_questions=3
                    )

        attempt_logs = [r for r in caplog.records if "Attempting API call" in r.message]
        assert len(attempt_logs) == create_mock.call_count

    @pytest.mark.asyncio
    async def test_attempt_logs_share_one_correlation_id(
        self, ai_service, caplog
    ):
        """Nested layers each mint their own correlation id, splitting the trace."""
        import logging as _logging
        import re
        create_mock = MagicMock(side_effect=self._rate_limit_error())
        with caplog.at_level(_logging.INFO, logger="app.services.ai_service"):
            with patch.object(
                ai_service.client.chat.completions, 'create', create_mock
            ), patch('app.services.ai_service.asyncio.sleep', new=AsyncMock()):
                with pytest.raises(AIRateLimitError):
                    await ai_service.generate_clarifying_questions(
                        summary="Test summary", num_questions=3
                    )

        ids = {
            m.group(1)
            for r in caplog.records
            if "Attempting API call" in r.message
            and (m := re.search(r"correlation_id=([0-9a-f-]+)", r.message))
        }
        assert len(ids) == 1

    def test_sdk_internal_retries_disabled(self, ai_service):
        """The openai SDK retries each request itself (default max_retries=2),
        stacking a third retry layer under _retry_with_backoff: a persistent
        failure made 3x3=9 real HTTP requests on the wire. The app layer is
        the sole retry owner, so the client must be built with max_retries=0.
        """
        assert ai_service.client.max_retries == 0
