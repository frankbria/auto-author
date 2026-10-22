"""
Characterization tests for the books.py -> book_cover.py extraction (issue #1133).

A *move* refactor: ``upload_book_cover_image`` was relocated from
``app/api/endpoints/books.py`` into ``app/api/endpoints/book_cover.py`` and mounted
under the same ``/books`` prefix. The invariant is route-table identity: the cover
URL is still served with the same method, and the handler now lives on
``book_cover.router``. Behavioral coverage is provided by the existing cover and
image-URL suites.
"""

from app.api.endpoints import book_cover, books
from app.main import app

MOVED_ROUTES = {
    ("POST", "/api/v1/books/{book_id}/cover-image"),  # upload_book_cover_image
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


def test_cover_route_still_served_by_app():
    missing = MOVED_ROUTES - _app_routes()
    assert not missing, f"cover route lost or renamed by the extraction: {missing}"


def test_cover_route_now_lives_on_book_cover_router():
    owned = _router_pairs(book_cover.router)
    assert MOVED_ROUTES <= owned, f"missing from book_cover.router: {MOVED_ROUTES - owned}"


def test_books_router_no_longer_owns_cover_route():
    overlap = MOVED_ROUTES & _router_pairs(books.router)
    assert not overlap, f"books.router still owns the cover route (duplicate mount): {overlap}"
