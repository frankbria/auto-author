import os
import json
import re
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Request,
    Query,
    UploadFile,
    File,
    Body,
)
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.core.security import get_current_user, RoleChecker
from app.schemas.book import (
    BookCreate,
    BookUpdate,
    BookResponse,
    BookDetailResponse,
    TocItemCreate,
    TocItemUpdate,
    ChapterMetadataResponse,
    TabStateRequest,
    TabStateResponse,
    BulkStatusUpdate,
    ChapterMetadata,
    ChapterStatus,
    # Question schemas
    Question,
    QuestionType,
    QuestionDifficulty,
    QuestionCreate,
    QuestionResponse,
    QuestionResponseCreate,
    QuestionRating,
    GenerateQuestionsRequest,
    GenerateQuestionsResponse,
    QuestionListParams,
    QuestionListResponse,
    QuestionProgressResponse,
)
from app.db.database import (
    create_book, get_book_by_id, get_books_by_user,
    update_book, delete_book
)
from app.db.toc_transactions import (
    update_toc_with_transaction,
    add_chapter_with_transaction,
    update_chapter_with_transaction,
    delete_chapter_with_transaction,
    reorder_chapters_with_transaction,
)
from app.api.dependencies import (
    rate_limit, audit_request, sanitize_input, get_rate_limiter
)
from app.services.ai_service import ai_service
from app.services.chapter_access_service import chapter_access_service
from app.services.chapter_status_service import chapter_status_service
from app.services.question_generation_service import get_question_generation_service
from bson import ObjectId


"""Chapters"""

router = APIRouter()


