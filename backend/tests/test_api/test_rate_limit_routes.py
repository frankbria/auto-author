"""
Issue #199: the suite globally no-ops `get_rate_limiter` (see
`tests/conftest.py::noop_rate_limiter`) so that generation/export/CRUD tests
aren't tripped by real limits. That's correct for most tests, but it means no
test in the whole suite drives a real HTTP 429 out of the production rate
limiter through an actual route — a `Depends(get_rate_limiter(...))` could be
silently deleted from any endpoint and every test would stay green.

This file uses the `arm_real_rate_limiter` fixture (added for #199) to
re-install the genuine limiter for one request path at a time, against real
Mongo-backed counting (`app/db/usage.py::increment_usage`), and asserts the
production 429 contract (status, headers, message).

Class 1 (below): one representative route per "family" of rate-limited
endpoint (AI generation, TOC analysis, export, avatar upload) actually 429s
at the configured cap.

Class 2 (`TestRateLimiterWiringCompleteness`): walks the live FastAPI app and
asserts that *every* production route which is supposed to declare
`Depends(get_rate_limiter(...))` still does -- so a future refactor that
drops the dependency from any one of them fails a test immediately, rather
than only being caught the next time issue #199 happens.
"""
import io

import pytest
from unittest.mock import patch, AsyncMock
from PIL import Image
from bson import ObjectId

from app.db import base
from app.main import app


# A summary comfortably above the PUT /summary 30-char minimum (mirrors
# tests/test_api/test_routes/test_books_pretoc_coverage.py::GOOD_SUMMARY).
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


def _ai_question_dicts(n: int = 2):
    """Deterministic AI question payload (mirrors
    tests/test_api/test_routes/test_books_chapter_questions_coverage.py)."""
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


async def _create_book(api, *, with_summary: bool = False, title: str = "Rate Limit Book"):
    resp = await api.post(
        "/api/v1/books/",
        json={"title": title, "genre": "Non-fiction", "target_audience": "Adults"},
    )
    assert resp.status_code == 201, resp.text
    book_id = resp.json()["id"]
    if with_summary:
        rs = await api.put(
            f"/api/v1/books/{book_id}/summary", json={"summary": GOOD_SUMMARY}
        )
        assert rs.status_code == 200, rs.text
    return book_id


async def _seed_toc(book_id: str, toc: dict) -> None:
    """Write a table_of_contents directly to the DB in production shape
    (mirrors tests/test_api/test_export_endpoints.py::_seed_toc)."""
    await base.books_collection.update_one(
        {"_id": ObjectId(book_id)}, {"$set": {"table_of_contents": toc}}
    )


def _small_toc():
    return {
        "chapters": [
            {
                "id": "ch1",
                "title": "Introduction",
                "description": "Getting started",
                "content": "<h1>Introduction</h1><p>Welcome to this test book.</p>",
                "order": 1,
                "level": 1,
                "parent_id": None,
                "status": "completed",
                "word_count": 10,
                "subchapters": [],
            }
        ],
        "total_chapters": 1,
        "estimated_pages": 1,
        "status": "edited",
    }


