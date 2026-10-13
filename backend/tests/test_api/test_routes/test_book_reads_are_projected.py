"""A handler reads the part of the book it uses, not the whole document (#829).

A book is one document: its chapters' bodies, its summary's history, its
interview answers. Handlers that wanted the owner, or the summary, or the
chapter list read all of it. Here the database's profiler says how many bytes
each route's read of ``books`` brought back, from a book whose bodies are 700
kilobytes and whose other large fields are another 300.
"""

from contextlib import asynccontextmanager

import pytest
from bson import ObjectId

from app.db import base

pytestmark = pytest.mark.asyncio

API = "/api/v1/books"
KB = 1000
BODY = "<p>" + "word " * 20_000 + "</p>"  # about 100 KB


async def _a_large_book(api) -> str:
    """Seven bodies of about 100 KB, 200 KB of summary history, 100 KB of interview answers."""
    created = await api.post(f"{API}/", json={"title": "A Large Book", "genre": "Fiction"})
    assert created.status_code == 201, created.text
    book_id = created.json()["id"]
    chapters = [
        {"id": f"c{n}", "title": f"Chapter {n}", "description": "", "level": 1, "order": n, "status": "draft",
         "word_count": 20_000, "content": BODY, "subchapters": []}
        for n in range(1, 7)
    ]
    chapters[0]["subchapters"] = [
        {"id": "c1a", "title": "A section", "level": 2, "order": 1, "word_count": 20_000, "content": BODY, "subchapters": []}
    ]
    await base.books_collection.update_one(
        {"_id": ObjectId(book_id)},
        {"$set": {
            "table_of_contents": {"chapters": chapters, "version": 1, "status": "edited"},
            "summary": "A book about a lighthouse keeper who writes letters to the sea. " * 5,
            "summary_history": [{"summary": "h" * 50 * KB, "timestamp": "2026-01-01T00:00:00Z"} for _ in range(4)],
            "question_responses": {"responses": [{"question": "q", "answer": "a" * 10 * KB} for _ in range(10)], "status": "completed"},
        }},
    )
    return book_id


@asynccontextmanager
async def _reads_of_the_book():
    """The finds made on ``books`` inside the block, as the database recorded them."""
    reads = []
    await base._db.command("profile", 2)
    try:
        yield reads
    finally:
        await base._db.command("profile", 0)
        reads.extend(await base._db["system.profile"].find({"ns": f"{base._db.name}.books", "op": "query"}).to_list(None))


def _bytes(reads) -> int:
    return sum(read.get("responseLength", 0) for read in reads)


# (what it is, method, path under the book, JSON body, the status it answers, the most its reads may bring back)
NO_BODIES = 350 * KB  # everything but the 700 KB of chapter bodies
ROUTES = [
    ("the book", "GET", "", None, 200, NO_BODIES),
    ("the summary", "GET", "/summary", None, 200, 230 * KB),
    ("saving the summary", "PUT", "/summary", {"summary": "A new summary of the book, long enough to be one. " * 4}, 200, 5 * KB),
    ("patching the summary", "PATCH", "/summary", {"summary": "A patched summary of the book, long enough to be one. " * 4}, 200, 230 * KB),
    ("the interview answers", "GET", "/question-responses", None, 200, 130 * KB),
    ("readiness for a table of contents", "GET", "/toc-readiness", None, 200, 5 * KB),
    ("the table of contents", "GET", "/toc", None, 200, NO_BODIES),
    ("the chapters' metadata", "GET", "/chapters/metadata", None, 200, NO_BODIES),
    ("enhancing text, refused for having none", "POST", "/chapters/c2/enhance-text", {"content": "   "}, 400, NO_BODIES),
    # A chapter's body is in the table of contents, so that is read whole; the 300 KB beside it is not.
    ("one chapter's content", "GET", "/chapters/c1a/content", None, 200, 750 * KB),
    ("several chapters' content", "POST", "/chapters/batch-content", {"chapter_ids": ["c1", "c2"]}, 200, 750 * KB),
]


@pytest.mark.parametrize("what, method, path, body, answers, at_most", ROUTES, ids=[route[0] for route in ROUTES])
async def test_the_read_brings_back_no_more_than_the_route_uses(auth_client_factory, what, method, path, body, answers, at_most):
    api = await auth_client_factory()
    book_id = await _a_large_book(api)

    async with _reads_of_the_book() as reads:
        answer = await api.request(method, f"{API}/{book_id}{path}", json=body)

    assert answer.status_code == answers, answer.text[:300]
    assert reads, "the profiler recorded no read of the book: this would pass by measuring nothing"
    assert _bytes(reads) <= at_most, f"{what}: {_bytes(reads):,} bytes read from books, in {len(reads)} read(s)"


async def test_the_book_in_these_tests_is_as_large_as_they_say(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _a_large_book(api)

    async with _reads_of_the_book() as reads:
        await base.books_collection.find_one({"_id": ObjectId(book_id)})

    assert _bytes(reads) > 950 * KB


async def test_what_the_routes_answer_is_what_they_answered_before(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _a_large_book(api)

    book = (await api.get(f"{API}/{book_id}")).json()
    summary = (await api.get(f"{API}/{book_id}/summary")).json()
    answers = (await api.get(f"{API}/{book_id}/question-responses")).json()
    ready = (await api.get(f"{API}/{book_id}/toc-readiness")).json()
    toc = (await api.get(f"{API}/{book_id}/toc")).json()
    metadata = (await api.get(f"{API}/{book_id}/chapters/metadata")).json()
    nested = (await api.get(f"{API}/{book_id}/chapters/c1a/content")).json()
    several = (await api.post(f"{API}/{book_id}/chapters/batch-content", json={"chapter_ids": ["c1", "c2"]})).json()

    assert book["title"] == "A Large Book" and book["id"] == book_id
    assert summary["summary"].startswith("A book about a lighthouse keeper") and len(summary["summary_history"]) == 4
    assert len(answers["responses"]) == 10
    assert ready["word_count"] > 30
    assert [c["id"] for c in toc["toc"]["chapters"]] == ["c1", "c2", "c3", "c4", "c5", "c6"] and toc["version"] == 1
    assert [c["id"] for c in metadata["chapters"]] == ["c1", "c1a", "c2", "c3", "c4", "c5", "c6"]
    assert metadata["chapters"][0]["word_count"] == 20_000
    assert nested["content"] == BODY
    assert several["chapters"]["c1"]["content"] == BODY and several["chapters"]["c2"]["content"] == BODY
