"""Tests for atomic / safely-ordered cascade book deletion (Plan 008).

The live delete path is ``app.db.book.delete_book``. It removes a book plus its
chapter access logs, questions, question responses and question ratings, then
pulls the book from the owner's ``book_ids``. Deletes run inside a MongoDB
transaction when a replica set is available; otherwise children are deleted
first and the book document last so a partial failure leaves the book
discoverable rather than orphaned.

A developer's Mongo is usually standalone, so most of these exercise the
non-transactional path, and the failure test asserts *containment* (book
survives, error logged). The transaction branch is the one Atlas runs, and
the tests at the end are for it: they need a replica set, which CI's
"Backend Tests (replica set)" job provides (#839). On a standalone server they
are skipped, unless ``REQUIRE_REPLICA_SET`` is set, in which case they fail.

Account deletion (``delete_all_user_books``) runs the same cascade once for the
whole account, never in a transaction: one command per collection however many
books there are (#786).
"""

import os
from collections import Counter

from pymongo import AsyncMongoClient
import pytest
import pytest_asyncio
from bson.objectid import ObjectId
from pymongo import monitoring

import app.db.audit_log as audit_log_dao
import app.db.book as book_dao
from app.db import base
from app.db.book import delete_book, delete_all_user_books
from app.db.base import get_collection
from tests.conftest import TEST_MONGO_URI


async def _seed_account(owner_id: str, book_count: int) -> list[str]:
    """Create ``book_count`` books owned by ``owner_id``, each with a question
    (+response, +rating) and a chapter access log, plus the user association.
    Returns the book ids."""
    books = await get_collection("books")
    users = await get_collection("users")
    questions = await get_collection("questions")
    responses = await get_collection("question_responses")
    ratings = await get_collection("question_ratings")
    access_logs = await get_collection("chapter_access_logs")

    book_ids = [str(_id) for _id in (await books.insert_many(
        [{"title": "Doomed", "owner_id": owner_id} for _ in range(book_count)]
    )).inserted_ids]

    await users.insert_one({"auth_id": owner_id, "book_ids": book_ids})

    question_ids = [str(_id) for _id in (await questions.insert_many(
        [{"book_id": b, "user_id": owner_id, "text": "Q?"} for b in book_ids]
    )).inserted_ids]
    await responses.insert_many(
        [{"question_id": q, "user_id": owner_id, "answer": "A"} for q in question_ids]
    )
    await ratings.insert_many([{"question_id": q, "rating": 5} for q in question_ids])
    await access_logs.insert_many(
        [{"book_id": b, "user_id": owner_id} for b in book_ids]
    )

    return book_ids


async def _seed_book_with_children(owner_id: str) -> str:
    return (await _seed_account(owner_id, 1))[0]


class _FailingDeleteMany:
    """Proxies a real collection but raises on ``delete_many``."""

    def __init__(self, wrapped):
        self._wrapped = wrapped

    def __getattr__(self, name):
        return getattr(self._wrapped, name)

    async def delete_many(self, *args, **kwargs):
        raise RuntimeError("simulated mongo failure")


def _fail_response_deletes(monkeypatch):
    real_get_collection = book_dao.get_collection

    async def fake_get_collection(name):
        coll = await real_get_collection(name)
        if name == "question_responses":
            return _FailingDeleteMany(coll)
        return coll

    monkeypatch.setattr(book_dao, "get_collection", fake_get_collection)


class _CommandLog(monitoring.CommandListener):
    """Counts every command sent to Mongo as ``(command, collection)``."""

    def __init__(self):
        self.commands = Counter()

    def started(self, event):
        # A getMore's own value is a cursor id; its collection is a separate key.
        collection = event.command.get("collection") or event.command.get(
            event.command_name
        )
        self.commands[(event.command_name, collection)] += 1

    def succeeded(self, event):
        pass

    def failed(self, event):
        pass


@pytest_asyncio.fixture
async def command_log(reinit_db, monkeypatch):
    """Rebind the DAOs to a client that logs its commands. Listeners can only be
    attached when a client is built."""
    log = _CommandLog()
    client = AsyncMongoClient(
        TEST_MONGO_URI, event_listeners=[log]
    )
    db = client.get_default_database()
    monkeypatch.setattr(base, "_db", db)
    monkeypatch.setattr(book_dao, "_client", client)
    monkeypatch.setattr(book_dao, "books_collection", db.get_collection("books"))
    monkeypatch.setattr(book_dao, "users_collection", db.get_collection("users"))
    monkeypatch.setattr(
        audit_log_dao, "audit_logs_collection", db.get_collection("audit_logs")
    )
    yield log
    await client.close()


