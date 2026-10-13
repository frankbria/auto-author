"""The table of contents travels without the chapters' bodies, and a book cannot outgrow its document (#828).

GET /toc returned every chapter's HTML, and so did PUT /toc, on routes the
editor calls to draw its tabs. Nothing capped a chapter's content or a TOC
body, and a book is one MongoDB document: past sixteen megabytes every save
of it fails, the small ones too.
"""

import pytest
from bson import ObjectId

from app.db import base
from app.schemas.book import MAX_CHAPTER_CONTENT_BYTES, MAX_TOC_BODY_BYTES
from tests.test_api.test_routes.test_books_toc_coverage import (  # noqa: F401  (the fixture is autouse)
    _create_book,
    _rebind_toc_transactions,
)

pytestmark = pytest.mark.asyncio

API = "/api/v1/books"
BODIES = {"c1": "<p>first body</p>", "c1a": "<p>nested body</p>", "c1a1": "<p>deep body</p>", "c2": "<p>second body</p>"}


async def _book_with_drafts(api) -> str:
    """Two chapters, one with a subchapter and a sub-subchapter, each with a body."""
    book_id = await _create_book(api)
    deep = {"id": "c1a1", "title": "Deep", "level": 3, "order": 1, "content": BODIES["c1a1"], "subchapters": []}
    nested = {"id": "c1a", "title": "One A", "level": 2, "order": 1, "content": BODIES["c1a"], "word_count": 2, "subchapters": [deep]}
    chapters = [
        {"id": "c1", "title": "One", "description": "d", "level": 1, "order": 1, "content": BODIES["c1"],
         "status": "in-progress", "word_count": 2, "subchapters": [nested]},
        {"id": "c2", "title": "Two", "description": "", "level": 1, "order": 2, "content": BODIES["c2"], "subchapters": []},
    ]
    await base.books_collection.update_one(
        {"_id": ObjectId(book_id)}, {"$set": {"table_of_contents": {"chapters": chapters, "version": 1}}}
    )
    return book_id


def _every_chapter(chapters):
    for chapter in chapters:
        yield chapter
        yield from _every_chapter(chapter.get("subchapters") or [])


async def _stored_bodies(book_id: str) -> dict:
    book = await base.books_collection.find_one({"_id": ObjectId(book_id)})
    return {c["id"]: c.get("content") for c in _every_chapter(book["table_of_contents"]["chapters"])}


