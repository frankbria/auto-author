"""
Integration coverage tests for the pre-TOC endpoint group in
`app/api/endpoints/books.py`:

  - POST /{book_id}/analyze-summary
  - POST /{book_id}/generate-questions
  - GET  /{book_id}/question-responses
  - PUT  /{book_id}/question-responses
  - GET  /{book_id}/toc-readiness

These run against a real MongoDB test database (session auth mocked via the
`auth_client_factory` fixture). Only the AI service (OpenAI) is patched.
"""

import pytest
from unittest.mock import patch, AsyncMock

from app.services.ai_errors import (
    AIRateLimitError,
    AINetworkError,
    AIServiceUnavailableError,
    AIInvalidRequestError,
    AIServiceError,
)

# A 24-hex ObjectId that won't exist in the freshly-dropped test DB.
MISSING_BOOK_ID = "507f1f77bcf86cd799439099"

# A summary comfortably above the PUT /summary 30-char minimum and the
# readiness basic-check thresholds (>=30 words / >=150 chars).
GOOD_SUMMARY = (
    "This is a thorough and detailed book summary about building reliable "
    "software systems for modern teams. It covers architecture, testing, "
    "deployment, observability, and long term maintenance practices in depth "
    "so that readers can apply the ideas immediately to their own projects."
)

ANALYSIS_OK = {
    "is_ready_for_toc": True,
    "confidence_score": 0.9,
    "analysis": "The summary is well structured and ready for TOC generation.",
    "suggestions": [],
    "word_count": 45,
    "character_count": 300,
    "meets_minimum_requirements": True,
}

ANALYSIS_NOT_READY = {
    "is_ready_for_toc": False,
    "confidence_score": 0.3,
    "analysis": "The summary needs more detail before TOC generation.",
    "suggestions": ["Add more structure"],
    "word_count": 45,
    "character_count": 300,
    "meets_minimum_requirements": False,
}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
async def _create_book(api, *, with_summary=True, title="Coverage Book"):
    """Create a book and (optionally) set a valid summary on it."""
    r = await api.post(
        "/api/v1/books/",
        json={"title": title, "genre": "Non-fiction", "target_audience": "Adults"},
    )
    assert r.status_code == 201, r.text
    book_id = r.json()["id"]

    if with_summary:
        rs = await api.put(
            f"/api/v1/books/{book_id}/summary",
            json={"summary": GOOD_SUMMARY},
        )
        assert rs.status_code == 200, rs.text
    return book_id


def _patch_analyze(return_value=None, side_effect=None):
    return patch(
        "app.services.ai_service.ai_service.analyze_summary_for_toc",
        new=AsyncMock(return_value=return_value, side_effect=side_effect),
    )


def _patch_questions(return_value=None, side_effect=None):
    return patch(
        "app.services.ai_service.ai_service.generate_clarifying_questions",
        new=AsyncMock(return_value=return_value, side_effect=side_effect),
    )


