import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import io
import os

pytest.skip(
    "Skipping this file for now - haven't integrated with Clerk yet.",
    allow_module_level=True,
)


def test_profile_picture_upload_success(authenticated_client, mock_user_data):
    """
    Test successful profile picture upload.
    Verifies that a user can successfully upload a profile picture.
    """
    # Create a test image file
    test_image = io.BytesIO(b"test image content")

    # Mock the clerk client
    mock_clerk = MagicMock()
    mock_clerk.users.update_user.return_value = {
        "id": mock_user_data["clerk_id"],
        "image_url": "https://example.com/new-avatar.jpg",
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
        "app.api.dependencies.get_clerk_client", return_value=mock_clerk
    ), patch(
        "app.db.database.update_user",
        return_value={
            **mock_user_data,
            "avatar_url": "https://example.com/new-avatar.jpg",
        },
    ):
        # Create the file data
        files = {"avatar": ("test_image.jpg", test_image, "image/jpeg")}

        # Make the request to upload profile picture
        response = authenticated_client.post("/api/v1/users/me/avatar", files=files)

        # Assert successful response
        assert response.status_code == 200
        data = response.json()

        # Verify the response contains the updated avatar URL
        assert "avatar_url" in data
        assert data["avatar_url"] == "https://example.com/new-avatar.jpg"

        # Verify clerk client was called to update the user
        mock_clerk.users.update_user.assert_called_once()


def test_profile_picture_upload_invalid_file(authenticated_client, mock_user_data):
    """
    Test profile picture upload with invalid file type.
    Verifies that the API rejects unsupported file formats.
    """
    # Create a test text file (not an image)
    test_file = io.BytesIO(b"this is not an image")

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
    ):
        # Create the file data
        files = {"avatar": ("test_file.txt", test_file, "text/plain")}

        # Make the request to upload profile picture
        response = authenticated_client.post("/api/v1/users/me/avatar", files=files)

        # Assert validation error
        assert response.status_code == 400
        data = response.json()

        # Verify error message about invalid file type
        assert "detail" in data
        assert "image" in data["detail"].lower()


def test_profile_picture_upload_large_file(authenticated_client, mock_user_data):
    """
    Test profile picture upload with a file that exceeds the size limit.
    Verifies that the API enforces file size limits.
    """
    # Create a large test file (10MB + 1 byte, assuming 10MB limit)
    large_file = io.BytesIO(b"0" * (10 * 1024 * 1024 + 1))

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
    ):
        # Create the file data
        files = {"avatar": ("large_image.jpg", large_file, "image/jpeg")}

        # Make the request to upload profile picture
        response = authenticated_client.post("/api/v1/users/me/avatar", files=files)

        # Assert validation error
        assert response.status_code == 400
        data = response.json()

        # Verify error message about file size
        assert "detail" in data
        assert "size" in data["detail"].lower()


def test_profile_picture_update_in_database(authenticated_client, mock_user_data):
    """
    Test that the profile picture URL is properly updated in the database.
    """
    # Create a test image file
    test_image = io.BytesIO(b"test image content")

    # Mock the clerk client
    mock_clerk = MagicMock()
    mock_clerk.users.update_user.return_value = {
        "id": mock_user_data["clerk_id"],
        "image_url": "https://example.com/new-avatar.jpg",
    }

    # Mock for database update
    db_update_mock = MagicMock(
        return_value={
            **mock_user_data,
            "avatar_url": "https://example.com/new-avatar.jpg",
        }
    )

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
        "app.api.dependencies.get_clerk_client", return_value=mock_clerk
    ), patch(
        "app.db.database.update_user", new=db_update_mock
    ):
        # Create the file data
        files = {"avatar": ("test_image.jpg", test_image, "image/jpeg")}

        # Make the request to upload profile picture
        response = authenticated_client.post("/api/v1/users/me/avatar", files=files)

        # Assert successful response
        assert response.status_code == 200

        # Verify database update was called with correct URL
        db_update_mock.assert_called_once()
        call_args = db_update_mock.call_args
        assert "user_data" in call_args[1]
        assert "avatar_url" in call_args[1]["user_data"]
        assert (
            call_args[1]["user_data"]["avatar_url"]
            == "https://example.com/new-avatar.jpg"
        )
