import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.question_generation_service import QuestionGenerationService
from app.schemas.book import (
    QuestionType,
    QuestionDifficulty,
    ResponseStatus,
    QuestionResponseCreate,
    QuestionRating,
    GenerateQuestionsResponse
)

# Import test fixtures directly
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../fixtures'))

from question_generation_fixtures import (
    sample_questions,
    sample_question_responses,
    sample_question_ratings,
    book_with_questions,
    ai_question_response
)


class TestQuestionGenerationService:
    """Tests for the QuestionGenerationService class."""

    @pytest.fixture
    def mock_ai_service(self):
        """Create a mock AI service."""
        ai_service = MagicMock()
        ai_service.generate_chapter_questions = AsyncMock()
        return ai_service

    @pytest.fixture
    def service(self, mock_ai_service):
        """Create an instance of QuestionGenerationService."""
        return QuestionGenerationService(mock_ai_service)

    @patch("app.services.question_generation_service.get_book_by_id")
    @patch("app.services.question_generation_service.create_question")
    async def test_generate_questions_for_chapter(self, mock_create_question, mock_get_book, service, mock_ai_service):
        """Test generating questions for a chapter."""
        # Mock book data
        mock_get_book.return_value = {
            "_id": "test-book-id",
            "title": "Test Book",
            "genre": "Fantasy",
            "target_audience": "Young Adult",
            "owner_id": "test-user-id",
            "table_of_contents": {
                "chapters": [
                    {
                        "id": "ch-test-1",
                        "title": "Test Chapter",
                        "description": "A chapter for testing",
                        "content": "This is test content for the chapter.",
                        "level": 1,
                        "order": 1,
                        "status": "draft"
                    }
                ]
            }
        }
        
        # Mock AI service response
        mock_ai_service.generate_chapter_questions.return_value = [
            {
                "question_text": "What is the main character's goal?",
                "question_type": "character",
                "difficulty": "medium",
                "help_text": "Think about what drives the character",
                "examples": ["To find their lost family"]
            },
            {
                "question_text": "How does the setting affect the mood?",
                "question_type": "setting",
                "difficulty": "medium",
                "help_text": "Consider the atmosphere",
                "examples": ["The dark forest creates tension"]
            }
        ]
        
        # Mock create_question to return saved questions
        mock_create_question.side_effect = [
            {"id": "q1", "question_text": "What is the main character's goal?", "question_type": "character"},
            {"id": "q2", "question_text": "How does the setting affect the mood?", "question_type": "setting"}
        ]
        
        # Call the method
        result = await service.generate_questions_for_chapter(
            book_id="test-book-id",
            chapter_id="ch-test-1",
            count=2,
            difficulty="medium",
            focus=["character", "setting"],
            current_user={"clerk_id": "test-user-id"}
        )
        
        # Assert that AI service was called
        mock_ai_service.generate_chapter_questions.assert_called_once()
        
        # Assert that questions were created in the database
        assert mock_create_question.call_count == 2
        
        # Verify the result structure
        assert isinstance(result, GenerateQuestionsResponse)
        assert len(result.questions) == 2
        assert result.total == 2
        assert result.success is True

    @patch("app.services.question_generation_service.db_get_questions_for_chapter")
    async def test_get_questions_for_chapter(self, mock_db_get_questions, service):
        """Test retrieving questions for a chapter."""
        # Mock database response
        from app.schemas.book import QuestionListResponse
        mock_response = QuestionListResponse(
            questions=sample_questions[:2],
            total=2,
            page=1,
            limit=10,
            has_more=False
        )
        mock_db_get_questions.return_value = mock_response
        
        # Call the method
        result = await service.get_questions_for_chapter(
            book_id="test-book-id",
            chapter_id="ch-test-1",
            page=1,
            limit=10
        )
        
        # Verify the result
        assert isinstance(result, QuestionListResponse)
        assert result.total == 2
        assert len(result.questions) == 2
        assert result.page == 1

    @patch("app.services.question_generation_service.get_question_by_id")
    @patch("app.services.question_generation_service.db_save_question_response")
    async def test_save_question_response(self, mock_db_save, mock_get_question, service):
        """Test saving a question response."""
        # Mock question lookup
        mock_get_question.return_value = {
            "id": "q1",
            "book_id": "test-book-id",
            "chapter_id": "ch-test-1",
            "question_text": "Test question?"
        }
        
        # Mock save response
        mock_db_save.return_value = {
            "id": "response-id",
            "question_id": "q1",
            "user_id": "test-user-id",
            "response_text": "This is a test response.",
            "status": "draft",
            "word_count": 5,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Create response data
        response_data = QuestionResponseCreate(
            response_text="This is a test response.",
            status=ResponseStatus.DRAFT
        )
        
        # Call the method
        result = await service.save_question_response(
            book_id="test-book-id",
            chapter_id="ch-test-1",
            question_id="q1",
            response_data=response_data,
            user_id="test-user-id"
        )
        
        # Verify that get_question_by_id was called
        mock_get_question.assert_called_once_with("q1", "test-user-id")
        
        # Verify that db_save_question_response was called
        mock_db_save.assert_called_once()
        
        # Verify the result
        assert result["id"] == "response-id"
        assert result["question_id"] == "q1"

    @patch("app.services.question_generation_service.db_get_question_response")
    async def test_get_question_response(self, mock_db_get, service):
        """Test retrieving a question response."""
        # Mock database response
        mock_db_get.return_value = sample_question_responses[0]
        
        # Call the method
        result = await service.get_question_response(
            question_id="q1",
            user_id="test-user-id"
        )
        
        # Verify the result
        assert result == sample_question_responses[0]
        mock_db_get.assert_called_once_with("q1", "test-user-id")

    @patch("app.services.question_generation_service.get_question_by_id")
    @patch("app.services.question_generation_service.db_save_question_rating")
    async def test_save_question_rating(self, mock_db_save, mock_get_question, service):
        """Test saving a question rating."""
        # Mock question lookup
        mock_get_question.return_value = {
            "id": "q1",
            "book_id": "test-book-id",
            "chapter_id": "ch-test-1",
            "question_text": "Test question?"
        }
        
        # Mock save response
        mock_db_save.return_value = {
            "id": "rating-id",
            "question_id": "q1",
            "user_id": "test-user-id",
            "rating": 4,
            "feedback": "Good question",
            "created_at": datetime.now(timezone.utc)
        }
        
        # Create rating data
        rating_data = QuestionRating(
            rating=4,
            feedback="Good question"
        )
        
        # Call the method
        result = await service.save_question_rating(
            question_id="q1",
            rating_data=rating_data,
            user_id="test-user-id"
        )
        
        # Verify that get_question_by_id was called
        mock_get_question.assert_called_once_with("q1", "test-user-id")
        
        # Verify that db_save_question_rating was called
        mock_db_save.assert_called_once()
        
        # Verify the result
        assert result["id"] == "rating-id"
        assert result["rating"] == 4

    @patch("app.services.question_generation_service.db_get_chapter_question_progress")
    async def test_get_chapter_question_progress(self, mock_db_get_progress, service):
        """Test retrieving question progress for a chapter."""
        # Mock database response
        from app.schemas.book import QuestionProgressResponse
        mock_response = QuestionProgressResponse(
            total=5,
            completed=2,
            in_progress=1,
            progress=0.4,
            status="in-progress"
        )
        mock_db_get_progress.return_value = mock_response
        
        # Call the method
        result = await service.get_chapter_question_progress(
            book_id="test-book-id",
            chapter_id="ch-test-1",
            user_id="test-user-id"
        )
        
        # Verify the result
        assert isinstance(result, QuestionProgressResponse)
        assert result.total == 5
        assert result.completed == 2
        assert result.in_progress == 1
        assert result.progress == 0.4
        assert result.status == "in-progress"

    @patch("app.services.question_generation_service.delete_questions_for_chapter")
    async def test_regenerate_chapter_questions(self, mock_delete_questions, service):
        """Test regenerating questions for a chapter."""
        # Mock delete questions response
        mock_delete_questions.return_value = 2  # 2 questions deleted
        
        # Mock the generate_questions_for_chapter method
        with patch.object(service, "generate_questions_for_chapter") as mock_generate:
            mock_generate.return_value = GenerateQuestionsResponse(
                questions=[
                    {"id": "q3", "question_text": "New question 1"},
                    {"id": "q4", "question_text": "New question 2"}
                ],
                total=2,
                generated_at=datetime.now(timezone.utc).isoformat(),
                success=True
            )
            
            # Call the method
            result = await service.regenerate_chapter_questions(
                book_id="test-book-id",
                chapter_id="ch-test-1",
                count=4,
                difficulty="medium",
                focus=["character"],
                user_id="test-user-id",
                preserve_responses=True
            )
            
            # Verify that delete_questions_for_chapter was called
            mock_delete_questions.assert_called_once_with(
                book_id="test-book-id",
                chapter_id="ch-test-1",
                user_id="test-user-id",
                preserve_with_responses=True
            )
            
            # Verify that generate_questions_for_chapter was called
            mock_generate.assert_called_once()
            
            # Verify the result
            assert isinstance(result, GenerateQuestionsResponse)
            assert result.total == 4  # preserved_count + new_count
            assert result.preserved_count == 2  # 4 - 2 deleted
            assert result.new_count == 2

    def test_get_suggested_length(self, service):
        """Test getting suggested response length based on difficulty."""
        assert service._get_suggested_length(QuestionDifficulty.EASY) == "100-200 words"
        assert service._get_suggested_length(QuestionDifficulty.MEDIUM) == "200-300 words"
        assert service._get_suggested_length(QuestionDifficulty.HARD) == "300-500 words"

    def test_generate_fallback_questions(self, service):
        """Test generating fallback questions when AI fails."""
        fallback_questions = service._generate_fallback_questions(
            book_id="test-book-id",
            chapter_id="ch-test-1",
            chapter_title="Test Chapter",
            count=3,
            difficulty=QuestionDifficulty.MEDIUM,
            focus_types=[QuestionType.CHARACTER, QuestionType.PLOT]
        )
        
        assert len(fallback_questions) == 3
        for question in fallback_questions:
            assert question.book_id == "test-book-id"
            assert question.chapter_id == "ch-test-1"
            assert question.difficulty == QuestionDifficulty.MEDIUM
            assert question.question_type in [QuestionType.CHARACTER, QuestionType.PLOT]
            assert len(question.question_text) > 0
            assert question.metadata is not None
            assert "suggested_response_length" in question.metadata
