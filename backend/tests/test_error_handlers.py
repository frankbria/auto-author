"""
Unit Tests for Error Handling Utilities
========================================

Tests for the error handling utility functions used in question endpoints.
"""

import pytest
from fastapi import HTTPException, status
from app.utils.error_handlers import (
    handle_book_not_found,
    handle_unauthorized_access,
    handle_validation_error,
    handle_question_generation_error,
    handle_question_not_found,
    handle_response_save_error,
    handle_rating_save_error,
    handle_generic_error,
    generate_request_id,
)
from app.schemas.errors import ErrorCode
from app.services.ai_errors import (
    AIServiceError,
    AIRateLimitError,
    AINetworkError,
    AIInvalidRequestError,
)


class TestRequestIdGeneration:
    """Tests for request ID generation"""

    def test_generate_request_id_format(self):
        """Test that request ID has correct format"""
        request_id = generate_request_id()
        assert request_id.startswith("req_")
        assert len(request_id) == 16  # req_ + 12 hex characters

    def test_generate_request_id_uniqueness(self):
        """Test that consecutive request IDs are unique"""
        id1 = generate_request_id()
        id2 = generate_request_id()
        assert id1 != id2


class TestBookNotFoundHandler:
    """Tests for handle_book_not_found"""

    def test_creates_404_exception(self):
        """Test that handler creates 404 HTTPException"""
        book_id = "test-book-123"
        with pytest.raises(HTTPException) as exc_info:
            raise handle_book_not_found(book_id)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    def test_includes_error_code(self):
        """Test that error response includes BOOK_NOT_FOUND code"""
        book_id = "test-book-123"
        with pytest.raises(HTTPException) as exc_info:
            raise handle_book_not_found(book_id)

        error_detail = exc_info.value.detail
        assert error_detail["error_code"] == ErrorCode.BOOK_NOT_FOUND.value

    def test_includes_book_id_in_details(self):
        """Test that error response includes book_id in details"""
        book_id = "test-book-123"
        with pytest.raises(HTTPException) as exc_info:
            raise handle_book_not_found(book_id)

        error_detail = exc_info.value.detail
        assert len(error_detail["details"]) > 0
        assert error_detail["details"][0]["value"] == book_id

    def test_uses_provided_request_id(self):
        """Test that handler uses provided request_id"""
        book_id = "test-book-123"
        request_id = "custom-req-id"
        with pytest.raises(HTTPException) as exc_info:
            raise handle_book_not_found(book_id, request_id)

        error_detail = exc_info.value.detail
        assert error_detail["request_id"] == request_id