# --------------------------------------------------------------------------- #
# analyze-summary
# --------------------------------------------------------------------------- #
class TestAnalyzeSummary:
    @pytest.mark.asyncio
    async def test_happy_path_persists_and_returns_analysis(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)

        with _patch_analyze(return_value=dict(ANALYSIS_OK)):
            r = await api.post(f"/api/v1/books/{book_id}/analyze-summary")

        assert r.status_code == 200, r.text
        body = r.json()
        assert body["book_id"] == book_id
        assert body["analysis"]["is_ready_for_toc"] is True
        assert "analyzed_at" in body

        # Persisted: readiness now returns the stored analysis branch.
        rr = await api.get(f"/api/v1/books/{book_id}/toc-readiness")
        assert rr.status_code == 200
        assert rr.json()["is_ready_for_toc"] is True

    @pytest.mark.asyncio
    async def test_404_when_book_missing(self, auth_client_factory):
        api = await auth_client_factory()
        r = await api.post(f"/api/v1/books/{MISSING_BOOK_ID}/analyze-summary")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_403_wrong_owner(self, auth_client_factory):
        owner = await auth_client_factory()
        book_id = await _create_book(owner)
        other = await auth_client_factory(
            overrides={"auth_id": "other-user-999", "email": "o@e.com"}
        )
        r = await other.post(f"/api/v1/books/{book_id}/analyze-summary")
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_400_when_no_summary(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api, with_summary=False)
        r = await api.post(f"/api/v1/books/{book_id}/analyze-summary")
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_error_dict_returns_503_and_not_persisted(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        error_analysis = {
            "is_ready_for_toc": False,
            "confidence_score": 0.0,
            "analysis": "Error occurred during analysis",
            "suggestions": ["Try again later"],
            "error": "AI_UNEXPECTED_ERROR: 401 invalid_api_key",
        }
        with _patch_analyze(return_value=error_analysis):
            r = await api.post(f"/api/v1/books/{book_id}/analyze-summary")
        assert r.status_code == 503
        assert r.json()["detail"]["error_code"] == "AI_ANALYSIS_FAILED"

        # Not persisted -> readiness falls back to the basic (no-analysis) branch.
        rr = await api.get(f"/api/v1/books/{book_id}/toc-readiness")
        assert rr.status_code == 200
        assert "not yet completed" in rr.json()["analysis"]

    @pytest.mark.asyncio
    async def test_network_error_returns_503(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        with _patch_analyze(side_effect=AINetworkError(correlation_id="c1")):
            r = await api.post(f"/api/v1/books/{book_id}/analyze-summary")
        assert r.status_code == 503
        assert r.json()["detail"]["error_code"] == "AI_NETWORK_ERROR"

    @pytest.mark.asyncio
    async def test_rate_limit_returns_429(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        with _patch_analyze(side_effect=AIRateLimitError(retry_after=42, correlation_id="c2")):
            r = await api.post(f"/api/v1/books/{book_id}/analyze-summary")
        assert r.status_code == 429
        assert r.json()["detail"]["retry_after"] == 42

    @pytest.mark.asyncio
    async def test_invalid_request_returns_400(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        with _patch_analyze(side_effect=AIInvalidRequestError(message="bad", correlation_id="c3")):
            r = await api.post(f"/api/v1/books/{book_id}/analyze-summary")
        assert r.status_code == 400
        assert r.json()["detail"]["error_code"] == "AI_INVALID_REQUEST"

    @pytest.mark.asyncio
    async def test_generic_ai_error_returns_500(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        with _patch_analyze(
            side_effect=AIServiceError(message="boom", error_code="AI_X", correlation_id="c4")
        ):
            r = await api.post(f"/api/v1/books/{book_id}/analyze-summary")
        assert r.status_code == 500
        assert r.json()["detail"]["error_code"] == "AI_X"

    @pytest.mark.asyncio
    async def test_unexpected_exception_returns_500(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        with _patch_analyze(side_effect=ValueError("kaboom")):
            r = await api.post(f"/api/v1/books/{book_id}/analyze-summary")
        assert r.status_code == 500


# --------------------------------------------------------------------------- #
# generate-questions
# --------------------------------------------------------------------------- #
class TestGenerateQuestions:
    @pytest.mark.asyncio
    async def test_happy_path(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        questions = ["Q1?", "Q2?", "Q3?", "Q4?"]
        with _patch_questions(return_value=questions):
            r = await api.post(
                f"/api/v1/books/{book_id}/generate-questions", json={"num_questions": 4}
            )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["book_id"] == book_id
        assert body["total_questions"] == 4
        assert body["questions"] == questions

    @pytest.mark.asyncio
    async def test_default_num_questions_when_out_of_range(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        # num_questions=99 is out of [3,6] -> endpoint coerces to 4 (no error).
        with _patch_questions(return_value=["a", "b", "c", "d"]) as mock:
            r = await api.post(
                f"/api/v1/books/{book_id}/generate-questions", json={"num_questions": 99}
            )
        assert r.status_code == 200
        # Confirm the coerced value (4) was passed through to the AI service.
        assert mock.call_args[0][2] == 4

    @pytest.mark.asyncio
    async def test_404_when_book_missing(self, auth_client_factory):
        api = await auth_client_factory()
        r = await api.post(f"/api/v1/books/{MISSING_BOOK_ID}/generate-questions", json={})
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_403_wrong_owner(self, auth_client_factory):
        owner = await auth_client_factory()
        book_id = await _create_book(owner)
        other = await auth_client_factory(
            overrides={"auth_id": "other-user-999", "email": "o@e.com"}
        )
        r = await other.post(f"/api/v1/books/{book_id}/generate-questions", json={})
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_400_when_no_summary(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api, with_summary=False)
        r = await api.post(f"/api/v1/books/{book_id}/generate-questions", json={})
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_rate_limit_returns_429(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        with _patch_questions(side_effect=AIRateLimitError(retry_after=60, correlation_id="q1")):
            r = await api.post(f"/api/v1/books/{book_id}/generate-questions", json={})
        assert r.status_code == 429
        assert r.json()["detail"]["error_code"] == "AI_RATE_LIMIT"

    @pytest.mark.asyncio
    async def test_service_unavailable_returns_503(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        with _patch_questions(
            side_effect=AIServiceUnavailableError(retry_after=30, correlation_id="q2")
        ):
            r = await api.post(f"/api/v1/books/{book_id}/generate-questions", json={})
        assert r.status_code == 503
        assert r.json()["detail"]["error_code"] == "AI_SERVICE_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_network_error_returns_503(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        with _patch_questions(side_effect=AINetworkError(correlation_id="q3")):
            r = await api.post(f"/api/v1/books/{book_id}/generate-questions", json={})
        assert r.status_code == 503
        assert r.json()["detail"]["error_code"] == "AI_NETWORK_ERROR"

    @pytest.mark.asyncio
    async def test_invalid_request_returns_400(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        with _patch_questions(side_effect=AIInvalidRequestError(message="bad", correlation_id="q4")):
            r = await api.post(f"/api/v1/books/{book_id}/generate-questions", json={})
        assert r.status_code == 400
        assert r.json()["detail"]["error_code"] == "AI_INVALID_REQUEST"

    @pytest.mark.asyncio
    async def test_generic_ai_error_returns_500(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        with _patch_questions(
            side_effect=AIServiceError(message="boom", error_code="AI_Y", correlation_id="q5")
        ):
            r = await api.post(f"/api/v1/books/{book_id}/generate-questions", json={})
        assert r.status_code == 500
        assert r.json()["detail"]["error_code"] == "AI_Y"

    @pytest.mark.asyncio
    async def test_unexpected_exception_returns_500(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        with _patch_questions(side_effect=RuntimeError("kaboom")):
            r = await api.post(f"/api/v1/books/{book_id}/generate-questions", json={})
        assert r.status_code == 500


# --------------------------------------------------------------------------- #
# GET question-responses
# --------------------------------------------------------------------------- #
class TestGetQuestionResponses:
    @pytest.mark.asyncio
    async def test_not_provided_when_empty(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        r = await api.get(f"/api/v1/books/{book_id}/question-responses")
        assert r.status_code == 200
        body = r.json()
        assert body == {"responses": [], "status": "not_provided"}

    @pytest.mark.asyncio
    async def test_returns_saved_responses(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        # Generate one question, then answer it fully so the set is complete.
        with _patch_questions(return_value=["Q1?"]):
            await api.post(f"/api/v1/books/{book_id}/generate-questions", json={})
        responses = [{"question": "Q1?", "answer": "A1"}]
        rp = await api.put(
            f"/api/v1/books/{book_id}/question-responses", json={"responses": responses}
        )
        assert rp.status_code == 200, rp.text

        r = await api.get(f"/api/v1/books/{book_id}/question-responses")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "completed"
        assert body["responses"] == responses
        assert body["answered_at"] is not None

    @pytest.mark.asyncio
    async def test_404_when_book_missing(self, auth_client_factory):
        api = await auth_client_factory()
        r = await api.get(f"/api/v1/books/{MISSING_BOOK_ID}/question-responses")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_403_wrong_owner(self, auth_client_factory):
        owner = await auth_client_factory()
        book_id = await _create_book(owner)
        other = await auth_client_factory(
            overrides={"auth_id": "other-user-999", "email": "o@e.com"}
        )
        r = await other.get(f"/api/v1/books/{book_id}/question-responses")
        assert r.status_code == 403


# --------------------------------------------------------------------------- #
# PUT question-responses
# --------------------------------------------------------------------------- #
class TestSaveQuestionResponses:
    @pytest.mark.asyncio
    async def test_happy_path_marks_questions_answered(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)

        # Generate questions first so the clarifying_questions branch is exercised.
        with _patch_questions(return_value=["Q1?", "Q2?"]):
            await api.post(f"/api/v1/books/{book_id}/generate-questions", json={})

        responses = [
            {"question": "Q1?", "answer": "Answer one"},
            {"question": "Q2?", "answer": "Answer two"},
        ]
        r = await api.put(
            f"/api/v1/books/{book_id}/question-responses", json={"responses": responses}
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["responses_saved"] == 2
        assert body["ready_for_toc_generation"] is True
        assert body["answered_at"] is not None

    @pytest.mark.asyncio
    async def test_404_when_book_missing(self, auth_client_factory):
        api = await auth_client_factory()
        r = await api.put(
            f"/api/v1/books/{MISSING_BOOK_ID}/question-responses",
            json={"responses": [{"question": "q", "answer": "a"}]},
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_403_wrong_owner(self, auth_client_factory):
        owner = await auth_client_factory()
        book_id = await _create_book(owner)
        other = await auth_client_factory(
            overrides={"auth_id": "other-user-999", "email": "o@e.com"}
        )
        r = await other.put(
            f"/api/v1/books/{book_id}/question-responses",
            json={"responses": [{"question": "q", "answer": "a"}]},
        )
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_400_responses_not_a_list(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        r = await api.put(
            f"/api/v1/books/{book_id}/question-responses",
            json={"responses": {"not": "a list"}},
        )
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_400_response_not_an_object(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        r = await api.put(
            f"/api/v1/books/{book_id}/question-responses",
            json={"responses": ["just a string"]},
        )
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_400_missing_question_or_answer(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        r = await api.put(
            f"/api/v1/books/{book_id}/question-responses",
            json={"responses": [{"question": "only question"}]},
        )
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_400_empty_answer(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        r = await api.put(
            f"/api/v1/books/{book_id}/question-responses",
            json={"responses": [{"question": "q", "answer": "   "}]},
        )
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_empty_list_is_accepted(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        r = await api.put(
            f"/api/v1/books/{book_id}/question-responses", json={"responses": []}
        )
        assert r.status_code == 200
        assert r.json()["responses_saved"] == 0


# --------------------------------------------------------------------------- #
# PUT question-responses — completion status is derived, not hardcoded (#276)
# --------------------------------------------------------------------------- #
class TestQuestionResponseCompletionStatus:
    """The stored status must reflect whether the answer set covers every
    clarifying question — the #203 auto-save persists partial sets mid-typing,
    so a hardcoded 'completed' is a trap for any consumer of the field."""

    @pytest.mark.asyncio
    async def test_partial_set_is_draft(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        with _patch_questions(return_value=["Q1?", "Q2?", "Q3?"]):
            await api.post(f"/api/v1/books/{book_id}/generate-questions", json={})

        # Answer only 1 of 3 — the mid-typing auto-save shape.
        r = await api.put(
            f"/api/v1/books/{book_id}/question-responses",
            json={"responses": [{"question": "Q1?", "answer": "A1"}]},
        )
        assert r.status_code == 200, r.text
        assert r.json()["ready_for_toc_generation"] is False

        g = await api.get(f"/api/v1/books/{book_id}/question-responses")
        assert g.json()["status"] == "draft"

    @pytest.mark.asyncio
    async def test_complete_set_is_completed(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        with _patch_questions(return_value=["Q1?", "Q2?"]):
            await api.post(f"/api/v1/books/{book_id}/generate-questions", json={})

        r = await api.put(
            f"/api/v1/books/{book_id}/question-responses",
            json={
                "responses": [
                    {"question": "Q1?", "answer": "A1"},
                    {"question": "Q2?", "answer": "A2"},
                ]
            },
        )
        assert r.status_code == 200, r.text
        assert r.json()["ready_for_toc_generation"] is True

        g = await api.get(f"/api/v1/books/{book_id}/question-responses")
        assert g.json()["status"] == "completed"

    @pytest.mark.asyncio
    async def test_duplicate_responses_do_not_fake_completion(self, auth_client_factory):
        """Count alone is foolable: two responses that both answer Q1 (and omit
        Q2) reach the question count while leaving a current question unanswered.
        Completion is coverage of every current question, not a headcount."""
        api = await auth_client_factory()
        book_id = await _create_book(api)
        with _patch_questions(return_value=["Q1?", "Q2?"]):
            await api.post(f"/api/v1/books/{book_id}/generate-questions", json={})

        r = await api.put(
            f"/api/v1/books/{book_id}/question-responses",
            json={
                "responses": [
                    {"question": "Q1?", "answer": "A1"},
                    {"question": "Q1?", "answer": "A1 again"},
                ]
            },
        )
        assert r.status_code == 200, r.text
        assert r.json()["ready_for_toc_generation"] is False

        g = await api.get(f"/api/v1/books/{book_id}/question-responses")
        assert g.json()["status"] == "draft"

    @pytest.mark.asyncio
    async def test_dict_shaped_questions_are_normalized(self, auth_client_factory):
        """Some generation paths store questions as {"question": ...} dicts, not
        plain strings. Completion must normalize both shapes (dicts are unhashable
        — a naive set/`in` comparison crashes)."""
        api = await auth_client_factory()
        book_id = await _create_book(api)
        with _patch_questions(
            return_value=[
                {"question": "Q1?", "category": "a"},
                {"question": "Q2?", "category": "b"},
            ]
        ):
            await api.post(f"/api/v1/books/{book_id}/generate-questions", json={})

        # Partial → draft (and, crucially, no 500 from unhashable dicts).
        r = await api.put(
            f"/api/v1/books/{book_id}/question-responses",
            json={"responses": [{"question": "Q1?", "answer": "A1"}]},
        )
        assert r.status_code == 200, r.text
        assert r.json()["ready_for_toc_generation"] is False

        # Complete → completed.
        r = await api.put(
            f"/api/v1/books/{book_id}/question-responses",
            json={
                "responses": [
                    {"question": "Q1?", "answer": "A1"},
                    {"question": "Q2?", "answer": "A2"},
                ]
            },
        )
        assert r.status_code == 200, r.text
        assert r.json()["ready_for_toc_generation"] is True

    @pytest.mark.asyncio
    async def test_no_clarifying_questions_stays_draft(self, auth_client_factory):
        """Without a question set to compare against, completeness is unknowable —
        never claim 'completed' (fail toward draft, not toward the trap)."""
        api = await auth_client_factory()
        book_id = await _create_book(api)  # no generate-questions call

        r = await api.put(
            f"/api/v1/books/{book_id}/question-responses",
            json={"responses": [{"question": "Q?", "answer": "A"}]},
        )
        assert r.status_code == 200, r.text
        assert r.json()["ready_for_toc_generation"] is False

        g = await api.get(f"/api/v1/books/{book_id}/question-responses")
        assert g.json()["status"] == "draft"


# --------------------------------------------------------------------------- #
# toc-readiness
# --------------------------------------------------------------------------- #
class TestTocReadiness:
    @pytest.mark.asyncio
    async def test_404_when_book_missing(self, auth_client_factory):
        api = await auth_client_factory()
        r = await api.get(f"/api/v1/books/{MISSING_BOOK_ID}/toc-readiness")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_403_wrong_owner(self, auth_client_factory):
        owner = await auth_client_factory()
        book_id = await _create_book(owner)
        other = await auth_client_factory(
            overrides={"auth_id": "other-user-999", "email": "o@e.com"}
        )
        r = await other.get(f"/api/v1/books/{book_id}/toc-readiness")
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_no_summary_basic_branch(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api, with_summary=False)
        r = await api.get(f"/api/v1/books/{book_id}/toc-readiness")
        assert r.status_code == 200
        body = r.json()
        assert body["is_ready_for_toc"] is False
        assert body["word_count"] == 0
        assert body["character_count"] == 0
        assert body["meets_minimum_requirements"] is False

    @pytest.mark.asyncio
    async def test_summary_present_no_analysis_basic_branch(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)  # summary set, no analysis run
        r = await api.get(f"/api/v1/books/{book_id}/toc-readiness")
        assert r.status_code == 200
        body = r.json()
        assert body["is_ready_for_toc"] is False
        # GOOD_SUMMARY clears the basic word/char thresholds.
        assert body["word_count"] >= 30
        assert body["character_count"] >= 150
        assert body["meets_minimum_requirements"] is True
        assert "not yet completed" in body["analysis"]

    @pytest.mark.asyncio
    async def test_with_analysis_ready_branch(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        with _patch_analyze(return_value=dict(ANALYSIS_OK)):
            await api.post(f"/api/v1/books/{book_id}/analyze-summary")

        r = await api.get(f"/api/v1/books/{book_id}/toc-readiness")
        assert r.status_code == 200
        body = r.json()
        assert body["is_ready_for_toc"] is True
        assert body["confidence_score"] == 0.9
        assert body["meets_minimum_requirements"] is True

    @pytest.mark.asyncio
    async def test_with_analysis_not_ready_branch(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        with _patch_analyze(return_value=dict(ANALYSIS_NOT_READY)):
            await api.post(f"/api/v1/books/{book_id}/analyze-summary")

        r = await api.get(f"/api/v1/books/{book_id}/toc-readiness")
        assert r.status_code == 200
        body = r.json()
        assert body["is_ready_for_toc"] is False
        assert body["confidence_score"] == 0.3
        assert body["suggestions"] == ["Add more structure"]

    @pytest.mark.asyncio
    async def test_readiness_driven_by_analysis_not_responses(self, auth_client_factory):
        """Readiness reflects the summary analysis alone. The old composite that
        also required questions + 'completed' responses was computed then
        discarded by both return branches — deleted as dead code (#276), so an
        analysis-ready book with zero questions/responses still reads ready."""
        api = await auth_client_factory()
        book_id = await _create_book(api)
        with _patch_analyze(return_value=dict(ANALYSIS_OK)):
            await api.post(f"/api/v1/books/{book_id}/analyze-summary")

        # No generate-questions, no question-responses saved.
        r = await api.get(f"/api/v1/books/{book_id}/toc-readiness")
        assert r.status_code == 200
        body = r.json()
        assert body["is_ready_for_toc"] is True
        # The discarded composite fields must not appear in the response.
        assert "next_steps" not in body

    @pytest.mark.asyncio
    async def test_full_pipeline_ready_with_questions_and_responses(self, auth_client_factory):
        """Drive every readiness-input branch: analysis ready + questions + completed responses."""
        api = await auth_client_factory()
        book_id = await _create_book(api)

        with _patch_analyze(return_value=dict(ANALYSIS_OK)):
            await api.post(f"/api/v1/books/{book_id}/analyze-summary")
        with _patch_questions(return_value=["Q1?", "Q2?"]):
            await api.post(f"/api/v1/books/{book_id}/generate-questions", json={})
        await api.put(
            f"/api/v1/books/{book_id}/question-responses",
            json={"responses": [{"question": "Q1?", "answer": "A1"}]},
        )

        r = await api.get(f"/api/v1/books/{book_id}/toc-readiness")
        assert r.status_code == 200
        body = r.json()
        assert body["is_ready_for_toc"] is True
