"""The account export is streamed (#966): its memory does not grow with the library.

The measure: tracemalloc's peak while the export generator runs to the end, its
chunks thrown away as a client socket would, for the same account at 50 and
then 500 books of 20 KB chapter text each. Built in memory, the peak grows with
the library (about 10x here: every book is held, then encoded, at once).
Streamed, it is set by the cursor batch, so the two peaks match. The test
allows 2x, which leaves room for allocator noise and still fails a 10x
growth, and a warm-up run first keeps one-off costs (connection pool, imports)
out of the 50-book peak. tracemalloc counts Python allocations only, which is
where the documents and the encoded JSON live.
"""

import json
import re
import tracemalloc
from datetime import datetime, timezone

import pytest
from bson import ObjectId
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.endpoints.account_export import (
    EXPORTED_COLLECTIONS,
    EXPORTED_PROFILE_FIELDS,
    stream_account_export,
)
from app.db.base import get_collection

OWNER = "stream-owner"
USER = {
    "auth_id": OWNER,
    "email": "stream@example.com",
    "first_name": "Streäm",
    "created_at": datetime(2026, 1, 2, 3, 4, 5),
    "preferences": {"theme": "dark"},
    "internal_note": "not exported",
}
CHAPTER_TEXT = "<p>" + "x" * 20_000 + "</p>"


async def _seed_books(count: int) -> None:
    await (await get_collection("books")).insert_many(
        [
            {
                "title": f"Book {i}",
                "owner_id": OWNER,
                "created_at": datetime(2026, 10, 1),
                "collaborators": [{"user_id": "someone-else"}],
                "table_of_contents": {
                    "chapters": [{"id": "ch1", "title": "One", "content": CHAPTER_TEXT}]
                },
            }
            for i in range(count)
        ]
    )


async def _drain(user: dict) -> tuple[int, int]:
    """Run the export to the end, keeping nothing. Returns (chunks, bytes)."""
    chunks = size = 0
    async for chunk in stream_account_export(user):
        chunks += 1
        size += len(chunk)
    return chunks, size


async def _peak(user: dict) -> tuple[int, int, int]:
    tracemalloc.start()
    try:
        tracemalloc.reset_peak()
        chunks, size = await _drain(user)
        return tracemalloc.get_traced_memory()[1], chunks, size
    finally:
        tracemalloc.stop()


@pytest.mark.asyncio
async def test_export_memory_does_not_grow_with_the_library(reinit_db):
    await _seed_books(50)
    await _drain(USER)  # warm-up
    peak_50, chunks_50, size_50 = await _peak(USER)

    await _seed_books(450)
    peak_500, chunks_500, size_500 = await _peak(USER)

    assert chunks_50 > 50 and chunks_500 > 500, "one chunk per book at least"
    assert size_500 > 9 * size_50, "vacuity: the larger library really is ~10x the output"
    assert peak_500 < 2 * peak_50, (peak_50, peak_500)
    assert size_500 > 4 * peak_500, "the file is far larger than what was held"


def _old_export(user: dict, docs: dict) -> bytes:
    """The pre-#966 in-memory build, verbatim, as the reference shape."""
    data = {
        "exported_at": datetime.now(timezone.utc),
        "profile": {f: user[f] for f in EXPORTED_PROFILE_FIELDS if f in user},
    }
    for name in EXPORTED_COLLECTIONS:
        data[name] = docs[name]
    return JSONResponse(
        jsonable_encoder(
            data,
            custom_encoder={
                ObjectId: str,
                datetime: lambda d: d.replace(tzinfo=d.tzinfo or timezone.utc).isoformat(),
            },
        )
    ).body


@pytest.mark.asyncio
async def test_streamed_export_matches_the_old_document_byte_for_byte(reinit_db):
    await _seed_books(2)
    book_ids = [str(b["_id"]) for b in await (await get_collection("books")).find().to_list(None)]
    q = await (await get_collection("questions")).insert_one(
        {"book_id": book_ids[0], "user_id": OWNER, "question_text": "Why—really?"}
    )
    await (await get_collection("question_responses")).insert_one(
        {"question_id": str(q.inserted_id), "user_id": OWNER, "response_text": "Because"}
    )
    # question_ratings left empty: an empty array must come out as [].
    await (await get_collection("questions")).insert_one(
        {"book_id": "x", "user_id": "someone-else", "question_text": "not mine"}
    )

    streamed = b"".join([chunk async for chunk in stream_account_export(USER)])

    docs = {}
    for name, owner_field in EXPORTED_COLLECTIONS.items():
        docs[name] = await (await get_collection(name)).find(
            {owner_field: OWNER}, {"collaborators": 0}
        ).to_list(None)
    reference = _old_export(USER, docs)

    stamp = re.compile(rb'"exported_at":"[^"]*"')
    assert stamp.sub(b"", streamed) == stamp.sub(b"", reference)
    parsed = json.loads(streamed)
    assert list(parsed) == ["exported_at", "profile", *EXPORTED_COLLECTIONS]
    assert parsed["question_ratings"] == []
    assert len(parsed["books"]) == 2 and "collaborators" not in parsed["books"][0]
    assert "internal_note" not in parsed["profile"]
