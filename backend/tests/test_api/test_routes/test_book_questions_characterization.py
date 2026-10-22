"""
Characterization tests for the books.py -> book_questions.py extraction (issue #1126).

A *move* refactor: the pre-TOC question handlers (generate, read and save responses) were
relocated from ``app/api/endpoints/books.py`` into
``app/api/endpoints/book_questions.py`` and mounted under the same ``/books``
prefix. The invariant is route-table identity: every pre-TOC question URL is still
served with the same method, and the moved handlers now live on
``book_questions.router``. Behavioral coverage is provided by the existing
pre-TOC question and AI endpoint suites.
"""

from app.api.endpoints import book_questions, books
from app.main import app

_BASE = "/api/v1/books/{book_id}"

MOVED_ROUTES = {
    ("POST", f"{_BASE}/generate-questions"),    # generate_clarifying_questions
    ("GET", f"{_BASE}/question-responses"),     # get_question_responses
    ("PUT", f"{_BASE}/question-responses"),     # save_question_responses
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


def test_moved_question_routes_still_served_by_app():
    missing = MOVED_ROUTES - _app_routes()
    assert not missing, f"pre-TOC question routes lost or renamed by the extraction: {missing}"


def test_moved_routes_now_live_on_book_questions_router():
    owned = _router_pairs(book_questions.router)
    assert MOVED_ROUTES <= owned, (
        f"missing from book_questions.router: {MOVED_ROUTES - owned}"
    )


def test_books_router_no_longer_owns_moved_routes():
    overlap = MOVED_ROUTES & _router_pairs(books.router)
    assert not overlap, f"books.router still owns moved routes (duplicate mount): {overlap}"
