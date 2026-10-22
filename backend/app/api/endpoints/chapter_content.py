"""
Chapter content endpoints: read, save (with the #759 precondition), analytics
and batch read.

Extracted verbatim from ``books.py`` (issue #1122). Behavior-preserving move:
routes are mounted under the same ``/books`` prefix in ``router.py``.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pymongo.errors import OperationFailure

from app.api.endpoints.book_toc import _book_is_full
from app.core.reporting import report_failure
from app.core.security import get_current_user_from_session
from app.db.book import NO_PRECONDITION
from app.db.database import (
    get_book_fields, get_book_metadata_by_id, get_book_owner_id,
    apply_chapter_content_update,
)
from app.schemas.book import ChapterContentUpdate, MAX_CHAPTER_CONTENT_BYTES
from app.services.chapter_access_service import chapter_access_service
from app.services.chapter_status_service import chapter_status_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _last_modified_token(value: Any) -> Optional[str]:
    """The chapter's save token (#759) as clients see it. The content PATCH
    stores an ISO string, but the bulk-status endpoint and the tab migration
    store a BSON Date, so both are rendered as one string. PyMongo decodes a Date
    as naive UTC; the offset is added so both kinds read the same way. Clients
    must echo it verbatim: it is compared, not parsed."""
    if isinstance(value, datetime):
        return value.replace(tzinfo=value.tzinfo or timezone.utc).isoformat()
    return value


async def _chapter_save_rejected(book_id: str, chapter_id: str) -> HTTPException:
    """Why a content save didn't land: 404 if the chapter is gone, else 409
    carrying what the editor needs to offer reload-or-overwrite (#760) without
    another GET. Overwrite = resend with ``current_last_modified``."""
    book = await get_book_fields(book_id, "table_of_contents") or {}
    chapters = (book.get("table_of_contents") or {}).get("chapters", [])
    # One level of subchapters: the depth apply_chapter_content_update writes.
    chapter = next(
        (
            c
            for top in chapters
            for c in [top, *(top.get("subchapters") or [])]
            if c.get("id") == chapter_id
        ),
        None,
    )
    if chapter is None:
        return HTTPException(status_code=404, detail="Chapter not found")
    return HTTPException(
        status_code=409,
        detail={
            "message": "This chapter was saved from somewhere else since you opened it.",
            "current_last_modified": _last_modified_token(chapter.get("last_modified")),
            "current_content": chapter.get("content", ""),
        },
    )


@router.get("/{book_id}/chapters/{chapter_id}/content", response_model=dict)
async def get_chapter_content(
    book_id: str,
    chapter_id: str,
    current_user: Dict = Depends(get_current_user_from_session),
    include_metadata: bool = Query(
        True, description="Include chapter metadata in response"
    ),
):
    """
    Get chapter content with enhanced metadata for tab interface.
    """
    # Get the book and verify ownership
    book = await get_book_fields(book_id, "owner_id", "table_of_contents")
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("auth_id"):
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
            user_id=current_user.get("auth_id"),
            book_id=book_id,
            chapter_id=chapter_id,
            access_type="read_content",
            metadata={
                "chapter_title": chapter.get("title", ""),
                "include_metadata": include_metadata,
                "access_timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception as error:
        logger.error("Failed to log chapter content access", exc_info=True)
        report_failure("access-log", error)
    # Prepare response
    response = {
        "book_id": book_id,
        "chapter_id": chapter_id,
        "title": chapter.get("title", ""),
        "content": chapter.get("content", ""),
        "last_modified": _last_modified_token(chapter.get("last_modified")),
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
            "last_modified": _last_modified_token(chapter.get("last_modified")),
            "is_active_tab": chapter.get("is_active_tab", False),
            "has_subchapters": bool(chapter.get("subchapters")),
            "subchapter_count": len(chapter.get("subchapters", [])),
        }

    return response


@router.patch("/{book_id}/chapters/{chapter_id}/content", response_model=dict)
async def update_chapter_content(
    book_id: str,
    chapter_id: str,
    body: ChapterContentUpdate,
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    Update chapter content with automatic metadata updates.

    With ``expected_last_modified`` in the body the save is conditional (#759):
    409 if the chapter was saved elsewhere since the client read it.
    """
    content = body.content
    auto_update_metadata = body.auto_update_metadata
    if len(content.encode()) > MAX_CHAPTER_CONTENT_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"This chapter is too long to save: the limit is {MAX_CHAPTER_CONTENT_BYTES:,} bytes. Split it into two chapters.",
        )
    # Verify ownership and read the TOC *structure*. The projection drops every
    # chapter's draft HTML, which this handler never reads — it only walks the
    # tree to find the target chapter, its parent, and its current status, then
    # writes through the scoped apply_chapter_content_update below. This is the
    # 3s autosave path, so the whole-document read it used to do was the worst
    # instance of the overfetch in #344.
    book = await get_book_metadata_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("auth_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to modify this book's content"
        )

    # Get current TOC
    current_toc = book.get("table_of_contents", {})
    chapters = current_toc.get("chapters", [])

    # Locate the chapter and compute only the fields that change. We persist via
    # a targeted arrayFilters $set (below) instead of rewriting the whole TOC, so
    # a concurrent autosave to a different chapter can't clobber this one (#177).
    def compute_chapter_update(chapter_list, parent_id=None):
        for chapter in chapter_list:
            if chapter.get("id") == chapter_id:
                # last_modified moves on every content write, metadata or not:
                # it is the token the precondition compares against.
                fields = {
                    "content": content,
                    "last_modified": datetime.now(timezone.utc).isoformat(),
                }
                if auto_update_metadata:
                    word_count = len(content.split()) if content else 0
                    fields["word_count"] = word_count
                    # ~200 words per minute
                    fields["estimated_reading_time"] = max(1, word_count // 200)
                    # Status transition based on content length (simple heuristic)
                    current_status = chapter.get("status", "draft")
                    if word_count > 100 and current_status == "draft":
                        fields["status"] = "in-progress"
                    elif word_count > 500 and current_status == "in-progress":
                        fields["status"] = "completed"
                return fields, parent_id, chapter.get("last_modified")
            # Recursively search subchapters (parent is this chapter's id)
            if chapter.get("subchapters"):
                result = compute_chapter_update(
                    chapter["subchapters"], parent_id=chapter.get("id")
                )
                if result:
                    return result
        return None

    computed = compute_chapter_update(chapters)
    if not computed:
        raise HTTPException(status_code=404, detail="Chapter not found")
    chapter_fields, parent_chapter_id, stored_last_modified = computed
    precondition = NO_PRECONDITION
    if "expected_last_modified" in body.model_fields_set:
        if body.expected_last_modified != _last_modified_token(stored_last_modified):
            raise await _chapter_save_rejected(book_id, chapter_id)
        # Match the raw stored value (string or Date) in the write itself, so a
        # save committed after the read above still makes this one a no-match.
        precondition = stored_last_modified
    # No access-log row for a save (#827): the editor saves three seconds after
    # the last keystroke, and nothing in the application read the rows.

    # Persist via a targeted, concurrency-safe positional update (only this
    # chapter's fields + an atomic version $inc) rather than a whole-TOC rewrite.
    try:
        persisted = await apply_chapter_content_update(
            book_id=book_id,
            chapter_id=chapter_id,
            parent_chapter_id=parent_chapter_id,
            chapter_fields=chapter_fields,
            user_auth_id=current_user.get("auth_id"),
            expected_last_modified=precondition,
        )
    except OperationFailure as error:
        raise _book_is_full(error) or error
    if not persisted:
        # Deleted/moved since the read above (404), or saved elsewhere (409).
        raise await _chapter_save_rejected(book_id, chapter_id)

    return {
        "book_id": book_id,
        "chapter_id": chapter_id,
        "success": True,
        "message": "Chapter content updated successfully",
        "metadata_updated": auto_update_metadata,
        "last_modified": chapter_fields["last_modified"],
    }


@router.get("/{book_id}/chapters/{chapter_id}/analytics", response_model=dict)
async def get_chapter_analytics(
    book_id: str,
    chapter_id: str,
    current_user: Dict = Depends(get_current_user_from_session),
    days: int = Query(
        30, description="Number of days to include in analytics", ge=1, le=365
    ),
):
    """
    Get analytics data for a specific chapter.
    """
    # Get the book and verify ownership
    owner_id = await get_book_owner_id(book_id)
    if owner_id is None:
        raise HTTPException(status_code=404, detail="Book not found")
    if owner_id != current_user.get("auth_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to access this book's analytics"
        )

    try:
        # Get chapter analytics
        # The service aggregates analytics for the whole book; this route is
        # chapter-specific, so keep only entries for the requested chapter.
        book_analytics = await chapter_access_service.get_chapter_analytics(
            book_id=book_id,
            days=days,
        )
        analytics = [
            entry
            for entry in book_analytics
            if entry.get("_id", {}).get("chapter_id") == chapter_id
        ]

        return {
            "book_id": book_id,
            "chapter_id": chapter_id,
            "analytics_period_days": days,
            "analytics": analytics,
            "success": True,
        }

    except Exception:
        logger.error("Failed to retrieve chapter analytics", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve chapter analytics"
        )


@router.post("/{book_id}/chapters/batch-content", response_model=dict)
async def batch_get_chapter_content(
    book_id: str,
    chapter_ids: List[str] = Body(..., embed=True),
    current_user: Dict = Depends(get_current_user_from_session),
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
    book = await get_book_fields(book_id, "owner_id", "table_of_contents")
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("auth_id"):
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
                # Calculate reading time from word count (fall back to content)
                word_count = chapter.get("word_count", 0)
                if not word_count:
                    content = chapter.get("content", "")
                    word_count = len(content.split()) if content else 0
                reading_time = chapter_status_service.calculate_reading_time(
                    word_count
                )

                chapter_info["metadata"] = {
                    "status": chapter.get("status", "draft"),
                    "word_count": chapter.get("word_count", 0),
                    "estimated_reading_time": reading_time,
                    "last_modified": _last_modified_token(chapter.get("last_modified")),
                    "is_active_tab": chapter.get("is_active_tab", False),
                }

            chapter_data[chapter_id] = chapter_info

    # Log batch access
    try:
        await chapter_access_service.log_access(
            user_id=current_user.get("auth_id"),
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
    except Exception as error:
        logger.error("Failed to log batch chapter access", exc_info=True)
        report_failure("access-log", error)

    return {
        "book_id": book_id,
        "chapters": chapter_data,
        "requested_count": len(chapter_ids),
        "found_count": len(found_chapters),
        "success": True,
    }
