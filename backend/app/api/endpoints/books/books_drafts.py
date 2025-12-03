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


"""Drafts"""

router = APIRouter()


@router.post("/{book_id}/chapters/{chapter_id}/generate-draft", response_model=dict)
async def generate_chapter_draft(
    book_id: str,
    chapter_id: str,
    data: dict = Body(default={}),
    current_user: Dict = Depends(get_current_user),
    rate_limit_info: Dict = Depends(
        get_rate_limiter(limit=5, window=3600)
    ),  # 5 per hour
):
    """
    Generate a draft chapter based on Q&A responses using AI.
    This transforms interview-style responses into narrative content.
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to generate draft for this book"
        )

    # Get chapter information from TOC
    toc = book.get("table_of_contents", {})
    chapters = toc.get("chapters", [])

    # Find the chapter
    chapter_info = None
    for chapter in chapters:
        if chapter.get("id") == chapter_id:
            chapter_info = chapter
            break
        # Check subchapters
        for subchapter in chapter.get("subchapters", []):
            if subchapter.get("id") == chapter_id:
                chapter_info = subchapter
                break

    if not chapter_info:
        raise HTTPException(status_code=404, detail="Chapter not found in table of contents")

    # Get question responses from request or book data
    question_responses = data.get("question_responses", [])

    # If no responses provided, try to get from stored chapter questions
    if not question_responses:
        # This would require implementing a question storage system
        # For now, we'll require responses to be provided
        raise HTTPException(
            status_code=400,
            detail="Question responses are required for draft generation. Please provide Q&A pairs."
        )

    # Validate question responses format
    for response in question_responses:
        if not isinstance(response, dict) or "question" not in response or "answer" not in response:
            raise HTTPException(
                status_code=400,
                detail="Each question response must have 'question' and 'answer' fields"
            )

    # Get optional parameters
    writing_style = data.get("writing_style", None)
    target_length = data.get("target_length", 2000)

    # Validate target length
    if not isinstance(target_length, int) or target_length < 100 or target_length > 10000:
        target_length = 2000

    # Prepare book metadata for context
    book_metadata = {
        "title": book.get("title", ""),
        "genre": book.get("genre", ""),
        "target_audience": book.get("target_audience", ""),
    }

    try:
        # Generate draft using AI service
        result = await ai_service.generate_chapter_draft(
            chapter_title=chapter_info.get("title", ""),
            chapter_description=chapter_info.get("description", ""),
            question_responses=question_responses,
            book_metadata=book_metadata,
            writing_style=writing_style,
            target_length=target_length
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate draft: {result.get('error', 'Unknown error')}"
            )

        # Log the draft generation
        await audit_request(
            request=Request(
                {
                    "type": "http",
                    "method": "POST",
                    "url": f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-draft",
                    "headers": {},
                    "path": f"/api/v1/books/{book_id}/chapters/{chapter_id}/generate-draft"
                }
            ),
            current_user=current_user,
            action="generate_chapter_draft",
            resource_type="chapter",
            target_id=chapter_id,
            metadata={
                "book_id": book_id,
                "chapter_title": chapter_info.get("title"),
                "question_count": len(question_responses),
                "target_length": target_length,
                "actual_length": result["metadata"].get("word_count", 0),
                "writing_style": writing_style or "default"
            }
        )

        return {
            "success": True,
            "book_id": book_id,
            "chapter_id": chapter_id,
            "draft": result["draft"],
            "metadata": result["metadata"],
            "suggestions": result.get("suggestions", []),
            "message": "Draft generated successfully"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating draft: {str(e)}"
        )
