"""
Profile picture (avatar) upload endpoint — POST /api/v1/users/me/avatar.

Rewritten for better-auth (the previous Clerk-based version was skipped).
Mirrors the book cover upload tests: real MongoDB via auth_client_factory,
FileUploadService mocked so no image processing / storage happens.
"""
import pytest
from unittest.mock import AsyncMock, patch
from PIL import Image
from io import BytesIO

pytestmark = pytest.mark.asyncio


@pytest.fixture
def test_image():
    img = Image.new("RGB", (200, 200), color="blue")
    buf = BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf


@pytest.fixture
def mock_upload_service():
    svc = AsyncMock()
    svc.process_and_save_profile_picture.return_value = "/uploads/profile_pictures/new.jpg"
    svc.delete_profile_picture.return_value = None
    return svc


async def test_avatar_upload_success(auth_client_factory, test_image, mock_upload_service):
    client = await auth_client_factory()
    with patch("app.services.file_upload_service.FileUploadService", return_value=mock_upload_service):
        response = await client.post(
            "/api/v1/users/me/avatar",
            files={"file": ("avatar.jpg", test_image, "image/jpeg")},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["avatar_url"] == "/uploads/profile_pictures/new.jpg"
    mock_upload_service.process_and_save_profile_picture.assert_called_once()


async def test_avatar_upload_invalid_file_type(auth_client_factory):
    """A non-image is rejected by real validation (400)."""
    client = await auth_client_factory()
    response = await client.post(
        "/api/v1/users/me/avatar",
        files={"file": ("notes.txt", BytesIO(b"not an image"), "text/plain")},
    )
    assert response.status_code == 400
    assert "detail" in response.json()


async def test_avatar_upload_file_too_large(auth_client_factory):
    """A file over the 5MB limit is rejected (400)."""
    client = await auth_client_factory()
    big = BytesIO(b"0" * (5 * 1024 * 1024 + 1))
    response = await client.post(
        "/api/v1/users/me/avatar",
        files={"file": ("big.jpg", big, "image/jpeg")},
    )
    assert response.status_code == 400
    assert "size" in response.json()["detail"].lower()


async def test_avatar_upload_replaces_existing(auth_client_factory, test_image, mock_upload_service):
    """Uploading a new avatar deletes the previous one."""
    client = await auth_client_factory(
        overrides={"avatar_url": "/uploads/profile_pictures/old.jpg"}
    )
    with patch("app.services.file_upload_service.FileUploadService", return_value=mock_upload_service):
        response = await client.post(
            "/api/v1/users/me/avatar",
            files={"file": ("avatar.jpg", test_image, "image/jpeg")},
        )
    assert response.status_code == 200
    mock_upload_service.delete_profile_picture.assert_called_once_with(
        "/uploads/profile_pictures/old.jpg"
    )


async def test_avatar_upload_persists_url(auth_client_factory, test_image, mock_upload_service):
    """The new avatar_url is persisted via update_user."""
    client = await auth_client_factory()
    with patch("app.services.file_upload_service.FileUploadService", return_value=mock_upload_service), \
         patch("app.api.endpoints.users.update_user", new=AsyncMock()) as update_mock:
        response = await client.post(
            "/api/v1/users/me/avatar",
            files={"file": ("avatar.jpg", test_image, "image/jpeg")},
        )
    assert response.status_code == 200
    update_mock.assert_called_once()
    assert update_mock.call_args.kwargs["user_data"]["avatar_url"] == "/uploads/profile_pictures/new.jpg"


async def test_avatar_upload_requires_auth(auth_client_factory, test_image):
    client = await auth_client_factory(auth=False)
    response = await client.post(
        "/api/v1/users/me/avatar",
        files={"file": ("avatar.jpg", test_image, "image/jpeg")},
    )
    assert response.status_code == 401
