"""cover_image_url and avatar_url are written by the server only (#797).

Both were client-writable, and the stored value is what the upload and delete
paths hand to storage as the file to remove. One tenant could name another's
object and have it deleted.

Real files in a per-test directory and real MongoDB. Storage is pinned to local
mode so a developer's backend/.env cloud credentials are never reached.
"""

import uuid
from datetime import datetime, timezone
from io import BytesIO
from types import SimpleNamespace

import pytest
from bson import ObjectId
from PIL import Image

import app.services.file_upload_service as fus
from app.api.endpoints import books as books_endpoint
from app.db.base import get_collection

pytestmark = pytest.mark.asyncio

ME = "test-auth-id-123"  # conftest's test_user
VICTIM = "victim-auth-id"


@pytest.fixture
def uploads(tmp_path, monkeypatch):
    covers = tmp_path / "cover_images"
    avatars = tmp_path / "profile_pictures"
    covers.mkdir()
    avatars.mkdir()
    monkeypatch.setattr(fus, "COVER_IMAGES_DIR", covers)
    monkeypatch.setattr(fus, "PROFILE_PICTURES_DIR", avatars)
    monkeypatch.setattr(fus, "get_cloud_storage_service", lambda: None)
    return SimpleNamespace(covers=covers, avatars=avatars)


def _names(directory):
    return sorted(p.name for p in directory.iterdir())


def _jpeg() -> BytesIO:
    buf = BytesIO()
    Image.new("RGB", (64, 96), color="red").save(buf, format="JPEG")
    buf.seek(0)
    return buf


async def _book(owner_id: str, **fields) -> str:
    books = await get_collection("books")
    now = datetime.now(timezone.utc)
    doc = {"title": "T", "owner_id": owner_id, "created_at": now, "updated_at": now}
    doc.update(fields)
    return str((await books.insert_one(doc)).inserted_id)


async def _stored(book_id: str) -> dict:
    books = await get_collection("books")
    return await books.find_one({"_id": ObjectId(book_id)})


async def _victim_book_with_cover(uploads) -> SimpleNamespace:
    """Another tenant's book, with the files the server would have written."""
    book_id = str(ObjectId())
    cover = f"{book_id}_{uuid.uuid4().hex}.jpg"
    thumb = f"{book_id}_{uuid.uuid4().hex}_thumb.jpg"
    (uploads.covers / cover).write_bytes(b"victim cover")
    (uploads.covers / thumb).write_bytes(b"victim thumb")
    books = await get_collection("books")
    await books.insert_one(
        {
            "_id": ObjectId(book_id),
            "title": "Victim",
            "owner_id": VICTIM,
            "cover_image_url": f"/uploads/cover_images/{cover}",
            "cover_thumbnail_url": f"/uploads/cover_images/{thumb}",
        }
    )
    return SimpleNamespace(
        files=[cover, thumb],
        cover_url=f"/uploads/cover_images/{cover}",
        thumbnail_url=f"/uploads/cover_images/{thumb}",
    )


async def _upload(client, book_id: str):
    return await client.post(
        f"/api/v1/books/{book_id}/cover-image",
        files={"file": ("cover.jpg", _jpeg(), "image/jpeg")},
    )


# --- the fields are not client-writable --------------------------------------


@pytest.mark.parametrize("method", ["put", "patch"])
async def test_book_update_ignores_cover_image_url(auth_client_factory, method):
    client = await auth_client_factory()
    book_id = await _book(ME, cover_image_url="/uploads/cover_images/server.jpg")

    response = await getattr(client, method)(
        f"/api/v1/books/{book_id}",
        json={"title": "Renamed", "cover_image_url": "https://evil.test/x.jpg"},
    )

    assert response.status_code == 200, response.text
    stored = await _stored(book_id)
    assert stored["title"] == "Renamed"
    assert stored["cover_image_url"] == "/uploads/cover_images/server.jpg"
    # The response still reports the server's value.
    assert response.json()["cover_image_url"] == "/uploads/cover_images/server.jpg"


async def test_an_empty_cover_image_url_does_not_clear_the_stored_one(
    auth_client_factory,
):
    """The metadata form sent '' on every save, which wiped an uploaded cover."""
    client = await auth_client_factory()
    book_id = await _book(ME, cover_image_url="/uploads/cover_images/server.jpg")

    response = await client.put(
        f"/api/v1/books/{book_id}", json={"title": "T2", "cover_image_url": ""}
    )

    assert response.status_code == 200, response.text
    assert (await _stored(book_id))["cover_image_url"] == (
        "/uploads/cover_images/server.jpg"
    )


async def test_book_create_ignores_cover_image_url(auth_client_factory):
    client = await auth_client_factory()

    response = await client.post(
        "/api/v1/books/",
        json={"title": "New", "cover_image_url": "https://evil.test/x.jpg"},
    )

    assert response.status_code == 201, response.text
    assert not (await _stored(response.json()["id"])).get("cover_image_url")
    assert not response.json().get("cover_image_url")


async def test_profile_update_rejects_avatar_url(auth_client_factory):
    client = await auth_client_factory()

    response = await client.patch(
        "/api/v1/users/me", json={"avatar_url": "https://evil.test/a.jpg"}
    )

    assert response.status_code == 422, response.text
    users = await get_collection("users")
    assert (await users.find_one({"auth_id": ME})).get("avatar_url") is None


