"""
Integration coverage tests for the TOC endpoints in app/api/endpoints/books.py.

Covers three endpoints and their branches:
  - POST /{book_id}/generate-toc   (happy + body/persisted responses + 404/403/400 + AI errors)
  - GET  /{book_id}/toc            (not-generated + generated + 404/403)
  - PUT  /{book_id}/toc            (happy + validation 400s + 404/403/409)

Real MongoDB runs; only the AI service is patched (it would otherwise call OpenAI).
Run with an isolated DB, e.g.:
  TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-c3 \
    uv run pytest tests/test_api/test_routes/test_books_toc_coverage.py -q
"""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi import status

from app.services.ai_errors import (
    AIServiceUnavailableError,
    AINetworkError,
    AIRateLimitError,
    AIInvalidRequestError,
    AIServiceError,
)


# A nonexistent but VALID ObjectId (24 hex chars) — exercises the 404 branches
# without tripping invalid-ObjectId handling.
MISSING_BOOK_ID = "507f1f77bcf86cd799439099"

LONG_SUMMARY = (
    "This is a sufficiently long book summary used to exercise the TOC "
    "generation flow end to end across the test suite."
)

MOCK_TOC_RESULT = {
    "toc": {
        "chapters": [
            {
                "id": "ch1",
                "title": "Introduction",
                "level": 1,
                "order": 1,
                "description": "Intro chapter",
            },
            {
                "id": "ch2",
                "title": "Body",
                "level": 1,
                "order": 2,
                "description": "Main chapter",
            },
        ],
        "total_chapters": 2,
        "estimated_pages": 40,
        "structure_notes": "linear",
    },
    "chapters_count": 2,
    "has_subchapters": False,
    "success": True,
}

AI_PATCH_TARGET = (
    "app.services.ai_service.ai_service.generate_toc_from_summary_and_responses"
)


@pytest.fixture(autouse=True)
def _rebind_toc_transactions(motor_reinit_db):
    """Rebind the globals captured by app.db.toc_transactions at import time.

    The PUT /toc handler delegates to update_toc_with_transaction, which uses the
    module-level `_client` / `books_collection` it imported from app.db.base. The
    conftest `motor_reinit_db` fixture creates a fresh Motor client per test and
    rebinds `base.*` plus the DAO modules, but NOT toc_transactions — leaving it
    pointed at a client whose event loop has been closed. Rebind it here so the
    transaction layer uses the same live, per-test client as everything else.
    """
    import app.db.toc_transactions as toctx
    from app.db import base

    toctx._client = base._client
    toctx._db = base._db
    toctx.books_collection = base.books_collection
    yield


