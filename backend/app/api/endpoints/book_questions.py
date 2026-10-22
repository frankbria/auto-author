"""
Pre-TOC (book-level) question endpoints: generate, read and save the
clarifying questions and their responses.

Extracted verbatim from ``books.py`` (issue #1126). Behavior-preserving move:
routes are mounted under the same ``/books`` prefix in ``router.py``.
"""
import logging
from datetime import datetime, timezone
from typing import Dict

from fastapi import APIRouter, Body, Depends, HTTPException, status

from app.api.dependencies import (
    get_rate_limiter, get_ai_usage_quota, get_entitlement_checker
)
from app.core.security import get_current_user_from_session
from app.db.database import get_book_fields, get_book_metadata_by_id, update_book
from app.schemas.ai_input import SaveQuestionResponsesRequest
from app.services.ai_errors import AIServiceError
from app.services.ai_service import ai_service
from app.utils.error_handlers import ai_error_http_exception

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{book_id}/generate-questions", status_code=status.HTTP_200_OK, dependencies=[Depends(get_ai_usage_quota()), Depends(get_entitlement_checker("generate_questions"))])
async def generate_clarifying_questions(
    book_id: str,
    data: dict = Body(default={}),
    current_user: Dict = Depends(get_current_user_from_session),
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=3, window=60)),
):
    """
    Generate clarifying questions based on the book summary to improve TOC generation.
    Uses AI to create 3-5 targeted questions that help structure the book content.
    """
    # Get the book and verify ownership
    book = await get_book_metadata_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("auth_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to generate questions for this book"
        )

    # Check if summary exists
    summary = book.get("summary", "")
    if not summary:
        raise HTTPException(
            status_code=400, detail="Book summary is required for question generation"
        )

    # Get number of questions from request (default: 4)
    num_questions = data.get("num_questions", 4)
    if not isinstance(num_questions, int) or num_questions < 3 or num_questions > 6:
        num_questions = 4

    # Prepare book metadata for context
    book_metadata = {
        "title": book.get("title", ""),
        "genre": book.get("genre", ""),
        "target_audience": book.get("target_audience", ""),
    }

    try:
        # Generate questions using AI service
        questions = await ai_service.generate_clarifying_questions(
            summary, book_metadata, num_questions
        )

        # Store questions in book record
        questions_data = {
            "questions": questions,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending",  # pending, answered, used
        }

        update_data = {
            "clarifying_questions": questions_data,
            "updated_at": datetime.now(timezone.utc),
        }
        await update_book(book_id, update_data, current_user.get("auth_id"))

        return {
            "book_id": book_id,
            "questions": questions,
            "generated_at": questions_data["generated_at"],
            "total_questions": len(questions),
        }

    except AIServiceError as e:
        raise ai_error_http_exception(e)
    except Exception:
        logger.error("Unexpected error generating questions", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error generating questions"
        )


@router.get("/{book_id}/question-responses", status_code=status.HTTP_200_OK)
async def get_question_responses(
    book_id: str,
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    Get saved question responses for a book.
    Returns responses that were previously saved for TOC generation.
    """
    # Get the book and verify ownership
    book = await get_book_fields(book_id, "owner_id", "question_responses")
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("auth_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to access responses for this book"
        )

    # Get question responses from book record
    question_responses = book.get("question_responses", {})

    # Legitimate "no data yet" case: the user hasn't answered any clarifying
    # questions for this book. This is real DB-backed state (an empty/absent
    # `question_responses` field), not mock data — the shape matches the
    # populated response below so the frontend can handle both uniformly.
    if not question_responses:
        return {"responses": [], "status": "not_provided"}

    return {
        "responses": question_responses.get("responses", []),
        "answered_at": question_responses.get("answered_at"),
        "status": question_responses.get("status", "not_provided"),
    }


@router.put("/{book_id}/question-responses", status_code=status.HTTP_200_OK)
async def save_question_responses(
    book_id: str,
    data: SaveQuestionResponsesRequest,
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    Save user responses to clarifying questions for TOC generation.
    Stores responses that will be used to generate the table of contents.
    """
    # Get the book and verify ownership
    book = await get_book_fields(book_id, "owner_id", "clarifying_questions")
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("auth_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to update responses for this book"
        )

    # Shape and size are checked by the request model (#800).
    responses = [pair.model_dump() for pair in data.responses]
    for i, response in enumerate(responses):
        if not response["answer"].strip():
            raise HTTPException(
                status_code=400, detail=f"Answer for question {i} cannot be empty"
            )

    # Derive completion status honestly (#276). All answers are validated
    # non-empty above, so a set is "completed" only when every clarifying
    # question on the book is covered by a response. Coverage (by question text),
    # not a count — duplicate or stale responses could otherwise reach the count
    # while leaving a current question unanswered. The #203 auto-save persists
    # partial sets mid-typing; without a question set to compare against we can't
    # assert completeness, so we fail toward "draft" — never a false "completed".
    # Stored questions may be plain strings or `{"question"/"question_text": ...}`
    # dicts depending on the generation path, so normalize before comparing.
    def _q_text(q):
        if isinstance(q, dict):
            return q.get("question", q.get("question_text", ""))
        return q

    clarifying_questions = book.get("clarifying_questions", {})
    question_texts = [_q_text(q) for q in clarifying_questions.get("questions", [])]
    answered = {_q_text(r.get("question")) for r in responses}
    is_complete = bool(question_texts) and all(t in answered for t in question_texts)

    responses_data = {
        "responses": responses,
        "answered_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed" if is_complete else "draft",
    }

    # Keep clarifying_questions status in step with completeness if it exists.
    if clarifying_questions:
        clarifying_questions["status"] = "answered" if is_complete else "pending"

    update_data = {
        "question_responses": responses_data,
        "clarifying_questions": clarifying_questions,
        "updated_at": datetime.now(timezone.utc),
    }
    await update_book(book_id, update_data, current_user.get("auth_id"))

    return {
        "book_id": book_id,
        "responses_saved": len(responses),
        "answered_at": responses_data["answered_at"],
        "ready_for_toc_generation": is_complete,
    }
