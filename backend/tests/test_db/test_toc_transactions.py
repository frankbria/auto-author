"""
Integration tests for app/db/toc_transactions.py.

Exercises the atomic TOC transaction helpers against a real local MongoDB
(via the motor_reinit_db fixture) — happy paths AND the data-integrity
failure paths: invalid IDs, missing/unauthorized books, optimistic-locking
version conflicts, missing chapters, and the transaction-detection fallback.

ponytail: the `if use_transaction:` real-transaction branches require a
MongoDB replica set; a standalone test server reports no setName, so those
functions run via the non-transactional fallback here. Covering the live
transaction/rollback branch would need a replica-set test fixture — upgrade
path if/when CI runs Mongo as a replica set.
"""

import pytest
import pytest_asyncio
from bson import ObjectId

import app.db.toc_transactions as tx


@pytest_asyncio.fixture
async def seed_book(motor_reinit_db):
    """Insert a book (optionally with a TOC) and return its id + owner."""
    owner = "owner-auth-123"

    async def _make(toc=None, owner_id=owner):
        doc = {"_id": ObjectId(), "owner_id": owner_id, "title": "T"}
        if toc is not None:
            doc["table_of_contents"] = toc
        await tx.books_collection.insert_one(doc)
        return str(doc["_id"]), owner_id

    return _make


async def _get_toc(book_id):
    book = await tx.books_collection.find_one({"_id": ObjectId(book_id)})
    return book.get("table_of_contents", {})


# ---------------------------------------------------------------------------
# update_toc_with_transaction
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_toc_creates_toc_and_assigns_ids(seed_book):
    book_id, owner = await seed_book()
    toc_data = {
        "chapters": [
            {"title": "Ch1", "subchapters": [{"title": "Sub1"}]},  # no ids
            {"title": "Ch2", "id": "keep-me"},
        ]
    }
    result = await tx.update_toc_with_transaction(book_id, toc_data, owner)

    assert result["version"] == 2
    assert result["status"] == "edited"
    ch = result["chapters"]
    assert ch[0]["id"] and ch[0]["subchapters"][0]["id"]  # auto-assigned
    assert ch[1]["id"] == "keep-me"  # preserved
    # persisted
    assert (await _get_toc(book_id))["version"] == 2


@pytest.mark.asyncio
async def test_update_toc_version_increment_on_existing_toc(seed_book):
    book_id, owner = await seed_book(toc={"version": 5, "chapters": []})
    result = await tx.update_toc_with_transaction(
        book_id, {"chapters": [{"title": "New"}]}, owner
    )
    assert result["version"] == 6


@pytest.mark.asyncio
async def test_update_toc_invalid_book_id(seed_book):
    await seed_book()
    with pytest.raises(ValueError, match="Invalid book ID format"):
        await tx.update_toc_with_transaction("not-an-objectid", {}, "owner-auth-123")


@pytest.mark.asyncio
async def test_update_toc_book_not_found(motor_reinit_db):
    with pytest.raises(ValueError, match="Book not found"):
        await tx.update_toc_with_transaction(str(ObjectId()), {}, "nobody")


@pytest.mark.asyncio
async def test_update_toc_not_authorized(seed_book):
    book_id, _ = await seed_book(owner_id="real-owner")
    with pytest.raises(ValueError, match="Not authorized"):
        await tx.update_toc_with_transaction(book_id, {}, "intruder")


@pytest.mark.asyncio
async def test_update_toc_version_conflict(seed_book):
    book_id, owner = await seed_book(toc={"version": 3, "chapters": []})
    with pytest.raises(ValueError, match="Version conflict"):
        await tx.update_toc_with_transaction(
            book_id, {"chapters": [], "expected_version": 1}, owner
        )


@pytest.mark.asyncio
async def test_update_toc_expected_version_match(seed_book):
    book_id, owner = await seed_book(toc={"version": 3, "chapters": []})
    result = await tx.update_toc_with_transaction(
        book_id, {"chapters": [], "expected_version": 3}, owner
    )
    assert result["version"] == 4


