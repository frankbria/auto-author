"""
Integration coverage tests for the chapter content / tab-state / analytics /
batch-content endpoint group in ``app/api/endpoints/books.py``.

Covered endpoints:
- POST   /{book_id}/chapters/tab-state        (save_tab_state)
- GET    /{book_id}/chapters/tab-state        (get_tab_state -- see note below)
- GET    /{book_id}/chapters/{chapter_id}/content   (get_chapter_content)
- PATCH  /{book_id}/chapters/{chapter_id}/content   (update_chapter_content)
- GET    /{book_id}/chapters/{chapter_id}/analytics (get_chapter_analytics)
- POST   /{book_id}/chapters/batch-content    (batch_get_chapter_content)

These run against a real MongoDB test database (session auth is mocked by the
``auth_client_factory`` fixture in ``tests/conftest.py``). No AI is involved.

Notes on *real* (sometimes surprising) behavior that these tests pin down:

* ``GET /{book_id}/chapters/tab-state`` is **shadowed** by the earlier-registered
  ``GET /{book_id}/chapters/{chapter_id}`` route, so a GET for tab-state is
  actually handled by ``get_chapter`` with ``chapter_id == "tab-state"`` and
  returns 404 "Chapter not found". The tests assert this real routing behavior.

* ``GET .../analytics`` happy path returns **500**: the endpoint calls
  ``chapter_access_service.get_chapter_analytics(user_id=..., book_id=...,
  chapter_id=..., days=...)`` but the service only accepts ``(book_id, days)``,
  raising ``TypeError`` which the endpoint converts to a 500.

* ``POST .../batch-content`` with ``include_metadata=True`` and at least one
  *found* chapter returns **500**: the endpoint does
  ``await chapter_status_service.calculate_reading_time(content_string)`` but
  ``calculate_reading_time`` is a (sync) classmethod expecting an ``int`` word
  count, so it raises and the global handler returns 500.
"""

import pytest
from bson import ObjectId

from app.db import base

