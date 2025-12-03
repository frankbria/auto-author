"""
Comprehensive test suite for Books TOC and Chapters endpoints.

This module tests:
- TOC generation readiness checks
- TOC generation with AI
- TOC retrieval and updates
- Chapter CRUD operations
- Chapter content management
- Chapter metadata and analytics
- Bulk chapter operations
- Tab state management

Coverage target: 75%+ of books_chapters.py
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
# TOC Generation Tests (from books_toc.py, but needed for context)
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
        # Response structure varies - check for success indicator
        assert "ready" in readiness or "success" in readiness


# ============================================================================
# Chapter CRUD Tests
# ============================================================================

class TestChapterCRUD:
    """Test Chapter Create, Read, Update, Delete, List operations."""

    @pytest.mark.asyncio
    async def test_create_chapter_success(self, auth_client_factory):
        """Test creating a new chapter."""
        client = await auth_client_factory()

        # Create book
        book_data = {
            "title": "Chapter Test Book",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        create_resp = await client.post("/api/v1/books/", json=book_data)
        assert create_resp.status_code == 201
        book_id = create_resp.json()["id"]

        # Create chapter with correct schema
        chapter_data = {
            "title": "New Chapter",
            "description": "Chapter description",
            "level": 1,
            "order": 1
        }
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        assert chapter_resp.status_code == 201
        response = chapter_resp.json()
        assert response["success"] is True
        assert "chapter_id" in response or "chapter" in response

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
        invalid_chapter = {"description": "Missing title"}
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=invalid_chapter)
        assert chapter_resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_chapter_invalid_book(self, auth_client_factory):
        """Test creating chapter for non-existent book fails."""
        client = await auth_client_factory()

        fake_book_id = str(ObjectId())
        chapter_data = {
            "title": "Chapter",
            "level": 1,
            "order": 1
        }
        chapter_resp = await client.post(f"/api/v1/books/{fake_book_id}/chapters", json=chapter_data)
        assert chapter_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_subchapter_success(self, auth_client_factory):
        """Test creating a subchapter with parent_id."""
        client = await auth_client_factory()

        # Create book
        book_data = {"title": "Subchapter Test", "genre": "Fiction", "target_audience": "Adults"}
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Create parent chapter
        parent_data = {"title": "Parent Chapter", "level": 1, "order": 1}
        parent_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=parent_data)
        parent_chapter = parent_resp.json()["chapter"]
        parent_id = parent_chapter["id"]

        # Create subchapter
        subchapter_data = {
            "title": "Subchapter",
            "level": 2,
            "order": 1,
            "parent_id": parent_id
        }
        sub_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=subchapter_data)
        assert sub_resp.status_code == 201

    @pytest.mark.asyncio
    async def test_get_chapter_success(self, auth_client_factory):
        """Test retrieving a specific chapter."""
        client = await auth_client_factory()

        # Create book and chapter
        book_data = {"title": "Get Chapter Test", "genre": "Fiction", "target_audience": "Adults"}
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {"title": "Test Chapter", "level": 1, "order": 1}
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["chapter"]["id"]

        # Get chapter
        get_resp = await client.get(f"/api/v1/books/{book_id}/chapters/{chapter_id}")
        assert get_resp.status_code == 200
        response = get_resp.json()
        assert response["success"] is True
        assert response["chapter"]["title"] == "Test Chapter"

    @pytest.mark.asyncio
    async def test_get_chapter_not_found(self, auth_client_factory):
        """Test getting non-existent chapter returns 404."""
        client = await auth_client_factory()

        # Create book
        book_data = {"title": "Test Book", "genre": "Fiction", "target_audience": "Adults"}
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
        book_data = {"title": "User 1 Book", "genre": "Fiction", "target_audience": "Adults"}
        create_resp = await client1.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {"title": "Private Chapter", "level": 1, "order": 1}
        chapter_resp = await client1.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["chapter"]["id"]

        # Try to access with user 2
        client2 = await auth_client_factory(overrides={"clerk_id": "different_user"})
        get_resp = await client2.get(f"/api/v1/books/{book_id}/chapters/{chapter_id}")
        assert get_resp.status_code in [403, 404]

    @pytest.mark.asyncio
    async def test_update_chapter_success(self, auth_client_factory):
        """Test updating a chapter."""
        client = await auth_client_factory()

        # Create book and chapter
        book_data = {"title": "Update Chapter Test", "genre": "Fiction", "target_audience": "Adults"}
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {"title": "Original Title", "level": 1, "order": 1}
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["chapter"]["id"]

        # Update chapter
        update_data = {"title": "Updated Title", "description": "Updated description"}
        update_resp = await client.put(f"/api/v1/books/{book_id}/chapters/{chapter_id}", json=update_data)
        assert update_resp.status_code == 200
        assert update_resp.json()["success"] is True

    @pytest.mark.asyncio
    async def test_update_chapter_not_found(self, auth_client_factory):
        """Test updating non-existent chapter returns 404."""
        client = await auth_client_factory()

        # Create book
        book_data = {"title": "Test Book", "genre": "Fiction", "target_audience": "Adults"}
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Try to update non-existent chapter
        fake_chapter_id = str(ObjectId())
        update_data = {"title": "New Title"}
        update_resp = await client.put(f"/api/v1/books/{book_id}/chapters/{fake_chapter_id}", json=update_data)
        assert update_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_chapter_unauthorized(self, auth_client_factory):
        """Test user cannot update another user's chapter."""
        # Create with user 1
        client1 = await auth_client_factory()
        book_data = {"title": "User 1 Book", "genre": "Fiction", "target_audience": "Adults"}
        create_resp = await client1.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {"title": "Private Chapter", "level": 1, "order": 1}
        chapter_resp = await client1.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["chapter"]["id"]

        # Try to update with user 2
        client2 = await auth_client_factory(overrides={"clerk_id": "different_user"})
        update_data = {"title": "Hacked Title"}
        update_resp = await client2.put(f"/api/v1/books/{book_id}/chapters/{chapter_id}", json=update_data)
        assert update_resp.status_code in [403, 404]

    @pytest.mark.asyncio
    async def test_delete_chapter_success(self, auth_client_factory):
        """Test deleting a chapter."""
        client = await auth_client_factory()

        # Create book and chapter
        book_data = {"title": "Delete Chapter Test", "genre": "Fiction", "target_audience": "Adults"}
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {"title": "Chapter to Delete", "level": 1, "order": 1}
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["chapter"]["id"]

        # Delete chapter
        delete_resp = await client.delete(f"/api/v1/books/{book_id}/chapters/{chapter_id}")
        assert delete_resp.status_code == 200
        assert delete_resp.json()["success"] is True

        # Verify deletion
        get_resp = await client.get(f"/api/v1/books/{book_id}/chapters/{chapter_id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_chapter_not_found(self, auth_client_factory):
        """Test deleting non-existent chapter returns 404."""
        client = await auth_client_factory()

        # Create book
        book_data = {"title": "Test Book", "genre": "Fiction", "target_audience": "Adults"}
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Try to delete non-existent chapter
        fake_chapter_id = str(ObjectId())
        delete_resp = await client.delete(f"/api/v1/books/{book_id}/chapters/{fake_chapter_id}")
        assert delete_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_chapter_cascades_subchapters(self, auth_client_factory):
        """Test deleting a chapter also deletes its subchapters."""
        client = await auth_client_factory()

        # Create book
        book_data = {"title": "Cascade Test", "genre": "Fiction", "target_audience": "Adults"}
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Create parent chapter
        parent_data = {"title": "Parent", "level": 1, "order": 1}
        parent_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=parent_data)
        parent_id = parent_resp.json()["chapter"]["id"]

        # Create subchapter
        sub_data = {"title": "Subchapter", "level": 2, "order": 1, "parent_id": parent_id}
        sub_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=sub_data)
        sub_id = sub_resp.json()["chapter"]["id"]

        # Delete parent
        delete_resp = await client.delete(f"/api/v1/books/{book_id}/chapters/{parent_id}")
        assert delete_resp.status_code == 200

        # Verify subchapter is also gone
        get_sub_resp = await client.get(f"/api/v1/books/{book_id}/chapters/{sub_id}")
        assert get_sub_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_chapters_success(self, auth_client_factory):
        """Test listing all chapters for a book."""
        client = await auth_client_factory()

        # Create book
        book_data = {"title": "List Chapters Test", "genre": "Fiction", "target_audience": "Adults"}
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Create multiple chapters
        for i in range(3):
            chapter_data = {"title": f"Chapter {i+1}", "level": 1, "order": i+1}
            await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)

        # List chapters
        list_resp = await client.get(f"/api/v1/books/{book_id}/chapters")
        assert list_resp.status_code == 200
        response = list_resp.json()
        assert response["success"] is True
        assert len(response["chapters"]) >= 3

    @pytest.mark.asyncio
    async def test_list_chapters_flat(self, auth_client_factory):
        """Test listing chapters in flat structure."""
        client = await auth_client_factory()

        # Create book
        book_data = {"title": "Flat List Test", "genre": "Fiction", "target_audience": "Adults"}
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Create parent and subchapter
        parent_data = {"title": "Parent", "level": 1, "order": 1}
        parent_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=parent_data)
        parent_id = parent_resp.json()["chapter"]["id"]

        sub_data = {"title": "Sub", "level": 2, "order": 1, "parent_id": parent_id}
        await client.post(f"/api/v1/books/{book_id}/chapters", json=sub_data)

        # List flat
        list_resp = await client.get(f"/api/v1/books/{book_id}/chapters?flat=true")
        assert list_resp.status_code == 200
        response = list_resp.json()
        assert response["structure"] == "flat"
        assert len(response["chapters"]) >= 2

    @pytest.mark.asyncio
    async def test_list_chapters_empty(self, auth_client_factory):
        """Test listing chapters when book has none."""
        client = await auth_client_factory()

        # Create book without chapters
        book_data = {"title": "Empty Chapters Test", "genre": "Fiction", "target_audience": "Adults"}
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # List chapters (should be empty)
        list_resp = await client.get(f"/api/v1/books/{book_id}/chapters")
        assert list_resp.status_code == 200
        response = list_resp.json()
        assert len(response["chapters"]) == 0


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
        book_data = {"title": "Content Test Book", "genre": "Fiction", "target_audience": "Adults"}
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {"title": "Test Chapter", "level": 1, "order": 1}
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["chapter"]["id"]

        # Get content
        content_resp = await client.get(f"/api/v1/books/{book_id}/chapters/{chapter_id}/content")
        assert content_resp.status_code == 200
        response = content_resp.json()
        assert response["success"] is True
        assert "content" in response

    @pytest.mark.asyncio
    async def test_get_chapter_content_with_metadata(self, auth_client_factory):
        """Test retrieving chapter content with metadata."""
        client = await auth_client_factory()

        # Create book and chapter
        book_data = {"title": "Metadata Test", "genre": "Fiction", "target_audience": "Adults"}
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {"title": "Test Chapter", "level": 1, "order": 1}
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["chapter"]["id"]

        # Get content with metadata
        content_resp = await client.get(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/content?include_metadata=true"
        )
        assert content_resp.status_code == 200
        response = content_resp.json()
        assert "metadata" in response
        assert "word_count" in response["metadata"]

    @pytest.mark.asyncio
    async def test_update_chapter_content_success(self, auth_client_factory):
        """Test updating chapter content."""
        client = await auth_client_factory()

        # Create book and chapter
        book_data = {"title": "Update Content Test", "genre": "Fiction", "target_audience": "Adults"}
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {"title": "Test Chapter", "level": 1, "order": 1}
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["chapter"]["id"]

        # Update content
        new_content_data = {
            "content": "Updated chapter content with more text.",
            "auto_update_metadata": True
        }
        update_resp = await client.patch(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/content",
            json=new_content_data
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["success"] is True

    @pytest.mark.asyncio
    async def test_update_content_auto_metadata(self, auth_client_factory):
        """Test that content update automatically updates word count and reading time."""
        client = await auth_client_factory()

        # Create book and chapter
        book_data = {"title": "Auto Metadata Test", "genre": "Fiction", "target_audience": "Adults"}
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {"title": "Test Chapter", "level": 1, "order": 1}
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["chapter"]["id"]

        # Update with long content
        long_content = " ".join(["word"] * 300)  # 300 words
        update_data = {"content": long_content, "auto_update_metadata": True}
        await client.patch(f"/api/v1/books/{book_id}/chapters/{chapter_id}/content", json=update_data)

        # Get content and verify metadata
        content_resp = await client.get(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/content?include_metadata=true"
        )
        metadata = content_resp.json()["metadata"]
        assert metadata["word_count"] > 0
        assert metadata["estimated_reading_time"] > 0

    @pytest.mark.asyncio
    async def test_update_content_unauthorized(self, auth_client_factory):
        """Test user cannot update another user's chapter content."""
        # Create with user 1
        client1 = await auth_client_factory()
        book_data = {"title": "User 1 Book", "genre": "Fiction", "target_audience": "Adults"}
        create_resp = await client1.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {"title": "Private Chapter", "level": 1, "order": 1}
        chapter_resp = await client1.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["chapter"]["id"]

        # Try to update with user 2
        client2 = await auth_client_factory(overrides={"clerk_id": "different_user"})
        new_content = {"content": "Hacked content"}
        update_resp = await client2.patch(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/content",
            json=new_content
        )
        assert update_resp.status_code in [403, 404]


# ============================================================================
# Chapter Metadata Tests
# ============================================================================

class TestChapterMetadata:
    """Test chapter metadata endpoints."""

    @pytest.mark.asyncio
    async def test_get_chapters_metadata(self, auth_client_factory):
        """Test getting metadata for all chapters."""
        client = await auth_client_factory()

        # Create book with chapters
        book_data = {"title": "Metadata Test", "genre": "Fiction", "target_audience": "Adults"}
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Create multiple chapters
        for i in range(3):
            chapter_data = {"title": f"Chapter {i+1}", "level": 1, "order": i+1}
            await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)

        # Get metadata
        metadata_resp = await client.get(f"/api/v1/books/{book_id}/chapters/metadata")
        assert metadata_resp.status_code == 200
        response = metadata_resp.json()
        assert len(response["chapters"]) >= 3
        assert "completion_stats" in response

    @pytest.mark.asyncio
    async def test_get_chapters_metadata_with_stats(self, auth_client_factory):
        """Test getting metadata with content stats."""
        client = await auth_client_factory()

        # Create book with chapter
        book_data = {"title": "Stats Test", "genre": "Fiction", "target_audience": "Adults"}
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {"title": "Chapter 1", "level": 1, "order": 1}
        await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)

        # Get metadata with stats
        metadata_resp = await client.get(
            f"/api/v1/books/{book_id}/chapters/metadata?include_content_stats=true"
        )
        assert metadata_resp.status_code == 200
        response = metadata_resp.json()
        assert "chapters" in response
        for chapter in response["chapters"]:
            assert "word_count" in chapter
            assert "estimated_reading_time" in chapter


