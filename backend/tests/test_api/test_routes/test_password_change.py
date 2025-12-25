import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import json
from datetime import datetime, timezone

pytest.skip(
    "Skipping this file - password changes are handled by better-auth, not the backend API.",
    allow_module_level=True,
)


def test_password_change_successful(auth_client_factory, test_user):
    """
    Test successful password change with correct current password.
    Verifies that password changes work when current password is correct.
    """
    # Password change data
    password_data = {
        "current_password": "CurrentPass123!",
        "new_password": "NewSecurePass456!",
    }

    # Make the request to change password
    response = auth_client_factory().post(
        "/api/v1/users/change-password", json=password_data
    )

    # Assert successful response
    assert response.status_code == 200
    data = response.json()

    # Verify response indicates successful password change
    assert "password_updated" in data
    assert data["password_updated"] == True

    # Verify the Clerk client was called with correct parameters
    mock_clerk_client.users.verify_password.assert_called_once_with(
        user_id=mock_user_data["clerk_id"],
        password=password_data["current_password"],
    )

    mock_clerk_client.users.update_user.assert_called_once_with(
        user_id=mock_user_data["clerk_id"], password=password_data["new_password"]
    )


def test_password_change_incorrect_current_password(
    authenticated_client, mock_user_data, mock_clerk_client
):
    """
    Test password change with incorrect current password.
    Verifies that the API rejects password changes when current password is incorrect.
    """
    # Configure mock to simulate incorrect current password
    mock_clerk_client.users.verify_password = AsyncMock(
        return_value={"verified": False}
    )

    # Password change data with incorrect current password
    password_data = {
        "current_password": "WrongCurrentPass123!",
        "new_password": "NewSecurePass456!",
    }

    # Mock the necessary dependencies
    with patch(
        "app.core.security.verify_jwt_token",
        return_value={"sub": mock_user_data["clerk_id"]},
    ), patch(
        "app.core.security.get_user_by_clerk_id", return_value=mock_user_data
    ), patch(
        "app.db.database.get_user_by_clerk_id", return_value=mock_user_data
    ), patch(
        "app.api.endpoints.users.get_current_user", return_value=mock_user_data
    ), patch(
        "app.api.dependencies.get_clerk_client", return_value=mock_clerk_client
    ), patch(
        "app.api.endpoints.auth.get_clerk_client", return_value=mock_clerk_client
    ):

        # Make the request to change password
        response = authenticated_client.post(
            "/api/v1/users/change-password", json=password_data
        )

        # Assert error response
        assert response.status_code == 401  # Unauthorized
        data = response.json()

        # Verify response indicates authentication failure
        assert "detail" in data
        assert (
            "incorrect" in data["detail"].lower() or "invalid" in data["detail"].lower()
        )

        # Verify that update was not called
        mock_clerk_client.users.update_user.assert_not_called()


def test_password_change_weak_password(
    authenticated_client, mock_user_data, mock_clerk_client
):
    """
    Test password change with a weak new password.
    Verifies that the API enforces password strength requirements.
    """
    # Password change data with weak new password
    password_data = {"current_password": "CurrentPass123!", "new_password": "weak"}

    # Mock the necessary dependencies
    with patch(
        "app.core.security.verify_jwt_token",
        return_value={"sub": mock_user_data["clerk_id"]},
    ), patch(
        "app.core.security.get_user_by_clerk_id", return_value=mock_user_data
    ), patch(
        "app.db.database.get_user_by_clerk_id", return_value=mock_user_data
    ), patch(
        "app.api.endpoints.users.get_current_user", return_value=mock_user_data
    ), patch(
        "app.api.endpoints.users.audit_request", return_value=None
    ), patch(
        "app.api.dependencies.get_clerk_client", return_value=mock_clerk_client
    ), patch(
        "app.api.endpoints.auth.get_clerk_client", return_value=mock_clerk_client
    ):

        # Make the request to change password
        response = authenticated_client.post(
            "/api/v1/users/change-password", json=password_data
        )

        # Assert validation error response
        assert response.status_code == 400  # Bad Request
        data = response.json()

        # Verify response indicates password strength issues
        assert "detail" in data
        assert (
            "password" in data["detail"].lower()
            and "requirements" in data["detail"].lower()
        )

        # Verify that update was not called
        mock_clerk_client.users.update_user.assert_not_called()


