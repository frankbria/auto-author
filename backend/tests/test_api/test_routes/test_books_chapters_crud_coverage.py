"""
Integration coverage for the chapter CRUD / list / metadata / bulk-status
endpoints in ``app/api/endpoints/books.py``.

Endpoints exercised (all under ``/api/v1/books/{book_id}/...``):
    POST   /{book_id}/chapters                       create_chapter
    GET    /{book_id}/chapters/{chapter_id}          get_chapter
    PUT    /{book_id}/chapters/{chapter_id}          update_chapter
    DELETE /{book_id}/chapters/{chapter_id}          delete_chapter
    GET    /{book_id}/chapters                        list_chapters
    GET    /{book_id}/chapters/metadata              get_chapters_metadata
    PATCH  /{book_id}/chapters/bulk-status           update_chapter_status_bulk

Real local MongoDB; session auth mocked via the shared conftest
``auth_client_factory`` fixture (conftest rebinds ``toc_transactions`` to the
per-test database, so the transactional create/update/delete run for real).
Chapters are seeded through the real ``POST /{book_id}/chapters`` endpoint.

Behavioral notes captured from the (now-fixed) implementation:

* The transactional endpoints scope their ``find_one`` by ``owner_id``. As a
  result a *wrong-owner* request cannot distinguish "not yours" from
  "missing" and surfaces as **404 "Book not found"**, not 403. (The
  non-transactional read endpoints -- get/list/metadata -- use a separate
  ownership check and *do* return 403.)
* ``create_chapter``'s ``except`` clause tests ``"not found"`` before the
  parent-specific branch, so a bad ``parent_id`` ("Parent chapter not found")
  also surfaces as **404 "Book not found"** rather than 400.
"""

import pytest
from bson import ObjectId


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


