"""
Tests for API AI Error Responses
=================================

Tests that API endpoints properly handle and return structured AI service errors.
"""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi import status
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.security import get_current_user_from_session
from app.services.ai_errors import (
    AIRateLimitError,
    AINetworkError,
    AIServiceUnavailableError,
    AIInvalidRequestError,
    AIServiceError
)


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return {
        "auth_id": "test-user-123",
        "email": "test@example.com",
        "role": "user"
    }


@pytest.fixture
async def client(mock_user):
    """Create async HTTP client for testing with session auth bypass."""
    # Override the session-based authentication dependency
    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user_from_session] = override_get_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={"better-auth.session_token": "test-session-token"}
    ) as ac:
        yield ac

    # Clean up dependency overrides after test
    app.dependency_overrides.clear()


@pytest.fixture
def mock_book():
    """Mock book data."""
    return {
        "_id": "book123",
        "owner_id": "test-user-123",
        "title": "Test Book",
        "summary": "This is a test book summary with sufficient content for testing.",
        "genre": "Non-fiction",
        "target_audience": "General readers",
        "question_responses": {
            "responses": [
                {"question": "What is the main topic?", "answer": "Testing"}
            ]
        }
    }


class TestGenerateClarifyingQuestionsErrors:
    """Test error handling in generate clarifying questions endpoint."""

    @pytest.mark.asyncio
    async def test_rate_limit_error_returns_429(self, client, mock_user, mock_book):
        """Test that rate limit errors return 429 status code."""
        with patch('app.api.endpoints.books.get_book_by_id', return_value=mock_book):
            with patch('app.services.ai_service.ai_service.generate_clarifying_questions') as mock_generate:
                mock_generate.side_effect = AIRateLimitError(
                    retry_after=60,
                    correlation_id="test-correlation-123"
                )

                response = await client.post(
                    "/api/v1/books/book123/generate-questions",
                    json={"num_questions": 4}
                )

                assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
                data = response.json()
                assert "detail" in data
                assert data["detail"]["error_code"] == "AI_RATE_LIMIT"
                assert data["detail"]["retry_after"] == 60
                assert data["detail"]["correlation_id"] == "test-correlation-123"

    @pytest.mark.asyncio
    async def test_network_error_returns_503(self, client, mock_user, mock_book):
        """Test that network errors return 503 status code."""
        with patch('app.api.endpoints.books.get_book_by_id', return_value=mock_book):
            with patch('app.services.ai_service.ai_service.generate_clarifying_questions') as mock_generate:
                mock_generate.side_effect = AINetworkError(
                    correlation_id="test-correlation-456"
                )

                response = await client.post(
                    "/api/v1/books/book123/generate-questions",
                    json={"num_questions": 4}
                )

                assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
                data = response.json()
                assert data["detail"]["error_code"] == "AI_NETWORK_ERROR"
                assert data["detail"]["retryable"] is True

    @pytest.mark.asyncio
    async def test_service_unavailable_returns_503(self, client, mock_user, mock_book):
        """Test that service unavailable errors return 503 status code."""
        with patch('app.api.endpoints.books.get_book_by_id', return_value=mock_book):
            with patch('app.services.ai_service.ai_service.generate_clarifying_questions') as mock_generate:
                mock_generate.side_effect = AIServiceUnavailableError(
                    retry_after=30,
                    correlation_id="test-correlation-789"
                )

                response = await client.post(
                    "/api/v1/books/book123/generate-questions",
                    json={"num_questions": 4}
                )

                assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
                data = response.json()
                assert data["detail"]["error_code"] == "AI_SERVICE_UNAVAILABLE"
                assert data["detail"]["retry_after"] == 30

    @pytest.mark.asyncio
    async def test_invalid_request_returns_400(self, client, mock_user, mock_book):
        """Test that invalid request errors return 400 status code."""
        with patch('app.api.endpoints.books.get_book_by_id', return_value=mock_book):
            with patch('app.services.ai_service.ai_service.generate_clarifying_questions') as mock_generate:
                mock_generate.side_effect = AIInvalidRequestError(
                    message="Invalid parameters",
                    correlation_id="test-correlation-abc"
                )

                response = await client.post(
                    "/api/v1/books/book123/generate-questions",
                    json={"num_questions": 4}
                )

                assert response.status_code == status.HTTP_400_BAD_REQUEST
                data = response.json()
                assert data["detail"]["error_code"] == "AI_INVALID_REQUEST"

    @pytest.mark.asyncio
    async def test_generic_ai_error_returns_500(self, client, mock_user, mock_book):
        """Test that generic AI errors return 500 status code."""
        with patch('app.api.endpoints.books.get_book_by_id', return_value=mock_book):
            with patch('app.services.ai_service.ai_service.generate_clarifying_questions') as mock_generate:
                mock_generate.side_effect = AIServiceError(
                    message="Unexpected error",
                    error_code="AI_UNEXPECTED_ERROR",
                    correlation_id="test-correlation-xyz"
                )

                response = await client.post(
                    "/api/v1/books/book123/generate-questions",
                    json={"num_questions": 4}
                )

                assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
                data = response.json()
                assert data["detail"]["error_code"] == "AI_UNEXPECTED_ERROR"


