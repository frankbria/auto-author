"""Integration tests for the voice-transcription cleanup endpoint (issue #56)."""
import pytest
from unittest.mock import AsyncMock, patch

MOCK_BOOK = {
    "_id": "test_book_id",
    "owner_id": "test-auth-id-123",
    "title": "Test Book",
    "table_of_contents": {"chapters": [{"id": "ch1", "title": "Chapter 1"}]},
}

URL = "/api/v1/books/test_book_id/chapters/ch1/enhance-transcription"


@pytest.mark.asyncio
async def test_cleanup_success(auth_client_factory):
    client = await auth_client_factory()
    mock_result = {
        "success": True,
        "enhanced": "The cat sat on the mat.",
        "metadata": {
            "enhancement_type": "transcription",
            "enhancement_label": "Dictation Cleanup",
            "original_word_count": 9,
            "enhanced_word_count": 6,
            "model_used": "gpt-4",
            "generated_at": "2026-06-29 10:00:00",
        },
    }
    with patch("app.api.endpoints.books.get_book_by_id", AsyncMock(return_value=MOCK_BOOK)):
        with patch("app.api.endpoints.books.ai_service.enhance_transcription",
                   AsyncMock(return_value=mock_result)):
            response = await client.post(
                URL, json={"content": "um so the cat you know sat on the mat"}
            )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["enhanced"] == "The cat sat on the mat."
    assert body["metadata"]["enhancement_label"] == "Dictation Cleanup"


@pytest.mark.asyncio
async def test_cleanup_requires_content(auth_client_factory):
    client = await auth_client_factory()
    with patch("app.api.endpoints.books.get_book_by_id", AsyncMock(return_value=MOCK_BOOK)):
        with patch("app.api.endpoints.books.ai_service.enhance_transcription",
                   AsyncMock()) as enhance:
            response = await client.post(URL, json={"content": "   "})
    assert response.status_code == 400
    assert "required" in response.json()["detail"].lower()
    enhance.assert_not_called()


@pytest.mark.asyncio
async def test_cleanup_book_not_found_returns_404(auth_client_factory):
    client = await auth_client_factory()
    with patch("app.api.endpoints.books.get_book_by_id", AsyncMock(return_value=None)):
        response = await client.post(URL, json={"content": "um hello there"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cleanup_chapter_not_found_returns_404(auth_client_factory):
    """An owned book but a missing chapter id 404s before calling the AI."""
    client = await auth_client_factory()
    bad_url = "/api/v1/books/test_book_id/chapters/nope/enhance-transcription"
    with patch("app.api.endpoints.books.get_book_by_id", AsyncMock(return_value=MOCK_BOOK)):
        with patch("app.api.endpoints.books.ai_service.enhance_transcription",
                   AsyncMock()) as enhance:
            response = await client.post(bad_url, json={"content": "um hello there"})
    assert response.status_code == 404
    enhance.assert_not_called()


@pytest.mark.asyncio
async def test_cleanup_ai_failure_returns_503(auth_client_factory):
    client = await auth_client_factory()
    mock_result = {"success": False, "error": "AI service unavailable", "enhanced": "", "metadata": {}}
    with patch("app.api.endpoints.books.get_book_by_id", AsyncMock(return_value=MOCK_BOOK)):
        with patch("app.api.endpoints.books.ai_service.enhance_transcription",
                   AsyncMock(return_value=mock_result)):
            response = await client.post(URL, json={"content": "um hello there"})
    assert response.status_code == 503
    assert "Failed to clean up" in response.json()["detail"]


@pytest.mark.asyncio
async def test_cleanup_rejects_other_users_book(auth_client_factory):
    client = await auth_client_factory()
    other_book = {**MOCK_BOOK, "owner_id": "someone-else"}
    with patch("app.api.endpoints.books.get_book_by_id", AsyncMock(return_value=other_book)):
        response = await client.post(URL, json={"content": "um hello there"})
    assert response.status_code == 403
