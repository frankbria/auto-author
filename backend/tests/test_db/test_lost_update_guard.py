"""
Regression tests for the #177 lost-update fix.

The old autosave path rewrote the WHOLE ``table_of_contents`` (and the whole
``summary_history`` array) via a version-less ``$set``, so two concurrent writers
silently clobbered each other — real data loss. These tests drive the new
targeted helpers against a real local MongoDB (via ``motor_reinit_db``) and
assert that interleaved writers no longer lose each other's updates.

``apply_chapter_content_update`` uses a positional ``$set`` (arrayFilters) that
touches only the target chapter, so a concurrent save to a *different* chapter
can't overwrite it. ``update_book_summary_atomic`` uses ``$push``/``$slice`` so
concurrent history appends both survive.
"""

import asyncio

import pytest
from bson import ObjectId

import app.db.book as bookdao

OWNER = "owner-auth-177"


async def _seed(toc=None, summary=None, summary_history=None, owner_id=OWNER):
    doc = {"_id": ObjectId(), "owner_id": owner_id, "title": "T"}
    if toc is not None:
        doc["table_of_contents"] = toc
    if summary is not None:
        doc["summary"] = summary
    if summary_history is not None:
        doc["summary_history"] = summary_history
    await bookdao.books_collection.insert_one(doc)
    return str(doc["_id"])


async def _book(book_id):
    return await bookdao.books_collection.find_one({"_id": ObjectId(book_id)})


def _chapters(book):
    return book["table_of_contents"]["chapters"]


def _by_id(chapters, cid):
    return next(c for c in chapters if c["id"] == cid)


# --------------------------------------------------------------------------- #
# apply_chapter_content_update
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_updates_only_target_chapter_and_bumps_version(motor_reinit_db):
    book_id = await _seed(
        toc={
            "version": 3,
            "chapters": [
                {"id": "a", "content": "old-a"},
                {"id": "b", "content": "old-b"},
            ],
        }
    )

    matched = await bookdao.apply_chapter_content_update(
        book_id, "a", None, {"content": "new-a", "word_count": 2}, OWNER
    )
    assert matched is True

    chapters = _chapters(await _book(book_id))
    assert _by_id(chapters, "a")["content"] == "new-a"
    assert _by_id(chapters, "a")["word_count"] == 2
    assert _by_id(chapters, "b")["content"] == "old-b"  # sibling untouched
    toc = (await _book(book_id))["table_of_contents"]
    assert toc["version"] == 4  # atomic $inc from 3
    assert toc["status"] == "edited"


@pytest.mark.asyncio
async def test_interleaved_writers_no_lost_update(motor_reinit_db):
    """Two concurrent saves to DIFFERENT chapters must both persist."""
    book_id = await _seed(
        toc={
            "version": 1,
            "chapters": [
                {"id": "a", "content": "old-a"},
                {"id": "b", "content": "old-b"},
            ],
        }
    )

    await asyncio.gather(
        bookdao.apply_chapter_content_update(
            book_id, "a", None, {"content": "WRITER-A"}, OWNER
        ),
        bookdao.apply_chapter_content_update(
            book_id, "b", None, {"content": "WRITER-B"}, OWNER
        ),
    )

    chapters = _chapters(await _book(book_id))
    # Neither write clobbered the other (the old whole-TOC $set lost one of these).
    assert _by_id(chapters, "a")["content"] == "WRITER-A"
    assert _by_id(chapters, "b")["content"] == "WRITER-B"
    # Both writers incremented the version atomically.
    assert (await _book(book_id))["table_of_contents"]["version"] == 3


@pytest.mark.asyncio
async def test_subchapter_targeted_update(motor_reinit_db):
    book_id = await _seed(
        toc={
            "version": 1,
            "chapters": [
                {
                    "id": "p",
                    "content": "parent",
                    "subchapters": [{"id": "s", "content": "old-sub"}],
                }
            ],
        }
    )

    matched = await bookdao.apply_chapter_content_update(
        book_id, "s", "p", {"content": "new-sub"}, OWNER
    )
    assert matched is True

    chapters = _chapters(await _book(book_id))
    assert chapters[0]["subchapters"][0]["content"] == "new-sub"
    assert chapters[0]["content"] == "parent"  # parent body untouched


@pytest.mark.asyncio
async def test_version_created_from_legacy_toc_without_version(motor_reinit_db):
    book_id = await _seed(toc={"chapters": [{"id": "a", "content": "x"}]})

    await bookdao.apply_chapter_content_update(
        book_id, "a", None, {"content": "y"}, OWNER
    )
    # $inc on a missing field starts from the increment value.
    assert (await _book(book_id))["table_of_contents"]["version"] == 1