# ---------------------------------------------------------------------------
# add_chapter_with_transaction
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_top_level_chapter(seed_book):
    book_id, owner = await seed_book(toc={"version": 1, "chapters": []})
    chapter = await tx.add_chapter_with_transaction(book_id, {"title": "C"}, owner)
    assert chapter["id"] and chapter["created_at"]
    toc = await _get_toc(book_id)
    assert len(toc["chapters"]) == 1 and toc["version"] == 2


@pytest.mark.asyncio
async def test_add_subchapter_to_parent(seed_book):
    parent_id = "parent-1"
    book_id, owner = await seed_book(
        toc={"version": 1, "chapters": [{"id": parent_id, "title": "P"}]}
    )
    sub = await tx.add_chapter_with_transaction(
        book_id, {"title": "Sub"}, owner, parent_chapter_id=parent_id
    )
    toc = await _get_toc(book_id)
    assert toc["chapters"][0]["subchapters"][0]["id"] == sub["id"]


@pytest.mark.asyncio
async def test_add_subchapter_parent_not_found(seed_book):
    book_id, owner = await seed_book(toc={"version": 1, "chapters": []})
    with pytest.raises(ValueError, match="Parent chapter not found"):
        await tx.add_chapter_with_transaction(
            book_id, {"title": "Sub"}, owner, parent_chapter_id="ghost"
        )


@pytest.mark.asyncio
async def test_add_chapter_book_not_found(motor_reinit_db):
    with pytest.raises(ValueError, match="not authorized"):
        await tx.add_chapter_with_transaction(str(ObjectId()), {"title": "C"}, "nobody")


# ---------------------------------------------------------------------------
# update_chapter_with_transaction
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_chapter_top_level(seed_book):
    cid = "ch-1"
    book_id, owner = await seed_book(
        toc={"version": 1, "chapters": [{"id": cid, "title": "Old"}]}
    )
    updated = await tx.update_chapter_with_transaction(
        book_id, cid, {"title": "New"}, owner
    )
    assert updated["title"] == "New" and updated["updated_at"]
    assert (await _get_toc(book_id))["version"] == 2


@pytest.mark.asyncio
async def test_update_chapter_in_subchapter(seed_book):
    sub_id = "sub-1"
    book_id, owner = await seed_book(
        toc={
            "version": 1,
            "chapters": [{"id": "p", "subchapters": [{"id": sub_id, "title": "Old"}]}],
        }
    )
    updated = await tx.update_chapter_with_transaction(
        book_id, sub_id, {"title": "New"}, owner
    )
    assert updated["title"] == "New"


@pytest.mark.asyncio
async def test_update_chapter_not_found(seed_book):
    book_id, owner = await seed_book(toc={"version": 1, "chapters": []})
    with pytest.raises(ValueError, match="Chapter not found"):
        await tx.update_chapter_with_transaction(book_id, "ghost", {"title": "x"}, owner)


@pytest.mark.asyncio
async def test_update_chapter_book_not_found(motor_reinit_db):
    with pytest.raises(ValueError, match="not authorized"):
        await tx.update_chapter_with_transaction(str(ObjectId()), "c", {}, "nobody")


# ---------------------------------------------------------------------------
# delete_chapter_with_transaction
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_top_level_chapter(seed_book):
    cid = "ch-1"
    book_id, owner = await seed_book(
        toc={"version": 1, "chapters": [{"id": cid, "title": "X"}]}
    )
    assert await tx.delete_chapter_with_transaction(book_id, cid, owner) is True
    toc = await _get_toc(book_id)
    assert toc["chapters"] == [] and toc["version"] == 2


@pytest.mark.asyncio
async def test_delete_subchapter(seed_book):
    sub_id = "sub-1"
    book_id, owner = await seed_book(
        toc={
            "version": 1,
            "chapters": [{"id": "p", "subchapters": [{"id": sub_id}]}],
        }
    )
    assert await tx.delete_chapter_with_transaction(book_id, sub_id, owner) is True
    toc = await _get_toc(book_id)
    assert toc["chapters"][0]["subchapters"] == []


