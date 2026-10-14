"""A database that cannot be asked is not a book that is not there (#849).

The book lookups caught every exception and returned None, so an outage was
answered 404: the client stopped retrying and the user was told their book was
gone. Only a malformed id names no book. Real routes and real MongoDB; the books
collection that refuses to answer is the only stand-in, and it raises pymongo's
own error.
"""

import pytest
from pymongo.errors import ServerSelectionTimeoutError

from app.db import book as book_db
from tests.test_api.test_routes.test_books_chapters_crud_coverage import create_book

pytestmark = pytest.mark.asyncio


class _Unreachable:
    def __init__(self, real):
        self._real = real

    def __getattr__(self, name):
        return getattr(self._real, name)

    async def find_one(self, *args, **kwargs):
        raise ServerSelectionTimeoutError("no primary available")


@pytest.mark.parametrize("path", [
    "",
    "/summary",
    "/toc",
    "/chapters/metadata",
    "/chapters/ch1",
    "/chapters/ch1/content",
    "/export/pdf",
])
async def test_an_unreachable_database_is_not_answered_404(auth_client_factory, monkeypatch, path):
    api = await auth_client_factory()
    book_id = await create_book(api)
    monkeypatch.setattr(book_db, "books_collection", _Unreachable(book_db.books_collection))

    response = await api.get(f"/api/v1/books/{book_id}{path}")

    assert response.status_code >= 500, (response.status_code, response.text)


async def test_a_malformed_id_is_still_404(auth_client_factory):
    api = await auth_client_factory()

    response = await api.get("/api/v1/books/not-an-object-id/toc")

    assert response.status_code in (400, 404), response.text
