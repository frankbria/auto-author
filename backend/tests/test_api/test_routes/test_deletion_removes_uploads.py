"""Deleting a book or an account removes its uploaded files (#785).

Real files in a per-test directory and real MongoDB. Storage is pinned to local
mode so a developer's backend/.env cloud credentials are never reached.
"""

import logging
from io import BytesIO
from types import SimpleNamespace

import pytest
from bson import ObjectId
from PIL import Image

import app.db.book as book_dao
import app.services.file_upload_service as fus
from app.db.base import get_collection
from app.db.book import delete_all_user_books, delete_book
from app.db.user import delete_user

pytestmark = pytest.mark.asyncio


@pytest.fixture
def uploads(tmp_path, monkeypatch):
    covers = tmp_path / "cover_images"
    avatars = tmp_path / "profile_pictures"
    covers.mkdir()
    avatars.mkdir()
    monkeypatch.setattr(fus, "COVER_IMAGES_DIR", covers)
    monkeypatch.setattr(fus, "PROFILE_PICTURES_DIR", avatars)
    monkeypatch.setattr(fus, "get_cloud_storage_service", lambda: None)
    return SimpleNamespace(covers=covers, avatars=avatars, root=tmp_path)


def _names(directory):
    return sorted(p.name for p in directory.iterdir())


async def _book_with_cover(uploads, owner_id: str, stem: str) -> str:
    """Insert a book whose cover and thumbnail exist on disk. Returns its id."""
    (uploads.covers / f"{stem}.jpg").write_bytes(b"cover")
    (uploads.covers / f"{stem}_thumb.jpg").write_bytes(b"thumb")
    books = await get_collection("books")
    result = await books.insert_one(
        {
            "title": "Doomed",
            "owner_id": owner_id,
            "cover_image_url": f"/uploads/cover_images/{stem}.jpg",
            "cover_thumbnail_url": f"/uploads/cover_images/{stem}_thumb.jpg",
        }
    )
    return str(result.inserted_id)


async def _user_with_avatar(uploads, auth_id: str) -> None:
    (uploads.avatars / f"{auth_id}.jpg").write_bytes(b"avatar")
    users = await get_collection("users")
    await users.insert_one(
        {
            "auth_id": auth_id,
            "email": f"{auth_id}@example.com",
            "avatar_url": f"/uploads/profile_pictures/{auth_id}.jpg",
        }
    )


def _block_storage(uploads, monkeypatch, attr: str):
    """Make FileUploadService() fail for real: its directory sits under a file."""
    blocker = uploads.root / "blocker"
    blocker.write_text("not a directory")
    monkeypatch.setattr(fus, attr, blocker / "nested")


def _jpeg() -> BytesIO:
    buf = BytesIO()
    Image.new("RGB", (64, 96), color="red").save(buf, format="JPEG")
    buf.seek(0)
    return buf


# --- book deletion -----------------------------------------------------------


async def test_delete_book_removes_cover_and_thumbnail(motor_reinit_db, uploads):
    book_id = await _book_with_cover(uploads, "owner-1", "a")

    assert await delete_book(book_id, "owner-1") is True

    assert _names(uploads.covers) == []


async def test_failed_cascade_keeps_the_cover_files(
    motor_reinit_db, uploads, monkeypatch
):
    """The book survives a failed cascade, so its cover has to survive too."""
    book_id = await _book_with_cover(uploads, "owner-2", "b")

    async def _boom(*args):
        raise RuntimeError("simulated mongo failure")

    monkeypatch.setattr(book_dao, "_delete_book_internal", _boom)

    with pytest.raises(RuntimeError):
        await delete_book(book_id, "owner-2")

    assert _names(uploads.covers) == ["b.jpg", "b_thumb.jpg"]


async def test_non_owner_delete_keeps_the_cover_files(motor_reinit_db, uploads):
    book_id = await _book_with_cover(uploads, "owner-3", "c")

    assert await delete_book(book_id, "someone-else") is False

    assert _names(uploads.covers) == ["c.jpg", "c_thumb.jpg"]


async def test_storage_failure_is_logged_and_the_book_is_still_deleted(
    motor_reinit_db, uploads, monkeypatch, caplog
):
    book_id = await _book_with_cover(uploads, "owner-4", "d")
    _block_storage(uploads, monkeypatch, "COVER_IMAGES_DIR")

    with caplog.at_level(logging.ERROR, logger="app.db.book"):
        assert await delete_book(book_id, "owner-4") is True

    books = await get_collection("books")
    assert await books.find_one({"_id": ObjectId(book_id)}) is None
    assert any(book_id in record.getMessage() for record in caplog.records)


async def test_delete_all_user_books_removes_every_cover_of_that_owner(
    motor_reinit_db, uploads
):
    await _book_with_cover(uploads, "victim", "v1")
    await _book_with_cover(uploads, "victim", "v2")
    await _book_with_cover(uploads, "bystander", "kept")

    assert await delete_all_user_books("victim") == 2

    assert _names(uploads.covers) == ["kept.jpg", "kept_thumb.jpg"]


# --- account deletion --------------------------------------------------------


@pytest.mark.parametrize("soft_delete", [True, False])
async def test_delete_user_removes_the_avatar(motor_reinit_db, uploads, soft_delete):
    await _user_with_avatar(uploads, "gone")
    await _user_with_avatar(uploads, "bystander")

    assert await delete_user("gone", soft_delete=soft_delete) is True

    assert _names(uploads.avatars) == ["bystander.jpg"]


