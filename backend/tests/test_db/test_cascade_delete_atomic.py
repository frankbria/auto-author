"""Tests for atomic / safely-ordered cascade book deletion (Plan 008).

The live delete path is ``app.db.book.delete_book``. It removes a book plus its
chapter access logs, questions, question responses and question ratings, then
pulls the book from the owner's ``book_ids``. Deletes run inside a MongoDB
transaction when a replica set is available; otherwise children are deleted
first and the book document last so a partial failure leaves the book
discoverable rather than orphaned.

Test Mongo is single-node, so these exercise the non-transactional path. The
failure test therefore asserts *containment* (book survives, error logged);
true rollback requires a replica set.
"""

import pytest
from bson.objectid import ObjectId

import app.db.book as book_dao
from app.db.book import delete_book
from app.db.base import get_collection


async def _seed_book_with_children(owner_id: str) -> str:
    """Create a book owned by ``owner_id`` with a question (+response, +rating),
    a chapter access log, and the user association. Returns the book id."""
    books = await get_collection("books")
    users = await get_collection("users")
    questions = await get_collection("questions")
    responses = await get_collection("question_responses")
    ratings = await get_collection("question_ratings")
    access_logs = await get_collection("chapter_access_logs")

    book_id = str((await books.insert_one(
        {"title": "Doomed", "owner_id": owner_id}
    )).inserted_id)

    await users.insert_one({"auth_id": owner_id, "book_ids": [book_id]})

    question_id = str((await questions.insert_one(
        {"book_id": book_id, "user_id": owner_id, "text": "Q?"}
    )).inserted_id)
    await responses.insert_one(
        {"question_id": question_id, "user_id": owner_id, "answer": "A"}
    )
    await ratings.insert_one({"question_id": question_id, "rating": 5})
    await access_logs.insert_one({"book_id": book_id, "user_id": owner_id})

    return book_id


@pytest.mark.asyncio
async def test_delete_book_removes_all_related_data(motor_reinit_db):
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
async def test_delete_book_not_owned_removes_nothing(motor_reinit_db):
    """A non-owner gets False and nothing is deleted."""
    owner = "owner-2"
    book_id = await _seed_book_with_children(owner)

    assert await delete_book(book_id, "someone-else") is False

    books = await get_collection("books")
    questions = await get_collection("questions")
    assert await books.find_one({"_id": ObjectId(book_id)}) is not None
    assert await questions.count_documents({"book_id": book_id}) == 1


@pytest.mark.asyncio
async def test_delete_book_failure_is_contained_and_logged(
    motor_reinit_db, monkeypatch, caplog
):
    """A mid-cascade failure (non-transactional path) leaves the book document
    intact (children-first ordering) and logs the error; the exception
    propagates so the endpoint can map it to a 500."""
    owner = "owner-3"
    book_id = await _seed_book_with_children(owner)

    real_get_collection = book_dao.get_collection

    class _FailingDeleteMany:
        """Proxies a real collection but raises on ``delete_many``."""

        def __init__(self, wrapped):
            self._wrapped = wrapped

        def __getattr__(self, name):
            return getattr(self._wrapped, name)

        async def delete_many(self, *args, **kwargs):
            raise RuntimeError("simulated mongo failure")

    async def fake_get_collection(name):
        coll = await real_get_collection(name)
        if name == "question_responses":
            return _FailingDeleteMany(coll)
        return coll

    monkeypatch.setattr(book_dao, "get_collection", fake_get_collection)

    with pytest.raises(RuntimeError, match="simulated mongo failure"):
        await delete_book(book_id, owner)

    # Book document deleted last -> survives the partial failure.
    books = await get_collection("books")
    assert await books.find_one({"_id": ObjectId(book_id)}) is not None

    assert any(
        "Cascade delete failed" in r.message for r in caplog.records
    ), "expected an error log for the failed cascade"
