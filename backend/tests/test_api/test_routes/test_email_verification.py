import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import json
from datetime import datetime, timezone

pytest.skip(
    "Skipping this file for now - haven't dealt with profile integration with Clerk yet.",
    allow_module_level=True,
)


def test_email_change_initiation(auth_client_factory, test_user):
    """
    Test the email change initiation process.
    Verifies that the API properly initiates the email change process with Clerk.
    """
    # Email change request data
    email_change_data = {"email": "new@example.com"}
    test_client = auth_client_factory()

    # Make the request to initiate email change
    response = test_client.post("/api/v1/users/email-change", json=email_change_data)

    # Assert successful response
    assert response.status_code == 200
    data = response.json()

    # Verify response indicates verification needed
    assert "verification_pending" in data
    assert data["verification_pending"] == True
    assert "email" in data
    assert data["email"] == "new@example.com"

    # Verify the Clerk client was called with correct parameters
    mock_clerk_client.emails.create_email_address.assert_called_once_with(
        user_id=mock_user_data["clerk_id"], email_address=email_change_data["email"]
    )
    mock_clerk_client.emails.prepare_verification.assert_called_once()


def test_email_change_verification(
    authenticated_client, mock_user_data, mock_clerk_client
):
    """
    Test the email change verification process.
    Verifies that the API properly handles the verification of a new email address.
    """
    # Verification data
    verification_data = {"email_id": "email_123", "code": "123456"}

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
        "app.db.database.update_user", return_value=mock_user_data
    ), patch(
        "app.api.dependencies.get_clerk_client", return_value=mock_clerk_client
    ), patch(
        "app.api.endpoints.auth.get_clerk_client", return_value=mock_clerk_client
    ):

        # Make the request to verify email change
        response = authenticated_client.post(
            "/api/v1/users/verify-email", json=verification_data
        )

        # Assert successful response
        assert response.status_code == 200
        data = response.json()

        # Verify response indicates successful verification
        assert "verification_successful" in data
        assert data["verification_successful"] == True

        # Verify the Clerk client was called with correct parameters
        mock_clerk_client.emails.verify.assert_called_once_with(
            email_id=verification_data["email_id"], code=verification_data["code"]
        )

        # Verify the primary email was updated
        mock_clerk_client.users.update_user.assert_called_once()


def test_email_change_verification_failure(
    authenticated_client, mock_user_data, mock_clerk_client
):
    """
    Test handling of failed email verification.
    Verifies that the API properly handles verification failures.
    """
    # Configure mock to simulate verification failure
    mock_clerk_client.emails.verify = AsyncMock(
        side_effect=Exception("Invalid verification code")
    )

    # Verification data with invalid code
    verification_data = {"email_id": "email_123", "code": "invalid"}

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

        # Make the request to verify email change
        response = authenticated_client.post(
            "/api/v1/users/verify-email", json=verification_data
        )

        # Assert error response
        assert response.status_code == 400
        data = response.json()

        # Verify response indicates verification failure
        assert "detail" in data
        assert "verification failed" in data["detail"].lower()
