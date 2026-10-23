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
import threading
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


class _Heartbeat:
    """Prove the loop ran *while* the blocking call was in flight.

    Counting ticks over a fixed sleep is a race: a loop stall as long as the
    sleep (CI steal, GC) lets the offloaded call finish before the first tick,
    so a correct offload reads 0 (#1202). Instead the stand-in for the slow
    call, ``block``, waits for the heartbeat to tick. Offloaded, the loop ticks
    and ``block`` returns at once; run on the loop thread, nothing can tick, so
    ``block`` times out and ``loop_ran`` stays False. No timing assumption on
    the passing path.
    """

    TIMEOUT = 2.0  # only ever waited out when the loop is actually blocked

    def __init__(self):
        self._ticked = threading.Event()
        self.loop_ran = None

    def block(self, *args, **kwargs):
        self.loop_ran = self._ticked.wait(self.TIMEOUT)

    async def run(self, coro):
        async def heartbeat():
            while True:
                await asyncio.sleep(0.005)
                self._ticked.set()

        beat = asyncio.create_task(heartbeat())
        try:
            return await coro
        finally:
            beat.cancel()
            try:
                await beat
            except asyncio.CancelledError:
                pass


LOOP_BLOCKED = (
    "the event loop was blocked for the whole call — health checks and every "
    "other request on this worker would have stalled (#346)"
)


@pytest.fixture
def hb():
    return _Heartbeat()


class TestImageProcessingOffload:
    @pytest.mark.asyncio
    async def test_cover_processing_keeps_the_loop_responsive(self, tmp_path, hb):
        """A slow PIL encode must not freeze the loop."""
        service = FileUploadService()
        service.cloud_storage = None

        real = fus._process_cover_sync

        def slow(*args, **kwargs):
            hb.block()  # stand-in for a large LANCZOS + encode
            return real(*args, **kwargs)

        with patch.object(fus, "_process_cover_sync", side_effect=slow):
            with patch.object(fus, "COVER_IMAGES_DIR", tmp_path):
                await hb.run(
                    service.process_and_save_cover_image(_make_upload(), "book1")
                )

        assert hb.loop_ran, LOOP_BLOCKED

    @pytest.mark.asyncio
    async def test_profile_processing_keeps_the_loop_responsive(self, tmp_path, hb):
        service = FileUploadService()
        service.cloud_storage = None

        real = fus._process_profile_sync

        def slow(*args, **kwargs):
            hb.block()
            return real(*args, **kwargs)

        with patch.object(fus, "_process_profile_sync", side_effect=slow):
            with patch.object(fus, "PROFILE_PICTURES_DIR", tmp_path):
                await hb.run(
                    service.process_and_save_profile_picture(_make_upload(), "user1")
                )

        assert hb.loop_ran, LOOP_BLOCKED

    @pytest.mark.asyncio
    async def test_validation_keeps_the_loop_responsive(self, hb):
        """Validation decodes the image too — same blocking class."""
        service = FileUploadService()
        real = fus._validate_image_sync

        def slow(*args, **kwargs):
            hb.block()
            return real(*args, **kwargs)

        with patch.object(fus, "_validate_image_sync", side_effect=slow):
            (ok, _) = await hb.run(
                service.validate_image_upload(_make_upload())
            )

        assert ok is True
        assert hb.loop_ran, LOOP_BLOCKED


