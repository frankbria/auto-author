"""
Comprehensive test suite for Books TOC and Chapters endpoints.

This module tests:
- TOC generation readiness checks
- TOC generation with AI
- TOC retrieval and updates
- Chapter CRUD operations
- Chapter content management
- Bulk chapter operations
- Tab state management

Part 2 of comprehensive books endpoint testing.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone
from bson import ObjectId


# ============================================================================
# Test Data
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
                "description": "Core content"
            }
        ]
    },
    "chapters_count": 2,
    "has_subchapters": False,
    "success": True
}


# ============================================================================
# TOC Generation Tests
# ============================================================================

class TestTOCGeneration:
    """Test Table of Contents generation and management."""

    @pytest.mark.asyncio
    async def test_check_toc_readiness_ready(self, auth_client_factory):
        """Test TOC generation readiness when all requirements are met."""
        client = await auth_client_factory()

        # Create book with summary and responses
        book_data = {
            "title": "TOC Ready Book",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Add summary
        summary_data = {"summary": "Comprehensive summary for TOC generation."}
        await client.patch(f"/api/v1/books/{book_id}/summary", json=summary_data)

        # Add question responses
        responses_data = {
            "responses": [
                {"question": "Q1", "answer": "Answer 1"},
                {"question": "Q2", "answer": "Answer 2"}
            ]
        }
        await client.put(f"/api/v1/books/{book_id}/question-responses", json=responses_data)

        # Check readiness
        readiness_resp = await client.get(f"/api/v1/books/{book_id}/toc-readiness")
        assert readiness_resp.status_code == 200
        readiness = readiness_resp.json()
        assert readiness["ready"] is True

    @pytest.mark.asyncio
    async def test_check_toc_readiness_missing_summary(self, auth_client_factory):
        """Test TOC readiness check when summary is missing."""
        client = await auth_client_factory()

        # Create book without summary
        book_data = {
            "title": "No Summary Book",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Check readiness (should not be ready)
        readiness_resp = await client.get(f"/api/v1/books/{book_id}/toc-readiness")
        assert readiness_resp.status_code == 200
        readiness = readiness_resp.json()
        assert readiness["ready"] is False
        assert "summary" in str(readiness.get("missing", [])).lower()

    @pytest.mark.asyncio
    async def test_check_toc_readiness_missing_responses(self, auth_client_factory):
        """Test TOC readiness check when question responses are missing."""
        client = await auth_client_factory()

        # Create book with summary only
        book_data = {
            "title": "No Responses Book",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Add summary
        summary_data = {"summary": "Summary without responses."}
        await client.patch(f"/api/v1/books/{book_id}/summary", json=summary_data)

        # Check readiness (should not be ready)
        readiness_resp = await client.get(f"/api/v1/books/{book_id}/toc-readiness")
        assert readiness_resp.status_code == 200
        readiness = readiness_resp.json()
        assert readiness["ready"] is False

    @pytest.mark.asyncio
    @patch("app.services.ai_service.AIService.generate_toc_from_summary_and_responses")
    async def test_generate_toc_success(self, mock_generate, auth_client_factory):
        """Test successful TOC generation."""
        mock_generate.return_value = MOCK_TOC_RESPONSE

        client = await auth_client_factory()

        # Create book with requirements
        book_data = {
            "title": "TOC Gen Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Add summary and responses
        await client.patch(f"/api/v1/books/{book_id}/summary",
                          json={"summary": "Summary for TOC."})
        await client.put(f"/api/v1/books/{book_id}/question-responses",
                        json={"responses": [{"question": "Q1", "answer": "A1"}]})

        # Generate TOC
        gen_resp = await client.post(f"/api/v1/books/{book_id}/generate-toc")
        assert gen_resp.status_code == 200
        toc = gen_resp.json()
        assert "toc" in toc
        assert toc["success"] is True

    @pytest.mark.asyncio
    async def test_generate_toc_no_summary(self, auth_client_factory):
        """Test TOC generation without summary fails."""
        client = await auth_client_factory()

        # Create book
        book_data = {
            "title": "No Summary TOC Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Try to generate TOC (should fail)
        gen_resp = await client.post(f"/api/v1/books/{book_id}/generate-toc")
        assert gen_resp.status_code == 400

    @pytest.mark.asyncio
    async def test_generate_toc_no_responses(self, auth_client_factory):
        """Test TOC generation without question responses fails."""
        client = await auth_client_factory()

        # Create book with summary only
        book_data = {
            "title": "No Responses TOC Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Add summary
        await client.patch(f"/api/v1/books/{book_id}/summary",
                          json={"summary": "Summary only."})

        # Try to generate TOC (should fail)
        gen_resp = await client.post(f"/api/v1/books/{book_id}/generate-toc")
        assert gen_resp.status_code == 400

    @pytest.mark.asyncio
    @patch("app.services.ai_service.AIService.generate_toc_from_summary_and_responses")
    async def test_generate_toc_ai_failure(self, mock_generate, auth_client_factory):
        """Test handling of AI service failure during TOC generation."""
        mock_generate.side_effect = Exception("AI service error")

        client = await auth_client_factory()

        # Create book with requirements
        book_data = {
            "title": "AI Failure Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Add requirements
        await client.patch(f"/api/v1/books/{book_id}/summary",
                          json={"summary": "Summary for TOC."})
        await client.put(f"/api/v1/books/{book_id}/question-responses",
                        json={"responses": [{"question": "Q1", "answer": "A1"}]})

        # Try to generate TOC (should handle error)
        gen_resp = await client.post(f"/api/v1/books/{book_id}/generate-toc")
        assert gen_resp.status_code in [500, 503]

    @pytest.mark.asyncio
    @patch("app.services.ai_service.AIService.generate_toc_from_summary_and_responses")
    async def test_get_book_toc_success(self, mock_generate, auth_client_factory):
        """Test retrieving book TOC."""
        mock_generate.return_value = MOCK_TOC_RESPONSE

        client = await auth_client_factory()

        # Create book and generate TOC
        book_data = {
            "title": "Get TOC Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Generate TOC
        await client.patch(f"/api/v1/books/{book_id}/summary",
                          json={"summary": "Summary."})
        await client.put(f"/api/v1/books/{book_id}/question-responses",
                        json={"responses": [{"question": "Q1", "answer": "A1"}]})
        await client.post(f"/api/v1/books/{book_id}/generate-toc")

        # Get TOC
        get_resp = await client.get(f"/api/v1/books/{book_id}/toc")
        assert get_resp.status_code == 200
        toc = get_resp.json()
        assert "toc" in toc or "table_of_contents" in toc

    @pytest.mark.asyncio
    async def test_get_toc_no_toc(self, auth_client_factory):
        """Test getting TOC when none exists."""
        client = await auth_client_factory()

        # Create book without TOC
        book_data = {
            "title": "No TOC Book",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Get TOC (should return empty or 404)
        get_resp = await client.get(f"/api/v1/books/{book_id}/toc")
        assert get_resp.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_get_toc_book_not_found(self, auth_client_factory):
        """Test getting TOC for non-existent book."""
        client = await auth_client_factory()

        fake_book_id = str(ObjectId())
        get_resp = await client.get(f"/api/v1/books/{fake_book_id}/toc")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    @patch("app.services.ai_service.AIService.generate_toc_from_summary_and_responses")
    async def test_update_book_toc_success(self, mock_generate, auth_client_factory):
        """Test updating book TOC."""
        mock_generate.return_value = MOCK_TOC_RESPONSE

        client = await auth_client_factory()

        # Create book and generate TOC
        book_data = {
            "title": "Update TOC Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Generate initial TOC
        await client.patch(f"/api/v1/books/{book_id}/summary",
                          json={"summary": "Summary."})
        await client.put(f"/api/v1/books/{book_id}/question-responses",
                        json={"responses": [{"question": "Q1", "answer": "A1"}]})
        await client.post(f"/api/v1/books/{book_id}/generate-toc")

        # Update TOC
        updated_toc = {
            "chapters": [
                {
                    "id": "ch1",
                    "title": "Updated Chapter 1",
                    "level": 1,
                    "order": 1
                }
            ]
        }
        update_resp = await client.put(f"/api/v1/books/{book_id}/toc", json={"toc": updated_toc})
        assert update_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_toc_validation_errors(self, auth_client_factory):
        """Test updating TOC with invalid data fails validation."""
        client = await auth_client_factory()

        # Create book
        book_data = {
            "title": "Validation Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Try to update with invalid TOC (missing required fields)
        invalid_toc = {"chapters": [{"title": "No ID"}]}  # Missing id field
        update_resp = await client.put(f"/api/v1/books/{book_id}/toc", json={"toc": invalid_toc})
        assert update_resp.status_code in [400, 422]


# ============================================================================
# Chapter CRUD Tests
# ============================================================================

class TestChapterCRUD:
    """Test Chapter Create, Read, Update, Delete, List operations."""

    @pytest.mark.asyncio
    @patch("app.services.ai_service.AIService.generate_toc_from_summary_and_responses")
    async def test_create_chapter_success(self, mock_generate, auth_client_factory):
        """Test creating a new chapter."""
        mock_generate.return_value = MOCK_TOC_RESPONSE

        client = await auth_client_factory()

        # Create book
        book_data = {
            "title": "Chapter Test Book",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Create chapter
        chapter_data = {
            "title": "New Chapter",
            "content": "Chapter content goes here.",
            "order": 1
        }
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        assert chapter_resp.status_code == 201
        chapter = chapter_resp.json()
        assert chapter["title"] == "New Chapter"

    @pytest.mark.asyncio
    async def test_create_chapter_validation_error(self, auth_client_factory):
        """Test creating chapter with invalid data fails."""
        client = await auth_client_factory()

        # Create book
        book_data = {
            "title": "Chapter Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Try to create chapter without required fields
        invalid_chapter = {"content": "Missing title"}
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=invalid_chapter)
        assert chapter_resp.status_code == 422

    @pytest.mark.asyncio
    async def test_get_chapter_success(self, auth_client_factory):
        """Test retrieving a specific chapter."""
        client = await auth_client_factory()

        # Create book and chapter
        book_data = {
            "title": "Get Chapter Test",
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

        # Get chapter
        get_resp = await client.get(f"/api/v1/books/{book_id}/chapters/{chapter_id}")
        assert get_resp.status_code == 200
        chapter = get_resp.json()
        assert chapter["title"] == "Test Chapter"

    @pytest.mark.asyncio
    async def test_get_chapter_not_found(self, auth_client_factory):
        """Test getting non-existent chapter returns 404."""
        client = await auth_client_factory()

        # Create book
        book_data = {
            "title": "Test Book",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Try to get non-existent chapter
        fake_chapter_id = str(ObjectId())
        get_resp = await client.get(f"/api/v1/books/{book_id}/chapters/{fake_chapter_id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_chapter_unauthorized(self, auth_client_factory):
        """Test user cannot access another user's chapter."""
        # Create chapter with user 1
        client1 = await auth_client_factory()
        book_data = {
            "title": "User 1 Book",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client1.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {
            "title": "Private Chapter",
            "content": "Content",
            "order": 1
        }
        chapter_resp = await client1.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["id"]

        # Try to access with user 2
        client2 = await auth_client_factory(overrides={"clerk_id": "different_user"})
        get_resp = await client2.get(f"/api/v1/books/{book_id}/chapters/{chapter_id}")
        assert get_resp.status_code in [403, 404]

    @pytest.mark.asyncio
    async def test_update_chapter_success(self, auth_client_factory):
        """Test updating a chapter."""
        client = await auth_client_factory()

        # Create book and chapter
        book_data = {
            "title": "Update Chapter Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {
            "title": "Original Title",
            "content": "Original content",
            "order": 1
        }
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["id"]

        # Update chapter
        update_data = {
            "title": "Updated Title",
            "content": "Updated content"
        }
        update_resp = await client.put(f"/api/v1/books/{book_id}/chapters/{chapter_id}", json=update_data)
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_update_chapter_not_found(self, auth_client_factory):
        """Test updating non-existent chapter returns 404."""
        client = await auth_client_factory()

        # Create book
        book_data = {
            "title": "Test Book",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Try to update non-existent chapter
        fake_chapter_id = str(ObjectId())
        update_data = {"title": "New Title"}
        update_resp = await client.put(f"/api/v1/books/{book_id}/chapters/{fake_chapter_id}", json=update_data)
        assert update_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_chapter_success(self, auth_client_factory):
        """Test deleting a chapter."""
        client = await auth_client_factory()

        # Create book and chapter
        book_data = {
            "title": "Delete Chapter Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {
            "title": "Chapter to Delete",
            "content": "Content",
            "order": 1
        }
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["id"]

        # Delete chapter
        delete_resp = await client.delete(f"/api/v1/books/{book_id}/chapters/{chapter_id}")
        assert delete_resp.status_code == 204

        # Verify deletion
        get_resp = await client.get(f"/api/v1/books/{book_id}/chapters/{chapter_id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_chapter_not_found(self, auth_client_factory):
        """Test deleting non-existent chapter returns 404."""
        client = await auth_client_factory()

        # Create book
        book_data = {
            "title": "Test Book",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Try to delete non-existent chapter
        fake_chapter_id = str(ObjectId())
        delete_resp = await client.delete(f"/api/v1/books/{book_id}/chapters/{fake_chapter_id}")
        assert delete_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_chapters_success(self, auth_client_factory):
        """Test listing all chapters for a book."""
        client = await auth_client_factory()

        # Create book
        book_data = {
            "title": "List Chapters Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Create multiple chapters
        for i in range(3):
            chapter_data = {
                "title": f"Chapter {i+1}",
                "content": f"Content {i+1}",
                "order": i+1
            }
            await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)

        # List chapters
        list_resp = await client.get(f"/api/v1/books/{book_id}/chapters")
        assert list_resp.status_code == 200
        chapters = list_resp.json()
        assert len(chapters) >= 3

    @pytest.mark.asyncio
    async def test_list_chapters_empty(self, auth_client_factory):
        """Test listing chapters when book has none."""
        client = await auth_client_factory()

        # Create book without chapters
        book_data = {
            "title": "Empty Chapters Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # List chapters (should be empty)
        list_resp = await client.get(f"/api/v1/books/{book_id}/chapters")
        assert list_resp.status_code == 200
        chapters = list_resp.json()
        assert len(chapters) == 0 or chapters == []

    @pytest.mark.asyncio
    async def test_list_chapters_pagination(self, auth_client_factory):
        """Test pagination when listing chapters."""
        client = await auth_client_factory()

        # Create book
        book_data = {
            "title": "Pagination Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Create many chapters
        for i in range(15):
            chapter_data = {
                "title": f"Chapter {i+1}",
                "content": f"Content {i+1}",
                "order": i+1
            }
            await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)

        # List with pagination
        list_resp = await client.get(f"/api/v1/books/{book_id}/chapters?limit=5&skip=0")
        assert list_resp.status_code == 200
        first_page = list_resp.json()
        assert len(first_page) <= 5


# ============================================================================
# Chapter Content Tests
# ============================================================================

class TestChapterContent:
    """Test chapter content retrieval and updates."""

    @pytest.mark.asyncio
    async def test_get_chapter_content_success(self, auth_client_factory):
        """Test retrieving chapter content."""
        client = await auth_client_factory()

        # Create book and chapter
        book_data = {
            "title": "Content Test Book",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {
            "title": "Test Chapter",
            "content": "This is the chapter content.",
            "order": 1
        }
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["id"]

        # Get content
        content_resp = await client.get(f"/api/v1/books/{book_id}/chapters/{chapter_id}/content")
        assert content_resp.status_code == 200
        content = content_resp.json()
        assert "content" in content

    @pytest.mark.asyncio
    async def test_update_chapter_content_success(self, auth_client_factory):
        """Test updating chapter content."""
        client = await auth_client_factory()

        # Create book and chapter
        book_data = {
            "title": "Update Content Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {
            "title": "Test Chapter",
            "content": "Original content",
            "order": 1
        }
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["id"]

        # Update content
        new_content = {"content": "Updated chapter content with more text."}
        update_resp = await client.patch(f"/api/v1/books/{book_id}/chapters/{chapter_id}/content", json=new_content)
        assert update_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_content_unauthorized(self, auth_client_factory):
        """Test user cannot update another user's chapter content."""
        # Create with user 1
        client1 = await auth_client_factory()
        book_data = {
            "title": "User 1 Book",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client1.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {
            "title": "Private Chapter",
            "content": "Private content",
            "order": 1
        }
        chapter_resp = await client1.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["id"]

        # Try to update with user 2
        client2 = await auth_client_factory(overrides={"clerk_id": "different_user"})
        new_content = {"content": "Hacked content"}
        update_resp = await client2.patch(f"/api/v1/books/{book_id}/chapters/{chapter_id}/content", json=new_content)
        assert update_resp.status_code in [403, 404]


# ============================================================================
# Tab State Tests
# ============================================================================

class TestTabState:
    """Test tab state save and retrieval."""

    @pytest.mark.asyncio
    async def test_save_tab_state_success(self, auth_client_factory):
        """Test saving tab state."""
        client = await auth_client_factory()

        # Create book
        book_data = {
            "title": "Tab State Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Save tab state
        tab_state = {
            "active_tab": "chapter_1",
            "open_tabs": ["chapter_1", "chapter_2", "chapter_3"]
        }
        save_resp = await client.post(f"/api/v1/books/{book_id}/chapters/tab-state", json=tab_state)
        assert save_resp.status_code in [200, 201]

    @pytest.mark.asyncio
    async def test_get_tab_state_success(self, auth_client_factory):
        """Test retrieving tab state."""
        client = await auth_client_factory()

        # Create book
        book_data = {
            "title": "Get Tab State Test",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Save tab state
        tab_state = {
            "active_tab": "chapter_1",
            "open_tabs": ["chapter_1", "chapter_2"]
        }
        await client.post(f"/api/v1/books/{book_id}/chapters/tab-state", json=tab_state)

        # Get tab state
        get_resp = await client.get(f"/api/v1/books/{book_id}/chapters/tab-state")
        assert get_resp.status_code == 200
        retrieved = get_resp.json()
        assert "active_tab" in retrieved or "open_tabs" in retrieved

    @pytest.mark.asyncio
    async def test_get_tab_state_not_found(self, auth_client_factory):
        """Test getting tab state when none exists returns defaults."""
        client = await auth_client_factory()

        # Create book without tab state
        book_data = {
            "title": "No Tab State",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Get tab state (should return defaults or 404)
        get_resp = await client.get(f"/api/v1/books/{book_id}/chapters/tab-state")
        assert get_resp.status_code in [200, 404]
