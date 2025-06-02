"""
Enhanced book deletion with cascade delete functionality.
This module provides a complete cascade deletion implementation for books.
"""

from bson.objectid import ObjectId
from typing import Optional
from .base import books_collection, users_collection, get_collection
from .audit_log import create_audit_log


async def delete_book_with_cascade(book_id: str, user_clerk_id: str) -> bool:
    """
    Delete a book and cascade delete all related data including:
    - Cover images
    - Chapter access logs
    - Questions and question responses
    - Question ratings
    - Any other related data
    """
    # First check if user owns the book
    book = await books_collection.find_one(
        {"_id": ObjectId(book_id), "owner_id": user_clerk_id}
    )
    if not book:
        return False

    # Import required services for cleanup
    from app.services.file_upload_service import file_upload_service
    
    # Delete associated cover images if they exist
    cover_image_url = book.get("cover_image_url")
    cover_thumbnail_url = book.get("cover_thumbnail_url")
    if cover_image_url:
        try:
            await file_upload_service.delete_cover_image(cover_image_url, cover_thumbnail_url)
        except Exception as e:
            # Log error but don't fail the deletion
            print(f"Error deleting cover images for book {book_id}: {e}")
    
    # Delete chapter access logs
    chapter_access_logs = get_collection("chapter_access_logs")
    access_logs_result = await chapter_access_logs.delete_many({"book_id": book_id})
    
    # Delete questions and question-related data
    questions_collection = get_collection("questions")
    question_responses_collection = get_collection("question_responses")
    question_ratings_collection = get_collection("question_ratings")
    
    # Get all questions for this book
    questions_cursor = questions_collection.find({"book_id": book_id})
    question_ids = []
    async for question in questions_cursor:
        question_ids.append(str(question["_id"]))
    
    # Delete all question-related data
    responses_deleted = 0
    ratings_deleted = 0
    if question_ids:
        responses_result = await question_responses_collection.delete_many(
            {"question_id": {"$in": question_ids}}
        )
        responses_deleted = responses_result.deleted_count
        
        ratings_result = await question_ratings_collection.delete_many(
            {"question_id": {"$in": question_ids}}
        )
        ratings_deleted = ratings_result.deleted_count
    
    questions_result = await questions_collection.delete_many({"book_id": book_id})
    
    # Delete the book
    result = await books_collection.delete_one({"_id": ObjectId(book_id)})

    # Remove book association from user
    if result.deleted_count > 0:
        await users_collection.update_one(
            {"clerk_id": user_clerk_id}, {"$pull": {"book_ids": book_id}}
        )

        # Create detailed audit log entry
        await create_audit_log(
            action="book_delete",
            actor_id=user_clerk_id,
            target_id=book_id,
            resource_type="book",
            details={
                "title": book.get("title", "Untitled"),
                "cascade_deleted": {
                    "cover_images": bool(cover_image_url),
                    "chapter_access_logs": access_logs_result.deleted_count,
                    "questions": questions_result.deleted_count,
                    "question_responses": responses_deleted,
                    "question_ratings": ratings_deleted,
                }
            },
        )

        return True

    return False


async def soft_delete_book(book_id: str, user_clerk_id: str) -> bool:
    """
    Soft delete a book by marking it as deleted without removing data.
    This allows for potential recovery of the book and its content.
    """
    from datetime import datetime, timezone
    
    # Check if user owns the book
    book = await books_collection.find_one(
        {"_id": ObjectId(book_id), "owner_id": user_clerk_id}
    )
    if not book:
        return False
    
    # Mark book as deleted
    update_result = await books_collection.update_one(
        {"_id": ObjectId(book_id)},
        {
            "$set": {
                "is_deleted": True,
                "deleted_at": datetime.now(timezone.utc),
                "deleted_by": user_clerk_id
            }
        }
    )
    
    if update_result.modified_count > 0:
        # Create audit log entry
        await create_audit_log(
            action="book_soft_delete",
            actor_id=user_clerk_id,
            target_id=book_id,
            resource_type="book",
            details={
                "title": book.get("title", "Untitled"),
                "soft_deleted": True
            },
        )
        return True
    
    return False


async def restore_soft_deleted_book(book_id: str, user_clerk_id: str) -> bool:
    """
    Restore a soft-deleted book.
    """
    # Check if user owns the book and it's soft deleted
    book = await books_collection.find_one(
        {
            "_id": ObjectId(book_id), 
            "owner_id": user_clerk_id,
            "is_deleted": True
        }
    )
    if not book:
        return False
    
    # Remove soft delete markers
    update_result = await books_collection.update_one(
        {"_id": ObjectId(book_id)},
        {
            "$unset": {
                "is_deleted": "",
                "deleted_at": "",
                "deleted_by": ""
            }
        }
    )
    
    if update_result.modified_count > 0:
        # Create audit log entry
        await create_audit_log(
            action="book_restore",
            actor_id=user_clerk_id,
            target_id=book_id,
            resource_type="book",
            details={
                "title": book.get("title", "Untitled"),
                "restored": True
            },
        )
        return True
    
    return False
