import pytest
import pytest_asyncio
from httpx import AsyncClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from fastapi import HTTPException, status
from app.core import security

pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_read_users_me(auth_client_factory, test_user):
    """
    Test that the /users/me endpoint returns the current user's information
    when properly authenticated.
    """
    client = await auth_client_factory()
    response = await client.get("/api/v1/users/me")

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user["email"]
    assert data["auth_id"] == test_user["auth_id"]


def test_missing_session_cookie(client, monkeypatch):
    """
    Test that the /users/me endpoint returns a 401 error when no session cookie is provided.

    With cookie-based authentication (better-auth), authentication is via httpOnly session cookies.
    When no valid session cookie is present, the endpoint returns 401 Unauthorized.
    """
    # CRITICAL: Disable BYPASS_AUTH to test actual session verification
    from app.core.config import settings
    monkeypatch.setattr(settings, "BYPASS_AUTH", False)

    response = client.get("/api/v1/users/me")

    # Should return 401 Unauthorized when no session cookie is provided
    assert response.status_code == 401
    assert "detail" in response.json()
    # Cookie-based auth returns "Not authenticated. Please sign in." message
    assert "not authenticated" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_invalid_session_cookie(auth_client_factory, monkeypatch):
    """
    Test that the /users/me endpoint returns a 401 error when an invalid session cookie is provided.

    With cookie-based authentication (better-auth), session validation happens via MongoDB lookup.
    When the session cookie doesn't correspond to a valid session, the endpoint returns 401.
    """
    # CRITICAL: Disable BYPASS_AUTH to test actual session verification
    from app.core.config import settings
    monkeypatch.setattr(settings, "BYPASS_AUTH", False)

    # Create client without auth (no valid session)
    client = await auth_client_factory(auth=False)

    # Set an invalid session cookie
    client.cookies.set("better-auth.session_token", "invalid-session-token")

    response = await client.get("/api/v1/users/me")

    # Should return 401 Unauthorized
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    body = response.json()
    assert "detail" in body
    # Cookie-based auth returns "Not authenticated" message
    assert "not authenticated" in body["detail"].lower()
