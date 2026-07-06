"""
Integration tests for chapter-level interview-question endpoints in
``app/api/endpoints/books.py``.

Endpoints under test (all mounted under ``/api/v1/books``):
    - POST   /{book_id}/chapters/{chapter_id}/generate-questions
    - GET    /{book_id}/chapters/{chapter_id}/questions
    - PUT    /{book_id}/chapters/{chapter_id}/questions/{question_id}/response
    - GET    /{book_id}/chapters/{chapter_id}/questions/{question_id}/response
    - POST   /{book_id}/chapters/{chapter_id}/questions/{question_id}/rating
    - GET    /{book_id}/chapters/{chapter_id}/question-progress
    - POST   /{book_id}/chapters/{chapter_id}/regenerate-questions

These run against real MongoDB (questions/responses/ratings persist). Only the
AI layer is patched: ``ai_service.generate_chapter_questions`` is replaced with a
deterministic list of question dicts so generation is reproducible and offline.
The dedicated AI-failure tests patch the service method to raise an
``AIServiceError`` so the endpoint's 503/422 error branches are exercised.
"""

from unittest.mock import patch, AsyncMock

import pytest

from app.services.ai_errors import AIRateLimitError
from app.services.question_generation_service import QuestionGenerationService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

AI_METHOD = "app.services.ai_service.ai_service.generate_chapter_questions"

# A valid-format ObjectId that does not correspond to any seeded book.
MISSING_BOOK_ID = "507f1f77bcf86cd799439099"
# A valid-format ObjectId that does not correspond to any seeded question.
MISSING_QUESTION_ID = "507f1f77bcf86cd799439088"


def _ai_question_dicts(n: int = 5):
    """Return a deterministic list of raw AI question dicts."""
    return [
        {
            "question_text": f"What is the central conflict driving scene number {i}?",
            "question_type": "plot",
            "difficulty": "medium",
            "help_text": "Consider the stakes for the protagonist.",
            "examples": [],
        }
        for i in range(n)
    ]


