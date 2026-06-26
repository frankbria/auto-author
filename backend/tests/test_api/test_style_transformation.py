"""Integration tests for the style-transformation endpoint (issue #58)."""
import pytest
from unittest.mock import AsyncMock, patch

MOCK_BOOK = {
    "_id": "test_book_id",
    "owner_id": "test-auth-id-123",
    "title": "Test Book",
    "table_of_contents": {"chapters": [{"id": "ch1", "title": "Chapter 1"}]},
}

URL = "/api/v1/books/test_book_id/chapters/ch1/transform-style"


@pytest.mark.asyncio
async def test_transform_style_success(auth_client_factory):
    client = await auth_client_factory()
    mock_result = {
        "success": True,
        "transformed": "A polished, professional rendition of the text.",
        "metadata": {
            "target_style": "professional",
            "style_label": "Professional",
            "original_word_count": 5,
            "transformed_word_count": 7,
            "model_used": "gpt-4",
            "generated_at": "2026-06-25 10:00:00",
        },
    }
    with patch("app.api.endpoints.books.get_book_by_id", AsyncMock(return_value=MOCK_BOOK)):
        with patch("app.api.endpoints.books.ai_service.transform_text_style",
                   AsyncMock(return_value=mock_result)):
            response = await client.post(
                URL, json={"content": "The cat sat there.", "target_style": "professional"}
            )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["transformed"] == "A polished, professional rendition of the text."
    assert body["metadata"]["style_label"] == "Professional"


@pytest.mark.asyncio
async def test_transform_style_requires_content(auth_client_factory):
    client = await auth_client_factory()
    with patch("app.api.endpoints.books.get_book_by_id", AsyncMock(return_value=MOCK_BOOK)):
        response = await client.post(URL, json={"content": "  ", "target_style": "professional"})
    assert response.status_code == 400
    assert "required" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_transform_style_rejects_invalid_style(auth_client_factory):
    client = await auth_client_factory()
    with patch("app.api.endpoints.books.get_book_by_id", AsyncMock(return_value=MOCK_BOOK)):
        response = await client.post(URL, json={"content": "Hello there.", "target_style": "spicy"})
    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_transform_style_ai_failure_returns_503(auth_client_factory):
    client = await auth_client_factory()
    mock_result = {"success": False, "error": "AI service unavailable", "transformed": "", "metadata": {}}
    with patch("app.api.endpoints.books.get_book_by_id", AsyncMock(return_value=MOCK_BOOK)):
        with patch("app.api.endpoints.books.ai_service.transform_text_style",
                   AsyncMock(return_value=mock_result)):
            response = await client.post(
                URL, json={"content": "Some text.", "target_style": "academic"}
            )
    assert response.status_code == 503
    assert "Failed to transform style" in response.json()["detail"]


@pytest.mark.asyncio
async def test_transform_style_rejects_other_users_book(auth_client_factory):
    client = await auth_client_factory()
    other_book = {**MOCK_BOOK, "owner_id": "someone-else"}
    with patch("app.api.endpoints.books.get_book_by_id", AsyncMock(return_value=other_book)):
        response = await client.post(
            URL, json={"content": "Some text.", "target_style": "creative"}
        )
    assert response.status_code == 403
