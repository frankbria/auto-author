"""
Backend API Test Suite for User Story 4.2 (Interview-Style Prompts)

This test suite provides comprehensive coverage of the backend API endpoints
for the chapter questions functionality, including CRUD operations, validation,
error handling, and integration with the AI service.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Import the FastAPI app and dependencies
from app.main import app
from app.database import get_database
from app.schemas.book import (
    QuestionType,
    QuestionDifficulty,
    ResponseStatus,
    QuestionResponseCreate,
    QuestionRating,
    GenerateQuestionsRequest,
    GenerateQuestionsResponse
)
from app.services.ai_service import AIService
from app.services.question_generation_service import QuestionGenerationService

# Test fixtures
from tests.fixtures.question_generation_fixtures import (
    sample_questions,
    sample_question_responses,
    sample_question_ratings,
    book_with_questions,
    ai_question_response
)


class TestChapterQuestionsAPI:
    """Test suite for chapter questions API endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        return TestClient(app)

    @pytest.fixture
    async def async_client(self):
        """Create an async test client for the FastAPI app."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client

    @pytest.fixture
    def mock_database(self):
        """Mock database dependency."""
        mock_db = MagicMock()
        app.dependency_overrides[get_database] = lambda: mock_db
        yield mock_db
        app.dependency_overrides.clear()

    @pytest.fixture
    def mock_ai_service(self):
        """Mock AI service for testing."""
        mock_service = MagicMock(spec=AIService)
        mock_service.generate_chapter_questions = AsyncMock()
        return mock_service

    @pytest.fixture
    def sample_book_data(self):
        """Sample book data for testing."""
        return {
            "_id": "test-book-id",
            "title": "Test Book",
            "genre": "Educational",
            "target_audience": "Software developers",
            "description": "A test book for API testing",
            "status": "active",
            "created_at": datetime.now(timezone.utc)
        }

    @pytest.fixture
    def sample_chapter_data(self):
        """Sample chapter data for testing."""
        return {
            "_id": "test-chapter-id",
            "book_id": "test-book-id",
            "title": "Test Chapter",
            "description": "A test chapter for API testing",
            "order": 1,
            "status": "draft",
            "content": "This is test chapter content...",
            "questions_generated": False,
            "created_at": datetime.now(timezone.utc)
        }

    @pytest.mark.asyncio
    class TestQuestionGeneration:
        """Tests for question generation endpoints."""

        async def test_generate_chapter_questions_success(self, async_client, mock_database, mock_ai_service, sample_book_data, sample_chapter_data):
            """Test successful question generation for a chapter."""
            # Setup mocks
            mock_database.books.find_one.return_value = sample_book_data
            mock_database.chapters.find_one.return_value = sample_chapter_data
            mock_database.questions.insert_many.return_value = MagicMock(inserted_ids=[f"q{i}" for i in range(3)])
            
            mock_ai_service.generate_chapter_questions.return_value = ai_question_response

            with patch('app.routers.questions.get_ai_service', return_value=mock_ai_service):
                response = await async_client.post(
                    "/api/books/test-book-id/chapters/test-chapter-id/questions/generate",
                    json={
                        "question_types": [QuestionType.CONTENT.value, QuestionType.AUDIENCE.value],
                        "difficulty": QuestionDifficulty.MEDIUM.value,
                        "count": 3,
                        "focus_areas": "Learning objectives, target audience, practical examples"
                    }
                )

            assert response.status_code == 200
            data = response.json()
            
            assert "questions" in data
            assert len(data["questions"]) == 3
            assert "generation_metadata" in data
            assert data["generation_metadata"]["ai_model"] == "gpt-4"
            
            # Verify AI service was called correctly
            mock_ai_service.generate_chapter_questions.assert_called_once()

        async def test_generate_questions_invalid_chapter(self, async_client, mock_database):
            """Test question generation with invalid chapter ID."""
            mock_database.chapters.find_one.return_value = None

            response = await async_client.post(
                "/api/books/test-book-id/chapters/invalid-chapter/questions/generate",
                json={"count": 3}
            )

            assert response.status_code == 404
            assert "Chapter not found" in response.json()["detail"]

        async def test_generate_questions_validation_errors(self, async_client, mock_database, sample_chapter_data):
            """Test question generation with invalid request data."""
            mock_database.chapters.find_one.return_value = sample_chapter_data

            # Test invalid count
            response = await async_client.post(
                "/api/books/test-book-id/chapters/test-chapter-id/questions/generate",
                json={"count": 0}
            )
            assert response.status_code == 422

            # Test invalid difficulty
            response = await async_client.post(
                "/api/books/test-book-id/chapters/test-chapter-id/questions/generate",
                json={"difficulty": "invalid_difficulty"}
            )
            assert response.status_code == 422

        async def test_generate_questions_ai_service_error(self, async_client, mock_database, mock_ai_service, sample_chapter_data):
            """Test handling of AI service errors during generation."""
            mock_database.chapters.find_one.return_value = sample_chapter_data
            mock_ai_service.generate_chapter_questions.side_effect = Exception("AI service unavailable")

            with patch('app.routers.questions.get_ai_service', return_value=mock_ai_service):
                response = await async_client.post(
                    "/api/books/test-book-id/chapters/test-chapter-id/questions/generate",
                    json={"count": 3}
                )

            assert response.status_code == 500
            assert "Failed to generate questions" in response.json()["detail"]

        async def test_regenerate_chapter_questions(self, async_client, mock_database, mock_ai_service, sample_chapter_data):
            """Test regenerating questions for a chapter."""
            mock_database.chapters.find_one.return_value = sample_chapter_data
            mock_database.questions.find.return_value = sample_questions
            mock_database.questions.delete_many.return_value = MagicMock(deleted_count=3)
            mock_database.questions.insert_many.return_value = MagicMock(inserted_ids=[f"q{i}" for i in range(3)])
            
            mock_ai_service.generate_chapter_questions.return_value = ai_question_response

            with patch('app.routers.questions.get_ai_service', return_value=mock_ai_service):
                response = await async_client.post(
                    "/api/books/test-book-id/chapters/test-chapter-id/questions/regenerate",
                    json={
                        "keep_responses": True,
                        "focus_areas": "Updated focus areas"
                    }
                )

            assert response.status_code == 200
            data = response.json()
            
            assert "questions" in data
            assert data["regeneration_metadata"]["previous_count"] == 3
            assert data["regeneration_metadata"]["kept_responses"] == True

    @pytest.mark.asyncio
    class TestQuestionRetrieval:
        """Tests for question retrieval endpoints."""

        async def test_get_chapter_questions_success(self, async_client, mock_database, sample_chapter_data):
            """Test successful retrieval of chapter questions."""
            mock_database.chapters.find_one.return_value = sample_chapter_data
            mock_database.questions.find.return_value = sample_questions

            response = await async_client.get(
                "/api/books/test-book-id/chapters/test-chapter-id/questions"
            )

            assert response.status_code == 200
            data = response.json()
            
            assert "questions" in data
            assert len(data["questions"]) == len(sample_questions)
            assert data["questions"][0]["question_text"] == sample_questions[0]["question_text"]

        async def test_get_chapter_questions_with_filters(self, async_client, mock_database, sample_chapter_data):
            """Test retrieving questions with type and difficulty filters."""
            mock_database.chapters.find_one.return_value = sample_chapter_data
            filtered_questions = [q for q in sample_questions if q["question_type"] == QuestionType.CONTENT]
            mock_database.questions.find.return_value = filtered_questions

            response = await async_client.get(
                "/api/books/test-book-id/chapters/test-chapter-id/questions",
                params={
                    "question_type": QuestionType.CONTENT.value,
                    "difficulty": QuestionDifficulty.MEDIUM.value
                }
            )

            assert response.status_code == 200
            data = response.json()
            
            assert len(data["questions"]) == len(filtered_questions)
            for question in data["questions"]:
                assert question["question_type"] == QuestionType.CONTENT.value

        async def test_get_single_question(self, async_client, mock_database):
            """Test retrieving a single question by ID."""
            question_data = sample_questions[0]
            mock_database.questions.find_one.return_value = question_data

            response = await async_client.get(
                "/api/questions/test-question-id"
            )

            assert response.status_code == 200
            data = response.json()
            
            assert data["id"] == question_data["id"]
            assert data["question_text"] == question_data["question_text"]

        async def test_get_question_not_found(self, async_client, mock_database):
            """Test retrieving non-existent question."""
            mock_database.questions.find_one.return_value = None

            response = await async_client.get("/api/questions/nonexistent-id")

            assert response.status_code == 404
            assert "Question not found" in response.json()["detail"]

    @pytest.mark.asyncio
    class TestQuestionResponses:
        """Tests for question response endpoints."""

        async def test_save_question_response_success(self, async_client, mock_database):
            """Test successful saving of question response."""
            question_data = sample_questions[0]
            mock_database.questions.find_one.return_value = question_data
            mock_database.question_responses.replace_one.return_value = MagicMock(upserted_id="response-id")

            response_data = {
                "response_text": "This is a comprehensive answer to the question.",
                "status": ResponseStatus.COMPLETE.value,
                "notes": "Added some personal insights"
            }

            response = await async_client.post(
                "/api/questions/test-question-id/response",
                json=response_data
            )

            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] == True
            assert "response_id" in data

        async def test_save_response_validation_errors(self, async_client, mock_database):
            """Test response saving with validation errors."""
            question_data = sample_questions[0]
            mock_database.questions.find_one.return_value = question_data

            # Test empty response text for COMPLETE status
            response = await async_client.post(
                "/api/questions/test-question-id/response",
                json={
                    "response_text": "",
                    "status": ResponseStatus.COMPLETE.value
                }
            )
            assert response.status_code == 422

            # Test invalid status
            response = await async_client.post(
                "/api/questions/test-question-id/response",
                json={
                    "response_text": "Valid response",
                    "status": "invalid_status"
                }
            )
            assert response.status_code == 422

        async def test_get_question_response(self, async_client, mock_database):
            """Test retrieving question response."""
            response_data = sample_question_responses[0]
            mock_database.question_responses.find_one.return_value = response_data

            response = await async_client.get(
                "/api/questions/test-question-id/response"
            )

            assert response.status_code == 200
            data = response.json()
            
            assert data["has_response"] == True
            assert data["response"]["response_text"] == response_data["response_text"]
            assert data["response"]["status"] == response_data["status"]

        async def test_get_response_not_found(self, async_client, mock_database):
            """Test retrieving non-existent response."""
            mock_database.question_responses.find_one.return_value = None

            response = await async_client.get(
                "/api/questions/test-question-id/response"
            )

            assert response.status_code == 200
            data = response.json()
            
            assert data["has_response"] == False
            assert data["response"] is None

        async def test_update_response_status(self, async_client, mock_database):
            """Test updating response status."""
            response_data = sample_question_responses[0]
            mock_database.question_responses.find_one.return_value = response_data
            mock_database.question_responses.update_one.return_value = MagicMock(modified_count=1)

            response = await async_client.patch(
                "/api/questions/test-question-id/response/status",
                json={"status": ResponseStatus.COMPLETE.value}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True

    @pytest.mark.asyncio
    class TestQuestionRatings:
        """Tests for question rating endpoints."""

        async def test_rate_question_success(self, async_client, mock_database):
            """Test successful question rating."""
            question_data = sample_questions[0]
            mock_database.questions.find_one.return_value = question_data
            mock_database.question_ratings.replace_one.return_value = MagicMock(upserted_id="rating-id")

            response = await async_client.post(
                "/api/questions/test-question-id/rate",
                json={
                    "rating": 4,
                    "feedback": "Very helpful question, could use more examples"
                }
            )

            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] == True
            assert "rating_id" in data

        async def test_rate_question_validation(self, async_client, mock_database):
            """Test question rating validation."""
            question_data = sample_questions[0]
            mock_database.questions.find_one.return_value = question_data

            # Test invalid rating value
            response = await async_client.post(
                "/api/questions/test-question-id/rate",
                json={"rating": 6}  # Rating should be 1-5
            )
            assert response.status_code == 422

            # Test negative rating
            response = await async_client.post(
                "/api/questions/test-question-id/rate",
                json={"rating": 0}
            )
            assert response.status_code == 422

        async def test_get_question_ratings(self, async_client, mock_database):
            """Test retrieving question ratings."""
            ratings_data = [
                {
                    "question_id": "test-question-id",
                    "rating": 4,
                    "feedback": "Good question",
                    "created_at": datetime.now(timezone.utc)
                }
            ]
            mock_database.question_ratings.find.return_value = ratings_data

            response = await async_client.get(
                "/api/questions/test-question-id/ratings"
            )

            assert response.status_code == 200
            data = response.json()
            
            assert "ratings" in data
            assert len(data["ratings"]) == 1
            assert data["ratings"][0]["rating"] == 4

    @pytest.mark.asyncio
    class TestQuestionProgress:
        """Tests for question progress endpoints."""

        async def test_get_chapter_progress(self, async_client, mock_database, sample_chapter_data):
            """Test retrieving chapter question progress."""
            mock_database.chapters.find_one.return_value = sample_chapter_data
            mock_database.questions.count_documents.return_value = 5
            mock_database.question_responses.count_documents.return_value = 3

            response = await async_client.get(
                "/api/books/test-book-id/chapters/test-chapter-id/questions/progress"
            )

            assert response.status_code == 200
            data = response.json()
            
            assert data["total_questions"] == 5
            assert data["answered_questions"] == 3
            assert data["completion_percentage"] == 60

        async def test_get_detailed_progress(self, async_client, mock_database, sample_chapter_data):
            """Test retrieving detailed progress breakdown."""
            mock_database.chapters.find_one.return_value = sample_chapter_data
            
            # Mock aggregation pipeline results
            progress_data = [
                {"_id": ResponseStatus.COMPLETE, "count": 3},
                {"_id": ResponseStatus.DRAFT, "count": 1},
                {"_id": ResponseStatus.SKIPPED, "count": 1}
            ]
            mock_database.question_responses.aggregate.return_value = progress_data

            response = await async_client.get(
                "/api/books/test-book-id/chapters/test-chapter-id/questions/progress/detailed"
            )

            assert response.status_code == 200
            data = response.json()
            
            assert data["by_status"][ResponseStatus.COMPLETE.value] == 3
            assert data["by_status"][ResponseStatus.DRAFT.value] == 1
            assert data["by_status"][ResponseStatus.SKIPPED.value] == 1

        async def test_update_question_progress(self, async_client, mock_database):
            """Test updating question progress tracking."""
            mock_database.question_progress.replace_one.return_value = MagicMock(upserted_id="progress-id")

            progress_data = {
                "question_id": "test-question-id",
                "time_spent": 300,  # 5 minutes
                "word_count": 150,
                "revision_count": 2
            }

            response = await async_client.post(
                "/api/questions/test-question-id/progress",
                json=progress_data
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True

    @pytest.mark.asyncio
    class TestErrorHandling:
        """Tests for error handling and edge cases."""

        async def test_database_connection_error(self, async_client, mock_database):
            """Test handling of database connection errors."""
            mock_database.questions.find.side_effect = Exception("Database connection failed")

            response = await async_client.get(
                "/api/books/test-book-id/chapters/test-chapter-id/questions"
            )

            assert response.status_code == 500
            assert "Internal server error" in response.json()["detail"]

        async def test_rate_limiting(self, async_client, mock_database, sample_chapter_data):
            """Test API rate limiting for expensive operations."""
            mock_database.chapters.find_one.return_value = sample_chapter_data

            # Make multiple rapid requests for question generation
            tasks = []
            for i in range(10):
                task = async_client.post(
                    "/api/books/test-book-id/chapters/test-chapter-id/questions/generate",
                    json={"count": 3}
                )
                tasks.append(task)

            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Some requests should be rate limited
            rate_limited_count = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code == 429)
            assert rate_limited_count > 0

        async def test_malformed_request_body(self, async_client):
            """Test handling of malformed JSON in request body."""
            response = await async_client.post(
                "/api/books/test-book-id/chapters/test-chapter-id/questions/generate",
                content="invalid json{",
                headers={"Content-Type": "application/json"}
            )

            assert response.status_code == 422

        async def test_concurrent_modifications(self, async_client, mock_database):
            """Test handling of concurrent modifications to questions."""
            question_data = sample_questions[0]
            mock_database.questions.find_one.return_value = question_data
            
            # Simulate optimistic locking failure
            mock_database.question_responses.replace_one.side_effect = Exception("Document was modified")

            response = await async_client.post(
                "/api/questions/test-question-id/response",
                json={
                    "response_text": "Concurrent modification test",
                    "status": ResponseStatus.COMPLETE.value
                }
            )

            assert response.status_code == 409
            assert "conflict" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    class TestPerformance:
        """Tests for API performance and optimization."""

        async def test_bulk_operations_performance(self, async_client, mock_database, sample_chapter_data):
            """Test performance of bulk question operations."""
            mock_database.chapters.find_one.return_value = sample_chapter_data
            
            # Generate large number of questions
            large_question_set = [sample_questions[0].copy() for _ in range(100)]
            mock_database.questions.find.return_value = large_question_set

            start_time = asyncio.get_event_loop().time()
            
            response = await async_client.get(
                "/api/books/test-book-id/chapters/test-chapter-id/questions"
            )
            
            end_time = asyncio.get_event_loop().time()
            request_time = end_time - start_time

            assert response.status_code == 200
            assert len(response.json()["questions"]) == 100
            assert request_time < 2.0  # Should complete within 2 seconds

        async def test_pagination_performance(self, async_client, mock_database, sample_chapter_data):
            """Test pagination performance for large question sets."""
            mock_database.chapters.find_one.return_value = sample_chapter_data
            
            # Mock paginated results
            paginated_questions = sample_questions[:2]  # First page
            mock_database.questions.find.return_value.skip.return_value.limit.return_value = paginated_questions
            mock_database.questions.count_documents.return_value = 100

            response = await async_client.get(
                "/api/books/test-book-id/chapters/test-chapter-id/questions",
                params={"page": 1, "limit": 2}
            )

            assert response.status_code == 200
            data = response.json()
            
            assert len(data["questions"]) == 2
            assert data["pagination"]["total"] == 100
            assert data["pagination"]["pages"] == 50

        async def test_caching_headers(self, async_client, mock_database, sample_chapter_data):
            """Test appropriate caching headers for question data."""
            mock_database.chapters.find_one.return_value = sample_chapter_data
            mock_database.questions.find.return_value = sample_questions

            response = await async_client.get(
                "/api/books/test-book-id/chapters/test-chapter-id/questions"
            )

            assert response.status_code == 200
            
            # Should include appropriate cache headers
            assert "Cache-Control" in response.headers
            assert "ETag" in response.headers
            
            # Questions data should be cached for a short period
            cache_control = response.headers["Cache-Control"]
            assert "max-age" in cache_control
