"""
#759: the chapter content PATCH takes an optional ``expected_last_modified``
precondition, so a stale tab gets a 409 instead of silently overwriting edits
saved from another device.

Real MongoDB test database; only session auth is faked (``auth_client_factory``).
"""

import asyncio
from datetime import datetime, timezone

import pytest
from bson import ObjectId

from app.api.endpoints import books as books_endpoint
from app.db import base

API = "/api/v1/books"


async def _book_with(api, chapters):
    r = await api.post(f"{API}/", json={"title": "Precondition", "genre": "Fiction"})
    assert r.status_code == 201, r.text
    book_id = r.json()["id"]
    await base.books_collection.update_one(
        {"_id": ObjectId(book_id)},
        {"$set": {"table_of_contents": {"chapters": chapters, "version": 1}}},
    )
    return book_id


def _ch(cid, **extra):
    return {"id": cid, "title": cid, "level": 1, "order": 1, "subchapters": [], **extra}


async def _stored_content(book_id, cid, parent=None):
    book = await base.books_collection.find_one({"_id": ObjectId(book_id)})
    chapters = book["table_of_contents"]["chapters"]
    if parent:
        chapters = next(c for c in chapters if c["id"] == parent)["subchapters"]
    return next(c for c in chapters if c["id"] == cid).get("content")


async def _token(api, book_id, cid):
    r = await api.get(f"{API}/{book_id}/chapters/{cid}/content")
    assert r.status_code == 200, r.text
    return r.json()["last_modified"]


def _url(book_id, cid):
    return f"{API}/{book_id}/chapters/{cid}/content"


@pytest.mark.asyncio
async def test_get_returns_last_modified_even_without_metadata(auth_client_factory):
    api = await auth_client_factory()
    stamp = "2026-10-01T10:00:00.000001+00:00"
    book_id = await _book_with(api, [_ch("c1", content="x", last_modified=stamp)])

    r = await api.get(_url(book_id, "c1"), params={"include_metadata": False})
    assert r.status_code == 200
    assert r.json()["last_modified"] == stamp


