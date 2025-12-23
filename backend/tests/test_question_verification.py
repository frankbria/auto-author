"""
Tests for question generation and response save verification logic.

These tests ensure that:
1. Question generation verifies all questions are saved to database
2. Verification catches save failures and discrepancies
3. Appropriate errors are raised when verification fails
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.question_generation_service import QuestionGenerationService
from app.schemas.book import (
    QuestionCreate,
    Question,
    QuestionType,
    QuestionDifficulty,
    QuestionListResponse,
    QuestionMetadata,
    ResponseStatus
)


@pytest.fixture
def mock_ai_service():
    """Mock AI service for testing."""
    mock = MagicMock()
    mock.generate_chapter_questions = AsyncMock()
    return mock


@pytest.fixture
def question_service(mock_ai_service):
    """Create question generation service with mocked AI."""
    return QuestionGenerationService(mock_ai_service)


@pytest.fixture
def sample_questions():
    """Sample questions for testing."""
    return [
        QuestionCreate(
            book_id="book-123",
            chapter_id="chapter-456",
            question_text="What is the main theme?",
            question_type=QuestionType.THEME,
            difficulty=QuestionDifficulty.MEDIUM,
            category="development",
            order=1,
            metadata=QuestionMetadata(suggested_response_length="200-300 words")
        ),
        QuestionCreate(
            book_id="book-123",
            chapter_id="chapter-456",
            question_text="Who are the main characters?",
            question_type=QuestionType.CHARACTER,
            difficulty=QuestionDifficulty.EASY,
            category="development",
            order=2,
            metadata=QuestionMetadata(suggested_response_length="100-200 words")
        ),
        QuestionCreate(
            book_id="book-123",
            chapter_id="chapter-456",
            question_text="What is the setting?",
            question_type=QuestionType.SETTING,
            difficulty=QuestionDifficulty.EASY,
            category="development",
            order=3,
            metadata=QuestionMetadata(suggested_response_length="100-200 words")
        )
    ]


@pytest.fixture
def sample_saved_questions():
    """Sample saved questions (as dicts from database)."""
    return [
        {
            "id": "q1",
            "book_id": "book-123",
            "chapter_id": "chapter-456",
            "question_text": "What is the main theme?",
            "question_type": "theme",
            "difficulty": "medium",
            "category": "development",
            "order": 1,
            "response_status": "unanswered",
            "metadata": {"suggested_response_length": "200-300 words"},
            "created_at": "2025-01-01T00:00:00Z"
        },
        {
            "id": "q2",
            "book_id": "book-123",
            "chapter_id": "chapter-456",
            "question_text": "Who are the main characters?",
            "question_type": "character",
            "difficulty": "easy",
            "category": "development",
            "order": 2,
            "response_status": "unanswered",
            "metadata": {"suggested_response_length": "100-200 words"},
            "created_at": "2025-01-01T00:00:00Z"
        },
        {
            "id": "q3",
            "book_id": "book-123",
            "chapter_id": "chapter-456",
            "question_text": "What is the setting?",
            "question_type": "setting",
            "difficulty": "easy",
            "category": "development",
            "order": 3,
            "response_status": "unanswered",
            "metadata": {"suggested_response_length": "100-200 words"},
            "created_at": "2025-01-01T00:00:00Z"
        }
    ]


class TestQuestionSaveVerification:
    """Tests for question save verification logic."""

    @pytest.mark.asyncio
    async def test_verification_passes_when_all_questions_saved(
        self,
        question_service,
        mock_ai_service,
        sample_questions,
        sample_saved_questions
    ):
        """Test that verification passes when all questions are saved correctly."""

        # Mock AI service to return raw questions
        mock_ai_service.generate_chapter_questions.return_value = [
            {
                "question_text": "What is the main theme?",
                "question_type": "theme",
                "difficulty": "medium"
            },
            {
                "question_text": "Who are the main characters?",
                "question_type": "character",
                "difficulty": "easy"
            },
            {
                "question_text": "What is the setting?",
                "question_type": "setting",
                "difficulty": "easy"
            }
        ]

        # Mock database operations
        with patch('app.services.question_generation_service.get_book_by_id', new_callable=AsyncMock) as mock_get_book, \
             patch('app.services.question_generation_service.create_questions_batch', new_callable=AsyncMock) as mock_batch, \
             patch('app.services.question_generation_service.db_get_questions_for_chapter', new_callable=AsyncMock) as mock_get_questions:

            # Setup mocks
            mock_get_book.return_value = {
                "id": "book-123",
                "title": "Test Book",
                "genre": "Fiction",
                "target_audience": "Adults",
                "table_of_contents": {
                    "chapters": [
                        {
                            "id": "chapter-456",
                            "title": "Test Chapter",
                            "content": "Test content",
                            "description": "Test description"
                        }
                    ]
                }
            }

            mock_batch.return_value = sample_saved_questions

            # Verification should find all 3 questions
            mock_get_questions.return_value = QuestionListResponse(
                questions=sample_saved_questions,
                total=3,
                page=1,
                pages=1
            )

            # Execute - should not raise an exception
            result = await question_service.generate_questions_for_chapter(
                book_id="book-123",
                chapter_id="chapter-456",
                count=3,
                user_id="user-789"
            )

            # Assertions
            assert len(result.questions) == 3
            assert result.total == 3
            mock_batch.assert_called_once()
            mock_get_questions.assert_called_once()

    @pytest.mark.asyncio
    async def test_verification_fails_when_questions_missing(
        self,
        question_service,
        mock_ai_service,
        sample_questions,
        sample_saved_questions
    ):
        """Test that verification fails when some questions are missing from database."""

        # Mock AI service
        mock_ai_service.generate_chapter_questions.return_value = [
            {
                "question_text": "What is the main theme?",
                "question_type": "theme",
                "difficulty": "medium"
            },
            {
                "question_text": "Who are the main characters?",
                "question_type": "character",
                "difficulty": "easy"
            },
            {
                "question_text": "What is the setting?",
                "question_type": "setting",
                "difficulty": "easy"
            }
        ]

        # Mock database operations
        with patch('app.services.question_generation_service.get_book_by_id', new_callable=AsyncMock) as mock_get_book, \
             patch('app.services.question_generation_service.create_questions_batch', new_callable=AsyncMock) as mock_batch, \
             patch('app.services.question_generation_service.db_get_questions_for_chapter', new_callable=AsyncMock) as mock_get_questions:

            # Setup mocks
            mock_get_book.return_value = {
                "id": "book-123",
                "title": "Test Book",
                "genre": "Fiction",
                "target_audience": "Adults",
                "table_of_contents": {
                    "chapters": [
                        {
                            "id": "chapter-456",
                            "title": "Test Chapter",
                            "content": "Test content",
                            "description": "Test description"
                        }
                    ]
                }
            }

            mock_batch.return_value = sample_saved_questions

            # Verification finds only 2 questions (1 is missing!)
            mock_get_questions.return_value = QuestionListResponse(
                questions=sample_saved_questions[:2],  # Only first 2 questions
                total=2,  # Only 2 found
                page=1,
                pages=1
            )

            # Execute - should raise an exception
            with pytest.raises(Exception) as exc_info:
                await question_service.generate_questions_for_chapter(
                    book_id="book-123",
                    chapter_id="chapter-456",
                    count=3,
                    user_id="user-789"
                )

            # Check error message
            assert "Data persistence verification failed" in str(exc_info.value)
            assert "Expected 3 questions, but only 2 found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verification_fails_when_query_fails(
        self,
        question_service,
        mock_ai_service,
        sample_questions,
        sample_saved_questions
    ):
        """Test that verification fails when the verification query itself fails."""

        # Mock AI service
        mock_ai_service.generate_chapter_questions.return_value = [
            {
                "question_text": "What is the main theme?",
                "question_type": "theme",
                "difficulty": "medium"
            }
        ]

        # Mock database operations
        with patch('app.services.question_generation_service.get_book_by_id', new_callable=AsyncMock) as mock_get_book, \
             patch('app.services.question_generation_service.create_questions_batch', new_callable=AsyncMock) as mock_batch, \
             patch('app.services.question_generation_service.db_get_questions_for_chapter', new_callable=AsyncMock) as mock_get_questions:

            # Setup mocks
            mock_get_book.return_value = {
                "id": "book-123",
                "title": "Test Book",
                "genre": "Fiction",
                "target_audience": "Adults",
                "table_of_contents": {
                    "chapters": [
                        {
                            "id": "chapter-456",
                            "title": "Test Chapter",
                            "content": "Test content",
                            "description": "Test description"
                        }
                    ]
                }
            }

            mock_batch.return_value = [sample_saved_questions[0]]

            # Verification query fails
            mock_get_questions.side_effect = Exception("Database connection error")

            # Execute - should raise an exception
            with pytest.raises(Exception) as exc_info:
                await question_service.generate_questions_for_chapter(
                    book_id="book-123",
                    chapter_id="chapter-456",
                    count=1,
                    user_id="user-789"
                )

            # Check error message
            assert "Failed to verify question persistence" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verification_logs_success(
        self,
        question_service,
        mock_ai_service,
        sample_questions,
        sample_saved_questions,
        caplog
    ):
        """Test that successful verification logs appropriate messages."""
        import logging
        caplog.set_level(logging.INFO)

        # Mock AI service
        mock_ai_service.generate_chapter_questions.return_value = [
            {
                "question_text": "What is the main theme?",
                "question_type": "theme",
                "difficulty": "medium"
            }
        ]

        # Mock database operations
        with patch('app.services.question_generation_service.get_book_by_id', new_callable=AsyncMock) as mock_get_book, \
             patch('app.services.question_generation_service.create_questions_batch', new_callable=AsyncMock) as mock_batch, \
             patch('app.services.question_generation_service.db_get_questions_for_chapter', new_callable=AsyncMock) as mock_get_questions:

            # Setup mocks
            mock_get_book.return_value = {
                "id": "book-123",
                "title": "Test Book",
                "genre": "Fiction",
                "target_audience": "Adults",
                "table_of_contents": {
                    "chapters": [
                        {
                            "id": "chapter-456",
                            "title": "Test Chapter",
                            "content": "Test content",
                            "description": "Test description"
                        }
                    ]
                }
            }

            mock_batch.return_value = [sample_saved_questions[0]]

            # Verification finds the question
            mock_get_questions.return_value = QuestionListResponse(
                questions=[sample_saved_questions[0]],
                total=1,
                page=1,
                pages=1
            )

            # Execute
            await question_service.generate_questions_for_chapter(
                book_id="book-123",
                chapter_id="chapter-456",
                count=1,
                user_id="user-789"
            )

            # Check logs
            assert "Verification successful" in caplog.text
            assert "1 questions confirmed in database" in caplog.text
            assert "book_id=book-123" in caplog.text
            assert "chapter_id=chapter-456" in caplog.text
            assert "user_id=user-789" in caplog.text
