"""
Integration coverage tests for app/api/endpoints/books.py CRUD endpoints.

Covers: create, list, get, PUT update, PATCH update, delete, cover-image upload,
and summary GET/PUT/PATCH. Each endpoint exercises happy-path plus error branches
(404 not found, 403 wrong owner, 400 bad id, 422 validation) to maximize branch
coverage.

Real MongoDB is used (session auth mocked via auth_client_factory). Only the
external file-upload service is patched for the cover-image endpoint.
"""

import pytest
from bson import ObjectId
from fastapi.encoders import jsonable_encoder

import app.services.file_upload_service as file_upload_module


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _create_payload(test_book):
    """Build a valid create-book JSON payload from the test_book fixture."""
    payload = test_book.copy()
    payload["owner_id"] = str(test_book["owner_id"])
    for key in ("_id", "id", "toc_items", "published"):
        payload.pop(key, None)
    return jsonable_encoder(payload)


async def _create_book(api, test_book):
    resp = await api.post("/api/v1/books/", json=_create_payload(test_book))
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# create_new_book
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_book_happy_path(auth_client_factory, test_book):
    api = await auth_client_factory()
    resp = await api.post("/api/v1/books/", json=_create_payload(test_book))
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == test_book["title"]
    assert "id" in data and data["id"]
    assert "created_at" in data and "updated_at" in data


