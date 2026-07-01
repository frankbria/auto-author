"""Integration tests for single-question regeneration (issue #62).

Exercises the ``POST /books/{book_id}/chapters/{chapter_id}/questions/{question_id}/regenerate``
endpoint end to end against a real (test) MongoDB with mocked session auth. AI generation
falls back to deterministic template questions when no AI key is configured, which is enough
to verify replacement, the per-question regeneration cap, and ownership/error handling.
"""

import pytest
from bson import ObjectId
from httpx import AsyncClient

from app.db.base import get_collection


async def _create_book_with_chapter(client: AsyncClient) -> tuple[str, str]:
    resp = await client.post(
        "/api/v1/books/",
        json={
            "title": "Regen Test Book",
            "description": "Testing question regeneration",
            "genre": "Non-fiction",
            "target_audience": "Developers",
        },
    )
    assert resp.status_code == 201
    book = resp.json()
    book_id = book["id"]

    chapter_id = f"ch-{str(ObjectId())}"
    toc = {"chapters": [{
        "id": chapter_id,
        "title": "Character Development",
        "description": "Building characters",
        "level": 1,
        "order": 1,
        "subchapters": [],
    }]}
    update = await client.put(
        f"/api/v1/books/{book_id}",
        json={
            "title": book["title"],
            "description": book.get("description"),
            "genre": book.get("genre"),
            "target_audience": book.get("target_audience"),
            "table_of_contents": toc,
        },
    )
    assert update.status_code == 200
    return book_id, chapter_id


async def _generate_questions(client: AsyncClient, book_id: str, chapter_id: str) -> list:
    resp = await client.post(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions",
        json={"count": 5, "focus": ["character"]},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["questions"]


@pytest.mark.asyncio
async def test_regenerate_single_question_success(auth_client_factory, motor_reinit_db):
    client = await auth_client_factory()
    book_id, chapter_id = await _create_book_with_chapter(client)
    questions = await _generate_questions(client, book_id, chapter_id)
    original = questions[0]

    resp = await client.post(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{original['id']}/regenerate",
        json={},
    )
    assert resp.status_code == 200, resp.text
    new_q = resp.json()

    # The question is replaced in place (same id/slot), with the counter bumped
    assert new_q["id"] == original["id"]
    assert new_q["order"] == original["order"]
    assert new_q["regeneration_count"] == 1

    # The question still exists at that id
    coll = await get_collection("questions")
    assert await coll.find_one({"_id": ObjectId(original["id"])}) is not None


@pytest.mark.asyncio
async def test_regenerate_single_question_clears_stale_response(auth_client_factory, motor_reinit_db):
    client = await auth_client_factory()
    book_id, chapter_id = await _create_book_with_chapter(client)
    questions = await _generate_questions(client, book_id, chapter_id)
    qid = questions[0]["id"]

    # Answer the question, then regenerate it — the old answer no longer applies.
    save = await client.put(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{qid}/response",
        json={"response_text": "My previous answer", "status": "completed"},
    )
    assert save.status_code == 200, save.text

    regen = await client.post(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{qid}/regenerate",
        json={},
    )
    assert regen.status_code == 200, regen.text

    resp = await client.get(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{qid}/response"
    )
    assert resp.status_code == 200
    assert resp.json()["has_response"] is False


@pytest.mark.asyncio
async def test_regenerate_single_question_focus_override(auth_client_factory, motor_reinit_db):
    client = await auth_client_factory()
    book_id, chapter_id = await _create_book_with_chapter(client)
    questions = await _generate_questions(client, book_id, chapter_id)

    resp = await client.post(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{questions[0]['id']}/regenerate",
        json={"focus": "theme"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["question_type"] == "theme"


@pytest.mark.asyncio
async def test_regenerate_single_question_at_limit_returns_429(auth_client_factory, motor_reinit_db):
    client = await auth_client_factory()
    book_id, chapter_id = await _create_book_with_chapter(client)
    questions = await _generate_questions(client, book_id, chapter_id)
    qid = questions[0]["id"]

    # Push this question to the regeneration cap
    coll = await get_collection("questions")
    await coll.update_one({"_id": ObjectId(qid)}, {"$set": {"regeneration_count": 5}})

    resp = await client.post(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{qid}/regenerate",
        json={},
    )
    assert resp.status_code == 429
    assert resp.json()["detail"]["error"] == "REGENERATION_LIMIT_REACHED"


@pytest.mark.asyncio
async def test_regenerate_single_question_not_found_returns_404(auth_client_factory, motor_reinit_db):
    client = await auth_client_factory()
    book_id, chapter_id = await _create_book_with_chapter(client)
    await _generate_questions(client, book_id, chapter_id)

    resp = await client.post(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{str(ObjectId())}/regenerate",
        json={},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_regenerate_single_question_wrong_owner_returns_403(auth_client_factory, motor_reinit_db):
    owner = await auth_client_factory()
    book_id, chapter_id = await _create_book_with_chapter(owner)
    questions = await _generate_questions(owner, book_id, chapter_id)
    qid = questions[0]["id"]

    other = await auth_client_factory(overrides={"auth_id": "someone-else-999"})
    resp = await other.post(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{qid}/regenerate",
        json={},
    )
    assert resp.status_code == 403