def _jpeg_bytes() -> io.BytesIO:
    img = Image.new("RGB", (200, 200), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf


def _assert_429(response):
    assert response.status_code == 429, response.text
    assert response.headers["X-RateLimit-Remaining"] == "0"
    assert "Retry-After" in response.headers
    assert "rate limit" in response.json()["detail"].lower()


# --------------------------------------------------------------------------- #
# Class 1: real 429s at representative routes
# --------------------------------------------------------------------------- #
class TestRateLimitDrivesReal429:
    @pytest.mark.asyncio
    async def test_chapter_generate_questions_rate_limited(
        self, auth_client_factory, arm_real_rate_limiter
    ):
        """Pins issue #199 on the AI-generation family: if
        `Depends(get_rate_limiter(...))` were removed from
        `generate_chapter_questions` (books.py), the 3rd request below would
        return 200 instead of 429 and this test would fail.
        """
        api = await auth_client_factory()
        book_id = await _create_book(api)
        chapter_id = "chapter-1"

        arm_real_rate_limiter(2)

        url = f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions"
        with patch(
            "app.services.ai_service.ai_service.generate_chapter_questions",
            new=AsyncMock(return_value=_ai_question_dicts()),
        ):
            r1 = await api.post(url, json={"count": 2})
            assert r1.status_code == 200, r1.text
            r2 = await api.post(url, json={"count": 2})
            assert r2.status_code == 200, r2.text
            r3 = await api.post(url, json={"count": 2})

        _assert_429(r3)

    @pytest.mark.asyncio
    async def test_analyze_summary_rate_limited(
        self, auth_client_factory, arm_real_rate_limiter
    ):
        """Pins issue #199 on the TOC-analysis family: if
        `Depends(get_rate_limiter(...))` were removed from
        `analyze_book_summary` (books.py), the 3rd request below would return
        200 instead of 429 and this test would fail.
        """
        api = await auth_client_factory()
        book_id = await _create_book(api, with_summary=True)

        arm_real_rate_limiter(2)

        url = f"/api/v1/books/{book_id}/analyze-summary"
        with patch(
            "app.services.ai_service.ai_service.analyze_summary_for_toc",
            new=AsyncMock(return_value=dict(ANALYSIS_OK)),
        ):
            r1 = await api.post(url)
            assert r1.status_code == 200, r1.text
            r2 = await api.post(url)
            assert r2.status_code == 200, r2.text
            r3 = await api.post(url)

        _assert_429(r3)

    @pytest.mark.asyncio
    async def test_export_pdf_rate_limited(
        self, auth_client_factory, arm_real_rate_limiter
    ):
        """Pins issue #199 on the export family: if
        `Depends(get_rate_limiter(...))` were removed from
        `export_book_pdf` (export.py), the 3rd request below would return 200
        instead of 429 and this test would fail. Real PDF generation (no
        mocking of export_service).
        """
        api = await auth_client_factory()
        book_id = await _create_book(api)
        await _seed_toc(book_id, _small_toc())

        arm_real_rate_limiter(2)

        url = f"/api/v1/books/{book_id}/export/pdf"
        r1 = await api.get(url)
        assert r1.status_code == 200, r1.text
        r2 = await api.get(url)
        assert r2.status_code == 200, r2.text
        r3 = await api.get(url)

        _assert_429(r3)

    @pytest.mark.asyncio
    async def test_avatar_upload_rate_limited(
        self, auth_client_factory, arm_real_rate_limiter
    ):
        """Pins issue #199 on the avatar-upload family: if
        `Depends(get_rate_limiter(...))` were removed from
        `upload_profile_picture` (users.py), the 3rd request below would
        return 200 instead of 429 and this test would fail.
        """
        api = await auth_client_factory()

        arm_real_rate_limiter(2)

        upload_service = AsyncMock()
        upload_service.process_and_save_profile_picture.return_value = (
            "/uploads/profile_pictures/new.jpg"
        )
        upload_service.delete_profile_picture.return_value = None

        url = "/api/v1/users/me/avatar"
        with patch(
            "app.services.file_upload_service.FileUploadService",
            return_value=upload_service,
        ):
            r1 = await api.post(
                url, files={"file": ("avatar.jpg", _jpeg_bytes(), "image/jpeg")}
            )
            assert r1.status_code == 200, r1.text
            r2 = await api.post(
                url, files={"file": ("avatar.jpg", _jpeg_bytes(), "image/jpeg")}
            )
            assert r2.status_code == 200, r2.text
            r3 = await api.post(
                url, files={"file": ("avatar.jpg", _jpeg_bytes(), "image/jpeg")}
            )

        _assert_429(r3)


# --------------------------------------------------------------------------- #
# Class 2: wiring completeness across the whole app
# --------------------------------------------------------------------------- #

# (METHOD, full registered path) pairs that MUST declare
# Depends(get_rate_limiter(...)) in production. Verified at 2026-07-13 by
# walking the live `app` object (see `_effective_rate_limited_routes` below);
# re-derive by running that walk against `app.main.app` if this list and the
# live app ever disagree -- that disagreement is itself the #199 regression
# this test exists to catch.
EXPECTED_RATE_LIMITED_ROUTES = {
    # users.py
    ("GET", "/api/v1/users/me"),
    ("PATCH", "/api/v1/users/me"),
    ("DELETE", "/api/v1/users/me"),
    ("POST", "/api/v1/users/me/avatar"),
    # export.py (mounted under /api/v1/books)
    ("GET", "/api/v1/books/{book_id}/export/pdf"),
    ("GET", "/api/v1/books/{book_id}/export/docx"),
    ("GET", "/api/v1/books/{book_id}/export/epub"),
    ("GET", "/api/v1/books/{book_id}/export/markdown"),
    # billing.py
    ("POST", "/api/v1/billing/checkout"),
    ("POST", "/api/v1/billing/portal"),
    # books.py
    ("POST", "/api/v1/books/"),
    ("GET", "/api/v1/books/"),
    ("GET", "/api/v1/books/{book_id}"),
    ("PUT", "/api/v1/books/{book_id}"),
    ("PATCH", "/api/v1/books/{book_id}"),
    ("DELETE", "/api/v1/books/{book_id}"),
    ("POST", "/api/v1/books/{book_id}/analyze-summary"),
    ("POST", "/api/v1/books/{book_id}/generate-questions"),
    ("POST", "/api/v1/books/{book_id}/generate-toc"),
    ("POST", "/api/v1/books/{book_id}/chapters/{chapter_id}/generate-questions"),
    (
        "POST",
        "/api/v1/books/{book_id}/chapters/{chapter_id}/questions/{question_id}/regenerate",
    ),
    ("POST", "/api/v1/books/{book_id}/chapters/{chapter_id}/regenerate-questions"),
    ("POST", "/api/v1/books/{book_id}/chapters/{chapter_id}/generate-draft"),
    ("POST", "/api/v1/books/{book_id}/chapters/{chapter_id}/transform-style"),
    ("POST", "/api/v1/books/{book_id}/chapters/{chapter_id}/enhance-text"),
    ("POST", "/api/v1/books/{book_id}/chapters/{chapter_id}/enhance-transcription"),
}

assert len(EXPECTED_RATE_LIMITED_ROUTES) == 26


def _walk_effective_routes(node):
    """Recursively resolve the app's route tree to (method, full_path,
    dependant) triples.

    Newer FastAPI (0.138+) doesn't flatten `include_router` calls into
    `app.routes` directly -- each `include_router` call is represented by an
    opaque `fastapi.routing._IncludedRouter` wrapper, and the real,
    prefix-resolved routes only materialize via its
    `effective_candidates()` / `effective_low_priority_routes()` methods as
    `fastapi.routing._EffectiveRouteContext` objects (which carry the final
    `path_format` and `dependant`). This walks that structure so the test
    reflects the actual live route table rather than a hardcoded guess.
    """
    from fastapi.routing import _IncludedRouter, _EffectiveRouteContext

    if isinstance(node, _IncludedRouter):
        for child in node.effective_candidates():
            yield from _walk_effective_routes(child)
        for child in node.effective_low_priority_routes():
            yield from _walk_effective_routes(child)
    elif isinstance(node, _EffectiveRouteContext):
        yield node
    # else: not a route-bearing node (e.g. a plain starlette Mount) -- skip.


def _route_dependency_calls():
    """Map every (method, path) on the live `app` to the SET of dependency
    callables declared directly on that route's dependant.

    Deliberately does NOT identify "the rate limiter" via
    `deps.get_rate_limiter()`'s *current* value (see
    `_shared_rate_limiter_call` below for why that's unsafe here) -- it just
    returns the raw per-route dependency sets so the caller can derive the
    shared limiter empirically.
    """
    calls_by_route = {}
    for top_level_route in app.routes:
        for ctx in _walk_effective_routes(top_level_route):
            if not ctx.dependant:
                continue
            calls = {dep.call for dep in ctx.dependant.dependencies}
            for method in ctx.methods:
                if method == "HEAD":
                    continue
                calls_by_route[(method, ctx.path_format)] = calls
    return calls_by_route


def _shared_rate_limiter_call(calls_by_route):
    """Derive the shared `noop_rate_limiter` callable from the routes
    themselves: the union of every route's dependency callables, narrowed by
    name. Routes capture the shared noop exactly once at import time, so this
    yields exactly one function object; using the union (not an intersection
    over the expected routes) keeps the derivation working even when a route
    has LOST the dependency, so the missing-route assertion can name it.

    This intentionally avoids reading `deps.get_rate_limiter()` directly:
    some unrelated test modules (`test_billing_checkout.py`,
    `test_billing_portal.py`) do `from tests.conftest import _sync_users`,
    which -- because `tests/` has no `__init__.py` while pytest itself loads
    `conftest.py` under the bare module name `conftest` -- causes conftest.py
    to execute a SECOND time under the distinct module identity
    `tests.conftest`. That second execution rebinds
    `app.api.dependencies.get_rate_limiter` to a brand-new `noop_rate_limiter`
    function object that no route was ever built against, so
    `deps.get_rate_limiter()` is not a reliable identity source once those
    modules have been collected in the same pytest session. Deriving the
    identity from the routes themselves (by name, not by importing conftest)
    sidesteps that landmine entirely.
    """
    return {
        c
        for calls in calls_by_route.values()
        for c in calls
        if getattr(c, "__name__", "") == "noop_rate_limiter"
    }


class TestRateLimiterWiringCompleteness:
    def test_every_expected_route_still_declares_the_rate_limiter(self):
        """Regression guard for issue #199: walks the live app and confirms
        every route in EXPECTED_RATE_LIMITED_ROUTES still carries
        Depends(get_rate_limiter(...)). If a future change drops the
        dependency from any one of these 26 routes, this test names exactly
        which (method, path) lost it.
        """
        calls_by_route = _route_dependency_calls()
        shared = _shared_rate_limiter_call(calls_by_route)
        assert len(shared) == 1, (
            "Expected exactly one noop_rate_limiter callable across the live "
            f"app's routes; found {shared}. The conftest limiter swap may "
            "have changed shape."
        )
        limiter = next(iter(shared))

        missing = {
            pair
            for pair in EXPECTED_RATE_LIMITED_ROUTES
            if limiter not in calls_by_route.get(pair, set())
        }
        assert not missing, (
            "The following routes no longer declare "
            f"Depends(get_rate_limiter(...)): {sorted(missing)}"
        )

    def test_no_unexpected_routes_appeared(self):
        """Companion assertion: if a new rate-limited route is added, this
        list (and its docstring provenance note) should be updated
        deliberately rather than silently drifting.
        """
        calls_by_route = _route_dependency_calls()
        limiter = next(iter(_shared_rate_limiter_call(calls_by_route)))

        actual = {
            pair
            for pair, calls in calls_by_route.items()
            if limiter in calls
        }
        unexpected = actual - EXPECTED_RATE_LIMITED_ROUTES
        assert not unexpected, (
            "Found rate-limited routes not accounted for in "
            f"EXPECTED_RATE_LIMITED_ROUTES: {sorted(unexpected)}. Update the "
            "list (and re-verify the count) if this is intentional."
        )
