"""#346: image processing and cloud SDK calls must not block the event loop.

``process_and_save_*`` ran PIL decode/LANCZOS-resize/``save(optimize=True)``
straight inside ``async def``, and ``cloud_storage_service`` called synchronous
boto3/Cloudinary SDKs the same way. On a 2-worker deploy a couple of concurrent
uploads (multi-second S3 round-trip plus a PIL encode) stalled health checks and
every other request on that worker.

These tests assert the *event loop stayed responsive* while the blocking work
ran. Asserting only on the returned URL would pass identically before and after
the fix — the whole defect is that the loop froze, not that the result was
wrong.
"""
import asyncio
import time
from io import BytesIO
from unittest.mock import Mock, patch

import pytest
from fastapi import UploadFile
from PIL import Image

from app.services import file_upload_service as fus
from app.services.file_upload_service import FileUploadService


def _make_upload(name="cover.jpg", ctype="image/jpeg", size=(600, 900)):
    img = Image.new("RGB", size, color="red")
    buf = BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    mock = Mock(spec=UploadFile)
    mock.filename = name
    mock.content_type = ctype
    mock.file = buf
    return mock


async def _count_ticks_while(coro, tick=0.005):
    """Run ``coro`` while a heartbeat counts loop iterations.

    If the awaited work blocks the loop, the heartbeat never gets scheduled and
    the count stays at 0. That count is the assertion.
    """
    ticks = 0

    async def heartbeat():
        nonlocal ticks
        while True:
            await asyncio.sleep(tick)
            ticks += 1

    beat = asyncio.create_task(heartbeat())
    try:
        result = await coro
    finally:
        beat.cancel()
        try:
            await beat
        except asyncio.CancelledError:
            pass
    return result, ticks


BLOCKING_SECONDS = 0.15


class TestImageProcessingOffload:
    @pytest.mark.asyncio
    async def test_cover_processing_keeps_the_loop_responsive(self, tmp_path):
        """A slow PIL encode must not freeze the loop."""
        service = FileUploadService()
        service.cloud_storage = None

        real = fus._process_cover_sync

        def slow(*args, **kwargs):
            time.sleep(BLOCKING_SECONDS)  # stand-in for a large LANCZOS + encode
            return real(*args, **kwargs)

        with patch.object(fus, "_process_cover_sync", side_effect=slow):
            with patch.object(fus, "COVER_IMAGES_DIR", tmp_path):
                (_, ticks) = await _count_ticks_while(
                    service.process_and_save_cover_image(_make_upload(), "book1")
                )

        assert ticks > 0, (
            "the event loop was blocked for the whole encode — health checks and "
            "every other request on this worker would have stalled (#346)"
        )

    @pytest.mark.asyncio
    async def test_profile_processing_keeps_the_loop_responsive(self, tmp_path):
        service = FileUploadService()
        service.cloud_storage = None

        real = fus._process_profile_sync

        def slow(*args, **kwargs):
            time.sleep(BLOCKING_SECONDS)
            return real(*args, **kwargs)

        with patch.object(fus, "_process_profile_sync", side_effect=slow):
            with patch.object(fus, "PROFILE_PICTURES_DIR", tmp_path):
                (_, ticks) = await _count_ticks_while(
                    service.process_and_save_profile_picture(_make_upload(), "user1")
                )

        assert ticks > 0

    @pytest.mark.asyncio
    async def test_validation_keeps_the_loop_responsive(self):
        """Validation decodes the image too — same blocking class."""
        service = FileUploadService()
        real = fus._validate_image_sync

        def slow(*args, **kwargs):
            time.sleep(BLOCKING_SECONDS)
            return real(*args, **kwargs)

        with patch.object(fus, "_validate_image_sync", side_effect=slow):
            ((ok, _), ticks) = await _count_ticks_while(
                service.validate_image_upload(_make_upload())
            )

        assert ok is True
        assert ticks > 0


class TestCloudStorageOffload:
    @pytest.mark.asyncio
    async def test_s3_upload_keeps_the_loop_responsive(self):
        """boto3 is synchronous; a multi-second S3 round-trip must not freeze the loop."""
        from app.services.cloud_storage_service import S3StorageService

        service = S3StorageService.__new__(S3StorageService)
        service.bucket_name = "b"
        service.region = "us-east-1"
        service.ClientError = Exception
        service.s3_client = Mock()
        service.s3_client.put_object = Mock(
            side_effect=lambda **kw: time.sleep(BLOCKING_SECONDS)
        )

        (url, ticks) = await _count_ticks_while(
            service.upload_image(b"data", "a.jpg", "image/jpeg")
        )

        assert url.startswith("https://b.s3.us-east-1.amazonaws.com/")
        assert ticks > 0, "the S3 round-trip blocked the event loop (#346)"

    @pytest.mark.asyncio
    async def test_s3_delete_keeps_the_loop_responsive(self):
        from app.services.cloud_storage_service import S3StorageService

        service = S3StorageService.__new__(S3StorageService)
        service.bucket_name = "b"
        service.region = "us-east-1"
        service.ClientError = Exception
        service.s3_client = Mock()
        service.s3_client.delete_object = Mock(
            side_effect=lambda **kw: time.sleep(BLOCKING_SECONDS)
        )

        url = "https://b.s3.us-east-1.amazonaws.com/cover_images/x.jpg"
        (ok, ticks) = await _count_ticks_while(service.delete_image(url))

        assert ok is True
        assert ticks > 0

    @pytest.mark.asyncio
    async def test_cloudinary_upload_keeps_the_loop_responsive(self):
        from app.services.cloud_storage_service import CloudinaryStorageService

        service = CloudinaryStorageService.__new__(CloudinaryStorageService)
        uploader = Mock()

        def slow_upload(*a, **kw):
            time.sleep(BLOCKING_SECONDS)
            return {"secure_url": "https://res.cloudinary.com/x/image/upload/v1/a.jpg"}

        uploader.upload = Mock(side_effect=slow_upload)
        service.cloudinary_uploader = uploader

        (url, ticks) = await _count_ticks_while(
            service.upload_image(b"data", "a.jpg", "image/jpeg")
        )

        assert url.endswith("a.jpg")
        assert ticks > 0

    @pytest.mark.asyncio
    async def test_cloudinary_destroy_keeps_the_loop_responsive(self):
        from app.services.cloud_storage_service import CloudinaryStorageService

        service = CloudinaryStorageService.__new__(CloudinaryStorageService)
        uploader = Mock()

        def slow_destroy(*a, **kw):
            time.sleep(BLOCKING_SECONDS)
            return {"result": "ok"}

        uploader.destroy = Mock(side_effect=slow_destroy)
        service.cloudinary_uploader = uploader

        url = "https://res.cloudinary.com/demo/image/upload/v1234/cover_images/a.jpg"
        (ok, ticks) = await _count_ticks_while(service.delete_image(url))

        assert ok is True
        assert ticks > 0