class TestGenerateTOCErrors:
    """Test error handling in generate TOC endpoint."""

    @pytest.mark.asyncio
    async def test_toc_rate_limit_error_returns_429(self, client, mock_user, mock_book):
        """Test that TOC generation rate limit errors return 429."""
        with patch('app.api.endpoints.books.get_book_by_id', return_value=mock_book):
            with patch('app.services.ai_service.ai_service.generate_toc_from_summary_and_responses') as mock_generate:
                mock_generate.side_effect = AIRateLimitError(
                    retry_after=90,
                    cached_content_available=True,
                    correlation_id="toc-correlation-123"
                )

                response = await client.post("/api/v1/books/book123/generate-toc")

                assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
                data = response.json()
                assert data["detail"]["error_code"] == "AI_RATE_LIMIT"
                assert data["detail"]["retry_after"] == 90
                assert data["detail"]["cached_content_available"] is True

    @pytest.mark.asyncio
    async def test_toc_network_error_returns_503(self, client, mock_user, mock_book):
        """Test that TOC generation network errors return 503."""
        with patch('app.api.endpoints.books.get_book_by_id', return_value=mock_book):
            with patch('app.services.ai_service.ai_service.generate_toc_from_summary_and_responses') as mock_generate:
                mock_generate.side_effect = AINetworkError(
                    correlation_id="toc-correlation-456"
                )

                response = await client.post("/api/v1/books/book123/generate-toc")

                assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
                data = response.json()
                assert data["detail"]["error_code"] == "AI_NETWORK_ERROR"

    @pytest.mark.asyncio
    async def test_toc_invalid_response_returns_500_retryable(self, client, mock_user, mock_book):
        """An unusable/poorly-formatted AI TOC surfaces as a retryable error (issue #48),
        not a silently-saved placeholder TOC."""
        with patch('app.api.endpoints.books.get_book_by_id', return_value=mock_book):
            with patch('app.services.ai_service.ai_service.generate_toc_from_summary_and_responses') as mock_generate:
                mock_generate.side_effect = AIServiceError(
                    message="The AI returned an unusable table of contents. Please try again.",
                    error_code="AI_INVALID_RESPONSE",
                    retryable=True,
                    correlation_id="toc-invalid-1",
                )

                response = await client.post("/api/v1/books/book123/generate-toc")

                assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
                data = response.json()
                assert data["detail"]["error_code"] == "AI_INVALID_RESPONSE"
                assert data["detail"]["retryable"] is True

    @pytest.mark.asyncio
    async def test_toc_service_unavailable_returns_503(self, client, mock_user, mock_book):
        """Test that TOC generation service unavailable errors return 503."""
        with patch('app.api.endpoints.books.get_book_by_id', return_value=mock_book):
            with patch('app.services.ai_service.ai_service.generate_toc_from_summary_and_responses') as mock_generate:
                mock_generate.side_effect = AIServiceUnavailableError(
                    retry_after=45,
                    correlation_id="toc-correlation-789"
                )

                response = await client.post("/api/v1/books/book123/generate-toc")

                assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
                data = response.json()
                assert data["detail"]["error_code"] == "AI_SERVICE_UNAVAILABLE"
                assert data["detail"]["retry_after"] == 45


