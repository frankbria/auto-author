"""Question response and rating saves are single atomic upserts (#762).

Every save used to read, then insert or update. Concurrent first saves all read
"nothing there", all insert, and every loser hits the unique question_user_idx
as a DuplicateKeyError (a 500 at the endpoint). edit_history also grew by one
entry per save with no cap. All tests run on real Mongo.
"""

import asyncio

import pytest

from app.db.base import get_collection
from app.db.questions import (
    EDIT_HISTORY_LIMIT,
    _upsert_one,
    create_question,
    ensure_question_indexes,
    get_question_response,
    save_question_rating,
    save_question_response,
    save_question_responses_batch,
)
from app.schemas.book import (
    QuestionCreate,
    QuestionDifficulty,
    QuestionMetadata,
    QuestionRating,
    QuestionResponseCreate,
    QuestionType,
)

CONCURRENT_SAVES = 20


async def _make_question(user_id, book_id, chapter_id):
    return await create_question(
        QuestionCreate(
            book_id=book_id,
            chapter_id=chapter_id,
            question_text="What is this chapter about?",
            question_type=QuestionType.PLOT,
            difficulty=QuestionDifficulty.MEDIUM,
            category="plot",
            order=0,
            metadata=QuestionMetadata(suggested_response_length="100-200 words"),
        ),
        user_id,
    )


async def _unique_indexes_in_place():
    """Build the indexes and prove the unique ones exist before racing them.

    Without question_user_idx the old code would not raise, it would just store
    duplicates; asserting it here keeps the race tests about the real failure.
    """
    await ensure_question_indexes()
    for name in ("question_responses", "question_ratings"):
        collection = await get_collection(name)
        indexes = await collection.index_information()
        assert indexes.get("question_user_idx", {}).get("unique") is True, name


async def _docs(collection_name, question_id, user_id):
    collection = await get_collection(collection_name)
    return [
        d async for d in collection.find({"question_id": question_id, "user_id": user_id})
    ]


@pytest.mark.asyncio
async def test_concurrent_first_response_saves_over_http_all_succeed(
    auth_client_factory, test_user
):
    """20 parallel first PUTs to /response: all 200, one document."""
    client = await auth_client_factory()
    user_id = test_user["auth_id"]
    book = await client.post("/api/v1/books/", json={"title": "Race Book"})
    assert book.status_code == 201
    book_id = book.json()["id"]
    question = await _make_question(user_id, book_id, "ch-1")
    await _unique_indexes_in_place()

    url = f"/api/v1/books/{book_id}/chapters/ch-1/questions/{question['id']}/response"
    responses = await asyncio.gather(*(
        client.put(url, json={"response_text": f"answer number {i}", "status": "draft"})
        for i in range(CONCURRENT_SAVES)
    ))

    assert [r.status_code for r in responses] == [200] * CONCURRENT_SAVES
    docs = await _docs("question_responses", question["id"], user_id)
    assert len(docs) == 1
    # Every request reports the one document that exists.
    assert {r.json()["response"]["id"] for r in responses} == {str(docs[0]["_id"])}
    assert len(docs[0]["metadata"]["edit_history"]) == CONCURRENT_SAVES


@pytest.mark.asyncio
async def test_concurrent_first_ratings_produce_one_document(motor_reinit_db):
    await _unique_indexes_in_place()
    user_id, question_id = "user-1", "q-1"

    results = await asyncio.gather(*(
        save_question_rating(
            question_id,
            QuestionRating(question_id=question_id, user_id=user_id, rating=1 + i % 5),
            user_id,
        )
        for i in range(CONCURRENT_SAVES)
    ))

    docs = await _docs("question_ratings", question_id, user_id)
    assert len(docs) == 1
    assert {r["id"] for r in results} == {str(docs[0]["_id"])}


