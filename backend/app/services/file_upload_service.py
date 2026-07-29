"""
File upload service for handling book cover images and other file uploads.
Currently uses local storage, but designed to be easily extended for cloud storage (S3, Cloudinary, etc.)
"""

import asyncio
import uuid
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
from fastapi import UploadFile, HTTPException, status
from io import BytesIO
from app.services.cloud_storage_service import get_cloud_storage_service
import logging

logger = logging.getLogger(__name__)

# Configuration
UPLOAD_DIR = Path("uploads")
COVER_IMAGES_DIR = UPLOAD_DIR / "cover_images"
PROFILE_PICTURES_DIR = UPLOAD_DIR / "profile_pictures"
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
# Guard against decompression bombs: a small file can decode to enormous
# pixel dimensions and exhaust memory/CPU. 50MP comfortably covers real photos.
MAX_IMAGE_PIXELS = 50_000_000
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif"
}

# Image processing settings
MAX_IMAGE_WIDTH = 1200
MAX_IMAGE_HEIGHT = 1800
THUMBNAIL_SIZE = (300, 450)
# Avatars are small — one image, no thumbnail. Downscaled to fit 400x400
# preserving aspect ratio; the UI crops to a circle via object-cover.
PROFILE_PICTURE_SIZE = (400, 400)

COVER_IMAGE_URL_PREFIX = "/uploads/cover_images/"
PROFILE_IMAGE_URL_PREFIX = "/uploads/profile_pictures/"


def _resolve_local_path(image_url: str, prefix: str, base_dir: Path) -> Optional[Path]:
    """Resolve a <prefix><name> URL to a path INSIDE base_dir, or None if it
    would escape the directory (path-traversal guard)."""
    if not image_url or not image_url.startswith(prefix):
        return None
    filename = image_url[len(prefix):]
    base = base_dir.resolve()
    candidate = (base / filename).resolve()
    if not candidate.is_relative_to(base):
        return None
    return candidate


def _resolve_local_cover_path(image_url: str) -> Optional[Path]:
    """Resolve a /uploads/cover_images/<name> URL to a path inside COVER_IMAGES_DIR."""
    return _resolve_local_path(image_url, COVER_IMAGE_URL_PREFIX, COVER_IMAGES_DIR)


def _resolve_local_profile_path(image_url: str) -> Optional[Path]:
    """Resolve a /uploads/profile_pictures/<name> URL to a path inside PROFILE_PICTURES_DIR."""
    return _resolve_local_path(image_url, PROFILE_IMAGE_URL_PREFIX, PROFILE_PICTURES_DIR)


# --- Blocking PIL work, isolated so it can be pushed off the event loop (#346).
#
# Decode, LANCZOS resize and save(optimize=True) are CPU-bound and were running
# inline in `async def`, freezing the loop — on a 2-worker deploy a couple of
# concurrent uploads stalled health checks and every other request on the
# worker. Same blocking-in-async class #175 fixed for OpenAI and #345 for
# exports. Each helper below is synchronous and must be called via
# `asyncio.to_thread`; the caller awaits it, so the file object is never
# touched by two threads at once.
#
# These go to the loop's DEFAULT executor rather than a dedicated pool like
# exports got in #345. Uploads are mostly network wait (S3/Cloudinary) with a
# short encode, which is what that pool is sized for; exports are long,
# CPU-bound and bursty, which is why they needed isolating.


def _validate_image_sync(fileobj) -> Tuple[bool, Optional[str]]:
    """Decode-verify an upload and reject decompression bombs. Blocking."""
    try:
        fileobj.seek(0)
        image = Image.open(fileobj)
        width, height = image.size
        image.verify()
        fileobj.seek(0)  # Reset after verify
    except Exception:
        return False, "Invalid image file"

    if width * height > MAX_IMAGE_PIXELS:
        return False, "Image dimensions too large"

    return True, None


def _prepare_image(fileobj, file_ext: str):
    """Open an upload and normalise it to RGB when the target format needs it."""
    fileobj.seek(0)
    image = Image.open(fileobj)
    if image.mode in ('RGBA', 'LA', 'P'):
        rgb_image = Image.new('RGB', image.size, (255, 255, 255))
        rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
        image = rgb_image
    return image


