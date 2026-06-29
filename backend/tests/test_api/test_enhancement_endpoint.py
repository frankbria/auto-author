"""Integration tests for the content-enhancement endpoint (issue #57)."""
import pytest
from unittest.mock import AsyncMock, patch

MOCK_BOOK = {
    "_id": "test_book_id",
    "owner_id": "test-auth-id-123",
    "title": "Test Book",
    "table_of_contents": {"chapters": [{"id": "ch1", "title": "Chapter 1"}]},
}

URL = "/api/v1/books/test_book_id/chapters/ch1/enhance-text"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "etype,label",
    [
        ("clarity", "Clarity"),
        ("grammar", "Grammar"),
        ("tone", "Tone"),
        ("vocabulary", "Vocabulary"),
    ],
)
async def test_enhance_success_each_type(auth_client_factory, etype, label):
    client = await auth_client_factory()
    mock_result = {
        "success": True,
        "enhanced": "An improved rendition of the text.",
        "metadata": {
            "enhancement_type": etype,
            "enhancement_label": label,
            "original_word_count": 5,
            "enhanced_word_count": 6,
            "model_used": "gpt-4",
            "generated_at": "2026-06-28 10:00:00",
        },
    }
    with patch("app.api.endpoints.books.get_book_by_id", AsyncMock(return_value=MOCK_BOOK)):
        with patch("app.api.endpoints.books.ai_service.enhance_text",
                   AsyncMock(return_value=mock_result)):
            response = await client.post(
                URL, json={"content": "The cat sat there.", "enhancement_type": etype}
            )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["enhanced"] == "An improved rendition of the text."
    assert body["metadata"]["enhancement_label"] == label


@pytest.mark.asyncio
async def test_enhance_requires_content(auth_client_factory):
    client = await auth_client_factory()
    with patch("app.api.endpoints.books.get_book_by_id", AsyncMock(return_value=MOCK_BOOK)):
        response = await client.post(URL, json={"content": "  ", "enhancement_type": "grammar"})
    assert response.status_code == 400
    assert "required" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_enhance_rejects_invalid_type(auth_client_factory):
    client = await auth_client_factory()
    with patch("app.api.endpoints.books.get_book_by_id", AsyncMock(return_value=MOCK_BOOK)):
        response = await client.post(URL, json={"content": "Hello there.", "enhancement_type": "seo"})
    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_enhance_book_not_found_returns_404(auth_client_factory):
    client = await auth_client_factory()
    with patch("app.api.endpoints.books.get_book_by_id", AsyncMock(return_value=None)):
        response = await client.post(
            URL, json={"content": "Some text.", "enhancement_type": "clarity"}
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_enhance_chapter_not_found_returns_404(auth_client_factory):
    """An owned book but a missing chapter id 404s before calling the AI."""
    client = await auth_client_factory()
    bad_url = "/api/v1/books/test_book_id/chapters/nope/enhance-text"
    with patch("app.api.endpoints.books.get_book_by_id", AsyncMock(return_value=MOCK_BOOK)):
        with patch("app.api.endpoints.books.ai_service.enhance_text",
                   AsyncMock()) as enhance:
            response = await client.post(
                bad_url, json={"content": "Some text.", "enhancement_type": "clarity"}
            )
    assert response.status_code == 404
    enhance.assert_not_called()


@pytest.mark.asyncio
async def test_enhance_ai_failure_returns_503(auth_client_factory):
    client = await auth_client_factory()
    mock_result = {"success": False, "error": "AI service unavailable", "enhanced": "", "metadata": {}}
    with patch("app.api.endpoints.books.get_book_by_id", AsyncMock(return_value=MOCK_BOOK)):
        with patch("app.api.endpoints.books.ai_service.enhance_text",
                   AsyncMock(return_value=mock_result)):
            response = await client.post(
                URL, json={"content": "Some text.", "enhancement_type": "tone"}
            )
    assert response.status_code == 503
    assert "Failed to enhance" in response.json()["detail"]


@pytest.mark.asyncio
async def test_enhance_rejects_other_users_book(auth_client_factory):
    client = await auth_client_factory()
    other_book = {**MOCK_BOOK, "owner_id": "someone-else"}
    with patch("app.api.endpoints.books.get_book_by_id", AsyncMock(return_value=other_book)):
        response = await client.post(
            URL, json={"content": "Some text.", "enhancement_type": "vocabulary"}
        )
    assert response.status_code == 403