@pytest.mark.asyncio
async def test_delete_chapter_not_found(seed_book):
    book_id, owner = await seed_book(toc={"version": 1, "chapters": []})
    with pytest.raises(ValueError, match="Chapter not found"):
        await tx.delete_chapter_with_transaction(book_id, "ghost", owner)


@pytest.mark.asyncio
async def test_delete_chapter_book_not_found(motor_reinit_db):
    with pytest.raises(ValueError, match="not authorized"):
        await tx.delete_chapter_with_transaction(str(ObjectId()), "c", "nobody")


# ---------------------------------------------------------------------------
# reorder_chapters_with_transaction
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reorder_chapters(seed_book):
    book_id, owner = await seed_book(
        toc={
            "version": 1,
            "chapters": [
                {"id": "a", "title": "A"},
                {"id": "b", "title": "B"},
                {"id": "c", "title": "C"},  # left out of order list
            ],
        }
    )
    result = await tx.reorder_chapters_with_transaction(
        book_id, [{"id": "b", "order": 1}, {"id": "a", "order": 2}], owner
    )
    ids = [c["id"] for c in result["chapters"]]
    assert ids[:2] == ["b", "a"]  # reordered
    assert "c" in ids  # untouched chapter appended at the end
    assert result["version"] == 2


@pytest.mark.asyncio
async def test_reorder_chapters_ignores_unknown_ids(seed_book):
    book_id, owner = await seed_book(
        toc={"version": 1, "chapters": [{"id": "a", "title": "A"}]}
    )
    result = await tx.reorder_chapters_with_transaction(
        book_id, [{"id": "missing", "order": 1}, {"id": "a", "order": 2}], owner
    )
    assert [c["id"] for c in result["chapters"]] == ["a"]


@pytest.mark.asyncio
async def test_reorder_chapters_book_not_found(motor_reinit_db):
    with pytest.raises(ValueError, match="not authorized"):
        await tx.reorder_chapters_with_transaction(str(ObjectId()), [], "nobody")


# ---------------------------------------------------------------------------
# transaction-detection fallback (DB error while probing replica-set status)
# ---------------------------------------------------------------------------

class _RaisingClient:
    """Stand-in whose session probe raises, forcing use_transaction=False."""

    def start_session(self):
        raise RuntimeError("probe failed")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "call",
    [
        lambda bid, owner: tx.update_toc_with_transaction(bid, {"chapters": []}, owner),
        lambda bid, owner: tx.add_chapter_with_transaction(bid, {"title": "C"}, owner),
        lambda bid, owner: tx.update_chapter_with_transaction(bid, "c", {"t": "x"}, owner),
        lambda bid, owner: tx.delete_chapter_with_transaction(bid, "c", owner),
        lambda bid, owner: tx.reorder_chapters_with_transaction(bid, [], owner),
    ],
    ids=["update_toc", "add", "update_ch", "delete", "reorder"],
)
async def test_detection_failure_falls_back_to_no_transaction(seed_book, monkeypatch, call):
    # Probing the client raises -> the except branch sets use_transaction=False
    # and the operation still completes via the non-transactional path.
    book_id, owner = await seed_book(
        toc={"version": 1, "chapters": [{"id": "c", "title": "Old"}]}
    )
    monkeypatch.setattr(tx, "_client", _RaisingClient())
    await call(book_id, owner)  # no exception -> fallback path ran


@pytest.mark.asyncio
async def test_update_toc_failed_write_raises(seed_book, monkeypatch):
    """modified_count == 0 with no version drift -> generic write failure."""
    book_id, owner = await seed_book(toc={"version": 2, "chapters": []})

    class _Result:
        modified_count = 0

    async def _fake_update_one(*args, **kwargs):
        return _Result()

    monkeypatch.setattr(tx.books_collection, "update_one", _fake_update_one)
    with pytest.raises(ValueError, match="Failed to update TOC"):
        await tx.update_toc_with_transaction(book_id, {"chapters": []}, owner)