async def create_book(api):
    """Create a book via the public API and return its id."""
    resp = await api.post(
        "/api/v1/books/",
        json={
            "title": "Coverage Book",
            "genre": "Fiction",
            "description": "A book for chapter coverage tests",
            "target_audience": "Adults",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def add_chapter(api, book_id, *, title="Chapter", level=1, order=1,
                      parent_id=None, description="desc"):
    """Create a chapter via the real POST endpoint and return its id."""
    payload = {
        "title": title,
        "description": description,
        "level": level,
        "order": order,
    }
    if parent_id is not None:
        payload["parent_id"] = parent_id
    resp = await api.post(f"/api/v1/books/{book_id}/chapters", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()["chapter_id"]


async def make_other_user(auth_client_factory):
    return await auth_client_factory(
        overrides={"auth_id": "other-user-999", "email": "o@e.com"}
    )


# --------------------------------------------------------------------------- #
# create_chapter  (POST /{book_id}/chapters)
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_create_chapter_happy_path(auth_client_factory):
    api = await auth_client_factory()
    book_id = await create_book(api)

    resp = await api.post(
        f"/api/v1/books/{book_id}/chapters",
        json={"title": "Ch1", "description": "d", "level": 1, "order": 1},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    assert body["message"] == "Chapter created successfully"
    assert body["book_id"] == book_id
    assert body["chapter_id"]
    assert body["chapter"]["title"] == "Ch1"
    assert body["chapter"]["status"] == "draft"

    # The created chapter is retrievable.
    got = await api.get(f"/api/v1/books/{book_id}/chapters/{body['chapter_id']}")
    assert got.status_code == 200
    assert got.json()["chapter"]["title"] == "Ch1"


@pytest.mark.asyncio
async def test_create_subchapter_happy_path(auth_client_factory):
    """level>1 with a valid parent_id nests the chapter under the parent."""
    api = await auth_client_factory()
    book_id = await create_book(api)
    parent_id = await add_chapter(api, book_id, title="Parent", level=1, order=1)

    resp = await api.post(
        f"/api/v1/books/{book_id}/chapters",
        json={"title": "Sub", "description": "d", "level": 2, "order": 1,
              "parent_id": parent_id},
    )

    assert resp.status_code == 201
    sub_id = resp.json()["chapter_id"]
    # Retrievable through the recursive lookup.
    got = await api.get(f"/api/v1/books/{book_id}/chapters/{sub_id}")
    assert got.status_code == 200
    assert got.json()["chapter"]["title"] == "Sub"


@pytest.mark.asyncio
async def test_create_chapter_bad_parent_returns_404(auth_client_factory):
    """A level>1 chapter with an unknown parent_id -> 404 (see module docstring)."""
    api = await auth_client_factory()
    book_id = await create_book(api)

    resp = await api.post(
        f"/api/v1/books/{book_id}/chapters",
        json={"title": "X", "level": 2, "order": 1, "parent_id": "does-not-exist"},
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Book not found"


@pytest.mark.asyncio
async def test_create_chapter_book_not_found(auth_client_factory):
    api = await auth_client_factory()
    missing_book = str(ObjectId())

    resp = await api.post(
        f"/api/v1/books/{missing_book}/chapters",
        json={"title": "X", "level": 1, "order": 1},
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Book not found"


@pytest.mark.asyncio
async def test_create_chapter_wrong_owner_returns_404(auth_client_factory):
    """Owner-scoped transaction reports another user's create as 404."""
    api = await auth_client_factory()
    book_id = await create_book(api)

    other = await make_other_user(auth_client_factory)
    resp = await other.post(
        f"/api/v1/books/{book_id}/chapters",
        json={"title": "X", "level": 1, "order": 1},
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Book not found"


@pytest.mark.asyncio
async def test_create_chapter_missing_required_fields_returns_422(auth_client_factory):
    """Missing required title/order -> pydantic validation error before handler."""
    api = await auth_client_factory()
    book_id = await create_book(api)

    resp = await api.post(
        f"/api/v1/books/{book_id}/chapters",
        json={"description": "no title and no order"},
    )

    assert resp.status_code == 422


# --------------------------------------------------------------------------- #
# get_chapter  (GET /{book_id}/chapters/{chapter_id})
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_get_chapter_happy_path(auth_client_factory):
    api = await auth_client_factory()
    book_id = await create_book(api)
    chapter_id = await add_chapter(api, book_id, title="Intro")

    resp = await api.get(f"/api/v1/books/{book_id}/chapters/{chapter_id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["book_id"] == book_id
    assert body["chapter"]["id"] == chapter_id
    assert body["chapter"]["title"] == "Intro"


@pytest.mark.asyncio
async def test_get_chapter_finds_nested_subchapter(auth_client_factory):
    api = await auth_client_factory()
    book_id = await create_book(api)
    parent_id = await add_chapter(api, book_id, title="Parent")
    sub_id = await add_chapter(api, book_id, title="Nested", level=2, order=1,
                               parent_id=parent_id)

    resp = await api.get(f"/api/v1/books/{book_id}/chapters/{sub_id}")

    assert resp.status_code == 200
    assert resp.json()["chapter"]["id"] == sub_id
    assert resp.json()["chapter"]["title"] == "Nested"


@pytest.mark.asyncio
async def test_get_chapter_book_not_found(auth_client_factory):
    api = await auth_client_factory()
    missing_book = str(ObjectId())

    resp = await api.get(f"/api/v1/books/{missing_book}/chapters/c1")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Book not found"


@pytest.mark.asyncio
async def test_get_chapter_invalid_objectid_book_not_found(auth_client_factory):
    """A non-ObjectId book id -> get_book_by_id returns None -> 404."""
    api = await auth_client_factory()

    resp = await api.get("/api/v1/books/not-an-objectid/chapters/c1")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Book not found"


@pytest.mark.asyncio
async def test_get_chapter_chapter_not_found(auth_client_factory):
    api = await auth_client_factory()
    book_id = await create_book(api)
    await add_chapter(api, book_id)

    resp = await api.get(f"/api/v1/books/{book_id}/chapters/does-not-exist")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Chapter not found"


@pytest.mark.asyncio
async def test_get_chapter_wrong_owner_forbidden(auth_client_factory):
    api = await auth_client_factory()
    book_id = await create_book(api)
    chapter_id = await add_chapter(api, book_id)

    other = await make_other_user(auth_client_factory)
    resp = await other.get(f"/api/v1/books/{book_id}/chapters/{chapter_id}")

    assert resp.status_code == 403
    assert "Not authorized" in resp.json()["detail"]


# --------------------------------------------------------------------------- #
# update_chapter  (PUT /{book_id}/chapters/{chapter_id})
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_update_chapter_happy_path(auth_client_factory):
    api = await auth_client_factory()
    book_id = await create_book(api)
    chapter_id = await add_chapter(api, book_id, title="Old", order=1)

    resp = await api.put(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}",
        json={"title": "New Title", "description": "new", "order": 5},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["message"] == "Chapter updated successfully"

    # The change is actually persisted.
    got = await api.get(f"/api/v1/books/{book_id}/chapters/{chapter_id}")
    assert got.json()["chapter"]["title"] == "New Title"
    assert got.json()["chapter"]["description"] == "new"
    assert got.json()["chapter"]["order"] == 5


@pytest.mark.asyncio
async def test_update_chapter_metadata_field(auth_client_factory):
    """The metadata-update branch of the handler persists the metadata dict."""
    api = await auth_client_factory()
    book_id = await create_book(api)
    chapter_id = await add_chapter(api, book_id)

    resp = await api.put(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}",
        json={"metadata": {"key": "value"}},
    )

    assert resp.status_code == 200
    got = await api.get(f"/api/v1/books/{book_id}/chapters/{chapter_id}")
    assert got.json()["chapter"]["metadata"] == {"key": "value"}


@pytest.mark.asyncio
async def test_update_chapter_chapter_not_found(auth_client_factory):
    api = await auth_client_factory()
    book_id = await create_book(api)
    await add_chapter(api, book_id)

    resp = await api.put(
        f"/api/v1/books/{book_id}/chapters/nope",
        json={"title": "x"},
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Chapter not found"


@pytest.mark.asyncio
async def test_update_chapter_book_not_found(auth_client_factory):
    api = await auth_client_factory()
    missing_book = str(ObjectId())

    resp = await api.put(
        f"/api/v1/books/{missing_book}/chapters/c1",
        json={"title": "x"},
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Book not found"


@pytest.mark.asyncio
async def test_update_chapter_wrong_owner_returns_404(auth_client_factory):
    """Owner-scoped transaction reports another user's update as 404."""
    api = await auth_client_factory()
    book_id = await create_book(api)
    chapter_id = await add_chapter(api, book_id)

    other = await make_other_user(auth_client_factory)
    resp = await other.put(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}",
        json={"title": "x"},
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Book not found"


# --------------------------------------------------------------------------- #
# delete_chapter  (DELETE /{book_id}/chapters/{chapter_id})
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_delete_chapter_happy_path(auth_client_factory):
    api = await auth_client_factory()
    book_id = await create_book(api)
    keep_id = await add_chapter(api, book_id, title="Keep", order=1)
    drop_id = await add_chapter(api, book_id, title="Drop", order=2)

    resp = await api.delete(f"/api/v1/books/{book_id}/chapters/{drop_id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["chapter_id"] == drop_id
    assert body["message"] == "Chapter deleted successfully"

    # Confirm the chapter is really gone and the other remains.
    after = await api.get(f"/api/v1/books/{book_id}/chapters/{drop_id}")
    assert after.status_code == 404
    remaining = await api.get(f"/api/v1/books/{book_id}/chapters")
    assert [c["id"] for c in remaining.json()["chapters"]] == [keep_id]


@pytest.mark.asyncio
async def test_delete_chapter_chapter_not_found(auth_client_factory):
    api = await auth_client_factory()
    book_id = await create_book(api)
    await add_chapter(api, book_id)

    resp = await api.delete(f"/api/v1/books/{book_id}/chapters/nope")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Chapter not found"


@pytest.mark.asyncio
async def test_delete_chapter_book_not_found(auth_client_factory):
    api = await auth_client_factory()
    missing_book = str(ObjectId())

    resp = await api.delete(f"/api/v1/books/{missing_book}/chapters/c1")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Book not found"


@pytest.mark.asyncio
async def test_delete_chapter_wrong_owner_surfaces_as_404(auth_client_factory):
    """Owner-scoped find_one means another user's delete reports 404, not 403."""
    api = await auth_client_factory()
    book_id = await create_book(api)
    chapter_id = await add_chapter(api, book_id)

    other = await make_other_user(auth_client_factory)
    resp = await other.delete(f"/api/v1/books/{book_id}/chapters/{chapter_id}")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Book not found"


@pytest.mark.asyncio
async def test_delete_subchapter_happy_path(auth_client_factory):
    api = await auth_client_factory()
    book_id = await create_book(api)
    parent_id = await add_chapter(api, book_id, title="Parent")
    sub_id = await add_chapter(api, book_id, title="Sub", level=2, order=1,
                               parent_id=parent_id)

    resp = await api.delete(f"/api/v1/books/{book_id}/chapters/{sub_id}")

    assert resp.status_code == 200
    assert resp.json()["chapter_id"] == sub_id
    assert (await api.get(f"/api/v1/books/{book_id}/chapters/{sub_id}")).status_code == 404


# --------------------------------------------------------------------------- #
# list_chapters  (GET /{book_id}/chapters)
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_list_chapters_hierarchical_default(auth_client_factory):
    api = await auth_client_factory()
    book_id = await create_book(api)
    c1 = await add_chapter(api, book_id, title="C1", order=1)
    c2 = await add_chapter(api, book_id, title="C2", order=2)

    resp = await api.get(f"/api/v1/books/{book_id}/chapters")

    assert resp.status_code == 200
    body = resp.json()
    assert body["structure"] == "hierarchical"
    assert body["total_chapters"] == 2
    assert [c["id"] for c in body["chapters"]] == [c1, c2]
    assert body["success"] is True


@pytest.mark.asyncio
async def test_list_chapters_flat_includes_subchapters(auth_client_factory):
    api = await auth_client_factory()
    book_id = await create_book(api)
    c1 = await add_chapter(api, book_id, title="C1", order=1)
    sub = await add_chapter(api, book_id, title="Sub", level=2, order=1, parent_id=c1)
    c2 = await add_chapter(api, book_id, title="C2", order=2)

    resp = await api.get(f"/api/v1/books/{book_id}/chapters?flat=true")

    assert resp.status_code == 200
    body = resp.json()
    assert body["structure"] == "flat"
    # 2 top-level + 1 nested subchapter flattened.
    assert body["total_chapters"] == 3
    assert {c["id"] for c in body["chapters"]} == {c1, sub, c2}


@pytest.mark.asyncio
async def test_list_chapters_empty_toc(auth_client_factory):
    """A book with no chapters returns an empty hierarchical list."""
    api = await auth_client_factory()
    book_id = await create_book(api)

    resp = await api.get(f"/api/v1/books/{book_id}/chapters")

    assert resp.status_code == 200
    body = resp.json()
    assert body["chapters"] == []
    assert body["total_chapters"] == 0


@pytest.mark.asyncio
async def test_list_chapters_book_not_found(auth_client_factory):
    api = await auth_client_factory()
    missing_book = str(ObjectId())

    resp = await api.get(f"/api/v1/books/{missing_book}/chapters")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Book not found"


@pytest.mark.asyncio
async def test_list_chapters_wrong_owner_forbidden(auth_client_factory):
    api = await auth_client_factory()
    book_id = await create_book(api)
    await add_chapter(api, book_id)

    other = await make_other_user(auth_client_factory)
    resp = await other.get(f"/api/v1/books/{book_id}/chapters")

    assert resp.status_code == 403
    assert "Not authorized" in resp.json()["detail"]


# --------------------------------------------------------------------------- #
# get_chapters_metadata  (GET /{book_id}/chapters/metadata)
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_get_chapters_metadata_happy_path(auth_client_factory):
    api = await auth_client_factory()
    book_id = await create_book(api)
    parent_id = await add_chapter(api, book_id, title="C1", order=1)
    await add_chapter(api, book_id, title="Sub", level=2, order=1, parent_id=parent_id)

    resp = await api.get(f"/api/v1/books/{book_id}/chapters/metadata")

    assert resp.status_code == 200
    body = resp.json()
    assert body["book_id"] == book_id
    # Top-level chapter + flattened subchapter.
    assert body["total_chapters"] == 2
    assert len(body["chapters"]) == 2
    titles = {c["title"] for c in body["chapters"]}
    assert titles == {"C1", "Sub"}
    # Both freshly created chapters are draft.
    assert body["completion_stats"]["draft"] == 2
    assert body["completion_stats"]["completed"] == 0
    # last_active_chapter key is always present in the response.
    assert "last_active_chapter" in body


@pytest.mark.asyncio
async def test_get_chapters_metadata_book_not_found(auth_client_factory):
    api = await auth_client_factory()
    missing_book = str(ObjectId())

    resp = await api.get(f"/api/v1/books/{missing_book}/chapters/metadata")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Book not found"


@pytest.mark.asyncio
async def test_get_chapters_metadata_wrong_owner_forbidden(auth_client_factory):
    api = await auth_client_factory()
    book_id = await create_book(api)
    await add_chapter(api, book_id)

    other = await make_other_user(auth_client_factory)
    resp = await other.get(f"/api/v1/books/{book_id}/chapters/metadata")

    assert resp.status_code == 403
    assert "Not authorized" in resp.json()["detail"]


# --------------------------------------------------------------------------- #
# update_chapter_status_bulk  (PATCH /{book_id}/chapters/bulk-status)
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_bulk_status_single_chapter_happy(auth_client_factory):
    api = await auth_client_factory()
    book_id = await create_book(api)
    chapter_id = await add_chapter(api, book_id)

    resp = await api.patch(
        f"/api/v1/books/{book_id}/chapters/bulk-status",
        json={"chapter_ids": [chapter_id], "status": "in-progress"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["updated_chapters"] == [chapter_id]
    assert body["new_status"] == "in-progress"
    assert "1 chapters" in body["message"]

    # Persisted.
    after = await api.get(f"/api/v1/books/{book_id}/chapters/{chapter_id}")
    assert after.json()["chapter"]["status"] == "in-progress"


@pytest.mark.asyncio
async def test_bulk_status_multiple_chapters(auth_client_factory):
    api = await auth_client_factory()
    book_id = await create_book(api)
    c1 = await add_chapter(api, book_id, title="C1", order=1)
    c2 = await add_chapter(api, book_id, title="C2", order=2)

    resp = await api.patch(
        f"/api/v1/books/{book_id}/chapters/bulk-status",
        json={"chapter_ids": [c1, c2], "status": "completed"},
    )

    assert resp.status_code == 200
    assert set(resp.json()["updated_chapters"]) == {c1, c2}


@pytest.mark.asyncio
async def test_bulk_status_updates_nested_subchapter(auth_client_factory):
    """Recursive collect_and_update_statuses reaches subchapters."""
    api = await auth_client_factory()
    book_id = await create_book(api)
    parent_id = await add_chapter(api, book_id, title="Parent")
    sub_id = await add_chapter(api, book_id, title="Sub", level=2, order=1,
                               parent_id=parent_id)

    resp = await api.patch(
        f"/api/v1/books/{book_id}/chapters/bulk-status",
        json={"chapter_ids": [sub_id], "status": "in-progress"},
    )

    assert resp.status_code == 200
    assert resp.json()["updated_chapters"] == [sub_id]


@pytest.mark.asyncio
async def test_bulk_status_same_status_is_allowed(auth_client_factory):
    """from == to is a valid transition (no-op transition branch)."""
    api = await auth_client_factory()
    book_id = await create_book(api)
    chapter_id = await add_chapter(api, book_id)

    resp = await api.patch(
        f"/api/v1/books/{book_id}/chapters/bulk-status",
        json={"chapter_ids": [chapter_id], "status": "draft"},
    )

    assert resp.status_code == 200
    assert resp.json()["updated_chapters"] == [chapter_id]


@pytest.mark.asyncio
async def test_bulk_status_without_timestamp_update(auth_client_factory):
    """update_timestamp=False skips the last_modified assignment branch."""
    api = await auth_client_factory()
    book_id = await create_book(api)
    chapter_id = await add_chapter(api, book_id)

    resp = await api.patch(
        f"/api/v1/books/{book_id}/chapters/bulk-status",
        json={"chapter_ids": [chapter_id], "status": "completed",
              "update_timestamp": False},
    )

    assert resp.status_code == 200
    assert resp.json()["updated_chapters"] == [chapter_id]


@pytest.mark.asyncio
async def test_bulk_status_invalid_transition_returns_400(auth_client_factory):
    """draft -> published is not an allowed transition."""
    api = await auth_client_factory()
    book_id = await create_book(api)
    chapter_id = await add_chapter(api, book_id)

    resp = await api.patch(
        f"/api/v1/books/{book_id}/chapters/bulk-status",
        json={"chapter_ids": [chapter_id], "status": "published"},
    )

    assert resp.status_code == 400
    assert "Invalid status transition" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_bulk_status_no_matching_chapters_returns_404(auth_client_factory):
    api = await auth_client_factory()
    book_id = await create_book(api)
    await add_chapter(api, book_id)

    resp = await api.patch(
        f"/api/v1/books/{book_id}/chapters/bulk-status",
        json={"chapter_ids": ["nonexistent"], "status": "in-progress"},
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "No matching chapters found"


@pytest.mark.asyncio
async def test_bulk_status_book_not_found(auth_client_factory):
    api = await auth_client_factory()
    missing_book = str(ObjectId())

    resp = await api.patch(
        f"/api/v1/books/{missing_book}/chapters/bulk-status",
        json={"chapter_ids": ["c1"], "status": "in-progress"},
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Book not found"


@pytest.mark.asyncio
async def test_bulk_status_wrong_owner_forbidden(auth_client_factory):
    api = await auth_client_factory()
    book_id = await create_book(api)
    chapter_id = await add_chapter(api, book_id)

    other = await make_other_user(auth_client_factory)
    resp = await other.patch(
        f"/api/v1/books/{book_id}/chapters/bulk-status",
        json={"chapter_ids": [chapter_id], "status": "in-progress"},
    )

    assert resp.status_code == 403
    assert "Not authorized" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_bulk_status_invalid_status_value_returns_422(auth_client_factory):
    """A status outside the ChapterStatus enum fails validation."""
    api = await auth_client_factory()
    book_id = await create_book(api)
    chapter_id = await add_chapter(api, book_id)

    resp = await api.patch(
        f"/api/v1/books/{book_id}/chapters/bulk-status",
        json={"chapter_ids": [chapter_id], "status": "bogus-status"},
    )

    assert resp.status_code == 422
