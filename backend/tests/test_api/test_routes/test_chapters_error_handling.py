"""
Issue #159 (P3.8): structured error handling + optimistic-concurrency mapping
for the chapter endpoints in ``app/api/endpoints/chapters.py``.

Two defects fixed here:

1. ``update_chapter_status_bulk`` persisted the whole TOC with no version guard,
   silently clobbering concurrent edits. It now routes through
   ``update_chapter_statuses_with_version_guard`` and maps a version conflict to
   **409** (mirroring create/update/delete_chapter).
2. The read/aggregate handlers (``get_chapters_metadata``, ``get_tab_state``,
   ``list_chapters``, ``save_tab_state``) had no ``try/except``, so an unexpected
   error propagated unlogged. They now log and return a structured **500** while
   preserving the existing 404/403 checks.

Real local MongoDB via the shared ``auth_client_factory`` fixture; the failure
paths are forced by monkeypatching a downstream call to raise.
"""

import pytest

import app.api.endpoints.chapters as chapters


async def create_book(api):
    resp = await api.post(
        "/api/v1/books/",
        json={
            "title": "Err Book",
            "genre": "Fiction",
            "description": "book for error-handling coverage",
            "target_audience": "Adults",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def add_chapter(api, book_id, *, title="Chapter", order=1):
    resp = await api.post(
        f"/api/v1/books/{book_id}/chapters",
        json={"title": title, "description": "d", "level": 1, "order": order},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["chapter_id"]


def _async_raiser(*_args, **_kwargs):
    async def _boom(*a, **k):
        raise RuntimeError("boom")
    return _boom


# --------------------------------------------------------------------------- #
# Part 1: bulk-status version conflict -> 409
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_bulk_status_version_conflict_returns_409(
    auth_client_factory, monkeypatch
):
    api = await auth_client_factory()
    book_id = await create_book(api)
    chapter_id = await add_chapter(api, book_id)

    async def _conflict(*a, **k):
        raise ValueError("Version conflict: expected 1, current 2")

    monkeypatch.setattr(
        chapters, "update_chapter_statuses_with_version_guard", _conflict
    )

    resp = await api.patch(
        f"/api/v1/books/{book_id}/chapters/bulk-status",
        json={"chapter_ids": [chapter_id], "status": "in-progress"},
    )

    assert resp.status_code == 409
    assert "modified" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_bulk_status_unexpected_error_returns_structured_500(
    auth_client_factory, monkeypatch
):
    api = await auth_client_factory()
    book_id = await create_book(api)
    chapter_id = await add_chapter(api, book_id)

    async def _boom(*a, **k):
        raise RuntimeError("db exploded")

    monkeypatch.setattr(
        chapters, "update_chapter_statuses_with_version_guard", _boom
    )

    resp = await api.patch(
        f"/api/v1/books/{book_id}/chapters/bulk-status",
        json={"chapter_ids": [chapter_id], "status": "in-progress"},
    )

    assert resp.status_code == 500
    assert resp.json()["detail"] == "Failed to update chapter statuses"


@pytest.mark.asyncio
async def test_bulk_status_logging_failure_does_not_fail_committed_update(
    auth_client_factory, monkeypatch
):
    """The status update has committed; a post-commit log_access error must not
    turn the request into a failure."""
    api = await auth_client_factory()
    book_id = await create_book(api)
    chapter_id = await add_chapter(api, book_id)

    async def _boom(*a, **k):
        raise RuntimeError("logging down")

    monkeypatch.setattr(chapters.chapter_access_service, "log_access", _boom)

    resp = await api.patch(
        f"/api/v1/books/{book_id}/chapters/bulk-status",
        json={"chapter_ids": [chapter_id], "status": "in-progress"},
    )

    assert resp.status_code == 200
    assert resp.json()["updated_chapters"] == [chapter_id]
    # The update really persisted (list_chapters does not log access, so it is
    # unaffected by the patched-to-fail log_access).
    after = await api.get(f"/api/v1/books/{book_id}/chapters")
    statuses = {c["id"]: c["status"] for c in after.json()["chapters"]}
    assert statuses[chapter_id] == "in-progress"


# --------------------------------------------------------------------------- #
# Part 2: read/aggregate handlers -> structured 500 (preserving 404/403)
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_list_chapters_unexpected_error_returns_500(
    auth_client_factory, monkeypatch
):
    api = await auth_client_factory()
    book_id = await create_book(api)

    monkeypatch.setattr(chapters, "get_book_by_id", _async_raiser())

    resp = await api.get(f"/api/v1/books/{book_id}/chapters")
    assert resp.status_code == 500
    assert resp.json()["detail"] == "Failed to list chapters"


@pytest.mark.asyncio
async def test_get_chapters_metadata_unexpected_error_returns_500(
    auth_client_factory, monkeypatch
):
    api = await auth_client_factory()
    book_id = await create_book(api)
    await add_chapter(api, book_id)

    # Ownership check passes; the later access-log lookup blows up.
    monkeypatch.setattr(
        chapters.chapter_access_service, "get_user_recent_chapters", _async_raiser()
    )

    resp = await api.get(f"/api/v1/books/{book_id}/chapters/metadata")
    assert resp.status_code == 500
    assert resp.json()["detail"] == "Failed to retrieve chapter metadata"


@pytest.mark.asyncio
async def test_get_tab_state_unexpected_error_returns_500(
    auth_client_factory, monkeypatch
):
    api = await auth_client_factory()
    book_id = await create_book(api)

    monkeypatch.setattr(
        chapters.chapter_access_service, "get_user_tab_state", _async_raiser()
    )

    resp = await api.get(f"/api/v1/books/{book_id}/chapters/tab-state")
    assert resp.status_code == 500
    assert resp.json()["detail"] == "Failed to retrieve tab state"


@pytest.mark.asyncio
async def test_save_tab_state_unexpected_error_returns_500(
    auth_client_factory, monkeypatch
):
    api = await auth_client_factory()
    book_id = await create_book(api)

    monkeypatch.setattr(
        chapters.chapter_access_service, "save_tab_state", _async_raiser()
    )

    resp = await api.post(
        f"/api/v1/books/{book_id}/chapters/tab-state",
        json={"active_chapter_id": "c1", "open_tab_ids": ["c1"], "tab_order": ["c1"]},
    )
    assert resp.status_code == 500
    assert resp.json()["detail"] == "Failed to save tab state"


@pytest.mark.asyncio
async def test_read_handlers_still_return_404_on_missing_book(
    auth_client_factory,
):
    """The new try/except must not swallow the intentional 404s."""
    from bson import ObjectId

    api = await auth_client_factory()
    missing = str(ObjectId())

    for path in (
        f"/api/v1/books/{missing}/chapters",
        f"/api/v1/books/{missing}/chapters/metadata",
        f"/api/v1/books/{missing}/chapters/tab-state",
    ):
        resp = await api.get(path)
        assert resp.status_code == 404, path
        assert resp.json()["detail"] == "Book not found"
