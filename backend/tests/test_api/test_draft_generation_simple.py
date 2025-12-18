"""Test the AI draft generation endpoint - simplified version"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_generate_chapter_draft_with_mock_book(auth_client_factory):
    """Test successful draft generation with mocked book operations"""
    # Create client
    client = await auth_client_factory()

    # Mock the book and chapter retrieval to bypass transaction issues
    mock_book = {
        "_id": "test_book_id",
        "owner_id": "test-auth-id-123",
        "title": "Test Book",
        "table_of_contents": {
            "chapters": [
                {
                    "id": "ch1",
                    "title": "Introduction to Testing",
                    "description": "Learn the basics of testing",
                    "level": 1,
                    "order": 1,
                    "subchapters": []
                }
            ],
            "total_chapters": 1,
            "version": 1
        }
    }

    # Mock the AI service result
    mock_ai_result = {
        "success": True,
        "draft": "# Introduction to Testing\n\nTesting is crucial for software quality...",
        "metadata": {
            "word_count": 150,
            "estimated_reading_time": 1,
            "generated_at": "2025-01-15 10:00:00",
            "model_used": "gpt-4",
            "writing_style": "educational",
            "target_length": 2000,
            "actual_length": 150
        },
        "suggestions": ["Add more examples", "Consider breaking into sections"]
    }

    with patch('app.api.endpoints.books.get_book_by_id', AsyncMock(return_value=mock_book)):
        with patch('app.api.endpoints.books.ai_service.generate_chapter_draft',
                   AsyncMock(return_value=mock_ai_result)):
            # Generate draft
            draft_data = {
                "question_responses": [
                    {
                        "question": "What is the main purpose of this chapter?",
                        "answer": "To introduce developers to testing concepts"
                    },
                    {
                        "question": "What key points should be covered?",
                        "answer": "Unit tests, integration tests, and test-driven development"
                    }
                ],
                "writing_style": "educational",
                "target_length": 2000
            }

            response = await client.post(
                f"/api/v1/books/test_book_id/chapters/ch1/generate-draft",
                json=draft_data
            )

            assert response.status_code == 200
            result = response.json()

            assert result["success"] is True
            assert result["book_id"] == "test_book_id"
            assert result["chapter_id"] == "ch1"
            assert "Introduction to Testing" in result["draft"]
            assert result["metadata"]["word_count"] == 150
            assert len(result["suggestions"]) == 2


@pytest.mark.asyncio
async def test_generate_draft_validates_responses(auth_client_factory):
    """Test that draft generation validates question responses"""
    client = await auth_client_factory()

    mock_book = {
        "_id": "test_book_id",
        "owner_id": "test-auth-id-123",
        "title": "Test Book",
        "table_of_contents": {
            "chapters": [{"id": "ch1", "title": "Chapter 1"}]
        }
    }

    with patch('app.api.endpoints.books.get_book_by_id', AsyncMock(return_value=mock_book)):
        # Try with empty responses
        response = await client.post(
            "/api/v1/books/test_book_id/chapters/ch1/generate-draft",
            json={"question_responses": []}
        )

        assert response.status_code == 400
        assert "Question responses are required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_generate_draft_handles_ai_errors(auth_client_factory):
    """Test draft generation handles AI service errors gracefully"""
    client = await auth_client_factory()

    mock_book = {
        "_id": "test_book_id",
        "owner_id": "test-auth-id-123",
        "title": "Test Book",
        "table_of_contents": {
            "chapters": [{"id": "ch1", "title": "Chapter 1"}]
        }
    }

    # Mock AI service to raise an error
    with patch('app.api.endpoints.books.get_book_by_id', AsyncMock(return_value=mock_book)):
        with patch('app.api.endpoints.books.ai_service.generate_chapter_draft',
                   AsyncMock(side_effect=Exception("AI service unavailable"))):

            response = await client.post(
                "/api/v1/books/test_book_id/chapters/ch1/generate-draft",
                json={
                    "question_responses": [
                        {"question": "Q", "answer": "A"}
                    ]
                }
            )

            assert response.status_code == 500
            assert "Error generating draft" in response.json()["detail"]