@pytest.mark.asyncio
async def test_delete_book_removes_all_related_data(reinit_db):
    """Happy path: book and every child collection are emptied, user updated."""
    owner = "owner-1"
    book_id = await _seed_book_with_children(owner)

    assert await delete_book(book_id, owner) is True

    books = await get_collection("books")
    users = await get_collection("users")
    questions = await get_collection("questions")
    responses = await get_collection("question_responses")
    ratings = await get_collection("question_ratings")
    access_logs = await get_collection("chapter_access_logs")

    assert await books.find_one({"_id": ObjectId(book_id)}) is None
    assert await questions.count_documents({"book_id": book_id}) == 0
    assert await responses.count_documents({"user_id": owner}) == 0
    assert await ratings.count_documents({}) == 0
    assert await access_logs.count_documents({"book_id": book_id}) == 0

    user = await users.find_one({"auth_id": owner})
    assert book_id not in user["book_ids"]


@pytest.mark.asyncio
async def test_delete_book_not_owned_removes_nothing(reinit_db):
    """A non-owner gets False and nothing is deleted."""
    owner = "owner-2"
    book_id = await _seed_book_with_children(owner)

    assert await delete_book(book_id, "someone-else") is False

    books = await get_collection("books")
    questions = await get_collection("questions")
    assert await books.find_one({"_id": ObjectId(book_id)}) is not None
    assert await questions.count_documents({"book_id": book_id}) == 1


@pytest.mark.asyncio
async def test_delete_all_user_books_only_touches_owner(reinit_db):
    """delete_all_user_books cascades every owned book (returning the count)
    and leaves other users' data alone (issue #179)."""
    await _seed_book_with_children("victim")
    await _seed_book_with_children("victim")
    kept = await _seed_book_with_children("bystander")

    assert await delete_all_user_books("victim") == 2
    assert await delete_all_user_books("victim") == 0  # idempotent second pass

    books = await get_collection("books")
    questions = await get_collection("questions")
    assert await books.count_documents({"owner_id": "victim"}) == 0
    assert await questions.count_documents({"user_id": "victim"}) == 0
    assert await books.find_one({"_id": ObjectId(kept)}) is not None
    assert await questions.count_documents({"book_id": kept}) == 1


@pytest.mark.asyncio
async def test_delete_all_user_books_failure_leaves_every_book(
    reinit_db, monkeypatch
):
    """A failed child delete propagates, so the account-deletion caller aborts
    before touching the user record, and every book document survives it
    (children first, parents last) for the retry."""
    await _seed_account("victim-2", 3)
    _fail_response_deletes(monkeypatch)

    with pytest.raises(RuntimeError, match="simulated mongo failure"):
        await delete_all_user_books("victim-2")

    books = await get_collection("books")
    assert await books.count_documents({"owner_id": "victim-2"}) == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("book_count", [3, 250])
async def test_delete_all_user_books_commands_do_not_grow_with_books(
    command_log, book_count
):
    """One command per collection whatever the size of the account (#786): the
    per-book loop cost about ten round trips a book and timed out at 2,649."""
    await _seed_account("victim", book_count)
    kept = await _seed_book_with_children("bystander")
    command_log.commands.clear()

    assert await delete_all_user_books("victim") == book_count

    commands = dict(command_log.commands)
    # Reading 250 ids back takes a second batch; a batch holds thousands.
    assert sum(
        commands.pop(key) for key in list(commands) if key[0] == "getMore"
    ) <= 2
    assert commands == {
        ("find", "books"): 1,
        ("delete", "chapter_access_logs"): 1,
        ("find", "questions"): 1,
        ("delete", "question_responses"): 1,
        ("delete", "question_ratings"): 1,
        ("delete", "questions"): 1,
        ("delete", "books"): 1,
        ("update", "users"): 1,
        ("insert", "audit_logs"): 1,
    }

    books = await get_collection("books")
    users = await get_collection("users")
    assert await books.count_documents({"owner_id": "victim"}) == 0
    assert (await users.find_one({"auth_id": "victim"}))["book_ids"] == []
    for name in ("questions", "question_responses", "chapter_access_logs"):
        collection = await get_collection(name)
        assert await collection.count_documents({"user_id": "victim"}) == 0
        assert await collection.count_documents({"user_id": "bystander"}) == 1
    ratings = await get_collection("question_ratings")
    assert await ratings.count_documents({}) == 1
    assert await books.find_one({"_id": ObjectId(kept)}) is not None


