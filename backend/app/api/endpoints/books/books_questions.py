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


"""Questions"""

router = APIRouter()


@router.post("/{book_id}/chapters/{chapter_id}/generate-questions", response_model=GenerateQuestionsResponse)
async def generate_chapter_questions(
    book_id: str,
    chapter_id: str,
    request_data: GenerateQuestionsRequest = Body(...),
    current_user: Dict = Depends(get_current_user),
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=3, window=120)), # 3 per 2 minutes
):
    """
    Generate interview-style questions for a specific chapter based on its content and metadata.

    This endpoint uses AI to create contextually relevant questions that help authors develop
    chapter content through a guided Q&A process. Questions are generated based on the chapter title,
    description, and book metadata (genre, audience, etc.).

    - Supports filtering by difficulty level (easy, medium, hard)
    - Allows focusing on specific question types (character, plot, setting, theme, research)
    - Returns a batch of questions with metadata to guide the author
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to generate questions for this book"
        )

    # Get question generation service
    question_service = get_question_generation_service()

    try:
        # Generate questions
        result = await question_service.generate_questions_for_chapter(
            book_id=book_id,
            chapter_id=chapter_id,
            count=request_data.count,
            difficulty=request_data.difficulty.value if request_data.difficulty else None,
            focus=[q_type.value for q_type in request_data.focus] if request_data.focus else None,
            user_id=current_user.get("clerk_id")
        )

        # Log question generation
        await audit_request(
            request=None,  # Request object not available in this context
            current_user=current_user,
            action="generate_questions",
            resource_type="chapter",
            target_id=chapter_id,
            metadata={
                "book_id": book_id,
                "count": request_data.count,
                "difficulty": request_data.difficulty.value if request_data.difficulty else None,
                "focus": [q_type.value for q_type in request_data.focus] if request_data.focus else None,
                "questions_generated": len(result.questions),
            }
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating questions: {str(e)}"
        )


@router.get("/{book_id}/chapters/{chapter_id}/questions", response_model=QuestionListResponse)
async def list_chapter_questions(
    book_id: str,
    chapter_id: str,
    status: Optional[str] = None,
    category: Optional[str] = None,
    question_type: Optional[QuestionType] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    current_user: Dict = Depends(get_current_user),
):
    """
    List questions for a specific chapter with optional filtering and pagination.

    This endpoint retrieves questions that have been generated for a chapter, with options to:
    - Filter by response status (questions with/without responses)
    - Filter by category (specific aspects of writing like "character motivation")
    - Filter by question type (character, plot, setting, theme, research)
    - Paginate results for better performance with large question sets
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to access this book's questions"
        )

    # Get question service
    question_service = get_question_generation_service()

    try:
        # Get questions with filters
        result = await question_service.get_questions_for_chapter(
            book_id=book_id,
            chapter_id=chapter_id,
            status=status,
            category=category,
            question_type=question_type.value if question_type else None,
            page=page,
            limit=limit
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving questions: {str(e)}"
        )


@router.put(
    "/{book_id}/chapters/{chapter_id}/questions/{question_id}/response",
    response_model=Dict[str, Any]
)
async def save_question_response(
    book_id: str,
    chapter_id: str,
    question_id: str,
    response_data: QuestionResponseCreate,
    current_user: Dict = Depends(get_current_user),
):
    """
    Save or update a response to a specific question.

    This endpoint allows authors to save their responses to interview-style questions.
    - Supports saving draft responses for later completion
    - Tracks editing history and word count
    - Validates response content
    - Auto-saves metadata like timestamps and word count
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to save responses for this book"
        )

    # Get question service
    question_service = get_question_generation_service()

    try:
        # Save response
        result = await question_service.save_question_response(
            book_id=book_id,
            chapter_id=chapter_id,
            question_id=question_id,
            response_data=response_data,
            user_id=current_user.get("clerk_id")
        )

        # Calculate word count for logging
        word_count = len(response_data.response_text.split()) if response_data.response_text else 0

        # Log response save
        await audit_request(
            request=None,
            current_user=current_user,
            action="save_question_response",
            resource_type="question",
            target_id=question_id,
            metadata={
                "book_id": book_id,
                "chapter_id": chapter_id,
                "status": response_data.status,
                "word_count": word_count,
                "is_update": "id" in result,
            }
        )

        return {
            "response": result,
            "success": True,
            "message": "Response saved successfully",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error saving response: {str(e)}"
        )


@router.get(
    "/{book_id}/chapters/{chapter_id}/questions/{question_id}/response",
    response_model=Dict[str, Any]
)
async def get_question_response(
    book_id: str,
    chapter_id: str,
    question_id: str,
    current_user: Dict = Depends(get_current_user),
):
    """
    Get the author's response to a specific question.

    This endpoint retrieves the saved response for a question, if one exists.
    Returns null if no response has been saved yet.
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to access responses for this book"
        )

    # Get question service
    question_service = get_question_generation_service()

    try:
        # Get response
        result = await question_service.get_question_response(
            question_id=question_id,
            user_id=current_user.get("clerk_id")
        )

        return {
            "response": result,
            "has_response": result is not None,
            "success": True,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving response: {str(e)}"
        )


