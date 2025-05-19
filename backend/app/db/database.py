from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from bson.objectid import ObjectId
from app.core.config import settings
import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

# Initialize MongoDB connection
client = AsyncIOMotorClient(settings.DATABASE_URI)
database = client[settings.DATABASE_NAME]

# Collections
users_collection = database.get_collection("users")
audit_logs_collection = database.get_collection("audit_logs")


async def get_collection(collection_name: str):
    return database[collection_name]


# User-related database operations
async def get_user_by_clerk_id(clerk_id: str) -> Optional[Dict]:
    """Get a user by their Clerk ID"""
    user = await users_collection.find_one({"clerk_id": clerk_id})
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
    clerk_id: str, user_data: Dict, actor_id: str = None
) -> Optional[Dict]:
    """Update an existing user"""
    # Add updated_at timestamp
    user_data["updated_at"] = datetime.utcnow()

    # Update the user
    updated_user = await users_collection.find_one_and_update(
        {"clerk_id": clerk_id}, {"$set": user_data}, return_document=True
    )

    # Log the change if user was found and updated
    if updated_user and actor_id:
        await create_audit_log(
            action="user_update",
            actor_id=actor_id,
            target_id=clerk_id,
            resource_type="user",
            details={"updated_fields": list(user_data.keys())},
        )

    return updated_user


async def delete_user(
    clerk_id: str, actor_id: str = None, soft_delete: bool = True
) -> bool:
    """Delete a user (soft delete by default)"""
    if soft_delete:
        # Mark user as inactive instead of deleting
        result = await users_collection.update_one(
            {"clerk_id": clerk_id},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}},
        )
    else:
        # Hard delete
        result = await users_collection.delete_one({"clerk_id": clerk_id})

    # Log the deletion
    if result.modified_count > 0 or result.deleted_count > 0:
        await create_audit_log(
            action="user_delete",
            actor_id=actor_id
            or clerk_id,  # If no actor specified, user deleted themselves
            target_id=clerk_id,
            resource_type="user",
            details={"soft_delete": soft_delete},
        )
        return True
    return False


async def create_audit_log(
    action: str, actor_id: str, target_id: str, resource_type: str, details: Dict = None
) -> Dict:
    """Create an audit log entry"""
    log_data = {
        "action": action,
        "actor_id": actor_id,
        "target_id": target_id,
        "resource_type": resource_type,
        "details": details or {},
        "timestamp": datetime.now(timezone.utc),
        "ip_address": None,  # This would be filled in by the API endpoint
    }

    await audit_logs_collection.insert_one(log_data)
    return log_data


async def delete_user_books(user_id: str, book_ids: List[str] = None) -> bool:
    """
    Delete books associated with a user

    Args:
        user_id: The user's ID (clerk_id)
        book_ids: Optional list of specific book IDs to delete. If None, deletes all user's books.

    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        # Get books collection
        books_collection = database.get_collection("books")

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
