# backend/app/db/user.py

import logging

from .base import users_collection, books_collection
from bson.objectid import ObjectId
from datetime import datetime, timezone
from typing import Optional, Dict, List
from .audit_log import create_audit_log

logger = logging.getLogger(__name__)


async def ensure_user_indexes() -> None:
    """Create the users collection's unique indexes (issue #178).

    Without a unique index on auth_id, the check-then-insert in the auth
    auto-create path lets parallel first-load requests each insert a doc for the
    same user. The index makes create_user's DuplicateKeyError guard effective.

    Idempotent (MongoDB skips existing indexes). Per-index try/except so a
    startup can't be bricked by one index.

    ponytail: if the collection ALREADY holds duplicate auth_id/email docs, the
    unique build fails here and is logged — an operator must dedupe first
    (one-time cleanup), the app keeps running with the race still open until then.
    """
    try:
        await users_collection.create_index(
            "auth_id", name="auth_id_unique_idx", unique=True
        )
    except Exception:
        logger.error("Failed to create unique index on users.auth_id", exc_info=True)

    try:
        # sparse: legacy/partial docs without an email don't all collide on null.
        await users_collection.create_index(
            "email", name="email_unique_idx", unique=True, sparse=True
        )
    except Exception:
        logger.error("Failed to create unique index on users.email", exc_info=True)


# User-related database operations
async def get_user_by_auth_id(auth_id: str) -> Optional[Dict]:
    """Get a user by their better-auth ID"""
    user = await users_collection.find_one({"auth_id": auth_id})
    return user


async def get_user_by_id(user_id: str) -> Optional[Dict]:
    """Get a user by their database ID"""
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    return user


async def get_user_by_email(email: str) -> Optional[Dict]:
    """Get a user by their email address"""
    user = await users_collection.find_one({"email": email})
    return user


async def create_user(user_data: Dict) -> Dict:
    """Insert a new user.

    Pure insert primitive: raises DuplicateKeyError when a unique index
    (auth_id/email, issue #178) rejects the insert. Callers apply their own
    policy — the auth auto-create path treats a duplicate auth_id as a
    concurrent-first-load race and re-fetches the winner; the legacy POST /users/
    endpoint treats it as a real conflict and returns 409.
    """
    result = await users_collection.insert_one(user_data)
    return await get_user_by_id(str(result.inserted_id))


async def update_user(
    auth_id: str, user_data: Dict, actor_id: str = None
) -> Optional[Dict]:
    """Update an existing user"""
    # Add updated_at timestamp
    user_data["updated_at"] = datetime.now(timezone.utc)

    # Update the user
    updated_user = await users_collection.find_one_and_update(
        {"auth_id": auth_id}, {"$set": user_data}, return_document=True
    )

    # Log the change if user was found and updated
    if updated_user and actor_id:
        await create_audit_log(
            action="user_update",
            actor_id=actor_id,
            target_id=auth_id,
            resource_type="user",
            details={"updated_fields": list(user_data.keys())},
        )

    return updated_user


async def delete_user(
    auth_id: str, actor_id: str = None, soft_delete: bool = True
) -> bool:
    """Delete a user (soft delete by default)"""
    if soft_delete:
        # Mark user as inactive instead of deleting
        result = await users_collection.update_one(
            {"auth_id": auth_id},
            {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}},
        )
        success = result.modified_count > 0
    else:
        # Hard delete
        result = await users_collection.delete_one({"auth_id": auth_id})
        success = result.deleted_count > 0

    # Log the deletion
    if success:
        await create_audit_log(
            action="user_delete",
            actor_id=actor_id
            or auth_id,  # If no actor specified, user deleted themselves
            target_id=auth_id,
            resource_type="user",
            details={"soft_delete": soft_delete},
        )
        return True
    return False


async def delete_user_books(user_id: str, book_ids: List[str] = None) -> bool:
    """
    Delete books associated with a user

    NB: raw ``delete_many`` on the books collection only — questions, responses,
    ratings and access logs survive. For account deletion use
    ``app.db.book.delete_all_user_books``, which cascades per book (#179).

    Args:
        user_id: The user's ID (auth_id or MongoDB _id)
        book_ids: Optional list of specific book IDs to delete. If None, deletes all user's books.

    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        # Books store their owner as owner_id (see create_book) — a user_id
        # filter matches nothing (issue #179).
        if book_ids:
            # Delete specific books for the user
            query = {
                "owner_id": user_id,
                "_id": {"$in": [ObjectId(bid) for bid in book_ids]},
            }
        else:
            # Delete all books for the user
            query = {"owner_id": user_id}

        # Delete the books
        result = await books_collection.delete_many(query)

        # Log the action
        await create_audit_log(
            action="delete_books",
            actor_id=user_id,
            target_id=user_id,
            resource_type="books",
            details={"deleted_count": result.deleted_count},
        )

        return result.deleted_count > 0
    except Exception:
        logger.error("Failed to delete user books", exc_info=True)
        return False
