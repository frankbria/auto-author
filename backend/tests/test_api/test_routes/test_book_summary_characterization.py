"""
Characterization tests for the books.py -> book_summary.py extraction (issue #1124).

A *move* refactor: the summary handlers (read, save, patch, AI analysis) were
relocated from ``app/api/endpoints/books.py`` into
``app/api/endpoints/book_summary.py`` and mounted under the same ``/books``
prefix. The invariant is route-table identity: every summary URL is still
served with the same method, and the moved handlers now live on
``book_summary.router``. Behavioral coverage is provided by the existing
summary and AI endpoint suites.
"""

from app.api.endpoints import book_summary, books
from app.main import app

_BASE = "/api/v1/books/{book_id}"

MOVED_SUMMARY_ROUTES = {
    ("GET", f"{_BASE}/summary"),            # get_book_summary
    ("PUT", f"{_BASE}/summary"),            # update_book_summary
    ("PATCH", f"{_BASE}/summary"),          # patch_book_summary
    ("POST", f"{_BASE}/analyze-summary"),   # analyze_book_summary
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


def test_moved_summary_routes_still_served_by_app():
    missing = MOVED_SUMMARY_ROUTES - _app_routes()
    assert not missing, f"summary routes lost or renamed by the extraction: {missing}"


def test_moved_routes_now_live_on_book_summary_router():
    owned = _router_pairs(book_summary.router)
    assert MOVED_SUMMARY_ROUTES <= owned, (
        f"missing from book_summary.router: {MOVED_SUMMARY_ROUTES - owned}"
    )


def test_books_router_no_longer_owns_moved_routes():
    overlap = MOVED_SUMMARY_ROUTES & _router_pairs(books.router)
    assert not overlap, f"books.router still owns moved routes (duplicate mount): {overlap}"
