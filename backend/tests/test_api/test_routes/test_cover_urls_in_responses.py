"""Book responses carry the cover thumbnail, and only covers the server wrote (#941).

A cover_image_url typed into the pre-#797 form field is still stored on some
books. It names a file the server never wrote (an external host, or another
book's file), so the response leaves it out instead of rendering it. The rule is
#797's: the URL must name one of this book's own files in the active storage.

Real MongoDB. Storage is pinned per test; the S3 client is never called.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from bson import ObjectId

import app.services.file_upload_service as fus
from app.core.config import Settings
from app.db.base import get_collection
from app.services.cloud_storage_service import S3StorageService

pytestmark = pytest.mark.asyncio

ME = "test-auth-id-123"  # conftest's test_user
HEX = uuid.uuid4().hex
S3_HOST = "https://bkt.s3.us-east-1.amazonaws.com"


@pytest.fixture
def local(tmp_path, monkeypatch):
    monkeypatch.setattr(fus, "COVER_IMAGES_DIR", tmp_path)
    monkeypatch.setattr(fus, "get_cloud_storage_service", lambda: None)
    monkeypatch.setattr(Settings, "storage_provider", property(lambda self: "local"))


@pytest.fixture
def s3(monkeypatch):
    service = S3StorageService.__new__(S3StorageService)
    service.bucket_name = "bkt"
    service.region = "us-east-1"
    service.s3_client = Mock()
    monkeypatch.setattr(fus, "get_cloud_storage_service", lambda: service)
    monkeypatch.setattr(Settings, "storage_provider", property(lambda self: "s3"))


async def _book_with_cover(cover, thumbnail) -> str:
    """A book of mine whose stored URLs are ``cover(id)`` and ``thumbnail(id)``."""
    books = await get_collection("books")
    now = datetime.now(timezone.utc)
    book_id = ObjectId()
    await books.insert_one(
        {
            "_id": book_id,
            "title": "Covered",
            "owner_id": ME,
            "created_at": now,
            "updated_at": now,
            "cover_image_url": cover(str(book_id)),
            "cover_thumbnail_url": thumbnail(str(book_id)),
        }
    )
    return str(book_id)


async def _responses(client, book_id):
    one = await client.get(f"/api/v1/books/{book_id}")
    assert one.status_code == 200, one.text
    listed = await client.get("/api/v1/books/")
    assert listed.status_code == 200, listed.text
    (mine,) = [b for b in listed.json() if b["id"] == book_id]
    return [one.json(), mine]


async def test_a_local_cover_and_its_thumbnail_are_returned(auth_client_factory, local):
    client = await auth_client_factory()
    book_id = await _book_with_cover(
        lambda i: f"/uploads/cover_images/{i}_{HEX}.jpg",
        lambda i: f"/uploads/cover_images/{i}_{HEX}_thumb.jpg",
    )

    for body in await _responses(client, book_id):
        assert body["cover_image_url"] == f"/uploads/cover_images/{book_id}_{HEX}.jpg"
        assert body["cover_thumbnail_url"] == (
            f"/uploads/cover_images/{book_id}_{HEX}_thumb.jpg"
        )


async def test_a_cloud_cover_and_its_thumbnail_are_returned(auth_client_factory, s3):
    client = await auth_client_factory()
    book_id = await _book_with_cover(
        lambda i: f"{S3_HOST}/cover_images/{i}/{HEX}.jpg",
        lambda i: f"{S3_HOST}/cover_images/{i}/{HEX}_thumb.jpg",
    )

    for body in await _responses(client, book_id):
        assert body["cover_image_url"] == f"{S3_HOST}/cover_images/{book_id}/{HEX}.jpg"
        assert body["cover_thumbnail_url"] == (
            f"{S3_HOST}/cover_images/{book_id}/{HEX}_thumb.jpg"
        )


@pytest.mark.parametrize(
    "legacy",
    [
        lambda i: "https://example.com/my-cover.jpg",  # typed into the old field
        lambda i: f"/uploads/cover_images/{ObjectId()}_{HEX}.jpg",  # another book's
        lambda i: f"{S3_HOST}/cover_images/{i}/{HEX}.jpg",  # not this storage
    ],
    ids=["external", "another-books-file", "other-storage"],
)
async def test_a_cover_the_server_did_not_write_is_not_returned(
    auth_client_factory, local, legacy
):
    client = await auth_client_factory()
    book_id = await _book_with_cover(legacy, legacy)

    for body in await _responses(client, book_id):
        assert body["cover_image_url"] is None
        assert body["cover_thumbnail_url"] is None