@router.post(
    "/{book_id}/chapters/{chapter_id}/questions/{question_id}/rating",
    response_model=Dict[str, Any]
)
async def rate_question(
    book_id: str,
    chapter_id: str,
    question_id: str,
    rating_data: QuestionRating,
    current_user: Dict = Depends(get_current_user),
):
    """
    Rate a question's relevance and quality.

    This endpoint allows authors to provide feedback on questions to improve future generation.
    - Uses a 1-5 star rating system
    - Accepts optional feedback comments
    - Updates existing ratings if already provided
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to rate questions for this book"
        )

    # Get question service
    question_service = get_question_generation_service()

    try:
        # Save rating
        result = await question_service.save_question_rating(
            question_id=question_id,
            rating_data=rating_data,
            user_id=current_user.get("clerk_id")
        )

        # Log rating
        await audit_request(
            request=None,
            current_user=current_user,
            action="rate_question",
            resource_type="question",
            target_id=question_id,
            metadata={
                "book_id": book_id,
                "chapter_id": chapter_id,
                "rating": rating_data.rating,
                "has_feedback": rating_data.feedback is not None,
            }
        )

        return {
            "rating": result,
            "success": True,
            "message": "Question rated successfully",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error saving rating: {str(e)}"
        )


@router.get(
    "/{book_id}/chapters/{chapter_id}/question-progress",
    response_model=QuestionProgressResponse
)
async def get_chapter_question_progress(
    book_id: str,
    chapter_id: str,
    current_user: Dict = Depends(get_current_user),
):
    """
    Get progress information for a chapter's questions.

    This endpoint provides statistics about question completion status:
    - Total number of questions
    - Number of completed questions
    - Progress percentage
    - Overall status (not-started, in-progress, completed)

    Used for progress tracking and visual indicators in the chapter tabs.
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to access this book's questions"
        )

    # Get question service
    question_service = get_question_generation_service()

    try:
        # Get progress
        result = await question_service.get_chapter_question_progress(
            book_id=book_id,
            chapter_id=chapter_id,
            user_id=current_user.get("clerk_id")
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving question progress: {str(e)}"
        )


@router.post(
    "/{book_id}/chapters/{chapter_id}/regenerate-questions",
    response_model=GenerateQuestionsResponse
)
async def regenerate_chapter_questions(
    book_id: str,
    chapter_id: str,
    request_data: GenerateQuestionsRequest = Body(...),
    preserve_responses: bool = Query(True, description="Preserve questions with responses"),
    current_user: Dict = Depends(get_current_user),
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=2, window=180)), # 2 per 3 minutes
):
    """
    Regenerate questions for a chapter, optionally preserving existing responses.

    This endpoint allows authors to get fresh questions while keeping their progress:
    - Can preserve questions that already have responses
    - Deletes questions without responses
    - Generates new questions to replace deleted ones
    - Applies the same filtering options as the generation endpoint
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to regenerate questions for this book"
        )

    # Get question service
    question_service = get_question_generation_service()

    try:
        # Regenerate questions
        result = await question_service.regenerate_chapter_questions(
            book_id=book_id,
            chapter_id=chapter_id,
            count=request_data.count,
            difficulty=request_data.difficulty.value if request_data.difficulty else None,
            focus=[q_type.value for q_type in request_data.focus] if request_data.focus else None,
            user_id=current_user.get("clerk_id"),
            preserve_responses=preserve_responses
        )

        # Log question regeneration
        await audit_request(
            request=None,
            current_user=current_user,
            action="regenerate_questions",
            resource_type="chapter",
            target_id=chapter_id,
            metadata={
                "book_id": book_id,
                "count": request_data.count,
                "difficulty": request_data.difficulty.value if request_data.difficulty else None,
                "focus": [q_type.value for q_type in request_data.focus] if request_data.focus else None,
                "preserve_responses": preserve_responses,
                "preserved_count": result.get("preserved_count", 0),
                "new_count": result.get("new_count", 0),
                "total_count": result.get("total", 0),
            }
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error regenerating questions: {str(e)}"
        )