class TestCloudStorageOffload:
    @pytest.mark.asyncio
    async def test_s3_upload_keeps_the_loop_responsive(self, hb):
        """boto3 is synchronous; a multi-second S3 round-trip must not freeze the loop."""
        from app.services.cloud_storage_service import S3StorageService

        service = S3StorageService.__new__(S3StorageService)
        service.bucket_name = "b"
        service.region = "us-east-1"
        service.ClientError = Exception
        service.s3_client = Mock()
        service.s3_client.put_object = Mock(
            side_effect=lambda **kw: hb.block()
        )

        url = await hb.run(
            service.upload_image(b"data", "a.jpg", "image/jpeg")
        )

        assert url.startswith("https://b.s3.us-east-1.amazonaws.com/")
        assert hb.loop_ran, LOOP_BLOCKED

    @pytest.mark.asyncio
    async def test_s3_delete_keeps_the_loop_responsive(self, hb):
        from app.services.cloud_storage_service import S3StorageService

        service = S3StorageService.__new__(S3StorageService)
        service.bucket_name = "b"
        service.region = "us-east-1"
        service.ClientError = Exception
        service.s3_client = Mock()
        service.s3_client.delete_object = Mock(
            side_effect=lambda **kw: hb.block()
        )

        url = "https://b.s3.us-east-1.amazonaws.com/cover_images/x.jpg"
        ok = await hb.run(
            service.delete_image(url, "cover_images/")
        )

        assert ok is True
        assert hb.loop_ran, LOOP_BLOCKED

    @pytest.mark.asyncio
    async def test_cloudinary_upload_keeps_the_loop_responsive(self, hb):
        from app.services.cloud_storage_service import CloudinaryStorageService

        service = CloudinaryStorageService.__new__(CloudinaryStorageService)

        service.cloud_name = "demo"
        uploader = Mock()

        def slow_upload(*a, **kw):
            hb.block()
            return {"secure_url": "https://res.cloudinary.com/x/image/upload/v1/a.jpg"}

        uploader.upload = Mock(side_effect=slow_upload)
        service.cloudinary_uploader = uploader

        url = await hb.run(
            service.upload_image(b"data", "a.jpg", "image/jpeg")
        )

        assert url.endswith("a.jpg")
        assert hb.loop_ran, LOOP_BLOCKED

    @pytest.mark.asyncio
    async def test_cloudinary_destroy_keeps_the_loop_responsive(self, hb):
        from app.services.cloud_storage_service import CloudinaryStorageService

        service = CloudinaryStorageService.__new__(CloudinaryStorageService)

        service.cloud_name = "demo"
        uploader = Mock()

        def slow_destroy(*a, **kw):
            hb.block()
            return {"result": "ok"}

        uploader.destroy = Mock(side_effect=slow_destroy)
        service.cloudinary_uploader = uploader

        url = "https://res.cloudinary.com/demo/image/upload/v1234/cover_images/a.jpg"
        ok = await hb.run(
            service.delete_image(url, "cover_images/")
        )

        assert ok is True
        assert hb.loop_ran, LOOP_BLOCKED


class TestCoverUploadRollback:
    """A failed thumbnail upload must not orphan the main image.

    The two uploads are sequential and not atomic. Pre-existing gap, fixed here
    because #346 rewrote this exact block: without a rollback the main image
    stays in the bucket forever while the caller gets a 500 and never learns
    the URL, so nothing will ever reference or clean it up.
    """

    @pytest.mark.asyncio
    async def test_main_image_is_deleted_when_the_thumbnail_upload_fails(self, hb):
        from unittest.mock import AsyncMock

        service = FileUploadService()
        cloud = Mock()
        cloud.upload_image = AsyncMock(
            side_effect=["https://cdn/main.jpg", RuntimeError("S3 exploded")]
        )
        cloud.delete_image = AsyncMock(return_value=True)
        service.cloud_storage = cloud

        with pytest.raises(Exception):
            await service.process_and_save_cover_image(_make_upload(), "book1")

        cloud.delete_image.assert_awaited_once_with(
            "https://cdn/main.jpg", "cover_images/book1/"
        )

    @pytest.mark.asyncio
    async def test_rollback_failure_does_not_mask_the_upload_failure(self, hb):
        """If cleanup also fails, the caller must still see the original error."""
        from unittest.mock import AsyncMock

        service = FileUploadService()
        cloud = Mock()
        cloud.upload_image = AsyncMock(
            side_effect=["https://cdn/main.jpg", RuntimeError("S3 exploded")]
        )
        cloud.delete_image = AsyncMock(side_effect=RuntimeError("delete also failed"))
        service.cloud_storage = cloud

        with pytest.raises(Exception) as exc:
            await service.process_and_save_cover_image(_make_upload(), "book1")

        # The handler converts to a 500; what matters is that the delete failure
        # did not replace or swallow the real cause.
        assert "delete also failed" not in str(exc.value)
