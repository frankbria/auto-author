"""Integration tests for single-question regeneration (issue #62).

Exercises the ``POST /books/{book_id}/chapters/{chapter_id}/questions/{question_id}/regenerate``
endpoint end to end against a real (test) MongoDB with mocked session auth. The AI wire
method is patched to return deterministic questions: these tests target replacement, the
per-question regeneration cap, and ownership/error handling — not AI generation. (They
previously leaned on an unconfigured OpenAI key being swallowed into template fallbacks;
since #182 genuine AI failures correctly surface as 503 instead.)
"""

from unittest.mock import AsyncMock, patch

import pytest
from bson import ObjectId
from httpx import AsyncClient

from app.db.base import get_collection
from app.services.ai_errors import AIRateLimitError

AI_METHOD = "app.services.ai_service.ai_service.generate_chapter_questions"


# Marker phrases the prompt builder emits per focus type, so the stub can
# honor a requested focus the way the real model would.
_FOCUS_MARKERS = {
    "character development, motivations": "character",
    "plot structure, events": "plot",
    "setting details, world-building": "setting",
    "themes, messages, symbolism": "theme",
    "research needs, factual accuracy": "research",
}


def _ai_question_dicts(prompt, count):
    qtype = "character"
    for marker, t in _FOCUS_MARKERS.items():
        if marker in prompt:
            qtype = t
            break
    return [
        {
            "question_text": f"What drives the {qtype} elements in scene {i} of this chapter?",
            "question_type": qtype,
            "difficulty": "medium",
        }
        for i in range(count)
    ]


@pytest.fixture(autouse=True)
def _deterministic_ai():
    """Patch the AI boundary so generation succeeds deterministically."""
    async def _fake(prompt, count=10):
        return _ai_question_dicts(prompt, count)

    with patch(AI_METHOD, new=AsyncMock(side_effect=_fake)):
        yield


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
    # AI-path replacement is not tagged as a template fallback (#182)
    assert new_q["is_fallback"] is False

    # The question still exists at that id
    coll = await get_collection("questions")
    assert await coll.find_one({"_id": ObjectId(original["id"])}) is not None


@pytest.mark.asyncio
async def test_regenerate_single_question_openai_outage_503(auth_client_factory, motor_reinit_db):
    """A genuine AI outage during single-question regeneration surfaces as a
    structured 503, not a silent template replacement (#182)."""
    client = await auth_client_factory()
    book_id, chapter_id = await _create_book_with_chapter(client)
    questions = await _generate_questions(client, book_id, chapter_id)
    qid = questions[0]["id"]

    with patch(AI_METHOD, new=AsyncMock(side_effect=AIRateLimitError("OpenAI outage"))):
        resp = await client.post(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{qid}/regenerate",
            json={},
        )
    assert resp.status_code == 503
    assert resp.json()["detail"]["error_code"] == "QUESTION_GENERATION_FAILED"

    # The original question is untouched (generation happens before any mutation).
    coll = await get_collection("questions")
    doc = await coll.find_one({"_id": ObjectId(qid)})
    assert doc is not None
    assert doc.get("regeneration_count", 0) == 0


@pytest.mark.asyncio
async def test_regenerate_single_question_fallback_replacement_tagged(auth_client_factory, motor_reinit_db):
    """When the AI responds but yields nothing usable, the in-place template
    replacement carries is_fallback=True instead of inheriting False (#182)."""
    client = await auth_client_factory()
    book_id, chapter_id = await _create_book_with_chapter(client)
    questions = await _generate_questions(client, book_id, chapter_id)
    qid = questions[0]["id"]
    assert questions[0]["is_fallback"] is False

    with patch(AI_METHOD, new=AsyncMock(return_value=[])):
        resp = await client.post(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{qid}/regenerate",
            json={},
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_fallback"] is True

    # The tag is persisted on the replaced document, not just echoed.
    coll = await get_collection("questions")
    doc = await coll.find_one({"_id": ObjectId(qid)})
    assert doc["is_fallback"] is True


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