class TestTheTableOfContentsHasNoBodies:
    async def test_reading_it_returns_no_content_at_any_depth(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _book_with_drafts(api)

        answer = await api.get(f"{API}/{book_id}/toc")

        assert answer.status_code == 200
        chapters = list(_every_chapter(answer.json()["toc"]["chapters"]))
        assert [c["id"] for c in chapters] == ["c1", "c1a", "c1a1", "c2"]
        assert [c for c in chapters if "content" in c] == []
        assert "body" not in answer.text
        # What the tabs do read is still there.
        assert chapters[0]["status"] == "in-progress" and chapters[0]["word_count"] == 2
        assert chapters[0]["title"] == "One" and chapters[1]["title"] == "One A"

    async def test_saving_it_returns_no_content_and_loses_none(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _book_with_drafts(api)
        sent = (await api.get(f"{API}/{book_id}/toc")).json()["toc"]
        sent["chapters"][1]["title"] = "Two, renamed"

        answer = await api.put(f"{API}/{book_id}/toc", json={"toc": sent})

        assert answer.status_code == 200, answer.text
        chapters = list(_every_chapter(answer.json()["toc"]["chapters"]))
        assert [c["title"] for c in chapters] == ["One", "One A", "Deep", "Two, renamed"]
        assert [c for c in chapters if "content" in c] == []
        assert "body" not in answer.text
        # Sending back what was read, which has no bodies now, erased none of them.
        assert await _stored_bodies(book_id) == BODIES

    async def test_a_chapters_body_is_still_read_from_its_own_route(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _book_with_drafts(api)

        answer = await api.get(f"{API}/{book_id}/chapters/c1a/content")

        assert answer.status_code == 200
        assert answer.json()["content"] == BODIES["c1a"]


class TestAChapterHasALargestSize:
    async def test_content_over_the_limit_is_refused_and_what_was_there_is_kept(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _book_with_drafts(api)

        answer = await api.patch(f"{API}/{book_id}/chapters/c2/content", json={"content": "a" * (MAX_CHAPTER_CONTENT_BYTES + 1)})

        assert answer.status_code == 413, answer.text[:200]
        assert "too long" in answer.json()["detail"]
        assert await _stored_bodies(book_id) == BODIES

    async def test_content_at_the_limit_is_saved(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _book_with_drafts(api)

        answer = await api.patch(f"{API}/{book_id}/chapters/c2/content", json={"content": "a" * MAX_CHAPTER_CONTENT_BYTES})

        assert answer.status_code == 200, answer.text[:200]
        assert len((await _stored_bodies(book_id))["c2"]) == MAX_CHAPTER_CONTENT_BYTES

    async def test_the_limit_is_in_bytes_which_is_what_the_database_counts(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _book_with_drafts(api)
        fewer_characters_than_the_limit = "é" * (MAX_CHAPTER_CONTENT_BYTES // 2 + 1)

        answer = await api.patch(f"{API}/{book_id}/chapters/c2/content", json={"content": fewer_characters_than_the_limit})

        assert answer.status_code == 413


class TestABookAtTheDatabasesLimit:
    """Its chapters are all in one document, and MongoDB refuses one over sixteen megabytes.
    That takes more full-size chapters than anyone writes, so there is no second limit to
    hit first: the save that would cross it is refused as too large, not as a server error."""

    @pytest.fixture
    async def a_full_book(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _book_with_drafts(api)
        await base.books_collection.update_one({"_id": ObjectId(book_id)}, {"$set": {"filler": "f" * 16_300_000}})
        return api, book_id

    async def test_a_save_that_would_cross_it_is_refused_as_too_large(self, a_full_book):
        api, book_id = a_full_book

        answer = await api.patch(f"{API}/{book_id}/chapters/c2/content", json={"content": "a" * MAX_CHAPTER_CONTENT_BYTES})

        assert answer.status_code == 413, answer.text[:300]
        assert "book" in answer.json()["detail"]
        assert await _stored_bodies(book_id) == BODIES

    async def test_a_small_save_to_the_same_book_still_lands(self, a_full_book):
        api, book_id = a_full_book

        answer = await api.patch(f"{API}/{book_id}/chapters/c2/content", json={"content": "<p>second</p>"})

        assert answer.status_code == 200, answer.text[:300]

    async def test_so_is_a_table_of_contents_that_would_cross_it(self, a_full_book):
        api, book_id = a_full_book
        sent = (await api.get(f"{API}/{book_id}/toc")).json()["toc"]
        sent["chapters"][1]["description"] = "d" * 600_000

        answer = await api.put(f"{API}/{book_id}/toc", json={"toc": sent})

        assert answer.status_code == 413, answer.text[:300]
        assert "book" in answer.json()["detail"]


class TestATableOfContentsBodyHasALargestSize:
    async def test_one_over_the_limit_is_refused_and_what_was_there_is_kept(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _book_with_drafts(api)
        sent = (await api.get(f"{API}/{book_id}/toc")).json()["toc"]
        sent["chapters"][1]["description"] = "d" * MAX_TOC_BODY_BYTES

        answer = await api.put(f"{API}/{book_id}/toc", json={"toc": sent})

        assert answer.status_code == 413, answer.text[:200]
        assert "too large" in answer.json()["detail"]
        stored = await base.books_collection.find_one({"_id": ObjectId(book_id)})
        assert stored["table_of_contents"]["chapters"][1]["description"] == ""
        assert await _stored_bodies(book_id) == BODIES

    async def test_an_ordinary_one_is_saved(self, auth_client_factory):
        api = await auth_client_factory()
        book_id = await _book_with_drafts(api)
        sent = (await api.get(f"{API}/{book_id}/toc")).json()["toc"]
        sent["chapters"][1]["description"] = "d" * 2000

        answer = await api.put(f"{API}/{book_id}/toc", json={"toc": sent})

        assert answer.status_code == 200, answer.text[:200]
