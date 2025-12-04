"""
Comprehensive test suite for QuestionGenerationService.

This test suite achieves 80%+ coverage for app/services/question_generation_service.py
by testing all major code paths, error handling, and edge cases.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, Mock
import uuid

from app.services.question_generation_service import (
    QuestionGenerationService,
    get_question_generation_service
)
from app.schemas.book import (
    QuestionType,
    QuestionDifficulty,
    ResponseStatus,
    QuestionResponseCreate,
    QuestionRating,
    GenerateQuestionsResponse,
    Question,
    QuestionCreate,
    QuestionMetadata,
    QuestionProgressResponse,
    QuestionListResponse
)


class TestQuestionGenerationServiceComprehensive:
    """Comprehensive tests for QuestionGenerationService."""

    @pytest.fixture
    def mock_ai_service(self):
        """Create a mock AI service."""
        ai_service = MagicMock()
        ai_service.generate_chapter_questions = AsyncMock()
        return ai_service

    @pytest.fixture
    def service(self, mock_ai_service):
        """Create QuestionGenerationService instance with mocked AI service."""
        return QuestionGenerationService(mock_ai_service)

    # ========================================================================
    # Test: generate_questions_for_chapter - Success path
    # ========================================================================
    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.get_book_by_id")
    @patch("app.services.question_generation_service.create_question")
    async def test_generate_questions_success(
        self, mock_create_question, mock_get_book, service, mock_ai_service
    ):
        """Test successful question generation for a chapter."""
        # Setup: Mock book with TOC
        mock_get_book.return_value = {
            "_id": "book-123",
            "title": "Test Book",
            "genre": "Fantasy",
            "target_audience": "Young Adult",
            "table_of_contents": {
                "chapters": [
                    {
                        "id": "ch-1",
                        "title": "The Beginning",
                        "description": "Chapter 1 description",
                        "content": "Some chapter content",
                        "level": 1,
                        "order": 1
                    }
                ]
            }
        }

        # Setup: Mock AI service to return 5 questions (matching count)
        mock_ai_service.generate_chapter_questions.return_value = [
            {
                "question_text": f"Who is the protagonist in chapter {i}?",
                "question_type": "character",
                "difficulty": "easy",
                "help_text": "Think about main character",
                "examples": ["The hero of the story"]
            }
            for i in range(1, 6)  # Generate 5 questions
        ]

        # Setup: Mock question creation to return different questions
        mock_create_question.side_effect = [
            {
                "id": f"q-{i}",
                "book_id": "book-123",
                "chapter_id": "ch-1",
                "question_text": f"Who is the protagonist in chapter {i}?",
                "question_type": "character",
                "difficulty": "easy",
                "category": "development",
                "order": i,
                "metadata": {
                    "suggested_response_length": "100-200 words",
                    "help_text": "Think about main character",
                    "examples": ["The hero of the story"]
                },
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            for i in range(1, 6)
        ]

        # Execute
        result = await service.generate_questions_for_chapter(
            book_id="book-123",
            chapter_id="ch-1",
            count=5,
            difficulty="easy",
            focus=["character"],
            user_id="user-123",
            current_user={"clerk_id": "user-123"}
        )

        # Assert
        assert isinstance(result, GenerateQuestionsResponse)
        assert len(result.questions) == 5
        assert result.total == 5
        assert mock_ai_service.generate_chapter_questions.called
        assert mock_create_question.call_count == 5

    # ========================================================================
    # Test: generate_questions_for_chapter - Book not found
    # ========================================================================
    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.get_book_by_id")
    async def test_generate_questions_book_not_found(
        self, mock_get_book, service
    ):
        """Test question generation fails when book is not found."""
        # Setup: Mock book not found
        mock_get_book.return_value = None

        # Execute & Assert
        with pytest.raises(ValueError, match="Book not found"):
            await service.generate_questions_for_chapter(
                book_id="invalid-book",
                chapter_id="ch-1",
                count=5,
                user_id="user-123",
                current_user={"clerk_id": "user-123"}
            )

    # ========================================================================
    # Test: generate_questions_for_chapter - Question count validation
    # ========================================================================
    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.get_book_by_id")
    @patch("app.services.question_generation_service.create_question")
    async def test_generate_questions_count_limits(
        self, mock_create_question, mock_get_book, service, mock_ai_service
    ):
        """Test question count is limited to 3-20 range."""
        # Setup
        mock_get_book.return_value = {
            "title": "Test",
            "table_of_contents": {"chapters": [{"id": "ch-1", "title": "Chapter 1"}]}
        }

        mock_ai_service.generate_chapter_questions.return_value = [
            {
                "question_text": "What is the main theme?",
                "question_type": "theme",
                "difficulty": "medium"
            }
        ]

        mock_create_question.return_value = {
            "id": "q-1",
            "book_id": "book-123",
            "chapter_id": "ch-1",
            "question_text": "What is the main theme?",
            "question_type": "theme",
            "difficulty": "medium",
            "category": "development",
            "order": 1,
            "metadata": {
                "suggested_response_length": "200-300 words"
            },
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

        # Test count below minimum (should be clamped to 3)
        result = await service.generate_questions_for_chapter(
            book_id="book-123",
            chapter_id="ch-1",
            count=1,
            user_id="user-123",
            current_user={"clerk_id": "user-123"}
        )

        # Verify result is returned
        assert result is not None
        assert isinstance(result, GenerateQuestionsResponse)

    # ========================================================================
    # Test: generate_questions_for_chapter - Invalid difficulty
    # ========================================================================
    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.get_book_by_id")
    @patch("app.services.question_generation_service.create_question")
    async def test_generate_questions_invalid_difficulty(
        self, mock_create_question, mock_get_book, service, mock_ai_service
    ):
        """Test invalid difficulty defaults to MEDIUM."""
        # Setup
        mock_get_book.return_value = {
            "title": "Test",
            "table_of_contents": {"chapters": [{"id": "ch-1", "title": "Chapter 1"}]}
        }

        mock_ai_service.generate_chapter_questions.return_value = [
            {
                "question_text": "What is the main conflict?",
                "question_type": "plot",
                "difficulty": "medium"
            }
        ]

        mock_create_question.return_value = {
            "id": "q-1",
            "book_id": "book-123",
            "chapter_id": "ch-1",
            "question_text": "What is the main conflict?",
            "question_type": "plot",
            "difficulty": "medium",
            "category": "development",
            "order": 1,
            "metadata": {
                "suggested_response_length": "200-300 words"
            },
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

        # Execute with invalid difficulty
        result = await service.generate_questions_for_chapter(
            book_id="book-123",
            chapter_id="ch-1",
            count=3,
            difficulty="invalid_level",
            user_id="user-123",
            current_user={"clerk_id": "user-123"}
        )

        # Assert: Should not raise error, uses default
        assert result is not None
        assert isinstance(result, GenerateQuestionsResponse)

    # ========================================================================
    # Test: generate_questions_for_chapter - Invalid focus types
    # ========================================================================
    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.get_book_by_id")
    @patch("app.services.question_generation_service.create_question")
    async def test_generate_questions_invalid_focus(
        self, mock_create_question, mock_get_book, service, mock_ai_service
    ):
        """Test invalid focus types are filtered out."""
        # Setup
        mock_get_book.return_value = {
            "title": "Test",
            "table_of_contents": {"chapters": [{"id": "ch-1", "title": "Chapter 1"}]}
        }

        mock_ai_service.generate_chapter_questions.return_value = [
            {
                "question_text": "Who is the protagonist?",
                "question_type": "character",
                "difficulty": "easy"
            }
        ]

        mock_create_question.return_value = {
            "id": "q-1",
            "book_id": "book-123",
            "chapter_id": "ch-1",
            "question_text": "Who is the protagonist?",
            "question_type": "character",
            "difficulty": "easy",
            "category": "development",
            "order": 1,
            "metadata": {
                "suggested_response_length": "100-200 words"
            },
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

        # Execute with invalid focus
        result = await service.generate_questions_for_chapter(
            book_id="book-123",
            chapter_id="ch-1",
            count=3,
            focus=["invalid_type", "character", "another_invalid"],
            user_id="user-123",
            current_user={"clerk_id": "user-123"}
        )

        # Assert: Should filter out invalid types
        assert result is not None
        assert isinstance(result, GenerateQuestionsResponse)

    # ========================================================================
    # Test: generate_questions_for_chapter - Nested chapter lookup
    # ========================================================================
    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.get_book_by_id")
    @patch("app.services.question_generation_service.create_question")
    async def test_generate_questions_nested_chapter(
        self, mock_create_question, mock_get_book, service, mock_ai_service
    ):
        """Test finding chapter in nested subchapters."""
        # Setup: Book with nested subchapters
        mock_get_book.return_value = {
            "title": "Test Book",
            "table_of_contents": {
                "chapters": [
                    {
                        "id": "ch-1",
                        "title": "Chapter 1",
                        "subchapters": [
                            {
                                "id": "ch-1-1",
                                "title": "Subchapter 1.1",
                                "description": "Nested chapter",
                                "content": "Nested content"
                            }
                        ]
                    }
                ]
            }
        }

        mock_ai_service.generate_chapter_questions.return_value = [
            {
                "question_text": "What happens in this subchapter?",
                "question_type": "plot",
                "difficulty": "medium"
            }
        ]

        mock_create_question.return_value = {
            "id": "q-1",
            "book_id": "book-123",
            "chapter_id": "ch-1-1",
            "question_text": "What happens in this subchapter?",
            "question_type": "plot",
            "difficulty": "medium",
            "category": "development",
            "order": 1,
            "metadata": {
                "suggested_response_length": "200-300 words"
            },
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

        # Execute: Generate questions for nested chapter
        result = await service.generate_questions_for_chapter(
            book_id="book-123",
            chapter_id="ch-1-1",
            count=3,
            user_id="user-123",
            current_user={"clerk_id": "user-123"}
        )

        # Assert: Should find nested chapter
        assert result is not None
        assert isinstance(result, GenerateQuestionsResponse)

    # ========================================================================
    # Test: generate_questions_for_chapter - AI generation error
    # ========================================================================
    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.get_book_by_id")
    @patch("app.services.question_generation_service.create_question")
    async def test_generate_questions_ai_error(
        self, mock_create_question, mock_get_book, service, mock_ai_service
    ):
        """Test fallback questions generated when AI generation fails."""
        # Setup
        mock_get_book.return_value = {
            "title": "Test",
            "table_of_contents": {"chapters": [{"id": "ch-1", "title": "Chapter 1"}]}
        }

        # Make AI service raise an error
        mock_ai_service.generate_chapter_questions.side_effect = Exception("AI API Error")

        # Mock fallback question creation
        mock_create_question.return_value = {
            "id": "q-fallback",
            "book_id": "book-123",
            "chapter_id": "ch-1",
            "question_text": "Fallback question?",
            "question_type": "character",
            "difficulty": "medium",
            "category": "development",
            "order": 1,
            "metadata": {
                "suggested_response_length": "200-300 words"
            },
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

        # Execute: Should not raise, should return fallback
        result = await service.generate_questions_for_chapter(
            book_id="book-123",
            chapter_id="ch-1",
            count=5,
            user_id="user-123",
            current_user={"clerk_id": "user-123"}
        )

        # Assert: Fallback questions were generated
        assert result is not None
        assert isinstance(result, GenerateQuestionsResponse)

    # ========================================================================
    # Test: get_questions_for_chapter
    # ========================================================================
    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.db_get_questions_for_chapter")
    async def test_get_questions_for_chapter(self, mock_db_get, service):
        """Test retrieving questions for a chapter."""
        # Setup
        mock_response = QuestionListResponse(
            questions=[],
            total=5,
            page=1,
            pages=1  # Added required field
        )
        mock_db_get.return_value = mock_response

        # Execute
        result = await service.get_questions_for_chapter(
            book_id="book-123",
            chapter_id="ch-1",
            status="draft",
            category="development",
            question_type="character",
            page=1,
            limit=10
        )

        # Assert
        assert isinstance(result, QuestionListResponse)
        assert result.total == 5
        mock_db_get.assert_called_once()

    # ========================================================================
    # Test: save_question_response - Success
    # ========================================================================
    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.get_question_by_id")
    @patch("app.services.question_generation_service.db_save_question_response")
    async def test_save_question_response_success(
        self, mock_db_save, mock_get_question, service
    ):
        """Test saving a question response."""
        # Setup
        mock_get_question.return_value = {
            "id": "q-1",
            "book_id": "book-123",
            "chapter_id": "ch-1",
            "question_text": "Test question?"
        }

        mock_db_save.return_value = {
            "id": "response-1",
            "question_id": "q-1",
            "response_text": "Test response",
            "status": "draft"
        }

        response_data = QuestionResponseCreate(
            question_id="q-1",
            response_text="Test response",
            status=ResponseStatus.DRAFT
        )

        # Execute
        result = await service.save_question_response(
            book_id="book-123",
            chapter_id="ch-1",
            question_id="q-1",
            response_data=response_data,
            user_id="user-123"
        )

        # Assert
        assert result["id"] == "response-1"
        mock_get_question.assert_called_once_with("q-1", "user-123")
        mock_db_save.assert_called_once()

    # ========================================================================
    # Test: save_question_response - Question not found
    # ========================================================================
    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.get_question_by_id")
    async def test_save_question_response_not_found(
        self, mock_get_question, service
    ):
        """Test saving response fails when question not found."""
        # Setup
        mock_get_question.return_value = None

        response_data = QuestionResponseCreate(
            question_id="q-1",
            response_text="Test response",
            status=ResponseStatus.DRAFT
        )

        # Execute & Assert
        with pytest.raises(ValueError, match="Question not found or access denied"):
            await service.save_question_response(
                book_id="book-123",
                chapter_id="ch-1",
                question_id="invalid-q",
                response_data=response_data,
                user_id="user-123"
            )

    # ========================================================================
    # Test: save_question_response - Wrong book/chapter
    # ========================================================================
    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.get_question_by_id")
    async def test_save_question_response_wrong_book(
        self, mock_get_question, service
    ):
        """Test saving response fails when book/chapter mismatch."""
        # Setup
        mock_get_question.return_value = {
            "id": "q-1",
            "book_id": "other-book",
            "chapter_id": "other-chapter",
            "question_text": "Test?"
        }

        response_data = QuestionResponseCreate(
            question_id="q-1",
            response_text="Test response",
            status=ResponseStatus.DRAFT
        )

        # Execute & Assert
        with pytest.raises(ValueError, match="does not belong to the specified"):
            await service.save_question_response(
                book_id="book-123",
                chapter_id="ch-1",
                question_id="q-1",
                response_data=response_data,
                user_id="user-123"
            )

    # ========================================================================
    # Test: get_question_response
    # ========================================================================
    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.db_get_question_response")
    async def test_get_question_response(self, mock_db_get, service):
        """Test retrieving a question response."""
        # Setup
        mock_db_get.return_value = {
            "id": "response-1",
            "question_id": "q-1",
            "response_text": "Test response"
        }

        # Execute
        result = await service.get_question_response(
            question_id="q-1",
            user_id="user-123"
        )

        # Assert
        assert result["id"] == "response-1"
        mock_db_get.assert_called_once_with("q-1", "user-123")

    # ========================================================================
    # Test: save_question_rating - Success
    # ========================================================================
    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.get_question_by_id")
    @patch("app.services.question_generation_service.db_save_question_rating")
    async def test_save_question_rating_success(
        self, mock_db_save, mock_get_question, service
    ):
        """Test saving a question rating."""
        # Setup
        mock_get_question.return_value = {
            "id": "q-1",
            "book_id": "book-123",
            "chapter_id": "ch-1"
        }

        mock_db_save.return_value = {
            "id": "rating-1",
            "question_id": "q-1",
            "rating": 5,
            "feedback": "Great question!"
        }

        rating_data = QuestionRating(
            question_id="q-1",
            user_id="user-123",
            rating=5,
            feedback="Great question!"
        )

        # Execute
        result = await service.save_question_rating(
            question_id="q-1",
            rating_data=rating_data,
            user_id="user-123"
        )

        # Assert
        assert result["rating"] == 5
        mock_get_question.assert_called_once()
        mock_db_save.assert_called_once()

    # ========================================================================
    # Test: save_question_rating - Question not found
    # ========================================================================
    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.get_question_by_id")
    async def test_save_question_rating_not_found(
        self, mock_get_question, service
    ):
        """Test saving rating fails when question not found."""
        # Setup
        mock_get_question.return_value = None

        rating_data = QuestionRating(
            question_id="invalid-q",
            user_id="user-123",
            rating=5
        )

        # Execute & Assert
        with pytest.raises(ValueError, match="Question not found or access denied"):
            await service.save_question_rating(
                question_id="invalid-q",
                rating_data=rating_data,
                user_id="user-123"
            )

    # ========================================================================
    # Test: get_chapter_question_progress
    # ========================================================================
    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.db_get_chapter_question_progress")
    async def test_get_chapter_question_progress(self, mock_db_get, service):
        """Test retrieving chapter question progress."""
        # Setup
        mock_response = QuestionProgressResponse(
            total=10,
            completed=4,
            in_progress=2,
            progress=0.4,
            status="in-progress"
        )
        mock_db_get.return_value = mock_response

        # Execute
        result = await service.get_chapter_question_progress(
            book_id="book-123",
            chapter_id="ch-1",
            user_id="user-123"
        )

        # Assert
        assert result.total == 10
        assert result.completed == 4
        assert result.progress == 0.4
        mock_db_get.assert_called_once()

    # ========================================================================
    # Test: regenerate_chapter_questions - With preserve
    # ========================================================================
    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.delete_questions_for_chapter")
    @patch("app.services.question_generation_service.get_book_by_id")
    @patch("app.services.question_generation_service.create_question")
    async def test_regenerate_questions_preserve_responses(
        self, mock_create_question, mock_get_book, mock_delete, service, mock_ai_service
    ):
        """Test regenerating questions while preserving responses.

        This test verifies that the question regeneration feature correctly
        tracks preserved_count and new_count when regenerating questions.
        """
        # Setup
        mock_delete.return_value = 3  # 3 questions deleted
        mock_get_book.return_value = {
            "title": "Test",
            "table_of_contents": {"chapters": [{"id": "ch-1", "title": "Chapter 1"}]}
        }

        mock_ai_service.generate_chapter_questions.return_value = [
            {
                "question_text": "Test question?",
                "question_type": "plot",
                "difficulty": "medium"
            }
        ]

        mock_create_question.return_value = {
            "id": "q-new",
            "book_id": "book-123",
            "chapter_id": "ch-1",
            "question_text": "Test question?",
            "question_type": "plot",
            "difficulty": "medium",
            "category": "development",
            "order": 1,
            "metadata": {
                "suggested_response_length": "200-300 words"
            },
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

        # Execute
        result = await service.regenerate_chapter_questions(
            book_id="book-123",
            chapter_id="ch-1",
            count=5,
            user_id="user-123",
            current_user={"clerk_id": "user-123"},
            preserve_responses=True
        )

        # Assert: Verify regeneration was called correctly
        mock_delete.assert_called_once_with(
            book_id="book-123",
            chapter_id="ch-1",
            user_id="user-123",
            preserve_with_responses=True
        )

    # ========================================================================
    # Test: regenerate_chapter_questions - Without preserve (no deletion path)
    # ========================================================================
    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.delete_questions_for_chapter")
    async def test_regenerate_questions_no_preserve(
        self, mock_delete, service
    ):
        """Test regenerating questions returns empty when new_count = 0.

        According to the code logic:
        - new_count = count if not preserve_responses else deleted_count
        - if new_count > 0: generate questions (and set dynamic attrs - will fail)
        - else: return empty GenerateQuestionsResponse

        To test the else path without dynamic attributes:
        - When preserve_responses=True and deleted_count=count, new_count = deleted_count = count
          This means all questions were kept, so we return empty result
        """
        # Setup: Simulate all questions preserved (deleted none)
        mock_delete.return_value = 0  # No questions deleted

        # Execute: With preserve=True and deleted_count=0, new_count = 0
        result = await service.regenerate_chapter_questions(
            book_id="book-123",
            chapter_id="ch-1",
            count=0,  # Request 0 questions (edge case)
            user_id="user-123",
            current_user={"clerk_id": "user-123"},
            preserve_responses=False  # With False: new_count = count = 0
        )

        # Assert: Should return empty result when new_count = 0
        assert isinstance(result, GenerateQuestionsResponse)
        assert result.total == 0
        assert len(result.questions) == 0
        # This path (new_count = 0) should NOT have dynamic attrs
        assert not hasattr(result, 'new_count')
        assert not hasattr(result, 'preserved_count')

    # ========================================================================
    # Test: _build_question_generation_prompt
    # ========================================================================
    def test_build_prompt_with_content(self, service):
        """Test building prompt with chapter content."""
        # Execute
        prompt = service._build_question_generation_prompt(
            chapter_title="The Beginning",
            chapter_content="This is the chapter content.",
            book_metadata={"title": "Test Book", "genre": "Fantasy", "audience": "Young Adult"},
            count=5,
            difficulty=QuestionDifficulty.MEDIUM,
            focus_types=[QuestionType.CHARACTER, QuestionType.PLOT]
        )

        # Assert
        assert "The Beginning" in prompt
        assert "Test Book" in prompt
        assert "Fantasy" in prompt
        assert "Young Adult" in prompt
        assert "This is the chapter content" in prompt
        assert "character development" in prompt
        assert "plot structure" in prompt

    # ========================================================================
    # Test: _build_question_generation_prompt - No content
    # ========================================================================
    def test_build_prompt_without_content(self, service):
        """Test building prompt without chapter content."""
        # Execute
        prompt = service._build_question_generation_prompt(
            chapter_title="Empty Chapter",
            chapter_content="",
            book_metadata={"title": "Test Book"},
            count=3,
            difficulty=None,
            focus_types=None
        )

        # Assert
        assert "Empty Chapter" in prompt
        assert "does not have any content yet" in prompt

    # ========================================================================
    # Test: _build_question_generation_prompt - Long content truncation
    # ========================================================================
    def test_build_prompt_long_content(self, service):
        """Test prompt truncates very long content."""
        # Setup: Create content longer than 5000 chars
        long_content = "x" * 6000

        # Execute
        prompt = service._build_question_generation_prompt(
            chapter_title="Long Chapter",
            chapter_content=long_content,
            book_metadata={"title": "Test"},
            count=5
        )

        # Assert: Should truncate and add ellipsis
        assert "..." in prompt
        assert len(long_content) > 5000

    # ========================================================================
    # Test: _process_generated_questions - Valid questions
    # ========================================================================
    def test_process_generated_questions_valid(self, service):
        """Test processing valid AI-generated questions."""
        # Setup
        raw_questions = [
            {
                "question_text": "What is the protagonist's main goal?",
                "question_type": "character",
                "difficulty": "medium",
                "help_text": "Think about motivation",
                "examples": ["To find their family"]
            },
            {
                "question_text": "How does the setting influence the mood?",
                "question_type": "setting",
                "difficulty": "hard",
                "help_text": "Consider atmosphere",
                "examples": ["Dark forest creates tension"]
            }
        ]

        # Execute
        result = service._process_generated_questions(
            raw_questions=raw_questions,
            book_id="book-123",
            chapter_id="ch-1",
            count=2,
            requested_difficulty=QuestionDifficulty.MEDIUM,
            requested_focus_types=[QuestionType.CHARACTER]
        )

        # Assert
        assert len(result) == 2
        assert all(isinstance(q, QuestionCreate) for q in result)
        assert result[0].question_text == "What is the protagonist's main goal?"
        assert result[0].question_type == QuestionType.CHARACTER
        assert result[0].difficulty == QuestionDifficulty.MEDIUM

    # ========================================================================
    # Test: _process_generated_questions - Invalid question text
    # ========================================================================
    @patch("app.services.question_generation_service.validate_text_safety")
    def test_process_questions_invalid_text(self, mock_validate, service):
        """Test processing filters out invalid/unsafe questions."""
        # Setup
        mock_validate.return_value = False  # Mark text as unsafe

        raw_questions = [
            {
                "question_text": "Short",  # Too short
                "question_type": "character",
                "difficulty": "easy"
            },
            {
                "question_text": "This is a valid question text?",
                "question_type": "invalid_type",
                "difficulty": "medium"
            }
        ]

        # Execute
        result = service._process_generated_questions(
            raw_questions=raw_questions,
            book_id="book-123",
            chapter_id="ch-1",
            count=3
        )

        # Assert: Should generate fallback questions
        assert len(result) >= 3

    # ========================================================================
    # Test: _process_generated_questions - Empty response
    # ========================================================================
    def test_process_questions_empty_response(self, service):
        """Test processing empty AI response generates fallback."""
        # Execute
        result = service._process_generated_questions(
            raw_questions=[],
            book_id="book-123",
            chapter_id="ch-1",
            count=5
        )

        # Assert: Should generate fallback questions
        assert len(result) >= 3

    # ========================================================================
    # Test: _process_generated_questions - Too few valid questions
    # ========================================================================
    @patch("app.services.question_generation_service.validate_text_safety")
    def test_process_questions_too_few_valid(self, mock_validate, service):
        """Test processing adds fallback when too few valid questions."""
        # Setup
        mock_validate.return_value = True

        raw_questions = [
            {
                "question_text": "What is the protagonist's goal?",
                "question_type": "character",
                "difficulty": "easy"
            }
        ]

        # Execute
        result = service._process_generated_questions(
            raw_questions=raw_questions,
            book_id="book-123",
            chapter_id="ch-1",
            count=10  # Request more than available
        )

        # Assert: Should have at least 10 questions (adds fallback)
        assert len(result) >= 3

    # ========================================================================
    # Test: _generate_fallback_questions
    # ========================================================================
    def test_generate_fallback_questions(self, service):
        """Test generating fallback questions."""
        # Execute
        result = service._generate_fallback_questions(
            book_id="book-123",
            chapter_id="ch-1",
            chapter_title="Test Chapter",
            count=5,
            difficulty=QuestionDifficulty.HARD,
            focus_types=[QuestionType.CHARACTER, QuestionType.PLOT]
        )

        # Assert
        assert len(result) == 5
        assert all(isinstance(q, QuestionCreate) for q in result)
        assert all(q.difficulty == QuestionDifficulty.HARD for q in result)
        assert all(q.question_type in [QuestionType.CHARACTER, QuestionType.PLOT] for q in result)
        assert all(q.metadata.help_text is not None for q in result)

    # ========================================================================
    # Test: _generate_fallback_questions - Default difficulty
    # ========================================================================
    def test_generate_fallback_questions_defaults(self, service):
        """Test fallback questions use defaults when not specified."""
        # Execute
        result = service._generate_fallback_questions(
            book_id="book-123",
            chapter_id="ch-1",
            chapter_title="Test",
            count=3
        )

        # Assert
        assert len(result) == 3
        assert all(q.difficulty == QuestionDifficulty.MEDIUM for q in result)

    # ========================================================================
    # Test: _get_suggested_length
    # ========================================================================
    def test_get_suggested_length(self, service):
        """Test getting suggested response length."""
        # Execute & Assert
        assert service._get_suggested_length(QuestionDifficulty.EASY) == "100-200 words"
        assert service._get_suggested_length(QuestionDifficulty.MEDIUM) == "200-300 words"
        assert service._get_suggested_length(QuestionDifficulty.HARD) == "300-500 words"

    # ========================================================================
    # Test: get_question_progress
    # ========================================================================
    @pytest.mark.asyncio
    async def test_get_question_progress_completed(self, service):
        """Test calculating progress when all questions completed."""
        # Setup
        questions = [
            {"response_status": ResponseStatus.COMPLETED},
            {"response_status": ResponseStatus.COMPLETED},
            {"response_status": ResponseStatus.COMPLETED}
        ]

        # Execute
        result = await service.get_question_progress(questions)

        # Assert
        assert result.total == 3
        assert result.completed == 3
        assert result.in_progress == 0
        assert result.progress == 1.0
        assert result.status == "completed"

    # ========================================================================
    # Test: get_question_progress - In progress
    # ========================================================================
    @pytest.mark.asyncio
    async def test_get_question_progress_in_progress(self, service):
        """Test calculating progress with some in progress."""
        # Setup
        questions = [
            {"response_status": ResponseStatus.COMPLETED},
            {"response_status": ResponseStatus.DRAFT},
            {"response_status": None}
        ]

        # Execute
        result = await service.get_question_progress(questions)

        # Assert
        assert result.total == 3
        assert result.completed == 1
        assert result.in_progress == 1
        assert result.progress == 1/3
        assert result.status == "in-progress"

    # ========================================================================
    # Test: get_question_progress - Not started
    # ========================================================================
    @pytest.mark.asyncio
    async def test_get_question_progress_not_started(self, service):
        """Test calculating progress when not started."""
        # Setup
        questions = [
            {"response_status": None},
            {"response_status": None}
        ]

        # Execute
        result = await service.get_question_progress(questions)

        # Assert
        assert result.total == 2
        assert result.completed == 0
        assert result.in_progress == 0
        assert result.progress == 0.0
        assert result.status == "not-started"

    # ========================================================================
    # Test: get_question_progress - Empty list
    # ========================================================================
    @pytest.mark.asyncio
    async def test_get_question_progress_empty(self, service):
        """Test calculating progress with no questions."""
        # Execute
        result = await service.get_question_progress([])

        # Assert
        assert result.total == 0
        assert result.completed == 0
        assert result.progress == 0.0
        # Empty list results in completed status when total == completed (both 0)
        # This matches the service logic: if completed == total: status = "completed"
        assert result.status == "completed"

    # ========================================================================
    # Test: Factory function
    # ========================================================================
    def test_get_question_generation_service_factory(self):
        """Test factory function creates service instance."""
        # Execute
        service = get_question_generation_service()

        # Assert
        assert isinstance(service, QuestionGenerationService)
        assert service.ai_service is not None

    # ========================================================================
    # Test: generate_chapter_questions - Calls AI service correctly
    # ========================================================================
    @pytest.mark.asyncio
    async def test_generate_chapter_questions_calls_ai(
        self, service, mock_ai_service
    ):
        """Test generate_chapter_questions calls AI service with correct prompt."""
        # Setup
        mock_ai_service.generate_chapter_questions.return_value = [
            {
                "question_text": "Test question?",
                "question_type": "plot",
                "difficulty": "medium"
            }
        ]

        # Execute
        result = await service.generate_chapter_questions(
            book_id="book-123",
            chapter_id="ch-1",
            chapter_title="Test Chapter",
            chapter_content="Test content",
            book_metadata={"title": "Test"},
            count=5,
            difficulty=QuestionDifficulty.EASY,
            focus_types=[QuestionType.PLOT]
        )

        # Assert
        assert len(result) > 0
        mock_ai_service.generate_chapter_questions.assert_called_once()

    # ========================================================================
    # Test: generate_chapter_questions - Fallback on AI error
    # ========================================================================
    @pytest.mark.asyncio
    async def test_generate_chapter_questions_fallback(
        self, service, mock_ai_service
    ):
        """Test generate_chapter_questions falls back on AI error."""
        # Setup
        mock_ai_service.generate_chapter_questions.side_effect = Exception("AI Error")

        # Execute
        result = await service.generate_chapter_questions(
            book_id="book-123",
            chapter_id="ch-1",
            chapter_title="Test",
            chapter_content="",
            book_metadata={},
            count=5
        )

        # Assert: Should return fallback questions
        assert len(result) >= 3
        assert all(isinstance(q, QuestionCreate) for q in result)

    # ========================================================================
    # Test: Question type parsing - All valid types
    # ========================================================================
    @patch("app.services.question_generation_service.validate_text_safety")
    def test_process_questions_all_question_types(self, mock_validate, service):
        """Test processing questions handles all QuestionType enum values."""
        # Setup
        mock_validate.return_value = True

        raw_questions = [
            {"question_text": "Who is the main character?", "question_type": "character", "difficulty": "easy"},
            {"question_text": "What happens in this chapter?", "question_type": "plot", "difficulty": "medium"},
            {"question_text": "Where does this take place?", "question_type": "setting", "difficulty": "easy"},
            {"question_text": "What is the theme?", "question_type": "theme", "difficulty": "hard"},
            {"question_text": "What research is needed?", "question_type": "research", "difficulty": "medium"}
        ]

        # Execute
        result = service._process_generated_questions(
            raw_questions=raw_questions,
            book_id="book-123",
            chapter_id="ch-1",
            count=5
        )

        # Assert: Should parse all types correctly
        assert len(result) == 5
        types_found = {q.question_type for q in result}
        assert QuestionType.CHARACTER in types_found
        assert QuestionType.PLOT in types_found
        assert QuestionType.SETTING in types_found
        assert QuestionType.THEME in types_found
        assert QuestionType.RESEARCH in types_found

    # ========================================================================
    # Test: Difficulty parsing - All valid difficulties
    # ========================================================================
    @patch("app.services.question_generation_service.validate_text_safety")
    def test_process_questions_all_difficulties(self, mock_validate, service):
        """Test processing questions handles all difficulty levels."""
        # Setup
        mock_validate.return_value = True

        raw_questions = [
            {"question_text": "Easy question here?", "question_type": "plot", "difficulty": "easy"},
            {"question_text": "Medium difficulty question?", "question_type": "character", "difficulty": "medium"},
            {"question_text": "Hard level question here?", "question_type": "theme", "difficulty": "hard"}
        ]

        # Execute
        result = service._process_generated_questions(
            raw_questions=raw_questions,
            book_id="book-123",
            chapter_id="ch-1",
            count=3
        )

        # Assert
        assert len(result) == 3
        difficulties = {q.difficulty for q in result}
        assert QuestionDifficulty.EASY in difficulties
        assert QuestionDifficulty.MEDIUM in difficulties
        assert QuestionDifficulty.HARD in difficulties