def _process_cover_sync(fileobj, file_ext: str, image_path: Path,
                        thumbnail_path: Path, to_cloud: bool):
    """Build a cover image + thumbnail. Blocking; call via asyncio.to_thread.

    Returns ``(main_bytes, thumb_bytes, image_format)``. For the local path the
    files are written here and the two byte payloads come back ``None``.
    """
    image = _prepare_image(fileobj, file_ext)

    if image.width > MAX_IMAGE_WIDTH or image.height > MAX_IMAGE_HEIGHT:
        image.thumbnail((MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT), Image.Resampling.LANCZOS)

    thumbnail = image.copy()
    thumbnail.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

    image_format = 'JPEG' if file_ext in ['.jpg', '.jpeg'] else 'PNG'

    if to_cloud:
        main_buffer = BytesIO()
        thumb_buffer = BytesIO()
        image.save(main_buffer, format=image_format, quality=85, optimize=True)
        thumbnail.save(thumb_buffer, format=image_format, quality=85, optimize=True)
        main_buffer.seek(0)
        thumb_buffer.seek(0)
        return main_buffer.read(), thumb_buffer.read(), image_format

    image.save(image_path, quality=85, optimize=True)
    thumbnail.save(thumbnail_path, quality=85, optimize=True)
    return None, None, image_format


def _process_profile_sync(fileobj, file_ext: str, image_path: Path, to_cloud: bool):
    """Build an avatar downscaled to fit PROFILE_PICTURE_SIZE. Blocking.

    Returns ``(image_bytes, image_format)``; ``image_bytes`` is ``None`` on the
    local path, where the file is written here.
    """
    image = _prepare_image(fileobj, file_ext)
    image.thumbnail(PROFILE_PICTURE_SIZE, Image.Resampling.LANCZOS)

    image_format = 'JPEG' if file_ext in ['.jpg', '.jpeg'] else 'PNG'

    if to_cloud:
        buffer = BytesIO()
        image.save(buffer, format=image_format, quality=85, optimize=True)
        buffer.seek(0)
        return buffer.read(), image_format

    image.save(image_path, quality=85, optimize=True)
    return None, image_format


