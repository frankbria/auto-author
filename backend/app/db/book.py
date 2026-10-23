# backend/app/db/book.py

import logging

from .base import books_collection, users_collection
from bson.errors import InvalidId
from bson.objectid import ObjectId
from datetime import datetime, timezone
from typing import Optional, List, Dict
from .audit_log import audit_after_write
from .book_delete import delete_all_user_books, delete_book  # noqa: F401  (re-exported, #1144)
from app.models.book import BookDB

logger = logging.getLogger(__name__)


# Book-related database operations
async def create_book(book_data: Dict, user_auth_id: str) -> Dict:
    """Create a new book in the database and associate it with a user"""
    try:
        # 1) Set owner ID
        book_data["owner_id"] = user_auth_id

        # 2) build the Pydantic model
        book_obj = BookDB(**book_data)

        # 3) serialize to a Mongo-ready dict, with _id alias and timestamps
        payload = book_obj.model_dump(by_alias=True)

        # 4) Insert the new book
        result = await books_collection.insert_one(payload)

        # 5) patch the real ObjectId back onto the model
        book_obj.id = result.inserted_id

        # Associate the book with the user
        attached = await users_collection.update_one(
            # Never onto a tombstone (deleted account, #784).
            {"auth_id": user_auth_id, "deleted_at": {"$exists": False}},
            {"$push": {"book_ids": str(book_obj.id)}},
        )
        # An insert that lands after delete_user's second cascade (#945) finds
        # the tombstone here: the book has no children or cover yet.
        if not attached.matched_count and await users_collection.count_documents(
            {"auth_id": user_auth_id, "deleted_at": {"$exists": True}}, limit=1
        ):
            await books_collection.delete_one({"_id": result.inserted_id})
            raise ValueError("The account was deleted")

        # Create audit log entry
        await audit_after_write(
            action="book_create",
            actor_id=user_auth_id,
            target_id=str(book_obj.id),
            resource_type="book",
        )
        return payload
    except Exception:
        logger.error("Failed to create book", exc_info=True)
        raise


# Drops the per-chapter draft HTML (top-level chapters and one level of
# subchapters) while leaving ids, titles, nesting, status and all top-level book
# metadata intact. Chapter bodies are the only unbounded field on a book, so
# excluding them turns a multi-KB→MB read into a small one (#344).
CONTENT_EXCLUDING_PROJECTION = {
    "table_of_contents.chapters.content": 0,
    "table_of_contents.chapters.subchapters.content": 0,
    # The other two unbounded fields (#1041). No route that walks the chapter list reads them.
    "summary_history": 0,
    "question_responses": 0,
}


async def get_book_by_id(book_id: str) -> Optional[Dict]:
    """Get a book by its ID, including every chapter's draft HTML.

    Prefer :func:`get_book_owner_id` when only ownership matters, or
    :func:`get_book_metadata_by_id` when the chapter bodies are not read — this
    one pulls the entire document (#344).
    """
    try:
        book = await books_collection.find_one({"_id": ObjectId(book_id)})
        return book
    except (InvalidId, TypeError):  # a malformed id names no book; a DB error is not that (#849)
        return None


async def get_book_owner_id(book_id: str) -> Optional[str]:
    """Return just the owner of a book, for an ownership check.

    Most book-scoped endpoints read nothing but ``owner_id`` from the book, yet
    an unprojected ``find_one`` hands back every chapter's HTML to answer that
    one question. Returns ``None`` for a missing book and for a malformed id,
    matching :func:`get_book_by_id` so callers keep turning both into a 404.
    """
    try:
        book = await books_collection.find_one(
            {"_id": ObjectId(book_id)}, {"owner_id": 1}
        )
        return book.get("owner_id") if book else None
    except (InvalidId, TypeError):  # a malformed id names no book; a DB error is not that (#849)
        return None


async def get_book_fields(book_id: str, *fields: str) -> Optional[Dict]:
    """Get a book's ``_id`` and the top-level fields named, and nothing else (#829).

    For a handler that uses the owner and one or two other fields. Naming
    ``table_of_contents`` brings every chapter's body with it: that is for the
    routes that return a body. ``None`` for a missing book and for a malformed
    id, like the lookups above.
    """
    try:
        return await books_collection.find_one(
            {"_id": ObjectId(book_id)}, {field: 1 for field in fields}
        )
    except (InvalidId, TypeError):  # a malformed id names no book; a DB error is not that (#849)
        return None