async def _create_book(api, title="TOC Coverage Book"):
    resp = await api.post(
        "/api/v1/books/",
        json={
            "title": title,
            "description": "A book for TOC coverage testing.",
            "genre": "Non-fiction",
            "target_audience": "Developers",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _set_summary(api, book_id, summary=LONG_SUMMARY):
    resp = await api.put(f"/api/v1/books/{book_id}/summary", json={"summary": summary})
    assert resp.status_code == 200, resp.text


async def _set_persisted_responses(api, book_id, responses):
    resp = await api.put(
        f"/api/v1/books/{book_id}/question-responses", json={"responses": responses}
    )
    assert resp.status_code == 200, resp.text


# --------------------------------------------------------------------------- #
# POST /{book_id}/generate-toc
# --------------------------------------------------------------------------- #


class TestGenerateToc:
    @pytest.mark.asyncio
    async def test_happy_path_responses_from_body(self, auth_client_factory):
        """Responses supplied in the request body are used (wizard path)."""
        api = await auth_client_factory()
        book_id = await _create_book(api)
        await _set_summary(api, book_id)

        with patch(AI_PATCH_TARGET, new=AsyncMock(return_value=MOCK_TOC_RESULT)) as m:
            resp = await api.post(
                f"/api/v1/books/{book_id}/generate-toc",
                json={
                    "question_responses": [
                        {"question": "Q1", "answer": "A1"},
                        {"question": "Q2", "answer": "A2"},
                    ]
                },
            )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["book_id"] == book_id
        assert body["success"] is True
        assert body["chapters_count"] == 2
        assert body["has_subchapters"] is False
        assert body["toc"]["chapters"][0]["title"] == "Introduction"
        assert "generated_at" in body
        # Body responses were passed through to the AI service.
        assert m.called
        assert len(m.call_args[0][1]) == 2

    @pytest.mark.asyncio
    async def test_happy_path_falls_back_to_persisted_responses(
        self, auth_client_factory
    ):
        """With no body responses, persisted question_responses are used."""
        api = await auth_client_factory()
        book_id = await _create_book(api)
        await _set_summary(api, book_id)
        await _set_persisted_responses(
            api,
            book_id,
            [
                {"question": "Persisted Q1", "answer": "PA1"},
                {"question": "Persisted Q2", "answer": "PA2"},
                {"question": "Persisted Q3", "answer": "PA3"},
            ],
        )

        with patch(AI_PATCH_TARGET, new=AsyncMock(return_value=MOCK_TOC_RESULT)) as m:
            # Empty body -> must fall back to persisted responses.
            resp = await api.post(f"/api/v1/books/{book_id}/generate-toc", json={})

        assert resp.status_code == 200, resp.text
        assert resp.json()["success"] is True
        assert m.called
        assert len(m.call_args[0][1]) == 3  # persisted responses used

        # And the generated TOC was persisted on the book.
        get_resp = await api.get(f"/api/v1/books/{book_id}/toc")
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "generated"

    @pytest.mark.asyncio
    async def test_book_not_found_returns_404(self, auth_client_factory):
        api = await auth_client_factory()
        resp = await api.post(
            f"/api/v1/books/{MISSING_BOOK_ID}/generate-toc",
            json={"question_responses": [{"question": "Q", "answer": "A"}]},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Book not found"

    @pytest.mark.asyncio
    async def test_wrong_owner_returns_403(self, auth_client_factory):
        owner = await auth_client_factory()
        book_id = await _create_book(owner)
        await _set_summary(owner, book_id)

        other = await auth_client_factory(
            overrides={"auth_id": "other-user-999", "email": "o@e.com"}
        )
        resp = await other.post(
            f"/api/v1/books/{book_id}/generate-toc",
            json={"question_responses": [{"question": "Q", "answer": "A"}]},
        )
        assert resp.status_code == 403
        assert "Not authorized" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_missing_summary_returns_400(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        # No summary set.
        resp = await api.post(
            f"/api/v1/books/{book_id}/generate-toc",
            json={"question_responses": [{"question": "Q", "answer": "A"}]},
        )
        assert resp.status_code == 400
        assert "summary is required" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_missing_responses_returns_400(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        await _set_summary(api, book_id)
        # Summary present but no responses anywhere.
        resp = await api.post(f"/api/v1/books/{book_id}/generate-toc", json={})
        assert resp.status_code == 400
        assert "question responses are required" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_ai_rate_limit_returns_429(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        await _set_summary(api, book_id)

        err = AIRateLimitError(
            retry_after=90, cached_content_available=True, correlation_id="rl-1"
        )
        with patch(AI_PATCH_TARGET, new=AsyncMock(side_effect=err)):
            resp = await api.post(
                f"/api/v1/books/{book_id}/generate-toc",
                json={"question_responses": [{"question": "Q", "answer": "A"}]},
            )
        assert resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        detail = resp.json()["detail"]
        assert detail["error_code"] == "AI_RATE_LIMIT"
        assert detail["retry_after"] == 90
        assert detail["cached_content_available"] is True
        assert detail["correlation_id"] == "rl-1"

    @pytest.mark.asyncio
    async def test_ai_service_unavailable_returns_503(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        await _set_summary(api, book_id)

        err = AIServiceUnavailableError(retry_after=45, correlation_id="su-1")
        with patch(AI_PATCH_TARGET, new=AsyncMock(side_effect=err)):
            resp = await api.post(
                f"/api/v1/books/{book_id}/generate-toc",
                json={"question_responses": [{"question": "Q", "answer": "A"}]},
            )
        assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        detail = resp.json()["detail"]
        assert detail["error_code"] == "AI_SERVICE_UNAVAILABLE"
        assert detail["retry_after"] == 45

    @pytest.mark.asyncio
    async def test_ai_network_error_returns_503(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        await _set_summary(api, book_id)

        err = AINetworkError(correlation_id="net-1")
        with patch(AI_PATCH_TARGET, new=AsyncMock(side_effect=err)):
            resp = await api.post(
                f"/api/v1/books/{book_id}/generate-toc",
                json={"question_responses": [{"question": "Q", "answer": "A"}]},
            )
        assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        detail = resp.json()["detail"]
        assert detail["error_code"] == "AI_NETWORK_ERROR"
        assert detail["retryable"] is True

    @pytest.mark.asyncio
    async def test_ai_invalid_request_returns_400(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        await _set_summary(api, book_id)

        err = AIInvalidRequestError(message="bad params", correlation_id="inv-1")
        with patch(AI_PATCH_TARGET, new=AsyncMock(side_effect=err)):
            resp = await api.post(
                f"/api/v1/books/{book_id}/generate-toc",
                json={"question_responses": [{"question": "Q", "answer": "A"}]},
            )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        detail = resp.json()["detail"]
        assert detail["error_code"] == "AI_INVALID_REQUEST"

    @pytest.mark.asyncio
    async def test_generic_ai_service_error_returns_500(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        await _set_summary(api, book_id)

        err = AIServiceError(
            message="boom",
            error_code="AI_UNEXPECTED_ERROR",
            retryable=True,
            correlation_id="gen-1",
        )
        with patch(AI_PATCH_TARGET, new=AsyncMock(side_effect=err)):
            resp = await api.post(
                f"/api/v1/books/{book_id}/generate-toc",
                json={"question_responses": [{"question": "Q", "answer": "A"}]},
            )
        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        detail = resp.json()["detail"]
        assert detail["error_code"] == "AI_UNEXPECTED_ERROR"
        assert detail["retryable"] is True

    @pytest.mark.asyncio
    async def test_unexpected_exception_returns_500(self, auth_client_factory):
        """A non-AI exception from the AI call hits the catch-all branch."""
        api = await auth_client_factory()
        book_id = await _create_book(api)
        await _set_summary(api, book_id)

        with patch(AI_PATCH_TARGET, new=AsyncMock(side_effect=RuntimeError("kaboom"))):
            resp = await api.post(
                f"/api/v1/books/{book_id}/generate-toc",
                json={"question_responses": [{"question": "Q", "answer": "A"}]},
            )
        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert resp.json()["detail"] == "Unexpected error generating TOC"


# --------------------------------------------------------------------------- #
# GET /{book_id}/toc
# --------------------------------------------------------------------------- #


class TestGetToc:
    @pytest.mark.asyncio
    async def test_not_generated_returns_empty_structure(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)

        resp = await api.get(f"/api/v1/books/{book_id}/toc")
        assert resp.status_code == 200
        body = resp.json()
        assert body["book_id"] == book_id
        assert body["status"] == "not_generated"
        assert body["version"] == 0
        assert body["generated_at"] is None
        assert body["updated_at"] is None
        assert body["toc"]["chapters"] == []
        assert body["toc"]["total_chapters"] == 0

    @pytest.mark.asyncio
    async def test_returns_generated_toc(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        await _set_summary(api, book_id)

        with patch(AI_PATCH_TARGET, new=AsyncMock(return_value=MOCK_TOC_RESULT)):
            gen = await api.post(
                f"/api/v1/books/{book_id}/generate-toc",
                json={"question_responses": [{"question": "Q", "answer": "A"}]},
            )
            assert gen.status_code == 200

        resp = await api.get(f"/api/v1/books/{book_id}/toc")
        assert resp.status_code == 200
        body = resp.json()
        assert body["book_id"] == book_id
        assert body["status"] == "generated"
        assert body["version"] == 1
        assert body["generated_at"] is not None
        assert len(body["toc"]["chapters"]) == 2
        assert body["toc"]["total_chapters"] == 2
        assert body["toc"]["estimated_pages"] == 40

    @pytest.mark.asyncio
    async def test_book_not_found_returns_404(self, auth_client_factory):
        api = await auth_client_factory()
        resp = await api.get(f"/api/v1/books/{MISSING_BOOK_ID}/toc")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Book not found"

    @pytest.mark.asyncio
    async def test_wrong_owner_returns_403(self, auth_client_factory):
        owner = await auth_client_factory()
        book_id = await _create_book(owner)

        other = await auth_client_factory(
            overrides={"auth_id": "other-user-999", "email": "o@e.com"}
        )
        resp = await other.get(f"/api/v1/books/{book_id}/toc")
        assert resp.status_code == 403
        assert "Not authorized" in resp.json()["detail"]


# --------------------------------------------------------------------------- #
# PUT /{book_id}/toc
# --------------------------------------------------------------------------- #


class TestUpdateToc:
    @pytest.mark.asyncio
    async def test_happy_path_saves_and_increments_version(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)

        toc = {
            "chapters": [
                {"title": "Chapter One", "order": 1},
                {"title": "Chapter Two", "order": 2},
            ],
            "total_chapters": 2,
        }
        resp = await api.put(f"/api/v1/books/{book_id}/toc", json={"toc": toc})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["book_id"] == book_id
        assert body["success"] is True
        assert body["chapters_count"] == 2
        # Fresh book starts at version 1, edit increments to 2.
        assert body["version"] == 2
        assert "updated_at" in body

        # Persisted as an edit.
        get_resp = await api.get(f"/api/v1/books/{book_id}/toc")
        assert get_resp.json()["status"] == "edited"

    @pytest.mark.asyncio
    async def test_toc_not_an_object_returns_400(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        resp = await api.put(
            f"/api/v1/books/{book_id}/toc", json={"toc": ["not", "a", "dict"]}
        )
        assert resp.status_code == 400
        assert "must be provided as an object" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_chapters_not_a_list_returns_400(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        resp = await api.put(
            f"/api/v1/books/{book_id}/toc",
            json={"toc": {"chapters": {"not": "a list"}}},
        )
        assert resp.status_code == 400
        assert "Chapters must be provided as a list" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_chapter_not_an_object_returns_400(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        resp = await api.put(
            f"/api/v1/books/{book_id}/toc",
            json={"toc": {"chapters": ["just a string"]}},
        )
        assert resp.status_code == 400
        assert "must be an object" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_chapter_missing_title_returns_400(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        resp = await api.put(
            f"/api/v1/books/{book_id}/toc",
            json={"toc": {"chapters": [{"order": 1}]}},
        )
        assert resp.status_code == 400
        assert "must have a title" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_book_not_found_returns_404(self, auth_client_factory):
        api = await auth_client_factory()
        resp = await api.put(
            f"/api/v1/books/{MISSING_BOOK_ID}/toc",
            json={"toc": {"chapters": [{"title": "Ch 1"}]}},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Book not found"

    @pytest.mark.asyncio
    async def test_wrong_owner_returns_403(self, auth_client_factory):
        owner = await auth_client_factory()
        book_id = await _create_book(owner)

        other = await auth_client_factory(
            overrides={"auth_id": "other-user-999", "email": "o@e.com"}
        )
        resp = await other.put(
            f"/api/v1/books/{book_id}/toc",
            json={"toc": {"chapters": [{"title": "Ch 1"}]}},
        )
        assert resp.status_code == 403
        assert "Not authorized" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_version_conflict_returns_409(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _create_book(api)
        # Fresh book has current version 1; expected_version=99 forces a conflict.
        resp = await api.put(
            f"/api/v1/books/{book_id}/toc",
            json={
                "toc": {
                    "chapters": [{"title": "Ch 1"}],
                    "expected_version": 99,
                }
            },
        )
        assert resp.status_code == 409
        assert "modified by another user" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_invalid_book_id_returns_400(self, auth_client_factory):
        """A malformed book id raises ValueError -> generic 400 branch."""
        api = await auth_client_factory()
        resp = await api.put(
            "/api/v1/books/not-an-objectid/toc",
            json={"toc": {"chapters": [{"title": "Ch 1"}]}},
        )
        assert resp.status_code == 400
        assert "Invalid book ID format" in resp.json()["detail"]