class TestUnauthorizedAccessHandler:
    """Tests for handle_unauthorized_access"""

    def test_creates_403_exception(self):
        """Test that handler creates 403 HTTPException"""
        with pytest.raises(HTTPException) as exc_info:
            raise handle_unauthorized_access(
                resource_type="book",
                resource_id="book-123",
                user_id="user-456",
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    def test_includes_error_code(self):
        """Test that error response includes FORBIDDEN_OPERATION code"""
        with pytest.raises(HTTPException) as exc_info:
            raise handle_unauthorized_access(
                resource_type="book",
                resource_id="book-123",
                user_id="user-456",
            )

        error_detail = exc_info.value.detail
        assert error_detail["error_code"] == ErrorCode.FORBIDDEN_OPERATION.value

    def test_includes_resource_info_in_message(self):
        """Test that error message includes resource type"""
        resource_type = "chapter"
        with pytest.raises(HTTPException) as exc_info:
            raise handle_unauthorized_access(
                resource_type=resource_type,
                resource_id="chapter-123",
                user_id="user-456",
            )

        error_detail = exc_info.value.detail
        assert resource_type in error_detail["error"]


class TestValidationErrorHandler:
    """Tests for handle_validation_error"""

    def test_creates_422_exception(self):
        """Test that handler creates 422 HTTPException"""
        with pytest.raises(HTTPException) as exc_info:
            raise handle_validation_error(
                field="count",
                message="Must be between 1 and 50",
                value=100,
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_includes_field_in_details(self):
        """Test that error response includes field name"""
        field = "rating"
        with pytest.raises(HTTPException) as exc_info:
            raise handle_validation_error(
                field=field,
                message="Must be between 1 and 5",
                value=10,
            )

        error_detail = exc_info.value.detail
        assert error_detail["details"][0]["field"] == field

    def test_includes_invalid_value(self):
        """Test that error response includes the invalid value"""
        invalid_value = 100
        with pytest.raises(HTTPException) as exc_info:
            raise handle_validation_error(
                field="count",
                message="Must be between 1 and 50",
                value=invalid_value,
            )

        error_detail = exc_info.value.detail
        assert error_detail["details"][0]["value"] == invalid_value


class TestQuestionGenerationErrorHandler:
    """Tests for handle_question_generation_error"""

    def test_handles_ai_service_error_with_retry(self):
        """Test handling retryable AI service errors"""
        ai_error = AIRateLimitError(retry_after=60)
        with pytest.raises(HTTPException) as exc_info:
            raise handle_question_generation_error(
                error=ai_error,
                book_id="book-123",
                chapter_id="chapter-456",
            )

        assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    def test_handles_ai_service_error_non_retryable(self):
        """Test handling non-retryable AI service errors"""
        ai_error = AIInvalidRequestError(message="Invalid prompt")
        with pytest.raises(HTTPException) as exc_info:
            raise handle_question_generation_error(
                error=ai_error,
                book_id="book-123",
                chapter_id="chapter-456",
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_handles_generic_exception(self):
        """Test handling generic exceptions"""
        generic_error = Exception("Something went wrong")
        with pytest.raises(HTTPException) as exc_info:
            raise handle_question_generation_error(
                error=generic_error,
                book_id="book-123",
                chapter_id="chapter-456",
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        error_detail = exc_info.value.detail
        assert error_detail["error_code"] == ErrorCode.QUESTION_GENERATION_FAILED.value

    def test_includes_context_in_details(self):
        """Test that error includes book_id and chapter_id in context"""
        book_id = "book-123"
        chapter_id = "chapter-456"
        with pytest.raises(HTTPException) as exc_info:
            raise handle_question_generation_error(
                error=Exception("Test error"),
                book_id=book_id,
                chapter_id=chapter_id,
            )

        error_detail = exc_info.value.detail
        details = error_detail["details"]
        book_detail = next((d for d in details if d.get("field") == "book_id"), None)
        chapter_detail = next((d for d in details if d.get("field") == "chapter_id"), None)

        assert book_detail is not None
        assert chapter_detail is not None
        assert book_detail["value"] == book_id
        assert chapter_detail["value"] == chapter_id


class TestQuestionNotFoundHandler:
    """Tests for handle_question_not_found"""

    def test_creates_404_exception(self):
        """Test that handler creates 404 HTTPException"""
        with pytest.raises(HTTPException) as exc_info:
            raise handle_question_not_found("question-123")

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    def test_includes_question_id(self):
        """Test that error includes question_id"""
        question_id = "question-123"
        with pytest.raises(HTTPException) as exc_info:
            raise handle_question_not_found(question_id)

        error_detail = exc_info.value.detail
        assert error_detail["details"][0]["value"] == question_id


class TestResponseSaveErrorHandler:
    """Tests for handle_response_save_error"""

    def test_handles_value_error_as_validation(self):
        """Test that ValueError is treated as validation error"""
        with pytest.raises(HTTPException) as exc_info:
            raise handle_response_save_error(
                error=ValueError("Response text is required"),
                question_id="question-123",
                user_id="user-456",
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_handles_generic_error(self):
        """Test handling generic errors"""
        with pytest.raises(HTTPException) as exc_info:
            raise handle_response_save_error(
                error=Exception("Database error"),
                question_id="question-123",
                user_id="user-456",
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        error_detail = exc_info.value.detail
        assert error_detail["error_code"] == ErrorCode.RESPONSE_SAVE_FAILED.value


class TestRatingSaveErrorHandler:
    """Tests for handle_rating_save_error"""

    def test_handles_value_error_as_validation(self):
        """Test that ValueError is treated as validation error"""
        with pytest.raises(HTTPException) as exc_info:
            raise handle_rating_save_error(
                error=ValueError("Invalid rating value"),
                question_id="question-123",
                user_id="user-456",
                rating_value=10,
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_includes_rating_value(self):
        """Test that error includes the invalid rating value"""
        rating_value = 10
        with pytest.raises(HTTPException) as exc_info:
            raise handle_rating_save_error(
                error=ValueError("Invalid rating"),
                question_id="question-123",
                user_id="user-456",
                rating_value=rating_value,
            )

        error_detail = exc_info.value.detail
        # Check if rating value is in the details
        assert error_detail["details"][0]["value"] == rating_value


class TestGenericErrorHandler:
    """Tests for handle_generic_error"""

    def test_creates_500_exception(self):
        """Test that handler creates 500 HTTPException"""
        with pytest.raises(HTTPException) as exc_info:
            raise handle_generic_error(
                error=Exception("Something went wrong"),
                operation="test operation",
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_includes_operation_in_message(self):
        """Test that error message includes operation description"""
        operation = "retrieving user data"
        with pytest.raises(HTTPException) as exc_info:
            raise handle_generic_error(
                error=Exception("Test error"),
                operation=operation,
            )

        error_detail = exc_info.value.detail
        assert operation in error_detail["error"]

    def test_includes_context_in_details(self):
        """Test that error includes context information"""
        context = {
            "book_id": "book-123",
            "chapter_id": "chapter-456",
        }
        with pytest.raises(HTTPException) as exc_info:
            raise handle_generic_error(
                error=Exception("Test error"),
                operation="test operation",
                context=context,
            )

        error_detail = exc_info.value.detail
        details = error_detail["details"]

        # Check that context items are in details
        book_detail = next((d for d in details if d.get("field") == "book_id"), None)
        chapter_detail = next((d for d in details if d.get("field") == "chapter_id"), None)

        assert book_detail is not None
        assert chapter_detail is not None
        assert book_detail["value"] == "book-123"
        assert chapter_detail["value"] == "chapter-456"


class TestErrorResponseStructure:
    """Tests for error response structure consistency"""

    def test_all_errors_include_timestamp(self):
        """Test that all error responses include timestamp"""
        handlers = [
            lambda: handle_book_not_found("book-123"),
            lambda: handle_unauthorized_access("book", "book-123", "user-456"),
            lambda: handle_validation_error("field", "message"),
            lambda: handle_question_not_found("question-123"),
        ]

        for handler in handlers:
            with pytest.raises(HTTPException) as exc_info:
                raise handler()

            error_detail = exc_info.value.detail
            assert "timestamp" in error_detail
            assert error_detail["timestamp"] is not None

    def test_all_errors_include_request_id(self):
        """Test that all error responses include request_id"""
        handlers = [
            lambda: handle_book_not_found("book-123", "req-123"),
            lambda: handle_unauthorized_access("book", "book-123", "user-456", request_id="req-123"),
            lambda: handle_validation_error("field", "message", request_id="req-123"),
        ]

        for handler in handlers:
            with pytest.raises(HTTPException) as exc_info:
                raise handler()

            error_detail = exc_info.value.detail
            assert "request_id" in error_detail
            assert error_detail["request_id"] == "req-123"

    def test_all_errors_include_error_code(self):
        """Test that all error responses include error_code"""
        handlers = [
            lambda: handle_book_not_found("book-123"),
            lambda: handle_unauthorized_access("book", "book-123", "user-456"),
            lambda: handle_validation_error("field", "message"),
            lambda: handle_question_not_found("question-123"),
        ]

        for handler in handlers:
            with pytest.raises(HTTPException) as exc_info:
                raise handler()

            error_detail = exc_info.value.detail
            assert "error_code" in error_detail
            assert error_detail["error_code"] in [code.value for code in ErrorCode]
