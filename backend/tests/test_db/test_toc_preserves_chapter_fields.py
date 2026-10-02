"""PUT /toc must not erase chapter drafts (#749).

The Edit TOC page sends each chapter as {id, title, description, level, order,
subchapters} — no content, status or word_count. `_update_toc_internal` merged
the TOC only at the top level, so that `chapters` list replaced the stored one
and every draft in the book became None on a plain rename. These tests send the
page's exact payload shape against a real Mongo and check the drafts survive.
"""

import pytest
import pytest_asyncio
from bson import ObjectId

import app.db.toc_transactions as tx

OWNER = "owner-749"

SERVER_FIELDS = {
    "status": "in-progress",
    "word_count": 1234,
    "last_modified": "2026-09-30T10:00:00+00:00",
    "estimated_reading_time": 6,
    "is_active_tab": True,
    "created_at": "2026-09-01T09:00:00+00:00",
}


def _stored(cid, title, order, subchapters=()):
    return {
        "id": cid,
        "title": title,
        "description": "",
        "level": 1,
        "order": order,
        "content": f"<p>draft of {cid}</p>",
        **SERVER_FIELDS,
        "subchapters": list(subchapters),
    }


def _stored_sub(cid, title, order):
    sub = _stored(cid, title, order)
    sub["level"] = 2
    del sub["subchapters"]
    return sub


def _edit_toc_item(cid, title, order, subchapters=None, level=1):
    """Exactly what edit-toc/page.tsx convertChaptersToTocData sends."""
    item = {"id": cid, "title": title, "description": "", "level": level, "order": order}
    if subchapters is not None:
        item["subchapters"] = subchapters
    return item


@pytest_asyncio.fixture
async def book_with_drafts(motor_reinit_db):
    toc = {
        "version": 3,
        "chapters": [
            _stored("c1", "One", 1, [_stored_sub("s1", "One-A", 1)]),
            _stored("c2", "Two", 2, [_stored_sub("s2", "Two-A", 1)]),
            _stored("c3", "Three", 3),
        ],
    }
    doc = {"_id": ObjectId(), "owner_id": OWNER, "title": "T", "table_of_contents": toc}
    await tx.books_collection.insert_one(doc)
    return str(doc["_id"])


async def _stored_toc(book_id):
    book = await tx.books_collection.find_one({"_id": ObjectId(book_id)})
    return book["table_of_contents"]


def _by_id(toc):
    flat = {}
    for ch in toc["chapters"]:
        flat[ch["id"]] = ch
        for sub in ch.get("subchapters", []):
            flat[sub["id"]] = sub
    return flat


def _assert_draft_kept(item, cid):
    assert item["content"] == f"<p>draft of {cid}</p>"
    for key, value in SERVER_FIELDS.items():
        assert item[key] == value, f"{cid}.{key}"


@pytest.mark.asyncio
async def test_rename_keeps_every_draft(book_with_drafts):
    payload = {
        "chapters": [
            _edit_toc_item("c1", "One renamed", 1, [_edit_toc_item("s1", "One-A", 1, level=2)]),
            _edit_toc_item("c2", "Two", 2, [_edit_toc_item("s2", "Two-A", 1, level=2)]),
            _edit_toc_item("c3", "Three", 3, []),
        ]
    }
    await tx.update_toc_with_transaction(book_with_drafts, payload, OWNER)

    items = _by_id(await _stored_toc(book_with_drafts))
    assert items["c1"]["title"] == "One renamed"
    for cid in ("c1", "s1", "c2", "s2", "c3"):
        _assert_draft_kept(items[cid], cid)


@pytest.mark.asyncio
async def test_reorder_move_and_delete(book_with_drafts):
    """Reorder chapters, move s2 under c3, and omit c1 (deleting it and s1)."""
    payload = {
        "chapters": [
            _edit_toc_item("c3", "Three", 1, [_edit_toc_item("s2", "Two-A", 1, level=2)]),
            _edit_toc_item("c2", "Two", 2, []),
        ]
    }
    result = await tx.update_toc_with_transaction(book_with_drafts, payload, OWNER)

    toc = await _stored_toc(book_with_drafts)
    assert [c["id"] for c in toc["chapters"]] == ["c3", "c2"]
    assert toc["chapters"][0]["order"] == 1
    items = _by_id(toc)
    assert "c1" not in items and "s1" not in items
    for cid in ("c3", "c2", "s2"):
        _assert_draft_kept(items[cid], cid)
    # The returned TOC is what was stored.
    assert _by_id(result)["s2"]["content"] == "<p>draft of s2</p>"


@pytest.mark.asyncio
async def test_stored_value_wins_and_new_items_keep_their_own(book_with_drafts):
    """Server-owned fields are not client-writable; unknown ids are untouched."""
    payload = {
        "chapters": [
            {**_edit_toc_item("c1", "One", 1, []), "content": None, "status": "draft"},
            {**_edit_toc_item("new", "Brand new", 2, []), "status": "draft", "word_count": 0},
        ]
    }
    await tx.update_toc_with_transaction(book_with_drafts, payload, OWNER)

    items = _by_id(await _stored_toc(book_with_drafts))
    _assert_draft_kept(items["c1"], "c1")
    assert items["new"]["status"] == "draft"
    assert items["new"]["word_count"] == 0
    assert "content" not in items["new"]


@pytest.mark.asyncio
async def test_idless_items_never_match_each_other(motor_reinit_db):
    """A legacy stored chapter with no id must not lend its draft to a new item."""
    legacy = _stored("x", "Legacy", 1)
    del legacy["id"]
    doc = {
        "_id": ObjectId(),
        "owner_id": OWNER,
        "title": "T",
        "table_of_contents": {"version": 1, "chapters": [legacy]},
    }
    await tx.books_collection.insert_one(doc)

    result = await tx.update_toc_with_transaction(
        str(doc["_id"]), {"chapters": [{"title": "Fresh", "order": 1}]}, OWNER
    )
    assert "content" not in result["chapters"][0]