@pytest.mark.asyncio
async def test_concurrent_first_batch_saves_produce_one_document(motor_reinit_db):
    user_id, book_id, chapter_id = "user-1", "book-1", "ch-1"
    question = await _make_question(user_id, book_id, chapter_id)
    await _unique_indexes_in_place()

    results = await asyncio.gather(*(
        save_question_responses_batch(
            [{"question_id": question["id"], "response_text": f"batch {i}", "status": "draft"}],
            user_id, book_id=book_id, chapter_id=chapter_id,
        )
        for i in range(CONCURRENT_SAVES)
    ))

    assert all(r["success"] for r in results), [r["errors"] for r in results]
    docs = await _docs("question_responses", question["id"], user_id)
    assert len(docs) == 1
    # Exactly one of the racers created the document; the rest updated it.
    assert sum(not r["results"][0]["is_update"] for r in results) == 1


@pytest.mark.asyncio
async def test_upsert_retries_the_duplicate_key_the_server_does_not(motor_reinit_db):
    """The client-side retry is real, not decoration.

    MongoDB >= 4.2 retries a duplicate-key upsert itself when the filter is pure
    equality on the unique index's fields, which is why the save tests above never
    reach the retry. A non-equality predicate switches that off. Measured locally
    (Mongo 8.0), a 50-way burst like this surfaces ~1.4 DuplicateKeyErrors without
    the retry, so ten bursts make a missing retry fail with near certainty.
    """
    await _unique_indexes_in_place()
    collection = await get_collection("question_responses")
    key = {"question_id": "q-1", "user_id": "user-1", "legacy": {"$exists": False}}

    for _ in range(10):
        await collection.delete_many({})
        results = await asyncio.gather(*(
            _upsert_one(collection, key, {"response_text": f"r{i}"})
            for i in range(50)
        ))

        assert len(await _docs("question_responses", "q-1", "user-1")) == 1
        assert sum(not is_update for _, is_update in results) == 1


@pytest.mark.asyncio
async def test_edit_history_is_capped_at_the_newest_entries(motor_reinit_db):
    """100 saves leave the newest EDIT_HISTORY_LIMIT entries, no more."""
    assert EDIT_HISTORY_LIMIT == 50
    user_id, question_id = "user-1", "q-1"

    for i in range(100):
        await save_question_response(
            question_id,
            QuestionResponseCreate(response_text=" ".join(["word"] * (i + 1))),
            user_id,
        )

    saved = await get_question_response(question_id, user_id)
    history = saved["metadata"]["edit_history"]
    assert len(history) == EDIT_HISTORY_LIMIT
    # One entry per save, carrying that save's word count; oldest dropped first.
    assert [e["word_count"] for e in history] == list(range(51, 101))
    assert saved["word_count"] == 100


@pytest.mark.asyncio
async def test_batch_save_shares_the_edit_history_cap(motor_reinit_db):
    user_id, book_id, chapter_id = "user-1", "book-1", "ch-1"
    question = await _make_question(user_id, book_id, chapter_id)

    for i in range(EDIT_HISTORY_LIMIT + 5):
        await save_question_responses_batch(
            [{"question_id": question["id"], "response_text": f"v{i}", "status": "draft"}],
            user_id, book_id=book_id, chapter_id=chapter_id,
        )

    saved = await get_question_response(question["id"], user_id)
    assert len(saved["metadata"]["edit_history"]) == EDIT_HISTORY_LIMIT


@pytest.mark.asyncio
async def test_rerating_keeps_the_original_created_at(motor_reinit_db):
    user_id, question_id = "user-1", "q-1"
    first = await save_question_rating(
        question_id, QuestionRating(question_id=question_id, user_id=user_id, rating=2), user_id
    )
    second = await save_question_rating(
        question_id,
        QuestionRating(question_id=question_id, user_id=user_id, rating=5, feedback="better"),
        user_id,
    )

    assert second["id"] == first["id"]
    assert second["created_at"] == first["created_at"]
    assert second["rating"] == 5
    assert second["feedback"] == "better"
