"""
Characterization tests for the books.py -> chapter_ai.py extraction (issue #1123).

A *move* refactor: the chapter AI handlers (draft, style, enhance, transcription) were relocated from
``app/api/endpoints/books.py`` into ``app/api/endpoints/chapter_ai.py``
and mounted under the same ``/books`` prefix. The invariant is route-table
identity: every AI URL is still served with the same method, and the
moved handlers now live on ``chapter_ai.router``. Behavioral coverage
is provided by the existing AI endpoint suites.
"""

from app.api.endpoints import books, chapter_ai
from app.main import app

_BASE = "/api/v1/books/{book_id}/chapters/{chapter_id}"

MOVED_AI_ROUTES = {
    ("POST", f"{_BASE}/generate-draft"),         # generate_chapter_draft
    ("POST", f"{_BASE}/transform-style"),        # transform_chapter_style
    ("POST", f"{_BASE}/enhance-text"),           # enhance_chapter_text
    ("POST", f"{_BASE}/enhance-transcription"),  # enhance_chapter_transcription
}


def _app_routes():
    """(METHOD, full-path) pairs served, via the OpenAPI schema (see the chapters twin)."""
    return {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
    }


def _router_pairs(router):
    return {
        (method, f"/api/v1/books{route.path}")
        for route in router.routes
        for method in getattr(route, "methods", ()) or ()
    }


def test_moved_ai_routes_still_served_by_app():
    missing = MOVED_AI_ROUTES - _app_routes()
    assert not missing, f"AI routes lost or renamed by the extraction: {missing}"


def test_moved_routes_now_live_on_chapter_ai_router():
    owned = _router_pairs(chapter_ai.router)
    assert MOVED_AI_ROUTES <= owned, (
        f"missing from chapter_ai.router: {MOVED_AI_ROUTES - owned}"
    )


def test_books_router_no_longer_owns_moved_routes():
    overlap = MOVED_AI_ROUTES & _router_pairs(books.router)
    assert not overlap, f"books.router still owns moved routes (duplicate mount): {overlap}"