async def _create_book(api, title="Questions Coverage Book"):
    resp = await api.post(
        "/api/v1/books/",
        json={"title": title, "genre": "Fiction", "target_audience": "Adults"},
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["id"]


async def _create_chapter(api, book_id, title="Chapter One"):
    """Return a chapter id for the question endpoints.

    The question endpoints key everything off the ``chapter_id`` string and do
    not require the chapter to exist in the book's TOC (generation falls back to
    defaults when the chapter is absent), so a synthetic id is sufficient and
    avoids the unrelated chapter-create code path.
    """
    return "chapter-1"


async def _generate_questions(api, book_id, chapter_id, count=5, body=None):
    """Generate questions with the AI patched; returns the parsed response JSON."""
    payload = body if body is not None else {"count": count}
    with patch(AI_METHOD, new=AsyncMock(return_value=_ai_question_dicts(count))):
        resp = await api.post(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions",
            json=payload,
        )
    return resp


async def _setup_with_questions(api, count=5):
    """Create a book + chapter and generate `count` questions; return ids."""
    book_id = await _create_book(api)
    chapter_id = await _create_chapter(api, book_id)
    resp = await _generate_questions(api, book_id, chapter_id, count=count)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    question_ids = [q["id"] for q in data["questions"]]
    return book_id, chapter_id, question_ids


# ===========================================================================
# generate_chapter_questions
# ===========================================================================

@pytest.mark.asyncio
async def test_generate_questions_happy_path_persists(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    chapter_id = await _create_chapter(api, book_id)

    resp = await _generate_questions(api, book_id, chapter_id, count=5)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == len(data["questions"])
    assert data["total"] >= 1
    assert "generation_id" in data
    # Every returned question has an id and belongs to the chapter.
    for q in data["questions"]:
        assert q["id"]
        assert q["chapter_id"] == chapter_id
        assert q["book_id"] == book_id

    # Confirm persistence via the list endpoint.
    list_resp = await api.get(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions?limit=50"
    )
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == data["total"]


@pytest.mark.asyncio
async def test_generate_questions_count_out_of_range_422(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    chapter_id = await _create_chapter(api, book_id)

    # count=51 exceeds the schema's le=50 -> validation error.
    resp = await api.post(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions",
        json={"count": 51},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_generate_questions_book_not_found_404(auth_client_factory):
    api = await auth_client_factory()
    resp = await _generate_questions(api, MISSING_BOOK_ID, "any-chapter", count=3)
    assert resp.status_code == 404
    body = resp.json()["detail"]
    assert body["error_code"] == "BOOK_NOT_FOUND"


@pytest.mark.asyncio
async def test_generate_questions_wrong_owner_403(auth_client_factory):
    owner = await auth_client_factory()
    book_id = await _create_book(owner)
    chapter_id = await _create_chapter(owner, book_id)

    other = await auth_client_factory(
        overrides={"auth_id": "other-user-999", "email": "o@e.com"}
    )
    resp = await _generate_questions(other, book_id, chapter_id, count=3)
    assert resp.status_code == 403
    assert resp.json()["detail"]["error_code"] == "FORBIDDEN_OPERATION"


@pytest.mark.asyncio
async def test_generate_questions_ai_service_error_503(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    chapter_id = await _create_chapter(api, book_id)

    # Simulate the service raising a retryable AI error -> 503.
    with patch.object(
        QuestionGenerationService,
        "generate_questions_for_chapter",
        new=AsyncMock(side_effect=AIRateLimitError("AI overloaded")),
    ):
        resp = await api.post(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions",
            json={"count": 5},
        )
    assert resp.status_code == 503
    assert resp.json()["detail"]["error_code"] == "QUESTION_GENERATION_FAILED"


@pytest.mark.asyncio
async def test_generate_questions_openai_outage_503_not_200(auth_client_factory):
    """AC #182: a failing ``_make_openai_request`` must surface as a structured
    503 through the full stack, not HTTP 200 with template questions."""
    api = await auth_client_factory()
    book_id = await _create_book(api)
    chapter_id = await _create_chapter(api, book_id)

    with patch(
        "app.services.ai_service.ai_service._make_openai_request",
        new=AsyncMock(side_effect=AIRateLimitError("OpenAI outage")),
    ):
        resp = await api.post(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions",
            json={"count": 5},
        )
    assert resp.status_code == 503
    assert resp.json()["detail"]["error_code"] == "QUESTION_GENERATION_FAILED"


@pytest.mark.asyncio
async def test_generate_questions_empty_ai_response_tagged_fallback(auth_client_factory):
    """AI responded but yielded nothing usable -> 200 with template questions
    explicitly tagged ``is_fallback`` so clients can tell real from fallback (#182)."""
    api = await auth_client_factory()
    book_id = await _create_book(api)
    chapter_id = await _create_chapter(api, book_id)

    with patch(AI_METHOD, new=AsyncMock(return_value=[])):
        resp = await api.post(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions",
            json={"count": 5},
        )
    assert resp.status_code == 200, resp.text
    questions = resp.json()["questions"]
    assert len(questions) >= 1
    assert all(q["is_fallback"] is True for q in questions)


@pytest.mark.asyncio
async def test_generate_questions_value_error_422(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    chapter_id = await _create_chapter(api, book_id)

    # Service-level ValueError is mapped to a 422 validation error by the endpoint.
    with patch.object(
        QuestionGenerationService,
        "generate_questions_for_chapter",
        new=AsyncMock(side_effect=ValueError("Chapter not found")),
    ):
        resp = await api.post(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions",
            json={"count": 5},
        )
    assert resp.status_code == 422
    assert resp.json()["detail"]["error_code"] == "VALIDATION_FAILED"


# ===========================================================================
# list_chapter_questions
# ===========================================================================

@pytest.mark.asyncio
async def test_list_questions_happy_and_filters(auth_client_factory):
    api = await auth_client_factory()
    book_id, chapter_id, _ = await _setup_with_questions(api, count=5)

    base = f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions"

    # Unfiltered.
    resp = await api.get(f"{base}?limit=50")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert data["page"] == 1

    # question_type filter (all generated are "plot").
    resp_type = await api.get(f"{base}?question_type=plot&limit=50")
    assert resp_type.status_code == 200
    assert resp_type.json()["total"] == 5

    # status filter for not-yet-answered questions.
    resp_status = await api.get(f"{base}?status=not_answered&limit=50")
    assert resp_status.status_code == 200
    assert resp_status.json()["total"] == 5

    # category filter that matches nothing.
    resp_cat = await api.get(f"{base}?category=does-not-exist&limit=50")
    assert resp_cat.status_code == 200
    assert resp_cat.json()["total"] == 0


@pytest.mark.asyncio
async def test_list_questions_pagination(auth_client_factory):
    api = await auth_client_factory()
    book_id, chapter_id, _ = await _setup_with_questions(api, count=5)

    base = f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions"
    resp = await api.get(f"{base}?page=1&limit=2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 1
    assert data["pages"] == 3  # ceil(5/2)
    assert data["has_more"] is True
    assert len(data["questions"]) == 2


@pytest.mark.asyncio
async def test_list_questions_invalid_pagination_422(auth_client_factory):
    api = await auth_client_factory()
    book_id, chapter_id, _ = await _setup_with_questions(api, count=3)
    base = f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions"

    # page below the Query ge=1 bound.
    assert (await api.get(f"{base}?page=0")).status_code == 422
    # limit above the Query le=50 bound.
    assert (await api.get(f"{base}?limit=999")).status_code == 422


@pytest.mark.asyncio
async def test_list_questions_book_not_found_404(auth_client_factory):
    api = await auth_client_factory()
    resp = await api.get(
        f"/api/v1/books/{MISSING_BOOK_ID}/chapters/c1/questions"
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["error_code"] == "BOOK_NOT_FOUND"


@pytest.mark.asyncio
async def test_list_questions_wrong_owner_403(auth_client_factory):
    owner = await auth_client_factory()
    book_id, chapter_id, _ = await _setup_with_questions(owner, count=3)

    other = await auth_client_factory(
        overrides={"auth_id": "other-user-999", "email": "o@e.com"}
    )
    resp = await other.get(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions"
    )
    assert resp.status_code == 403


# ===========================================================================
# save_question_response
# ===========================================================================

@pytest.mark.asyncio
async def test_save_response_happy_path(auth_client_factory):
    api = await auth_client_factory()
    book_id, chapter_id, qids = await _setup_with_questions(api, count=3)
    qid = qids[0]

    resp = await api.put(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{qid}/response",
        json={"response_text": "This chapter explores loss and resilience.", "status": "draft"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["response"]["word_count"] == 6


@pytest.mark.asyncio
async def test_save_response_update_existing(auth_client_factory):
    api = await auth_client_factory()
    book_id, chapter_id, qids = await _setup_with_questions(api, count=3)
    qid = qids[0]
    url = f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{qid}/response"

    first = await api.put(url, json={"response_text": "First draft answer."})
    assert first.status_code == 200
    second = await api.put(
        url, json={"response_text": "A revised and longer answer here.", "status": "completed"}
    )
    assert second.status_code == 200
    assert second.json()["response"]["status"] == "completed"


@pytest.mark.asyncio
async def test_save_response_whitespace_only_422(auth_client_factory):
    api = await auth_client_factory()
    book_id, chapter_id, qids = await _setup_with_questions(api, count=3)
    qid = qids[0]

    resp = await api.put(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{qid}/response",
        json={"response_text": "   "},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["error_code"] == "VALIDATION_FAILED"


@pytest.mark.asyncio
async def test_save_response_book_not_found_404(auth_client_factory):
    api = await auth_client_factory()
    resp = await api.put(
        f"/api/v1/books/{MISSING_BOOK_ID}/chapters/c1/questions/{MISSING_QUESTION_ID}/response",
        json={"response_text": "Some answer text."},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["error_code"] == "BOOK_NOT_FOUND"


@pytest.mark.asyncio
async def test_save_response_wrong_owner_403(auth_client_factory):
    owner = await auth_client_factory()
    book_id, chapter_id, qids = await _setup_with_questions(owner, count=3)

    other = await auth_client_factory(
        overrides={"auth_id": "other-user-999", "email": "o@e.com"}
    )
    resp = await other.put(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{qids[0]}/response",
        json={"response_text": "Trying to write to someone else's book."},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_save_response_question_not_found_422(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    chapter_id = await _create_chapter(api, book_id)

    # Valid book/owner but the question id does not exist -> service ValueError -> 422.
    resp = await api.put(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{MISSING_QUESTION_ID}/response",
        json={"response_text": "Answer for a missing question."},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["error_code"] == "VALIDATION_FAILED"


@pytest.mark.asyncio
async def test_save_response_wrong_chapter_422(auth_client_factory):
    api = await auth_client_factory()
    book_id, chapter_id, qids = await _setup_with_questions(api, count=3)

    # Real question id but mismatched chapter in the path -> service ValueError -> 422.
    resp = await api.put(
        f"/api/v1/books/{book_id}/chapters/wrong-chapter/questions/{qids[0]}/response",
        json={"response_text": "Answer with mismatched chapter."},
    )
    assert resp.status_code == 422


# ===========================================================================
# get_question_response
# ===========================================================================

@pytest.mark.asyncio
async def test_get_response_after_save(auth_client_factory):
    api = await auth_client_factory()
    book_id, chapter_id, qids = await _setup_with_questions(api, count=3)
    qid = qids[0]
    url = f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{qid}/response"

    await api.put(url, json={"response_text": "A saved answer to retrieve."})
    resp = await api.get(url)
    assert resp.status_code == 200
    body = resp.json()
    assert body["has_response"] is True
    assert body["response"]["response_text"] == "A saved answer to retrieve."


@pytest.mark.asyncio
async def test_get_response_none_when_unanswered(auth_client_factory):
    api = await auth_client_factory()
    book_id, chapter_id, qids = await _setup_with_questions(api, count=3)

    resp = await api.get(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{qids[0]}/response"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["has_response"] is False
    assert body["response"] is None


@pytest.mark.asyncio
async def test_get_response_book_not_found_404(auth_client_factory):
    api = await auth_client_factory()
    resp = await api.get(
        f"/api/v1/books/{MISSING_BOOK_ID}/chapters/c1/questions/{MISSING_QUESTION_ID}/response"
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["error_code"] == "BOOK_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_response_wrong_owner_403(auth_client_factory):
    owner = await auth_client_factory()
    book_id, chapter_id, qids = await _setup_with_questions(owner, count=3)

    other = await auth_client_factory(
        overrides={"auth_id": "other-user-999", "email": "o@e.com"}
    )
    resp = await other.get(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{qids[0]}/response"
    )
    assert resp.status_code == 403


# ===========================================================================
# rate_question
# ===========================================================================

@pytest.mark.asyncio
async def test_rate_question_happy_path(auth_client_factory):
    api = await auth_client_factory()
    book_id, chapter_id, qids = await _setup_with_questions(api, count=3)
    qid = qids[0]

    resp = await api.post(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{qid}/rating",
        json={"question_id": qid, "user_id": "ignored", "rating": 4, "feedback": "Helpful"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["rating"]["rating"] == 4


@pytest.mark.asyncio
async def test_rate_question_invalid_rating_422(auth_client_factory):
    api = await auth_client_factory()
    book_id, chapter_id, qids = await _setup_with_questions(api, count=3)
    qid = qids[0]

    # rating below the schema's ge=1 bound.
    resp = await api.post(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{qid}/rating",
        json={"question_id": qid, "user_id": "x", "rating": 0},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_rate_question_book_not_found_404(auth_client_factory):
    api = await auth_client_factory()
    resp = await api.post(
        f"/api/v1/books/{MISSING_BOOK_ID}/chapters/c1/questions/{MISSING_QUESTION_ID}/rating",
        json={"question_id": MISSING_QUESTION_ID, "user_id": "x", "rating": 3},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["error_code"] == "BOOK_NOT_FOUND"


@pytest.mark.asyncio
async def test_rate_question_wrong_owner_403(auth_client_factory):
    owner = await auth_client_factory()
    book_id, chapter_id, qids = await _setup_with_questions(owner, count=3)

    other = await auth_client_factory(
        overrides={"auth_id": "other-user-999", "email": "o@e.com"}
    )
    resp = await other.post(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{qids[0]}/rating",
        json={"question_id": qids[0], "user_id": "x", "rating": 3},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_rate_question_not_found_422(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    chapter_id = await _create_chapter(api, book_id)

    # Valid book/owner but nonexistent question -> service ValueError -> 422.
    resp = await api.post(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{MISSING_QUESTION_ID}/rating",
        json={"question_id": MISSING_QUESTION_ID, "user_id": "x", "rating": 5},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["error_code"] == "VALIDATION_FAILED"


# ===========================================================================
# get_chapter_question_progress
# ===========================================================================

@pytest.mark.asyncio
async def test_progress_not_started(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    chapter_id = await _create_chapter(api, book_id)

    resp = await api.get(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/question-progress"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["completed"] == 0
    assert data["status"] == "not-started"


@pytest.mark.asyncio
async def test_progress_in_progress_after_answer(auth_client_factory):
    api = await auth_client_factory()
    book_id, chapter_id, qids = await _setup_with_questions(api, count=3)

    # Answer one question as completed.
    await api.put(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{qids[0]}/response",
        json={"response_text": "A completed answer.", "status": "completed"},
    )

    resp = await api.get(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/question-progress"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert data["completed"] == 1
    assert 0.0 < data["progress"] < 1.0
    assert data["status"] == "in-progress"


@pytest.mark.asyncio
async def test_progress_book_not_found_404(auth_client_factory):
    api = await auth_client_factory()
    resp = await api.get(
        f"/api/v1/books/{MISSING_BOOK_ID}/chapters/c1/question-progress"
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["error_code"] == "BOOK_NOT_FOUND"


@pytest.mark.asyncio
async def test_progress_wrong_owner_403(auth_client_factory):
    owner = await auth_client_factory()
    book_id, chapter_id, _ = await _setup_with_questions(owner, count=3)

    other = await auth_client_factory(
        overrides={"auth_id": "other-user-999", "email": "o@e.com"}
    )
    resp = await other.get(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/question-progress"
    )
    assert resp.status_code == 403


# ===========================================================================
# regenerate_chapter_questions
# ===========================================================================

@pytest.mark.asyncio
async def test_regenerate_questions_happy_path(auth_client_factory):
    api = await auth_client_factory()
    book_id, chapter_id, _ = await _setup_with_questions(api, count=5)

    # Regenerate without preserving responses -> fresh batch.
    with patch(AI_METHOD, new=AsyncMock(return_value=_ai_question_dicts(5))):
        resp = await api.post(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/regenerate-questions?preserve_responses=false",
            json={"count": 4},
        )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["questions"]) >= 1
    # AI-generated questions are not tagged as fallback (#182).
    assert all(q["is_fallback"] is False for q in data["questions"])


@pytest.mark.asyncio
async def test_regenerate_questions_openai_outage_503(auth_client_factory):
    """The regeneration route maps a genuine OpenAI failure to 503 too (#182)."""
    api = await auth_client_factory()
    book_id = await _create_book(api)
    chapter_id = await _create_chapter(api, book_id)

    with patch(
        "app.services.ai_service.ai_service._make_openai_request",
        new=AsyncMock(side_effect=AIRateLimitError("OpenAI outage")),
    ):
        resp = await api.post(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/regenerate-questions?preserve_responses=false",
            json={"count": 4},
        )
    assert resp.status_code == 503
    assert resp.json()["detail"]["error_code"] == "QUESTION_GENERATION_FAILED"


@pytest.mark.asyncio
async def test_regenerate_questions_count_out_of_range_422(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    chapter_id = await _create_chapter(api, book_id)

    resp = await api.post(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/regenerate-questions",
        json={"count": 51},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_regenerate_questions_book_not_found_404(auth_client_factory):
    api = await auth_client_factory()
    resp = await api.post(
        f"/api/v1/books/{MISSING_BOOK_ID}/chapters/c1/regenerate-questions",
        json={"count": 4},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["error_code"] == "BOOK_NOT_FOUND"


@pytest.mark.asyncio
async def test_regenerate_questions_wrong_owner_403(auth_client_factory):
    owner = await auth_client_factory()
    book_id, chapter_id, _ = await _setup_with_questions(owner, count=3)

    other = await auth_client_factory(
        overrides={"auth_id": "other-user-999", "email": "o@e.com"}
    )
    resp = await other.post(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/regenerate-questions",
        json={"count": 4},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_regenerate_questions_ai_service_error_503(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    chapter_id = await _create_chapter(api, book_id)

    with patch.object(
        QuestionGenerationService,
        "regenerate_chapter_questions",
        new=AsyncMock(side_effect=AIRateLimitError("AI overloaded")),
    ):
        resp = await api.post(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/regenerate-questions",
            json={"count": 4},
        )
    assert resp.status_code == 503
    assert resp.json()["detail"]["error_code"] == "QUESTION_GENERATION_FAILED"


@pytest.mark.asyncio
async def test_regenerate_questions_value_error_422(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    chapter_id = await _create_chapter(api, book_id)

    with patch.object(
        QuestionGenerationService,
        "regenerate_chapter_questions",
        new=AsyncMock(side_effect=ValueError("Chapter not found")),
    ):
        resp = await api.post(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/regenerate-questions",
            json={"count": 4},
        )
    assert resp.status_code == 422
    assert resp.json()["detail"]["error_code"] == "VALIDATION_FAILED"
