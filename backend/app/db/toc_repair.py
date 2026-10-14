"""One-time repairs of stored tables of contents, run at start-up."""

import uuid

from .base import get_collection
from .toc_transactions import _version_guard, _walk_toc


async def repair_duplicate_chapter_ids() -> int:
    """Give every later occurrence of a stored duplicate chapter id a fresh
    uuid4; the first keeps its id, draft and questions (#885). #754 refuses new
    duplicates, but a book stored before it could hold two, and one autosave
    overwrote both. Idempotent: a repaired book has nothing left to change.
    Returns the number of books repaired.

    Reads only the ids of every book, then the whole TOC of a book that needs
    it; the write is guarded on the TOC version, so an edit in between wins and
    the next start-up repairs it.
    """
    books_collection = await get_collection("books")
    repaired = 0
    async for book in books_collection.find(
        {"table_of_contents.chapters.0": {"$exists": True}},
        {"table_of_contents.chapters.id": 1, "table_of_contents.chapters.subchapters.id": 1},
    ):
        ids = [c.get("id") for c in _walk_toc(book["table_of_contents"]["chapters"]) if isinstance(c.get("id"), str)]
        if len(ids) == len(set(ids)):
            continue
        full = await books_collection.find_one({"_id": book["_id"]}, {"table_of_contents": 1})
        toc = full["table_of_contents"]
        guard = _version_guard(toc)
        seen = set()
        for item in _walk_toc(toc["chapters"]):
            cid = item.get("id")
            if not isinstance(cid, str):
                continue
            if cid in seen:
                item["id"] = str(uuid.uuid4())
            seen.add(cid)
        result = await books_collection.update_one(
            {"_id": book["_id"], "table_of_contents.version": guard},
            {"$set": {"table_of_contents.chapters": toc["chapters"]}, "$inc": {"table_of_contents.version": 1}},
        )
        repaired += result.modified_count
    return repaired