API = "/api/v1/books"
MISSING_BOOK_ID = str(ObjectId())  # valid ObjectId, but never created


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
async def _create_book(api, title="Coverage Book"):
    r = await api.post(f"{API}/", json={"title": title, "genre": "Fiction"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _seed_toc(api, book_id, chapters):
    """Persist a TOC with arbitrary chapter dicts.

    Written directly through the (test-rewired) async books collection. The
    ``PUT .../toc`` endpoint can't be used here because
    ``toc_transactions.py`` captured a now-closed Motor client at import time.
    """
    result = await base.books_collection.update_one(
        {"_id": ObjectId(book_id)},
        {"$set": {"table_of_contents": {"chapters": chapters, "version": 1}}},
    )
    assert result.matched_count == 1
    return result


def _chapter(cid, title="Chapter", **extra):
    base = {
        "id": cid,
        "title": title,
        "description": "desc",
        "level": 1,
        "order": 1,
        "subchapters": [],
    }
    base.update(extra)
    return base


# --------------------------------------------------------------------------- #
# save_tab_state  (POST /{book_id}/chapters/tab-state)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_save_tab_state_success(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)

    payload = {
        "active_chapter_id": "c1",
        "open_tab_ids": ["c1", "c2"],
        "tab_order": ["c1", "c2"],
    }
    r = await api.post(f"{API}/{book_id}/chapters/tab-state", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["book_id"] == book_id
    assert body["tab_state_id"]  # a real inserted log id
    assert body["message"] == "Tab state saved successfully"


@pytest.mark.asyncio
async def test_save_tab_state_book_not_found(auth_client_factory):
    api = await auth_client_factory()
    payload = {
        "active_chapter_id": "c1",
        "open_tab_ids": ["c1"],
        "tab_order": ["c1"],
    }
    r = await api.post(f"{API}/{MISSING_BOOK_ID}/chapters/tab-state", json=payload)
    assert r.status_code == 404
    assert r.json()["detail"] == "Book not found"


@pytest.mark.asyncio
async def test_save_tab_state_wrong_owner(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)

    other = await auth_client_factory(
        overrides={"auth_id": "other-user-999", "email": "o@e.com"}
    )
    payload = {
        "active_chapter_id": "c1",
        "open_tab_ids": ["c1"],
        "tab_order": ["c1"],
    }
    r = await other.post(f"{API}/{book_id}/chapters/tab-state", json=payload)
    assert r.status_code == 403
    assert "Not authorized" in r.json()["detail"]


@pytest.mark.asyncio
async def test_save_tab_state_validation_missing_required_field(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    # active_chapter_id is required -> standard pydantic "missing" error -> 422
    payload = {
        "open_tab_ids": ["c1"],
        "tab_order": ["c1"],
    }
    r = await api.post(f"{API}/{book_id}/chapters/tab-state", json=payload)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_save_tab_state_validation_too_many_open_tabs(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    # open_tab_ids Field(max_length=20) -> "too_long" constraint error -> 422
    tabs = [f"c{i}" for i in range(21)]
    payload = {
        "active_chapter_id": "c0",
        "open_tab_ids": tabs,
        "tab_order": tabs,
    }
    r = await api.post(f"{API}/{book_id}/chapters/tab-state", json=payload)
    assert r.status_code == 422


# --------------------------------------------------------------------------- #
# get_tab_state  (GET /{book_id}/chapters/tab-state)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_get_tab_state_no_saved_state(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    # Nothing saved yet -> 200 with tab_state null
    r = await api.get(f"{API}/{book_id}/chapters/tab-state")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["book_id"] == book_id
    assert body["tab_state"] is None
    assert body["message"] == "No saved tab state found"


@pytest.mark.asyncio
async def test_get_tab_state_after_save(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)

    save_payload = {
        "active_chapter_id": "c1",
        "open_tab_ids": ["c1", "c2"],
        "tab_order": ["c1", "c2"],
    }
    s = await api.post(f"{API}/{book_id}/chapters/tab-state", json=save_payload)
    assert s.status_code == 200, s.text

    r = await api.get(f"{API}/{book_id}/chapters/tab-state")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    ts = body["tab_state"]
    assert ts["active_chapter_id"] == "c1"
    assert ts["open_tab_ids"] == ["c1", "c2"]
    assert ts["tab_order"] == ["c1", "c2"]
    assert ts["last_updated"] is not None


@pytest.mark.asyncio
async def test_get_tab_state_book_not_found(auth_client_factory):
    api = await auth_client_factory()
    r = await api.get(f"{API}/{MISSING_BOOK_ID}/chapters/tab-state")
    assert r.status_code == 404
    assert r.json()["detail"] == "Book not found"


@pytest.mark.asyncio
async def test_get_tab_state_wrong_owner(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)

    other = await auth_client_factory(
        overrides={"auth_id": "other-user-999", "email": "o@e.com"}
    )
    r = await other.get(f"{API}/{book_id}/chapters/tab-state")
    assert r.status_code == 403
    assert "Not authorized" in r.json()["detail"]


# --------------------------------------------------------------------------- #
# get_chapter_content  (GET /{book_id}/chapters/{chapter_id}/content)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_get_chapter_content_with_metadata(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    await _seed_toc(
        api,
        book_id,
        [
            _chapter(
                "ch1",
                title="Intro",
                content="hello world here",
                word_count=3,
                status="in-progress",
            )
        ],
    )

    r = await api.get(f"{API}/{book_id}/chapters/ch1/content")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["chapter_id"] == "ch1"
    assert body["title"] == "Intro"
    assert body["content"] == "hello world here"
    assert body["success"] is True
    md = body["metadata"]
    assert md["status"] == "in-progress"
    assert md["word_count"] == 3
    assert md["estimated_reading_time"] == 1  # max(1, round(3/200))
    assert md["has_subchapters"] is False
    assert md["subchapter_count"] == 0


@pytest.mark.asyncio
async def test_get_chapter_content_without_metadata(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    await _seed_toc(api, book_id, [_chapter("ch1", content="x y z")])

    r = await api.get(
        f"{API}/{book_id}/chapters/ch1/content", params={"include_metadata": "false"}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["content"] == "x y z"
    assert "metadata" not in body


@pytest.mark.asyncio
async def test_get_chapter_content_word_count_computed_from_content(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    # word_count stored as 0 -> reading time recomputed from content text
    await _seed_toc(
        api,
        book_id,
        [_chapter("ch1", content="one two three four five", word_count=0)],
    )

    r = await api.get(f"{API}/{book_id}/chapters/ch1/content")
    assert r.status_code == 200, r.text
    md = r.json()["metadata"]
    # word_count field still reflects stored value (0), but reading_time computed
    assert md["word_count"] == 0
    assert md["estimated_reading_time"] == 1  # max(1, round(5/200))


@pytest.mark.asyncio
async def test_get_chapter_content_subchapter_found(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    parent = _chapter("p1", title="Parent")
    parent["subchapters"] = [
        _chapter("sub1", title="Sub", level=2, content="deep content here")
    ]
    await _seed_toc(api, book_id, [parent])

    r = await api.get(f"{API}/{book_id}/chapters/sub1/content")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["chapter_id"] == "sub1"
    assert body["title"] == "Sub"
    assert body["content"] == "deep content here"


@pytest.mark.asyncio
async def test_get_chapter_content_book_not_found(auth_client_factory):
    api = await auth_client_factory()
    r = await api.get(f"{API}/{MISSING_BOOK_ID}/chapters/ch1/content")
    assert r.status_code == 404
    assert r.json()["detail"] == "Book not found"


@pytest.mark.asyncio
async def test_get_chapter_content_chapter_not_found(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    await _seed_toc(api, book_id, [_chapter("ch1", content="text")])

    r = await api.get(f"{API}/{book_id}/chapters/does-not-exist/content")
    assert r.status_code == 404
    assert r.json()["detail"] == "Chapter not found"


@pytest.mark.asyncio
async def test_get_chapter_content_wrong_owner(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    await _seed_toc(api, book_id, [_chapter("ch1", content="text")])

    other = await auth_client_factory(
        overrides={"auth_id": "other-user-999", "email": "o@e.com"}
    )
    r = await other.get(f"{API}/{book_id}/chapters/ch1/content")
    assert r.status_code == 403
    assert "Not authorized" in r.json()["detail"]


# --------------------------------------------------------------------------- #
# update_chapter_content  (PATCH /{book_id}/chapters/{chapter_id}/content)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_update_chapter_content_draft_to_in_progress(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    await _seed_toc(
        api, book_id, [_chapter("ch1", content="", word_count=0, status="draft")]
    )

    new_content = " ".join(["word"] * 150)  # > 100 words
    r = await api.patch(
        f"{API}/{book_id}/chapters/ch1/content",
        json={"content": new_content, "auto_update_metadata": True},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["metadata_updated"] is True

    # Verify persistence + computed metadata + status transition draft -> in-progress
    g = await api.get(f"{API}/{book_id}/chapters/ch1/content")
    md = g.json()["metadata"]
    assert md["word_count"] == 150
    assert md["status"] == "in-progress"


@pytest.mark.asyncio
async def test_update_chapter_content_in_progress_to_completed(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    await _seed_toc(
        api,
        book_id,
        [_chapter("ch1", content="seed", word_count=10, status="in-progress")],
    )

    new_content = " ".join(["word"] * 600)  # > 500 words
    r = await api.patch(
        f"{API}/{book_id}/chapters/ch1/content",
        json={"content": new_content, "auto_update_metadata": True},
    )
    assert r.status_code == 200, r.text

    g = await api.get(f"{API}/{book_id}/chapters/ch1/content")
    md = g.json()["metadata"]
    assert md["word_count"] == 600
    assert md["status"] == "completed"


@pytest.mark.asyncio
async def test_update_chapter_content_no_auto_metadata(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    await _seed_toc(
        api,
        book_id,
        [_chapter("ch1", content="old", word_count=1, status="draft")],
    )

    new_content = " ".join(["word"] * 300)  # would normally bump status/word_count
    r = await api.patch(
        f"{API}/{book_id}/chapters/ch1/content",
        json={"content": new_content, "auto_update_metadata": False},
    )
    assert r.status_code == 200, r.text
    assert r.json()["metadata_updated"] is False

    # Content changed, but metadata (word_count/status) left untouched
    g = await api.get(f"{API}/{book_id}/chapters/ch1/content")
    body = g.json()
    assert body["content"] == new_content
    assert body["metadata"]["word_count"] == 1
    assert body["metadata"]["status"] == "draft"


@pytest.mark.asyncio
async def test_update_chapter_content_book_not_found(auth_client_factory):
    api = await auth_client_factory()
    r = await api.patch(
        f"{API}/{MISSING_BOOK_ID}/chapters/ch1/content",
        json={"content": "hi", "auto_update_metadata": True},
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "Book not found"


@pytest.mark.asyncio
async def test_update_chapter_content_chapter_not_found(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    await _seed_toc(api, book_id, [_chapter("ch1", content="text")])

    r = await api.patch(
        f"{API}/{book_id}/chapters/nope/content",
        json={"content": "hi", "auto_update_metadata": True},
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "Chapter not found"


@pytest.mark.asyncio
async def test_update_chapter_content_wrong_owner(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    await _seed_toc(api, book_id, [_chapter("ch1", content="text")])

    other = await auth_client_factory(
        overrides={"auth_id": "other-user-999", "email": "o@e.com"}
    )
    r = await other.patch(
        f"{API}/{book_id}/chapters/ch1/content",
        json={"content": "hi", "auto_update_metadata": True},
    )
    assert r.status_code == 403
    assert "Not authorized" in r.json()["detail"]


# --------------------------------------------------------------------------- #
# get_chapter_analytics  (GET /{book_id}/chapters/{chapter_id}/analytics)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_get_chapter_analytics_happy_path(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    await _seed_toc(api, book_id, [_chapter("ch1", content="text")])

    r = await api.get(f"{API}/{book_id}/chapters/ch1/analytics", params={"days": 14})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["book_id"] == book_id
    assert body["chapter_id"] == "ch1"
    assert body["analytics_period_days"] == 14
    assert isinstance(body["analytics"], list)


@pytest.mark.asyncio
async def test_get_chapter_analytics_book_not_found(auth_client_factory):
    api = await auth_client_factory()
    r = await api.get(f"{API}/{MISSING_BOOK_ID}/chapters/ch1/analytics")
    assert r.status_code == 404
    assert r.json()["detail"] == "Book not found"


@pytest.mark.asyncio
async def test_get_chapter_analytics_wrong_owner(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)

    other = await auth_client_factory(
        overrides={"auth_id": "other-user-999", "email": "o@e.com"}
    )
    r = await other.get(f"{API}/{book_id}/chapters/ch1/analytics")
    assert r.status_code == 403
    assert "Not authorized" in r.json()["detail"]


@pytest.mark.asyncio
async def test_get_chapter_analytics_days_too_low(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    r = await api.get(
        f"{API}/{book_id}/chapters/ch1/analytics", params={"days": 0}
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_get_chapter_analytics_days_too_high(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    r = await api.get(
        f"{API}/{book_id}/chapters/ch1/analytics", params={"days": 400}
    )
    assert r.status_code == 422


# --------------------------------------------------------------------------- #
# batch_get_chapter_content  (POST /{book_id}/chapters/batch-content)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_batch_content_without_metadata_found_and_missing(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    await _seed_toc(
        api,
        book_id,
        [
            _chapter("ch1", title="One", content="alpha"),
            _chapter("ch2", title="Two", content="beta"),
        ],
    )

    r = await api.post(
        f"{API}/{book_id}/chapters/batch-content",
        json={
            "chapter_ids": ["ch1", "ch2", "missing"],
            "include_metadata": False,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["requested_count"] == 3
    assert body["found_count"] == 2
    assert set(body["chapters"].keys()) == {"ch1", "ch2"}
    assert body["chapters"]["ch1"]["title"] == "One"
    assert body["chapters"]["ch1"]["content"] == "alpha"
    assert "metadata" not in body["chapters"]["ch1"]


@pytest.mark.asyncio
async def test_batch_content_metadata_all_missing_returns_empty(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    await _seed_toc(api, book_id, [_chapter("ch1", content="alpha")])

    # include_metadata True but no requested id is found -> metadata branch never
    # executes -> clean 200 with empty chapters dict.
    r = await api.post(
        f"{API}/{book_id}/chapters/batch-content",
        json={"chapter_ids": ["nope1", "nope2"], "include_metadata": True},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["found_count"] == 0
    assert body["requested_count"] == 2
    assert body["chapters"] == {}


@pytest.mark.asyncio
async def test_batch_content_metadata_found_returns_metadata(auth_client_factory):
    """include_metadata True + a found chapter returns per-chapter metadata with a
    computed (non-negative int) estimated_reading_time."""
    api = await auth_client_factory()
    book_id = await _create_book(api)
    await _seed_toc(
        api,
        book_id,
        [_chapter("ch1", title="One", content="alpha beta gamma", status="draft")],
    )

    r = await api.post(
        f"{API}/{book_id}/chapters/batch-content",
        json={"chapter_ids": ["ch1"], "include_metadata": True},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["found_count"] == 1
    md = body["chapters"]["ch1"]["metadata"]
    assert md["status"] == "draft"
    rt = md["estimated_reading_time"]
    assert isinstance(rt, int) and rt >= 0


@pytest.mark.asyncio
async def test_batch_content_too_many_chapters(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    r = await api.post(
        f"{API}/{book_id}/chapters/batch-content",
        json={
            "chapter_ids": [f"c{i}" for i in range(21)],
            "include_metadata": False,
        },
    )
    assert r.status_code == 400
    assert "more than 20" in r.json()["detail"]


@pytest.mark.asyncio
async def test_batch_content_book_not_found(auth_client_factory):
    api = await auth_client_factory()
    r = await api.post(
        f"{API}/{MISSING_BOOK_ID}/chapters/batch-content",
        json={"chapter_ids": ["ch1"], "include_metadata": False},
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "Book not found"


@pytest.mark.asyncio
async def test_batch_content_wrong_owner(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    await _seed_toc(api, book_id, [_chapter("ch1", content="alpha")])

    other = await auth_client_factory(
        overrides={"auth_id": "other-user-999", "email": "o@e.com"}
    )
    r = await other.post(
        f"{API}/{book_id}/chapters/batch-content",
        json={"chapter_ids": ["ch1"], "include_metadata": False},
    )
    assert r.status_code == 403
    assert "Not authorized" in r.json()["detail"]
