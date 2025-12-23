# backend/app/db/book.py

from .base import books_collection, users_collection
from bson.objectid import ObjectId
from datetime import datetime, timezone
from typing import Optional, List, Dict
from .audit_log import create_audit_log
from app.models.book import BookDB
from app.models.user import UserDB


# Book-related database operations
async def create_book(book_data: Dict, user_auth_id: str) -> Dict:
    """Create a new book in the database and associate it with a user"""
    try:
        # 1) Set owner ID
        book_data["owner_id"] = user_auth_id

        # 2) build the Pydantic model
        book_obj = BookDB(**book_data)
        # print(f"Creating book: {book_obj}")

        # 3) serialize to a Mongo-ready dict, with _id alias and timestamps
        payload = book_obj.model_dump(by_alias=True)

        # 4) Insert the new book
        print(f"database of the books_collection: {books_collection.database.name}")
        result = await books_collection.insert_one(payload)

        # 5) patch the real ObjectId back onto the model
        book_obj.id = result.inserted_id
        # print(f"Inserted book with ID: {book_obj.id}")

        # Associate the book with the user
        await users_collection.update_one(
            {"auth_id": user_auth_id}, {"$push": {"book_ids": str(book_obj.id)}}
        )

        print(f"Audit log: {user_auth_id}")
        # Create audit log entry
        await create_audit_log(
            action="book_create",
            actor_id=user_auth_id,
            target_id=str(book_obj.id),
            resource_type="book",
            details={"title": book_obj.title},
        )
        return payload
    except Exception as e:
        import traceback

        print(f"create_book_error {e}")
        traceback.print_exc()
        raise


async def get_book_by_id(book_id: str) -> Optional[Dict]:
    """Get a book by its ID"""
    # print(f"Getting book by ID: {book_id}")
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
    """Delete a book and remove its association from the user.

    This performs a cascade deletion, removing:
    - The book document
    - All questions for the book
    - All question responses for the book
    - Book association from the user
    """
    # First check if user owns the book
    book = await books_collection.find_one(
        {"_id": ObjectId(book_id), "owner_id": user_auth_id}
    )
    if not book:
        return False

    # Cascade delete: Remove all questions and responses for this book
    from app.db.questions import delete_questions_for_book
    await delete_questions_for_book(book_id=book_id, user_id=user_auth_id)

    # Delete the book
    result = await books_collection.delete_one({"_id": ObjectId(book_id)})

    # Remove book association from user
    if result.deleted_count > 0:
        await users_collection.update_one(
            {"auth_id": user_auth_id}, {"$pull": {"book_ids": book_id}}
        )

        # Create audit log entry
        await create_audit_log(
            action="book_delete",
            actor_id=user_auth_id,
            target_id=book_id,
            resource_type="book",
            details={"title": book.get("title", "Untitled")},
        )

        return True

    return False