@pytest.mark.asyncio
async def test_missing_chapter_no_match_does_not_bump_version(motor_reinit_db):
    """A chapter id that no longer exists must be a clean no-match (False),
    not a false success that only bumps the version (TOCTOU guard)."""
    book_id = await _seed(
        toc={"version": 2, "chapters": [{"id": "a", "content": "x"}]}
    )
    matched = await bookdao.apply_chapter_content_update(
        book_id, "gone", None, {"content": "y"}, OWNER
    )
    assert matched is False
    toc = (await _book(book_id))["table_of_contents"]
    assert toc["version"] == 2  # untouched
    assert _by_id(toc["chapters"], "a")["content"] == "x"


@pytest.mark.asyncio
async def test_missing_subchapter_no_match(motor_reinit_db):
    book_id = await _seed(
        toc={
            "version": 1,
            "chapters": [{"id": "p", "content": "parent", "subchapters": []}],
        }
    )
    matched = await bookdao.apply_chapter_content_update(
        book_id, "gone-sub", "p", {"content": "y"}, OWNER
    )
    assert matched is False
    assert (await _book(book_id))["table_of_contents"]["version"] == 1


@pytest.mark.asyncio
async def test_wrong_owner_not_matched(motor_reinit_db):
    book_id = await _seed(
        toc={"version": 1, "chapters": [{"id": "a", "content": "x"}]}
    )
    matched = await bookdao.apply_chapter_content_update(
        book_id, "a", None, {"content": "y"}, "someone-else"
    )
    assert matched is False
    assert _chapters(await _book(book_id))[0]["content"] == "x"


# --------------------------------------------------------------------------- #
# update_book_summary_atomic
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_summary_archives_current_revision(motor_reinit_db):
    book_id = await _seed(summary="A", summary_history=[])

    updated = await bookdao.update_book_summary_atomic(book_id, "B", OWNER)
    assert updated["summary"] == "B"
    # The document's current summary ("A") is archived at write time.
    assert [h["summary"] for h in updated["summary_history"]] == ["A"]


@pytest.mark.asyncio
async def test_summary_no_history_when_unchanged_or_empty(motor_reinit_db):
    book_id = await _seed(summary="", summary_history=[])
    # First save: current summary is empty -> nothing archived.
    updated = await bookdao.update_book_summary_atomic(book_id, "A", OWNER)
    assert updated["summary"] == "A"
    assert updated.get("summary_history", []) == []

    # Re-saving the same value archives nothing (unchanged).
    updated = await bookdao.update_book_summary_atomic(book_id, "A", OWNER)
    assert updated.get("summary_history", []) == []


@pytest.mark.asyncio
async def test_interleaved_summary_writers_keep_both_revisions(motor_reinit_db):
    """Concurrent edits (A->B, A->C) must not lose an archived revision.

    The pipeline archives the document's *current* summary at write time, so the
    write that commits second sees the first's committed value and archives it —
    unlike the old read-modify-write, which could push a stale value and drop the
    intermediate revision entirely.
    """
    book_id = await _seed(summary="A", summary_history=[])

    await asyncio.gather(
        bookdao.update_book_summary_atomic(book_id, "B", OWNER),
        bookdao.update_book_summary_atomic(book_id, "C", OWNER),
    )

    book = await _book(book_id)
    history = [h["summary"] for h in book["summary_history"]]
    # Two writers -> two archived revisions; the seed "A" is always one of them,
    # and no revision was lost to a clobber.
    assert len(history) == 2
    assert "A" in history
    assert book["summary"] in {"B", "C"}


@pytest.mark.asyncio
async def test_summary_with_leading_dollar_is_literal(motor_reinit_db):
    """A summary starting with '$' must be stored verbatim, not interpreted as a
    MongoDB field path inside the aggregation-pipeline update."""
    book_id = await _seed(summary="A", summary_history=[])
    dollar = "$summary is worth $100 — a literal string, not a field path."

    updated = await bookdao.update_book_summary_atomic(book_id, dollar, OWNER)
    assert updated["summary"] == dollar
    assert [h["summary"] for h in updated["summary_history"]] == ["A"]

    # And the prior "$"-summary is archived verbatim on the next change.
    updated = await bookdao.update_book_summary_atomic(book_id, "plain again", OWNER)
    assert dollar in [h["summary"] for h in updated["summary_history"]]


@pytest.mark.asyncio
async def test_summary_history_capped_at_20(motor_reinit_db):
    book_id = await _seed(
        summary="s20",
        summary_history=[{"summary": f"h{i}"} for i in range(20)],
    )
    updated = await bookdao.update_book_summary_atomic(book_id, "s21", OWNER)
    assert len(updated["summary_history"]) == 20  # $slice: -20 dropped the oldest
    assert updated["summary_history"][-1]["summary"] == "s20"
    assert all(h["summary"] != "h0" for h in updated["summary_history"])
