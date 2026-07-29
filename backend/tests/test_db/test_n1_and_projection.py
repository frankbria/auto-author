"""Real-Mongo tests for the #214 perf cleanups.

Two independent changes folded into the dead-code removal:

* N+1 elimination in ``questions.py`` — ``get_questions`` /
  ``get_ratings_for_chapter`` / ``get_chapter_question_progress`` used to issue
  one ``find_one`` per question; they now do a single ``$in`` batched lookup.
  Correctness tests pin the join result; a ``find_one``-must-not-be-called guard
  pins the batching itself (a revert to the per-question loop fails it).
* ``get_books_by_user`` now projects out the heavy per-chapter ``content`` HTML
  from ``table_of_contents`` (the dashboard list never uses it).
"""

import pytest
from unittest.mock import patch
from bson import ObjectId
import motor.motor_asyncio

from app.db.base import get_collection
from app.db.questions import (
    get_questions_for_chapter,
    get_ratings_for_chapter,
    get_chapter_question_progress,
)
from app.db.book import (
    get_books_by_user,
    get_book_owner_id,
    get_book_metadata_by_id,
)

pytestmark = pytest.mark.asyncio

BOOK = "book-1"
CH = "ch-1"
USER = "user-1"


async def _seed_question(order: int) -> str:
    qid = ObjectId()
    coll = await get_collection("questions")
    await coll.insert_one({
        "_id": qid,
        "book_id": BOOK,
        "chapter_id": CH,
        "user_id": USER,
        "question_text": f"Question number {order} for the chapter?",
        "question_type": "plot",
        "difficulty": "easy",
        "category": "general",
        "order": order,
        "metadata": {"suggested_response_length": "short"},
    })
    return str(qid)


async def _seed_response(question_id: str, status: str = "completed") -> None:
    coll = await get_collection("question_responses")
    await coll.insert_one({
        "question_id": question_id,
        "user_id": USER,
        "response_text": "an answer",
        "status": status,
    })


async def _seed_rating(question_id: str, rating: int) -> None:
    coll = await get_collection("question_ratings")
    await coll.insert_one({
        "question_id": question_id,
        "user_id": USER,
        "rating": rating,
        "feedback": f"fb-{rating}",
    })


# --- N+1: correctness of the batched join ---------------------------------

async def test_get_questions_attaches_correct_response_status(motor_reinit_db):
    q1 = await _seed_question(1)
    q2 = await _seed_question(2)
    await _seed_question(3)  # unanswered
    await _seed_response(q1, status="completed")
    await _seed_response(q2, status="draft")

    result = await get_questions_for_chapter(BOOK, CH, USER)
    by_id = {q.id: q for q in result.questions}

    assert by_id[q1].response_status == "completed" and by_id[q1].has_response is True
    assert by_id[q2].response_status == "draft"
    unanswered = [q for q in result.questions if not q.has_response]
    assert len(unanswered) == 1 and unanswered[0].response_status == "not_answered"


async def test_get_ratings_for_chapter_batched_join(motor_reinit_db):
    q1 = await _seed_question(1)
    q2 = await _seed_question(2)
    await _seed_question(3)  # no rating
    await _seed_rating(q1, 5)
    await _seed_rating(q2, 2)

    results = await get_ratings_for_chapter(BOOK, CH, USER)

    assert len(results) == 2
    by_text = {r["question_text"]: r for r in results}
    q1_text = "Question number 1 for the chapter?"
    q2_text = "Question number 2 for the chapter?"
    assert by_text[q1_text]["rating"] == 5 and by_text[q1_text]["feedback"] == "fb-5"
    assert by_text[q2_text]["rating"] == 2


async def test_get_chapter_question_progress_counts(motor_reinit_db):
    q1 = await _seed_question(1)
    q2 = await _seed_question(2)
    await _seed_question(3)  # not started
    await _seed_response(q1, status="completed")
    await _seed_response(q2, status="draft")

    progress = await get_chapter_question_progress(BOOK, CH, USER)

    assert progress.total == 3
    assert progress.completed == 1
    assert progress.in_progress == 1
    assert progress.status == "in-progress"


# --- N+1: the batching itself (find_one must not be called per-question) ---

async def test_progress_does_not_issue_per_question_find_one(motor_reinit_db):
    """The old loop called find_one once per question; the batched version calls
    only find(). Raising on any find_one turns a reverted N+1 loop RED."""
    for i in range(1, 4):
        qid = await _seed_question(i)
        await _seed_response(qid, status="completed")

    with patch.object(
        motor.motor_asyncio.AsyncIOMotorCollection,
        "find_one",
        side_effect=AssertionError("N+1 regression: find_one called per question"),
    ):
        progress = await get_chapter_question_progress(BOOK, CH, USER)

    assert progress.total == 3 and progress.completed == 3


# --- projection: heavy chapter content excluded from the list --------------

