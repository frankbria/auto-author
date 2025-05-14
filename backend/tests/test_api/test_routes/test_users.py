import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


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
    }


def test_read_users_me(client: TestClient, mock_user_data):
    """
    Test that the /users/me endpoint returns the current user's information
    when properly authenticated.
    """
    # This test will need to be updated with proper auth mocking
    # Currently just a placeholder showing the structure
    with patch("app.core.security.get_current_user", return_value=mock_user_data):
        response = client.get("/api/v1/users/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == mock_user_data["email"]
        assert data["clerk_id"] == mock_user_data["clerk_id"]
