"""
Transaction-based TOC (Table of Contents) operations for MongoDB.
Ensures atomic updates to prevent race conditions and maintain data consistency.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from bson.objectid import ObjectId
import uuid
from motor.motor_asyncio import AsyncIOMotorClientSession

from .base import _client, _db, books_collection, ObjectId
from .audit_log import create_audit_log


async def update_toc_with_transaction(
    book_id: str,
    toc_data: Dict[str, Any],
    user_clerk_id: str
) -> Dict[str, Any]:
    """
    Update TOC with transaction support to ensure atomicity.
    Uses optimistic locking with version checking.
    """
    async with await _client.start_session() as session:
        async with session.start_transaction():
            # Get current book with version check
            book = await books_collection.find_one(
                {"_id": ObjectId(book_id), "owner_id": user_clerk_id},
                session=session
            )
            
            if not book:
                raise ValueError("Book not found or not authorized")
            
            current_toc = book.get("table_of_contents", {})
            current_version = current_toc.get("version", 1)
            
            # Check if provided version matches current version (optimistic locking)
            if "expected_version" in toc_data:
                expected_version = toc_data.pop("expected_version")
                if current_version != expected_version:
                    raise ValueError(f"Version conflict: expected {expected_version}, current {current_version}")
            
            # Create updated TOC with atomic version increment
            updated_toc = {
                **toc_data,
                "generated_at": current_toc.get("generated_at"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "status": "edited",
                "version": current_version + 1,
            }
            
            # Update using atomic operators
            result = await books_collection.update_one(
                {
                    "_id": ObjectId(book_id),
                    "owner_id": user_clerk_id,
                    "table_of_contents.version": current_version  # Ensure version hasn't changed
                },
                {
                    "$set": {
                        "table_of_contents": updated_toc,
                        "updated_at": datetime.now(timezone.utc)
                    }
                },
                session=session
            )
            
            if result.modified_count == 0:
                raise ValueError("Concurrent modification detected, please retry")
            
            # Create audit log within transaction
            await create_audit_log(
                action="toc_update",
                actor_id=user_clerk_id,
                target_id=book_id,
                resource_type="toc",
                details={
                    "previous_version": current_version,
                    "new_version": updated_toc["version"],
                    "chapters_count": len(updated_toc.get("chapters", []))
                },
                session=session
            )
            
            return updated_toc


async def add_chapter_with_transaction(
    book_id: str,
    chapter_data: Dict[str, Any],
    parent_id: Optional[str],
    user_clerk_id: str
) -> Dict[str, Any]:
    """
    Add a new chapter with transaction support.
    Ensures unique chapter IDs and proper order management.
    """
    async with await _client.start_session() as session:
        async with session.start_transaction():
            # Get current book
            book = await books_collection.find_one(
                {"_id": ObjectId(book_id), "owner_id": user_clerk_id},
                session=session
            )
            
            if not book:
                raise ValueError("Book not found or not authorized")
            
            current_toc = book.get("table_of_contents", {"chapters": []})
            chapters = current_toc.get("chapters", [])
            
            # Generate unique chapter ID
            chapter_id = str(uuid.uuid4())
            
            # Ensure chapter ID is unique (defensive programming)
            existing_ids = _get_all_chapter_ids(chapters)
            while chapter_id in existing_ids:
                chapter_id = str(uuid.uuid4())
            
            # Create new chapter
            new_chapter = {
                "id": chapter_id,
                "title": chapter_data.get("title"),
                "description": chapter_data.get("description", ""),
                "order": chapter_data.get("order", 0),
                "parent_id": parent_id,
                "children": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "status": "draft",
                **{k: v for k, v in chapter_data.items() if k not in ["title", "description", "order"]}
            }
            
            # Add chapter to appropriate location
            if parent_id:
                chapters = _add_chapter_to_parent(chapters, parent_id, new_chapter)
            else:
                # Adjust order of existing chapters if needed
                if new_chapter["order"] is not None:
                    chapters = _insert_chapter_at_order(chapters, new_chapter)
                else:
                    new_chapter["order"] = len(chapters)
                    chapters.append(new_chapter)
            
            # Update TOC with atomic increment
            updated_toc = {
                **current_toc,
                "chapters": chapters,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "version": current_toc.get("version", 1) + 1,
            }
            
            # Perform atomic update
            result = await books_collection.update_one(
                {
                    "_id": ObjectId(book_id),
                    "owner_id": user_clerk_id,
                    "table_of_contents.version": current_toc.get("version", 1)
                },
                {
                    "$set": {
                        "table_of_contents": updated_toc,
                        "updated_at": datetime.now(timezone.utc)
                    }
                },
                session=session
            )
            
            if result.modified_count == 0:
                raise ValueError("Concurrent modification detected, please retry")
            
            # Create audit log
            await create_audit_log(
                action="chapter_create",
                actor_id=user_clerk_id,
                target_id=chapter_id,
                resource_type="chapter",
                details={
                    "book_id": book_id,
                    "parent_id": parent_id,
                    "title": new_chapter["title"]
                },
                session=session
            )
            
            return new_chapter


async def update_chapter_with_transaction(
    book_id: str,
    chapter_id: str,
    updates: Dict[str, Any],
    user_clerk_id: str
) -> Dict[str, Any]:
    """
    Update a chapter with transaction support.
    Handles nested chapters and maintains consistency.
    """
    async with await _client.start_session() as session:
        async with session.start_transaction():
            # Get current book
            book = await books_collection.find_one(
                {"_id": ObjectId(book_id), "owner_id": user_clerk_id},
                session=session
            )
            
            if not book:
                raise ValueError("Book not found or not authorized")
            
            current_toc = book.get("table_of_contents", {"chapters": []})
            chapters = current_toc.get("chapters", [])
            
            # Find and update chapter
            updated_chapter = None
            chapters, updated_chapter = _update_chapter_in_list(chapters, chapter_id, updates)
            
            if not updated_chapter:
                raise ValueError("Chapter not found")
            
            # Update TOC
            updated_toc = {
                **current_toc,
                "chapters": chapters,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "version": current_toc.get("version", 1) + 1,
            }
            
            # Perform atomic update
            result = await books_collection.update_one(
                {
                    "_id": ObjectId(book_id),
                    "owner_id": user_clerk_id,
                    "table_of_contents.version": current_toc.get("version", 1)
                },
                {
                    "$set": {
                        "table_of_contents": updated_toc,
                        "updated_at": datetime.now(timezone.utc)
                    }
                },
                session=session
            )
            
            if result.modified_count == 0:
                raise ValueError("Concurrent modification detected, please retry")
            
            # Create audit log
            await create_audit_log(
                action="chapter_update",
                actor_id=user_clerk_id,
                target_id=chapter_id,
                resource_type="chapter",
                details={
                    "book_id": book_id,
                    "updates": list(updates.keys())
                },
                session=session
            )
            
            return updated_chapter


async def delete_chapter_with_transaction(
    book_id: str,
    chapter_id: str,
    user_clerk_id: str
) -> bool:
    """
    Delete a chapter with transaction support.
    Ensures all related data is cleaned up atomically.
    """
    async with await _client.start_session() as session:
        async with session.start_transaction():
            # Get current book
            book = await books_collection.find_one(
                {"_id": ObjectId(book_id), "owner_id": user_clerk_id},
                session=session
            )
            
            if not book:
                raise ValueError("Book not found or not authorized")
            
            current_toc = book.get("table_of_contents", {"chapters": []})
            chapters = current_toc.get("chapters", [])
            
            # Remove chapter
            chapters, deleted = _remove_chapter_from_list(chapters, chapter_id)
            
            if not deleted:
                raise ValueError("Chapter not found")
            
            # Update TOC
            updated_toc = {
                **current_toc,
                "chapters": chapters,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "version": current_toc.get("version", 1) + 1,
            }
            
            # Perform atomic update
            result = await books_collection.update_one(
                {
                    "_id": ObjectId(book_id),
                    "owner_id": user_clerk_id,
                    "table_of_contents.version": current_toc.get("version", 1)
                },
                {
                    "$set": {
                        "table_of_contents": updated_toc,
                        "updated_at": datetime.now(timezone.utc)
                    }
                },
                session=session
            )
            
            if result.modified_count == 0:
                raise ValueError("Concurrent modification detected, please retry")
            
            # Delete related questions (if any)
            questions_collection = _db.get_collection("questions")
            await questions_collection.delete_many(
                {"chapter_id": chapter_id},
                session=session
            )
            
            # Create audit log
            await create_audit_log(
                action="chapter_delete",
                actor_id=user_clerk_id,
                target_id=chapter_id,
                resource_type="chapter",
                details={
                    "book_id": book_id
                },
                session=session
            )
            
            return True


async def reorder_chapters_with_transaction(
    book_id: str,
    chapter_orders: List[Dict[str, Any]],
    user_clerk_id: str
) -> Dict[str, Any]:
    """
    Reorder chapters atomically to prevent inconsistent states.
    """
    async with await _client.start_session() as session:
        async with session.start_transaction():
            # Get current book
            book = await books_collection.find_one(
                {"_id": ObjectId(book_id), "owner_id": user_clerk_id},
                session=session
            )
            
            if not book:
                raise ValueError("Book not found or not authorized")
            
            current_toc = book.get("table_of_contents", {"chapters": []})
            chapters = current_toc.get("chapters", [])
            
            # Apply new order
            for order_update in chapter_orders:
                chapter_id = order_update.get("id")
                new_order = order_update.get("order")
                parent_id = order_update.get("parent_id")
                
                chapters = _update_chapter_order(chapters, chapter_id, new_order, parent_id)
            
            # Update TOC
            updated_toc = {
                **current_toc,
                "chapters": chapters,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "version": current_toc.get("version", 1) + 1,
            }
            
            # Perform atomic update
            result = await books_collection.update_one(
                {
                    "_id": ObjectId(book_id),
                    "owner_id": user_clerk_id,
                    "table_of_contents.version": current_toc.get("version", 1)
                },
                {
                    "$set": {
                        "table_of_contents": updated_toc,
                        "updated_at": datetime.now(timezone.utc)
                    }
                },
                session=session
            )
            
            if result.modified_count == 0:
                raise ValueError("Concurrent modification detected, please retry")
            
            # Create audit log
            await create_audit_log(
                action="chapters_reorder",
                actor_id=user_clerk_id,
                target_id=book_id,
                resource_type="toc",
                details={
                    "chapters_reordered": len(chapter_orders)
                },
                session=session
            )
            
            return updated_toc


# Helper functions

def _get_all_chapter_ids(chapters: List[Dict]) -> set:
    """Recursively get all chapter IDs."""
    ids = set()
    for chapter in chapters:
        ids.add(chapter["id"])
        if "children" in chapter:
            ids.update(_get_all_chapter_ids(chapter["children"]))
    return ids


def _add_chapter_to_parent(chapters: List[Dict], parent_id: str, new_chapter: Dict) -> List[Dict]:
    """Add a chapter as a child of the specified parent."""
    for chapter in chapters:
        if chapter["id"] == parent_id:
            if "children" not in chapter:
                chapter["children"] = []
            chapter["children"].append(new_chapter)
            return chapters
        elif "children" in chapter:
            chapter["children"] = _add_chapter_to_parent(chapter["children"], parent_id, new_chapter)
    return chapters


def _insert_chapter_at_order(chapters: List[Dict], new_chapter: Dict) -> List[Dict]:
    """Insert a chapter at the specified order, adjusting other chapters."""
    order = new_chapter["order"]
    # Adjust orders of existing chapters
    for chapter in chapters:
        if chapter.get("order", 0) >= order:
            chapter["order"] = chapter.get("order", 0) + 1
    
    # Insert the new chapter
    chapters.append(new_chapter)
    chapters.sort(key=lambda x: x.get("order", 0))
    return chapters


def _update_chapter_in_list(chapters: List[Dict], chapter_id: str, updates: Dict) -> tuple:
    """Update a chapter in the list and return the updated list and chapter."""
    updated_chapter = None
    for i, chapter in enumerate(chapters):
        if chapter["id"] == chapter_id:
            chapters[i] = {
                **chapter,
                **updates,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            updated_chapter = chapters[i]
            break
        elif "children" in chapter:
            chapter["children"], child_updated = _update_chapter_in_list(
                chapter["children"], chapter_id, updates
            )
            if child_updated:
                updated_chapter = child_updated
    
    return chapters, updated_chapter


def _remove_chapter_from_list(chapters: List[Dict], chapter_id: str) -> tuple:
    """Remove a chapter from the list and return the updated list."""
    deleted = False
    updated_chapters = []
    
    for chapter in chapters:
        if chapter["id"] == chapter_id:
            deleted = True
            continue
        
        if "children" in chapter:
            chapter["children"], child_deleted = _remove_chapter_from_list(
                chapter["children"], chapter_id
            )
            deleted = deleted or child_deleted
        
        updated_chapters.append(chapter)
    
    return updated_chapters, deleted


def _update_chapter_order(chapters: List[Dict], chapter_id: str, new_order: int, parent_id: Optional[str]) -> List[Dict]:
    """Update the order of a specific chapter."""
    # This is a simplified version - in production, you'd want more sophisticated logic
    # to handle moving chapters between parents, etc.
    for chapter in chapters:
        if chapter["id"] == chapter_id:
            chapter["order"] = new_order
            if parent_id is not None:
                chapter["parent_id"] = parent_id
        elif "children" in chapter:
            chapter["children"] = _update_chapter_order(
                chapter["children"], chapter_id, new_order, parent_id
            )
    
    # Re-sort chapters by order
    chapters.sort(key=lambda x: x.get("order", 0))
    return chapters