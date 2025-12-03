"""
Comprehensive test suite for Books endpoints.

This module tests all endpoints in app/api/endpoints/books.py:
- Book CRUD operations (create, read, update, patch, delete)
- Summary management (get, update, patch, analyze)
- Question workflow (generate, get responses, save responses)
- TOC generation and management
- Chapter CRUD operations
- Chapter content management
- Chapter questions integration
- Draft generation with AI
- Bulk operations
- Tab state management

Target coverage: 80%+ for books.py
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone
from fastapi.encoders import jsonable_encoder
from bson import ObjectId


# ============================================================================
# Test Data and Mocks
# ============================================================================

MOCK_TOC_RESPONSE = {
    "toc": {
        "chapters": [
            {
                "id": "ch1",
                "title": "Introduction",
                "level": 1,
                "order": 1,
                "description": "Introduction chapter"
            },
            {
                "id": "ch2",
                "title": "Main Content",
                "level": 1,
                "order": 2,
                "description": "Core content",
                "subchapters": [
                    {
                        "id": "ch2-1",
                        "title": "Subsection",
                        "level": 2,
                        "order": 1
                    }
                ]
            }
        ]
    },
    "chapters_count": 2,
    "has_subchapters": True,
    "success": True
}

MOCK_SUMMARY_ANALYSIS = {
    "analysis": "This is a well-structured summary with clear objectives.",
    "strengths": ["Clear structure", "Engaging narrative"],
    "suggestions": ["Add more detail to chapter 3"],
    "readability_score": 85,
    "success": True
}

MOCK_QUESTIONS = [
    {
        "id": "q1",
        "question_text": "What is the main theme?",
        "question_type": "text",
        "category": "plot",
        "order": 1
    },
    {
        "id": "q2",
        "question_text": "Who is the target audience?",
        "question_type": "text",
        "category": "audience",
        "order": 2
    },
    {
        "id": "q3",
        "question_text": "What is the desired tone?",
        "question_type": "multiple_choice",
        "category": "style",
        "order": 3,
        "options": ["Formal", "Casual", "Academic"]
    }
]

MOCK_DRAFT = {
    "content": "This is a generated draft content for the chapter. It includes multiple paragraphs and detailed information.",
    "word_count": 250,
    "success": True,
    "style": "narrative"
}


# ============================================================================
# Book CRUD Tests
# ============================================================================

class TestBookCRUD:
    """Test Book Create, Read, Update, Delete operations."""

    @pytest.mark.asyncio
    async def test_delete_book_success(self, auth_client_factory, test_book):
        """Test successful book deletion."""
        client = await auth_client_factory()

        # Create a book first
        book_data = {
            "title": "Book to Delete",
            "description": "This book will be deleted",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        assert create_resp.status_code == 201
        book_id = create_resp.json()["id"]

        # Delete the book
        delete_resp = await client.delete(f"/api/v1/books/{book_id}")
        assert delete_resp.status_code == 204

        # Verify book is deleted
        get_resp = await client.get(f"/api/v1/books/{book_id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_book_not_found(self, auth_client_factory):
        """Test deleting a non-existent book returns 404."""
        client = await auth_client_factory()

        fake_book_id = str(ObjectId())
        delete_resp = await client.delete(f"/api/v1/books/{fake_book_id}")
        assert delete_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_book_unauthorized(self, auth_client_factory):
        """Test user cannot delete another user's book."""
        # Create book with user 1
        client1 = await auth_client_factory()
        book_data = {
            "title": "User 1 Book",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client1.post("/api/v1/books/", json=book_data)
        assert create_resp.status_code == 201
        book_id = create_resp.json()["id"]

        # Try to delete with user 2
        client2 = await auth_client_factory(overrides={"clerk_id": "different_user"})
        delete_resp = await client2.delete(f"/api/v1/books/{book_id}")
        assert delete_resp.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_book_invalid_id(self, auth_client_factory):
        """Test deleting a book with invalid ID format returns 400."""
        client = await auth_client_factory()

        delete_resp = await client.delete("/api/v1/books/invalid_id")
        assert delete_resp.status_code == 400
        assert "invalid book id format" in delete_resp.text.lower()

    @pytest.mark.asyncio
    async def test_update_book_full_update(self, auth_client_factory):
        """Test full update of book details using PUT."""
        client = await auth_client_factory()

        # Create a book
        book_data = {
            "title": "Original Title",
            "description": "Original description",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        assert create_resp.status_code == 201
        book_id = create_resp.json()["id"]

        # Full update with PUT
        update_data = {
            "title": "Updated Title",
            "description": "Updated description",
            "genre": "Non-Fiction",
            "target_audience": "Teenagers"
        }
        update_resp = await client.put(f"/api/v1/books/{book_id}", json=update_data)
        assert update_resp.status_code == 200

        updated_book = update_resp.json()
        assert updated_book["title"] == "Updated Title"
        assert updated_book["description"] == "Updated description"
        assert updated_book["genre"] == "Non-Fiction"
        assert updated_book["target_audience"] == "Teenagers"

    @pytest.mark.asyncio
    async def test_update_book_validation_error(self, auth_client_factory):
        """Test book update with invalid data returns 422."""
        client = await auth_client_factory()

        # Create a book
        book_data = {
            "title": "Valid Book",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        assert create_resp.status_code == 201
        book_id = create_resp.json()["id"]

        # Try to update with invalid title (too long)
        update_data = {"title": "A" * 101}  # Exceeds max length
        update_resp = await client.put(f"/api/v1/books/{book_id}", json=update_data)
        assert update_resp.status_code == 422

    @pytest.mark.asyncio
    async def test_patch_book_partial_update(self, auth_client_factory):
        """Test partial update of book using PATCH."""
        client = await auth_client_factory()

        # Create a book
        book_data = {
            "title": "Original Title",
            "description": "Original description",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        assert create_resp.status_code == 201
        book_id = create_resp.json()["id"]

        # Partial update - only title
        patch_data = {"title": "Patched Title"}
        patch_resp = await client.patch(f"/api/v1/books/{book_id}", json=patch_data)
        assert patch_resp.status_code == 200

        patched_book = patch_resp.json()
        assert patched_book["title"] == "Patched Title"
        assert patched_book["description"] == "Original description"  # Unchanged
        assert patched_book["genre"] == "Fiction"  # Unchanged

    @pytest.mark.asyncio
    async def test_patch_book_not_found(self, auth_client_factory):
        """Test PATCH on non-existent book returns 404."""
        client = await auth_client_factory()

        fake_book_id = str(ObjectId())
        patch_data = {"title": "New Title"}
        patch_resp = await client.patch(f"/api/v1/books/{fake_book_id}", json=patch_data)
        assert patch_resp.status_code == 404


# ============================================================================
# Summary Management Tests
# ============================================================================

class TestSummaryManagement:
    """Test book summary CRUD and analysis operations."""

    @pytest.mark.asyncio
    async def test_get_book_summary_success(self, auth_client_factory):
        """Test retrieving book summary."""
        client = await auth_client_factory()

        # Create book with summary
        book_data = {
            "title": "Book with Summary",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Add summary
        summary_data = {"summary": "This is a test summary for the book."}
        await client.patch(f"/api/v1/books/{book_id}/summary", json=summary_data)

        # Get summary
        get_resp = await client.get(f"/api/v1/books/{book_id}/summary")
        assert get_resp.status_code == 200
        assert get_resp.json()["summary"] == "This is a test summary for the book."

    @pytest.mark.asyncio
    async def test_get_summary_book_not_found(self, auth_client_factory):
        """Test getting summary for non-existent book returns 404."""
        client = await auth_client_factory()

        fake_book_id = str(ObjectId())
        get_resp = await client.get(f"/api/v1/books/{fake_book_id}/summary")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_summary_empty(self, auth_client_factory):
        """Test getting summary when book has no summary."""
        client = await auth_client_factory()

        # Create book without summary
        book_data = {
            "title": "Book Without Summary",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Get summary - should return empty or null
        get_resp = await client.get(f"/api/v1/books/{book_id}/summary")
        assert get_resp.status_code == 200
        summary = get_resp.json().get("summary")
        assert summary is None or summary == ""

    @pytest.mark.asyncio
    async def test_update_book_summary_success(self, auth_client_factory):
        """Test updating book summary with PUT."""
        client = await auth_client_factory()

        # Create book
        book_data = {
            "title": "Summary Test Book",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Update summary
        summary_data = {"summary": "This is a comprehensive summary with at least 50 characters to meet validation."}
        update_resp = await client.put(f"/api/v1/books/{book_id}/summary", json=summary_data)
        assert update_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_summary_too_short(self, auth_client_factory):
        """Test updating summary with text that's too short fails validation."""
        client = await auth_client_factory()

        # Create book
        book_data = {
            "title": "Summary Test Book",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Try to update with too short summary
        summary_data = {"summary": "Too short"}
        update_resp = await client.put(f"/api/v1/books/{book_id}/summary", json=summary_data)
        assert update_resp.status_code == 400

    @pytest.mark.asyncio
    async def test_patch_book_summary_success(self, auth_client_factory):
        """Test partially updating book summary with PATCH."""
        client = await auth_client_factory()

        # Create book
        book_data = {
            "title": "Summary Patch Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Patch summary
        summary_data = {"summary": "This is a patched summary with sufficient length for validation requirements."}
        patch_resp = await client.patch(f"/api/v1/books/{book_id}/summary", json=summary_data)
        assert patch_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_patch_summary_empty_validation(self, auth_client_factory):
        """Test PATCH with empty summary fails validation."""
        client = await auth_client_factory()

        # Create book
        book_data = {
            "title": "Summary Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Try to patch with empty summary
        summary_data = {"summary": ""}
        patch_resp = await client.patch(f"/api/v1/books/{book_id}/summary", json=summary_data)
        assert patch_resp.status_code == 400

    @pytest.mark.asyncio
    @patch("app.services.ai_service.AIService.analyze_summary_for_toc")
    async def test_analyze_summary_success(self, mock_analyze, auth_client_factory):
        """Test AI analysis of book summary."""
        mock_analyze.return_value = MOCK_SUMMARY_ANALYSIS

        client = await auth_client_factory()

        # Create book with summary
        book_data = {
            "title": "Analysis Test Book",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Add summary
        summary_data = {"summary": "This is a comprehensive summary for AI analysis with enough content."}
        await client.patch(f"/api/v1/books/{book_id}/summary", json=summary_data)

        # Analyze summary
        analyze_resp = await client.post(f"/api/v1/books/{book_id}/analyze-summary")
        assert analyze_resp.status_code == 200
        analysis = analyze_resp.json()
        assert "analysis" in analysis
        assert "readability_score" in analysis

    @pytest.mark.asyncio
    async def test_analyze_summary_empty(self, auth_client_factory):
        """Test analyzing empty summary fails."""
        client = await auth_client_factory()

        # Create book without summary
        book_data = {
            "title": "No Summary Book",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Try to analyze (should fail - no summary)
        analyze_resp = await client.post(f"/api/v1/books/{book_id}/analyze-summary")
        assert analyze_resp.status_code == 400

    @pytest.mark.asyncio
    @patch("app.services.ai_service.AIService.analyze_summary_for_toc")
    async def test_analyze_summary_ai_failure(self, mock_analyze, auth_client_factory):
        """Test handling of AI service failure during analysis."""
        mock_analyze.side_effect = Exception("AI service unavailable")

        client = await auth_client_factory()

        # Create book with summary
        book_data = {
            "title": "AI Failure Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Add summary
        summary_data = {"summary": "This is a summary to test AI failure handling."}
        await client.patch(f"/api/v1/books/{book_id}/summary", json=summary_data)

        # Try to analyze (should handle error gracefully)
        analyze_resp = await client.post(f"/api/v1/books/{book_id}/analyze-summary")
        assert analyze_resp.status_code in [500, 503]  # Service error


# ============================================================================
# Question Workflow Tests
# ============================================================================

class TestQuestionWorkflow:
    """Test clarifying questions generation and response management."""

    @pytest.mark.asyncio
    @patch("app.services.ai_service.AIService.generate_clarifying_questions")
    async def test_generate_clarifying_questions_success(self, mock_generate, auth_client_factory):
        """Test successful generation of clarifying questions."""
        mock_generate.return_value = {"questions": MOCK_QUESTIONS, "success": True}

        client = await auth_client_factory()

        # Create book with summary
        book_data = {
            "title": "Questions Test Book",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Add summary
        summary_data = {"summary": "Comprehensive summary for question generation."}
        await client.patch(f"/api/v1/books/{book_id}/summary", json=summary_data)

        # Generate questions
        gen_resp = await client.post(f"/api/v1/books/{book_id}/generate-questions")
        assert gen_resp.status_code == 200
        questions = gen_resp.json()
        assert "questions" in questions
        assert len(questions["questions"]) > 0

    @pytest.mark.asyncio
    async def test_generate_questions_no_summary(self, auth_client_factory):
        """Test generating questions without summary fails."""
        client = await auth_client_factory()

        # Create book without summary
        book_data = {
            "title": "No Summary Book",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Try to generate questions (should fail)
        gen_resp = await client.post(f"/api/v1/books/{book_id}/generate-questions")
        assert gen_resp.status_code == 400

    @pytest.mark.asyncio
    @patch("app.services.ai_service.AIService.generate_clarifying_questions")
    async def test_generate_questions_genre_specific(self, mock_generate, auth_client_factory):
        """Test generating genre-specific questions."""
        mock_generate.return_value = {
            "questions": [
                {
                    "id": "q1",
                    "question_text": "What is the magic system?",
                    "question_type": "text",
                    "category": "worldbuilding",
                    "order": 1
                }
            ],
            "success": True
        }

        client = await auth_client_factory()

        # Create fantasy book
        book_data = {
            "title": "Fantasy Questions Test",
            "genre": "Fantasy",
            "target_audience": "Young Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Add summary
        summary_data = {"summary": "A fantasy story with magic and adventure."}
        await client.patch(f"/api/v1/books/{book_id}/summary", json=summary_data)

        # Generate questions
        gen_resp = await client.post(f"/api/v1/books/{book_id}/generate-questions")
        assert gen_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_question_responses_empty(self, auth_client_factory):
        """Test getting question responses when none exist."""
        client = await auth_client_factory()

        # Create book
        book_data = {
            "title": "Response Test Book",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Get responses (should be empty)
        get_resp = await client.get(f"/api/v1/books/{book_id}/question-responses")
        assert get_resp.status_code == 200
        responses = get_resp.json()
        assert "responses" in responses
        assert len(responses["responses"]) == 0

    @pytest.mark.asyncio
    async def test_save_question_responses_new(self, auth_client_factory):
        """Test saving new question responses."""
        client = await auth_client_factory()

        # Create book
        book_data = {
            "title": "Response Save Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Save responses
        responses_data = {
            "responses": [
                {"question": "What is the theme?", "answer": "Love and loss"},
                {"question": "Who is the protagonist?", "answer": "Jane Doe"},
                {"question": "What is the setting?", "answer": "Modern day New York"}
            ]
        }
        save_resp = await client.put(f"/api/v1/books/{book_id}/question-responses", json=responses_data)
        assert save_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_save_question_responses_update_existing(self, auth_client_factory):
        """Test updating existing question responses."""
        client = await auth_client_factory()

        # Create book
        book_data = {
            "title": "Response Update Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Save initial responses
        responses_data = {
            "responses": [
                {"question": "Q1", "answer": "Answer 1"}
            ]
        }
        await client.put(f"/api/v1/books/{book_id}/question-responses", json=responses_data)

        # Update responses
        updated_responses = {
            "responses": [
                {"question": "Q1", "answer": "Updated Answer 1"},
                {"question": "Q2", "answer": "Answer 2"}
            ]
        }
        update_resp = await client.put(f"/api/v1/books/{book_id}/question-responses", json=updated_responses)
        assert update_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_save_responses_validation_error(self, auth_client_factory):
        """Test saving responses with invalid data fails validation."""
        client = await auth_client_factory()

        # Create book
        book_data = {
            "title": "Validation Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Try to save invalid responses (missing required fields)
        invalid_responses = {"responses": [{"question": "Q1"}]}  # Missing answer
        save_resp = await client.put(f"/api/v1/books/{book_id}/question-responses", json=invalid_responses)
        assert save_resp.status_code == 422


# Continue in next part...