async def test_get_books_by_user_projects_out_chapter_content(motor_reinit_db):
    books = await get_collection("books")
    await books.insert_one({
        "owner_id": USER,
        "title": "My Book",
        "toc_items": [{"id": "c1", "title": "Chapter One", "order": 1, "level": 1}],
        "table_of_contents": {
            "version": 1,
            "chapters": [
                {
                    "id": "c1",
                    "title": "Chapter One",
                    "content": "<p>" + "x" * 5000 + "</p>",
                    "subchapters": [
                        {"id": "c1a", "title": "Sub", "content": "<p>" + "y" * 5000 + "</p>"}
                    ],
                }
            ],
        },
    })

    result = await get_books_by_user(USER)

    assert len(result) == 1
    book = result[0]
    chapter = book["table_of_contents"]["chapters"][0]
    # Heavy HTML gone...
    assert "content" not in chapter
    assert "content" not in chapter["subchapters"][0]
    # ...structure/titles/toc_items intact.
    assert chapter["title"] == "Chapter One"
    assert chapter["subchapters"][0]["title"] == "Sub"
    assert book["toc_items"][0]["title"] == "Chapter One"
    assert book["title"] == "My Book"


# --- #344: ownership checks must not drag chapter HTML over the wire --------


async def _seed_book_with_heavy_chapters() -> ObjectId:
    """A book whose chapter bodies dwarf its metadata, so overfetch is visible."""
    books = await get_collection("books")
    book_id = ObjectId()
    await books.insert_one({
        "_id": book_id,
        "owner_id": USER,
        "title": "Heavy Book",
        "summary": "A summary.",
        "genre": "nonfiction",
        "target_audience": "engineers",
        "toc_items": [{"id": "c1", "title": "Chapter One", "order": 1, "level": 1}],
        "table_of_contents": {
            "version": 1,
            "chapters": [
                {
                    "id": "c1",
                    "title": "Chapter One",
                    "status": "in-progress",
                    "content": "<p>" + "x" * 20000 + "</p>",
                    "subchapters": [
                        {
                            "id": "c1a",
                            "title": "Sub",
                            "status": "draft",
                            "content": "<p>" + "y" * 20000 + "</p>",
                        }
                    ],
                }
            ],
        },
    })
    return book_id


async def test_get_book_owner_id_returns_only_the_owner(motor_reinit_db):
    book_id = await _seed_book_with_heavy_chapters()

    owner = await get_book_owner_id(str(book_id))

    assert owner == USER


async def test_get_book_owner_id_fetches_nothing_but_the_owner(motor_reinit_db):
    """Pins the projection itself: dropping it makes this fail.

    Asserting on the return value alone would still pass if the projection were
    removed, since the caller only reads owner_id either way. So capture what
    Mongo actually sent back.
    """
    book_id = await _seed_book_with_heavy_chapters()

    captured = {}
    real_find_one = motor.motor_asyncio.AsyncIOMotorCollection.find_one

    async def spy(self, filter=None, *args, **kwargs):
        doc = await real_find_one(self, filter, *args, **kwargs)
        captured["doc"] = doc
        return doc

    with patch.object(motor.motor_asyncio.AsyncIOMotorCollection, "find_one", spy):
        await get_book_owner_id(str(book_id))

    doc = captured["doc"]
    # _id always comes back unless explicitly suppressed; nothing else may.
    assert set(doc.keys()) <= {"_id", "owner_id"}
    assert "table_of_contents" not in doc
    assert "title" not in doc


async def test_get_book_owner_id_returns_none_for_missing_and_malformed_ids(motor_reinit_db):
    assert await get_book_owner_id(str(ObjectId())) is None
    # A non-ObjectId string must not raise — callers turn None into a 404.
    assert await get_book_owner_id("not-an-object-id") is None


async def test_get_book_metadata_by_id_excludes_chapter_html(motor_reinit_db):
    book_id = await _seed_book_with_heavy_chapters()

    book = await get_book_metadata_by_id(str(book_id))

    chapter = book["table_of_contents"]["chapters"][0]
    # Heavy HTML gone, at both levels...
    assert "content" not in chapter
    assert "content" not in chapter["subchapters"][0]
    # ...but everything the callers actually read survives. The autosave path
    # needs ids, nesting and status to locate the chapter and compute its
    # status transition; analyze-summary/generate-questions need the top-level
    # metadata.
    assert chapter["id"] == "c1"
    assert chapter["status"] == "in-progress"
    assert chapter["subchapters"][0]["id"] == "c1a"
    assert chapter["subchapters"][0]["status"] == "draft"
    assert book["owner_id"] == USER
    assert book["title"] == "Heavy Book"
    assert book["summary"] == "A summary."
    assert book["genre"] == "nonfiction"
    assert book["target_audience"] == "engineers"


async def test_get_book_metadata_by_id_returns_none_for_missing_and_malformed_ids(motor_reinit_db):
    assert await get_book_metadata_by_id(str(ObjectId())) is None
    assert await get_book_metadata_by_id("not-an-object-id") is None
