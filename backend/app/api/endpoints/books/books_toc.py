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


"""Toc"""

router = APIRouter()


@router.post("/{book_id}/analyze-summary", status_code=status.HTTP_200_OK)
async def analyze_book_summary(
    book_id: str,
    current_user: Dict = Depends(get_current_user),
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=5, window=60)),
):
    """
    Analyze the book summary using AI to determine readiness for TOC generation.
    This endpoint uses OpenAI to analyze the summary's structure and completeness.
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
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

        # Store analysis results in book record for future reference
        update_data = {
            "summary_analysis": {
                **analysis,
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
            },
            "updated_at": datetime.now(timezone.utc),
        }
        await update_book(book_id, update_data, current_user.get("clerk_id"))

        return {
            "book_id": book_id,
            "analysis": analysis,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error analyzing summary: {str(e)}"
        )


@router.post("/{book_id}/generate-questions", status_code=status.HTTP_200_OK)
async def generate_clarifying_questions(
    book_id: str,
    data: dict = Body(default={}),
    current_user: Dict = Depends(get_current_user),
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=3, window=60)),
):
    """
    Generate clarifying questions based on the book summary to improve TOC generation.
    Uses AI to create 3-5 targeted questions that help structure the book content.
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
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
        await update_book(book_id, update_data, current_user.get("clerk_id"))

        return {
            "book_id": book_id,
            "questions": questions,
            "generated_at": questions_data["generated_at"],
            "total_questions": len(questions),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating questions: {str(e)}"
        )


@router.get("/{book_id}/question-responses", status_code=status.HTTP_200_OK)
async def get_question_responses(
    book_id: str,
    current_user: Dict = Depends(get_current_user),
):
    """
    Get saved question responses for a book.
    Returns responses that were previously saved for TOC generation.
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to access responses for this book"
        )

    # Get question responses from book record
    question_responses = book.get("question_responses", {})

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
    data: dict = Body(...),
    current_user: Dict = Depends(get_current_user),
):
    """
    Save user responses to clarifying questions for TOC generation.
    Stores responses that will be used to generate the table of contents.
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to update responses for this book"
        )

    # Validate responses data
    responses = data.get("responses", [])
    if not isinstance(responses, list):
        raise HTTPException(
            status_code=400, detail="Responses must be provided as a list"
        )

    # Validate each response
    for i, response in enumerate(responses):
        if not isinstance(response, dict):
            raise HTTPException(
                status_code=400, detail=f"Response {i} must be an object"
            )
        if "question" not in response or "answer" not in response:
            raise HTTPException(
                status_code=400,
                detail=f"Response {i} must contain 'question' and 'answer' fields",
            )
        if not response["answer"] or not response["answer"].strip():
            raise HTTPException(
                status_code=400, detail=f"Answer for question {i} cannot be empty"
            )

    # Store responses in book record
    responses_data = {
        "responses": responses,
        "answered_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed",
    }

    # Update clarifying_questions status if it exists
    clarifying_questions = book.get("clarifying_questions", {})
    if clarifying_questions:
        clarifying_questions["status"] = "answered"

    update_data = {
        "question_responses": responses_data,
        "clarifying_questions": clarifying_questions,
        "updated_at": datetime.now(timezone.utc),
    }
    await update_book(book_id, update_data, current_user.get("clerk_id"))

    return {
        "book_id": book_id,
        "responses_saved": len(responses),
        "answered_at": responses_data["answered_at"],
        "ready_for_toc_generation": True,
    }


