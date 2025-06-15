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
    # Check if we're in a test environment or if transactions are not supported
    use_transaction = True
    try:
        async with await _client.start_session() as session:
            # Test if transactions are supported
            info = await _client.admin.command('isMaster')
            use_transaction = info.get('setName') is not None  # Has replica set
    except Exception:
        use_transaction = False
    
    if use_transaction:
        async with await _client.start_session() as session:
            async with session.start_transaction():
                return await _update_toc_internal(book_id, toc_data, user_clerk_id, session)
    else:
        # Fallback for test environment without transactions
        return await _update_toc_internal(book_id, toc_data, user_clerk_id, None)


async def _update_toc_internal(
    book_id: str,
    toc_data: Dict[str, Any],
    user_clerk_id: str,
    session: Optional[AsyncIOMotorClientSession]
) -> Dict[str, Any]:
    """Internal function to update TOC with or without transaction"""
    # Get current book with version check
    try:
        book_oid = ObjectId(book_id)
    except Exception as e:
        raise ValueError(f"Invalid book ID format: {book_id}")
        
    find_query = {"_id": book_oid, "owner_id": user_clerk_id}
    
    # Debug logging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Looking for book with query: {find_query}")
    
    book = await books_collection.find_one(find_query, session=session)
    
    if not book:
        # Try without owner check to see if it's auth or existence issue
        book_exists = await books_collection.find_one(
            {"_id": book_oid},
            session=session
        )
        if book_exists:
            raise ValueError("Not authorized to update this book")
        else:
            raise ValueError("Book not found")
    
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
        "version": current_version + 1
    }
    
    # Assign IDs to chapters that don't have them
    for chapter in updated_toc.get("chapters", []):
        if not chapter.get("id"):
            chapter["id"] = str(uuid.uuid4())
        # Also handle subchapters
        for subchapter in chapter.get("subchapters", []):
            if not subchapter.get("id"):
                subchapter["id"] = str(uuid.uuid4())
    
    # Update the book with the new TOC
    # For new books without TOC, don't check version
    update_query = {
        "_id": book_oid,
        "owner_id": user_clerk_id
    }
    
    # Only add version check if TOC exists
    if current_toc:
        update_query["table_of_contents.version"] = current_version
    
    update_result = await books_collection.update_one(
        update_query,
        {
            "$set": {
                "table_of_contents": updated_toc,
                "updated_at": datetime.now(timezone.utc)
            }
        },
        session=session
    )
    
    if update_result.modified_count == 0:
        # Check if it was a version conflict
        current_book = await books_collection.find_one(
            {"_id": book_oid},
            session=session
        )
        if current_book:
            current_v = current_book.get("table_of_contents", {}).get("version", 1)
            if current_v != current_version:
                raise ValueError(f"Version conflict: TOC was updated by another process")
        raise ValueError("Failed to update TOC")
    
    # Log the update
    await create_audit_log(
        action="update_toc",
        actor_id=user_clerk_id,
        target_id=book_id,
        resource_type="book",
        details={
            "chapters_count": len(updated_toc.get("chapters", [])),
            "version": updated_toc["version"]
        },
        session=session
    )
    
    return updated_toc


