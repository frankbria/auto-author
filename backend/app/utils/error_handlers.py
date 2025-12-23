"""
Error Handling Utilities
=========================

This module provides utility functions for handling errors in question-related
endpoints with consistent formatting and detailed debugging information.
"""

from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status
from app.schemas.errors import ErrorCode, ErrorDetail, ErrorResponse, create_error_response
from app.services.ai_errors import AIServiceError
import logging
import uuid

logger = logging.getLogger(__name__)


def generate_request_id() -> str:
    """Generate a unique request ID for error tracking"""
    return f"req_{uuid.uuid4().hex[:12]}"


def handle_book_not_found(
    book_id: str,
    request_id: Optional[str] = None
) -> HTTPException:
    """
    Create HTTPException for book not found error.

    Args:
        book_id: The book ID that was not found
        request_id: Optional request correlation ID

    Returns:
        HTTPException with standardized error response
    """
    request_id = request_id or generate_request_id()

    error_response = create_error_response(
        error_code=ErrorCode.BOOK_NOT_FOUND,
        message="Book not found",
        status_code=status.HTTP_404_NOT_FOUND,
        details=[
            ErrorDetail(
                field="book_id",
                message=f"No book exists with ID: {book_id}",
                code=ErrorCode.BOOK_NOT_FOUND.value,
                value=book_id
            )
        ],
        request_id=request_id
    )

    logger.warning(f"Book not found: {book_id} [request_id={request_id}]")

    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=error_response.model_dump(mode='json')
    )


def handle_unauthorized_access(
    resource_type: str,
    resource_id: str,
    user_id: str,
    required_permission: str = "owner",
    request_id: Optional[str] = None
) -> HTTPException:
    """
    Create HTTPException for unauthorized access error.

    Args:
        resource_type: Type of resource (e.g., "book", "chapter")
        resource_id: ID of the resource
        user_id: ID of the user attempting access
        required_permission: Required permission level
        request_id: Optional request correlation ID

    Returns:
        HTTPException with standardized error response
    """
    request_id = request_id or generate_request_id()

    error_response = create_error_response(
        error_code=ErrorCode.FORBIDDEN_OPERATION,
        message=f"Not authorized to access this {resource_type}",
        status_code=status.HTTP_403_FORBIDDEN,
        details=[
            ErrorDetail(
                field=f"{resource_type}_id",
                message=f"You must be the {resource_type} {required_permission} to perform this operation",
                code=ErrorCode.UNAUTHORIZED_ACCESS.value,
                value=resource_id
            )
        ],
        request_id=request_id
    )

    logger.warning(
        f"Unauthorized access attempt: user={user_id}, "
        f"resource={resource_type}/{resource_id} [request_id={request_id}]"
    )

    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=error_response.model_dump(mode='json')
    )


def handle_validation_error(
    field: str,
    message: str,
    value: Any = None,
    additional_details: Optional[List[ErrorDetail]] = None,
    request_id: Optional[str] = None
) -> HTTPException:
    """
    Create HTTPException for validation error.

    Args:
        field: Field name that failed validation
        message: Validation error message
        value: The invalid value
        additional_details: Optional additional error details
        request_id: Optional request correlation ID

    Returns:
        HTTPException with standardized error response
    """
    request_id = request_id or generate_request_id()

    details = [
        ErrorDetail(
            field=field,
            message=message,
            code=ErrorCode.VALIDATION_FAILED.value,
            value=value
        )
    ]

    if additional_details:
        details.extend(additional_details)

    error_response = create_error_response(
        error_code=ErrorCode.VALIDATION_FAILED,
        message="Request validation failed",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details=details,
        request_id=request_id
    )

    logger.info(f"Validation error: field={field}, value={value} [request_id={request_id}]")

    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=error_response.model_dump(mode='json')
    )


def handle_question_generation_error(
    error: Exception,
    book_id: str,
    chapter_id: str,
    request_id: Optional[str] = None
) -> HTTPException:
    """
    Create HTTPException for question generation error.

    Args:
        error: The original exception
        book_id: Book ID
        chapter_id: Chapter ID
        request_id: Optional request correlation ID

    Returns:
        HTTPException with standardized error response
    """
    request_id = request_id or generate_request_id()

    # Handle AI service errors specially
    if isinstance(error, AIServiceError):
        error_response = create_error_response(
            error_code=ErrorCode.QUESTION_GENERATION_FAILED,
            message=f"Question generation failed: {error.message}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE if error.retryable else status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[
                ErrorDetail(
                    message=error.message,
                    code=error.error_code
                ),
                ErrorDetail(
                    field="retryable",
                    message=f"This error is {'retryable' if error.retryable else 'not retryable'}",
                    value=error.retryable
                )
            ],
            request_id=request_id
        )
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE if error.retryable else status.HTTP_500_INTERNAL_SERVER_ERROR
    else:
        error_response = create_error_response(
            error_code=ErrorCode.QUESTION_GENERATION_FAILED,
            message="Failed to generate questions for chapter",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[
                ErrorDetail(
                    field="book_id",
                    message=f"Error during question generation: {str(error)}",
                    value=book_id
                ),
                ErrorDetail(
                    field="chapter_id",
                    message="Chapter ID for failed operation",
                    value=chapter_id
                )
            ],
            request_id=request_id
        )
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    logger.error(
        f"Question generation failed: book={book_id}, chapter={chapter_id}, "
        f"error={str(error)} [request_id={request_id}]"
    )

    return HTTPException(
        status_code=status_code,
        detail=error_response.model_dump(mode='json')
    )