async def test_avatar_storage_failure_is_logged_and_the_user_is_still_erased(
    motor_reinit_db, uploads, monkeypatch, caplog
):
    await _user_with_avatar(uploads, "gone-2")
    _block_storage(uploads, monkeypatch, "PROFILE_PICTURES_DIR")

    with caplog.at_level(logging.ERROR, logger="app.db.user"):
        assert await delete_user("gone-2") is True

    users = await get_collection("users")
    doc = await users.find_one({"auth_id": "gone-2"})
    assert set(doc) == {"_id", "auth_id", "deleted_at"}
    assert any("gone-2" in record.getMessage() for record in caplog.records)


# --- cloud storage -----------------------------------------------------------


class _FakeCloud:
    """Stands in for S3/Cloudinary, the one dependency here with no local form."""

    def __init__(self):
        self.deleted = []

    async def delete_image(self, url: str) -> bool:
        if "unreachable" in url:
            raise ConnectionError("storage unreachable")
        if "foreign" in url:
            return False  # what both providers return for a URL they don't own
        self.deleted.append(url)
        return True


@pytest.fixture
def cloud(monkeypatch):
    fake = _FakeCloud()
    monkeypatch.setattr(fus, "get_cloud_storage_service", lambda: fake)
    return fake


async def _cloud_book(owner_id: str, cover: str, thumbnail: str) -> str:
    books = await get_collection("books")
    result = await books.insert_one(
        {
            "title": "Doomed",
            "owner_id": owner_id,
            "cover_image_url": f"https://cdn.example.com/{cover}",
            "cover_thumbnail_url": f"https://cdn.example.com/{thumbnail}",
        }
    )
    return str(result.inserted_id)


async def test_cloud_book_delete_removes_cover_and_thumbnail(motor_reinit_db, cloud):
    book_id = await _cloud_book("owner-5", "c.jpg", "c_thumb.jpg")

    assert await delete_book(book_id, "owner-5") is True

    assert cloud.deleted == [
        "https://cdn.example.com/c.jpg",
        "https://cdn.example.com/c_thumb.jpg",
    ]


async def test_cloud_thumbnail_is_deleted_even_when_the_cover_delete_raises(
    motor_reinit_db, cloud, caplog
):
    book_id = await _cloud_book("owner-6", "unreachable.jpg", "t_thumb.jpg")

    with caplog.at_level(logging.ERROR, logger="app.services.file_upload_service"):
        assert await delete_book(book_id, "owner-6") is True

    assert cloud.deleted == ["https://cdn.example.com/t_thumb.jpg"]
    assert any("unreachable" in record.getMessage() for record in caplog.records)


async def test_cloud_refusing_a_cover_is_logged(motor_reinit_db, cloud, caplog):
    """A False from the provider is a file left behind; it must not be silent."""
    book_id = await _cloud_book("owner-7", "foreign.jpg", "foreign_thumb.jpg")

    with caplog.at_level(logging.WARNING, logger="app.services.file_upload_service"):
        assert await delete_book(book_id, "owner-7") is True

    messages = [record.getMessage() for record in caplog.records]
    assert any("foreign.jpg" in m for m in messages)
    assert any("foreign_thumb.jpg" in m for m in messages)


async def test_cloud_refusing_an_avatar_is_logged(motor_reinit_db, cloud, caplog):
    users = await get_collection("users")
    await users.insert_one(
        {"auth_id": "gone-3", "avatar_url": "https://cdn.example.com/foreign-a.jpg"}
    )

    with caplog.at_level(logging.WARNING, logger="app.services.file_upload_service"):
        assert await delete_user("gone-3") is True

    assert any("foreign-a.jpg" in r.getMessage() for r in caplog.records)


# --- routes ------------------------------------------------------------------


async def test_book_delete_route_removes_an_uploaded_cover(
    auth_client_factory, test_user, uploads
):
    """Upload through the real route, so the stored URLs are the real ones."""
    client = await auth_client_factory()
    books = await get_collection("books")
    book_id = str(
        (
            await books.insert_one({"title": "T", "owner_id": test_user["auth_id"]})
        ).inserted_id
    )
    upload = await client.post(
        f"/api/v1/books/{book_id}/cover-image",
        files={"file": ("cover.jpg", _jpeg(), "image/jpeg")},
    )
    assert upload.status_code == 200, upload.text
    assert len(_names(uploads.covers)) == 2

    response = await client.delete(f"/api/v1/books/{book_id}")

    assert response.status_code == 204, response.text
    assert _names(uploads.covers) == []


async def test_account_delete_route_removes_avatar_and_covers(
    auth_client_factory, test_user, uploads
):
    (uploads.avatars / "me.jpg").write_bytes(b"avatar")
    client = await auth_client_factory(
        overrides={"avatar_url": "/uploads/profile_pictures/me.jpg"}
    )
    await _book_with_cover(uploads, test_user["auth_id"], "mine-1")
    await _book_with_cover(uploads, test_user["auth_id"], "mine-2")

    response = await client.delete("/api/v1/users/me")

    assert response.status_code == 200, response.text
    assert _names(uploads.avatars) == []
    assert _names(uploads.covers) == []


async def test_admin_delete_route_removes_the_target_users_files(
    auth_client_factory, uploads
):
    """The admin's own session carries the admin's avatar_url, not the target's."""
    (uploads.avatars / "admin.jpg").write_bytes(b"avatar")
    client = await auth_client_factory(
        overrides={
            "auth_id": "admin-1",
            "role": "admin",
            "avatar_url": "/uploads/profile_pictures/admin.jpg",
        }
    )
    await _user_with_avatar(uploads, "target-1")
    await _book_with_cover(uploads, "target-1", "theirs")

    response = await client.delete("/api/v1/users/target-1")

    assert response.status_code == 204, response.text
    assert _names(uploads.avatars) == ["admin.jpg"]
    assert _names(uploads.covers) == []
