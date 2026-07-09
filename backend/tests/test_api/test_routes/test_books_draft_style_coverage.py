"""Integration tests raising coverage of three books.py endpoints:

- POST /{book_id}/chapters/{chapter_id}/generate-draft   (generate_chapter_draft)
- POST /{book_id}/chapters/{chapter_id}/transform-style   (transform_chapter_style)
- POST /{book_id}/chapters/{chapter_id}/questions/responses/batch
      (save_question_responses_batch_endpoint)

Real MongoDB is used for book/chapter creation and batch persistence. Only the
AI service methods (generate_chapter_draft / transform_text_style) are patched,
since those endpoints call OpenAI.
"""
import pytest
from bson import ObjectId
from unittest.mock import AsyncMock, patch

from app.db import base


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_book(api, title="Coverage Book", genre="Fiction"):
    r = await api.post("/api/v1/books/", json={"title": title, "genre": genre})
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


async def _seed_toc_chapter(book_id, chapter_id="ch1", title="Chapter 1",
                            description="A chapter for coverage tests"):
    """Seed a chapter into the book's table_of_contents directly in MongoDB.

    The create_chapter HTTP endpoint can't be used here (it forwards an
    incompatible ``parent_id`` kwarg to the transaction layer), so we persist
    the TOC entry directly. generate-draft looks the chapter up in this TOC.
    """
    result = await base.books_collection.update_one(
        {"_id": ObjectId(book_id)},
        {"$set": {"table_of_contents": {"chapters": [
            {"id": chapter_id, "title": title, "description": description,
             "subchapters": []}
        ]}}},
    )
    assert result.matched_count == 1
    return chapter_id


_DRAFT_OK = {
    "success": True,
    "draft": "# Generated\n\nA narrative crafted from the interview responses.",
    "metadata": {
        "word_count": 42,
        "estimated_reading_time": 1,
        "generated_at": "2026-06-26 10:00:00",
        "model_used": "gpt-4",
        "writing_style": "professional",
        "target_length": 2000,
        "actual_length": 42,
    },
    "suggestions": ["Add an example", "Tighten the intro"],
}

_QA = [
    {"question": "What is the core idea?", "answer": "The value of testing."},
    {"question": "Give an example?", "answer": "A project without tests had many bugs."},
]


# ===========================================================================
# generate_chapter_draft
# ===========================================================================

