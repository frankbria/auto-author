"""Audit rows carry no book titles and no per-read rows (issue #787).

Uses the REAL audit_after_commit: auth_client_factory stubs it out, so it is put back.
"""

import ast
import json
from pathlib import Path

import pytest

from app.api.dependencies import audit_after_commit
from app.api.endpoints import books as books_endpoint
from app.api.endpoints import book_cover as book_cover_endpoint
from app.api.endpoints import chapter_questions as chapter_questions_endpoint
from app.api.endpoints import chapter_ai as chapter_ai_endpoint
from app.api.endpoints import users as users_endpoint
from tests.conftest import _sync_logs

TITLE = "Zebra Quokka Memoir 787"


@pytest.mark.asyncio
async def test_audit_rows_have_no_title_and_no_read_rows(
    auth_client_factory, test_book, monkeypatch
):
    api = await auth_client_factory()
    monkeypatch.setattr(users_endpoint, "audit_after_commit", audit_after_commit)
    monkeypatch.setattr(books_endpoint, "audit_after_commit", audit_after_commit)
    monkeypatch.setattr(book_cover_endpoint, "audit_after_commit", audit_after_commit)
    monkeypatch.setattr(chapter_questions_endpoint, "audit_after_commit", audit_after_commit)
    monkeypatch.setattr(chapter_ai_endpoint, "audit_after_commit", audit_after_commit)

    payload = {"title": TITLE, "genre": test_book.get("genre", "Non-Fiction")}
    resp = await api.post("/api/v1/books/", json=payload)
    assert resp.status_code == 201, resp.text
    book_id = resp.json()["id"]

    assert (await api.get(f"/api/v1/books/{book_id}")).status_code == 200
    assert (await api.get("/api/v1/users/me")).status_code == 200
    assert (await api.delete(f"/api/v1/books/{book_id}")).status_code == 204

    rows = list(_sync_logs.find({}))
    actions = {r["action"] for r in rows}
    # Vacuity guard: the writes under test really happened.
    assert {"book_create", "book_delete"} <= actions
    assert TITLE not in json.dumps(rows, default=str)
    assert not actions & {"book_view", "profile_view"}


def test_no_audit_call_site_records_a_title():
    """Chapter and book titles reach audit rows through call-site dict literals;
    most of those endpoints need an AI call to exercise, so scan the source."""
    calls, offenders = 0, []
    for path in (Path(__file__).resolve().parents[2] / "app").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", getattr(node.func, "attr", None))
            if name not in {"audit_request", "audit_after_commit", "audit_after_write", "create_audit_log"}:
                continue
            calls += 1
            for kw in node.keywords:
                if kw.arg in {"metadata", "details"}:
                    offenders += [
                        f"{path.name}:{k.lineno} {k.value}"
                        for k in ast.walk(kw.value)
                        if isinstance(k, ast.Constant) and "title" in str(k.value).lower()
                    ]
    assert calls >= 20, "scan found too few audit calls to mean anything"
    assert offenders == []
