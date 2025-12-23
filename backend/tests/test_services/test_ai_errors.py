"""
Tests for AI Service Error Types
=================================

Tests the custom exception classes used for AI service error handling.
"""

import pytest
from datetime import datetime
from app.services.ai_errors import (
    AIServiceError,
    AIRateLimitError,
    AINetworkError,
    AIServiceUnavailableError,
    AIInvalidRequestError,
    AIResponseParsingError,
    AICacheError
)


class TestAIServiceError:
    """Test the base AIServiceError class."""

    def test_base_error_initialization(self):
        """Test basic error initialization."""
        error = AIServiceError(
            message="Test error",
            error_code="TEST_ERROR",
            retryable=True,
            retry_after=30
        )

        assert error.message == "Test error"
        assert error.error_code == "TEST_ERROR"
        assert error.retryable is True
        assert error.retry_after == 30
        assert error.cached_content_available is False
        assert error.original_exception is None
        assert error.correlation_id is None
        assert isinstance(error.timestamp, str)

    def test_error_with_all_parameters(self):
        """Test error with all optional parameters."""
        original = ValueError("Original error")
        error = AIServiceError(
            message="Test error",
            error_code="TEST_ERROR",
            retryable=True,
            retry_after=60,
            cached_content_available=True,
            original_exception=original,
            correlation_id="test-123"
        )

        assert error.cached_content_available is True
        assert error.original_exception is original
        assert error.correlation_id == "test-123"

    def test_error_to_dict(self):
        """Test error serialization to dictionary."""
        error = AIServiceError(
            message="Test error",
            error_code="TEST_ERROR",
            retryable=True,
            retry_after=30,
            correlation_id="test-123"
        )

        error_dict = error.to_dict()

        assert "error" in error_dict
        assert error_dict["error"]["message"] == "Test error"
        assert error_dict["error"]["error_code"] == "TEST_ERROR"
        assert error_dict["error"]["retryable"] is True
        assert error_dict["error"]["retry_after"] == 30
        assert error_dict["error"]["correlation_id"] == "test-123"
        assert "timestamp" in error_dict["error"]

    def test_error_string_representation(self):
        """Test error string representation."""
        error = AIServiceError(
            message="Test error",
            error_code="TEST_ERROR",
            retry_after=30,
            correlation_id="test-123"
        )

        error_str = str(error)
        assert "TEST_ERROR" in error_str
        assert "Test error" in error_str
        assert "retry_after=30s" in error_str
        assert "correlation_id=test-123" in error_str


class TestAIRateLimitError:
    """Test the AIRateLimitError class."""

    def test_rate_limit_error_defaults(self):
        """Test rate limit error with default values."""
        error = AIRateLimitError()

        assert error.error_code == "AI_RATE_LIMIT"
        assert error.retryable is True
        assert error.retry_after == 60
        assert "rate limit" in error.message.lower()

    def test_rate_limit_error_custom_retry_after(self):
        """Test rate limit error with custom retry_after."""
        error = AIRateLimitError(retry_after=120)

        assert error.retry_after == 120
        assert error.retryable is True

    def test_rate_limit_error_with_cached_content(self):
        """Test rate limit error with cached content available."""
        error = AIRateLimitError(
            cached_content_available=True,
            correlation_id="rate-limit-123"
        )

        assert error.cached_content_available is True
        assert error.correlation_id == "rate-limit-123"


class TestAINetworkError:
    """Test the AINetworkError class."""

    def test_network_error_defaults(self):
        """Test network error with default values."""
        error = AINetworkError()

        assert error.error_code == "AI_NETWORK_ERROR"
        assert error.retryable is True
        assert "network" in error.message.lower()

    def test_network_error_with_retry_after(self):
        """Test network error with custom retry_after."""
        error = AINetworkError(retry_after=45)

        assert error.retry_after == 45
        assert error.retryable is True

    def test_network_error_with_original_exception(self):
        """Test network error with original exception."""
        original = ConnectionError("Connection refused")
        error = AINetworkError(
            original_exception=original,
            correlation_id="network-123"
        )

        assert error.original_exception is original
        assert error.correlation_id == "network-123"


