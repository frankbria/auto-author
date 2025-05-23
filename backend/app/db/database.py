from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from bson.objectid import ObjectId
from app.core.config import settings
from app.models.book import BookDB
from app.models.user import UserDB
import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

# Initialize MongoDB connection
client = AsyncIOMotorClient(settings.DATABASE_URI)
database = client[settings.DATABASE_NAME]

# Collections
users_collection = database.get_collection("users")
books_collection = database.get_collection("books")
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
    user_data["updated_at"] = datetime.now(timezone.utc)

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
            {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}},
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


# Book-related database operations
async def create_book(book_data: Dict, user_clerk_id: str) -> Dict:
    """Create a new book in the database and associate it with a user"""
    # 1) Set owner ID
    book_data["owner_id"] = user_clerk_id

    # 2) build the Pydantic model
    book_obj = BookDB(**book_data)
    # print(f"Creating book: {book_obj}")

    # 3) serialize to a Mongo-ready dict, with _id alias and timestamps
    payload = book_obj.model_dump(by_alias=True)

    # 4) Insert the new book
    result = await books_collection.insert_one(payload)

    # 5) patch the real ObjectId back onto the model
    book_obj.id = result.inserted_id
    # print(f"Inserted book with ID: {book_obj.id}")

    # Associate the book with the user
    await users_collection.update_one(
        {"clerk_id": user_clerk_id}, {"$push": {"book_ids": str(book_obj.id)}}
    )

    # Create audit log entry
    await create_audit_log(
        action="book_create",
        actor_id=user_clerk_id,
        target_id=str(book_obj.id),
        resource_type="book",
        details={"title": book_data.get("title", "Untitled")},
    )

    # Return the created book
    # created_book = await get_book_by_id(str(book_obj.id))
    created_book = book_obj.model_dump()
    # print(f"Created book: {created_book}")
    created_book["id"] = str(book_obj.id)
    created_book.pop("_id", None)  # Remove the MongoDB ObjectId field
    return created_book


async def get_book_by_id(book_id: str) -> Optional[Dict]:
    """Get a book by its ID"""
    # print(f"Getting book by ID: {book_id}")
    try:
        book = await books_collection.find_one({"_id": ObjectId(book_id)})
        return book
    except Exception:
        return None


async def get_books_by_user(
    user_clerk_id: str, skip: int = 0, limit: int = 100
) -> List[Dict]:
    """Get all books owned by a user"""
    cursor = books_collection.find({"owner_id": user_clerk_id}).skip(skip).limit(limit)
    books = await cursor.to_list(length=limit)
    return books


async def update_book(
    book_id: str, book_data: Dict, user_clerk_id: str
) -> Optional[Dict]:
    """Update an existing book"""
    # Add updated_at timestamp
    book_data["updated_at"] = datetime.now(timezone.utc)

    # Update the book
    updated_book = await books_collection.find_one_and_update(
        {"_id": ObjectId(book_id), "owner_id": user_clerk_id},  # Only owner can update
        {"$set": book_data},
        return_document=True,
    )

    # Create audit log entry if book was found and updated
    if updated_book:
        await create_audit_log(
            action="book_update",
            actor_id=user_clerk_id,
            target_id=book_id,
            resource_type="book",
            details={"updated_fields": list(book_data.keys())},
        )

    return updated_book


async def delete_book(book_id: str, user_clerk_id: str) -> bool:
    """Delete a book and remove its association from the user"""
    # First check if user owns the book
    book = await books_collection.find_one(
        {"_id": ObjectId(book_id), "owner_id": user_clerk_id}
    )
    if not book:
        return False

    # Delete the book
    result = await books_collection.delete_one({"_id": ObjectId(book_id)})

    # Remove book association from user
    if result.deleted_count > 0:
        await users_collection.update_one(
            {"clerk_id": user_clerk_id}, {"$pull": {"book_ids": book_id}}
        )

        # Create audit log entry
        await create_audit_log(
            action="book_delete",
            actor_id=user_clerk_id,
            target_id=book_id,
            resource_type="book",
            details={"title": book.get("title", "Untitled")},
        )

        return True

    return False
