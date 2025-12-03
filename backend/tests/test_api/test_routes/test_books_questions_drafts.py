"""
Comprehensive test suite for Books Chapter Questions and Draft Generation.

This module tests:
- Chapter question generation
- Chapter question listing and filtering
- Question response management
- Question rating
- Question progress tracking
- Chapter draft generation with AI
- Bulk chapter operations

Part 3 of comprehensive books endpoint testing.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone
from bson import ObjectId


# ============================================================================
# Test Data
# ============================================================================

MOCK_CHAPTER_QUESTIONS = [
    {
        "id": "q1",
        "question_text": "What is the key event in this chapter?",
        "question_type": "text",
        "category": "plot",
        "order": 1
    },
    {
        "id": "q2",
        "question_text": "What character development occurs?",
        "question_type": "text",
        "category": "character",
        "order": 2
    },
    {
        "id": "q3",
        "question_text": "What is the chapter's tone?",
        "question_type": "multiple_choice",
        "category": "style",
        "order": 3,
        "options": ["Serious", "Humorous", "Dramatic", "Informative"]
    }
]

MOCK_DRAFT = {
    "content": "This is a generated draft content for the chapter. It includes multiple paragraphs with detailed narrative based on the question responses. The content flows naturally and maintains consistency with the book's style and tone.",
    "word_count": 350,
    "success": True,
    "style": "narrative",
    "metadata": {
        "generated_at": "2024-01-01T00:00:00Z",
        "model": "gpt-4"
    }
}


# ============================================================================
# Chapter Questions Tests
# ============================================================================

@pytest.mark.skip(reason="Feature not implemented - Sprint 3: Chapter question generation API endpoints")
class TestChapterQuestions:
    """Test chapter question generation and management."""

    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.QuestionGenerationService.generate_questions_for_chapter")
    async def test_generate_chapter_questions_success(self, mock_generate, auth_client_factory):
        """Test generating questions for a chapter."""
        mock_generate.return_value = {"questions": MOCK_CHAPTER_QUESTIONS, "success": True}

        client = await auth_client_factory()

        # Create book and chapter
        book_data = {
            "title": "Chapter Questions Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {
            "title": "Test Chapter",
            "content": "Chapter content for question generation.",
            "order": 1
        }
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["id"]

        # Generate questions
        gen_resp = await client.post(f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions")
        assert gen_resp.status_code == 200
        questions = gen_resp.json()
        assert "questions" in questions
        assert len(questions["questions"]) > 0

    @pytest.mark.asyncio
    async def test_generate_questions_no_content(self, auth_client_factory):
        """Test generating questions for chapter without content fails."""
        client = await auth_client_factory()

        # Create book and chapter without content
        book_data = {
            "title": "No Content Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {
            "title": "Empty Chapter",
            "order": 1
        }
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["id"]

        # Try to generate questions (should fail)
        gen_resp = await client.post(f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions")
        assert gen_resp.status_code == 400

    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.QuestionGenerationService.generate_questions_for_chapter")
    async def test_generate_questions_genre_specific(self, mock_generate, auth_client_factory):
        """Test generating genre-specific questions for chapter."""
        mock_generate.return_value = {
            "questions": [
                {
                    "id": "q1",
                    "question_text": "What magical elements are present?",
                    "question_type": "text",
                    "category": "worldbuilding",
                    "order": 1
                }
            ],
            "success": True
        }

        client = await auth_client_factory()

        # Create fantasy book and chapter
        book_data = {
            "title": "Fantasy Book",
            "genre": "Fantasy",
            "target_audience": "Young Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {
            "title": "Magic Chapter",
            "content": "A chapter full of magical elements.",
            "order": 1
        }
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["id"]

        # Generate questions
        gen_resp = await client.post(f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions")
        assert gen_resp.status_code == 200

    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.QuestionGenerationService.generate_questions_for_chapter")
    async def test_list_chapter_questions_all(self, mock_generate, auth_client_factory):
        """Test listing all questions for a chapter."""
        mock_generate.return_value = {"questions": MOCK_CHAPTER_QUESTIONS, "success": True}

        client = await auth_client_factory()

        # Create book, chapter, and generate questions
        book_data = {
            "title": "List Questions Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {
            "title": "Test Chapter",
            "content": "Content",
            "order": 1
        }
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["id"]

        # Generate questions
        await client.post(f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions")

        # List questions
        list_resp = await client.get(f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions")
        assert list_resp.status_code == 200
        questions = list_resp.json()
        assert len(questions) > 0 or "questions" in questions

    @pytest.mark.asyncio
    async def test_list_questions_empty(self, auth_client_factory):
        """Test listing questions when none exist."""
        client = await auth_client_factory()

        # Create book and chapter without questions
        book_data = {
            "title": "No Questions Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {
            "title": "Test Chapter",
            "content": "Content",
            "order": 1
        }
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["id"]

        # List questions (should be empty)
        list_resp = await client.get(f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions")
        assert list_resp.status_code == 200
        questions = list_resp.json()
        assert len(questions) == 0 or questions.get("questions", []) == []

    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.QuestionGenerationService.generate_questions_for_chapter")
    async def test_list_questions_with_pagination(self, mock_generate, auth_client_factory):
        """Test listing questions with pagination."""
        # Generate many questions
        many_questions = [
            {
                "id": f"q{i}",
                "question_text": f"Question {i}?",
                "question_type": "text",
                "category": "plot",
                "order": i
            }
            for i in range(20)
        ]
        mock_generate.return_value = {"questions": many_questions, "success": True}

        client = await auth_client_factory()

        # Create book and chapter
        book_data = {
            "title": "Pagination Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {
            "title": "Test Chapter",
            "content": "Content",
            "order": 1
        }
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["id"]

        # Generate questions
        await client.post(f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions")

        # List with pagination
        list_resp = await client.get(f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions?limit=10&skip=0")
        assert list_resp.status_code == 200


# ============================================================================
# Question Response Tests
# ============================================================================

@pytest.mark.skip(reason="Feature not implemented - Sprint 3: Question responses, rating, progress")
class TestQuestionResponses:
    """Test question response management."""

    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.QuestionGenerationService.generate_questions_for_chapter")
    async def test_save_question_response_new(self, mock_generate, auth_client_factory):
        """Test saving a new question response."""
        mock_generate.return_value = {"questions": MOCK_CHAPTER_QUESTIONS, "success": True}

        client = await auth_client_factory()

        # Create book, chapter, and questions
        book_data = {
            "title": "Response Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {
            "title": "Test Chapter",
            "content": "Content",
            "order": 1
        }
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["id"]

        # Generate questions
        gen_resp = await client.post(f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions")
        questions = gen_resp.json()["questions"]
        question_id = questions[0]["id"]

        # Save response
        response_data = {
            "response_text": "This is my answer to the question.",
            "status": "completed"
        }
        save_resp = await client.put(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{question_id}/response",
            json=response_data
        )
        assert save_resp.status_code == 200

    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.QuestionGenerationService.generate_questions_for_chapter")
    async def test_save_response_update_existing(self, mock_generate, auth_client_factory):
        """Test updating an existing question response."""
        mock_generate.return_value = {"questions": MOCK_CHAPTER_QUESTIONS, "success": True}

        client = await auth_client_factory()

        # Create book, chapter, questions
        book_data = {
            "title": "Update Response Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {
            "title": "Test Chapter",
            "content": "Content",
            "order": 1
        }
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["id"]

        gen_resp = await client.post(f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions")
        questions = gen_resp.json()["questions"]
        question_id = questions[0]["id"]

        # Save initial response
        response_data = {"response_text": "Initial answer", "status": "draft"}
        await client.put(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{question_id}/response",
            json=response_data
        )

        # Update response
        updated_data = {"response_text": "Updated answer", "status": "completed"}
        update_resp = await client.put(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{question_id}/response",
            json=updated_data
        )
        assert update_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_save_response_validation_error(self, auth_client_factory):
        """Test saving response with invalid data fails."""
        client = await auth_client_factory()

        # Create book and chapter
        book_data = {
            "title": "Validation Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {
            "title": "Test Chapter",
            "content": "Content",
            "order": 1
        }
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["id"]

        # Try to save invalid response
        fake_question_id = str(ObjectId())
        invalid_data = {"status": "completed"}  # Missing response_text
        save_resp = await client.put(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{fake_question_id}/response",
            json=invalid_data
        )
        assert save_resp.status_code in [400, 422]

    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.QuestionGenerationService.generate_questions_for_chapter")
    async def test_get_question_response_success(self, mock_generate, auth_client_factory):
        """Test retrieving a question response."""
        mock_generate.return_value = {"questions": MOCK_CHAPTER_QUESTIONS, "success": True}

        client = await auth_client_factory()

        # Create book, chapter, questions, and response
        book_data = {
            "title": "Get Response Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {
            "title": "Test Chapter",
            "content": "Content",
            "order": 1
        }
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["id"]

        gen_resp = await client.post(f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions")
        questions = gen_resp.json()["questions"]
        question_id = questions[0]["id"]

        # Save response
        response_data = {"response_text": "My answer", "status": "completed"}
        await client.put(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{question_id}/response",
            json=response_data
        )

        # Get response
        get_resp = await client.get(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{question_id}/response"
        )
        assert get_resp.status_code == 200
        response = get_resp.json()
        assert "response_text" in response or "text" in response

    @pytest.mark.asyncio
    async def test_get_response_not_found(self, auth_client_factory):
        """Test getting non-existent response."""
        client = await auth_client_factory()

        # Create book and chapter
        book_data = {
            "title": "Not Found Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {
            "title": "Test Chapter",
            "content": "Content",
            "order": 1
        }
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["id"]

        # Try to get non-existent response
        fake_question_id = str(ObjectId())
        get_resp = await client.get(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{fake_question_id}/response"
        )
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_response_unauthorized(self, auth_client_factory):
        """Test user cannot access another user's response."""
        # Create with user 1
        client1 = await auth_client_factory()
        book_data = {
            "title": "User 1 Book",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client1.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Try to access with user 2
        client2 = await auth_client_factory(overrides={"clerk_id": "different_user"})
        fake_chapter_id = str(ObjectId())
        fake_question_id = str(ObjectId())
        get_resp = await client2.get(
            f"/api/v1/books/{book_id}/chapters/{fake_chapter_id}/questions/{fake_question_id}/response"
        )
        assert get_resp.status_code in [403, 404]


# ============================================================================
# Question Rating Tests
# ============================================================================

@pytest.mark.skip(reason="Feature not implemented - Sprint 3: Question rating system")
class TestQuestionRating:
    """Test question rating functionality."""

    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.QuestionGenerationService.generate_questions_for_chapter")
    async def test_rate_question_success(self, mock_generate, auth_client_factory):
        """Test rating a question."""
        mock_generate.return_value = {"questions": MOCK_CHAPTER_QUESTIONS, "success": True}

        client = await auth_client_factory()

        # Create book, chapter, questions
        book_data = {
            "title": "Rating Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {
            "title": "Test Chapter",
            "content": "Content",
            "order": 1
        }
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["id"]

        gen_resp = await client.post(f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions")
        questions = gen_resp.json()["questions"]
        question_id = questions[0]["id"]

        # Rate question
        rating_data = {"rating": 5, "feedback": "Excellent question"}
        rate_resp = await client.post(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{question_id}/rating",
            json=rating_data
        )
        assert rate_resp.status_code == 200

    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.QuestionGenerationService.generate_questions_for_chapter")
    async def test_update_question_rating(self, mock_generate, auth_client_factory):
        """Test updating an existing question rating."""
        mock_generate.return_value = {"questions": MOCK_CHAPTER_QUESTIONS, "success": True}

        client = await auth_client_factory()

        # Create book, chapter, questions
        book_data = {
            "title": "Update Rating Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {
            "title": "Test Chapter",
            "content": "Content",
            "order": 1
        }
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["id"]

        gen_resp = await client.post(f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions")
        questions = gen_resp.json()["questions"]
        question_id = questions[0]["id"]

        # Initial rating
        await client.post(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{question_id}/rating",
            json={"rating": 3}
        )

        # Update rating
        update_resp = await client.post(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{question_id}/rating",
            json={"rating": 5, "feedback": "Changed my mind"}
        )
        assert update_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_rate_question_invalid_rating(self, auth_client_factory):
        """Test rating with invalid value fails validation."""
        client = await auth_client_factory()

        # Create book and chapter
        book_data = {
            "title": "Invalid Rating Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {
            "title": "Test Chapter",
            "content": "Content",
            "order": 1
        }
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["id"]

        fake_question_id = str(ObjectId())

        # Try invalid ratings
        for invalid_rating in [0, 6, -1, 10]:
            rate_resp = await client.post(
                f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{fake_question_id}/rating",
                json={"rating": invalid_rating}
            )
            assert rate_resp.status_code in [400, 422]


# ============================================================================
# Question Progress Tests
# ============================================================================

@pytest.mark.skip(reason="Feature not implemented - Sprint 3: Question progress tracking")
class TestQuestionProgress:
    """Test question progress tracking."""

    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.QuestionGenerationService.generate_questions_for_chapter")
    async def test_get_progress_all_completed(self, mock_generate, auth_client_factory):
        """Test progress when all questions are completed."""
        mock_generate.return_value = {"questions": MOCK_CHAPTER_QUESTIONS, "success": True}

        client = await auth_client_factory()

        # Create book, chapter, questions
        book_data = {
            "title": "Progress Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {
            "title": "Test Chapter",
            "content": "Content",
            "order": 1
        }
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["id"]

        gen_resp = await client.post(f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions")
        questions = gen_resp.json()["questions"]

        # Answer all questions
        for q in questions:
            await client.put(
                f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{q['id']}/response",
                json={"response_text": "Answer", "status": "completed"}
            )

        # Get progress
        progress_resp = await client.get(f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/progress")
        assert progress_resp.status_code == 200
        progress = progress_resp.json()
        assert progress.get("progress") == 100 or progress.get("completed") == len(questions)

    @pytest.mark.asyncio
    async def test_get_progress_no_questions(self, auth_client_factory):
        """Test progress when no questions exist."""
        client = await auth_client_factory()

        # Create book and chapter without questions
        book_data = {
            "title": "No Questions Progress",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {
            "title": "Test Chapter",
            "content": "Content",
            "order": 1
        }
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["id"]

        # Get progress
        progress_resp = await client.get(f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/progress")
        assert progress_resp.status_code == 200
        progress = progress_resp.json()
        assert progress.get("total") == 0


# ============================================================================
# Draft Generation Tests
# ============================================================================

@pytest.mark.skip(reason="Feature not implemented - Sprint 3: Draft generation from responses")
class TestDraftGeneration:
    """Test chapter draft generation with AI."""

    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.QuestionGenerationService.generate_questions_for_chapter")
    @patch("app.services.ai_service.AIService.generate_chapter_draft")
    async def test_generate_draft_success(self, mock_draft, mock_questions, auth_client_factory):
        """Test successful draft generation."""
        mock_questions.return_value = {"questions": MOCK_CHAPTER_QUESTIONS, "success": True}
        mock_draft.return_value = MOCK_DRAFT

        client = await auth_client_factory()

        # Create book, chapter, questions, and responses
        book_data = {
            "title": "Draft Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {
            "title": "Test Chapter",
            "content": "Initial content",
            "order": 1
        }
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["id"]

        # Generate and answer questions
        gen_resp = await client.post(f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions")
        questions = gen_resp.json()["questions"]

        for q in questions:
            await client.put(
                f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{q['id']}/response",
                json={"response_text": "Answer", "status": "completed"}
            )

        # Generate draft
        draft_resp = await client.post(f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-draft")
        assert draft_resp.status_code == 200
        draft = draft_resp.json()
        assert "content" in draft
        assert draft["success"] is True

    @pytest.mark.asyncio
    async def test_generate_draft_no_responses(self, auth_client_factory):
        """Test draft generation without question responses fails."""
        client = await auth_client_factory()

        # Create book and chapter without responses
        book_data = {
            "title": "No Responses Draft",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {
            "title": "Test Chapter",
            "content": "Content",
            "order": 1
        }
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["id"]

        # Try to generate draft (should fail)
        draft_resp = await client.post(f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-draft")
        assert draft_resp.status_code == 400

    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.QuestionGenerationService.generate_questions_for_chapter")
    @patch("app.services.ai_service.AIService.generate_chapter_draft")
    async def test_generate_draft_style_variations(self, mock_draft, mock_questions, auth_client_factory):
        """Test draft generation with different style options."""
        mock_questions.return_value = {"questions": MOCK_CHAPTER_QUESTIONS, "success": True}

        for style in ["narrative", "expository", "descriptive", "persuasive"]:
            mock_draft.return_value = {**MOCK_DRAFT, "style": style}

            client = await auth_client_factory()

            # Create book, chapter, questions
            book_data = {
                "title": f"Style Test {style}",
                "genre": "Fiction",
                "target_audience": "Adults"
            }
            create_resp = await client.post("/api/v1/books/", json=book_data)
            book_id = create_resp.json()["id"]

            chapter_data = {
                "title": "Test Chapter",
                "content": "Content",
                "order": 1
            }
            chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
            chapter_id = chapter_resp.json()["id"]

            # Generate and answer questions
            gen_resp = await client.post(f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions")
            questions = gen_resp.json()["questions"]

            for q in questions:
                await client.put(
                    f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{q['id']}/response",
                    json={"response_text": "Answer", "status": "completed"}
                )

            # Generate draft with style
            draft_resp = await client.post(
                f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-draft",
                json={"style": style}
            )
            assert draft_resp.status_code == 200

    @pytest.mark.asyncio
    @patch("app.services.question_generation_service.QuestionGenerationService.generate_questions_for_chapter")
    @patch("app.services.ai_service.AIService.generate_chapter_draft")
    async def test_generate_draft_ai_failure(self, mock_draft, mock_questions, auth_client_factory):
        """Test handling of AI service failure during draft generation."""
        mock_questions.return_value = {"questions": MOCK_CHAPTER_QUESTIONS, "success": True}
        mock_draft.side_effect = Exception("AI service error")

        client = await auth_client_factory()

        # Create book, chapter, questions
        book_data = {
            "title": "AI Failure Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {
            "title": "Test Chapter",
            "content": "Content",
            "order": 1
        }
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["id"]

        # Generate and answer questions
        gen_resp = await client.post(f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions")
        questions = gen_resp.json()["questions"]

        for q in questions:
            await client.put(
                f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{q['id']}/response",
                json={"response_text": "Answer", "status": "completed"}
            )

        # Try to generate draft (should handle error)
        draft_resp = await client.post(f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-draft")
        assert draft_resp.status_code in [500, 503]
