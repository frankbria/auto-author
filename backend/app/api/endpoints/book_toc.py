"""
Book TOC endpoints: readiness check, AI generation, read and save of the TOC.

Extracted verbatim from ``books.py`` (issue #1125). Behavior-preserving move:
routes are mounted under the same ``/books`` prefix in ``router.py``.
``_book_is_full`` moved with them; ``chapter_content`` imports it from here.
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import ValidationError
from pymongo.errors import OperationFailure

from app.api.dependencies import (
    get_rate_limiter, get_ai_usage_quota, get_entitlement_checker
)
from app.core.security import get_current_user_from_session
from app.db.database import get_book_by_id, get_book_fields, get_book_metadata_by_id
from app.db.toc_transactions import update_toc_with_transaction, _walk_toc
from app.schemas.ai_input import GenerateTocRequest
from app.schemas.book import MAX_TOC_BODY_BYTES
from app.services.ai_errors import AIServiceError
from app.services.ai_service import ai_service
from app.utils.error_handlers import ai_error_http_exception

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{book_id}/toc-readiness", status_code=status.HTTP_200_OK)
async def check_toc_generation_readiness(
    book_id: str,
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    Check if a book is ready for TOC generation based on summary analysis and question responses.
    Returns the current state and what steps are needed next.
    """
    # Get the book and verify ownership
    book = await get_book_fields(book_id, "owner_id", "summary", "summary_analysis")
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("auth_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to check readiness for this book"
        )

    # Readiness is driven by the summary + its AI analysis. A composite that
    # also required questions and "completed" responses used to be computed
    # here, but both return branches below discard it (they return only
    # summary-analysis fields), so it was dead — removed (#276).
    summary = book.get("summary", "")
    summary_analysis = book.get("summary_analysis", {})
    has_analysis = bool(summary_analysis)

    # If we have analysis data, return it in the format expected by the frontend
    if has_analysis:
        # Return the analysis data from AI service in the format expected by frontend
        return {
            "is_ready_for_toc": summary_analysis.get("is_ready_for_toc", False),
            "confidence_score": summary_analysis.get("confidence_score", 0.0),
            "analysis": summary_analysis.get("analysis", "Analysis not available"),
            "suggestions": summary_analysis.get("suggestions", []),
            "word_count": summary_analysis.get(
                "word_count", len(summary.split()) if summary else 0
            ),
            "character_count": summary_analysis.get(
                "character_count", len(summary) if summary else 0
            ),
            "meets_minimum_requirements": summary_analysis.get(
                "meets_minimum_requirements", False
            ),
        }
    else:
        # No analysis available - return basic readiness check
        word_count = len(summary.split()) if summary else 0
        char_count = len(summary) if summary else 0
        meets_min_requirements = word_count >= 30 and char_count >= 150

        return {
            "is_ready_for_toc": False,
            "confidence_score": 0.0,
            "analysis": "Summary analysis not yet completed. Please run analysis first.",
            "suggestions": ["Run summary analysis to get readiness assessment"],
            "word_count": word_count,
            "character_count": char_count,
            "meets_minimum_requirements": meets_min_requirements,
        }


