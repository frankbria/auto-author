import pytest, pytest_asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from fastapi import HTTPException, status
from app.core import security


def test_read_users_me(auth_client_factory, test_user):
    """
    Test that the /users/me endpoint returns the current user's information
    when properly authenticated.
    """
    # The auth_mock fixture handles mocking the JWT verification and user retrieval
    # The auth_headers fixture provides the Authorization header

    client = auth_client_factory()
    response = client.get("/api/v1/users/me")
    print(response.json())

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user["email"]
    assert data["clerk_id"] == test_user["clerk_id"]


def test_missing_token(client: TestClient):
    """
    Test that the /users/me endpoint returns a 403 error when no token is provided
    """
    # Don't provide any authorization headers
    response = client.get("/api/v1/users/me")

    # FastAPI's HTTPBearer returns 403 Forbidden when no token is provided
    assert response.status_code == 403
    assert "detail" in response.json()


def test_invalid_token(auth_client_factory, invalid_jwt_token, monkeypatch):
    """
    Test that the /users/me endpoint returns a 401 error when an invalid token is provided
    """

    # 1) Force verify_jwt_token to blow up with an HTTPException(401)
    def fail_verify(token: str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    monkeypatch.setattr(security, "verify_jwt_token", fail_verify)

    # 2) Set up the security module to reject the token
    # Provide headers with the test token
    headers = {"Authorization": f"Bearer {invalid_jwt_token}"}
    client = auth_client_factory(auth=False)
    client.headers.update(headers)
    response = client.get("/api/v1/users/me")

    # Should return 401 Unauthorized
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    body = response.json()
    assert "detail" in body
    assert "invalid authentication credentials" in body["detail"].lower()
