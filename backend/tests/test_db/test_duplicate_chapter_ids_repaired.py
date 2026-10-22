"""Books that already store duplicate chapter ids are repaired (#885).

#754 refuses new duplicates, but a book stored before it can hold two chapters
with one id. The autosave writes with array_filters on the id, so one save to
such a book overwrote both chapters. A start-up repair gives every later
occurrence a fresh id; the first keeps its id and its draft.

Against a real MongoDB.
"""

import pytest
from bson import ObjectId

import app.db.toc_transactions as tx
from app.db.book import apply_chapter_content_update
from app.db.toc_repair import repair_duplicate_chapter_ids

OWNER = "owner-auth-885"


def _chapter(cid: str, title: str, content: str, subchapters=None) -> dict:
    return {"id": cid, "title": title, "content": content, "level": 1, "order": 1, "subchapters": subchapters or []}


async def _book(chapters: list, version: int = 3) -> ObjectId:
    book_id = ObjectId()
    await tx.books_collection.insert_one(
        {"_id": book_id, "owner_id": OWNER, "title": "Small Changes",
         "table_of_contents": {"chapters": chapters, "version": version}}
    )
    return book_id


async def _chapters(book_id: ObjectId) -> list:
    book = await tx.books_collection.find_one({"_id": book_id})
    flat = []
    for chapter in book["table_of_contents"]["chapters"]:
        flat.append(chapter)
        flat.extend(chapter.get("subchapters") or [])
    return flat


@pytest.mark.asyncio
async def test_later_occurrences_get_fresh_ids_and_the_first_keeps_its_own(reinit_db):
    book_id = await _book([
        _chapter("dup", "First", "first draft", subchapters=[_chapter("dup", "Nested", "nested draft")]),
        _chapter("dup", "Second", "second draft"),
        _chapter("solo", "Third", "third draft"),
    ])

    assert await repair_duplicate_chapter_ids() == 1

    first, nested, second, third = await _chapters(book_id)
    assert (first["id"], first["content"]) == ("dup", "first draft")
    assert (nested["content"], second["content"], third["id"]) == ("nested draft", "second draft", "solo")
    ids = [c["id"] for c in (first, nested, second, third)]
    assert len(set(ids)) == 4
    book = await tx.books_collection.find_one({"_id": book_id})
    assert book["table_of_contents"]["version"] == 4


@pytest.mark.asyncio
async def test_the_repair_is_idempotent_and_leaves_clean_books_alone(reinit_db):
    repaired = await _book([_chapter("dup", "A", "a"), _chapter("dup", "B", "b")])
    clean = await _book([_chapter("x", "A", "a"), _chapter("y", "B", "b")])
    no_toc = ObjectId()
    await tx.books_collection.insert_one({"_id": no_toc, "owner_id": OWNER, "title": "Empty"})

    assert await repair_duplicate_chapter_ids() == 1
    after_first = await _chapters(repaired)
    assert await repair_duplicate_chapter_ids() == 0

    assert await _chapters(repaired) == after_first
    book = await tx.books_collection.find_one({"_id": clean})
    assert book["table_of_contents"]["version"] == 3


@pytest.mark.asyncio
async def test_after_the_repair_one_save_changes_one_chapter(reinit_db):
    book_id = await _book([_chapter("dup", "First", "first draft"), _chapter("dup", "Second", "second draft")])

    await repair_duplicate_chapter_ids()
    assert await apply_chapter_content_update(str(book_id), "dup", None, {"content": "edited"}, OWNER)

    first, second = await _chapters(book_id)
    assert (first["content"], second["content"]) == ("edited", "second draft")


@pytest.mark.asyncio
async def test_a_malformed_toc_does_not_stop_the_repair_of_other_books(reinit_db):
    """Found in review: an AI TOC is stored as it came, nulls and all."""
    await _book([None, _chapter("dup", "A", "a"), _chapter("dup", "B", "b")])
    await tx.books_collection.insert_one({"_id": ObjectId(), "owner_id": OWNER, "table_of_contents": {"chapters": {"0": "x"}}})
    later = await _book([_chapter("dup", "C", "c"), _chapter("dup", "D", "d")])

    assert await repair_duplicate_chapter_ids() == 2

    first, second = await _chapters(later)
    assert first["id"] == "dup" and second["id"] != "dup"