@router.post("/{book_id}/generate-toc", status_code=status.HTTP_200_OK, dependencies=[Depends(get_ai_usage_quota()), Depends(get_entitlement_checker("generate_toc"))])
async def generate_table_of_contents(
    book_id: str,
    data: GenerateTocRequest = Body(default=GenerateTocRequest()),
    current_user: Dict = Depends(get_current_user_from_session),
    rate_limit_info: Dict = Depends(
        get_rate_limiter(limit=2, window=300)
    ),  # 2 per 5 minutes
):
    """
    Generate a Table of Contents based on the book summary and user responses to clarifying questions.
    This endpoint creates a hierarchical TOC structure that can be edited by the user.
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("auth_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to generate TOC for this book"
        )

    # Check if summary exists
    summary = book.get("summary", "")
    if not summary:
        raise HTTPException(
            status_code=400, detail="Book summary is required for TOC generation"
        )

    # Question responses come from the clarifying-questions wizard, which sends
    # them in the request body ({"question_responses": [{question, answer}, ...]}).
    # Fall back to any responses persisted on the book. Previously this only read
    # the persisted field, but the wizard never persists them, so TOC generation
    # always failed with "Question responses are required".
    responses = [pair.model_dump() for pair in data.question_responses]
    if not responses:
        # Checked like a request body: these may have been saved before the caps (#800).
        persisted = book.get("question_responses", {}).get("responses", [])
        try:
            fallback = GenerateTocRequest(question_responses=persisted)
        except ValidationError:
            raise HTTPException(
                status_code=422,
                detail="The saved answers are over the size limit. Save them again, shorter.",
            )
        responses = [pair.model_dump() for pair in fallback.question_responses]
    if not responses:
        raise HTTPException(
            status_code=400, detail="Question responses are required for TOC generation"
        )

    # Prepare book metadata for context
    book_metadata = {
        "title": book.get("title", ""),
        "genre": book.get("genre", ""),
        "target_audience": book.get("target_audience", ""),
    }

    try:
        # Generate TOC using AI service
        toc_result = await ai_service.generate_toc_from_summary_and_responses(
            summary, responses, book_metadata
        )

        # The AI numbers chapters positionally (ch1, ch1-1). On accept, PUT
        # /toc keeps the id and draft of any stored chapter with the same id,
        # so a positional id would hand an old draft to an unrelated chapter
        # (#754). The proposal carries fresh ids instead.
        for item in _walk_toc(toc_result["toc"].get("chapters") or []):
            item["id"] = str(uuid.uuid4())

        # Propose only; never persist (#753). The old unguarded $set replaced the
        # stored TOC and every chapter draft before the user saw the result, and
        # lost any autosave that landed during the AI call. PUT /toc on accept is
        # the only writer. `base_version` is the version read before the AI call
        # (PUT's default is 1 for a book with no TOC); the client sends it back
        # as expected_version so a TOC that changed meanwhile is a 409.
        stored_toc = book.get("table_of_contents") or {}
        base_version = stored_toc.get("version", 1)
        # What accepting this proposal would replace, so the wizard can say so.
        replaces_drafts = sum(
            1
            for item in _walk_toc(stored_toc.get("chapters") or [])
            if str(item.get("content") or "").strip()
        )

        return {
            "book_id": book_id,
            "toc": toc_result["toc"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "base_version": base_version,
            "replaces_drafts": replaces_drafts,
            "chapters_count": toc_result["chapters_count"],
            "has_subchapters": toc_result["has_subchapters"],
            "success": toc_result["success"],
        }

    except AIServiceError as e:
        raise ai_error_http_exception(e)
    except Exception:
        logger.error("Unexpected error generating TOC", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error generating TOC"
        )


def _without_bodies(chapters: Any) -> Any:
    """Chapters as GET and PUT /toc return them: without ``content``, at any depth (#828).

    The editor reads the table of contents to draw its tabs and reads a
    chapter's body from the chapter's own route. A stored TOC can hold AI JSON
    verbatim, so anything that is not a chapter is passed through as it is.
    """
    if not isinstance(chapters, list):
        return chapters
    return [
        {
            key: _without_bodies(value) if key == "subchapters" else value
            for key, value in chapter.items()
            if key != "content"
        }
        if isinstance(chapter, dict)
        else chapter
        for chapter in chapters
    ]


# What MongoDB answers when a write would take a document past sixteen megabytes.
_DOCUMENT_TOO_LARGE_CODES = {10334, 17419}


def _book_is_full(error: Exception) -> Optional[HTTPException]:
    """413 if ``error`` is the database refusing to let the book's document grow (#828).

    A book is one document. It was a 500, on every save that made the book longer.
    """
    if isinstance(error, OperationFailure) and error.code in _DOCUMENT_TOO_LARGE_CODES:
        return HTTPException(
            status_code=413,
            detail="This book has reached the largest size it can be stored at. Shorten a chapter to save more.",
        )
    return None


@router.get("/{book_id}/toc", status_code=status.HTTP_200_OK)
async def get_book_toc(
    book_id: str,
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    Get the Table of Contents for a book.
    Returns the current TOC structure or empty structure if none exists.
    """

    # Get the book and verify ownership
    book = await get_book_metadata_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("auth_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to access this book's TOC"
        )

    # Get TOC from book record
    toc = book.get("table_of_contents", {})

    if not toc:
        # Return empty TOC structure
        return {
            "book_id": book_id,
            "toc": {
                "chapters": [],
                "total_chapters": 0,
                "estimated_pages": 0,
                "structure_notes": "",
            },
            "status": "not_generated",
            # What a first save expects, as a TOC without a version counts (#871).
            "version": 1,
            "generated_at": None,
            "updated_at": None,
        }

    return {
        "book_id": book_id,
        "toc": {
            "chapters": _without_bodies(toc.get("chapters", [])),
            "total_chapters": toc.get("total_chapters", 0),
            "estimated_pages": toc.get("estimated_pages", 0),
            "structure_notes": toc.get("structure_notes", ""),
        },
        "status": toc.get("status", "unknown"),
        "version": toc.get("version", 1),
        "generated_at": toc.get("generated_at"),
        "updated_at": toc.get("updated_at"),
    }


@router.put("/{book_id}/toc", status_code=status.HTTP_200_OK)
async def update_book_toc(
    book_id: str,
    data: dict = Body(...),
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    Update the Table of Contents for a book.
    Saves user edits to the TOC structure with transaction support.
    """
    # Validate TOC data. Both keys are *required*, not defaulted: the update
    # replaces `table_of_contents` wholesale, so defaulting a missing key to
    # {} / [] wipes the saved chapters and answers 200 (#492). An intentional
    # clear is still expressible as {"toc": {"chapters": []}}.
    if "toc" not in data:
        raise HTTPException(
            status_code=400, detail="Request body must contain a 'toc' object"
        )

    toc_data = data["toc"]
    if not isinstance(toc_data, dict):
        raise HTTPException(
            status_code=400, detail="TOC data must be provided as an object"
        )

    if "chapters" not in toc_data:
        raise HTTPException(
            status_code=400, detail="TOC must contain a 'chapters' list"
        )

    chapters = toc_data["chapters"]
    if not isinstance(chapters, list):
        raise HTTPException(
            status_code=400, detail="Chapters must be provided as a list"
        )

    # ensure_ascii=False: counted as the UTF-8 it is stored as, not as JSON's \uXXXX escapes.
    if len(json.dumps(toc_data, ensure_ascii=False).encode()) > MAX_TOC_BODY_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"The table of contents is too large to save: the limit is {MAX_TOC_BODY_BYTES:,} bytes.",
        )

    # Validate each chapter
    for i, chapter in enumerate(chapters):
        if not isinstance(chapter, dict):
            raise HTTPException(
                status_code=400, detail=f"Chapter {i} must be an object"
            )
        if "title" not in chapter or not chapter["title"]:
            raise HTTPException(
                status_code=400, detail=f"Chapter {i} must have a title"
            )
        subchapters = chapter.get("subchapters", [])
        if not isinstance(subchapters, list) or not all(
            isinstance(sub, dict) for sub in subchapters
        ):
            raise HTTPException(
                status_code=400,
                detail=f"Chapter {i} subchapters must be a list of objects",
            )

    try:
        logger.info(f"Updating TOC for book_id={book_id}, user_auth_id={current_user.get('auth_id')}")

        # Update TOC with transaction
        # A chapter's body has one way in, its own route, where its size is
        # checked (#828). Sent here it is dropped; the stored one is kept by id.
        updated_toc = await update_toc_with_transaction(
            book_id=book_id,
            toc_data={**toc_data, "chapters": _without_bodies(chapters)},
            user_auth_id=current_user.get("auth_id")
        )

        # Describe what was stored, not what was sent (#496). Echoing `toc_data`
        # meant a partial update answered 200 with the partial object while the
        # database held the merged one, so a client trusting the response then
        # disagreed with its own next GET. Shape matches GET /toc exactly.
        return {
            "book_id": book_id,
            "toc": {
                "chapters": _without_bodies(updated_toc.get("chapters", [])),
                "total_chapters": updated_toc.get("total_chapters", 0),
                "estimated_pages": updated_toc.get("estimated_pages", 0),
                "structure_notes": updated_toc.get("structure_notes", ""),
            },
            "updated_at": updated_toc["updated_at"],
            "version": updated_toc["version"],
            "chapters_count": len(chapters),
            "success": True,
        }
    except ValueError as e:
        if "Version conflict" in str(e):
            raise HTTPException(
                status_code=409,
                detail="The TOC has been modified by another user. Please refresh and try again."
            )
        elif "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Book not found")
        elif "not authorized" in str(e).lower():
            raise HTTPException(
                status_code=403, detail="Not authorized to update this book's TOC"
            )
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as error:
        full = _book_is_full(error)
        if full:
            raise full
        logger.error("Failed to update TOC", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update TOC")
