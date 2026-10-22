"""
Book summary endpoints: read, save, patch and AI analysis of the summary.

Extracted verbatim from ``books.py`` (issue #1124). Behavior-preserving move:
routes are mounted under the same ``/books`` prefix in ``router.py``.
"""
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Dict

from fastapi import APIRouter, Body, Depends, HTTPException, status

from app.api.dependencies import (
    get_rate_limiter, get_ai_usage_quota, get_entitlement_checker
)
from app.core.security import get_current_user_from_session
from app.db.database import (
    get_book_fields, get_book_metadata_by_id, update_book,
    update_book_summary_atomic,
)
from app.services.ai_errors import AIServiceError
from app.services.ai_service import ai_service
from app.utils.error_handlers import ai_error_http_exception

logger = logging.getLogger(__name__)

router = APIRouter()

# Helper to load offensive words from JSON
OFFENSIVE_WORDS_PATH = os.path.join(
    os.path.dirname(__file__), "../../utils/offensive_words.json"
)
with open(OFFENSIVE_WORDS_PATH, encoding="utf-8") as f:
    OFFENSIVE_WORDS = json.load(f)


@router.get("/{book_id}/summary", status_code=status.HTTP_200_OK)
async def get_book_summary(
    book_id: str,
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    Retrieve the summary and its revision history for a book.
    """
    book = await get_book_fields(book_id, "owner_id", "summary", "summary_history")

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("auth_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to access this book"
        )
    summary = book.get("summary", "")
    summary_history = book.get("summary_history", [])
    return {"summary": summary, "summary_history": summary_history}


@router.put("/{book_id}/summary", status_code=status.HTTP_200_OK)
async def update_book_summary(
    book_id: str,
    data: dict = Body(...),
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    Save or update the summary for a book, and store revision history.
    Validates min/max length and filters offensive content.
    """
    summary = data.get("summary", "")
    if not summary or not isinstance(summary, str):
        raise HTTPException(
            status_code=400, detail="Summary is required and must be a string."
        )
    # Validation: min/max length
    min_len, max_len = 30, 2000
    if len(summary) < min_len:
        raise HTTPException(
            status_code=400, detail=f"Summary must be at least {min_len} characters."
        )
    if len(summary) > max_len:
        raise HTTPException(
            status_code=400, detail=f"Summary must be at most {max_len} characters."
        )
    # Offensive content filter (simple word blacklist)
    pattern = re.compile(
        r"\b(" + "|".join(map(re.escape, OFFENSIVE_WORDS)) + r")\b", re.IGNORECASE
    )
    if pattern.search(summary):
        raise HTTPException(
            status_code=400, detail="Summary contains inappropriate language."
        )
    book = await get_book_fields(book_id, "owner_id")
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("auth_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to update this book"
        )
    # Persist atomically (archives the document's current summary at write time,
    # bounded to the last 20) so concurrent saves can't clobber history (#177).
    updated_book = await update_book_summary_atomic(
        book_id=book_id,
        summary=summary,
        user_auth_id=current_user.get("auth_id"),
    )
    if not updated_book:
        # The book was deleted between the ownership check and this write.
        raise HTTPException(status_code=404, detail="Book not found")
    history = updated_book.get("summary_history", [])
    return {"summary": summary, "summary_history": history}


@router.patch("/{book_id}/summary", status_code=status.HTTP_200_OK)
async def patch_book_summary(
    book_id: str,
    data: dict = Body(...),
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    Partially update the summary for a book. Only updates the summary field if provided.
    Stores revision history and validates input.
    """
    book = await get_book_fields(book_id, "owner_id", "summary", "summary_history")
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("auth_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to update this book"
        )
    summary = data.get("summary")
    if summary is not None:
        if not isinstance(summary, str):
            raise HTTPException(status_code=400, detail="Summary must be a string.")
        min_len, max_len = 30, 2000
        if len(summary) < min_len:
            raise HTTPException(
                status_code=400,
                detail=f"Summary must be at least {min_len} characters.",
            )
        if len(summary) > max_len:
            raise HTTPException(
                status_code=400, detail=f"Summary must be at most {max_len} characters."
            )
        # Persist atomically (same concurrency-safe path as PUT /summary) so
        # concurrent summary edits can't clobber each other's history (#177).
        updated_book = await update_book_summary_atomic(
            book_id=book_id,
            summary=summary,
            user_auth_id=current_user.get("auth_id"),
        )
        if not updated_book:
            # The book was deleted between the ownership check and this write.
            raise HTTPException(status_code=404, detail="Book not found")
        history = updated_book.get("summary_history", [])
        return {"summary": summary, "summary_history": history}
    # If no summary provided, return current summary
    return {
        "summary": book.get("summary"),
        "summary_history": book.get("summary_history", []),
    }


@router.post("/{book_id}/analyze-summary", status_code=status.HTTP_200_OK, dependencies=[Depends(get_ai_usage_quota()), Depends(get_entitlement_checker("analyze_summary"))])
async def analyze_book_summary(
    book_id: str,
    current_user: Dict = Depends(get_current_user_from_session),
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=5, window=60)),
):
    """
    Analyze the book summary using AI to determine readiness for TOC generation.
    This endpoint uses OpenAI to analyze the summary's structure and completeness.
    """
    # Get the book and verify ownership
    book = await get_book_metadata_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("auth_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to analyze this book"
        )

    # Check if summary exists
    summary = book.get("summary", "")
    if not summary:
        raise HTTPException(
            status_code=400, detail="Book summary is required for analysis"
        )

    # Prepare book metadata for context
    book_metadata = {
        "title": book.get("title", ""),
        "genre": book.get("genre", ""),
        "target_audience": book.get("target_audience", ""),
    }

    try:
        # Analyze summary using AI service
        analysis = await ai_service.analyze_summary_for_toc(summary, book_metadata)

        # A failed analysis must NOT be persisted. ai_service swallows AI errors
        # into an error dict; storing it sets summary_analysis with
        # meets_minimum_requirements=false, which permanently blocks the readiness
        # check (has_analysis=true) for an otherwise-valid summary. Surface it as a
        # retryable error and let the readiness endpoint fall back to its basic
        # word/character-count check instead.
        if analysis.get("error"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "message": "Summary analysis is temporarily unavailable. Please try again.",
                    "error_code": "AI_ANALYSIS_FAILED",
                    "retryable": True,
                },
            )

        # Store analysis results in book record for future reference
        update_data = {
            "summary_analysis": {
                **analysis,
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
            },
            "updated_at": datetime.now(timezone.utc),
        }
        await update_book(book_id, update_data, current_user.get("auth_id"))

        return {
            "book_id": book_id,
            "analysis": analysis,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    except HTTPException:
        # Don't let the generic handler below turn our 4xx/5xx into an opaque 500.
        raise
    except AIServiceError as e:
        raise ai_error_http_exception(e)
    except Exception:
        logger.error("Error analyzing summary", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Error analyzing summary"
        )
