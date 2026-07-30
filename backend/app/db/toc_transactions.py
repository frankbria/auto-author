"""
Transaction-based TOC (Table of Contents) operations for MongoDB.
Ensures atomic updates to prevent race conditions and maintain data consistency.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from bson.objectid import ObjectId
import uuid
from motor.motor_asyncio import AsyncIOMotorClientSession

from .base import books_collection, ObjectId
from .audit_log import create_audit_log


def _version_guard(current_toc: Dict[str, Any]) -> Any:
    """Snapshot the read-time TOC version as an ``update_one`` filter value.

    MUST be called *before* the TOC dict is mutated — callers mutate the dict
    they read in place, so reading the version after mutation would guard on
    the value we are about to write and never detect a conflict.

    A legacy TOC with no ``version`` field is matched on its *absence* rather
    than on a defaulted 1, otherwise its first guarded write would always look
    like a conflict.
    """
    return current_toc["version"] if "version" in current_toc else {"$exists": False}


async def _set_toc_guarded(
    book_oid: ObjectId,
    user_auth_id: str,
    updated_toc: Dict[str, Any],
    version_guard: Any,
    session: Optional[AsyncIOMotorClientSession] = None,
) -> None:
    """Compare-and-swap the whole ``table_of_contents`` under an optimistic lock.

    Every caller here reads the TOC, mutates it in memory, and writes it back
    whole. Filtering that write on the version we read makes it a no-op if
    another writer (e.g. the autosave path) committed in between, so concurrent
    edits raise instead of silently clobbering each other. This holds on
    standalone Mongo too, where ``session`` is ``None`` and there is no
    transaction to abort (#337).

    ``version_guard`` comes from :func:`_version_guard`, captured before the
    caller mutated the TOC.

    ``modified_count`` (rather than ``matched_count``) is a sufficient conflict
    signal only because every caller increments ``version`` — the document can
    never be written identically, so a matched-but-unmodified result is
    impossible. An idempotent write added here later would need
    ``matched_count``.
    """
    result = await books_collection.update_one(
        {
            "_id": book_oid,
            "owner_id": user_auth_id,
            "table_of_contents.version": version_guard,
        },
        {
            "$set": {
                "table_of_contents": updated_toc,
                "updated_at": datetime.now(timezone.utc),
            }
        },
        session=session,
    )

    if result.modified_count == 0:
        # The filter missed — but "someone bumped the version" is only one of
        # three reasons. Re-read to distinguish, so the API can answer 404/403
        # instead of a misleading "modified by another user" 409. This mirrors
        # the re-read `_update_toc_internal` already does, and only costs a read
        # on the failure path.
        current = await books_collection.find_one({"_id": book_oid}, session=session)
        if not current:
            raise ValueError("Book not found")
        if current.get("owner_id") != user_auth_id:
            raise ValueError("Not authorized to modify this book")
        raise ValueError("Version conflict: TOC was updated by another process")


async def update_toc_with_transaction(
    book_id: str,
    toc_data: Dict[str, Any],
    user_auth_id: str
) -> Dict[str, Any]:
    """
    Update TOC with transaction support to ensure atomicity.
    Uses optimistic locking with version checking.

    Runs as a single compare-and-swap, deliberately WITHOUT a transaction.

    These are single-document writes: one read of the book, one guarded
    ``update_one`` filtered on the version that read observed. The CAS is atomic
    on its own, so a transaction adds nothing — and actively breaks the 409
    contract on a replica set. Inside a transaction the guarded update reads at
    the transaction snapshot, so the version filter always matches and the
    conflict never raises ValueError; the genuine conflict aborts at COMMIT as a
    WriteConflict, which reaches the endpoint as a generic OperationFailure and
    becomes a 500. Without the transaction the filter misses, ValueError is
    raised, and the endpoint returns 409 on every topology (#369).

    ``update_chapter_statuses_with_version_guard`` (#159) already took this
    route for the same reason.
    """
    return await _update_toc_internal(book_id, toc_data, user_auth_id, None)


async def _update_toc_internal(
    book_id: str,
    toc_data: Dict[str, Any],
    user_auth_id: str,
    session: Optional[AsyncIOMotorClientSession]
) -> Dict[str, Any]:
    """Internal function to update TOC with or without transaction"""
    # Get current book with version check
    try:
        book_oid = ObjectId(book_id)
    except Exception as e:
        raise ValueError(f"Invalid book ID format: {book_id}")

    find_query = {"_id": book_oid, "owner_id": user_auth_id}

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
        "owner_id": user_auth_id
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
        actor_id=user_auth_id,
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
    user_auth_id: str,
    parent_chapter_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Add a new chapter or subchapter with transaction support.

    Runs as a single compare-and-swap, deliberately WITHOUT a transaction.

    These are single-document writes: one read of the book, one guarded
    ``update_one`` filtered on the version that read observed. The CAS is atomic
    on its own, so a transaction adds nothing — and actively breaks the 409
    contract on a replica set. Inside a transaction the guarded update reads at
    the transaction snapshot, so the version filter always matches and the
    conflict never raises ValueError; the genuine conflict aborts at COMMIT as a
    WriteConflict, which reaches the endpoint as a generic OperationFailure and
    becomes a 500. Without the transaction the filter misses, ValueError is
    raised, and the endpoint returns 409 on every topology (#369).

    ``update_chapter_statuses_with_version_guard`` (#159) already took this
    route for the same reason.
    """
    return await _add_chapter_internal(book_id, chapter_data, user_auth_id, parent_chapter_id, None)


async def _add_chapter_internal(
    book_id: str,
    chapter_data: Dict[str, Any],
    user_auth_id: str,
    parent_chapter_id: Optional[str],
    session: Optional[AsyncIOMotorClientSession]
) -> Dict[str, Any]:
    """Internal function to add chapter with or without transaction"""
    # Get the book
    book = await books_collection.find_one(
        {"_id": ObjectId(book_id), "owner_id": user_auth_id},
        session=session
    )
    if not book:
        raise ValueError("Book not found or not authorized")

    toc = book.get("table_of_contents", {})
    version_guard = _version_guard(toc)  # snapshot before mutating `toc`
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
    await _set_toc_guarded(
        ObjectId(book_id), user_auth_id, toc, version_guard, session
    )

    return chapter_data


async def update_chapter_with_transaction(
    book_id: str,
    chapter_id: str,
    chapter_updates: Dict[str, Any],
    user_auth_id: str
) -> Dict[str, Any]:
    """
    Update a chapter with transaction support.

    Runs as a single compare-and-swap, deliberately WITHOUT a transaction.

    These are single-document writes: one read of the book, one guarded
    ``update_one`` filtered on the version that read observed. The CAS is atomic
    on its own, so a transaction adds nothing — and actively breaks the 409
    contract on a replica set. Inside a transaction the guarded update reads at
    the transaction snapshot, so the version filter always matches and the
    conflict never raises ValueError; the genuine conflict aborts at COMMIT as a
    WriteConflict, which reaches the endpoint as a generic OperationFailure and
    becomes a 500. Without the transaction the filter misses, ValueError is
    raised, and the endpoint returns 409 on every topology (#369).

    ``update_chapter_statuses_with_version_guard`` (#159) already took this
    route for the same reason.
    """
    return await _update_chapter_internal(book_id, chapter_id, chapter_updates, user_auth_id, None)


async def _update_chapter_internal(
    book_id: str,
    chapter_id: str,
    chapter_updates: Dict[str, Any],
    user_auth_id: str,
    session: Optional[AsyncIOMotorClientSession]
) -> Dict[str, Any]:
    """Internal function to update chapter with or without transaction"""
    # Get the book
    book = await books_collection.find_one(
        {"_id": ObjectId(book_id), "owner_id": user_auth_id},
        session=session
    )
    if not book:
        raise ValueError("Book not found or not authorized")

    toc = book.get("table_of_contents", {})
    version_guard = _version_guard(toc)  # snapshot before mutating `toc`
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
    await _set_toc_guarded(
        ObjectId(book_id), user_auth_id, toc, version_guard, session
    )

    return updated_chapter


async def delete_chapter_with_transaction(
    book_id: str,
    chapter_id: str,
    user_auth_id: str
) -> bool:
    """
    Delete a chapter with transaction support.

    Runs as a single compare-and-swap, deliberately WITHOUT a transaction.

    These are single-document writes: one read of the book, one guarded
    ``update_one`` filtered on the version that read observed. The CAS is atomic
    on its own, so a transaction adds nothing — and actively breaks the 409
    contract on a replica set. Inside a transaction the guarded update reads at
    the transaction snapshot, so the version filter always matches and the
    conflict never raises ValueError; the genuine conflict aborts at COMMIT as a
    WriteConflict, which reaches the endpoint as a generic OperationFailure and
    becomes a 500. Without the transaction the filter misses, ValueError is
    raised, and the endpoint returns 409 on every topology (#369).

    ``update_chapter_statuses_with_version_guard`` (#159) already took this
    route for the same reason.
    """
    return await _delete_chapter_internal(book_id, chapter_id, user_auth_id, None)


async def _delete_chapter_internal(
    book_id: str,
    chapter_id: str,
    user_auth_id: str,
    session: Optional[AsyncIOMotorClientSession]
) -> bool:
    """Internal function to delete chapter with or without transaction"""
    # Get the book
    book = await books_collection.find_one(
        {"_id": ObjectId(book_id), "owner_id": user_auth_id},
        session=session
    )
    if not book:
        raise ValueError("Book not found or not authorized")

    toc = book.get("table_of_contents", {})
    version_guard = _version_guard(toc)  # snapshot before mutating `toc`
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
    await _set_toc_guarded(
        ObjectId(book_id), user_auth_id, toc, version_guard, session
    )

    return True


async def update_chapter_statuses_with_version_guard(
    book_id: str,
    chapter_ids: List[str],
    new_status: str,
    user_auth_id: str,
    expected_version: int,
    update_timestamp: bool = False,
) -> Dict[str, Any]:
    """
    Bulk-update chapter statuses under an optimistic-concurrency guard.

    A bulk status change touches a single book document, so a single
    compare-and-swap ``update_one`` (filtered on ``table_of_contents.version``,
    the same guard ``_update_toc_internal`` uses) is atomic on its own — no
    multi-document transaction needed. If a concurrent TOC edit bumps the
    version between the read and the write, ``modified_count`` is 0 and we raise
    a ``Version conflict`` instead of silently clobbering the other write. This
    holds on both replica-set and standalone deployments (unlike a transaction,
    which would surface a concurrent commit as a WriteConflict).

    ``expected_version`` is the version the caller validated against.
    """
    book_oid = ObjectId(book_id)
    book = await books_collection.find_one({"_id": book_oid, "owner_id": user_auth_id})
    if not book:
        if await books_collection.find_one({"_id": book_oid}):
            raise ValueError("Not authorized to update this book")
        raise ValueError("Book not found")

    current_toc = book.get("table_of_contents", {})
    current_version = current_toc.get("version", 1)
    if current_version != expected_version:
        raise ValueError(
            f"Version conflict: expected {expected_version}, current {current_version}"
        )

    chapters = current_toc.get("chapters", [])
    id_set = set(chapter_ids)
    updated_chapters: List[str] = []

    def apply_statuses(chapter_list):
        for chapter in chapter_list:
            if chapter.get("id") in id_set:
                chapter["status"] = new_status
                if update_timestamp:
                    chapter["last_modified"] = datetime.now(timezone.utc)
                updated_chapters.append(chapter["id"])
            if chapter.get("subchapters"):
                apply_statuses(chapter["subchapters"])

    apply_statuses(chapters)

    if not updated_chapters:
        raise ValueError("No matching chapters found")

    updated_toc = {
        **current_toc,
        "chapters": chapters,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "status": "edited",
        "version": current_version + 1,
    }

    # Compare-and-swap: the version filter makes this a no-op if another writer
    # bumped the TOC since we read it, so concurrent edits can't clobber.
    await _set_toc_guarded(
        book_oid, user_auth_id, updated_toc, _version_guard(current_toc)
    )

    # Preserve the book-level audit entry the previous update_book() path emitted.
    await create_audit_log(
        action="book_update",
        actor_id=user_auth_id,
        target_id=book_id,
        resource_type="book",
        details={"updated_fields": ["table_of_contents", "updated_at"]},
    )

    return {"updated_chapters": updated_chapters}


async def reorder_chapters_with_transaction(
    book_id: str,
    chapter_orders: List[Dict[str, Any]],
    user_auth_id: str
) -> Dict[str, Any]:
    """
    Reorder chapters with transaction support.
    chapter_orders should be a list of {"id": "chapter_id", "order": 1}

    Runs as a single compare-and-swap, deliberately WITHOUT a transaction.

    These are single-document writes: one read of the book, one guarded
    ``update_one`` filtered on the version that read observed. The CAS is atomic
    on its own, so a transaction adds nothing — and actively breaks the 409
    contract on a replica set. Inside a transaction the guarded update reads at
    the transaction snapshot, so the version filter always matches and the
    conflict never raises ValueError; the genuine conflict aborts at COMMIT as a
    WriteConflict, which reaches the endpoint as a generic OperationFailure and
    becomes a 500. Without the transaction the filter misses, ValueError is
    raised, and the endpoint returns 409 on every topology (#369).

    ``update_chapter_statuses_with_version_guard`` (#159) already took this
    route for the same reason.
    """
    return await _reorder_chapters_internal(book_id, chapter_orders, user_auth_id, None)


async def _reorder_chapters_internal(
    book_id: str,
    chapter_orders: List[Dict[str, Any]],
    user_auth_id: str,
    session: Optional[AsyncIOMotorClientSession]
) -> Dict[str, Any]:
    """Internal function to reorder chapters with or without transaction"""
    # Get the book
    book = await books_collection.find_one(
        {"_id": ObjectId(book_id), "owner_id": user_auth_id},
        session=session
    )
    if not book:
        raise ValueError("Book not found or not authorized")

    toc = book.get("table_of_contents", {})
    version_guard = _version_guard(toc)  # snapshot before mutating `toc`
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
    await _set_toc_guarded(
        ObjectId(book_id), user_auth_id, toc, version_guard, session
    )

    return toc