def test_password_change_same_as_current(
    authenticated_client, mock_user_data, mock_clerk_client
):
    """
    Test password change where new password is the same as current password.
    Verifies that the API prevents using the same password again.
    """
    # Password change data with new password same as current
    password_data = {
        "current_password": "CurrentPass123!",
        "new_password": "CurrentPass123!",
    }

    # Mock the necessary dependencies
    with patch(
        "app.core.security.verify_jwt_token",
        return_value={"sub": mock_user_data["clerk_id"]},
    ), patch(
        "app.core.security.get_user_by_clerk_id", return_value=mock_user_data
    ), patch(
        "app.db.database.get_user_by_clerk_id", return_value=mock_user_data
    ), patch(
        "app.api.endpoints.users.get_current_user", return_value=mock_user_data
    ), patch(
        "app.api.endpoints.users.audit_request", return_value=None
    ), patch(
        "app.api.dependencies.get_clerk_client", return_value=mock_clerk_client
    ), patch(
        "app.api.endpoints.auth.get_clerk_client", return_value=mock_clerk_client
    ):

        # Make the request to change password
        response = authenticated_client.post(
            "/api/v1/users/change-password", json=password_data
        )

        # Assert validation error response
        assert response.status_code == 400  # Bad Request
        data = response.json()

        # Verify response indicates password reuse issue
        assert "detail" in data
        assert "same" in data["detail"].lower() and "current" in data["detail"].lower()

        # Verify that update was not called
        mock_clerk_client.users.update_user.assert_not_called()


def test_password_strength_requirements(
    authenticated_client, mock_user_data, mock_clerk_client
):
    """
    Test various password strength scenarios.
    Verifies that the API enforces password complexity rules.
    """
    # Test cases with different passwords and expected results
    test_cases = [
        # (password, should_pass)
        ("short", False),  # Too short
        ("nouppercase123!", False),  # No uppercase
        ("NOLOWERCASE123!", False),  # No lowercase
        ("NoNumbers!", False),  # No numbers
        ("NoSpecialChars123", False),  # No special characters
        ("Strong!Password123", True),  # Meets all requirements
    ]

    for password, should_pass in test_cases:
        # Reset the mock for each test case
        mock_clerk_client.users.verify_password.reset_mock()
        mock_clerk_client.users.update_user.reset_mock()

        password_data = {
            "current_password": "CurrentPass123!",
            "new_password": password,
        }

        # Mock the necessary dependencies
        with patch(
            "app.core.security.verify_jwt_token",
            return_value={"sub": mock_user_data["clerk_id"]},
        ), patch(
            "app.core.security.get_user_by_clerk_id", return_value=mock_user_data
        ), patch(
            "app.db.database.get_user_by_clerk_id", return_value=mock_user_data
        ), patch(
            "app.api.endpoints.users.get_current_user", return_value=mock_user_data
        ), patch(
            "app.api.endpoints.users.audit_request", return_value=None
        ), patch(
            "app.api.dependencies.get_clerk_client", return_value=mock_clerk_client
        ), patch(
            "app.api.endpoints.auth.get_clerk_client", return_value=mock_clerk_client
        ):

            # Make the request to change password
            response = authenticated_client.post(
                "/api/v1/users/change-password", json=password_data
            )

            if should_pass:
                # Assert successful response
                assert (
                    response.status_code == 200
                ), f"Password '{password}' should have passed"
                mock_clerk_client.users.update_user.assert_called_once()
            else:
                # Assert validation error response
                assert (
                    response.status_code == 400
                ), f"Password '{password}' should have been rejected"
                mock_clerk_client.users.update_user.assert_not_called()
