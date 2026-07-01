"""
Characterization tests for the books.py -> chapters.py extraction (issue #94).

This is a *move* refactor: the chapter-management handlers were relocated from
``app/api/endpoints/books.py`` into ``app/api/endpoints/chapters.py`` and mounted
under the same ``/books`` prefix. The one invariant unique to this refactor —
and not asserted by any existing test — is **route-table identity**: every
chapter URL must still be served, with the same method, and the moved handlers
must now live on ``chapters.router``.

Behavioral coverage (status codes, response shapes, auth, not-owned, 404) is
provided by the existing suites, which pass both before and after the move:
    - test_books_chapters_crud_coverage.py   (create/get/update/delete/list/metadata/bulk)
    - test_books_chapter_content_coverage.py (content/tab-state)
"""

from app.api.endpoints import chapters
from app.main import app


# The 9 handlers moved out of books.py into chapters.py, by (method, path)
# relative to the /books mount prefix.
MOVED_CHAPTER_ROUTES = {
    ("POST", "/api/v1/books/{book_id}/chapters"),                 # create_chapter
    ("GET", "/api/v1/books/{book_id}/chapters"),                  # list_chapters
    ("GET", "/api/v1/books/{book_id}/chapters/metadata"),         # get_chapters_metadata
    ("GET", "/api/v1/books/{book_id}/chapters/tab-state"),        # get_tab_state
    ("POST", "/api/v1/books/{book_id}/chapters/tab-state"),       # save_tab_state
    ("PATCH", "/api/v1/books/{book_id}/chapters/bulk-status"),    # update_chapter_status_bulk
    ("GET", "/api/v1/books/{book_id}/chapters/{chapter_id}"),     # get_chapter
    ("PUT", "/api/v1/books/{book_id}/chapters/{chapter_id}"),     # update_chapter
    ("DELETE", "/api/v1/books/{book_id}/chapters/{chapter_id}"),  # delete_chapter
}


def _app_routes():
    """Set of (method, full-path) pairs registered on the app."""
    pairs = set()
    for route in app.routes:
        methods = getattr(route, "methods", None)
        if not methods:
            continue
        for method in methods:
            pairs.add((method, route.path))
    return pairs


def test_moved_chapter_routes_still_served_by_app():
    """Every moved chapter route is still reachable under the same URL/method."""
    app_pairs = _app_routes()
    missing = MOVED_CHAPTER_ROUTES - app_pairs
    assert not missing, f"chapter routes lost or renamed by the extraction: {missing}"


def test_moved_routes_now_live_on_chapters_router():
    """The 9 moved handlers are owned by chapters.router, not books.router."""
    owned = set()
    for route in chapters.router.routes:
        for method in getattr(route, "methods", ()) or ():
            # chapters.router paths are prefix-relative (mounted at /books elsewhere)
            owned.add((method, f"/api/v1/books{route.path}"))
    assert MOVED_CHAPTER_ROUTES <= owned, (
        f"expected chapters.router to own the moved routes; missing: "
        f"{MOVED_CHAPTER_ROUTES - owned}"
    )


def test_metadata_and_tab_state_registered_before_parameterized_route():
    """
    Literal sub-paths must precede /chapters/{chapter_id} so FastAPI does not
    match them as chapter_id='metadata'/'tab-state'. Guards the route-ordering
    bug that #121 previously fixed.
    """
    # Only the *GET* literal sub-paths need ordering: they share the GET method
    # with GET /chapters/{chapter_id}, so a wrong order makes them match as
    # chapter_id='metadata'/'tab-state'. /chapters/bulk-status is PATCH-only
    # (no PATCH /{chapter_id} exists), so its order relative to {chapter_id} is
    # irrelevant — it sits after {chapter_id} here, exactly as in the original.
    order = [r.path for r in chapters.router.routes if getattr(r, "methods", None)]
    param_path = "/{book_id}/chapters/{chapter_id}"
    assert param_path in order, f"{param_path} not registered on chapters.router"
    param = order.index(param_path)
    for literal in ("/{book_id}/chapters/metadata", "/{book_id}/chapters/tab-state"):
        assert literal in order, f"{literal} not registered on chapters.router"
        assert order.index(literal) < param, (
            f"{literal} must be registered before /chapters/{{chapter_id}}"
        )


def test_books_router_no_longer_owns_moved_routes():
    """books.router must not still define the moved chapter handlers (no dupes)."""
    from app.api.endpoints import books

    books_pairs = set()
    for route in books.router.routes:
        for method in getattr(route, "methods", ()) or ():
            books_pairs.add((method, f"/api/v1/books{route.path}"))
    overlap = MOVED_CHAPTER_ROUTES & books_pairs
    assert not overlap, f"books.router still owns moved routes (duplicate mount): {overlap}"