async def test_user_put_rejects_avatar_url(auth_client_factory):
    client = await auth_client_factory()

    response = await client.put(
        f"/api/v1/users/{ME}", json={"avatar_url": "https://evil.test/a.jpg"}
    )

    assert response.status_code == 422, response.text


# --- a stored URL naming another tenant's file is never deleted --------------


async def test_upload_leaves_a_foreign_cover_named_by_the_stored_url(
    auth_client_factory, uploads
):
    """A's book carries B's URLs (as a pre-#797 client could set). A uploads."""
    client = await auth_client_factory()
    victim = await _victim_book_with_cover(uploads)
    book_id = await _book(
        ME, cover_image_url=victim.cover_url, cover_thumbnail_url=victim.thumbnail_url
    )

    response = await _upload(client, book_id)

    assert response.status_code == 200, response.text
    for name in victim.files:
        assert (uploads.covers / name).exists(), f"victim file {name} was deleted"
    assert len(_names(uploads.covers)) == 4


async def test_book_delete_leaves_a_foreign_cover_named_by_the_stored_url(
    auth_client_factory, uploads
):
    client = await auth_client_factory()
    victim = await _victim_book_with_cover(uploads)
    book_id = await _book(
        ME, cover_image_url=victim.cover_url, cover_thumbnail_url=victim.thumbnail_url
    )

    response = await client.delete(f"/api/v1/books/{book_id}")

    assert response.status_code == 204, response.text
    assert _names(uploads.covers) == sorted(victim.files)


async def test_avatar_upload_and_account_delete_leave_a_foreign_avatar(
    auth_client_factory, uploads
):
    theirs = f"{VICTIM}_{uuid.uuid4().hex}.jpg"
    (uploads.avatars / theirs).write_bytes(b"victim avatar")
    client = await auth_client_factory(
        overrides={"avatar_url": f"/uploads/profile_pictures/{theirs}"}
    )

    upload = await client.post(
        "/api/v1/users/me/avatar",
        files={"file": ("a.jpg", _jpeg(), "image/jpeg")},
    )
    assert upload.status_code == 200, upload.text
    assert (uploads.avatars / theirs).exists()

    # Put the foreign URL back, then delete the account.
    users = await get_collection("users")
    await users.update_one(
        {"auth_id": ME}, {"$set": {"avatar_url": f"/uploads/profile_pictures/{theirs}"}}
    )
    response = await client.delete("/api/v1/users/me")

    assert response.status_code == 200, response.text
    assert (uploads.avatars / theirs).exists()


# --- cover upload: persist first, then delete the old files ------------------


async def test_upload_replaces_the_books_own_previous_cover(
    auth_client_factory, uploads
):
    client = await auth_client_factory()
    book_id = await _book(ME)
    first = await _upload(client, book_id)
    assert first.status_code == 200, first.text
    old_files = _names(uploads.covers)
    assert len(old_files) == 2

    second = await _upload(client, book_id)

    assert second.status_code == 200, second.text
    new_files = _names(uploads.covers)
    assert len(new_files) == 2 and not set(new_files) & set(old_files)
    stored = await _stored(book_id)
    assert stored["cover_image_url"] == second.json()["cover_image_url"]
    assert stored["cover_image_url"].rsplit("/", 1)[1] in new_files


async def test_a_failed_update_keeps_the_old_cover_and_removes_the_new_files(
    auth_client_factory, uploads, monkeypatch
):
    client = await auth_client_factory()
    book_id = await _book(ME)
    assert (await _upload(client, book_id)).status_code == 200
    old_files = _names(uploads.covers)
    old_url = (await _stored(book_id))["cover_image_url"]

    async def _boom(*args, **kwargs):
        raise RuntimeError("simulated mongo failure")

    monkeypatch.setattr(books_endpoint, "update_book", _boom)

    response = await _upload(client, book_id)

    assert response.status_code == 500, response.text
    assert _names(uploads.covers) == old_files
    assert (await _stored(book_id))["cover_image_url"] == old_url


async def test_an_update_that_matches_no_book_removes_the_new_files(
    auth_client_factory, uploads, monkeypatch
):
    """The book was deleted between the ownership check and the write."""
    client = await auth_client_factory()
    book_id = await _book(ME)

    async def _gone(*args, **kwargs):
        return None

    monkeypatch.setattr(books_endpoint, "update_book", _gone)

    response = await _upload(client, book_id)

    assert response.status_code == 404, response.text
    assert _names(uploads.covers) == []


async def test_an_uppercase_book_id_in_the_path_names_the_same_files(
    auth_client_factory, uploads
):
    """ObjectId accepts uppercase hex. The id in the path must not become a
    second owner prefix that the lowercase id can never delete."""
    client = await auth_client_factory()
    book_id = await _book(ME)

    upload = await _upload(client, book_id.upper())

    assert upload.status_code == 200, upload.text
    names = _names(uploads.covers)
    assert len(names) == 2 and all(n.startswith(f"{book_id}_") for n in names)

    response = await client.delete(f"/api/v1/books/{book_id.upper()}")

    assert response.status_code == 204, response.text
    assert _names(uploads.covers) == []