class TestAnalyzeSummaryErrors:
    """Test error handling in analyze summary endpoint (issue #48).

    Timeouts surface from ai_service as AINetworkError, so a graceful
    timeout response is the same path as any network error: 503 + retry info.
    """

    @pytest.mark.asyncio
    async def test_analyze_network_error_returns_503(self, client, mock_user, mock_book):
        """Timeouts/network errors during summary analysis return 503, not 500."""
        with patch('app.api.endpoints.books.get_book_by_id', return_value=mock_book):
            with patch('app.services.ai_service.ai_service.analyze_summary_for_toc') as mock_analyze:
                mock_analyze.side_effect = AINetworkError(
                    correlation_id="analyze-correlation-456"
                )

                response = await client.post("/api/v1/books/book123/analyze-summary")

                assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
                data = response.json()
                assert data["detail"]["error_code"] == "AI_NETWORK_ERROR"
                assert data["detail"]["retryable"] is True
                assert data["detail"]["correlation_id"] == "analyze-correlation-456"

    @pytest.mark.asyncio
    async def test_analyze_rate_limit_error_returns_429(self, client, mock_user, mock_book):
        """Rate limit errors during summary analysis return 429 with retry info."""
        with patch('app.api.endpoints.books.get_book_by_id', return_value=mock_book):
            with patch('app.services.ai_service.ai_service.analyze_summary_for_toc') as mock_analyze:
                mock_analyze.side_effect = AIRateLimitError(
                    retry_after=60,
                    correlation_id="analyze-correlation-123"
                )

                response = await client.post("/api/v1/books/book123/analyze-summary")

                assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
                data = response.json()
                assert data["detail"]["error_code"] == "AI_RATE_LIMIT"
                assert data["detail"]["retry_after"] == 60

    @pytest.mark.asyncio
    async def test_analyze_service_unavailable_returns_503(self, client, mock_user, mock_book):
        """Service-unavailable errors during summary analysis return 503."""
        with patch('app.api.endpoints.books.get_book_by_id', return_value=mock_book):
            with patch('app.services.ai_service.ai_service.analyze_summary_for_toc') as mock_analyze:
                mock_analyze.side_effect = AIServiceUnavailableError(
                    retry_after=30,
                    correlation_id="analyze-correlation-789"
                )

                response = await client.post("/api/v1/books/book123/analyze-summary")

                assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
                data = response.json()
                assert data["detail"]["error_code"] == "AI_SERVICE_UNAVAILABLE"
                assert data["detail"]["retry_after"] == 30

    @pytest.mark.asyncio
    async def test_analyze_error_dict_returns_503_and_is_not_persisted(
        self, client, mock_user, mock_book
    ):
        """A swallowed AI error (e.g. invalid OpenAI key) returns an error dict, not
        an exception. The endpoint must surface it as a retryable 503 and must NOT
        persist it — a stored failed analysis permanently poisons the readiness
        check (has_analysis=true, meets_minimum_requirements=false)."""
        error_analysis = {
            "is_ready_for_toc": False,
            "confidence_score": 0.0,
            "analysis": "Error occurred during analysis",
            "suggestions": ["Please try again later or contact support"],
            "error": "AI_UNEXPECTED_ERROR: 401 invalid_api_key",
        }
        with patch('app.api.endpoints.books.get_book_by_id', return_value=mock_book):
            with patch(
                'app.services.ai_service.ai_service.analyze_summary_for_toc',
                new=AsyncMock(return_value=error_analysis),
            ):
                with patch(
                    'app.api.endpoints.books.update_book', new=AsyncMock()
                ) as mock_update:
                    response = await client.post(
                        "/api/v1/books/book123/analyze-summary"
                    )

                    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
                    data = response.json()
                    assert data["detail"]["error_code"] == "AI_ANALYSIS_FAILED"
                    assert data["detail"]["retryable"] is True
                    # The poisoned analysis must never be written to the book.
                    mock_update.assert_not_called()


class TestErrorResponseStructure:
    """Test the structure of error responses."""

    @pytest.mark.asyncio
    async def test_error_response_includes_all_fields(self, client, mock_user, mock_book):
        """Test that error responses include all expected fields."""
        with patch('app.api.endpoints.books.get_book_by_id', return_value=mock_book):
            with patch('app.services.ai_service.ai_service.generate_clarifying_questions') as mock_generate:
                mock_generate.side_effect = AIRateLimitError(
                    message="Custom rate limit message",
                    retry_after=120,
                    cached_content_available=False,
                    correlation_id="detailed-correlation-123"
                )

                response = await client.post(
                    "/api/v1/books/book123/generate-questions",
                    json={"num_questions": 4}
                )

                assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
                data = response.json()

                # Check all expected fields are present
                assert "detail" in data
                detail = data["detail"]
                assert "message" in detail
                assert "error_code" in detail
                assert "retry_after" in detail
                assert "cached_content_available" in detail
                assert "correlation_id" in detail

                # Check values
                assert detail["message"] == "Custom rate limit message"
                assert detail["error_code"] == "AI_RATE_LIMIT"
                assert detail["retry_after"] == 120
                assert detail["cached_content_available"] is False
                assert detail["correlation_id"] == "detailed-correlation-123"

    @pytest.mark.asyncio
    async def test_correlation_id_tracking(self, client, mock_user, mock_book):
        """Test that correlation IDs are preserved in error responses."""
        test_correlation_id = "unique-test-id-12345"

        with patch('app.api.endpoints.books.get_book_by_id', return_value=mock_book):
            with patch('app.services.ai_service.ai_service.generate_clarifying_questions') as mock_generate:
                mock_generate.side_effect = AIServiceError(
                    message="Test error",
                    error_code="TEST_ERROR",
                    correlation_id=test_correlation_id
                )

                response = await client.post(
                    "/api/v1/books/book123/generate-questions",
                    json={"num_questions": 4}
                )

                data = response.json()
                assert data["detail"]["correlation_id"] == test_correlation_id


class TestSuccessfulResponses:
    """Test successful responses to ensure error handling doesn't break normal flow."""

    @pytest.mark.asyncio
    async def test_successful_question_generation(self, client, mock_user, mock_book):
        """Test successful question generation still works."""
        with patch('app.api.endpoints.books.get_book_by_id', return_value=mock_book):
            with patch('app.api.endpoints.books.update_book', return_value=None):
                with patch('app.services.ai_service.ai_service.generate_clarifying_questions') as mock_generate:
                    mock_generate.return_value = [
                        "Question 1?",
                        "Question 2?",
                        "Question 3?"
                    ]

                    response = await client.post(
                        "/api/v1/books/book123/generate-questions",
                        json={"num_questions": 3}
                    )

                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()
                    assert "questions" in data
                    assert len(data["questions"]) == 3
                    assert "correlation_id" not in data  # No error
