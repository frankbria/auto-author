"""A log written after the work is done cannot turn the work into a 500 (#847).

A chapter was created, then its access log failed and the request answered
500: the client retried and made the chapter twice. A book's audit row failed
the same way after the book existed. A draft was generated (and the AI call
paid for), then its audit row failed and the draft was thrown away. Saving the
tab state is different: the access log IS the saved state there, so its
failure must still fail the request.

Real routes and real MongoDB; the failing write is the only stand-in.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.api import dependencies
from app.db import audit_log
from app.api.endpoints import books as books_endpoint, users as users_endpoint
from app.services.chapter_access_service import chapter_access_service
from tests.test_api.test_routes.test_books_chapters_crud_coverage import create_book

pytestmark = pytest.mark.asyncio


class _Refuses:
    async def insert_one(self, *args, **kwargs):
        raise RuntimeError("the log write failed")


@pytest.fixture
def access_log_down(monkeypatch):
    async def refusing_collection():
        return _Refuses()

    monkeypatch.setattr(chapter_access_service, "_get_collection", refusing_collection)


@pytest.fixture
def audit_log_down(monkeypatch):
    """Call after creating the client: the factory stubs the audit out, and these
    tests need the real one running into a failing write."""
    def arm():
        for module in (books_endpoint, users_endpoint):
            monkeypatch.setattr(module, "audit_after_commit", dependencies.audit_after_commit)
        # The collection itself, so the routes' rows and the DB layer's own fail alike.
        monkeypatch.setattr(audit_log, "audit_logs_collection", _Refuses())

    return arm


async def test_a_chapter_is_created_once_even_when_its_access_log_fails(auth_client_factory, access_log_down):
    api = await auth_client_factory()
    book_id = await create_book(api)

    created = await api.post(f"/api/v1/books/{book_id}/chapters", json={"title": "Only once", "order": 1})

    assert created.status_code == 201, created.text
    toc = (await api.get(f"/api/v1/books/{book_id}/toc")).json()["toc"]
    assert [c["title"] for c in toc["chapters"]].count("Only once") == 1


async def test_saving_the_tab_state_still_fails_when_its_write_fails(auth_client_factory, access_log_down):
    api = await auth_client_factory()
    book_id = await create_book(api)

    saved = await api.post(
        f"/api/v1/books/{book_id}/chapters/tab-state",
        json={"active_chapter_id": "c1", "open_tab_ids": ["c1"], "tab_order": ["c1"]},
    )

    assert saved.status_code >= 500, saved.text


async def test_a_book_is_created_once_even_when_its_audit_row_fails(auth_client_factory, audit_log_down):
    api = await auth_client_factory()
    audit_log_down()

    created = await api.post("/api/v1/books/", json={"title": "Only once"})

    assert created.status_code == 201, created.text
    titles = [b["title"] for b in (await api.get("/api/v1/books/")).json()]
    assert titles.count("Only once") == 1


async def test_a_profile_update_succeeds_even_when_its_audit_row_fails(auth_client_factory, audit_log_down):
    api = await auth_client_factory()
    audit_log_down()

    updated = await api.patch("/api/v1/users/me", json={"bio": "Saved once."})

    assert updated.status_code == 200, updated.text
    assert updated.json()["bio"] == "Saved once."


async def test_a_generated_draft_is_returned_even_when_its_audit_row_fails(auth_client_factory, audit_log_down):
    api = await auth_client_factory()
    audit_log_down()
    book = {"_id": "b1", "owner_id": "test-auth-id-123", "title": "T",
            "table_of_contents": {"chapters": [{"id": "ch1", "title": "One", "level": 1, "order": 1, "subchapters": []}]}}
    draft = {"success": True, "draft": "The draft.", "metadata": {"word_count": 2}, "suggestions": []}

    with patch("app.api.endpoints.books.get_book_metadata_by_id", AsyncMock(return_value=book)), \
            patch("app.api.endpoints.books.ai_service.generate_chapter_draft", AsyncMock(return_value=draft)):
        response = await api.post(
            "/api/v1/books/b1/chapters/ch1/generate-draft",
            json={"question_responses": [{"question": "Why?", "answer": "Because."}]},
        )

    assert response.status_code == 200, response.text
    assert response.json()["draft"] == "The draft."


async def test_a_custom_validator_error_answers_422_not_500(auth_client_factory):
    # The 422 handler used to serialize the ValueError in the error's ctx and answer 500.
    api = await auth_client_factory()
    book_id = await create_book(api)

    saved = await api.post(
        f"/api/v1/books/{book_id}/chapters/tab-state",
        json={"active_chapter_id": "c1", "open_tab_ids": ["c1"], "tab_order": ["c1", "c1"]},
    )

    assert saved.status_code == 422, saved.text
    assert "duplicate entries" in saved.text
