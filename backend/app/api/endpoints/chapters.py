"""
Chapter management endpoints — CRUD, listing, metadata, bulk status, tab state.

Extracted verbatim from ``books.py`` (issue #94) as the first slice of the
books.py decomposition. Behavior-preserving move: routes are mounted under the
same ``/books`` prefix in ``router.py`` so URLs, schemas, and status codes are
unchanged. Handler order (metadata / tab-state before ``{chapter_id}``) is
preserved so path matching is identical to the original single-file router.
"""
import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import get_current_user_from_session
from app.schemas.book import (
    TocItemCreate,
    TocItemUpdate,
    ChapterMetadataResponse,
    TabStateRequest,
    BulkStatusUpdate,
    ChapterMetadata,
    ChapterStatus,
)
from app.db.database import get_book_by_id
from app.db.toc_transactions import (
    add_chapter_with_transaction,
    update_chapter_with_transaction,
    delete_chapter_with_transaction,
    update_chapter_statuses_with_version_guard,
)
from app.services.chapter_access_service import chapter_access_service
from app.services.chapter_status_service import chapter_status_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/{book_id}/chapters", response_model=dict, status_code=status.HTTP_201_CREATED
)
async def create_chapter(
    book_id: str,
    chapter_data: TocItemCreate,
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    Create a new chapter in the book's TOC.
    Can be used to add a new chapter at any level (chapter or subchapter).
    Uses transaction to ensure atomic operation.
    """
    try:
        # Prepare chapter data
        chapter_dict = {
            "title": chapter_data.title,
            "description": chapter_data.description or "",
            "level": chapter_data.level,
            "order": chapter_data.order,
            "status": "draft",
            "word_count": 0,
            "estimated_reading_time": 0,
            "is_active_tab": False,
        }

        # Add chapter with transaction
        new_chapter = await add_chapter_with_transaction(
            book_id=book_id,
            chapter_data=chapter_dict,
            parent_chapter_id=chapter_data.parent_id if chapter_data.level > 1 else None,
            user_auth_id=current_user.get("auth_id")
        )

        # Log chapter creation
        await chapter_access_service.log_access(
            user_id=current_user.get("auth_id"),
            book_id=book_id,
            chapter_id=new_chapter["id"],
            access_type="create",
            metadata={"chapter_title": chapter_data.title, "level": chapter_data.level},
        )

        return {
            "book_id": book_id,
            "chapter": new_chapter,
            "chapter_id": new_chapter["id"],
            "success": True,
            "message": "Chapter created successfully",
        }
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Book not found")
        elif "not authorized" in str(e).lower():
            raise HTTPException(
                status_code=403, detail="Not authorized to modify this book's chapters"
            )
        elif "Parent chapter not found" in str(e):
            raise HTTPException(status_code=400, detail="Parent chapter not found")
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.error("Failed to create chapter", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create chapter")


# NOTE: literal sub-paths (/chapters/metadata, /chapters/tab-state) must be
# registered BEFORE the parameterized /chapters/{chapter_id} route, otherwise
# FastAPI matches them as chapter_id="metadata"/"tab-state" and they 404.
@router.get("/{book_id}/chapters/metadata", response_model=ChapterMetadataResponse)
async def get_chapters_metadata(
    book_id: str,
    current_user: Dict = Depends(get_current_user_from_session),
    include_content_stats: bool = Query(
        False, description="Include word count and reading time"
    ),
):
    """
    Get comprehensive metadata for all chapters in a book.
    Optimized for tab interface rendering.
    """
    try:
        # Get the book and verify ownership
        book = await get_book_by_id(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        if book.get("owner_id") != current_user.get("auth_id"):
            raise HTTPException(
                status_code=403, detail="Not authorized to access this book's chapters"
            )

        # Get current TOC
        current_toc = book.get("table_of_contents", {})
        chapters = current_toc.get("chapters", [])

        # Convert chapters to metadata format
        chapter_metadata_list = []

        def process_chapters(chapter_list, level=1):
            for chapter in chapter_list:
                # Calculate reading time if word count exists
                word_count = chapter.get("word_count", 0)
                estimated_reading_time = chapter_status_service.calculate_reading_time(
                    word_count
                )

                metadata = ChapterMetadata(
                    id=chapter.get("id"),
                    title=chapter.get("title"),
                    status=chapter.get("status", ChapterStatus.DRAFT.value),
                    word_count=word_count,
                    last_modified=chapter.get("last_modified"),
                    estimated_reading_time=estimated_reading_time,
                    order=chapter.get("order", 0),
                    level=chapter.get("level", level),
                    has_content=word_count > 0,
                    description=chapter.get("description"),
                    parent_id=chapter.get("parent_id"),
                )
                chapter_metadata_list.append(metadata)

                # Process subchapters
                if chapter.get("subchapters"):
                    process_chapters(chapter["subchapters"], level + 1)

        process_chapters(chapters)

        # Calculate completion stats
        completion_stats = chapter_status_service.get_completion_stats(
            [chapter.dict() for chapter in chapter_metadata_list]
        )

        # Get last active chapter from recent access logs
        recent_chapters = await chapter_access_service.get_user_recent_chapters(
            current_user.get("auth_id"), book_id, limit=1
        )
        last_active_chapter = recent_chapters[0]["_id"] if recent_chapters else None

        return ChapterMetadataResponse(
            book_id=book_id,
            chapters=chapter_metadata_list,
            total_chapters=len(chapter_metadata_list),
            completion_stats=completion_stats,
            last_active_chapter=last_active_chapter,
        )
    except HTTPException:
        raise
    except Exception:
        logger.error("Failed to retrieve chapter metadata", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve chapter metadata"
        )


@router.get("/{book_id}/chapters/tab-state", response_model=dict)
async def get_tab_state(book_id: str, current_user: Dict = Depends(get_current_user_from_session)):
    """
    Retrieve saved tab state for restoration.
    """
    try:
        # Verify book ownership
        book = await get_book_by_id(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        if book.get("owner_id") != current_user.get("auth_id"):
            raise HTTPException(
                status_code=403, detail="Not authorized to access this book"
            )

        # Get latest tab state
        tab_state = await chapter_access_service.get_user_tab_state(
            current_user.get("auth_id"), book_id
        )

        if not tab_state:
            return {
                "book_id": book_id,
                "tab_state": None,
                "message": "No saved tab state found",
            }

        metadata = tab_state.get("metadata", {})
        return {
            "book_id": book_id,
            "tab_state": {
                "active_chapter_id": metadata.get("active_chapter_id"),
                "open_tab_ids": metadata.get("open_tab_ids", []),
                "tab_order": metadata.get("tab_order", []),
                "last_updated": tab_state.get("timestamp"),
            },
            "success": True,
        }
    except HTTPException:
        raise
    except Exception:
        logger.error("Failed to retrieve tab state", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve tab state")


@router.get("/{book_id}/chapters/{chapter_id}", response_model=dict)
async def get_chapter(
    book_id: str,
    chapter_id: str,
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    Get a specific chapter by ID from the book's TOC.
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("auth_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to access this book's chapters"
        )  # Get TOC and find the chapter
    current_toc = book.get("table_of_contents", {})
    chapters = current_toc.get("chapters", [])

    def find_chapter(chapter_list):
        for chapter in chapter_list:
            if chapter.get("id") == chapter_id:
                return chapter
            # Recursively search subchapters
            if chapter.get("subchapters"):
                found = find_chapter(chapter["subchapters"])
                if found:
                    return found
        return None

    chapter = find_chapter(chapters)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    # Log chapter access
    await chapter_access_service.log_access(
        user_id=current_user.get("auth_id"),
        book_id=book_id,
        chapter_id=chapter_id,
        access_type="view",
        metadata={"chapter_title": chapter.get("title")},
    )

    return {"book_id": book_id, "chapter": chapter, "success": True}


@router.put("/{book_id}/chapters/{chapter_id}", response_model=dict)
async def update_chapter(
    book_id: str,
    chapter_id: str,
    chapter_data: TocItemUpdate,
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    Update a specific chapter in the book's TOC.
    Uses transaction to ensure atomic operation.
    """
    try:
        # Build updates dict
        updates = {}
        if chapter_data.title is not None:
            updates["title"] = chapter_data.title
        if chapter_data.description is not None:
            updates["description"] = chapter_data.description
        if chapter_data.level is not None:
            updates["level"] = chapter_data.level
        if chapter_data.order is not None:
            updates["order"] = chapter_data.order
        if chapter_data.metadata is not None:
            updates["metadata"] = chapter_data.metadata

        # Update chapter with transaction
        updated_chapter = await update_chapter_with_transaction(
            book_id=book_id,
            chapter_id=chapter_id,
            chapter_updates=updates,
            user_auth_id=current_user.get("auth_id")
        )

        # Log chapter update
        await chapter_access_service.log_access(
            user_id=current_user.get("auth_id"),
            book_id=book_id,
            chapter_id=chapter_id,
            access_type="edit",
            metadata={
                "updated_fields": {
                    "title": chapter_data.title is not None,
                    "description": chapter_data.description is not None,
                    "level": chapter_data.level is not None,
                    "order": chapter_data.order is not None,
                    "metadata": chapter_data.metadata is not None,
                }
            },
        )

        return {
            "book_id": book_id,
            "chapter_id": chapter_id,
            "success": True,
            "message": "Chapter updated successfully",
        }
    except ValueError as e:
        if "not found" in str(e).lower():
            if "Chapter" in str(e):
                raise HTTPException(status_code=404, detail="Chapter not found")
            else:
                raise HTTPException(status_code=404, detail="Book not found")
        elif "not authorized" in str(e).lower():
            raise HTTPException(
                status_code=403, detail="Not authorized to modify this book's chapters"
            )
        elif "Concurrent modification" in str(e):
            raise HTTPException(
                status_code=409,
                detail="The chapter has been modified by another user. Please refresh and try again."
            )
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.error("Failed to update chapter", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update chapter")


@router.delete("/{book_id}/chapters/{chapter_id}", response_model=dict)
async def delete_chapter(
    book_id: str,
    chapter_id: str,
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    Delete a specific chapter from the book's TOC.
    Note: Deleting a chapter will also delete all its subchapters and related questions.
    Uses transaction to ensure atomic operation.
    """
    try:
        # Delete chapter with transaction
        success = await delete_chapter_with_transaction(
            book_id=book_id,
            chapter_id=chapter_id,
            user_auth_id=current_user.get("auth_id")
        )

        # Log chapter access for deletion was moved to transaction

        return {
            "book_id": book_id,
            "chapter_id": chapter_id,
            "success": True,
            "message": "Chapter deleted successfully",
        }
    except ValueError as e:
        if "not found" in str(e).lower():
            if "Chapter" in str(e):
                raise HTTPException(status_code=404, detail="Chapter not found")
            else:
                raise HTTPException(status_code=404, detail="Book not found")
        elif "not authorized" in str(e).lower():
            raise HTTPException(
                status_code=403, detail="Not authorized to modify this book's chapters"
            )
        elif "Concurrent modification" in str(e):
            raise HTTPException(
                status_code=409,
                detail="The TOC has been modified by another user. Please refresh and try again."
            )
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.error("Failed to delete chapter", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete chapter")



@router.get("/{book_id}/chapters", response_model=dict)
async def list_chapters(
    book_id: str,
    current_user: Dict = Depends(get_current_user_from_session),
    flat: bool = Query(
        False, description="Return flat list instead of hierarchical structure"
    ),
):
    """
    List all chapters in the book's TOC.
    Can return either hierarchical structure (default) or flat list.
    """
    try:
        # Get the book and verify ownership
        book = await get_book_by_id(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        if book.get("owner_id") != current_user.get("auth_id"):
            raise HTTPException(
                status_code=403, detail="Not authorized to access this book's chapters"
            )

        # Get TOC
        current_toc = book.get("table_of_contents", {})
        chapters = current_toc.get("chapters", [])

        if flat:
            # Return flat list of all chapters and subchapters
            def flatten_chapters(chapter_list, result=None):
                if result is None:
                    result = []
                for chapter in chapter_list:
                    result.append(
                        {
                            "id": chapter.get("id"),
                            "title": chapter.get("title"),
                            "description": chapter.get("description", ""),
                            "level": chapter.get("level", 1),
                            "order": chapter.get("order", 0),
                        }
                    )
                    if chapter.get("subchapters"):
                        flatten_chapters(chapter["subchapters"], result)
                return result

            flat_chapters = flatten_chapters(chapters)
            return {
                "book_id": book_id,
                "chapters": flat_chapters,
                "total_chapters": len(flat_chapters),
                "structure": "flat",
                "success": True,
            }
        else:
            # Return hierarchical structure
            return {
                "book_id": book_id,
                "chapters": chapters,
                "total_chapters": current_toc.get("total_chapters", len(chapters)),
                "structure": "hierarchical",
                "success": True,
            }
    except HTTPException:
        raise
    except Exception:
        logger.error("Failed to list chapters", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list chapters")


# Enhanced Chapter Metadata and Tab Management Endpoints


@router.patch("/{book_id}/chapters/bulk-status", response_model=dict)
async def update_chapter_status_bulk(
    book_id: str,
    update_data: BulkStatusUpdate,
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    Update status for multiple chapters simultaneously.
    Useful for tab operations like "Mark selected as completed".
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("auth_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to modify this book's chapters"
        )

    # Get current TOC. The version read here is used as the optimistic-locking
    # baseline: the persist below only succeeds if the TOC hasn't changed since.
    current_toc = book.get("table_of_contents", {})
    chapters = current_toc.get("chapters", [])
    current_version = current_toc.get("version", 1)

    # Collect current statuses and validate transitions up front (so an invalid
    # transition still surfaces as a 400 before any write).
    chapter_statuses = {}
    updated_chapters = []

    def collect_and_validate_statuses(chapter_list):
        for chapter in chapter_list:
            if chapter.get("id") in update_data.chapter_ids:
                current_status = chapter.get("status", ChapterStatus.DRAFT.value)

                if chapter_status_service.validate_status_transition(
                    current_status, update_data.status.value
                ):
                    chapter_statuses[chapter["id"]] = current_status
                    updated_chapters.append(chapter["id"])
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid status transition for chapter {chapter['id']}: {current_status} -> {update_data.status.value}",
                    )

            # Process subchapters
            if chapter.get("subchapters"):
                collect_and_validate_statuses(chapter["subchapters"])

    collect_and_validate_statuses(chapters)

    if not updated_chapters:
        raise HTTPException(status_code=404, detail="No matching chapters found")

    # Persist through the optimistic-concurrency helper so a concurrent TOC edit
    # produces a clean 409 instead of silently clobbering the other write.
    try:
        await update_chapter_statuses_with_version_guard(
            book_id=book_id,
            chapter_ids=updated_chapters,
            new_status=update_data.status.value,
            user_auth_id=current_user.get("auth_id"),
            expected_version=current_version,
            update_timestamp=update_data.update_timestamp,
        )
    except HTTPException:
        raise
    except ValueError as e:
        msg = str(e)
        low = msg.lower()
        if "version conflict" in low:
            raise HTTPException(
                status_code=409,
                detail="The TOC has been modified by another user. Please refresh and try again.",
            )
        elif "not authorized" in low:
            raise HTTPException(
                status_code=403, detail="Not authorized to modify this book's chapters"
            )
        elif "no matching chapters" in low:
            raise HTTPException(status_code=404, detail="No matching chapters found")
        elif "not found" in low:
            raise HTTPException(status_code=404, detail="Book not found")
        else:
            raise HTTPException(status_code=400, detail=msg)
    except Exception:
        logger.error("Failed to bulk-update chapter statuses", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to update chapter statuses"
        )

    # Log the bulk status change
    for chapter_id in updated_chapters:
        await chapter_access_service.log_access(
            user_id=current_user.get("auth_id"),
            book_id=book_id,
            chapter_id=chapter_id,
            access_type="status_update",
            metadata={
                "old_status": chapter_statuses[chapter_id],
                "new_status": update_data.status.value,
                "bulk_update": True,
            },
        )

    return {
        "book_id": book_id,
        "updated_chapters": updated_chapters,
        "new_status": update_data.status.value,
        "success": True,
        "message": f"Successfully updated status for {len(updated_chapters)} chapters",
    }


@router.post("/{book_id}/chapters/tab-state", response_model=dict)
async def save_tab_state(
    book_id: str,
    tab_state: TabStateRequest,
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    Save current tab state for persistence across sessions.
    """
    try:
        # Verify book ownership
        book = await get_book_by_id(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        if book.get("owner_id") != current_user.get("auth_id"):
            raise HTTPException(
                status_code=403, detail="Not authorized to access this book"
            )

        # Save tab state via access logging service
        log_id = await chapter_access_service.save_tab_state(
            user_id=current_user.get("auth_id"),
            book_id=book_id,
            active_chapter_id=tab_state.active_chapter_id,
            open_tab_ids=tab_state.open_tab_ids,
            tab_order=tab_state.tab_order,
        )

        return {
            "book_id": book_id,
            "tab_state_id": log_id,
            "success": True,
            "message": "Tab state saved successfully",
        }
    except HTTPException:
        raise
    except Exception:
        logger.error("Failed to save tab state", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save tab state")
