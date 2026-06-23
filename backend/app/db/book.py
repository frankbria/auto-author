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