@pytest.mark.asyncio
async def test_create_book_missing_title_422(auth_client_factory):
    api = await auth_client_factory()
    resp = await api.post("/api/v1/books/", json={"genre": "Fiction"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_book_title_too_long_422(auth_client_factory):
    api = await auth_client_factory()
    resp = await api.post("/api/v1/books/", json={"title": "A" * 101})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# get_user_books
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_user_books_happy_path(auth_client_factory, test_book):
    api = await auth_client_factory()
    await _create_book(api, test_book)
    await _create_book(api, test_book)

    resp = await api.get("/api/v1/books/")
    assert resp.status_code == 200
    books = resp.json()
    assert isinstance(books, list)
    assert len(books) == 2
    assert all("id" in b for b in books)


@pytest.mark.asyncio
async def test_list_user_books_pagination(auth_client_factory, test_book):
    api = await auth_client_factory()
    await _create_book(api, test_book)
    await _create_book(api, test_book)

    resp = await api.get("/api/v1/books/?skip=1&limit=1")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_list_user_books_only_owner_books(auth_client_factory, test_book):
    owner = await auth_client_factory()
    await _create_book(owner, test_book)

    other = await auth_client_factory(
        overrides={"auth_id": "other-user-999", "email": "other@example.com"}
    )
    resp = await other.get("/api/v1/books/")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_user_books_invalid_query_422(auth_client_factory):
    api = await auth_client_factory()
    # limit must be <= 100
    resp = await api.get("/api/v1/books/?limit=500")
    assert resp.status_code == 422
    # skip must be >= 0
    resp = await api.get("/api/v1/books/?skip=-1")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# get_book
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_book_happy_path(auth_client_factory, test_book):
    api = await auth_client_factory()
    book_id = await _create_book(api, test_book)

    resp = await api.get(f"/api/v1/books/{book_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == book_id
    assert data["title"] == test_book["title"]


@pytest.mark.asyncio
async def test_get_book_invalid_id_400(auth_client_factory):
    api = await auth_client_factory()
    resp = await api.get("/api/v1/books/not-an-objectid")
    assert resp.status_code == 400
    assert "Invalid book ID format" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_get_book_not_found_404(auth_client_factory):
    api = await auth_client_factory()
    resp = await api.get(f"/api/v1/books/{ObjectId()}")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Book not found"


@pytest.mark.asyncio
async def test_get_book_wrong_owner_403(auth_client_factory, test_book):
    owner = await auth_client_factory()
    book_id = await _create_book(owner, test_book)

    other = await auth_client_factory(
        overrides={"auth_id": "other-user-999", "email": "other@example.com"}
    )
    resp = await other.get(f"/api/v1/books/{book_id}")
    assert resp.status_code == 403
    assert "don't have access" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# update_book_details (PUT)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_put_book_happy_path(auth_client_factory, test_book):
    api = await auth_client_factory()
    book_id = await _create_book(api, test_book)

    put_data = {
        "title": "Put Title",
        "genre": "science",
        "target_audience": "professional",
    }
    resp = await api.put(f"/api/v1/books/{book_id}", json=put_data)
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Put Title"
    assert data["genre"] == "science"
    assert data["target_audience"] == "professional"


@pytest.mark.asyncio
async def test_put_book_invalid_id_400(auth_client_factory):
    api = await auth_client_factory()
    resp = await api.put("/api/v1/books/bad-id", json={"title": "X"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_put_book_not_found_404(auth_client_factory):
    api = await auth_client_factory()
    resp = await api.put(f"/api/v1/books/{ObjectId()}", json={"title": "X"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_put_book_wrong_owner_404(auth_client_factory, test_book):
    owner = await auth_client_factory()
    book_id = await _create_book(owner, test_book)

    other = await auth_client_factory(
        overrides={"auth_id": "other-user-999", "email": "other@example.com"}
    )
    resp = await other.put(f"/api/v1/books/{book_id}", json={"title": "Hijack"})
    # update_book filters by owner; no match -> 404
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_put_book_title_too_long_422(auth_client_factory, test_book):
    api = await auth_client_factory()
    book_id = await _create_book(api, test_book)
    resp = await api.put(f"/api/v1/books/{book_id}", json={"title": "A" * 101})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# patch_book_details (PATCH)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_patch_book_happy_path(auth_client_factory, test_book):
    api = await auth_client_factory()
    book_id = await _create_book(api, test_book)

    resp = await api.patch(
        f"/api/v1/books/{book_id}",
        json={"title": "Patched Title", "target_audience": "academic"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Patched Title"
    assert data["target_audience"] == "academic"


@pytest.mark.asyncio
async def test_patch_book_invalid_id_400(auth_client_factory):
    api = await auth_client_factory()
    resp = await api.patch("/api/v1/books/xyz", json={"title": "X"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_patch_book_not_found_404(auth_client_factory):
    api = await auth_client_factory()
    resp = await api.patch(f"/api/v1/books/{ObjectId()}", json={"title": "X"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_book_wrong_owner_404(auth_client_factory, test_book):
    owner = await auth_client_factory()
    book_id = await _create_book(owner, test_book)

    other = await auth_client_factory(
        overrides={"auth_id": "other-user-999", "email": "other@example.com"}
    )
    resp = await other.patch(f"/api/v1/books/{book_id}", json={"title": "Hijack"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_book_title_too_long_422(auth_client_factory, test_book):
    api = await auth_client_factory()
    book_id = await _create_book(api, test_book)
    resp = await api.patch(f"/api/v1/books/{book_id}", json={"title": "A" * 101})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# delete_book_endpoint
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_delete_book_happy_path(auth_client_factory, test_book):
    api = await auth_client_factory()
    book_id = await _create_book(api, test_book)

    resp = await api.delete(f"/api/v1/books/{book_id}")
    assert resp.status_code == 204

    # Confirm it is gone
    resp = await api.get(f"/api/v1/books/{book_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_book_invalid_id_400(auth_client_factory):
    api = await auth_client_factory()
    resp = await api.delete("/api/v1/books/nope")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_delete_book_not_found_404(auth_client_factory):
    api = await auth_client_factory()
    resp = await api.delete(f"/api/v1/books/{ObjectId()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_book_wrong_owner_403(auth_client_factory, test_book):
    owner = await auth_client_factory()
    book_id = await _create_book(owner, test_book)

    other = await auth_client_factory(
        overrides={"auth_id": "other-user-999", "email": "other@example.com"}
    )
    resp = await other.delete(f"/api/v1/books/{book_id}")
    assert resp.status_code == 403
    assert "don't have permission" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# upload_book_cover_image
# ---------------------------------------------------------------------------
class _FakeUploadService:
    """Stand-in for FileUploadService that avoids real image/storage work."""

    instances = []

    def __init__(self):
        self.deleted = []
        _FakeUploadService.instances.append(self)

    async def process_and_save_cover_image(self, file, book_id):
        return (
            f"/uploads/cover_images/{book_id}.png",
            f"/uploads/cover_images/{book_id}_thumb.png",
        )

    async def delete_cover_image(self, image_url, thumbnail_url):
        self.deleted.append((image_url, thumbnail_url))
        return None


@pytest.fixture
def patch_upload_service(monkeypatch):
    _FakeUploadService.instances = []
    monkeypatch.setattr(
        file_upload_module, "FileUploadService", _FakeUploadService
    )
    return _FakeUploadService


@pytest.mark.asyncio
async def test_upload_cover_image_happy_path(
    auth_client_factory, test_book, patch_upload_service
):
    api = await auth_client_factory()
    book_id = await _create_book(api, test_book)

    resp = await api.post(
        f"/api/v1/books/{book_id}/cover-image",
        files={"file": ("cover.png", b"fake-bytes", "image/png")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["book_id"] == book_id
    assert data["cover_image_url"] == f"/uploads/cover_images/{book_id}.png"
    assert data["cover_thumbnail_url"].endswith("_thumb.png")


@pytest.mark.asyncio
async def test_upload_cover_image_replaces_old(
    auth_client_factory, test_book, patch_upload_service
):
    api = await auth_client_factory()
    book_id = await _create_book(api, test_book)

    # First upload sets a cover image
    resp = await api.post(
        f"/api/v1/books/{book_id}/cover-image",
        files={"file": ("cover.png", b"fake-bytes", "image/png")},
    )
    assert resp.status_code == 200

    # Second upload should trigger deletion of the previous cover
    resp = await api.post(
        f"/api/v1/books/{book_id}/cover-image",
        files={"file": ("cover2.png", b"more-bytes", "image/png")},
    )
    assert resp.status_code == 200

    # The second service instance should have recorded a deletion of the old url
    assert any(svc.deleted for svc in patch_upload_service.instances)


@pytest.mark.asyncio
async def test_upload_cover_image_wrong_owner_404(
    auth_client_factory, test_book, patch_upload_service
):
    owner = await auth_client_factory()
    book_id = await _create_book(owner, test_book)

    other = await auth_client_factory(
        overrides={"auth_id": "other-user-999", "email": "other@example.com"}
    )
    resp = await other.post(
        f"/api/v1/books/{book_id}/cover-image",
        files={"file": ("cover.png", b"fake-bytes", "image/png")},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_upload_cover_image_not_found_404(
    auth_client_factory, patch_upload_service
):
    api = await auth_client_factory()
    resp = await api.post(
        f"/api/v1/books/{ObjectId()}/cover-image",
        files={"file": ("cover.png", b"fake-bytes", "image/png")},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# get_book_summary
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_summary_happy_path(auth_client_factory, test_book):
    api = await auth_client_factory()
    book_id = await _create_book(api, test_book)

    resp = await api.get(f"/api/v1/books/{book_id}/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"] == ""
    assert data["summary_history"] == []


@pytest.mark.asyncio
async def test_get_summary_not_found_404(auth_client_factory):
    api = await auth_client_factory()
    resp = await api.get(f"/api/v1/books/{ObjectId()}/summary")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_summary_wrong_owner_403(auth_client_factory, test_book):
    owner = await auth_client_factory()
    book_id = await _create_book(owner, test_book)

    other = await auth_client_factory(
        overrides={"auth_id": "other-user-999", "email": "other@example.com"}
    )
    resp = await other.get(f"/api/v1/books/{book_id}/summary")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# update_book_summary (PUT)
# ---------------------------------------------------------------------------
VALID_SUMMARY = "This is a perfectly valid book summary with enough characters."


@pytest.mark.asyncio
async def test_put_summary_happy_path(auth_client_factory, test_book):
    api = await auth_client_factory()
    book_id = await _create_book(api, test_book)

    resp = await api.put(
        f"/api/v1/books/{book_id}/summary", json={"summary": VALID_SUMMARY}
    )
    assert resp.status_code == 200
    assert resp.json()["summary"] == VALID_SUMMARY

    # Updating again should record revision history
    new_summary = "A second revision of the summary that is also long enough now."
    resp = await api.put(
        f"/api/v1/books/{book_id}/summary", json={"summary": new_summary}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"] == new_summary
    assert len(data["summary_history"]) == 1
    assert data["summary_history"][0]["summary"] == VALID_SUMMARY


@pytest.mark.asyncio
async def test_put_summary_missing_400(auth_client_factory, test_book):
    api = await auth_client_factory()
    book_id = await _create_book(api, test_book)
    resp = await api.put(f"/api/v1/books/{book_id}/summary", json={})
    assert resp.status_code == 400
    assert "required" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_put_summary_too_short_400(auth_client_factory, test_book):
    api = await auth_client_factory()
    book_id = await _create_book(api, test_book)
    resp = await api.put(
        f"/api/v1/books/{book_id}/summary", json={"summary": "too short"}
    )
    assert resp.status_code == 400
    assert "at least" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_put_summary_too_long_400(auth_client_factory, test_book):
    api = await auth_client_factory()
    book_id = await _create_book(api, test_book)
    resp = await api.put(
        f"/api/v1/books/{book_id}/summary", json={"summary": "A" * 2001}
    )
    assert resp.status_code == 400
    assert "at most" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_put_summary_offensive_400(auth_client_factory, test_book):
    api = await auth_client_factory()
    book_id = await _create_book(api, test_book)
    # The filter matches whole blacklisted words (word-boundary regex). A summary
    # (>=30 chars) containing a real blacklisted word must be rejected.
    offensive = "This summary is long enough and also contains the word shit here."
    resp = await api.put(
        f"/api/v1/books/{book_id}/summary", json={"summary": offensive}
    )
    assert resp.status_code == 400
    assert "inappropriate" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_put_summary_not_found_404(auth_client_factory):
    api = await auth_client_factory()
    resp = await api.put(
        f"/api/v1/books/{ObjectId()}/summary", json={"summary": VALID_SUMMARY}
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_put_summary_wrong_owner_403(auth_client_factory, test_book):
    owner = await auth_client_factory()
    book_id = await _create_book(owner, test_book)

    other = await auth_client_factory(
        overrides={"auth_id": "other-user-999", "email": "other@example.com"}
    )
    resp = await other.put(
        f"/api/v1/books/{book_id}/summary", json={"summary": VALID_SUMMARY}
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# patch_book_summary (PATCH)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_patch_summary_happy_path(auth_client_factory, test_book):
    api = await auth_client_factory()
    book_id = await _create_book(api, test_book)

    resp = await api.patch(
        f"/api/v1/books/{book_id}/summary", json={"summary": VALID_SUMMARY}
    )
    assert resp.status_code == 200
    assert resp.json()["summary"] == VALID_SUMMARY


@pytest.mark.asyncio
async def test_patch_summary_no_summary_returns_current(
    auth_client_factory, test_book
):
    api = await auth_client_factory()
    book_id = await _create_book(api, test_book)

    # Seed an existing summary
    await api.patch(
        f"/api/v1/books/{book_id}/summary", json={"summary": VALID_SUMMARY}
    )

    # PATCH with no summary key returns the current summary unchanged
    resp = await api.patch(f"/api/v1/books/{book_id}/summary", json={})
    assert resp.status_code == 200
    assert resp.json()["summary"] == VALID_SUMMARY


@pytest.mark.asyncio
async def test_patch_summary_not_string_400(auth_client_factory, test_book):
    api = await auth_client_factory()
    book_id = await _create_book(api, test_book)
    resp = await api.patch(
        f"/api/v1/books/{book_id}/summary", json={"summary": 12345}
    )
    assert resp.status_code == 400
    assert "must be a string" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_patch_summary_too_short_400(auth_client_factory, test_book):
    api = await auth_client_factory()
    book_id = await _create_book(api, test_book)
    resp = await api.patch(
        f"/api/v1/books/{book_id}/summary", json={"summary": "short"}
    )
    assert resp.status_code == 400
    assert "at least" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_patch_summary_too_long_400(auth_client_factory, test_book):
    api = await auth_client_factory()
    book_id = await _create_book(api, test_book)
    resp = await api.patch(
        f"/api/v1/books/{book_id}/summary", json={"summary": "A" * 2001}
    )
    assert resp.status_code == 400
    assert "at most" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_patch_summary_records_history(auth_client_factory, test_book):
    api = await auth_client_factory()
    book_id = await _create_book(api, test_book)

    await api.patch(
        f"/api/v1/books/{book_id}/summary", json={"summary": VALID_SUMMARY}
    )
    new_summary = "Another sufficiently long replacement summary for the book."
    resp = await api.patch(
        f"/api/v1/books/{book_id}/summary", json={"summary": new_summary}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"] == new_summary
    assert len(data["summary_history"]) == 1
    assert data["summary_history"][0]["summary"] == VALID_SUMMARY


@pytest.mark.asyncio
async def test_patch_summary_not_found_404(auth_client_factory):
    api = await auth_client_factory()
    resp = await api.patch(
        f"/api/v1/books/{ObjectId()}/summary", json={"summary": VALID_SUMMARY}
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_summary_wrong_owner_403(auth_client_factory, test_book):
    owner = await auth_client_factory()
    book_id = await _create_book(owner, test_book)

    other = await auth_client_factory(
        overrides={"auth_id": "other-user-999", "email": "other@example.com"}
    )
    resp = await other.patch(
        f"/api/v1/books/{book_id}/summary", json={"summary": VALID_SUMMARY}
    )
    assert resp.status_code == 403