def handle_database_error(
    operation: str,
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> HTTPException:
    """
    Create HTTPException for database error.

    Args:
        operation: The database operation that failed
        error: The original exception
        context: Optional context information
        request_id: Optional request correlation ID

    Returns:
        HTTPException with standardized error response
    """
    request_id = request_id or generate_request_id()

    details = [
        ErrorDetail(
            message=f"Database operation failed: {operation}",
            code=ErrorCode.DATABASE_ERROR.value
        )
    ]

    if context:
        for key, value in context.items():
            details.append(
                ErrorDetail(
                    field=key,
                    message=f"Context: {key}",
                    value=value
                )
            )

    error_response = create_error_response(
        error_code=ErrorCode.DATABASE_ERROR,
        message=f"Database error during {operation}",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details=details,
        request_id=request_id
    )

    logger.error(
        f"Database error: operation={operation}, error={str(error)}, "
        f"context={context} [request_id={request_id}]"
    )

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=error_response.model_dump(mode='json')
    )


def handle_question_not_found(
    question_id: str,
    request_id: Optional[str] = None
) -> HTTPException:
    """
    Create HTTPException for question not found error.

    Args:
        question_id: The question ID that was not found
        request_id: Optional request correlation ID

    Returns:
        HTTPException with standardized error response
    """
    request_id = request_id or generate_request_id()

    error_response = create_error_response(
        error_code=ErrorCode.QUESTION_NOT_FOUND,
        message="Question not found",
        status_code=status.HTTP_404_NOT_FOUND,
        details=[
            ErrorDetail(
                field="question_id",
                message=f"No question exists with ID: {question_id}",
                code=ErrorCode.QUESTION_NOT_FOUND.value,
                value=question_id
            )
        ],
        request_id=request_id
    )

    logger.warning(f"Question not found: {question_id} [request_id={request_id}]")

    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=error_response.model_dump(mode='json')
    )


def handle_response_save_error(
    error: Exception,
    question_id: str,
    user_id: str,
    request_id: Optional[str] = None
) -> HTTPException:
    """
    Create HTTPException for response save error.

    Args:
        error: The original exception
        question_id: Question ID
        user_id: User ID
        request_id: Optional request correlation ID

    Returns:
        HTTPException with standardized error response
    """
    request_id = request_id or generate_request_id()

    # Check if it's a validation error from the service
    if isinstance(error, ValueError):
        return handle_validation_error(
            field="response_text",
            message=str(error),
            request_id=request_id
        )

    error_response = create_error_response(
        error_code=ErrorCode.RESPONSE_SAVE_FAILED,
        message="Failed to save question response",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details=[
            ErrorDetail(
                field="question_id",
                message=f"Error saving response: {str(error)}",
                value=question_id
            )
        ],
        request_id=request_id
    )

    logger.error(
        f"Response save failed: question={question_id}, user={user_id}, "
        f"error={str(error)} [request_id={request_id}]"
    )

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=error_response.model_dump(mode='json')
    )


def handle_rating_save_error(
    error: Exception,
    question_id: str,
    user_id: str,
    rating_value: Optional[int] = None,
    request_id: Optional[str] = None
) -> HTTPException:
    """
    Create HTTPException for rating save error.

    Args:
        error: The original exception
        question_id: Question ID
        user_id: User ID
        rating_value: The rating value that was attempted
        request_id: Optional request correlation ID

    Returns:
        HTTPException with standardized error response
    """
    request_id = request_id or generate_request_id()

    # Check if it's a validation error from the service
    if isinstance(error, ValueError):
        return handle_validation_error(
            field="rating",
            message=str(error),
            value=rating_value,
            request_id=request_id
        )

    error_response = create_error_response(
        error_code=ErrorCode.RATING_SAVE_FAILED,
        message="Failed to save question rating",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details=[
            ErrorDetail(
                field="question_id",
                message=f"Error saving rating: {str(error)}",
                value=question_id
            )
        ],
        request_id=request_id
    )

    logger.error(
        f"Rating save failed: question={question_id}, user={user_id}, "
        f"rating={rating_value}, error={str(error)} [request_id={request_id}]"
    )

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=error_response.model_dump(mode='json')
    )


def handle_generic_error(
    error: Exception,
    operation: str,
    context: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> HTTPException:
    """
    Create HTTPException for generic errors.

    Args:
        error: The original exception
        operation: Description of the operation that failed
        context: Optional context information
        request_id: Optional request correlation ID

    Returns:
        HTTPException with standardized error response
    """
    request_id = request_id or generate_request_id()

    details = [
        ErrorDetail(
            message=f"Operation failed: {str(error)}",
            code=ErrorCode.OPERATION_FAILED.value
        )
    ]

    if context:
        for key, value in context.items():
            details.append(
                ErrorDetail(
                    field=key,
                    message=f"Context: {key}",
                    value=value
                )
            )

    error_response = create_error_response(
        error_code=ErrorCode.OPERATION_FAILED,
        message=f"Error during {operation}",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details=details,
        request_id=request_id
    )

    logger.error(
        f"Generic error: operation={operation}, error={str(error)}, "
        f"context={context} [request_id={request_id}]"
    )

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=error_response.model_dump(mode='json')
    )
