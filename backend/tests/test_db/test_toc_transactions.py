"""
Integration tests for app/db/toc_transactions.py.

Exercises the atomic TOC helpers against a real local MongoDB (via the
motor_reinit_db fixture) — happy paths AND the data-integrity failure paths:
invalid IDs, missing/unauthorized books, optimistic-locking version conflicts,
and missing chapters.

The `if use_transaction:` branches these tests used to note as uncoverable are
gone (#369). They needed a replica-set fixture because a standalone server
reports no setName — but the branch they guarded was also the bug: inside a
transaction the guarded update reads at the transaction snapshot, so the version
filter always matched, the ValueError never raised, and a genuine conflict
surfaced at commit as a WriteConflict → generic OperationFailure → 500 instead
of the intended 409.

Every one of these helpers is a single-document compare-and-swap, so the CAS is
atomic without a transaction and behaves identically on standalone and replica
set. Deleting the branch was the fix; there is no longer a topology-dependent
path to cover, which is why the note is retired rather than satisfied.
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


# ---------------------------------------------------------------------------
# update_chapter_statuses_with_version_guard  (issue #159)
# ---------------------------------------------------------------------------


def _toc(version=1, chapters=None):
    return {"version": version, "status": "generated", "chapters": chapters or []}


@pytest.mark.asyncio
async def test_bulk_status_helper_happy_increments_version(seed_book):
    toc = _toc(version=3, chapters=[
        {"id": "c1", "title": "C1", "status": "draft"},
        {"id": "c2", "title": "C2", "status": "draft"},
    ])
    book_id, owner = await seed_book(toc=toc)

    result = await tx.update_chapter_statuses_with_version_guard(
        book_id=book_id,
        chapter_ids=["c1"],
        new_status="in-progress",
        user_auth_id=owner,
        expected_version=3,
    )

    assert result["updated_chapters"] == ["c1"]
    stored = await _get_toc(book_id)
    assert stored["version"] == 4
    statuses = {c["id"]: c["status"] for c in stored["chapters"]}
    assert statuses == {"c1": "in-progress", "c2": "draft"}

    # The book-level audit entry the previous update_book() path emitted is preserved.
    audit = await tx._db.get_collection("audit_logs").find_one(
        {"target_id": book_id, "action": "book_update"}
    )
    assert audit is not None
    assert "table_of_contents" in audit["details"]["updated_fields"]


@pytest.mark.asyncio
async def test_bulk_status_helper_versionless_toc_no_false_conflict(seed_book):
    """A legacy TOC with no `version` field must not produce a false conflict."""
    toc = {"chapters": [{"id": "c1", "title": "C1", "status": "draft"}]}  # no version
    book_id, owner = await seed_book(toc=toc)

    result = await tx.update_chapter_statuses_with_version_guard(
        book_id=book_id, chapter_ids=["c1"], new_status="in-progress",
        user_auth_id=owner, expected_version=1,
    )

    assert result["updated_chapters"] == ["c1"]
    stored = await _get_toc(book_id)
    assert stored["version"] == 2
    assert stored["chapters"][0]["status"] == "in-progress"


@pytest.mark.asyncio
async def test_bulk_status_helper_stale_version_conflicts(seed_book):
    """A stale expected_version must NOT overwrite — this is the lost-update fix."""
    toc = _toc(version=5, chapters=[{"id": "c1", "title": "C1", "status": "draft"}])
    book_id, owner = await seed_book(toc=toc)

    with pytest.raises(ValueError, match="Version conflict"):
        await tx.update_chapter_statuses_with_version_guard(
            book_id=book_id,
            chapter_ids=["c1"],
            new_status="in-progress",
            user_auth_id=owner,
            expected_version=4,  # stale
        )

    # Nothing was written.
    stored = await _get_toc(book_id)
    assert stored["version"] == 5
    assert stored["chapters"][0]["status"] == "draft"


@pytest.mark.asyncio
async def test_bulk_status_helper_updates_nested_subchapter(seed_book):
    toc = _toc(version=1, chapters=[
        {"id": "p1", "title": "P", "status": "draft", "subchapters": [
            {"id": "s1", "title": "S", "status": "draft"},
        ]},
    ])
    book_id, owner = await seed_book(toc=toc)

    result = await tx.update_chapter_statuses_with_version_guard(
        book_id=book_id, chapter_ids=["s1"], new_status="in-progress",
        user_auth_id=owner, expected_version=1,
    )

    assert result["updated_chapters"] == ["s1"]
    stored = await _get_toc(book_id)
    assert stored["chapters"][0]["subchapters"][0]["status"] == "in-progress"


@pytest.mark.asyncio
async def test_bulk_status_helper_no_matching_chapters(seed_book):
    toc = _toc(version=1, chapters=[{"id": "c1", "title": "C1", "status": "draft"}])
    book_id, owner = await seed_book(toc=toc)

    with pytest.raises(ValueError, match="No matching chapters found"):
        await tx.update_chapter_statuses_with_version_guard(
            book_id=book_id, chapter_ids=["nope"], new_status="in-progress",
            user_auth_id=owner, expected_version=1,
        )


@pytest.mark.asyncio
async def test_bulk_status_helper_timestamp_sets_last_modified(seed_book):
    toc = _toc(version=1, chapters=[{"id": "c1", "title": "C1", "status": "draft"}])
    book_id, owner = await seed_book(toc=toc)

    await tx.update_chapter_statuses_with_version_guard(
        book_id=book_id, chapter_ids=["c1"], new_status="in-progress",
        user_auth_id=owner, expected_version=1, update_timestamp=True,
    )

    stored = await _get_toc(book_id)
    assert stored["chapters"][0].get("last_modified") is not None


@pytest.mark.asyncio
async def test_bulk_status_helper_book_not_found(motor_reinit_db):
    with pytest.raises(ValueError, match="Book not found"):
        await tx.update_chapter_statuses_with_version_guard(
            book_id=str(ObjectId()), chapter_ids=["c1"], new_status="in-progress",
            user_auth_id="someone", expected_version=1,
        )


@pytest.mark.asyncio
async def test_bulk_status_helper_wrong_owner_not_authorized(seed_book):
    toc = _toc(version=1, chapters=[{"id": "c1", "title": "C1", "status": "draft"}])
    book_id, _ = await seed_book(toc=toc, owner_id="real-owner")

    with pytest.raises(ValueError, match=r"[Nn]ot authorized"):
        await tx.update_chapter_statuses_with_version_guard(
            book_id=book_id, chapter_ids=["c1"], new_status="in-progress",
            user_auth_id="intruder", expected_version=1,
        )


# ---------------------------------------------------------------------------
# Interleaved-writer / lost-update guard  (issue #337)
#
# add/update/delete/reorder each read the whole TOC, mutate it in memory, and
# $set it back. Without a version guard on the write filter that is plain
# last-write-wins on standalone Mongo (session=None), so a concurrent autosave
# is silently clobbered. These tests fire a competing write in the window
# between the read and the write and assert the second writer LOSES loudly
# rather than overwriting.
# ---------------------------------------------------------------------------


def _interleave_competing_write(monkeypatch, book_id, competing_toc):
    """Run a competing whole-TOC write in the read -> write window.

    Wraps ``books_collection.find_one`` so that the first call (the operation's
    own read) is followed immediately by another writer committing
    ``competing_toc``. The operation under test then attempts its write against
    a TOC whose version has already moved on.
    """
    real_find_one = tx.books_collection.find_one
    state = {"fired": False}

    async def find_one_then_interleave(*args, **kwargs):
        doc = await real_find_one(*args, **kwargs)
        if not state["fired"]:
            state["fired"] = True
            await tx.books_collection.update_one(
                {"_id": ObjectId(book_id)},
                {"$set": {"table_of_contents": competing_toc}},
            )
        return doc

    monkeypatch.setattr(tx.books_collection, "find_one", find_one_then_interleave)
    return state


_INTERLEAVED_OPS = [
    lambda bid, owner: tx.add_chapter_with_transaction(bid, {"title": "New"}, owner),
    lambda bid, owner: tx.update_chapter_with_transaction(
        bid, "c1", {"title": "Renamed"}, owner
    ),
    lambda bid, owner: tx.delete_chapter_with_transaction(bid, "c1", owner),
    lambda bid, owner: tx.reorder_chapters_with_transaction(
        bid, [{"id": "c1", "order": 1}], owner
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "call", _INTERLEAVED_OPS, ids=["add", "update", "delete", "reorder"]
)
async def test_interleaved_writer_does_not_lose_update(seed_book, monkeypatch, call):
    """A concurrent TOC write must not be clobbered — it must raise instead."""
    book_id, owner = await seed_book(
        toc=_toc(version=1, chapters=[{"id": "c1", "title": "Original"}])
    )

    # The other writer (e.g. the autosave path) commits first and bumps to v2.
    competing = _toc(
        version=2, chapters=[{"id": "c1", "title": "Original", "content": "autosaved"}]
    )
    state = _interleave_competing_write(monkeypatch, book_id, competing)

    with pytest.raises(ValueError, match="Version conflict"):
        await call(book_id, owner)

    assert state["fired"], "competing write never ran — test is not interleaving"

    # The competing writer's data survived completely intact.
    stored = await tx.books_collection.find_one({"_id": ObjectId(book_id)})
    assert stored["table_of_contents"] == competing


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "call", _INTERLEAVED_OPS, ids=["add", "update", "delete", "reorder"]
)
async def test_versionless_toc_no_false_conflict(seed_book, call):
    """A legacy TOC with no `version` field must still write on first attempt."""
    book_id, owner = await seed_book(
        toc={"chapters": [{"id": "c1", "title": "Original"}]}  # no version field
    )

    await call(book_id, owner)  # must not raise

    stored = await _get_toc(book_id)
    assert stored["version"] == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "call", _INTERLEAVED_OPS, ids=["add", "update", "delete", "reorder"]
)
async def test_guarded_write_scoped_to_owner(seed_book, monkeypatch, call):
    """The write filter is owner-scoped, not just _id-scoped.

    A filter miss caused by an ownership change must report *not authorized*,
    not a misleading "someone else edited the TOC" conflict.
    """
    book_id, owner = await seed_book(
        toc=_toc(version=1, chapters=[{"id": "c1", "title": "Original"}])
    )

    # Ownership changes between the read and the write.
    real_find_one = tx.books_collection.find_one
    state = {"fired": False}

    async def find_one_then_reassign(*args, **kwargs):
        doc = await real_find_one(*args, **kwargs)
        if not state["fired"]:
            state["fired"] = True
            await tx.books_collection.update_one(
                {"_id": ObjectId(book_id)}, {"$set": {"owner_id": "someone-else"}}
            )
        return doc

    monkeypatch.setattr(tx.books_collection, "find_one", find_one_then_reassign)

    with pytest.raises(ValueError, match=r"[Nn]ot authorized"):
        await call(book_id, owner)

    stored = await _get_toc(book_id)
    assert stored["version"] == 1  # untouched


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "call", _INTERLEAVED_OPS, ids=["add", "update", "delete", "reorder"]
)
async def test_book_deleted_mid_operation_reports_not_found(
    seed_book, monkeypatch, call
):
    """A book deleted in the read -> write window is 'not found', not a conflict."""
    book_id, owner = await seed_book(
        toc=_toc(version=1, chapters=[{"id": "c1", "title": "Original"}])
    )

    real_find_one = tx.books_collection.find_one
    state = {"fired": False}

    async def find_one_then_delete(*args, **kwargs):
        doc = await real_find_one(*args, **kwargs)
        if not state["fired"]:
            state["fired"] = True
            await tx.books_collection.delete_one({"_id": ObjectId(book_id)})
        return doc

    monkeypatch.setattr(tx.books_collection, "find_one", find_one_then_delete)

    with pytest.raises(ValueError, match="Book not found"):
        await call(book_id, owner)


@pytest.mark.asyncio
async def test_update_toc_interleaved_writer_does_not_lose_update(
    seed_book, monkeypatch
):
    """update_toc is the fifth helper that lost its transaction wrapper (#369).

    The other four are covered by the parametrised interleave test above; this
    one has a different signature and a different conflict message, so it gets
    its own. Same property: a competing commit in the read -> write window must
    make this write raise rather than clobber.
    """
    book_id, owner = await seed_book(
        toc=_toc(version=1, chapters=[{"id": "c1", "title": "Original"}])
    )

    competing = _toc(
        version=2, chapters=[{"id": "c1", "title": "Original", "content": "autosaved"}]
    )
    state = _interleave_competing_write(monkeypatch, book_id, competing)

    with pytest.raises(ValueError):
        await tx.update_toc_with_transaction(
            book_id, {"chapters": [{"id": "c1", "title": "Mine"}]}, owner
        )

    assert state["fired"], "competing write never ran — test is not interleaving"

    # The competing writer's data survived intact.
    stored = await tx.books_collection.find_one({"_id": ObjectId(book_id)})
    assert stored["table_of_contents"] == competing


@pytest.mark.asyncio
async def test_helpers_do_not_open_transactions(monkeypatch, seed_book):
    """The topology-dependent path is gone, not merely unused (#369).

    Pinning this structurally rather than behaviourally: a transaction would
    reintroduce the 500-instead-of-409 bug only on a replica set, which no
    standalone test can observe. Asserting that no session is ever started
    catches the regression on any topology.
    """
    book_id, owner = await seed_book(
        toc=_toc(version=1, chapters=[{"id": "c1", "title": "Original"}])
    )

    import app.db.base as base

    def _fail_start_session(*a, **kw):
        raise AssertionError(
            "TOC helpers must not open a session: inside a transaction the "
            "guarded update reads at the snapshot, so a concurrent commit "
            "surfaces as a WriteConflict (500) instead of ValueError (409)"
        )

    monkeypatch.setattr(base._client, "start_session", _fail_start_session)

    await tx.add_chapter_with_transaction(book_id, {"title": "New"}, owner)
    await tx.update_chapter_with_transaction(book_id, "c1", {"title": "Edited"}, owner)
    await tx.reorder_chapters_with_transaction(book_id, [{"id": "c1", "order": 1}], owner)
    await tx.delete_chapter_with_transaction(book_id, "c1", owner)
