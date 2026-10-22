"""
Characterization tests for the books.py -> chapter_questions.py extraction (issue #857).

A *move* refactor: the chapter-question handlers were relocated from
``app/api/endpoints/books.py`` into ``app/api/endpoints/chapter_questions.py``
and mounted under the same ``/books`` prefix. The invariant is route-table
identity: every question URL is still served with the same method, and the
moved handlers now live on ``chapter_questions.router``. Behavioral coverage
is provided by the existing question suites.
"""

from app.api.endpoints import books, chapter_questions
from app.main import app

_BASE = "/api/v1/books/{book_id}/chapters/{chapter_id}"

MOVED_QUESTION_ROUTES = {
    ("POST", f"{_BASE}/generate-questions"),                       # generate_chapter_questions
    ("GET", f"{_BASE}/questions"),                                 # list_chapter_questions
    ("PUT", f"{_BASE}/questions/{{question_id}}/response"),        # save_question_response
    ("GET", f"{_BASE}/questions/{{question_id}}/response"),        # get_question_response
    ("POST", f"{_BASE}/questions/{{question_id}}/rating"),         # rate_question
    ("POST", f"{_BASE}/questions/{{question_id}}/regenerate"),     # regenerate_single_question
    ("GET", f"{_BASE}/question-progress"),                         # get_chapter_question_progress
    ("POST", f"{_BASE}/regenerate-questions"),                     # regenerate_chapter_questions
    ("POST", f"{_BASE}/questions/responses/batch"),                # save_question_responses_batch_endpoint
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
    missing = MOVED_QUESTION_ROUTES - _app_routes()
    assert not missing, f"question routes lost or renamed by the extraction: {missing}"


def test_moved_routes_now_live_on_chapter_questions_router():
    owned = _router_pairs(chapter_questions.router)
    assert MOVED_QUESTION_ROUTES <= owned, (
        f"missing from chapter_questions.router: {MOVED_QUESTION_ROUTES - owned}"
    )


def test_books_router_no_longer_owns_moved_routes():
    overlap = MOVED_QUESTION_ROUTES & _router_pairs(books.router)
    assert not overlap, f"books.router still owns moved routes (duplicate mount): {overlap}"
