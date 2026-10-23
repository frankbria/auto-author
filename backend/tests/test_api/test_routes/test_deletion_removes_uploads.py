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
import app.db.book_delete as book_delete_dao
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


# Files are named the way the upload service names them, <owner>_<uuid hex>:
# the delete helpers refuse anything else (#797).
_HEX = "0" * 32


def _cover_files(book_id: str) -> list:
    return [f"{book_id}_{_HEX}.jpg", f"{book_id}_{_HEX}_thumb.jpg"]


def _avatar_file(auth_id: str) -> str:
    return f"{auth_id}_{_HEX}.jpg"


async def _book_with_cover(uploads, owner_id: str) -> str:
    """Insert a book whose cover and thumbnail exist on disk. Returns its id."""
    book_id = str(ObjectId())
    cover, thumb = _cover_files(book_id)
    (uploads.covers / cover).write_bytes(b"cover")
    (uploads.covers / thumb).write_bytes(b"thumb")
    books = await get_collection("books")
    await books.insert_one(
        {
            "_id": ObjectId(book_id),
            "title": "Doomed",
            "owner_id": owner_id,
            "cover_image_url": f"/uploads/cover_images/{cover}",
            "cover_thumbnail_url": f"/uploads/cover_images/{thumb}",
        }
    )
    return book_id


