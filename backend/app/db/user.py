# backend/app/db/user.py

from .base import users_collection, books_collection
from bson.objectid import ObjectId
from datetime import datetime, timezone
from typing import Optional, Dict, List
from .audit_log import create_audit_log


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
    """Create a new user in the database"""
    result = await users_collection.insert_one(user_data)
    created_user = await get_user_by_id(str(result.inserted_id))
    return created_user


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

    Args:
        user_id: The user's ID (auth_id or MongoDB _id)
        book_ids: Optional list of specific book IDs to delete. If None, deletes all user's books.

    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        # Get books collection

        # Prepare filter to find books
        if book_ids:
            # Delete specific books for the user
            query = {
                "user_id": user_id,
                "_id": {"$in": [ObjectId(bid) for bid in book_ids]},
            }
        else:
            # Delete all books for the user
            query = {"user_id": user_id}

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
    except Exception as e:
        # In a production app, you might want to log this error
        print(f"Error deleting user books: {e}")
        return False
