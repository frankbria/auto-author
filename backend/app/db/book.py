# backend/app/db/book.py

import logging

from app.core.reporting import report_failure

from .base import books_collection, users_collection, _client, get_collection
from bson.objectid import ObjectId
from datetime import datetime, timezone
from typing import Optional, List, Dict, Tuple
from motor.motor_asyncio import AsyncIOMotorClientSession
from .audit_log import create_audit_log
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
        await users_collection.update_one(
            # Never onto a tombstone (deleted account, #784).
            {"auth_id": user_auth_id, "deleted_at": {"$exists": False}},
            {"$push": {"book_ids": str(book_obj.id)}},
        )

        # Create audit log entry
        await create_audit_log(
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
    except Exception:
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
    except Exception:
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
    except Exception:
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
    book_id: str, book_data: Dict, user_auth_id: str
) -> Optional[Dict]:
    """Update an existing book"""
    # Add updated_at timestamp
    book_data["updated_at"] = datetime.now(timezone.utc)

    # Update the book
    updated_book = await books_collection.find_one_and_update(
        {"_id": ObjectId(book_id), "owner_id": user_auth_id},  # Only owner can update
        {"$set": book_data},
        return_document=True,
    )

    # Create audit log entry if book was found and updated
    if updated_book:
        await create_audit_log(
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
        await create_audit_log(
            action="book_update",
            actor_id=user_auth_id,
            target_id=book_id,
            resource_type="book",
            details={"updated_fields": ["summary", "summary_history"]},
        )

    return updated_book


# All a delete needs from a book. Unprojected, the read pulls every chapter's
# HTML just to throw it away (#786).
_DELETE_PROJECTION = {"title": 1, "cover_image_url": 1, "cover_thumbnail_url": 1}

# One $in filter is a single BSON document, capped at 16MB; an id costs about
# 35 bytes in it.
_QUESTION_ID_CHUNK = 100_000


async def delete_book(book_id: str, user_auth_id: str) -> bool:
    """Delete a book and cascade-delete all of its related data.

    Removes (atomically when MongoDB supports transactions via a replica set,
    and with a safe children-first ordering otherwise):
    - chapter access logs, questions, question responses, question ratings
    - the book document
    - the book association on the user

    Mirrors the conditional-transaction pattern in ``toc_transactions``. On a
    non-transactional deployment a mid-cascade failure leaves the book document
    (deleted last) intact, so it stays discoverable rather than orphaned.
    """
    book = await books_collection.find_one(
        {"_id": ObjectId(book_id), "owner_id": user_auth_id}, _DELETE_PROJECTION
    )
    if not book:
        return False
    # ObjectId() accepts uppercase hex; children and files are keyed by the
    # canonical lowercase id (#797).
    book_id = str(book["_id"])

    # Detect replica-set support; multi-document transactions require one.
    use_transaction = True
    try:
        async with await _client.start_session():
            info = await _client.admin.command("isMaster")
            use_transaction = info.get("setName") is not None
    except Exception:
        use_transaction = False

    try:
        if use_transaction:
            async with await _client.start_session() as session:
                async with session.start_transaction():
                    deleted, counts = await _delete_books_internal(
                        [book_id], user_auth_id, session
                    )
        else:
            deleted, counts = await _delete_books_internal([book_id], user_auth_id, None)
    except Exception:
        # Transactional path rolls back; non-transactional path is contained by
        # children-first ordering (the book document is deleted last).
        logger.error("Cascade delete failed for book %s", book_id, exc_info=True)
        raise

    # The book vanished between the ownership check and the delete.
    if not deleted:
        return False

    await _delete_cover_files(book)

    await create_audit_log(
        action="book_delete",
        actor_id=user_auth_id,
        target_id=book_id,
        resource_type="book",
        details={"cascade_deleted": counts},
    )
    return True


async def delete_all_user_books(user_auth_id: str) -> int:
    """Cascade-delete every book the user owns (account deletion, issue #179).

    One command per collection however many books there are (#786): a per-book
    loop timed out on a 2,649-book account. A failure propagates so the caller
    can abort before touching the user record (children first, parents last),
    leaving the books in place for a retry. Returns the number of books deleted.

    Never a transaction, even on a replica set: one spanning a whole account
    outlives the 60s transaction limit on exactly the accounts this is for.
    ponytail: the id list is a snapshot — a book created mid-cascade survives.
    """
    books = await books_collection.find(
        {"owner_id": user_auth_id}, _DELETE_PROJECTION
    ).to_list(length=None)
    if not books:
        return 0

    deleted, counts = await _delete_books_internal(
        [str(book["_id"]) for book in books], user_auth_id, None
    )

    # shortcut: one storage call per cover, in sequence; batch them if accounts
    # with thousands of covers appear (cover upload has no UI yet, #941).
    for book in books:
        await _delete_cover_files(book)

    # One row for the account, without the titles a per-book row would keep.
    await create_audit_log(
        action="delete_books",
        actor_id=user_auth_id,
        target_id=user_auth_id,
        resource_type="books",
        details={"deleted_count": deleted, "cascade_deleted": counts},
    )
    return deleted


async def _delete_cover_files(book: Dict) -> None:
    """Remove a deleted book's cover and thumbnail. Only once the delete has
    committed: a removed file cannot roll back (#785)."""
    cover_url = book.get("cover_image_url")
    thumbnail_url = book.get("cover_thumbnail_url")
    if not (cover_url or thumbnail_url):
        return
    book_id = str(book["_id"])
    try:
        from app.services.file_upload_service import FileUploadService

        await FileUploadService().delete_cover_image(book_id, cover_url, thumbnail_url)
    except Exception as error:
        logger.error("Failed to delete cover files for book %s", book_id, exc_info=True)
        report_failure("delete-files", error)


async def _delete_books_internal(
    book_ids: List[str],
    user_auth_id: str,
    session: Optional[AsyncIOMotorClientSession],
) -> Tuple[int, Dict[str, int]]:
    """Run the cascade deletes for ``book_ids``, optionally inside a transaction
    ``session``. Children go first and the book documents + user association
    last, so a non-transactional partial failure leaves the books discoverable.
    Returns the number of book documents deleted (0 if they vanished after the
    ownership check) and the per-collection child delete counts.
    """
    chapter_access_logs = await get_collection("chapter_access_logs")
    questions_collection = await get_collection("questions")
    responses_collection = await get_collection("question_responses")
    ratings_collection = await get_collection("question_ratings")
    in_books = {"$in": book_ids}
    question_scope = {"book_id": in_books, "user_id": user_auth_id}

    access_logs_result = await chapter_access_logs.delete_many(
        {"book_id": in_books}, session=session
    )

    questions = await questions_collection.find(
        question_scope, {"_id": 1}, session=session
    ).to_list(length=None)
    question_ids = [str(q["_id"]) for q in questions]

    responses_deleted = ratings_deleted = 0
    for start in range(0, len(question_ids), _QUESTION_ID_CHUNK):
        in_questions = {"question_id": {"$in": question_ids[start : start + _QUESTION_ID_CHUNK]}}
        responses_deleted += (
            await responses_collection.delete_many(in_questions, session=session)
        ).deleted_count
        ratings_deleted += (
            await ratings_collection.delete_many(in_questions, session=session)
        ).deleted_count

    questions_result = await questions_collection.delete_many(
        question_scope, session=session
    )

    # Parents last: book documents, then the user's book_ids association.
    books_result = await books_collection.delete_many(
        {"_id": {"$in": [ObjectId(b) for b in book_ids]}, "owner_id": user_auth_id},
        session=session,
    )
    if books_result.deleted_count:
        await users_collection.update_one(
            {"auth_id": user_auth_id}, {"$pull": {"book_ids": in_books}}, session=session
        )

    return books_result.deleted_count, {
        "chapter_access_logs": access_logs_result.deleted_count,
        "questions": questions_result.deleted_count,
        "question_responses": responses_deleted,
        "question_ratings": ratings_deleted,
    }