@pytest.mark.asyncio
async def test_delete_all_user_books_chunks_question_ids(command_log, monkeypatch):
    """Responses and ratings are keyed by question id alone, and one ``$in`` is
    capped at 16MB, so the ids go in chunks."""
    monkeypatch.setattr(book_dao, "_QUESTION_ID_CHUNK", 2)
    await _seed_account("victim", 5)
    command_log.commands.clear()

    assert await delete_all_user_books("victim") == 5

    assert command_log.commands[("delete", "question_responses")] == 3
    assert command_log.commands[("delete", "question_ratings")] == 3
    for name in ("question_responses", "question_ratings"):
        assert await (await get_collection(name)).count_documents({}) == 0


@pytest.mark.asyncio
async def test_delete_all_user_books_writes_one_audit_row(reinit_db):
    """One summary row for the account, carrying counts and no book titles."""
    await _seed_account("victim", 2)

    assert await delete_all_user_books("victim") == 2

    rows = await base.audit_logs_collection.find({}, {"_id": 0}).to_list(None)
    assert [(row["action"], row["actor_id"], row["details"]) for row in rows] == [
        (
            "delete_books",
            "victim",
            {
                "deleted_count": 2,
                "cascade_deleted": {
                    "chapter_access_logs": 2,
                    "questions": 2,
                    "question_responses": 2,
                    "question_ratings": 2,
                },
            },
        )
    ]


@pytest.mark.asyncio
async def test_delete_book_failure_is_contained_and_logged(
    reinit_db, monkeypatch, caplog
):
    """A mid-cascade failure (non-transactional path) leaves the book document
    intact (children-first ordering) and logs the error; the exception
    propagates so the endpoint can map it to a 500."""
    owner = "owner-3"
    book_id = await _seed_book_with_children(owner)

    _fail_response_deletes(monkeypatch)

    with pytest.raises(RuntimeError, match="simulated mongo failure"):
        await delete_book(book_id, owner)

    # Book document deleted last -> survives the partial failure.
    books = await get_collection("books")
    assert await books.find_one({"_id": ObjectId(book_id)}) is not None

    assert any(
        "Cascade delete failed" in r.message for r in caplog.records
    ), "expected an error log for the failed cascade"


def test_the_cascade_uses_the_test_runs_own_client(reinit_db):
    """``book.py`` binds ``_client`` when it is imported. Left at that, it is a
    client from another event loop: the replica-set probe raises on it, the
    error is swallowed, and the cascade quietly takes the path without a
    transaction, on a replica set too (#839)."""
    assert book_dao._client is base._client


@pytest.fixture
async def replica_set(reinit_db):
    """Skip on a standalone server. A run that says it has a replica set and has not is a failure."""
    if (await base._client.admin.command("hello")).get("setName") is None:
        if os.environ.get("REQUIRE_REPLICA_SET"):
            pytest.fail("REQUIRE_REPLICA_SET is set, and the test database is not a replica set")
        pytest.skip("needs a replica set: transactions do not exist on a standalone server")


@pytest.fixture
def cascade_sessions(monkeypatch):
    """What ``delete_book`` hands the cascade as its session, and whether a transaction was open then."""
    seen = []
    real = book_dao._delete_books_internal

    async def watched(book_ids, user_auth_id, session):
        seen.append((session, session is not None and session.in_transaction))
        return await real(book_ids, user_auth_id, session)

    monkeypatch.setattr(book_dao, "_delete_books_internal", watched)
    return seen


@pytest.mark.asyncio
async def test_on_a_replica_set_the_cascade_runs_in_a_transaction(replica_set, cascade_sessions):
    owner = "owner-rs-1"
    book_id = await _seed_book_with_children(owner)

    assert await delete_book(book_id, owner) is True

    [(session, in_transaction)] = cascade_sessions
    assert session is not None
    assert in_transaction is True
    for name in ("books", "questions", "question_responses", "question_ratings", "chapter_access_logs"):
        assert await (await get_collection(name)).count_documents({}) == 0, name


@pytest.mark.asyncio
async def test_on_a_replica_set_a_failure_puts_back_what_was_already_deleted(
    replica_set, cascade_sessions, monkeypatch
):
    """The access logs are deleted before the step that fails. Without a
    transaction they stay deleted; with one, the failure undoes them."""
    owner = "owner-rs-2"
    book_id = await _seed_book_with_children(owner)
    _fail_response_deletes(monkeypatch)

    with pytest.raises(RuntimeError, match="simulated mongo failure"):
        await delete_book(book_id, owner)

    assert [session is not None for session, _ in cascade_sessions] == [True]
    for name in ("books", "questions", "question_responses", "question_ratings", "chapter_access_logs"):
        assert await (await get_collection(name)).count_documents({}) == 1, name