async def get_book_owner_and_chapter(book_id: str, chapter_id: str) -> Optional[Dict]:
    """The book's ``_id`` and ``owner_id`` plus ``chapter``: the one chapter named, or ``None`` (#1041).

    The chapter is picked inside the database, so only its own body comes back.
    Bodies are written at two levels (a chapter, or a subchapter of one: see
    :func:`apply_chapter_content_update`), so two levels are searched. The found
    chapter's own subchapters are cut to their ids: the caller counts them and
    never reads their bodies. ``None`` for a missing book and for a malformed id.
    """
    top = "$table_of_contents.chapters"
    sub = {"$reduce": {"input": {"$ifNull": [top, []]}, "initialValue": [],
                       "in": {"$concatArrays": ["$$value", {"$cond": [{"$isArray": "$$this.subchapters"}, "$$this.subchapters", []]}]}}}
    both = {"$concatArrays": [{"$cond": [{"$isArray": top}, top, []]}, sub]}
    found = {"$filter": {"input": both, "as": "c", "cond": {"$eq": ["$$c.id", chapter_id]}}}
    try:
        cursor = await books_collection.aggregate([
            {"$match": {"_id": ObjectId(book_id)}},
            {"$project": {"owner_id": 1, "chapter": {"$first": found}}},
            {"$set": {"chapter.subchapters": {"$cond": [
                {"$isArray": "$chapter.subchapters"},
                {"$map": {"input": "$chapter.subchapters", "as": "s", "in": {"id": "$$s.id"}}},
                "$$REMOVE",
            ]}}},
        ])
        book = next(iter(await cursor.to_list(1)), None)
        if book and not book.get("chapter"):
            book["chapter"] = None  # the $set above leaves {} where no chapter matched
        return book
    except (InvalidId, TypeError):  # a malformed id names no book; a DB error is not that (#849)
        return None


async def get_book_metadata_by_id(book_id: str) -> Optional[Dict]:
    """Get a book without any chapter draft HTML.

    For callers that need the book's metadata or its chapter *structure* —
    ids, nesting, titles, status — but never a chapter body.
    """
    try:
        book = await books_collection.find_one(
            {"_id": ObjectId(book_id)}, CONTENT_EXCLUDING_PROJECTION
        )
        return book
    except (InvalidId, TypeError):  # a malformed id names no book; a DB error is not that (#849)
        return None


async def get_books_by_user(
    user_auth_id: str, skip: int = 0, limit: int = 100
) -> List[Dict]:
    """Get all books owned by a user.

    Projects out the heavy per-chapter ``content`` HTML from ``table_of_contents``
    (top-level chapters and one level of subchapters). The dashboard list endpoint
    returns ``BookResponse``, which exposes ``toc_items`` but never the full
    ``table_of_contents`` body — so fetching every chapter's draft here is pure
    overfetch (a book with long chapters sends KBs of unused HTML per row).
    Titles/structure/``toc_items`` are untouched.
    """
    cursor = (
        books_collection.find({"owner_id": user_auth_id}, CONTENT_EXCLUDING_PROJECTION)
        # Newest first. Without an explicit sort Mongo returns natural (roughly
        # insertion) order, so once a user passes the endpoint's 100-row page size
        # the dashboard shows their OLDEST 100 forever and a newly created book is
        # never visible — it sits past the end of page one. On staging (#488) that
        # account had 2,649 books and the dashboard's newest card was months old.
        #
        # Sort on updated_at ALONE, deliberately. The collection already carries
        # owner_updated_idx (owner_id, updated_at DESC), and this exact shape uses
        # it: explain() reports LIMIT -> FETCH -> IXSCAN. Adding an _id tiebreaker
        # for tie determinism looks harmless but measured as
        # SORT -> FETCH -> IXSCAN — a blocking in-memory sort on every dashboard
        # load, which is what hits Mongo's 32MB sort cap as a library grows.
        # Ties within one second are rare and not worth that.
        .sort("updated_at", -1)
        .skip(skip)
        .limit(limit)
    )
    books = await cursor.to_list(length=limit)
    return books


async def update_book(
    book_id: str, book_data: Dict, user_auth_id: str, return_document: bool = True
) -> Optional[Dict]:
    """Update an existing book. ``return_document`` is pymongo's: pass
    ``ReturnDocument.BEFORE`` for the document the update replaced."""
    # Add updated_at timestamp
    book_data["updated_at"] = datetime.now(timezone.utc)

    # Update the book
    updated_book = await books_collection.find_one_and_update(
        {"_id": ObjectId(book_id), "owner_id": user_auth_id},  # Only owner can update
        {"$set": book_data},
        return_document=return_document,
    )

    # Create audit log entry if book was found and updated
    if updated_book:
        await audit_after_write(
            action="book_update",
            actor_id=user_auth_id,
            target_id=book_id,
            resource_type="book",
            details={"updated_fields": list(book_data.keys())},
        )

    return updated_book


# Default for ``expected_last_modified``: no precondition. ``None`` can't be the
# default because it is a real precondition ("never saved").
NO_PRECONDITION = object()


