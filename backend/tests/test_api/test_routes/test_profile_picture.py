import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import json
import io
from datetime import datetime, timezone

pytest.skip(
    "Skipping this file - profile pictures need to be re-implemented for better-auth.",
    allow_module_level=True,
)


@pytest.fixture
def test_image_file():
    """
    Create a mock image file for testing
    """
    # Create a small image-like byte stream
    content = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x01D\x00;"
    return io.BytesIO(content)


def test_avatar_upload_successful(
    authenticated_client,
    mock_updated_user,
    mock_clerk_client,
    test_image_file,
):
    """
    Test successful avatar upload.
    Verifies that the API handles avatar uploads correctly.
    """

    # Create form data with file
    files = {"file": ("test_image.gif", test_image_file, "image/gif")}

    # Make the request to upload avatar
    response = authenticated_client.post("/api/v1/users/avatar", files=files)

    # Assert successful response
    assert response.status_code == 200
    data = response.json()

    # Verify avatar URL was updated
    assert "avatar_url" in data
    assert data["avatar_url"] == "https://example.com/new_avatar.jpg"

    # Verify Clerk API was called
    mock_clerk_client.users.update_user_profile_image.assert_called_once()


def test_avatar_upload_invalid_file_type(
    authenticated_client, mock_user_data, mock_clerk_client
):
    """
    Test avatar upload with invalid file type.
    Verifies that the API rejects non-image files.
    """
    # Create non-image file
    non_image_file = io.BytesIO(b"This is not an image file")

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
        "app.api.endpoints.users.get_clerk_client", return_value=mock_clerk_client
    ):

        # Create form data with non-image file
        files = {"file": ("document.txt", non_image_file, "text/plain")}

        # Make the request to upload avatar
        response = authenticated_client.post("/api/v1/users/avatar", files=files)

        # Assert validation error response
        assert response.status_code == 400
        data = response.json()

        # Verify error message about file type
        assert "detail" in data
        assert "image" in data["detail"].lower()


def test_avatar_upload_file_too_large(
    authenticated_client, mock_user_data, mock_clerk_client
):
    """
    Test avatar upload with a file that exceeds size limit.
    Verifies that the API rejects files that are too large.
    """
    # Create large image file (simulate 6MB file which exceeds typical 5MB limit)
    large_file = io.BytesIO(b"GIF89a" + b"X" * (6 * 1024 * 1024))

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
        "app.api.endpoints.users.get_clerk_client", return_value=mock_clerk_client
    ):

        # Create form data with large file
        files = {"file": ("large_image.gif", large_file, "image/gif")}

        # Make the request to upload avatar
        response = authenticated_client.post("/api/v1/users/avatar", files=files)

        # Assert validation error response
        assert response.status_code == 413  # Request Entity Too Large
        data = response.json()

        # Verify error message about file size
        assert "detail" in data
        assert "size" in data["detail"].lower() or "large" in data["detail"].lower()


def test_avatar_upload_no_file(authenticated_client, mock_user_data, mock_clerk_client):
    """
    Test avatar upload with no file provided.
    Verifies that the API rejects requests with missing file.
    """
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
        "app.api.endpoints.users.get_clerk_client", return_value=mock_clerk_client
    ):

        # Empty files dictionary
        files = {}

        # Make the request to upload avatar
        response = authenticated_client.post("/api/v1/users/avatar", files=files)

        # Assert validation error response
        assert response.status_code == 400
        data = response.json()

        # Verify error message about missing file
        assert "detail" in data
        assert "file" in data["detail"].lower() and (
            "missing" in data["detail"].lower() or "required" in data["detail"].lower()
        )


def test_avatar_update_via_url(authenticated_client, mock_user_data, mock_updated_user):
    """
    Test updating avatar URL directly (without file upload).
    Verifies that the API allows updating the avatar via URL.
    """
    # Update with new avatar URL
    avatar_update = {"avatar_url": "https://example.com/new_avatar.jpg"}

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
        "app.db.database.update_user", return_value=mock_updated_user
    ):

        # Make the request to update avatar URL
        response = authenticated_client.patch("/api/v1/users/me", json=avatar_update)

        # Assert successful response
        assert response.status_code == 200
        data = response.json()

        # Verify avatar URL was updated
        assert data["avatar_url"] == avatar_update["avatar_url"]


def test_avatar_url_validation(authenticated_client, mock_user_data):
    """
    Test validation of avatar URL.
    Verifies that the API validates avatar URL format.
    """
    # Update with invalid avatar URL
    invalid_update = {"avatar_url": "not-a-valid-url"}

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
    ):

        # Make the request to update avatar URL
        response = authenticated_client.patch("/api/v1/users/me", json=invalid_update)

        # Assert validation error response
        assert response.status_code == 422
        data = response.json()

        # Verify error message about invalid URL
        assert "detail" in data
