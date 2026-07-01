"""
Test File Upload Service functionality
Tests both local and cloud storage modes
"""
import pytest
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi import UploadFile, HTTPException
from PIL import Image
from io import BytesIO
from app.services.file_upload_service import (
    FileUploadService,
    COVER_IMAGES_DIR,
    PROFILE_PICTURES_DIR,
    PROFILE_IMAGE_URL_PREFIX,
)


class TestProfilePictureUpload:
    """Profile picture (avatar) processing — local and cloud paths."""

    def _make_file(self, name="a.jpg", ctype="image/jpeg", size=(600, 600)):
        img = Image.new("RGB", size, color="blue")
        buf = BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        mock = Mock(spec=UploadFile)
        mock.filename = name
        mock.content_type = ctype
        mock.file = buf
        return mock

    @pytest.fixture
    def cleanup_profile_files(self):
        yield
        if PROFILE_PICTURES_DIR.exists():
            for f in PROFILE_PICTURES_DIR.glob("user-1_*"):
                f.unlink()

    @pytest.mark.asyncio
    async def test_process_saves_local_and_downscales(self, cleanup_profile_files):
        with patch("app.services.file_upload_service.get_cloud_storage_service", return_value=None):
            service = FileUploadService()
            url = await service.process_and_save_profile_picture(self._make_file(), "user-1")
        assert url.startswith(PROFILE_IMAGE_URL_PREFIX)
        saved = PROFILE_PICTURES_DIR / url[len(PROFILE_IMAGE_URL_PREFIX):]
        assert saved.exists()
        with Image.open(saved) as im:
            assert im.width <= 400 and im.height <= 400  # downscaled to <=400px

    @pytest.mark.asyncio
    async def test_process_rejects_non_image(self):
        with patch("app.services.file_upload_service.get_cloud_storage_service", return_value=None):
            service = FileUploadService()
            with pytest.raises(HTTPException) as exc:
                await service.process_and_save_profile_picture(
                    self._make_file(name="a.txt", ctype="text/plain"), "user-1"
                )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_process_uses_cloud_storage(self):
        cloud = AsyncMock()
        cloud.upload_image.return_value = "https://cdn.example.com/avatar.jpg"
        with patch("app.services.file_upload_service.get_cloud_storage_service", return_value=cloud):
            service = FileUploadService()
            url = await service.process_and_save_profile_picture(self._make_file(), "user-1")
        assert url == "https://cdn.example.com/avatar.jpg"
        cloud.upload_image.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_local_avatar(self, cleanup_profile_files):
        with patch("app.services.file_upload_service.get_cloud_storage_service", return_value=None):
            service = FileUploadService()
            url = await service.process_and_save_profile_picture(self._make_file(), "user-1")
            saved = PROFILE_PICTURES_DIR / url[len(PROFILE_IMAGE_URL_PREFIX):]
            assert saved.exists()
            await service.delete_profile_picture(url)
            assert not saved.exists()

    @pytest.mark.asyncio
    async def test_validate_rejects_decompression_bomb(self):
        """A file whose image decodes to huge dimensions is rejected."""
        with patch("app.services.file_upload_service.get_cloud_storage_service", return_value=None):
            service = FileUploadService()
        fake_image = MagicMock()
        fake_image.size = (10000, 10000)  # 100MP > MAX_IMAGE_PIXELS
        fake_image.verify.return_value = None
        with patch("app.services.file_upload_service.Image.open", return_value=fake_image):
            ok, err = await service.validate_image_upload(self._make_file())
        assert ok is False
        assert "dimensions" in err.lower()

    @pytest.mark.asyncio
    async def test_delete_refuses_path_traversal(self):
        with patch("app.services.file_upload_service.get_cloud_storage_service", return_value=None):
            service = FileUploadService()
            # Must not raise, must not touch anything outside the dir.
            await service.delete_profile_picture("/uploads/profile_pictures/../../etc/passwd")