@pytest.mark.asyncio
async def test_generate_draft_happy_path(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    chapter_id = await _seed_toc_chapter(book_id)

    with patch(
        "app.api.endpoints.books.ai_service.generate_chapter_draft",
        new=AsyncMock(return_value=_DRAFT_OK),
    ):
        r = await api.post(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-draft",
            json={
                "question_responses": _QA,
                "writing_style": "professional",
                "target_length": 1500,
            },
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["book_id"] == book_id
    assert body["chapter_id"] == chapter_id
    assert body["draft"].startswith("# Generated")
    assert body["metadata"]["word_count"] == 42
    assert body["suggestions"] == ["Add an example", "Tighten the intro"]
    assert body["message"] == "Draft generated successfully"


@pytest.mark.asyncio
async def test_generate_draft_coerces_invalid_target_length(auth_client_factory):
    """target_length out of range is silently coerced to 2000 (still succeeds)."""
    api = await auth_client_factory()
    book_id = await _create_book(api)
    chapter_id = await _seed_toc_chapter(book_id)

    with patch(
        "app.api.endpoints.books.ai_service.generate_chapter_draft",
        new=AsyncMock(return_value=_DRAFT_OK),
    ) as mock_gen:
        r = await api.post(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-draft",
            json={"question_responses": _QA, "target_length": 999999},
        )
    assert r.status_code == 200, r.text
    # Endpoint coerces the bad value to the 2000 default before calling the AI.
    assert mock_gen.call_args.kwargs["target_length"] == 2000


@pytest.mark.asyncio
async def test_generate_draft_book_not_found(auth_client_factory):
    api = await auth_client_factory()
    missing_book = str(ObjectId())
    r = await api.post(
        f"/api/v1/books/{missing_book}/chapters/whatever/generate-draft",
        json={"question_responses": _QA},
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "Book not found"


@pytest.mark.asyncio
async def test_generate_draft_wrong_owner_403(auth_client_factory):
    owner = await auth_client_factory()
    book_id = await _create_book(owner)
    chapter_id = await _seed_toc_chapter(book_id)

    other = await auth_client_factory(
        overrides={"auth_id": "other-user-999", "email": "o@e.com"}
    )
    r = await other.post(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-draft",
        json={"question_responses": _QA},
    )
    assert r.status_code == 403
    assert "Not authorized" in r.json()["detail"]


@pytest.mark.asyncio
async def test_generate_draft_chapter_not_in_toc_404(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    # Valid book, but a chapter id that isn't in the TOC.
    r = await api.post(
        f"/api/v1/books/{book_id}/chapters/nonexistent-chapter/generate-draft",
        json={"question_responses": _QA},
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "Chapter not found in table of contents"


@pytest.mark.asyncio
async def test_generate_draft_requires_responses_400(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    chapter_id = await _seed_toc_chapter(book_id)
    r = await api.post(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-draft",
        json={},
    )
    assert r.status_code == 400
    assert "Question responses are required" in r.json()["detail"]


@pytest.mark.asyncio
async def test_generate_draft_malformed_response_400(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    chapter_id = await _seed_toc_chapter(book_id)
    r = await api.post(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-draft",
        json={"question_responses": [{"question": "Missing the answer field"}]},
    )
    assert r.status_code == 400
    assert "must have 'question' and 'answer'" in r.json()["detail"]


@pytest.mark.asyncio
async def test_generate_draft_ai_returns_failure_503(auth_client_factory):
    """AI failure (incl. #181 truncation) surfaces its message as a 503, not a generic 500."""
    api = await auth_client_factory()
    book_id = await _create_book(api)
    chapter_id = await _seed_toc_chapter(book_id)

    with patch(
        "app.api.endpoints.books.ai_service.generate_chapter_draft",
        new=AsyncMock(return_value={"success": False, "error": "model down"}),
    ):
        r = await api.post(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-draft",
            json={"question_responses": _QA},
        )
    assert r.status_code == 503
    assert r.json()["detail"] == "Failed to generate draft: model down"


@pytest.mark.asyncio
async def test_generate_draft_ai_raises_500(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    chapter_id = await _seed_toc_chapter(book_id)

    with patch(
        "app.api.endpoints.books.ai_service.generate_chapter_draft",
        new=AsyncMock(side_effect=RuntimeError("boom")),
    ):
        r = await api.post(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-draft",
            json={"question_responses": _QA},
        )
    assert r.status_code == 500
    assert r.json()["detail"] == "Error generating draft"


# ===========================================================================
# transform_chapter_style
# ===========================================================================

def _transform_ok(style):
    return {
        "success": True,
        "transformed": f"Text rewritten in the {style} style.",
        "metadata": {
            "target_style": style,
            "style_label": style.capitalize(),
            "original_word_count": 5,
            "transformed_word_count": 8,
            "model_used": "gpt-4",
            "generated_at": "2026-06-26 10:00:00",
        },
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "style", ["professional", "conversational", "academic", "creative", "technical"]
)
async def test_transform_style_happy_path_each_style(auth_client_factory, style):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    chapter_id = await _seed_toc_chapter(book_id)

    with patch(
        "app.api.endpoints.books.ai_service.transform_text_style",
        new=AsyncMock(return_value=_transform_ok(style)),
    ):
        r = await api.post(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/transform-style",
            json={"content": "The cat sat on the mat.", "target_style": style},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["book_id"] == book_id
    assert body["chapter_id"] == chapter_id
    assert style in body["transformed"]
    assert body["metadata"]["target_style"] == style
    assert body["message"] == "Style transformed successfully"


@pytest.mark.asyncio
async def test_transform_style_book_not_found_404(auth_client_factory):
    api = await auth_client_factory()
    missing_book = str(ObjectId())
    r = await api.post(
        f"/api/v1/books/{missing_book}/chapters/ch1/transform-style",
        json={"content": "Some text.", "target_style": "professional"},
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "Book not found"


@pytest.mark.asyncio
async def test_transform_style_wrong_owner_403(auth_client_factory):
    owner = await auth_client_factory()
    book_id = await _create_book(owner)
    chapter_id = await _seed_toc_chapter(book_id)

    other = await auth_client_factory(
        overrides={"auth_id": "other-user-999", "email": "o@e.com"}
    )
    r = await other.post(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/transform-style",
        json={"content": "Some text.", "target_style": "creative"},
    )
    assert r.status_code == 403
    assert "Not authorized" in r.json()["detail"]


@pytest.mark.asyncio
async def test_transform_style_requires_content_400(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    chapter_id = await _seed_toc_chapter(book_id)
    r = await api.post(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/transform-style",
        json={"content": "   ", "target_style": "professional"},
    )
    assert r.status_code == 400
    assert "Content is required" in r.json()["detail"]


@pytest.mark.asyncio
async def test_transform_style_invalid_style_400(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    chapter_id = await _seed_toc_chapter(book_id)
    r = await api.post(
        f"/api/v1/books/{book_id}/chapters/{chapter_id}/transform-style",
        json={"content": "Hello there.", "target_style": "spicy"},
    )
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert "Unsupported writing style" in detail
    assert "professional" in detail  # lists valid styles


@pytest.mark.asyncio
async def test_transform_style_ai_failure_503(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    chapter_id = await _seed_toc_chapter(book_id)

    with patch(
        "app.api.endpoints.books.ai_service.transform_text_style",
        new=AsyncMock(return_value={"success": False, "error": "AI unavailable"}),
    ):
        r = await api.post(
            f"/api/v1/books/{book_id}/chapters/{chapter_id}/transform-style",
            json={"content": "Some text.", "target_style": "academic"},
        )
    assert r.status_code == 503
    assert "Failed to transform style" in r.json()["detail"]


# ===========================================================================
# save_question_responses_batch_endpoint
# ===========================================================================

def _batch_url(book_id, chapter_id="ch1"):
    return f"/api/v1/books/{book_id}/chapters/{chapter_id}/questions/responses/batch"


async def _create_question(book_id, chapter_id="ch1", user_id="test-auth-id-123", order=0):
    """Persist a real question so batch saves pass the ownership check (#187)."""
    from app.db.questions import create_question
    from app.schemas.book import (
        QuestionCreate, QuestionType, QuestionDifficulty, QuestionMetadata,
    )
    question = await create_question(
        QuestionCreate(
            book_id=book_id,
            chapter_id=chapter_id,
            question_text=f"Coverage question {order + 1}, what happens?",
            question_type=QuestionType.PLOT,
            difficulty=QuestionDifficulty.MEDIUM,
            category="plot",
            order=order,
            metadata=QuestionMetadata(suggested_response_length="100-200 words"),
        ),
        user_id,
    )
    return question["id"]


@pytest.mark.asyncio
async def test_batch_responses_happy_path(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    q1 = await _create_question(book_id)
    q2 = await _create_question(book_id, order=1)

    payload = [
        {"question_id": q1, "response_text": "First answer here.", "status": "draft"},
        {"question_id": q2, "response_text": "Second answer, completed.", "status": "completed"},
    ]
    r = await api.post(_batch_url(book_id), json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["total"] == 2
    assert body["saved"] == 2
    assert body["failed"] == 0
    assert body["errors"] is None
    assert len(body["results"]) == 2
    assert all(item["success"] for item in body["results"])
    assert "request_id" in body


@pytest.mark.asyncio
async def test_batch_responses_partial_failure(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)

    q1 = await _create_question(book_id)
    payload = [
        {"question_id": q1, "response_text": "Valid answer.", "status": "draft"},
        {"question_id": q1, "response_text": "", "status": "draft"},  # missing text -> fails
        {"question_id": "", "response_text": "No question id.", "status": "draft"},  # missing id -> fails
    ]
    r = await api.post(_batch_url(book_id), json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is False
    assert body["total"] == 3
    assert body["saved"] == 1
    assert body["failed"] == 2
    assert body["errors"] is not None
    assert len(body["errors"]) == 2


@pytest.mark.asyncio
async def test_batch_responses_update_existing(auth_client_factory):
    """A second save of the same question_id updates rather than duplicating."""
    api = await auth_client_factory()
    book_id = await _create_book(api)

    q_id = await _create_question(book_id)
    first = await api.post(
        _batch_url(book_id),
        json=[{"question_id": q_id, "response_text": "Original.", "status": "draft"}],
    )
    assert first.status_code == 200
    second = await api.post(
        _batch_url(book_id),
        json=[{"question_id": q_id, "response_text": "Edited and longer.", "status": "completed"}],
    )
    assert second.status_code == 200, second.text
    body = second.json()
    assert body["saved"] == 1
    assert body["results"][0]["is_update"] is True


@pytest.mark.asyncio
async def test_batch_responses_empty_list_422(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    r = await api.post(_batch_url(book_id), json=[])
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["error_code"] == "VALIDATION_FAILED"
    assert detail["details"][0]["message"] == "No responses provided"


@pytest.mark.asyncio
async def test_batch_responses_too_many_422(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _create_book(api)
    payload = [
        {"question_id": f"q{i}", "response_text": "x", "status": "draft"}
        for i in range(101)
    ]
    r = await api.post(_batch_url(book_id), json=payload)
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert "exceeds maximum" in detail["details"][0]["message"]


@pytest.mark.asyncio
async def test_batch_responses_book_not_found_404(auth_client_factory):
    api = await auth_client_factory()
    missing_book = str(ObjectId())
    r = await api.post(
        _batch_url(missing_book),
        json=[{"question_id": "q1", "response_text": "Answer.", "status": "draft"}],
    )
    assert r.status_code == 404
    detail = r.json()["detail"]
    assert detail["error_code"] == "BOOK_NOT_FOUND"


@pytest.mark.asyncio
async def test_batch_responses_wrong_owner_403(auth_client_factory):
    owner = await auth_client_factory()
    book_id = await _create_book(owner)

    other = await auth_client_factory(
        overrides={"auth_id": "other-user-999", "email": "o@e.com"}
    )
    r = await other.post(
        _batch_url(book_id),
        json=[{"question_id": "q1", "response_text": "Answer.", "status": "draft"}],
    )
    assert r.status_code == 403
    detail = r.json()["detail"]
    assert detail["error_code"] == "FORBIDDEN_OPERATION"


@pytest.mark.asyncio
async def test_batch_responses_foreign_question_rejected(auth_client_factory):
    """#187: a question_id from another book/chapter is flagged, not silently
    saved as an orphaned response."""
    api = await auth_client_factory()
    book_id = await _create_book(api)
    other_book_id = await _create_book(api, title="Other Book")

    valid_q = await _create_question(book_id)
    foreign_q = await _create_question(other_book_id)  # same owner, wrong book

    r = await api.post(
        _batch_url(book_id),
        json=[
            {"question_id": valid_q, "response_text": "Legit answer.", "status": "draft"},
            {"question_id": foreign_q, "response_text": "Misrouted answer.", "status": "draft"},
        ],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is False
    assert body["saved"] == 1
    assert body["failed"] == 1
    errors = {e["question_id"]: e for e in body["errors"]}
    assert "not found" in errors[foreign_q]["error"].lower()

    # The rejected item wrote nothing — no orphaned response document.
    from app.db.questions import get_question_response
    assert await get_question_response(foreign_q, "test-auth-id-123") is None
    assert await get_question_response(valid_q, "test-auth-id-123") is not None


@pytest.mark.asyncio
async def test_batch_responses_other_users_question_rejected(auth_client_factory):
    """#187: referencing another user's question id through your own book's
    batch endpoint is rejected — the check is scoped to the caller's user_id."""
    api = await auth_client_factory()
    book_id = await _create_book(api)
    victim_q = await _create_question(book_id, user_id="victim-user-999")

    r = await api.post(
        _batch_url(book_id),
        json=[{"question_id": victim_q, "response_text": "Hijack attempt.", "status": "draft"}],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is False
    assert body["saved"] == 0
    assert body["failed"] == 1
    assert "not found" in body["errors"][0]["error"].lower()

    from app.db.questions import get_question_response
    assert await get_question_response(victim_q, "test-auth-id-123") is None