class FileUploadService:
    """Service for handling file uploads with validation and storage."""

    def __init__(self):
        """Initialize the upload service and ensure directories exist."""
        self.cloud_storage = get_cloud_storage_service()
        if self.cloud_storage is None:
            # Only create local directories if not using cloud storage
            COVER_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
            PROFILE_PICTURES_DIR.mkdir(parents=True, exist_ok=True)
            logger.info("Using local file storage for uploads")
        else:
            logger.info("Using cloud storage for uploads")

    async def validate_image_upload(
        self,
        file: UploadFile
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate an uploaded image file.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_IMAGE_EXTENSIONS:
            return False, f"Invalid file type. Allowed types: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"

        # Check MIME type
        if file.content_type not in ALLOWED_MIME_TYPES:
            return False, f"Invalid content type. Allowed types: {', '.join(ALLOWED_MIME_TYPES)}"

        # Check file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning

        if file_size > MAX_FILE_SIZE:
            return False, f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"

        # Validate it's actually an image, and guard against decompression bombs
        # (a small file that decodes to enormous dimensions). PIL work is
        # blocking, so it goes to a worker thread (#346).
        return await asyncio.to_thread(_validate_image_sync, file.file)

    async def process_and_save_cover_image(
        self,
        file: UploadFile,
        book_id: str
    ) -> Tuple[str, str]:
        """
        Process and save a cover image for a book.

        Returns:
            Tuple of (image_url, thumbnail_url)
        """
        # Validate the upload
        is_valid, error_msg = await self.validate_image_upload(file)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        # Generate unique filename
        file_ext = Path(file.filename).suffix.lower()
        unique_filename = f"{book_id}_{uuid.uuid4().hex}{file_ext}"
        thumbnail_filename = f"{book_id}_{uuid.uuid4().hex}_thumb{file_ext}"

        # Paths for saving
        image_path = COVER_IMAGES_DIR / unique_filename
        thumbnail_path = COVER_IMAGES_DIR / thumbnail_filename

        try:
            # All decode/resize/encode work happens on a worker thread so the
            # event loop stays free to serve other requests (#346).
            main_bytes, thumb_bytes, image_format = await asyncio.to_thread(
                _process_cover_sync,
                file.file,
                file_ext,
                image_path,
                thumbnail_path,
                bool(self.cloud_storage),
            )

            if self.cloud_storage:
                content_type = f"image/{image_format.lower()}"
                image_url = await self.cloud_storage.upload_image(
                    file_data=main_bytes,
                    filename=unique_filename,
                    content_type=content_type,
                    folder=f"cover_images/{book_id}"
                )

                try:
                    thumbnail_url = await self.cloud_storage.upload_image(
                        file_data=thumb_bytes,
                        filename=thumbnail_filename,
                        content_type=content_type,
                        folder=f"cover_images/{book_id}/thumbnails"
                    )
                except Exception:
                    # The two uploads are not atomic. Without this the main
                    # image stays in the bucket forever while the caller gets a
                    # 500 and no record of the URL — an orphan nothing will ever
                    # reference or clean up. Roll it back, but never let the
                    # cleanup failure mask the upload failure.
                    try:
                        await self.cloud_storage.delete_image(image_url)
                    except Exception:
                        logger.error(
                            "Failed to roll back orphaned cover image %s",
                            image_url,
                            exc_info=True,
                        )
                    raise
            else:
                # _process_cover_sync already wrote both files.
                image_url = f"/uploads/cover_images/{unique_filename}"
                thumbnail_url = f"/uploads/cover_images/{thumbnail_filename}"

            return image_url, thumbnail_url

        except Exception:
            # Clean up any partially saved files
            if image_path.exists():
                image_path.unlink()
            if thumbnail_path.exists():
                thumbnail_path.unlink()

            logger.error("Failed to process image", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process image"
            )

    async def delete_cover_image(self, image_url: str, thumbnail_url: Optional[str] = None):
        """Delete a cover image and its thumbnail."""
        try:
            if self.cloud_storage:
                # Delete from cloud storage
                if image_url:
                    await self.cloud_storage.delete_image(image_url)
                if thumbnail_url:
                    await self.cloud_storage.delete_image(thumbnail_url)
            else:
                # Delete from local storage
                for url in (image_url, thumbnail_url):
                    if not url:
                        continue
                    path = _resolve_local_cover_path(url)
                    if path is None:
                        logger.warning("Refusing to delete cover image outside uploads dir")
                        continue
                    if path.exists():
                        path.unlink()

        except Exception as e:
            # Log error but don't fail the operation
            logger.error(f"Error deleting image files: {e}")

    async def process_and_save_profile_picture(
        self,
        file: UploadFile,
        user_id: str,
    ) -> str:
        """
        Process and save an avatar for a user. Returns the image URL.
        Mirrors process_and_save_cover_image but produces a single image
        downscaled to fit 400x400 (aspect ratio preserved, no thumbnail).
        """
        is_valid, error_msg = await self.validate_image_upload(file)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )

        file_ext = Path(file.filename).suffix.lower()
        unique_filename = f"{user_id}_{uuid.uuid4().hex}{file_ext}"
        image_path = PROFILE_PICTURES_DIR / unique_filename

        try:
            # Blocking PIL work goes to a worker thread (#346).
            image_bytes, image_format = await asyncio.to_thread(
                _process_profile_sync,
                file.file,
                file_ext,
                image_path,
                bool(self.cloud_storage),
            )

            if self.cloud_storage:
                return await self.cloud_storage.upload_image(
                    file_data=image_bytes,
                    filename=unique_filename,
                    content_type=f"image/{image_format.lower()}",
                    folder=f"profile_pictures/{user_id}",
                )

            # _process_profile_sync already wrote the file.
            return f"{PROFILE_IMAGE_URL_PREFIX}{unique_filename}"

        except Exception:
            if image_path.exists():
                image_path.unlink()
            logger.error("Failed to process profile picture", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process image",
            )

    async def delete_profile_picture(self, image_url: str):
        """Delete a previously-stored avatar (cloud or local). Never raises."""
        try:
            if not image_url:
                return
            if self.cloud_storage:
                await self.cloud_storage.delete_image(image_url)
                return
            path = _resolve_local_profile_path(image_url)
            if path is None:
                logger.warning("Refusing to delete profile picture outside uploads dir")
                return
            if path.exists():
                path.unlink()
        except Exception as e:
            logger.error(f"Error deleting profile picture: {e}")

    def get_upload_stats(self) -> dict:
        """Get statistics about uploaded files."""
        total_files = 0
        total_size = 0

        if COVER_IMAGES_DIR.exists():
            for file_path in COVER_IMAGES_DIR.iterdir():
                if file_path.is_file():
                    total_files += 1
                    total_size += file_path.stat().st_size

        return {
            "total_files": total_files,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "upload_directory": str(UPLOAD_DIR.absolute())
        }


# Create a singleton instance
file_upload_service = FileUploadService()
