import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from fastapi import HTTPException


@pytest.fixture
def mock_jwt_token():
    """
    Fixture that provides a mock JWT token for authentication
    """
    return "test_jwt_token"


@pytest.fixture
def auth_headers(mock_jwt_token):
    """
    Fixture that provides authentication headers
    """
    return {"Authorization": f"Bearer {mock_jwt_token}"}


@pytest.fixture
def mock_user_data():
    """
    Sample user data for testing
    """
    return {
        "id": "user_123",
        "clerk_id": "clerk_user_123",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "role": "user",
        "created_at": datetime.now(timezone.utc),  # Using proper UTC format
        "updated_at": datetime.now(timezone.utc),
        "books": [],
    }


@pytest.fixture
def auth_mock(mock_user_data):
    """
    Fixture that mocks the authentication functions
    """
    with patch("app.core.security.verify_jwt_token") as mock_verify_token, patch(
        "app.core.security.get_user_by_clerk_id", return_value=mock_user_data
    ) as mock_get_user:
        # Configure the token verification to return a valid payload with user ID
        mock_verify_token.return_value = {"sub": mock_user_data["clerk_id"]}
        yield {"verify_token": mock_verify_token, "get_user": mock_get_user}


@pytest.fixture
def authenticated_client(client: TestClient, auth_headers, auth_mock):
    """
    Fixture that provides an authenticated client for making API requests
    """

    # This fixture combines the client, auth_headers, and auth_mock
    # so you can simply use authenticated_client.get("/some/endpoint") in your tests
    class AuthenticatedClient:
        def __init__(self, client, headers):
            self.client = client
            self.headers = headers

        def get(self, url, **kwargs):
            if "headers" not in kwargs:
                kwargs["headers"] = self.headers
            return self.client.get(url, **kwargs)

        def post(self, url, **kwargs):
            if "headers" not in kwargs:
                kwargs["headers"] = self.headers
            return self.client.post(url, **kwargs)

        def put(self, url, **kwargs):
            if "headers" not in kwargs:
                kwargs["headers"] = self.headers
            return self.client.put(url, **kwargs)

        def delete(self, url, **kwargs):
            if "headers" not in kwargs:
                kwargs["headers"] = self.headers
            return self.client.delete(url, **kwargs)

    return AuthenticatedClient(client, auth_headers)


def test_read_users_me(client: TestClient, mock_user_data, auth_headers, auth_mock):
    """
    Test that the /users/me endpoint returns the current user's information
    when properly authenticated.
    """
    # The auth_mock fixture handles mocking the JWT verification and user retrieval
    # The auth_headers fixture provides the Authorization header

    response = client.get("/api/v1/users/me", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == mock_user_data["email"]
    assert data["clerk_id"] == mock_user_data["clerk_id"]


def test_missing_token(client: TestClient):
    """
    Test that the /users/me endpoint returns a 403 error when no token is provided
    """
    # Don't provide any authorization headers
    response = client.get("/api/v1/users/me")

    # FastAPI's HTTPBearer returns 403 Forbidden when no token is provided
    assert response.status_code == 403
    assert "detail" in response.json()


def test_invalid_token(client: TestClient, mock_jwt_token):
    """
    Test that the /users/me endpoint returns a 401 error when an invalid token is provided
    """
    # Set up the security module to reject the token
    with patch(
        "app.core.security.verify_jwt_token",
        side_effect=HTTPException(
            status_code=401, detail="Invalid authentication credentials"
        ),
    ):
        # Provide headers with the test token
        headers = {"Authorization": f"Bearer {mock_jwt_token}"}
        response = client.get("/api/v1/users/me", headers=headers)

        # Should return 401 Unauthorized
        assert response.status_code == 401
        assert "detail" in response.json()


@pytest.fixture
def mock_admin_user():
    """
    Sample admin user data for testing
    """
    return {
        "id": "admin_123",
        "clerk_id": "clerk_admin_123",
        "email": "admin@example.com",
        "first_name": "Admin",
        "last_name": "User",
        "role": "admin",
        "created_at": datetime.now(timezone.utc),  # Using proper UTC format
        "updated_at": datetime.now(timezone.utc),
        "books": [],
    }


@pytest.fixture
def admin_auth_mock(mock_admin_user):
    """
    Fixture that mocks the authentication functions for an admin user
    """
    with patch("app.core.security.verify_jwt_token") as mock_verify_token, patch(
        "app.core.security.get_user_by_clerk_id", return_value=mock_admin_user
    ) as mock_get_user:
        # Configure the token verification to return a valid payload with user ID
        mock_verify_token.return_value = {"sub": mock_admin_user["clerk_id"]}
        yield {"verify_token": mock_verify_token, "get_user": mock_get_user}


def test_admin_access(
    client: TestClient, mock_admin_user, auth_headers, admin_auth_mock
):
    """
    Test that an admin user can access protected endpoints
    """
    # Using the admin auth mock and auth headers
    response = client.get("/api/v1/users/me", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == mock_admin_user["email"]
    assert data["role"] == "admin"
    assert data["clerk_id"] == mock_admin_user["clerk_id"]


def test_with_authenticated_client(authenticated_client, mock_user_data):
    """
    Test using the authenticated_client fixture
    """
    # The authenticated_client handles all the authentication details for us
    response = authenticated_client.get("/api/v1/users/me")

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == mock_user_data["email"]
    assert data["clerk_id"] == mock_user_data["clerk_id"]