@router.get("/{book_id}/toc-readiness", status_code=status.HTTP_200_OK)
async def check_toc_generation_readiness(
    book_id: str,
    current_user: Dict = Depends(get_current_user),
):
    """
    Check if a book is ready for TOC generation based on summary analysis and question responses.
    Returns the current state and what steps are needed next.
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to check readiness for this book"
        )

    # Check summary existence and quality
    summary = book.get("summary", "")
    has_summary = bool(summary and len(summary) >= 30)

    # Check if summary has been analyzed
    summary_analysis = book.get("summary_analysis", {})
    has_analysis = bool(summary_analysis)
    is_summary_ready = (
        summary_analysis.get("is_ready_for_toc", False) if has_analysis else False
    )

    # Check clarifying questions status
    clarifying_questions = book.get("clarifying_questions", {})
    has_questions = bool(clarifying_questions.get("questions", []))
    questions_status = clarifying_questions.get("status", "not_generated")

    # Check question responses
    question_responses = book.get("question_responses", {})
    has_responses = bool(question_responses.get("responses", []))
    responses_status = question_responses.get("status", "not_provided")

    # Determine overall readiness
    is_ready_for_toc = (
        has_summary
        and has_analysis
        and is_summary_ready
        and has_questions
        and has_responses
        and responses_status == "completed"
    )  # Determine next steps
    next_steps = []
    if not has_summary:
        next_steps.append("Provide a book summary (minimum 30 characters)")
    elif not has_analysis:
        next_steps.append("Analyze summary for TOC readiness")
    elif not is_summary_ready:
        next_steps.append("Improve summary based on analysis suggestions")
    elif not has_questions:
        next_steps.append("Generate clarifying questions")
    elif not has_responses:
        next_steps.append("Answer clarifying questions")
    elif responses_status != "completed":
        next_steps.append("Complete all question responses")

    if is_ready_for_toc:
        next_steps.append("Ready to generate Table of Contents")

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


@router.post("/{book_id}/generate-toc", status_code=status.HTTP_200_OK)
async def generate_table_of_contents(
    book_id: str,
    data: dict = Body(default={}),
    current_user: Dict = Depends(get_current_user),
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
    if book.get("owner_id") != current_user.get("clerk_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to generate TOC for this book"
        )

    # Check if summary exists
    summary = book.get("summary", "")
    if not summary:
        raise HTTPException(
            status_code=400, detail="Book summary is required for TOC generation"
        )

    # Check if question responses exist
    question_responses = book.get("question_responses", {})
    responses = question_responses.get("responses", [])
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

        # Store generated TOC in book record
        toc_data = {
            **toc_result["toc"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "generated",
            "version": 1,
        }

        update_data = {
            "table_of_contents": toc_data,
            "updated_at": datetime.now(timezone.utc),
        }
        await update_book(book_id, update_data, current_user.get("clerk_id"))

        return {
            "book_id": book_id,
            "toc": toc_result["toc"],
            "generated_at": toc_data["generated_at"],
            "chapters_count": toc_result["chapters_count"],
            "has_subchapters": toc_result["has_subchapters"],
            "success": toc_result["success"],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating TOC: {str(e)}")


@router.get("/{book_id}/toc", status_code=status.HTTP_200_OK)
async def get_book_toc(
    book_id: str,
    current_user: Dict = Depends(get_current_user),
):
    """
    Get the Table of Contents for a book.
    Returns the current TOC structure or empty structure if none exists.
    """

    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
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
            "version": 0,
            "generated_at": None,
            "updated_at": None,
        }

    return {
        "book_id": book_id,
        "toc": {
            "chapters": toc.get("chapters", []),
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
    current_user: Dict = Depends(get_current_user),
):
    """
    Update the Table of Contents for a book.
    Saves user edits to the TOC structure with transaction support.
    """
    # Validate TOC data
    toc_data = data.get("toc", {})
    if not isinstance(toc_data, dict):
        raise HTTPException(
            status_code=400, detail="TOC data must be provided as an object"
        )

    chapters = toc_data.get("chapters", [])
    if not isinstance(chapters, list):
        raise HTTPException(
            status_code=400, detail="Chapters must be provided as a list"
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

    try:
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Updating TOC for book_id={book_id}, user_clerk_id={current_user.get('clerk_id')}")

        # Update TOC with transaction
        updated_toc = await update_toc_with_transaction(
            book_id=book_id,
            toc_data=toc_data,
            user_clerk_id=current_user.get("clerk_id")
        )

        return {
            "book_id": book_id,
            "toc": toc_data,
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
    except Exception as e:
        print(f"Error updating TOC: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update TOC")


# Individual Chapter CRUD Operations
