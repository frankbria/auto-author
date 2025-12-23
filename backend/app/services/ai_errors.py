"""
AI Service Error Types
======================

This module defines custom exception classes for AI service errors,
providing structured error handling with retry capabilities and
fallback content support.
"""

from typing import Optional, Dict, Any
from datetime import datetime


class AIServiceError(Exception):
    """
    Base exception class for all AI service errors.

    Attributes:
        message: Human-readable error message
        error_code: Machine-readable error code
        retryable: Whether this error can be retried
        retry_after: Seconds to wait before retrying (None if not applicable)
        cached_content_available: Whether cached fallback content is available
        original_exception: The original exception that caused this error
        timestamp: When the error occurred
        correlation_id: Optional correlation ID for tracking
    """

    def __init__(
        self,
        message: str,
        error_code: str,
        retryable: bool = False,
        retry_after: Optional[int] = None,
        cached_content_available: bool = False,
        original_exception: Optional[Exception] = None,
        correlation_id: Optional[str] = None
    ):
        self.message = message
        self.error_code = error_code
        self.retryable = retryable
        self.retry_after = retry_after
        self.cached_content_available = cached_content_available
        self.original_exception = original_exception
        self.correlation_id = correlation_id
        self.timestamp = datetime.now().isoformat()

        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses."""
        return {
            "error": {
                "message": self.message,
                "error_code": self.error_code,
                "retryable": self.retryable,
                "retry_after": self.retry_after,
                "cached_content_available": self.cached_content_available,
                "timestamp": self.timestamp,
                "correlation_id": self.correlation_id
            }
        }

    def __str__(self) -> str:
        parts = [f"{self.error_code}: {self.message}"]
        if self.retry_after:
            parts.append(f"retry_after={self.retry_after}s")
        if self.correlation_id:
            parts.append(f"correlation_id={self.correlation_id}")
        return " | ".join(parts)


class AIRateLimitError(AIServiceError):
    """
    Raised when AI service rate limits are exceeded.

    This error is always retryable and includes information about
    when to retry the request.
    """

    def __init__(
        self,
        message: str = "AI service rate limit exceeded",
        retry_after: int = 60,
        cached_content_available: bool = False,
        original_exception: Optional[Exception] = None,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=message,
            error_code="AI_RATE_LIMIT",
            retryable=True,
            retry_after=retry_after,
            cached_content_available=cached_content_available,
            original_exception=original_exception,
            correlation_id=correlation_id
        )


class AINetworkError(AIServiceError):
    """
    Raised when network connectivity issues prevent AI service access.

    This error is retryable with exponential backoff.
    """

    def __init__(
        self,
        message: str = "Network error communicating with AI service",
        retry_after: Optional[int] = None,
        cached_content_available: bool = False,
        original_exception: Optional[Exception] = None,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=message,
            error_code="AI_NETWORK_ERROR",
            retryable=True,
            retry_after=retry_after,
            cached_content_available=cached_content_available,
            original_exception=original_exception,
            correlation_id=correlation_id
        )


class AIServiceUnavailableError(AIServiceError):
    """
    Raised when the AI service is temporarily unavailable.

    This typically indicates server-side issues and is retryable.
    """

    def __init__(
        self,
        message: str = "AI service temporarily unavailable",
        retry_after: int = 30,
        cached_content_available: bool = False,
        original_exception: Optional[Exception] = None,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=message,
            error_code="AI_SERVICE_UNAVAILABLE",
            retryable=True,
            retry_after=retry_after,
            cached_content_available=cached_content_available,
            original_exception=original_exception,
            correlation_id=correlation_id
        )


class AIInvalidRequestError(AIServiceError):
    """
    Raised when the request to the AI service is invalid.

    This error is not retryable as it indicates a problem with
    the request parameters or format.
    """

    def __init__(
        self,
        message: str = "Invalid request to AI service",
        cached_content_available: bool = False,
        original_exception: Optional[Exception] = None,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=message,
            error_code="AI_INVALID_REQUEST",
            retryable=False,
            retry_after=None,
            cached_content_available=cached_content_available,
            original_exception=original_exception,
            correlation_id=correlation_id
        )


class AIResponseParsingError(AIServiceError):
    """
    Raised when the AI service response cannot be parsed.

    This error may be retryable as it could be due to a temporary
    issue with the AI service's response format.
    """

    def __init__(
        self,
        message: str = "Failed to parse AI service response",
        retryable: bool = True,
        cached_content_available: bool = False,
        original_exception: Optional[Exception] = None,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=message,
            error_code="AI_RESPONSE_PARSING_ERROR",
            retryable=retryable,
            retry_after=None,
            cached_content_available=cached_content_available,
            original_exception=original_exception,
            correlation_id=correlation_id
        )


class AICacheError(AIServiceError):
    """
    Raised when cache operations fail.

    This error is not critical and should not prevent the main operation.
    It's logged but typically handled gracefully.
    """

    def __init__(
        self,
        message: str = "Cache operation failed",
        original_exception: Optional[Exception] = None,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=message,
            error_code="AI_CACHE_ERROR",
            retryable=False,
            retry_after=None,
            cached_content_available=False,
            original_exception=original_exception,
            correlation_id=correlation_id
        )
