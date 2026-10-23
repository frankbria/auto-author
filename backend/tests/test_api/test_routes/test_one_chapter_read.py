"""Reading one chapter's content brings back that chapter and no other (#1041).

The chapter is picked inside the database. Bodies are written at two levels (a
chapter, or a subchapter of one), so both are covered, plus a chapter that is not
there and one nested deeper than a body can be written.
"""

import pytest
from bson import ObjectId

from app.db import base

pytestmark = pytest.mark.asyncio

API = "/api/v1/books"


def _chapter(chapter_id, body, subchapters=()):
    return {"id": chapter_id, "title": f"T {chapter_id}", "level": 1, "order": 1, "status": "draft",
            "word_count": 3, "content": body, "subchapters": list(subchapters)}


async def _book_with_nesting(api) -> str:
    created = await api.post(f"{API}/", json={"title": "Nested", "genre": "Fiction"})
    book_id = created.json()["id"]
    deep = _chapter("deep", "<p>deep</p>")
    sub = _chapter("sub", "<p>sub body</p>", [deep])
    top = _chapter("top", "<p>top body</p>", [sub, _chapter("sub2", "<p>sub2 body</p>")])
    await base.books_collection.update_one(
        {"_id": ObjectId(book_id)},
        {"$set": {"table_of_contents": {"chapters": [_chapter("first", "<p>first</p>"), top], "version": 1}}},
    )
    return book_id


async def test_a_top_level_chapter_comes_back_with_its_subchapters_counted_not_read(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _book_with_nesting(api)

    answer = await api.get(f"{API}/{book_id}/chapters/top/content")

    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["content"] == "<p>top body</p>" and body["title"] == "T top"
    assert body["metadata"]["has_subchapters"] is True and body["metadata"]["subchapter_count"] == 2


async def test_a_subchapter_comes_back_with_its_own_body(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _book_with_nesting(api)

    answer = await api.get(f"{API}/{book_id}/chapters/sub2/content")

    assert answer.status_code == 200, answer.text
    assert answer.json()["content"] == "<p>sub2 body</p>"
    assert answer.json()["metadata"]["has_subchapters"] is False


async def test_a_chapter_without_subchapters_is_found(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _book_with_nesting(api)

    answer = await api.get(f"{API}/{book_id}/chapters/first/content")

    assert answer.status_code == 200 and answer.json()["content"] == "<p>first</p>"


async def test_a_chapter_nested_below_the_depth_bodies_are_written_at_is_not_found(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _book_with_nesting(api)

    answer = await api.get(f"{API}/{book_id}/chapters/deep/content")

    assert answer.status_code == 404


@pytest.mark.parametrize("chapter_id", ["nope", "", "TOP"])
async def test_a_chapter_that_is_not_there_is_404(auth_client_factory, chapter_id):
    api = await auth_client_factory()
    book_id = await _book_with_nesting(api)

    answer = await api.get(f"{API}/{book_id}/chapters/{chapter_id or 'x'}/content")

    assert answer.status_code == 404 and answer.json()["detail"] == "Chapter not found"


async def test_a_book_with_no_table_of_contents_has_no_such_chapter(auth_client_factory):
    api = await auth_client_factory()
    book_id = (await api.post(f"{API}/", json={"title": "Empty", "genre": "Fiction"})).json()["id"]
    await base.books_collection.update_one({"_id": ObjectId(book_id)}, {"$unset": {"table_of_contents": ""}})

    answer = await api.get(f"{API}/{book_id}/chapters/top/content")

    assert answer.status_code == 404 and answer.json()["detail"] == "Chapter not found"


async def test_a_book_that_is_not_there_is_404(auth_client_factory):
    api = await auth_client_factory()

    answer = await api.get(f"{API}/{ObjectId()}/chapters/top/content")

    assert answer.status_code == 404 and answer.json()["detail"] == "Book not found"


async def test_the_reads_that_walk_the_chapter_list_leave_out_summary_history_and_interview_answers(auth_client_factory):
    from app.db.database import get_book_metadata_by_id, get_books_by_user

    api = await auth_client_factory()
    book_id = await _book_with_nesting(api)
    await base.books_collection.update_one(
        {"_id": ObjectId(book_id)},
        {"$set": {"summary_history": [{"summary": "old"}], "question_responses": {"responses": []}, "summary": "kept"}},
    )

    book = await get_book_metadata_by_id(book_id)

    assert book["summary"] == "kept" and book["owner_id"]
    assert "summary_history" not in book and "question_responses" not in book
    assert "content" not in book["table_of_contents"]["chapters"][0]
    assert all("summary_history" not in listed for listed in await get_books_by_user(book["owner_id"]))
