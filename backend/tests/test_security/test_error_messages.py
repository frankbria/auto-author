"""
Security guard test: API error responses must not leak internal exception detail.

Regression guard for issue #87. Endpoint handlers previously embedded
`{str(e)}` in the HTTP error `detail`, exposing internal implementation
detail to clients. This test triggers a handled 500 and asserts the client
sees a generic message that does NOT contain the raised exception's text.
"""

from unittest.mock import patch, AsyncMock

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.security import get_current_user_from_session

SENTINEL = "INTERNAL_LEAK_SENTINEL_a1b2c3_db_connection_string"


@pytest.fixture
async def client():
    async def override_get_current_user():
        return {"auth_id": "test-user-123", "email": "t@example.com", "role": "user"}

    app.dependency_overrides[get_current_user_from_session] = override_get_current_user
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={"better-auth.session_token": "test-session-token"},
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_handled_500_returns_generic_detail(client):
    """A handled server error must return a generic detail, not the exception text."""
    with patch(
        "app.api.endpoints.books.get_books_by_user",
        AsyncMock(side_effect=Exception(SENTINEL)),
    ):
        resp = await client.get("/api/v1/books/")

    assert resp.status_code == 500
    body = resp.json()
    assert body["detail"] == "Failed to retrieve books"
    assert SENTINEL not in resp.text
    # The exception class name must not leak either.
    assert "type" not in body