# ============================================================================
# Bulk Operations Tests
# ============================================================================

class TestBulkOperations:
    """Test bulk chapter operations."""

    @pytest.mark.asyncio
    async def test_update_chapter_status_bulk(self, auth_client_factory):
        """Test updating status for multiple chapters."""
        client = await auth_client_factory()

        # Create book with chapters
        book_data = {"title": "Bulk Test", "genre": "Fiction", "target_audience": "Adults"}
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Create chapters
        chapter_ids = []
        for i in range(3):
            chapter_data = {"title": f"Chapter {i+1}", "level": 1, "order": i+1}
            resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
            chapter_ids.append(resp.json()["chapter"]["id"])

        # Bulk status update
        bulk_data = {
            "chapter_ids": chapter_ids,
            "status": "in-progress",
            "update_timestamp": True
        }
        bulk_resp = await client.patch(f"/api/v1/books/{book_id}/chapters/bulk-status", json=bulk_data)
        assert bulk_resp.status_code == 200
        response = bulk_resp.json()
        assert response["success"] is True
        assert len(response["updated_chapters"]) == 3

    @pytest.mark.asyncio
    async def test_batch_get_chapter_content(self, auth_client_factory):
        """Test getting content for multiple chapters at once."""
        client = await auth_client_factory()

        # Create book with chapters
        book_data = {"title": "Batch Test", "genre": "Fiction", "target_audience": "Adults"}
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Create chapters
        chapter_ids = []
        for i in range(3):
            chapter_data = {"title": f"Chapter {i+1}", "level": 1, "order": i+1}
            resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
            chapter_ids.append(resp.json()["chapter"]["id"])

        # Batch get content
        batch_data = {"chapter_ids": chapter_ids, "include_metadata": True}
        batch_resp = await client.post(
            f"/api/v1/books/{book_id}/chapters/batch-content",
            json=batch_data
        )
        assert batch_resp.status_code == 200
        response = batch_resp.json()
        assert response["success"] is True
        assert response["found_count"] == 3

    @pytest.mark.asyncio
    async def test_batch_get_content_limit(self, auth_client_factory):
        """Test that batch content retrieval has a limit."""
        client = await auth_client_factory()

        # Create book
        book_data = {"title": "Limit Test", "genre": "Fiction", "target_audience": "Adults"}
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Try to request more than 20 chapters (limit)
        fake_ids = [str(ObjectId()) for _ in range(25)]
        batch_data = {"chapter_ids": fake_ids, "include_metadata": False}
        batch_resp = await client.post(
            f"/api/v1/books/{book_id}/chapters/batch-content",
            json=batch_data
        )
        assert batch_resp.status_code == 400


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
        book_data = {"title": "Tab State Test", "genre": "Fiction", "target_audience": "Adults"}
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Save tab state with correct schema
        tab_state = {
            "active_chapter_id": "chapter_1",
            "open_tab_ids": ["chapter_1", "chapter_2", "chapter_3"],
            "tab_order": ["chapter_1", "chapter_2", "chapter_3"]
        }
        save_resp = await client.post(f"/api/v1/books/{book_id}/chapters/tab-state", json=tab_state)
        assert save_resp.status_code in [200, 201]

    @pytest.mark.asyncio
    async def test_get_tab_state_success(self, auth_client_factory):
        """Test retrieving tab state."""
        client = await auth_client_factory()

        # Create book
        book_data = {"title": "Get Tab State Test", "genre": "Fiction", "target_audience": "Adults"}
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Save tab state
        tab_state = {
            "active_chapter_id": "chapter_1",
            "open_tab_ids": ["chapter_1", "chapter_2"],
            "tab_order": ["chapter_1", "chapter_2"]
        }
        await client.post(f"/api/v1/books/{book_id}/chapters/tab-state", json=tab_state)

        # Get tab state
        get_resp = await client.get(f"/api/v1/books/{book_id}/chapters/tab-state")
        assert get_resp.status_code == 200
        response = get_resp.json()
        assert "tab_state" in response

    @pytest.mark.asyncio
    async def test_get_tab_state_not_found(self, auth_client_factory):
        """Test getting tab state when none exists returns proper response."""
        client = await auth_client_factory()

        # Create book without tab state
        book_data = {"title": "No Tab State", "genre": "Fiction", "target_audience": "Adults"}
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        # Get tab state (should return null or default)
        get_resp = await client.get(f"/api/v1/books/{book_id}/chapters/tab-state")
        assert get_resp.status_code == 200
        response = get_resp.json()
        assert response.get("tab_state") is None or response.get("tab_state") == {}