@router.post(
    "/{book_id}/chapters", response_model=dict, status_code=status.HTTP_201_CREATED
)
async def create_chapter(
    book_id: str,
    chapter_data: TocItemCreate,
    current_user: Dict = Depends(get_current_user),
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
            user_clerk_id=current_user.get("clerk_id")
        )

        # Log chapter creation
        await chapter_access_service.log_access(
            user_id=current_user.get("clerk_id"),
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
    except Exception as e:
        print(f"Error creating chapter: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create chapter")


@router.get("/{book_id}/chapters/{chapter_id}", response_model=dict)
async def get_chapter(
    book_id: str,
    chapter_id: str,
    current_user: Dict = Depends(get_current_user),
):
    """
    Get a specific chapter by ID from the book's TOC.
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
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
        user_id=current_user.get("clerk_id"),
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
    current_user: Dict = Depends(get_current_user),
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
            user_clerk_id=current_user.get("clerk_id")
        )

        # Log chapter update
        await chapter_access_service.log_access(
            user_id=current_user.get("clerk_id"),
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
    except Exception as e:
        print(f"Error updating chapter: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update chapter")


@router.delete("/{book_id}/chapters/{chapter_id}", response_model=dict)
async def delete_chapter(
    book_id: str,
    chapter_id: str,
    current_user: Dict = Depends(get_current_user),
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
            user_clerk_id=current_user.get("clerk_id")
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
    except Exception as e:
        print(f"Error deleting chapter: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete chapter")



@router.get("/{book_id}/chapters", response_model=dict)
async def list_chapters(
    book_id: str,
    current_user: Dict = Depends(get_current_user),
    flat: bool = Query(
        False, description="Return flat list instead of hierarchical structure"
    ),
):
    """
    List all chapters in the book's TOC.
    Can return either hierarchical structure (default) or flat list.
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
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


# Enhanced Chapter Metadata and Tab Management Endpoints


@router.get("/{book_id}/chapters/metadata", response_model=ChapterMetadataResponse)
async def get_chapters_metadata(
    book_id: str,
    current_user: Dict = Depends(get_current_user),
    include_content_stats: bool = Query(
        False, description="Include word count and reading time"
    ),
):
    """
    Get comprehensive metadata for all chapters in a book.
    Optimized for tab interface rendering.
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
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
        current_user.get("clerk_id"), book_id, limit=1
    )
    last_active_chapter = recent_chapters[0]["_id"] if recent_chapters else None

    return ChapterMetadataResponse(
        book_id=book_id,
        chapters=chapter_metadata_list,
        total_chapters=len(chapter_metadata_list),
        completion_stats=completion_stats,
        last_active_chapter=last_active_chapter,
    )


@router.patch("/{book_id}/chapters/bulk-status", response_model=dict)
async def update_chapter_status_bulk(
    book_id: str,
    update_data: BulkStatusUpdate,
    current_user: Dict = Depends(get_current_user),
):
    """
    Update status for multiple chapters simultaneously.
    Useful for tab operations like "Mark selected as completed".
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to modify this book's chapters"
        )

    # Get current TOC
    current_toc = book.get("table_of_contents", {})
    chapters = current_toc.get("chapters", [])

    # Collect current statuses for validation
    chapter_statuses = {}
    updated_chapters = []

    def collect_and_update_statuses(chapter_list):
        for chapter in chapter_list:
            if chapter.get("id") in update_data.chapter_ids:
                current_status = chapter.get("status", ChapterStatus.DRAFT.value)
                chapter_statuses[chapter["id"]] = current_status

                # Validate transition
                if chapter_status_service.validate_status_transition(
                    current_status, update_data.status.value
                ):
                    chapter["status"] = update_data.status.value
                    if update_data.update_timestamp:
                        chapter["last_modified"] = datetime.now(timezone.utc)
                    updated_chapters.append(chapter["id"])
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid status transition for chapter {chapter['id']}: {current_status} -> {update_data.status.value}",
                    )

            # Process subchapters
            if chapter.get("subchapters"):
                collect_and_update_statuses(chapter["subchapters"])

    collect_and_update_statuses(chapters)

    if not updated_chapters:
        raise HTTPException(status_code=404, detail="No matching chapters found")

    # Update TOC in database
    updated_toc = {
        **current_toc,
        "chapters": chapters,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "status": "edited",
        "version": current_toc.get("version", 1) + 1,
    }

    update_book_data = {
        "table_of_contents": updated_toc,
        "updated_at": datetime.now(timezone.utc),
    }
    await update_book(book_id, update_book_data, current_user.get("clerk_id"))

    # Log the bulk status change
    for chapter_id in updated_chapters:
        await chapter_access_service.log_access(
            user_id=current_user.get("clerk_id"),
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
    current_user: Dict = Depends(get_current_user),
):
    """
    Save current tab state for persistence across sessions.
    """
    # Verify book ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
        print(
            f"User {current_user.get('clerk_id')} is not authorized to access book {book_id}"
        )
        raise HTTPException(
            status_code=403, detail="Not authorized to access this book"
        )

    # Save tab state via access logging service
    log_id = await chapter_access_service.save_tab_state(
        user_id=current_user.get("clerk_id"),
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


@router.get("/{book_id}/chapters/tab-state", response_model=dict)
async def get_tab_state(book_id: str, current_user: Dict = Depends(get_current_user)):
    """
    Retrieve saved tab state for restoration.
    """
    # Verify book ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
        print(
            f"User {current_user.get('clerk_id')} is not authorized to access book {book_id}"
        )
        raise HTTPException(
            status_code=403, detail="Not authorized to access this book"
        )

    # Get latest tab state
    tab_state = await chapter_access_service.get_user_tab_state(
        current_user.get("clerk_id"), book_id
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


# Enhanced Chapter Content Integration Endpoints


@router.get("/{book_id}/chapters/{chapter_id}/content", response_model=dict)
async def get_chapter_content(
    book_id: str,
    chapter_id: str,
    current_user: Dict = Depends(get_current_user),
    include_metadata: bool = Query(
        True, description="Include chapter metadata in response"
    ),
):
    """
    Get chapter content with enhanced metadata for tab interface.
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to access this book's content"
        )

    # Find the chapter in TOC
    current_toc = book.get("table_of_contents", {})
    chapters = current_toc.get("chapters", [])

    def find_chapter(chapter_list):
        for chapter in chapter_list:
            if chapter.get("id") == chapter_id:
                return chapter
            if chapter.get("subchapters"):
                found = find_chapter(chapter["subchapters"])
                if found:
                    return found
        return None

    chapter = find_chapter(chapters)
    if not chapter:
        raise HTTPException(
            status_code=404, detail="Chapter not found"
        )  # Log chapter access
    try:
        await chapter_access_service.log_access(
            user_id=current_user.get("clerk_id"),
            book_id=book_id,
            chapter_id=chapter_id,
            access_type="read_content",
            metadata={
                "chapter_title": chapter.get("title", ""),
                "include_metadata": include_metadata,
                "access_timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception as e:
        print(f"Failed to log chapter content access: {e}")  # Prepare response
    response = {
        "book_id": book_id,
        "chapter_id": chapter_id,
        "title": chapter.get("title", ""),
        "content": chapter.get("content", ""),
        "success": True,
    }

    if include_metadata:
        # Calculate reading time using word count
        word_count = chapter.get("word_count", 0)
        # If word_count is not available, calculate it from content
        if word_count == 0:
            content = chapter.get("content", "")
            word_count = len(content.split()) if content else 0

        reading_time = chapter_status_service.calculate_reading_time(word_count)

        response["metadata"] = {
            "status": chapter.get("status", "draft"),
            "word_count": chapter.get("word_count", 0),
            "estimated_reading_time": reading_time,
            "last_modified": chapter.get("last_modified"),
            "is_active_tab": chapter.get("is_active_tab", False),
            "has_subchapters": bool(chapter.get("subchapters")),
            "subchapter_count": len(chapter.get("subchapters", [])),
        }

    return response


@router.patch("/{book_id}/chapters/{chapter_id}/content", response_model=dict)
async def update_chapter_content(
    book_id: str,
    chapter_id: str,
    content: str = Body(..., embed=True),
    auto_update_metadata: bool = Body(True, embed=True),
    current_user: Dict = Depends(get_current_user),
):
    """
    Update chapter content with automatic metadata updates.
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to modify this book's content"
        )

    # Get current TOC
    current_toc = book.get("table_of_contents", {})
    chapters = current_toc.get("chapters", [])

    def update_chapter_in_list(chapter_list):
        for chapter in chapter_list:
            if chapter.get("id") == chapter_id:
                # Update content
                chapter["content"] = content

                if auto_update_metadata:
                    # Update metadata
                    word_count = len(content.split()) if content else 0
                    chapter["word_count"] = word_count
                    chapter["last_modified"] = datetime.now(timezone.utc).isoformat()
                    # Calculate reading time synchronously (simple calculation)
                    chapter["estimated_reading_time"] = max(
                        1, word_count // 200
                    )  # ~200 words per minute

                    # Set status based on content length (simple heuristic)
                    current_status = chapter.get("status", "draft")
                    if word_count > 100 and current_status == "draft":
                        chapter["status"] = "in-progress"
                    elif word_count > 500 and current_status == "in-progress":
                        chapter["status"] = "completed"

                return chapter
            # Recursively search subchapters
            if chapter.get("subchapters"):
                result = update_chapter_in_list(chapter["subchapters"])
                if result:
                    return result
        return None

    updated_chapter = update_chapter_in_list(chapters)
    if not updated_chapter:
        raise HTTPException(
            status_code=404, detail="Chapter not found"
        )  # Log chapter access
    try:
        await chapter_access_service.log_access(
            user_id=current_user.get("clerk_id"),
            book_id=book_id,
            chapter_id=chapter_id,
            access_type="update_content",
            metadata={
                "content_length": len(content) if content else 0,
                "auto_updated_metadata": auto_update_metadata,
                "update_timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception as e:
        print(f"Failed to log chapter content update: {e}")

    # Update TOC data
    updated_toc = {
        **current_toc,
        "chapters": chapters,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "status": "edited",
        "version": current_toc.get("version", 1) + 1,
    }

    # Save to database
    update_data = {
        "table_of_contents": updated_toc,
        "updated_at": datetime.now(timezone.utc),
    }
    await update_book(book_id, update_data, current_user.get("clerk_id"))

    return {
        "book_id": book_id,
        "chapter_id": chapter_id,
        "success": True,
        "message": "Chapter content updated successfully",
        "metadata_updated": auto_update_metadata,
    }


@router.get("/{book_id}/chapters/{chapter_id}/analytics", response_model=dict)
async def get_chapter_analytics(
    book_id: str,
    chapter_id: str,
    current_user: Dict = Depends(get_current_user),
    days: int = Query(
        30, description="Number of days to include in analytics", ge=1, le=365
    ),
):
    """
    Get analytics data for a specific chapter.
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to access this book's analytics"
        )

    try:
        # Get chapter analytics
        analytics = await chapter_access_service.get_chapter_analytics(
            user_id=current_user.get("clerk_id"),
            book_id=book_id,
            chapter_id=chapter_id,
            days=days,
        )

        return {
            "book_id": book_id,
            "chapter_id": chapter_id,
            "analytics_period_days": days,
            "analytics": analytics,
            "success": True,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve chapter analytics: {str(e)}"
        )


@router.post("/{book_id}/chapters/batch-content", response_model=dict)
async def batch_get_chapter_content(
    book_id: str,
    chapter_ids: List[str] = Body(..., embed=True),
    current_user: Dict = Depends(get_current_user),
    include_metadata: bool = Body(True, embed=True),
):
    """
    Get content for multiple chapters in a single request (optimized for tab loading).
    """
    # Limit the number of chapters that can be requested at once
    if len(chapter_ids) > 20:
        raise HTTPException(
            status_code=400, detail="Cannot request more than 20 chapters at once"
        )

    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to access this book's content"
        )

    # Get current TOC
    current_toc = book.get("table_of_contents", {})
    chapters = current_toc.get("chapters", [])

    def find_chapter(chapter_list, target_id):
        for chapter in chapter_list:
            if chapter.get("id") == target_id:
                return chapter
            if chapter.get("subchapters"):
                found = find_chapter(chapter["subchapters"], target_id)
                if found:
                    return found
        return None

    # Collect chapter data
    chapter_data = {}
    found_chapters = []

    for chapter_id in chapter_ids:
        chapter = find_chapter(chapters, chapter_id)
        if chapter:
            found_chapters.append(chapter)

            chapter_info = {
                "id": chapter_id,
                "title": chapter.get("title", ""),
                "content": chapter.get("content", ""),
            }

            if include_metadata:
                # Calculate reading time
                reading_time = await chapter_status_service.calculate_reading_time(
                    chapter.get("content", "")
                )

                chapter_info["metadata"] = {
                    "status": chapter.get("status", "draft"),
                    "word_count": chapter.get("word_count", 0),
                    "estimated_reading_time": reading_time,
                    "last_modified": chapter.get("last_modified"),
                    "is_active_tab": chapter.get("is_active_tab", False),
                }

            chapter_data[chapter_id] = chapter_info

    # Log batch access
    try:
        await chapter_access_service.log_access(
            user_id=current_user.get("clerk_id"),
            book_id=book_id,
            chapter_id="batch_request",
            access_type="batch_read_content",
            metadata={
                "requested_chapters": chapter_ids,
                "found_chapters": len(found_chapters),
                "include_metadata": include_metadata,
                "access_timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception as e:
        print(f"Failed to log batch chapter access: {e}")

    return {
        "book_id": book_id,
        "chapters": chapter_data,
        "requested_count": len(chapter_ids),
        "found_count": len(found_chapters),
        "success": True,
    }


# Interview-Style Questions Endpoints
