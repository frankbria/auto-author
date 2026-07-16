"""Real-Mongo tests for the generate-then-swap primitives (#234).

Exercises the two DAO changes that let bulk regeneration create the new batch
before deleting the old one:

* ``delete_questions_for_chapter(..., exclude_ids=...)`` — skip the freshly
  created questions so a delete-after-generate doesn't wipe them.
* ``count_questions_without_responses`` — the up-front count that decides how
  many replacements to generate (no longer derived from the delete's return).
"""

import pytest
from bson import ObjectId

from app.db.base import get_collection
from app.db.questions import (
    delete_questions_for_chapter,
    count_questions_without_responses,
)

pytestmark = pytest.mark.asyncio

BOOK = "book-1"
CH = "ch-1"
USER = "user-1"


async def _seed_question(qid: ObjectId, order: int = 1) -> str:
    coll = await get_collection("questions")
    await coll.insert_one(
        {"_id": qid, "book_id": BOOK, "chapter_id": CH, "user_id": USER, "order": order}
    )
    return str(qid)


async def _seed_response(question_id: str) -> None:
    coll = await get_collection("question_responses")
    await coll.insert_one(
        {"question_id": question_id, "user_id": USER, "response_text": "an answer"}
    )


async def test_delete_excludes_given_ids(motor_reinit_db):
    keep = await _seed_question(ObjectId(), order=2)
    gone1 = await _seed_question(ObjectId(), order=1)
    gone3 = await _seed_question(ObjectId(), order=3)

    deleted = await delete_questions_for_chapter(
        book_id=BOOK,
        chapter_id=CH,
        user_id=USER,
        preserve_with_responses=True,
        exclude_ids={keep},
    )

    assert deleted == 2
    coll = await get_collection("questions")
    remaining = {str(q["_id"]) async for q in coll.find({"chapter_id": CH})}
    assert remaining == {keep}
    assert gone1 not in remaining and gone3 not in remaining


async def test_count_questions_without_responses(motor_reinit_db):
    answered = await _seed_question(ObjectId(), order=1)
    await _seed_question(ObjectId(), order=2)  # unanswered
    await _seed_question(ObjectId(), order=3)  # unanswered
    another_answered = await _seed_question(ObjectId(), order=4)
    await _seed_response(answered)
    await _seed_response(another_answered)

    assert await count_questions_without_responses(BOOK, CH, USER) == 2


async def test_count_is_zero_when_all_answered(motor_reinit_db):
    q = await _seed_question(ObjectId())
    await _seed_response(q)
    assert await count_questions_without_responses(BOOK, CH, USER) == 0


async def test_count_ignores_other_users_and_chapters(motor_reinit_db):
    await _seed_question(ObjectId())  # our unanswered question
    coll = await get_collection("questions")
    await coll.insert_one(
        {"_id": ObjectId(), "book_id": BOOK, "chapter_id": "other-ch", "user_id": USER, "order": 1}
    )
    await coll.insert_one(
        {"_id": ObjectId(), "book_id": BOOK, "chapter_id": CH, "user_id": "other-user", "order": 1}
    )
    assert await count_questions_without_responses(BOOK, CH, USER) == 1
