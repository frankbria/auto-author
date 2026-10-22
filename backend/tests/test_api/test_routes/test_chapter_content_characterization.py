"""
Characterization tests for the books.py -> chapter_content.py extraction (issue #1122).

A *move* refactor: the chapter-content handlers were relocated from
``app/api/endpoints/books.py`` into ``app/api/endpoints/chapter_content.py``
and mounted under the same ``/books`` prefix. The invariant is route-table
identity: every content URL is still served with the same method, and the
moved handlers now live on ``chapter_content.router``. Behavioral coverage
is provided by the existing content suites.
"""

from app.api.endpoints import books, chapter_content
from app.main import app

_BASE = "/api/v1/books/{book_id}/chapters/{chapter_id}"

MOVED_CONTENT_ROUTES = {
    ("GET", f"{_BASE}/content"),                                   # get_chapter_content
    ("PATCH", f"{_BASE}/content"),                                 # update_chapter_content
    ("GET", f"{_BASE}/analytics"),                                 # get_chapter_analytics
    ("POST", "/api/v1/books/{book_id}/chapters/batch-content"),    # batch_get_chapter_content
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


def test_moved_content_routes_still_served_by_app():
    missing = MOVED_CONTENT_ROUTES - _app_routes()
    assert not missing, f"content routes lost or renamed by the extraction: {missing}"


def test_moved_routes_now_live_on_chapter_content_router():
    owned = _router_pairs(chapter_content.router)
    assert MOVED_CONTENT_ROUTES <= owned, (
        f"missing from chapter_content.router: {MOVED_CONTENT_ROUTES - owned}"
    )


def test_books_router_no_longer_owns_moved_routes():
    overlap = MOVED_CONTENT_ROUTES & _router_pairs(books.router)
    assert not overlap, f"books.router still owns moved routes (duplicate mount): {overlap}"
