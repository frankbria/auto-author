"""
Error Response Schemas
======================

This module defines standardized error response schemas for API endpoints,
providing consistent error formatting and detailed debugging information.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ErrorCode(str, Enum):
    """Standard error codes for API responses"""

    # Resource errors
    BOOK_NOT_FOUND = "BOOK_NOT_FOUND"
    CHAPTER_NOT_FOUND = "CHAPTER_NOT_FOUND"
    QUESTION_NOT_FOUND = "QUESTION_NOT_FOUND"
    RESPONSE_NOT_FOUND = "RESPONSE_NOT_FOUND"

    # Authorization errors
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    FORBIDDEN_OPERATION = "FORBIDDEN_OPERATION"

    # Validation errors
    INVALID_REQUEST_DATA = "INVALID_REQUEST_DATA"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    INVALID_PARAMETER = "INVALID_PARAMETER"

    # Question-specific errors
    QUESTION_GENERATION_FAILED = "QUESTION_GENERATION_FAILED"
    QUESTION_LIMIT_EXCEEDED = "QUESTION_LIMIT_EXCEEDED"
    INVALID_DIFFICULTY_LEVEL = "INVALID_DIFFICULTY_LEVEL"
    INVALID_QUESTION_TYPE = "INVALID_QUESTION_TYPE"

    # Response-specific errors
    RESPONSE_SAVE_FAILED = "RESPONSE_SAVE_FAILED"
    RESPONSE_TOO_SHORT = "RESPONSE_TOO_SHORT"
    RESPONSE_TOO_LONG = "RESPONSE_TOO_LONG"

    # Rating errors
    RATING_SAVE_FAILED = "RATING_SAVE_FAILED"
    INVALID_RATING_VALUE = "INVALID_RATING_VALUE"

    # Database errors
    DATABASE_ERROR = "DATABASE_ERROR"
    DATABASE_CONNECTION_FAILED = "DATABASE_CONNECTION_FAILED"

    # Rate limiting
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # General errors
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    OPERATION_FAILED = "OPERATION_FAILED"


class ErrorDetail(BaseModel):
    """Detailed error information for a single field or operation"""

    field: Optional[str] = Field(None, description="Field name if field-specific error")
    message: str = Field(..., description="Human-readable error message")
    code: Optional[str] = Field(None, description="Specific error code for this detail")
    value: Optional[Any] = Field(None, description="The invalid value that caused the error")


class ErrorResponse(BaseModel):
    """Standardized error response schema"""

    error: str = Field(..., description="Main error message")
    error_code: ErrorCode = Field(..., description="Machine-readable error code")
    status_code: int = Field(..., description="HTTP status code")
    details: Optional[List[ErrorDetail]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the error occurred")
    request_id: Optional[str] = Field(None, description="Request correlation ID for tracking")
    help_url: Optional[str] = Field(None, description="URL to documentation for this error")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Failed to generate questions for chapter",
                "error_code": "QUESTION_GENERATION_FAILED",
                "status_code": 500,
                "details": [
                    {
                        "field": "chapter_id",
                        "message": "Chapter does not exist in book",
                        "code": "CHAPTER_NOT_FOUND",
                        "value": "invalid-id-123"
                    }
                ],
                "timestamp": "2025-12-22T10:30:00Z",
                "request_id": "req_abc123",
                "help_url": "https://docs.autoauthor.app/errors/question-generation-failed"
            }
        }


class ValidationErrorResponse(ErrorResponse):
    """Error response for validation failures"""

    error_code: ErrorCode = ErrorCode.VALIDATION_FAILED

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Request validation failed",
                "error_code": "VALIDATION_FAILED",
                "status_code": 422,
                "details": [
                    {
                        "field": "count",
                        "message": "Value must be between 1 and 50",
                        "code": "INVALID_PARAMETER",
                        "value": 100
                    },
                    {
                        "field": "difficulty",
                        "message": "Must be one of: easy, medium, hard",
                        "code": "INVALID_DIFFICULTY_LEVEL",
                        "value": "extreme"
                    }
                ],
                "timestamp": "2025-12-22T10:30:00Z",
                "request_id": "req_abc123"
            }
        }


class AuthorizationErrorResponse(ErrorResponse):
    """Error response for authorization failures"""

    error_code: ErrorCode = ErrorCode.FORBIDDEN_OPERATION
    status_code: int = 403

    class Config:
        json_schema_extra = {
            "example": {
                "error": "You are not authorized to perform this operation",
                "error_code": "FORBIDDEN_OPERATION",
                "status_code": 403,
                "details": [
                    {
                        "message": "You must be the book owner to generate questions",
                        "code": "UNAUTHORIZED_ACCESS"
                    }
                ],
                "timestamp": "2025-12-22T10:30:00Z",
                "request_id": "req_abc123"
            }
        }


class ResourceNotFoundErrorResponse(ErrorResponse):
    """Error response for resource not found errors"""

    status_code: int = 404

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Resource not found",
                "error_code": "BOOK_NOT_FOUND",
                "status_code": 404,
                "details": [
                    {
                        "field": "book_id",
                        "message": "No book exists with this ID",
                        "value": "invalid-book-id"
                    }
                ],
                "timestamp": "2025-12-22T10:30:00Z",
                "request_id": "req_abc123"
            }
        }


class RateLimitErrorResponse(ErrorResponse):
    """Error response for rate limit exceeded"""

    error_code: ErrorCode = ErrorCode.RATE_LIMIT_EXCEEDED
    status_code: int = 429
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retrying")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Rate limit exceeded for question generation",
                "error_code": "RATE_LIMIT_EXCEEDED",
                "status_code": 429,
                "retry_after": 120,
                "details": [
                    {
                        "message": "Maximum 3 question generations per 2 minutes",
                        "code": "RATE_LIMIT_EXCEEDED"
                    }
                ],
                "timestamp": "2025-12-22T10:30:00Z",
                "request_id": "req_abc123"
            }
        }


def create_error_response(
    error_code: ErrorCode,
    message: str,
    status_code: int,
    details: Optional[List[ErrorDetail]] = None,
    request_id: Optional[str] = None,
    help_url: Optional[str] = None
) -> ErrorResponse:
    """
    Helper function to create standardized error responses.

    Args:
        error_code: The error code enum value
        message: Human-readable error message
        status_code: HTTP status code
        details: Optional list of detailed error information
        request_id: Optional request correlation ID
        help_url: Optional URL to error documentation

    Returns:
        ErrorResponse object
    """
    return ErrorResponse(
        error=message,
        error_code=error_code,
        status_code=status_code,
        details=details,
        request_id=request_id,
        help_url=help_url
    )