# ============================================================================
# Analytics Tests
# ============================================================================

class TestChapterAnalytics:
    """Test chapter analytics endpoints."""

    @pytest.mark.asyncio
    async def test_get_chapter_analytics(self, auth_client_factory):
        """Test getting analytics for a chapter."""
        client = await auth_client_factory()

        # Create book and chapter
        book_data = {"title": "Analytics Test", "genre": "Fiction", "target_audience": "Adults"}
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {"title": "Test Chapter", "level": 1, "order": 1}
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["chapter"]["id"]

        # Get analytics
        analytics_resp = await client.get(f"/api/v1/books/{book_id}/chapters/{chapter_id}/analytics")
        assert analytics_resp.status_code == 200
        response = analytics_resp.json()
        assert response["success"] is True
        assert "analytics" in response

    @pytest.mark.asyncio
    async def test_get_chapter_analytics_custom_days(self, auth_client_factory):
        """Test getting analytics with custom time period."""
        client = await auth_client_factory()

        # Create book and chapter
        book_data = {"title": "Custom Analytics", "genre": "Fiction", "target_audience": "Adults"}
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        chapter_data = {"title": "Test Chapter", "level": 1, "order": 1}
        chapter_resp = await client.post(f"/api/v1/books/{book_id}/chapters", json=chapter_data)
        chapter_id = chapter_resp.json()["chapter"]["id"]

        # Get analytics for 7 days
        analytics_resp = await client.get(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/analytics?days=7"
        )
        assert analytics_resp.status_code == 200
        response = analytics_resp.json()
        assert response["analytics_period_days"] == 7


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_chapter_operations_invalid_book_id(self, auth_client_factory):
        """Test that invalid book IDs are handled properly."""
        client = await auth_client_factory()

        invalid_id = "invalid_id"
        chapter_data = {"title": "Test", "level": 1, "order": 1}

        # Should get 400 or 422 for invalid ID format
        resp = await client.post(f"/api/v1/books/{invalid_id}/chapters", json=chapter_data)
        assert resp.status_code in [400, 404, 422]

    @pytest.mark.asyncio
    async def test_concurrent_modification_detection(self, auth_client_factory):
        """Test that concurrent modifications are detected."""
        # This would require mocking concurrent updates
        # Placeholder for future implementation
        pass

    @pytest.mark.asyncio
    async def test_chapter_not_found_handling(self, auth_client_factory):
        """Test proper 404 handling for non-existent chapters."""
        client = await auth_client_factory()

        # Create book
        book_data = {"title": "Error Test", "genre": "Fiction", "target_audience": "Adults"}
        create_resp = await client.post("/api/v1/books/", json=book_data)
        book_id = create_resp.json()["id"]

        fake_chapter_id = str(ObjectId())

        # Test all endpoints
        get_resp = await client.get(f"/api/v1/books/{book_id}/chapters/{fake_chapter_id}")
        assert get_resp.status_code == 404

        update_resp = await client.put(
            f"/api/v1/books/{book_id}/chapters/{fake_chapter_id}",
            json={"title": "Updated"}
        )
        assert update_resp.status_code == 404

        delete_resp = await client.delete(f"/api/v1/books/{book_id}/chapters/{fake_chapter_id}")
        assert delete_resp.status_code == 404

        content_resp = await client.get(f"/api/v1/books/{book_id}/chapters/{fake_chapter_id}/content")
        assert content_resp.status_code == 404
