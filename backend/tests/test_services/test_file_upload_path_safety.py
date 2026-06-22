"""
Path-safety tests for local cover-image deletion.
Verifies that delete_cover_image cannot escape COVER_IMAGES_DIR (path traversal).
"""
import pytest
from unittest.mock import patch
from app.services.file_upload_service import (
    FileUploadService,
    _resolve_local_cover_path,
    COVER_IMAGES_DIR,
)


class TestResolveLocalCoverPath:
    """Unit tests for the containment helper."""

    def test_happy_path_resolves_inside_dir(self):
        path = _resolve_local_cover_path("/uploads/cover_images/abc.png")
        assert path is not None
        assert path.is_relative_to(COVER_IMAGES_DIR.resolve())

    def test_traversal_rejected(self):
        assert _resolve_local_cover_path("/uploads/cover_images/../../etc/passwd") is None

    def test_wrong_prefix_rejected(self):
        assert _resolve_local_cover_path("/etc/passwd") is None

    def test_empty_rejected(self):
        assert _resolve_local_cover_path("") is None


class TestDeleteCoverImageContainment:
    """delete_cover_image must not unlink anything outside the uploads dir."""

    @pytest.fixture
    def local_service(self):
        # Force local-storage mode (no cloud backend).
        with patch(
            "app.services.file_upload_service.get_cloud_storage_service",
            return_value=None,
        ):
            return FileUploadService()

    @pytest.mark.asyncio
    async def test_traversal_url_does_not_unlink(self, local_service):
        with patch("pathlib.Path.unlink") as mock_unlink, \
             patch("pathlib.Path.exists", return_value=True):
            await local_service.delete_cover_image(
                "/uploads/cover_images/../../etc/passwd"
            )
        mock_unlink.assert_not_called()

    @pytest.mark.asyncio
    async def test_normal_url_unlinks(self, local_service):
        with patch("pathlib.Path.unlink") as mock_unlink, \
             patch("pathlib.Path.exists", return_value=True):
            await local_service.delete_cover_image(
                "/uploads/cover_images/abc.png"
            )
        mock_unlink.assert_called_once()
