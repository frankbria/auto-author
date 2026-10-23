"""A handler reads the part of the book it uses, not the whole document (#829).

A book is one document: its chapters' bodies, its summary's history, its
interview answers. Handlers that wanted the owner, or the summary, or the
chapter list read all of it. Here the database's profiler says how many bytes
each route's read of ``books`` brought back, from a book whose bodies are 700
kilobytes and whose other large fields are another 300.
"""

from contextlib import asynccontextmanager
from io import BytesIO
from unittest.mock import AsyncMock

import pytest
from bson import ObjectId

from app.api.endpoints import chapter_ai as chapter_ai_endpoint
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
    # The profiler's record outlives the block that made it. Each test starts with an empty
    # database, so nothing is left from another test; this is for a second block in the same one.
    await base._db["system.profile"].drop()
    await base._db.command("profile", 2)
    try:
        yield reads
    finally:
        await base._db.command("profile", 0)
        # A find is recorded as a query; an aggregation (#1041) as a command.
        ns = f"{base._db.name}.books"
        reads.extend(await base._db["system.profile"].find(
            {"ns": ns, "$or": [{"op": "query"}, {"op": "command", "command.aggregate": "books"}]}
        ).to_list(None))


def _bytes(reads) -> int:
    return sum(read.get("responseLength", 0) for read in reads)


# (what it is, method, path under the book, JSON body, the status it answers, the most its reads may bring back)
NO_BODIES = 350 * KB  # everything but the 700 KB of chapter bodies
NO_BODIES_OR_BULK = 10 * KB  # and without the 300 KB of summary history and interview answers (#1041)
ONE_BODY = 110 * KB  # the 100 KB body asked for, and the owner
ROUTES = [
    ("the book", "GET", "", None, 200, NO_BODIES_OR_BULK),
    ("the summary", "GET", "/summary", None, 200, 230 * KB),
    ("saving the summary", "PUT", "/summary", {"summary": "A new summary of the book, long enough to be one. " * 4}, 200, 5 * KB),
    ("patching the summary", "PATCH", "/summary", {"summary": "A patched summary of the book, long enough to be one. " * 4}, 200, 230 * KB),
    ("the interview answers", "GET", "/question-responses", None, 200, 130 * KB),
    ("readiness for a table of contents", "GET", "/toc-readiness", None, 200, 5 * KB),
    ("the table of contents", "GET", "/toc", None, 200, NO_BODIES_OR_BULK),
    ("the chapters' metadata", "GET", "/chapters/metadata", None, 200, NO_BODIES_OR_BULK),
    ("enhancing text, refused for having none", "POST", "/chapters/c2/enhance-text", {"content": "   "}, 400, NO_BODIES_OR_BULK),
    ("saving the interview answers", "PUT", "/question-responses",
     {"responses": [{"question": "Who is it for?", "answer": "Readers who like the sea."}]}, 200, 5 * KB),
    ("cleaning up a transcription, refused for having none", "POST", "/chapters/c2/enhance-transcription", {"content": "   "}, 400, NO_BODIES_OR_BULK),
    ("deleting the book", "DELETE", "", None, 204, 5 * KB),
    # Only the chapter asked for: a subchapter's body, not its parent's, its siblings' or the 300 KB beside them (#1041).
    ("one chapter's content", "GET", "/chapters/c1a/content", None, 200, ONE_BODY),
    ("several chapters' content", "POST", "/chapters/batch-content", {"chapter_ids": ["c1", "c2"]}, 200, 750 * KB),
    # Two reads: the book without its bodies, then the one chapter for the body to show beside the refusal.
    ("a save refused as out of date", "PATCH", "/chapters/c2/content",
     {"content": "<p>new</p>", "expected_last_modified": "2000-01-01T00:00:00+00:00"}, 409, NO_BODIES_OR_BULK + ONE_BODY),
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


async def test_generating_a_draft_reads_no_bodies(auth_client_factory, monkeypatch):
    """The model is stood in for; the book and the read of it are real."""
    api = await auth_client_factory()
    book_id = await _a_large_book(api)
    drafted = {"success": True, "draft": "A draft.", "metadata": {"word_count": 2, "estimated_reading_time": 1}, "suggestions": []}
    monkeypatch.setattr(chapter_ai_endpoint.ai_service, "generate_chapter_draft", AsyncMock(return_value=drafted))

    async with _reads_of_the_book() as reads:
        answer = await api.post(
            f"{API}/{book_id}/chapters/c2/generate-draft",
            json={"question_responses": [{"question": "What happens here?", "answer": "The keeper finds the first letter."}]},
        )

    assert answer.status_code == 200, answer.text[:300]
    assert reads and _bytes(reads) <= NO_BODIES_OR_BULK, f"{_bytes(reads):,} bytes read from books"


async def test_uploading_a_cover_reads_the_owner_and_the_cover_it_replaces(auth_client_factory, monkeypatch, tmp_path):
    import app.services.file_upload_service as uploads
    from PIL import Image

    monkeypatch.setattr(uploads, "COVER_IMAGES_DIR", tmp_path)
    monkeypatch.setattr(uploads, "get_cloud_storage_service", lambda: None)
    api = await auth_client_factory()
    book_id = await _a_large_book(api)
    picture = BytesIO()
    Image.new("RGB", (400, 600), "navy").save(picture, format="JPEG")

    async with _reads_of_the_book() as reads:
        answer = await api.post(f"{API}/{book_id}/cover-image", files={"file": ("cover.jpg", picture.getvalue(), "image/jpeg")})

    assert answer.status_code == 200, answer.text[:300]
    assert reads and _bytes(reads) <= 5 * KB, f"{_bytes(reads):,} bytes read from books"


async def test_one_measurement_does_not_count_the_one_before(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _a_large_book(api)

    async with _reads_of_the_book() as first:
        await api.get(f"{API}/{book_id}/toc-readiness")
    async with _reads_of_the_book() as second:
        await api.get(f"{API}/{book_id}/toc-readiness")

    assert len(first) == len(second) == 1 and _bytes(first) == _bytes(second)


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
