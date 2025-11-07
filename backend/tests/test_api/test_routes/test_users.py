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
    assert data["clerk_id"] == test_user["clerk_id"]


def test_missing_token(client, monkeypatch):
    """
    Test that the /users/me endpoint returns a 401 error when no token is provided
    """
    # CRITICAL: Disable BYPASS_AUTH to test actual token verification
    from app.core.config import settings
    monkeypatch.setattr(settings, "BYPASS_AUTH", False)

    response = client.get("/api/v1/users/me")

    # Should return 401 Unauthorized when no authentication is provided
    assert response.status_code == 401
    assert "detail" in response.json()
    assert "missing authentication credentials" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_invalid_token(auth_client_factory, invalid_jwt_token, monkeypatch):
    """
    Test that the /users/me endpoint returns a 401 error when an invalid token is provided
    """
    # CRITICAL: Disable BYPASS_AUTH to test actual token verification
    from app.core.config import settings
    monkeypatch.setattr(settings, "BYPASS_AUTH", False)

    # 1) Force verify_jwt_token to blow up with an HTTPException(401)
    def fail_verify(token: str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    monkeypatch.setattr(security, "verify_jwt_token", fail_verify)

    # 2) Set up the security module to reject the token
    # Provide headers with the test token
    client = await auth_client_factory(auth=False)
    client.headers.update({"Authorization": f"Bearer {invalid_jwt_token}"})
    response = await client.get("/api/v1/users/me")

    # Should return 401 Unauthorized
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    body = response.json()
    assert "detail" in body
    assert "invalid authentication credentials" in body["detail"].lower()