async def apply_chapter_content_update(
    book_id: str,
    chapter_id: str,
    parent_chapter_id: Optional[str],
    chapter_fields: Dict,
    user_auth_id: str,
    expected_last_modified=NO_PRECONDITION,
) -> bool:
    """Concurrency-safe, targeted update of a SINGLE chapter's fields.

    The old autosave path rewrote the whole ``table_of_contents`` via
    ``update_book``'s version-less ``$set``, so a concurrent autosave to a
    *different* chapter (or a reorder) silently clobbered this one — the #177
    lost update. This positional ``$set`` (via ``array_filters``) touches only
    the target chapter's fields and bumps the TOC version atomically with
    ``$inc``, so concurrent saves to different chapters no longer collide and no
    version guard / 409 round-trip is needed.

    ponytail: supports a top-level chapter or one level of subchapter — the data
    model's max depth (matches ``add_chapter_with_transaction``). Deeper nesting
    would need another ``array_filters`` level.

    The query filter requires the target chapter (and parent, for a subchapter)
    to still exist, so a chapter deleted/moved since the caller's read is a clean
    no-match rather than a false success that only bumps the version. Returns
    True when the update matched (and thus applied), False otherwise.

    ``expected_last_modified`` (#759) is the chapter's *stored* ``last_modified``
    as the caller read it (string, Date, or ``None`` for never saved). When
    given, the filter also requires the stored value to still equal it, so a
    write committed since the caller's read makes this a no-match too.
    """
    now = datetime.now(timezone.utc)
    query = {"_id": ObjectId(book_id), "owner_id": user_auth_id}
    target = {"id": chapter_id}
    if expected_last_modified is not NO_PRECONDITION:
        target["last_modified"] = expected_last_modified
    if parent_chapter_id:
        prefix = "table_of_contents.chapters.$[p].subchapters.$[c]."
        array_filters = [{"p.id": parent_chapter_id}]
        # Require the parent+child to exist so a chapter deleted/moved since the
        # caller's read makes this a clean no-match (returns False) instead of a
        # false success that only bumps the version.
        query["table_of_contents.chapters"] = {
            "$elemMatch": {
                "id": parent_chapter_id,
                "subchapters": {"$elemMatch": target},
            }
        }
    else:
        prefix = "table_of_contents.chapters.$[c]."
        array_filters = []
        query["table_of_contents.chapters"] = {"$elemMatch": target}
    array_filters.append({f"c.{key}": value for key, value in target.items()})

    set_doc = {prefix + key: value for key, value in chapter_fields.items()}
    set_doc["table_of_contents.updated_at"] = now.isoformat()
    set_doc["table_of_contents.status"] = "edited"
    set_doc["updated_at"] = now

    result = await books_collection.update_one(
        query,
        {"$set": set_doc, "$inc": {"table_of_contents.version": 1}},
        array_filters=array_filters,
    )
    return result.matched_count > 0


async def update_book_summary_atomic(
    book_id: str,
    summary: str,
    user_auth_id: str,
) -> Optional[Dict]:
    """Persist a book summary, atomically archiving the *document's current*
    summary to history at write time.

    The endpoint used to read ``summary_history``, append in memory, then ``$set``
    the whole array — two concurrent saves read the same list and one overwrote
    the other's appended revision (#177). This uses an aggregation-pipeline update
    so the revision archived is the value stored on the document when the write
    commits, not a value the caller read earlier. Single-document writes serialize,
    so two concurrent edits (A->B, A->C) both land in history: the second write
    sees the first's committed summary and archives it. History is capped at the
    last 20 revisions. An unchanged or empty prior summary archives nothing.

    Returns the updated document (or None if the book wasn't found / not owned).
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    update = [
        {
            "$set": {
                "summary_history": {
                    "$slice": [
                        {
                            "$concatArrays": [
                                {"$ifNull": ["$summary_history", []]},
                                {
                                    "$cond": [
                                        {
                                            "$and": [
                                                {"$ne": [{"$ifNull": ["$summary", ""]}, ""]},
                                                # $literal: a user summary starting with
                                                # "$" would otherwise be read as a field path.
                                                {"$ne": ["$summary", {"$literal": summary}]},
                                            ]
                                        },
                                        [{"summary": "$summary", "timestamp": now_iso}],
                                        [],
                                    ]
                                },
                            ]
                        },
                        -20,
                    ]
                }
            }
        },
        {"$set": {"summary": {"$literal": summary}, "updated_at": now}},
    ]

    updated_book = await books_collection.find_one_and_update(
        {"_id": ObjectId(book_id), "owner_id": user_auth_id},
        update,
        return_document=True,
    )

    if updated_book:
        await audit_after_write(
            action="book_update",
            actor_id=user_auth_id,
            target_id=book_id,
            resource_type="book",
            details={"updated_fields": ["summary", "summary_history"]},
        )

    return updated_book