async def add_chapter_with_transaction(
    book_id: str,
    chapter_data: Dict[str, Any],
    user_clerk_id: str,
    parent_chapter_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Add a new chapter or subchapter with transaction support.
    """
    use_transaction = True
    try:
        async with await _client.start_session() as session:
            info = await _client.admin.command('isMaster')
            use_transaction = info.get('setName') is not None
    except Exception:
        use_transaction = False
    
    if use_transaction:
        async with await _client.start_session() as session:
            async with session.start_transaction():
                return await _add_chapter_internal(book_id, chapter_data, user_clerk_id, parent_chapter_id, session)
    else:
        return await _add_chapter_internal(book_id, chapter_data, user_clerk_id, parent_chapter_id, None)


async def _add_chapter_internal(
    book_id: str,
    chapter_data: Dict[str, Any],
    user_clerk_id: str,
    parent_chapter_id: Optional[str],
    session: Optional[AsyncIOMotorClientSession]
) -> Dict[str, Any]:
    """Internal function to add chapter with or without transaction"""
    # Get the book
    book = await books_collection.find_one(
        {"_id": ObjectId(book_id), "owner_id": user_clerk_id},
        session=session
    )
    if not book:
        raise ValueError("Book not found or not authorized")
    
    toc = book.get("table_of_contents", {})
    chapters = toc.get("chapters", [])
    
    # Generate chapter ID if not provided
    if not chapter_data.get("id"):
        chapter_data["id"] = str(uuid.uuid4())
    
    # Add timestamps
    now = datetime.now(timezone.utc).isoformat()
    chapter_data["created_at"] = now
    chapter_data["updated_at"] = now
    
    if parent_chapter_id:
        # Adding a subchapter
        parent_found = False
        for chapter in chapters:
            if chapter.get("id") == parent_chapter_id:
                if "subchapters" not in chapter:
                    chapter["subchapters"] = []
                chapter["subchapters"].append(chapter_data)
                parent_found = True
                break
        
        if not parent_found:
            raise ValueError("Parent chapter not found")
    else:
        # Adding a top-level chapter
        chapters.append(chapter_data)
    
    # Update TOC version
    toc["chapters"] = chapters
    toc["version"] = toc.get("version", 1) + 1
    toc["updated_at"] = now
    
    # Update the book
    await books_collection.update_one(
        {"_id": ObjectId(book_id)},
        {
            "$set": {
                "table_of_contents": toc,
                "updated_at": datetime.now(timezone.utc)
            }
        },
        session=session
    )
    
    return chapter_data


async def update_chapter_with_transaction(
    book_id: str,
    chapter_id: str,
    chapter_updates: Dict[str, Any],
    user_clerk_id: str
) -> Dict[str, Any]:
    """
    Update a chapter with transaction support.
    """
    use_transaction = True
    try:
        async with await _client.start_session() as session:
            info = await _client.admin.command('isMaster')
            use_transaction = info.get('setName') is not None
    except Exception:
        use_transaction = False
    
    if use_transaction:
        async with await _client.start_session() as session:
            async with session.start_transaction():
                return await _update_chapter_internal(book_id, chapter_id, chapter_updates, user_clerk_id, session)
    else:
        return await _update_chapter_internal(book_id, chapter_id, chapter_updates, user_clerk_id, None)


async def _update_chapter_internal(
    book_id: str,
    chapter_id: str,
    chapter_updates: Dict[str, Any],
    user_clerk_id: str,
    session: Optional[AsyncIOMotorClientSession]
) -> Dict[str, Any]:
    """Internal function to update chapter with or without transaction"""
    # Get the book
    book = await books_collection.find_one(
        {"_id": ObjectId(book_id), "owner_id": user_clerk_id},
        session=session
    )
    if not book:
        raise ValueError("Book not found or not authorized")
    
    toc = book.get("table_of_contents", {})
    chapters = toc.get("chapters", [])
    
    # Find and update the chapter
    chapter_found = False
    updated_chapter = None
    
    def update_chapter_recursive(chapters_list):
        nonlocal chapter_found, updated_chapter
        for i, chapter in enumerate(chapters_list):
            if chapter.get("id") == chapter_id:
                # Update the chapter
                chapters_list[i] = {**chapter, **chapter_updates}
                chapters_list[i]["updated_at"] = datetime.now(timezone.utc).isoformat()
                chapter_found = True
                updated_chapter = chapters_list[i]
                return
            # Check subchapters
            if "subchapters" in chapter:
                update_chapter_recursive(chapter["subchapters"])
    
    update_chapter_recursive(chapters)
    
    if not chapter_found:
        raise ValueError("Chapter not found")
    
    # Update TOC version
    toc["chapters"] = chapters
    toc["version"] = toc.get("version", 1) + 1
    toc["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    # Update the book
    await books_collection.update_one(
        {"_id": ObjectId(book_id)},
        {
            "$set": {
                "table_of_contents": toc,
                "updated_at": datetime.now(timezone.utc)
            }
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
    """
    use_transaction = True
    try:
        async with await _client.start_session() as session:
            info = await _client.admin.command('isMaster')
            use_transaction = info.get('setName') is not None
    except Exception:
        use_transaction = False
    
    if use_transaction:
        async with await _client.start_session() as session:
            async with session.start_transaction():
                return await _delete_chapter_internal(book_id, chapter_id, user_clerk_id, session)
    else:
        return await _delete_chapter_internal(book_id, chapter_id, user_clerk_id, None)


async def _delete_chapter_internal(
    book_id: str,
    chapter_id: str,
    user_clerk_id: str,
    session: Optional[AsyncIOMotorClientSession]
) -> bool:
    """Internal function to delete chapter with or without transaction"""
    # Get the book
    book = await books_collection.find_one(
        {"_id": ObjectId(book_id), "owner_id": user_clerk_id},
        session=session
    )
    if not book:
        raise ValueError("Book not found or not authorized")
    
    toc = book.get("table_of_contents", {})
    chapters = toc.get("chapters", [])
    
    # Find and delete the chapter
    chapter_found = False
    
    def delete_chapter_recursive(chapters_list):
        nonlocal chapter_found
        for i, chapter in enumerate(chapters_list):
            if chapter.get("id") == chapter_id:
                chapters_list.pop(i)
                chapter_found = True
                return
            # Check subchapters
            if "subchapters" in chapter:
                delete_chapter_recursive(chapter["subchapters"])
    
    delete_chapter_recursive(chapters)
    
    if not chapter_found:
        raise ValueError("Chapter not found")
    
    # Update TOC version
    toc["chapters"] = chapters
    toc["version"] = toc.get("version", 1) + 1
    toc["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    # Update the book
    await books_collection.update_one(
        {"_id": ObjectId(book_id)},
        {
            "$set": {
                "table_of_contents": toc,
                "updated_at": datetime.now(timezone.utc)
            }
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
    Reorder chapters with transaction support.
    chapter_orders should be a list of {"id": "chapter_id", "order": 1}
    """
    use_transaction = True
    try:
        async with await _client.start_session() as session:
            info = await _client.admin.command('isMaster')
            use_transaction = info.get('setName') is not None
    except Exception:
        use_transaction = False
    
    if use_transaction:
        async with await _client.start_session() as session:
            async with session.start_transaction():
                return await _reorder_chapters_internal(book_id, chapter_orders, user_clerk_id, session)
    else:
        return await _reorder_chapters_internal(book_id, chapter_orders, user_clerk_id, None)


async def _reorder_chapters_internal(
    book_id: str,
    chapter_orders: List[Dict[str, Any]],
    user_clerk_id: str,
    session: Optional[AsyncIOMotorClientSession]
) -> Dict[str, Any]:
    """Internal function to reorder chapters with or without transaction"""
    # Get the book
    book = await books_collection.find_one(
        {"_id": ObjectId(book_id), "owner_id": user_clerk_id},
        session=session
    )
    if not book:
        raise ValueError("Book not found or not authorized")
    
    toc = book.get("table_of_contents", {})
    chapters = toc.get("chapters", [])
    
    # Create a map of chapter IDs to chapters
    chapter_map = {}
    for chapter in chapters:
        chapter_map[chapter.get("id")] = chapter
    
    # Reorder chapters based on provided order
    new_chapters = []
    for order_item in sorted(chapter_orders, key=lambda x: x["order"]):
        chapter_id = order_item["id"]
        if chapter_id in chapter_map:
            chapter = chapter_map[chapter_id]
            chapter["order"] = order_item["order"]
            new_chapters.append(chapter)
    
    # Add any chapters that weren't in the order list at the end
    for chapter in chapters:
        if chapter.get("id") not in [o["id"] for o in chapter_orders]:
            new_chapters.append(chapter)
    
    # Update TOC
    toc["chapters"] = new_chapters
    toc["version"] = toc.get("version", 1) + 1
    toc["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    # Update the book
    await books_collection.update_one(
        {"_id": ObjectId(book_id)},
        {
            "$set": {
                "table_of_contents": toc,
                "updated_at": datetime.now(timezone.utc)
            }
        },
        session=session
    )
    
    return toc