@pytest.mark.asyncio
async def test_same_stale_token_twice_gives_200_then_409(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _book_with(
        api, [_ch("c1", content="v0", last_modified="2026-10-01T10:00:00+00:00")]
    )
    token = await _token(api, book_id, "c1")

    first = await api.patch(
        _url(book_id, "c1"), json={"content": "device A", "expected_last_modified": token}
    )
    assert first.status_code == 200, first.text
    new_token = first.json()["last_modified"]
    assert new_token and new_token != token

    second = await api.patch(
        _url(book_id, "c1"), json={"content": "device B", "expected_last_modified": token}
    )
    assert second.status_code == 409, second.text
    detail = second.json()["detail"]
    # What #760 needs to offer reload-or-overwrite without another GET.
    assert detail["current_last_modified"] == new_token
    assert detail["current_content"] == "device A"
    assert await _stored_content(book_id, "c1") == "device A"

    # Overwrite = resend with the current token.
    again = await api.patch(
        _url(book_id, "c1"),
        json={"content": "device B", "expected_last_modified": new_token},
    )
    assert again.status_code == 200, again.text
    assert await _stored_content(book_id, "c1") == "device B"


@pytest.mark.asyncio
async def test_concurrent_writers_with_one_token_exactly_one_wins(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _book_with(
        api, [_ch("c1", content="v0", last_modified="2026-10-01T10:00:00+00:00")]
    )
    token = await _token(api, book_id, "c1")

    responses = await asyncio.gather(
        *(
            api.patch(
                _url(book_id, "c1"),
                json={"content": f"writer-{i}", "expected_last_modified": token},
            )
            for i in range(5)
        )
    )

    codes = sorted(r.status_code for r in responses)
    assert codes == [200, 409, 409, 409, 409], [r.text for r in responses]
    winner = next(i for i, r in enumerate(responses) if r.status_code == 200)
    assert await _stored_content(book_id, "c1") == f"writer-{winner}"


def _commit_first(monkeypatch, competing_write):
    """Run a real competing write in the window between the handler's read and
    its own write. The gather test above usually lands there too, but only
    when the event loop happens to interleave; this pins the window open."""
    real = books_endpoint.apply_chapter_content_update

    async def write_after_competitor(**kwargs):
        await competing_write(real, kwargs)
        return await real(**kwargs)

    monkeypatch.setattr(
        books_endpoint, "apply_chapter_content_update", write_after_competitor
    )


@pytest.mark.asyncio
async def test_save_committed_after_the_read_still_gets_409(
    auth_client_factory, monkeypatch
):
    api = await auth_client_factory()
    book_id = await _book_with(
        api, [_ch("c1", content="v0", last_modified="2026-10-01T10:00:00+00:00")]
    )
    token = await _token(api, book_id, "c1")

    async def other_device_saves(real, kwargs):
        fields = {"content": "other device", "last_modified": "2026-10-01T11:00:00+00:00"}
        assert await real(**{**kwargs, "chapter_fields": fields})

    _commit_first(monkeypatch, other_device_saves)
    r = await api.patch(
        _url(book_id, "c1"), json={"content": "stale", "expected_last_modified": token}
    )
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["current_content"] == "other device"
    assert await _stored_content(book_id, "c1") == "other device"


@pytest.mark.asyncio
async def test_chapter_deleted_after_the_read_is_404(auth_client_factory, monkeypatch):
    api = await auth_client_factory()
    book_id = await _book_with(api, [_ch("c1", content="v0"), _ch("c2")])
    token = await _token(api, book_id, "c1")

    async def chapter_deleted(real, kwargs):
        await base.books_collection.update_one(
            {"_id": ObjectId(book_id)},
            {"$pull": {"table_of_contents.chapters": {"id": "c1"}}},
        )

    _commit_first(monkeypatch, chapter_deleted)
    r = await api.patch(
        _url(book_id, "c1"), json={"content": "A", "expected_last_modified": token}
    )
    assert r.status_code == 404, r.text


@pytest.mark.asyncio
async def test_without_precondition_last_writer_still_wins(auth_client_factory):
    """Back-compat: the current client sends no precondition until #760."""
    api = await auth_client_factory()
    book_id = await _book_with(api, [_ch("c1", content="v0")])

    for text in ("one", "two"):
        r = await api.patch(_url(book_id, "c1"), json={"content": text})
        assert r.status_code == 200, r.text
    assert await _stored_content(book_id, "c1") == "two"


@pytest.mark.asyncio
async def test_null_token_guards_a_never_saved_chapter(auth_client_factory):
    """Freshly generated chapters have no last_modified; null is a real check."""
    api = await auth_client_factory()
    book_id = await _book_with(api, [_ch("c1")])
    assert await _token(api, book_id, "c1") is None

    first = await api.patch(
        _url(book_id, "c1"), json={"content": "A", "expected_last_modified": None}
    )
    assert first.status_code == 200, first.text
    second = await api.patch(
        _url(book_id, "c1"), json={"content": "B", "expected_last_modified": None}
    )
    assert second.status_code == 409, second.text
    assert await _stored_content(book_id, "c1") == "A"


@pytest.mark.asyncio
async def test_date_stored_last_modified_round_trips(auth_client_factory):
    """The bulk-status endpoint stores a BSON Date, not a string."""
    api = await auth_client_factory()
    stored = datetime(2026, 10, 1, 10, 0, 0, 123000, tzinfo=timezone.utc)
    book_id = await _book_with(api, [_ch("c1", content="v0", last_modified=stored)])
    token = await _token(api, book_id, "c1")
    # Same shape as the tokens the PATCH writes, so a client never sees two formats.
    assert token == "2026-10-01T10:00:00.123000+00:00"

    r = await api.patch(
        _url(book_id, "c1"), json={"content": "fresh", "expected_last_modified": token}
    )
    assert r.status_code == 200, r.text
    assert await _stored_content(book_id, "c1") == "fresh"


@pytest.mark.asyncio
async def test_no_auto_metadata_still_invalidates_the_token(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _book_with(
        api, [_ch("c1", content="v0", last_modified="2026-10-01T10:00:00+00:00")]
    )
    token = await _token(api, book_id, "c1")

    body = {"content": "A", "auto_update_metadata": False, "expected_last_modified": token}
    assert (await api.patch(_url(book_id, "c1"), json=body)).status_code == 200
    body["content"] = "B"
    assert (await api.patch(_url(book_id, "c1"), json=body)).status_code == 409
    assert await _stored_content(book_id, "c1") == "A"


@pytest.mark.asyncio
async def test_subchapter_precondition(auth_client_factory):
    api = await auth_client_factory()
    sub = _ch("s1", content="v0", last_modified="2026-10-01T10:00:00+00:00", level=2)
    book_id = await _book_with(api, [_ch("p1", subchapters=[sub])])
    token = await _token(api, book_id, "s1")

    body = {"content": "A", "expected_last_modified": token}
    assert (await api.patch(_url(book_id, "s1"), json=body)).status_code == 200
    body["content"] = "B"
    assert (await api.patch(_url(book_id, "s1"), json=body)).status_code == 409
    assert await _stored_content(book_id, "s1", parent="p1") == "A"


@pytest.mark.asyncio
async def test_missing_chapter_is_404_not_409(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _book_with(api, [_ch("c1", content="v0")])

    r = await api.patch(
        _url(book_id, "gone"), json={"content": "A", "expected_last_modified": "x"}
    )
    assert r.status_code == 404
