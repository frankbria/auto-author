"""#1050: a chapter's questions and their answers come back in one request,
read with a fixed number of queries however many questions the chapter has."""

import pytest
from bson import ObjectId

from app.db import questions as questions_db
from app.db.base import get_collection

pytestmark = pytest.mark.asyncio

CH = "ch-1050"


async def _make_book(client) -> str:
    resp = await client.post("/api/v1/books/", json={
        "title": "Answers", "description": "d", "genre": "Fiction", "target_audience": "General",
    })
    assert resp.status_code == 201
    return resp.json()["id"]


async def _seed(book_id: str, user_id: str, statuses: list) -> list:
    """One question per entry; a status of None means no response. Returns question ids."""
    questions = await get_collection("questions")
    responses = await get_collection("question_responses")
    ids = []
    for order, status in enumerate(statuses, start=1):
        qid = ObjectId()
        await questions.insert_one({
            "_id": qid, "book_id": book_id, "chapter_id": CH, "user_id": user_id,
            "question_text": f"Question {order}?", "question_type": "plot",
            "difficulty": "easy", "category": "general", "order": order,
            "metadata": {"suggested_response_length": "short"},
        })
        ids.append(str(qid))
        if status:
            await responses.insert_one({
                "question_id": str(qid), "user_id": user_id,
                "response_text": f"Answer {order}", "status": status,
            })
    return ids


def _url(book_id: str) -> str:
    return f"/api/v1/books/{book_id}/chapters/{CH}/question-answers"


async def test_returns_answers_attached_to_their_questions(auth_client_factory):
    client = await auth_client_factory(overrides={"auth_id": "u-1050"})
    book_id = await _make_book(client)
    ids = await _seed(book_id, "u-1050", ["completed", None, "draft", "completed"])

    resp = await client.get(_url(book_id))

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_questions"] == 4
    assert body["completed_count"] == 2
    assert body["in_progress_count"] == 1
    assert body["responses"] == [
        {"question_id": ids[0], "question": "Question 1?", "answer": "Answer 1", "status": "completed"},
        {"question_id": ids[2], "question": "Question 3?", "answer": "Answer 3", "status": "draft"},
        {"question_id": ids[3], "question": "Question 4?", "answer": "Answer 4", "status": "completed"},
    ]


async def test_empty_chapter(auth_client_factory):
    client = await auth_client_factory(overrides={"auth_id": "u-1050"})
    book_id = await _make_book(client)

    resp = await client.get(_url(book_id))

    assert resp.status_code == 200
    assert resp.json() == {
        "responses": [], "total_questions": 0, "completed_count": 0, "in_progress_count": 0,
    }


async def test_other_users_book_is_forbidden_and_missing_book_is_404(auth_client_factory):
    owner = await auth_client_factory(overrides={"auth_id": "owner-1050"})
    other = await auth_client_factory(overrides={"auth_id": "other-1050"})
    book_id = await _make_book(owner)
    await _seed(book_id, "owner-1050", ["completed"])

    assert (await other.get(_url(book_id))).status_code == 403
    assert (await owner.get(_url(str(ObjectId())))).status_code == 404


async def test_query_count_does_not_grow_with_questions(auth_client_factory, monkeypatch):
    client = await auth_client_factory(overrides={"auth_id": "u-1050"})
    book_id = await _make_book(client)
    await _seed(book_id, "u-1050", ["completed"] * 20)

    calls = []
    real_get_collection = questions_db.get_collection

    class Counting:
        def __init__(self, coll):
            self._coll = coll

        def __getattr__(self, name):
            attr = getattr(self._coll, name)
            if name in ("find", "find_one", "aggregate", "count_documents"):
                def wrapped(*a, **kw):
                    calls.append(name)
                    return attr(*a, **kw)
                return wrapped
            return attr

    async def counting(name):
        return Counting(await real_get_collection(name))

    monkeypatch.setattr(questions_db, "get_collection", counting)

    resp = await client.get(_url(book_id))

    assert resp.status_code == 200
    assert len(resp.json()["responses"]) == 20
    assert len(calls) <= 2, calls