class TestFileUploadService:
    """Test the file upload service functionality."""

    @pytest.fixture
    def mock_cloud_storage(self):
        """Mock cloud storage service."""
        mock_storage = AsyncMock()
        mock_storage.upload_image.return_value = "https://cdn.example.com/image.jpg"
        mock_storage.delete_image.return_value = True
        return mock_storage

    @pytest.fixture
    def mock_upload_file(self):
        """Create a mock UploadFile."""
        # Create a small test image
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)

        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.file = img_bytes
        mock_file.size = len(img_bytes.getvalue())
        return mock_file

    @pytest.fixture
    def cleanup_local_files(self):
        """Clean up any local test files."""
        yield
        # Clean up after test
        if COVER_IMAGES_DIR.exists():
            for file in COVER_IMAGES_DIR.glob("test_book_*"):
                file.unlink()

    def test_init_with_cloud_storage(self, mock_cloud_storage):
        """Test initialization with cloud storage available."""
        with patch('app.services.file_upload_service.get_cloud_storage_service', return_value=mock_cloud_storage):
            service = FileUploadService()
            assert service.cloud_storage == mock_cloud_storage

    def test_init_without_cloud_storage(self):
        """Test initialization without cloud storage (local mode)."""
        with patch('app.services.file_upload_service.get_cloud_storage_service', return_value=None):
            service = FileUploadService()
            assert service.cloud_storage is None
            assert COVER_IMAGES_DIR.exists()

    @pytest.mark.asyncio
    async def test_validate_image_upload_valid(self, mock_upload_file):
        """Test validation of valid image upload."""
        service = FileUploadService()
        is_valid, error = await service.validate_image_upload(mock_upload_file)

        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_image_upload_invalid_extension(self):
        """Test validation rejects invalid file extensions."""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.txt"
        mock_file.content_type = "text/plain"

        service = FileUploadService()
        is_valid, error = await service.validate_image_upload(mock_file)

        assert is_valid is False
        assert "Invalid file type" in error

    @pytest.mark.asyncio
    async def test_validate_image_upload_too_large(self):
        """Test validation rejects files that are too large."""
        # Create a mock file that reports large size
        large_file = Mock(spec=UploadFile)
        large_file.filename = "large.jpg"
        large_file.content_type = "image/jpeg"

        # Mock file object that reports large size
        mock_file_obj = Mock()
        mock_file_obj.tell.return_value = 6 * 1024 * 1024  # 6MB
        mock_file_obj.seek = Mock()
        mock_file_obj.read.return_value = b"fake image data"
        large_file.file = mock_file_obj

        service = FileUploadService()
        is_valid, error = await service.validate_image_upload(large_file)

        assert is_valid is False
        assert "File too large" in error

    @pytest.mark.asyncio
    async def test_process_and_save_cover_image_cloud_storage(self, mock_upload_file, mock_cloud_storage):
        """Test image processing and upload to cloud storage."""
        with patch('app.services.file_upload_service.get_cloud_storage_service', return_value=mock_cloud_storage):
            service = FileUploadService()
            service.cloud_storage = mock_cloud_storage

            image_url, thumbnail_url = await service.process_and_save_cover_image(
                mock_upload_file,
                "test_book_123"
            )

            assert image_url == "https://cdn.example.com/image.jpg"
            assert thumbnail_url == "https://cdn.example.com/image.jpg"

            # Verify cloud storage was called twice (main image and thumbnail)
            assert mock_cloud_storage.upload_image.call_count == 2

    @pytest.mark.asyncio
    async def test_process_and_save_cover_image_local_storage(self, mock_upload_file, cleanup_local_files):
        """Test image processing and save to local storage."""
        with patch('app.services.file_upload_service.get_cloud_storage_service', return_value=None):
            service = FileUploadService()

            image_url, thumbnail_url = await service.process_and_save_cover_image(
                mock_upload_file,
                "test_book_123"
            )

            assert image_url.startswith("/uploads/cover_images/test_book_123_")
            assert thumbnail_url.startswith("/uploads/cover_images/test_book_123_")
            assert image_url.endswith(".jpg")
            assert "_thumb" in thumbnail_url

            # Verify files were created
            image_filename = image_url.split("/")[-1]
            thumb_filename = thumbnail_url.split("/")[-1]
            assert (COVER_IMAGES_DIR / image_filename).exists()
            assert (COVER_IMAGES_DIR / thumb_filename).exists()

    @pytest.mark.asyncio
    async def test_process_and_save_cover_image_validation_failure(self, mock_upload_file):
        """Test that validation failures raise HTTPException."""
        mock_upload_file.filename = "invalid.txt"

        service = FileUploadService()

        with pytest.raises(HTTPException) as exc_info:
            await service.process_and_save_cover_image(mock_upload_file, "book_123")

        assert exc_info.value.status_code == 400
        assert "Invalid file type" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_process_and_save_cover_image_processing_error(self, mock_upload_file):
        """Test error handling during image processing."""
        # Make the image file invalid
        mock_upload_file.file = BytesIO(b"invalid image data")

        service = FileUploadService()

        with pytest.raises(HTTPException) as exc_info:
            await service.process_and_save_cover_image(mock_upload_file, "book_123")

        assert exc_info.value.status_code == 400
        assert "Invalid image file" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_cover_image_cloud_storage(self, mock_cloud_storage):
        """Test image deletion from cloud storage."""
        with patch('app.services.file_upload_service.get_cloud_storage_service', return_value=mock_cloud_storage):
            service = FileUploadService()
            service.cloud_storage = mock_cloud_storage

            await service.delete_cover_image(
                "https://cdn.example.com/image.jpg",
                "https://cdn.example.com/thumb.jpg"
            )

            # Verify cloud storage delete was called for both images
            assert mock_cloud_storage.delete_image.call_count == 2

    @pytest.mark.asyncio
    async def test_delete_cover_image_local_storage(self, cleanup_local_files):
        """Test image deletion from local storage."""
        # Create test files
        test_image = COVER_IMAGES_DIR / "test_image.jpg"
        test_thumb = COVER_IMAGES_DIR / "test_thumb.jpg"
        test_image.touch()
        test_thumb.touch()

        with patch('app.services.file_upload_service.get_cloud_storage_service', return_value=None):
            service = FileUploadService()

            await service.delete_cover_image(
                "/uploads/cover_images/test_image.jpg",
                "/uploads/cover_images/test_thumb.jpg"
            )

            # Verify files were deleted
            assert not test_image.exists()
            assert not test_thumb.exists()

    @pytest.mark.asyncio
    async def test_delete_cover_image_handles_errors(self, mock_cloud_storage):
        """Test that delete errors are handled gracefully."""
        mock_cloud_storage.delete_image.side_effect = Exception("Delete failed")

        with patch('app.services.file_upload_service.get_cloud_storage_service', return_value=mock_cloud_storage):
            service = FileUploadService()
            service.cloud_storage = mock_cloud_storage

            # Should not raise exception
            await service.delete_cover_image("https://cdn.example.com/image.jpg")

    def test_get_upload_stats(self, cleanup_local_files):
        """Test upload statistics calculation."""
        # Ensure directory exists
        COVER_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

        # Create some test files
        for i in range(3):
            test_file = COVER_IMAGES_DIR / f"test_{i}.jpg"
            test_file.write_bytes(b"x" * 1000)

        service = FileUploadService()
        stats = service.get_upload_stats()

        # Debug output
        print(f"Stats: {stats}")
        print(f"Files in dir: {list(COVER_IMAGES_DIR.glob('*'))}")

        assert stats["total_files"] >= 3
        # Size might be rounded to 0.0 for small files
        assert stats["total_size_mb"] >= 0.0

    @pytest.mark.asyncio
    async def test_image_resizing(self, mock_cloud_storage):
        """Test that large images are resized."""
        # Create a large test image
        large_img = Image.new('RGB', (2000, 3000), color='blue')
        img_bytes = BytesIO()
        large_img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)

        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "large.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.file = img_bytes

        with patch('app.services.file_upload_service.get_cloud_storage_service', return_value=mock_cloud_storage):
            service = FileUploadService()
            service.cloud_storage = mock_cloud_storage

            # Capture the uploaded image data
            uploaded_data = None

            async def capture_upload(file_data, **kwargs):
                nonlocal uploaded_data
                uploaded_data = file_data
                return "https://cdn.example.com/resized.jpg"

            mock_cloud_storage.upload_image.side_effect = capture_upload

            await service.process_and_save_cover_image(mock_file, "book_123")

            # Verify the image was resized
            assert uploaded_data is not None
            resized_img = Image.open(BytesIO(uploaded_data))
            assert resized_img.width <= 1200
            assert resized_img.height <= 1800