async def _user_with_avatar(uploads, auth_id: str) -> None:
    (uploads.avatars / _avatar_file(auth_id)).write_bytes(b"avatar")
    users = await get_collection("users")
    await users.insert_one(
        {
            "auth_id": auth_id,
            "email": f"{auth_id}@example.com",
            "avatar_url": f"/uploads/profile_pictures/{_avatar_file(auth_id)}",
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


async def test_delete_book_removes_cover_and_thumbnail(reinit_db, uploads):
    book_id = await _book_with_cover(uploads, "owner-1")

    assert await delete_book(book_id, "owner-1") is True

    assert _names(uploads.covers) == []


@pytest.mark.parametrize(
    "delete", [delete_book, lambda _book_id, owner: delete_all_user_books(owner)]
)
async def test_failed_cascade_keeps_the_cover_files(
    reinit_db, uploads, monkeypatch, delete
):
    """The book survives a failed cascade, so its cover has to survive too."""
    book_id = await _book_with_cover(uploads, "owner-2")

    async def _boom(*args):
        raise RuntimeError("simulated mongo failure")

    monkeypatch.setattr(book_delete_dao, "_delete_books_internal", _boom)

    with pytest.raises(RuntimeError):
        await delete(book_id, "owner-2")

    assert _names(uploads.covers) == _cover_files(book_id)


async def test_non_owner_delete_keeps_the_cover_files(reinit_db, uploads):
    book_id = await _book_with_cover(uploads, "owner-3")

    assert await delete_book(book_id, "someone-else") is False

    assert _names(uploads.covers) == _cover_files(book_id)


async def test_storage_failure_is_logged_and_the_book_is_still_deleted(
    reinit_db, uploads, monkeypatch, caplog
):
    book_id = await _book_with_cover(uploads, "owner-4")
    _block_storage(uploads, monkeypatch, "COVER_IMAGES_DIR")

    with caplog.at_level(logging.ERROR, logger="app.db.book_delete"):
        assert await delete_book(book_id, "owner-4") is True

    books = await get_collection("books")
    assert await books.find_one({"_id": ObjectId(book_id)}) is None
    assert any(book_id in record.getMessage() for record in caplog.records)


async def test_delete_all_user_books_removes_every_cover_of_that_owner(
    reinit_db, uploads
):
    await _book_with_cover(uploads, "victim")
    await _book_with_cover(uploads, "victim")
    kept = await _book_with_cover(uploads, "bystander")

    assert await delete_all_user_books("victim") == 2

    assert _names(uploads.covers) == _cover_files(kept)


# --- account deletion --------------------------------------------------------


async def test_delete_user_removes_the_avatar(reinit_db, uploads):
    await _user_with_avatar(uploads, "gone")
    await _user_with_avatar(uploads, "bystander")

    assert await delete_user("gone") is True

    assert _names(uploads.avatars) == [_avatar_file("bystander")]


async def test_avatar_storage_failure_is_logged_and_the_user_is_still_erased(
    reinit_db, uploads, monkeypatch, caplog
):
    await _user_with_avatar(uploads, "gone-2")
    _block_storage(uploads, monkeypatch, "PROFILE_PICTURES_DIR")

    with caplog.at_level(logging.ERROR, logger="app.db.user"):
        assert await delete_user("gone-2") is True

    users = await get_collection("users")
    doc = await users.find_one({"auth_id": "gone-2"})
    assert set(doc) == {"_id", "auth_id", "deleted_at", "purge_at", "retained"}
    assert any("gone-2" in record.getMessage() for record in caplog.records)


async def test_book_created_after_the_cascade_read_is_gone_after_deletion(
    reinit_db, uploads
):
    """A POST /books in flight during deletion can land after the cascade's id
    read (#945). The endpoints run the cascade, then delete_user; a book created
    between them must not outlive the account, nor its cover and children."""
    await _user_with_avatar(uploads, "racer")
    await delete_all_user_books("racer")  # the endpoint's pass, before the tombstone

    late_id = str((await book_dao.create_book({"title": "Late"}, "racer"))["_id"])
    cover, thumb = _cover_files(late_id)
    (uploads.covers / cover).write_bytes(b"cover")
    (uploads.covers / thumb).write_bytes(b"thumb")
    books = await get_collection("books")
    await books.update_one(
        {"_id": ObjectId(late_id)},
        {
            "$set": {
                "cover_image_url": f"/uploads/cover_images/{cover}",
                "cover_thumbnail_url": f"/uploads/cover_images/{thumb}",
            }
        },
    )
    questions = await get_collection("questions")
    await questions.insert_one({"book_id": late_id, "user_id": "racer", "text": "Q?"})

    assert await delete_user("racer") is True

    assert await books.count_documents({"owner_id": "racer"}) == 0
    assert await questions.count_documents({"book_id": late_id}) == 0
    assert _names(uploads.covers) == []


async def test_book_created_after_deletion_returns_is_not_kept(reinit_db, uploads):
    """The insert of a request still in flight can land after delete_user's
    second pass too (#945); create_book then finds the tombstone itself."""
    await _user_with_avatar(uploads, "racer-2")
    assert await delete_user("racer-2") is True

    with pytest.raises(ValueError):
        await book_dao.create_book({"title": "Later"}, "racer-2")

    books = await get_collection("books")
    assert await books.count_documents({"owner_id": "racer-2"}) == 0


# --- cloud storage -----------------------------------------------------------


class _FakeCloud:
    """Stands in for S3/Cloudinary, the one dependency here with no local form."""

    def __init__(self):
        self.deleted = []
        self.prefixes = set()

    async def delete_image(self, url: str, key_prefix: str) -> bool:
        self.prefixes.add(key_prefix)
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


async def test_cloud_book_delete_removes_cover_and_thumbnail(reinit_db, cloud):
    book_id = await _cloud_book("owner-5", "c.jpg", "c_thumb.jpg")

    assert await delete_book(book_id, "owner-5") is True

    assert cloud.deleted == [
        "https://cdn.example.com/c.jpg",
        "https://cdn.example.com/c_thumb.jpg",
    ]
    assert cloud.prefixes == {f"cover_images/{book_id}/"}


async def test_cloud_thumbnail_is_deleted_even_when_the_cover_delete_raises(
    reinit_db, cloud, caplog
):
    book_id = await _cloud_book("owner-6", "unreachable.jpg", "t_thumb.jpg")

    with caplog.at_level(logging.ERROR, logger="app.services.file_upload_service"):
        assert await delete_book(book_id, "owner-6") is True

    assert cloud.deleted == ["https://cdn.example.com/t_thumb.jpg"]
    assert any("unreachable" in record.getMessage() for record in caplog.records)


async def test_cloud_refusing_a_cover_is_logged(reinit_db, cloud, caplog):
    """A False from the provider is a file left behind; it must not be silent."""
    book_id = await _cloud_book("owner-7", "foreign.jpg", "foreign_thumb.jpg")

    with caplog.at_level(logging.WARNING, logger="app.services.file_upload_service"):
        assert await delete_book(book_id, "owner-7") is True

    messages = [record.getMessage() for record in caplog.records]
    assert any("foreign.jpg" in m for m in messages)
    assert any("foreign_thumb.jpg" in m for m in messages)


async def test_cloud_refusing_an_avatar_is_logged(reinit_db, cloud, caplog):
    users = await get_collection("users")
    await users.insert_one(
        {"auth_id": "gone-3", "avatar_url": "https://cdn.example.com/foreign-a.jpg"}
    )

    with caplog.at_level(logging.WARNING, logger="app.services.file_upload_service"):
        assert await delete_user("gone-3") is True

    assert any("foreign-a.jpg" in r.getMessage() for r in caplog.records)
    assert cloud.prefixes == {"profile_pictures/gone-3/"}


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
    mine = _avatar_file(test_user["auth_id"])
    (uploads.avatars / mine).write_bytes(b"avatar")
    client = await auth_client_factory(
        overrides={"avatar_url": f"/uploads/profile_pictures/{mine}"}
    )
    await _book_with_cover(uploads, test_user["auth_id"])
    await _book_with_cover(uploads, test_user["auth_id"])

    response = await client.delete("/api/v1/users/me")

    assert response.status_code == 200, response.text
    assert _names(uploads.avatars) == []
    assert _names(uploads.covers) == []


async def test_admin_delete_route_removes_the_target_users_files(
    auth_client_factory, uploads
):
    """The admin's own session carries the admin's avatar_url, not the target's."""
    (uploads.avatars / _avatar_file("admin-1")).write_bytes(b"avatar")
    client = await auth_client_factory(
        overrides={
            "auth_id": "admin-1",
            "role": "admin",
            "avatar_url": f"/uploads/profile_pictures/{_avatar_file('admin-1')}",
        }
    )
    await _user_with_avatar(uploads, "target-1")
    await _book_with_cover(uploads, "target-1")

    response = await client.delete("/api/v1/users/target-1")

    assert response.status_code == 204, response.text
    assert _names(uploads.avatars) == [_avatar_file("admin-1")]
    assert _names(uploads.covers) == []


# --- races that used to orphan a cover (#938) --------------------------------


async def test_delete_book_removes_a_cover_replaced_after_its_ownership_check(
    reinit_db, uploads, monkeypatch
):
    """A cover upload landing between delete_book's read and its delete swaps
    the pair; the delete must remove the pair the book had when it went."""
    book_id = await _book_with_cover(uploads, "owner-8")
    new_cover, new_thumb = f"{book_id}_{'1' * 32}.jpg", f"{book_id}_{'1' * 32}_thumb.jpg"
    real = book_delete_dao._delete_books_internal

    async def _upload_lands_first(*args):
        (uploads.covers / new_cover).write_bytes(b"new")
        (uploads.covers / new_thumb).write_bytes(b"new")
        for name in _cover_files(book_id):  # the upload removes the old pair itself
            (uploads.covers / name).unlink()
        books = await get_collection("books")
        await books.update_one(
            {"_id": ObjectId(book_id)},
            {"$set": {
                "cover_image_url": f"/uploads/cover_images/{new_cover}",
                "cover_thumbnail_url": f"/uploads/cover_images/{new_thumb}",
            }},
        )
        return await real(*args)

    monkeypatch.setattr(book_delete_dao, "_delete_books_internal", _upload_lands_first)

    assert await delete_book(book_id, "owner-8") is True

    assert _names(uploads.covers) == []


async def test_overlapping_cover_uploads_leave_no_orphan(
    auth_client_factory, test_user, uploads, monkeypatch
):
    """Both requests read the book before either writes; whichever write lands
    second must remove the pair the first one wrote."""
    import asyncio

    client = await auth_client_factory()
    books = await get_collection("books")
    book_id = str(
        (await books.insert_one({"title": "T", "owner_id": test_user["auth_id"]})).inserted_id
    )
    both_saved = asyncio.Barrier(2)
    real = fus.FileUploadService.process_and_save_cover_image

    async def _save_then_wait(self, *args, **kwargs):
        urls = await real(self, *args, **kwargs)
        await asyncio.wait_for(both_saved.wait(), timeout=10)
        return urls

    monkeypatch.setattr(fus.FileUploadService, "process_and_save_cover_image", _save_then_wait)

    responses = await asyncio.gather(*(
        client.post(
            f"/api/v1/books/{book_id}/cover-image",
            files={"file": ("cover.jpg", _jpeg(), "image/jpeg")},
        )
        for _ in range(2)
    ))

    assert [r.status_code for r in responses] == [200, 200], [r.text for r in responses]
    book = await books.find_one({"_id": ObjectId(book_id)})
    assert _names(uploads.covers) == sorted(
        url.rsplit("/", 1)[1] for url in (book["cover_image_url"], book["cover_thumbnail_url"])
    )


async def test_overlapping_avatar_uploads_leave_no_orphan(
    auth_client_factory, test_user, uploads, monkeypatch
):
    """Both requests start from a session that still shows the old avatar; the
    file each write replaced must go, not the session's copy twice (#1143)."""
    import asyncio

    auth_id = test_user["auth_id"]
    old = _avatar_file(auth_id)
    (uploads.avatars / old).write_bytes(b"old")
    old_url = f"/uploads/profile_pictures/{old}"
    users = await get_collection("users")
    client = await auth_client_factory(overrides={"avatar_url": old_url})
    both_saved = asyncio.Barrier(2)
    real = fus.FileUploadService.process_and_save_profile_picture

    async def _save_then_wait(self, *args, **kwargs):
        url = await real(self, *args, **kwargs)
        await asyncio.wait_for(both_saved.wait(), timeout=10)
        return url

    monkeypatch.setattr(
        fus.FileUploadService, "process_and_save_profile_picture", _save_then_wait
    )

    responses = await asyncio.gather(*(
        client.post(
            "/api/v1/users/me/avatar",
            files={"file": ("a.jpg", _jpeg(), "image/jpeg")},
        )
        for _ in range(2)
    ))

    assert [r.status_code for r in responses] == [200, 200], [r.text for r in responses]
    user = await users.find_one({"auth_id": auth_id})
    assert _names(uploads.avatars) == [user["avatar_url"].rsplit("/", 1)[1]]
