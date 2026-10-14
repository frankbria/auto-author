"""One-time repairs of stored tables of contents, run at start-up."""

import logging
import uuid

from .base import get_collection
from .toc_transactions import _version_guard, _walk_toc

logger = logging.getLogger(__name__)


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
    # shortcut: scans every book's ids at every start-up; add an app_meta
    # "done" marker if the collection grows large enough for that to matter.
    # Projects two levels of ids, the data model's depth (see
    # apply_chapter_content_update).
    books_collection = await get_collection("books")
    repaired = 0
    async for book in books_collection.find(
        {"table_of_contents.chapters.0": {"$exists": True}},
        {"table_of_contents.chapters.id": 1, "table_of_contents.chapters.subchapters.id": 1},
    ):
        # One malformed TOC (an AI TOC is stored as it came) must not stop the rest.
        try:
            if not _has_duplicates(book["table_of_contents"]["chapters"]):
                continue
            full = await books_collection.find_one({"_id": book["_id"]}, {"table_of_contents": 1})
            toc = full["table_of_contents"]
            guard = _version_guard(toc)
            seen = set()
            for item in _items(toc["chapters"]):
                cid = item.get("id")
                if not (isinstance(cid, str) and cid):
                    continue
                if cid in seen:
                    item["id"] = str(uuid.uuid4())
                seen.add(cid)
            result = await books_collection.update_one(
                {"_id": book["_id"], "table_of_contents.version": guard},
                {"$set": {"table_of_contents.chapters": toc["chapters"]}, "$inc": {"table_of_contents.version": 1}},
            )
            repaired += result.modified_count
        except Exception:
            logger.warning("Could not check book %s for duplicate chapter ids", book["_id"], exc_info=True)
    return repaired


def _items(chapters):
    """The chapter dicts of a TOC, skipping anything that is not one."""
    if not isinstance(chapters, list):
        return []
    return list(_walk_toc(c for c in chapters if isinstance(c, dict)))


def _has_duplicates(chapters) -> bool:
    # Same rule as #754's _require_unique_ids: only non-empty string ids count.
    ids = [c.get("id") for c in _items(chapters) if isinstance(c.get("id"), str) and c.get("id")]
    return len(ids) != len(set(ids))
