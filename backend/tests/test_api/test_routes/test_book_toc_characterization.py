"""
Characterization tests for the books.py -> book_toc.py extraction (issue #1125).

A *move* refactor: the TOC handlers (readiness, AI generation, read, save) were
relocated from ``app/api/endpoints/books.py`` into
``app/api/endpoints/book_toc.py`` and mounted under the same ``/books``
prefix. The invariant is route-table identity: every TOC URL is still
served with the same method, and the moved handlers now live on
``book_toc.router``. Behavioral coverage is provided by the existing
TOC and AI endpoint suites.
"""

from app.api.endpoints import book_toc, books
from app.main import app

_BASE = "/api/v1/books/{book_id}"

MOVED_ROUTES = {
    ("GET", f"{_BASE}/toc-readiness"),      # check_toc_generation_readiness
    ("POST", f"{_BASE}/generate-toc"),      # generate_table_of_contents
    ("GET", f"{_BASE}/toc"),                # get_book_toc
    ("PUT", f"{_BASE}/toc"),                # update_book_toc
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


def test_moved_toc_routes_still_served_by_app():
    missing = MOVED_ROUTES - _app_routes()
    assert not missing, f"TOC routes lost or renamed by the extraction: {missing}"


def test_moved_routes_now_live_on_book_toc_router():
    owned = _router_pairs(book_toc.router)
    assert MOVED_ROUTES <= owned, (
        f"missing from book_toc.router: {MOVED_ROUTES - owned}"
    )


def test_books_router_no_longer_owns_moved_routes():
    overlap = MOVED_ROUTES & _router_pairs(books.router)
    assert not overlap, f"books.router still owns moved routes (duplicate mount): {overlap}"
