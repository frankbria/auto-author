# backend/app/db/book.py

import logging

from .base import books_collection, users_collection, _client, get_collection
from bson.objectid import ObjectId
from datetime import datetime, timezone
from typing import Optional, List, Dict
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
            {"auth_id": user_auth_id}, {"$push": {"book_ids": str(book_obj.id)}}
        )

        # Create audit log entry
        await create_audit_log(
            action="book_create",
            actor_id=user_auth_id,
            target_id=str(book_obj.id),
            resource_type="book",
            details={"title": book_obj.title},
        )
        return payload
    except Exception:
        logger.error("Failed to create book", exc_info=True)
        raise


async def get_book_by_id(book_id: str) -> Optional[Dict]:
    """Get a book by its ID"""
    try:
        book = await books_collection.find_one({"_id": ObjectId(book_id)})
        return book
    except Exception:
        return None


async def get_books_by_user(
    user_auth_id: str, skip: int = 0, limit: int = 100
) -> List[Dict]:
    """Get all books owned by a user"""
    cursor = books_collection.find({"owner_id": user_auth_id}).skip(skip).limit(limit)
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


async def apply_chapter_content_update(
    book_id: str,
    chapter_id: str,
    parent_chapter_id: Optional[str],
    chapter_fields: Dict,
    user_auth_id: str,
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
    """
    now = datetime.now(timezone.utc)
    query = {"_id": ObjectId(book_id), "owner_id": user_auth_id}
    if parent_chapter_id:
        prefix = "table_of_contents.chapters.$[p].subchapters.$[c]."
        array_filters = [{"p.id": parent_chapter_id}, {"c.id": chapter_id}]
        # Require the parent+child to exist so a chapter deleted/moved since the
        # caller's read makes this a clean no-match (returns False) instead of a
        # false success that only bumps the version.
        query["table_of_contents.chapters"] = {
            "$elemMatch": {"id": parent_chapter_id, "subchapters.id": chapter_id}
        }
    else:
        prefix = "table_of_contents.chapters.$[c]."
        array_filters = [{"c.id": chapter_id}]
        query["table_of_contents.chapters.id"] = chapter_id

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
    # First check if user owns the book
    book = await books_collection.find_one(
        {"_id": ObjectId(book_id), "owner_id": user_auth_id}
    )
    if not book:
        return False

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
                    counts = await _delete_book_internal(book_id, user_auth_id, session)
        else:
            counts = await _delete_book_internal(book_id, user_auth_id, None)
    except Exception:
        # Transactional path rolls back; non-transactional path is contained by
        # children-first ordering (the book document is deleted last).
        logger.error("Cascade delete failed for book %s", book_id, exc_info=True)
        raise

    # The book vanished between the ownership check and the delete.
    if counts is None:
        return False

    # Create audit log entry
    await create_audit_log(
        action="book_delete",
        actor_id=user_auth_id,
        target_id=book_id,
        resource_type="book",
        details={"title": book.get("title", "Untitled"), "cascade_deleted": counts},
    )
    return True


async def _delete_book_internal(
    book_id: str,
    user_auth_id: str,
    session: Optional[AsyncIOMotorClientSession],
) -> Optional[Dict[str, int]]:
    """Run the cascade deletes, optionally inside a transaction ``session``.

    Children are deleted first and the book document + user association last, so
    a non-transactional partial failure leaves the book discoverable. Returns
    per-collection delete counts, or ``None`` if the book document was already
    gone (deleted between the ownership check and here).
    """
    chapter_access_logs = await get_collection("chapter_access_logs")
    questions_collection = await get_collection("questions")
    responses_collection = await get_collection("question_responses")
    ratings_collection = await get_collection("question_ratings")

    access_logs_result = await chapter_access_logs.delete_many(
        {"book_id": book_id}, session=session
    )

    questions = await questions_collection.find(
        {"book_id": book_id, "user_id": user_auth_id}, session=session
    ).to_list(length=None)
    question_ids = [str(q["_id"]) for q in questions]

    responses_deleted = 0
    ratings_deleted = 0
    if question_ids:
        responses_deleted = (
            await responses_collection.delete_many(
                {"question_id": {"$in": question_ids}}, session=session
            )
        ).deleted_count
        ratings_deleted = (
            await ratings_collection.delete_many(
                {"question_id": {"$in": question_ids}}, session=session
            )
        ).deleted_count

    questions_result = await questions_collection.delete_many(
        {"book_id": book_id, "user_id": user_auth_id}, session=session
    )

    # Parent last: book document, then the user's book_ids association.
    result = await books_collection.delete_one(
        {"_id": ObjectId(book_id)}, session=session
    )
    if result.deleted_count == 0:
        return None

    await users_collection.update_one(
        {"auth_id": user_auth_id}, {"$pull": {"book_ids": book_id}}, session=session
    )

    return {
        "chapter_access_logs": access_logs_result.deleted_count,
        "questions": questions_result.deleted_count,
        "question_responses": responses_deleted,
        "question_ratings": ratings_deleted,
    }