class TestAIServiceUnavailableError:
    """Test the AIServiceUnavailableError class."""

    def test_service_unavailable_defaults(self):
        """Test service unavailable error with defaults."""
        error = AIServiceUnavailableError()

        assert error.error_code == "AI_SERVICE_UNAVAILABLE"
        assert error.retryable is True
        assert error.retry_after == 30
        assert "unavailable" in error.message.lower()

    def test_service_unavailable_with_cache(self):
        """Test service unavailable with cached content."""
        error = AIServiceUnavailableError(
            cached_content_available=True,
            retry_after=60
        )

        assert error.cached_content_available is True
        assert error.retry_after == 60


class TestAIInvalidRequestError:
    """Test the AIInvalidRequestError class."""

    def test_invalid_request_defaults(self):
        """Test invalid request error defaults."""
        error = AIInvalidRequestError()

        assert error.error_code == "AI_INVALID_REQUEST"
        assert error.retryable is False
        assert error.retry_after is None
        assert "invalid request" in error.message.lower()

    def test_invalid_request_not_retryable(self):
        """Test that invalid request errors are never retryable."""
        error = AIInvalidRequestError(
            message="Bad parameters",
            correlation_id="invalid-123"
        )

        assert error.retryable is False
        assert error.retry_after is None
        assert error.message == "Bad parameters"


class TestAIResponseParsingError:
    """Test the AIResponseParsingError class."""

    def test_parsing_error_defaults(self):
        """Test parsing error with defaults."""
        error = AIResponseParsingError()

        assert error.error_code == "AI_RESPONSE_PARSING_ERROR"
        assert error.retryable is True
        assert "parse" in error.message.lower()

    def test_parsing_error_not_retryable(self):
        """Test parsing error marked as not retryable."""
        error = AIResponseParsingError(retryable=False)

        assert error.retryable is False

    def test_parsing_error_with_cached_content(self):
        """Test parsing error with cached fallback."""
        error = AIResponseParsingError(
            cached_content_available=True,
            correlation_id="parse-123"
        )

        assert error.cached_content_available is True


class TestAICacheError:
    """Test the AICacheError class."""

    def test_cache_error_defaults(self):
        """Test cache error defaults."""
        error = AICacheError()

        assert error.error_code == "AI_CACHE_ERROR"
        assert error.retryable is False
        assert error.retry_after is None
        assert "cache" in error.message.lower()

    def test_cache_error_not_critical(self):
        """Test that cache errors are not retryable."""
        error = AICacheError(
            message="Redis connection failed",
            correlation_id="cache-123"
        )

        assert error.retryable is False
        assert error.message == "Redis connection failed"


class TestErrorInteroperability:
    """Test error classes working together."""

    def test_all_errors_inherit_from_base(self):
        """Test that all error classes inherit from AIServiceError."""
        errors = [
            AIRateLimitError(),
            AINetworkError(),
            AIServiceUnavailableError(),
            AIInvalidRequestError(),
            AIResponseParsingError(),
            AICacheError()
        ]

        for error in errors:
            assert isinstance(error, AIServiceError)
            assert isinstance(error, Exception)

    def test_error_codes_are_unique(self):
        """Test that all error codes are unique."""
        errors = [
            AIRateLimitError(),
            AINetworkError(),
            AIServiceUnavailableError(),
            AIInvalidRequestError(),
            AIResponseParsingError(),
            AICacheError()
        ]

        error_codes = [error.error_code for error in errors]
        assert len(error_codes) == len(set(error_codes))

    def test_retryable_errors_have_consistent_behavior(self):
        """Test that retryable errors behave consistently."""
        retryable_errors = [
            AIRateLimitError(),
            AINetworkError(),
            AIServiceUnavailableError(),
            AIResponseParsingError()
        ]

        for error in retryable_errors:
            assert error.retryable is True

    def test_non_retryable_errors(self):
        """Test that non-retryable errors are marked correctly."""
        non_retryable_errors = [
            AIInvalidRequestError(),
            AICacheError()
        ]

        for error in non_retryable_errors:
            assert error.retryable is False
            assert error.retry_after is None

    def test_timestamp_format(self):
        """Test that timestamps are in ISO format."""
        error = AIServiceError(
            message="Test",
            error_code="TEST"
        )

        # Should be able to parse the timestamp
        timestamp = datetime.fromisoformat(error.timestamp)
        assert isinstance(timestamp, datetime)
