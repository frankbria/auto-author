"""
Chapter question endpoints: generate, list, answer, rate, regenerate, progress
and batch save.

Extracted verbatim from ``books.py`` (issue #857). Behavior-preserving move:
routes are mounted under the same ``/books`` prefix in ``router.py``.
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.api.dependencies import (
    audit_after_commit, get_rate_limiter, get_ai_usage_quota,
    get_entitlement_checker
)
from app.core.security import get_current_user_from_session
from app.db.database import (
    get_book_owner_id,
)
from app.schemas.ai_input import MAX_ANSWER_CHARS
from app.schemas.book import (
    Question,
    QuestionType,
    QuestionResponseCreate,
    QuestionRating,
    GenerateQuestionsRequest,
    GenerateQuestionsResponse,
    RegenerateQuestionRequest,
    QuestionListResponse,
    QuestionProgressResponse,
)
from app.services.question_generation_service import (
    get_question_generation_service,
    RegenerationLimitError,
    QuestionNotFoundError,
)
from app.utils.error_handlers import (
    handle_book_not_found,
    handle_unauthorized_access,
    handle_validation_error,
    handle_question_generation_error,
    handle_question_not_found,
    handle_response_save_error,
    handle_rating_save_error,
    handle_generic_error,
    generate_request_id,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{book_id}/chapters/{chapter_id}/generate-questions", response_model=GenerateQuestionsResponse, dependencies=[Depends(get_ai_usage_quota()), Depends(get_entitlement_checker("chapter_generate_questions"))])
async def generate_chapter_questions(
    book_id: str,
    chapter_id: str,
    request_data: GenerateQuestionsRequest = Body(...),
    current_user: Dict = Depends(get_current_user_from_session),
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

    Error Codes:
        - BOOK_NOT_FOUND (404): Book does not exist
        - FORBIDDEN_OPERATION (403): User is not the book owner
        - VALIDATION_FAILED (422): Invalid request parameters
        - QUESTION_GENERATION_FAILED (500/503): Question generation failed
        - RATE_LIMIT_EXCEEDED (429): Too many requests
    """
    request_id = generate_request_id()

    # Validate request parameters
    if request_data.count and (request_data.count < 1 or request_data.count > 50):
        raise handle_validation_error(
            field="count",
            message="Question count must be between 1 and 50",
            value=request_data.count,
            request_id=request_id
        )

    # Get the book and verify ownership
    owner_id = await get_book_owner_id(book_id)
    if owner_id is None:
        raise handle_book_not_found(book_id, request_id)

    if owner_id != current_user.get("auth_id"):
        raise handle_unauthorized_access(
            resource_type="book",
            resource_id=book_id,
            user_id=current_user.get("auth_id"),
            required_permission="owner",
            request_id=request_id
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
            user_id=current_user.get("auth_id")
        )

        # Log question generation
        await audit_after_commit(
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
                "request_id": request_id,
            }
        )

        return result

    except ValueError as e:
        # Handle validation errors from the service
        raise handle_validation_error(
            field="chapter_id",
            message=str(e),
            value=chapter_id,
            request_id=request_id
        )
    except Exception as e:
        # Handle all other errors including AI service errors
        raise handle_question_generation_error(
            error=e,
            book_id=book_id,
            chapter_id=chapter_id,
            request_id=request_id
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
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    List questions for a specific chapter with optional filtering and pagination.

    This endpoint retrieves questions that have been generated for a chapter, with options to:
    - Filter by response status (questions with/without responses)
    - Filter by category (specific aspects of writing like "character motivation")
    - Filter by question type (character, plot, setting, theme, research)
    - Paginate results for better performance with large question sets

    Error Codes:
        - BOOK_NOT_FOUND (404): Book does not exist
        - FORBIDDEN_OPERATION (403): User is not the book owner
        - VALIDATION_FAILED (422): Invalid filter or pagination parameters
        - OPERATION_FAILED (500): Error retrieving questions
    """
    request_id = generate_request_id()

    # Validate pagination parameters
    if page < 1:
        raise handle_validation_error(
            field="page",
            message="Page number must be greater than 0",
            value=page,
            request_id=request_id
        )

    if limit < 1 or limit > 50:
        raise handle_validation_error(
            field="limit",
            message="Limit must be between 1 and 50",
            value=limit,
            request_id=request_id
        )

    # Get the book and verify ownership
    owner_id = await get_book_owner_id(book_id)
    if owner_id is None:
        raise handle_book_not_found(book_id, request_id)

    if owner_id != current_user.get("auth_id"):
        raise handle_unauthorized_access(
            resource_type="book",
            resource_id=book_id,
            user_id=current_user.get("auth_id"),
            required_permission="owner",
            request_id=request_id
        )

    # Get question service
    question_service = get_question_generation_service()

    try:
        # Get questions with filters
        result = await question_service.get_questions_for_chapter(
            book_id=book_id,
            chapter_id=chapter_id,
            user_id=current_user.get("auth_id"),
            status=status,
            category=category,
            question_type=question_type.value if question_type else None,
            page=page,
            limit=limit
        )

        return result

    except ValueError as e:
        # Handle validation errors from the service
        raise handle_validation_error(
            field="filters",
            message=str(e),
            request_id=request_id
        )
    except Exception as e:
        # Handle all other errors
        raise handle_generic_error(
            error=e,
            operation="retrieving questions",
            context={
                "book_id": book_id,
                "chapter_id": chapter_id,
                "filters": {
                    "status": status,
                    "category": category,
                    "question_type": question_type.value if question_type else None,
                }
            },
            request_id=request_id
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
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    Save or update a response to a specific question.

    This endpoint allows authors to save their responses to interview-style questions.
    - Supports saving draft responses for later completion
    - Tracks editing history and word count
    - Validates response content
    - Auto-saves metadata like timestamps and word count

    Error Codes:
        - BOOK_NOT_FOUND (404): Book does not exist
        - QUESTION_NOT_FOUND (404): Question does not exist
        - FORBIDDEN_OPERATION (403): User is not the book owner
        - VALIDATION_FAILED (422): Invalid response data
        - RESPONSE_SAVE_FAILED (500): Error saving response
    """
    request_id = generate_request_id()

    # Validate response data
    if not response_data.response_text or not response_data.response_text.strip():
        raise handle_validation_error(
            field="response_text",
            message="Response text cannot be empty",
            value=response_data.response_text,
            request_id=request_id
        )

    # Get the book and verify ownership
    owner_id = await get_book_owner_id(book_id)
    if owner_id is None:
        raise handle_book_not_found(book_id, request_id)

    if owner_id != current_user.get("auth_id"):
        raise handle_unauthorized_access(
            resource_type="book",
            resource_id=book_id,
            user_id=current_user.get("auth_id"),
            required_permission="owner",
            request_id=request_id
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
            user_id=current_user.get("auth_id")
        )

        is_update = result.pop("is_update", False)

        # Calculate word count for logging
        word_count = len(response_data.response_text.split()) if response_data.response_text else 0

        # Log response save
        await audit_after_commit(
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
                "is_update": is_update,
                "request_id": request_id,
            }
        )

        return {
            "response": result,
            "success": True,
            "message": "Response saved successfully",
        }

    except ValueError as e:
        # Handle validation errors from the service
        raise handle_response_save_error(
            error=e,
            question_id=question_id,
            user_id=current_user.get("auth_id"),
            request_id=request_id
        )
    except Exception as e:
        # Handle all other errors
        raise handle_response_save_error(
            error=e,
            question_id=question_id,
            user_id=current_user.get("auth_id"),
            request_id=request_id
        )


@router.get(
    "/{book_id}/chapters/{chapter_id}/questions/{question_id}/response",
    response_model=Dict[str, Any]
)
async def get_question_response(
    book_id: str,
    chapter_id: str,
    question_id: str,
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    Get the author's response to a specific question.

    This endpoint retrieves the saved response for a question, if one exists.
    Returns null if no response has been saved yet.

    Error Codes:
        - BOOK_NOT_FOUND (404): Book does not exist
        - QUESTION_NOT_FOUND (404): Question does not exist
        - FORBIDDEN_OPERATION (403): User is not the book owner
        - OPERATION_FAILED (500): Error retrieving response
    """
    request_id = generate_request_id()

    # Get the book and verify ownership
    owner_id = await get_book_owner_id(book_id)
    if owner_id is None:
        raise handle_book_not_found(book_id, request_id)

    if owner_id != current_user.get("auth_id"):
        raise handle_unauthorized_access(
            resource_type="book",
            resource_id=book_id,
            user_id=current_user.get("auth_id"),
            required_permission="owner",
            request_id=request_id
        )

    # Get question service
    question_service = get_question_generation_service()

    try:
        # Get response
        result = await question_service.get_question_response(
            question_id=question_id,
            user_id=current_user.get("auth_id")
        )

        return {
            "response": result,
            "has_response": result is not None,
            "success": True,
        }

    except ValueError:
        # Handle question not found errors
        raise handle_question_not_found(question_id, request_id)
    except Exception as e:
        # Handle all other errors
        raise handle_generic_error(
            error=e,
            operation="retrieving question response",
            context={
                "book_id": book_id,
                "chapter_id": chapter_id,
                "question_id": question_id,
            },
            request_id=request_id
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
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    Rate a question's relevance and quality.

    This endpoint allows authors to provide feedback on questions to improve future generation.
    - Uses a 1-5 star rating system
    - Accepts optional feedback comments
    - Updates existing ratings if already provided

    Error Codes:
        - BOOK_NOT_FOUND (404): Book does not exist
        - FORBIDDEN_OPERATION (403): User is not the book owner
        - VALIDATION_FAILED (422): Rating outside 1-5 (schema), or the question
          does not exist or is not the user's
        - RATING_SAVE_FAILED (500): Error saving rating
    """
    request_id = generate_request_id()

    # Get the book and verify ownership
    owner_id = await get_book_owner_id(book_id)
    if owner_id is None:
        raise handle_book_not_found(book_id, request_id)

    if owner_id != current_user.get("auth_id"):
        raise handle_unauthorized_access(
            resource_type="book",
            resource_id=book_id,
            user_id=current_user.get("auth_id"),
            required_permission="owner",
            request_id=request_id
        )

    # Get question service
    question_service = get_question_generation_service()

    try:
        # Save rating
        result = await question_service.save_question_rating(
            question_id=question_id,
            rating_data=rating_data,
            user_id=current_user.get("auth_id")
        )

        # Log rating
        await audit_after_commit(
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
                "request_id": request_id,
            }
        )

        return {
            "rating": result,
            "success": True,
            "message": "Question rated successfully",
        }

    except ValueError as e:
        # Handle validation errors from the service
        raise handle_rating_save_error(
            error=e,
            question_id=question_id,
            user_id=current_user.get("auth_id"),
            rating_value=rating_data.rating,
            request_id=request_id
        )
    except Exception as e:
        # Handle all other errors
        raise handle_rating_save_error(
            error=e,
            question_id=question_id,
            user_id=current_user.get("auth_id"),
            rating_value=rating_data.rating,
            request_id=request_id
        )


@router.post(
    "/{book_id}/chapters/{chapter_id}/questions/{question_id}/regenerate",
    response_model=Question,
    dependencies=[Depends(get_ai_usage_quota()), Depends(get_entitlement_checker("regenerate_question"))],
)
async def regenerate_single_question(
    book_id: str,
    chapter_id: str,
    question_id: str,
    request_data: RegenerateQuestionRequest = Body(default=RegenerateQuestionRequest()),
    current_user: Dict = Depends(get_current_user_from_session),
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=2, window=180)),  # 2 per 3 minutes
):
    """
    Regenerate a single question, replacing it with a fresh, meaningfully different one.

    The new question avoids duplicating the chapter's other questions and incorporates any
    prior rating feedback. Each question may be regenerated up to a fixed limit.

    Error Codes:
        - BOOK_NOT_FOUND (404): Book does not exist
        - QUESTION_NOT_FOUND (404): Question does not exist or isn't owned by the user
        - FORBIDDEN_OPERATION (403): User is not the book owner
        - REGENERATION_LIMIT_REACHED (429): Question hit its regeneration cap
        - RATE_LIMIT_EXCEEDED (429): Too many requests
        - QUESTION_GENERATION_FAILED (500/503): Regeneration failed
    """
    request_id = generate_request_id()

    # Get the book and verify ownership
    owner_id = await get_book_owner_id(book_id)
    if owner_id is None:
        raise handle_book_not_found(book_id, request_id)

    if owner_id != current_user.get("auth_id"):
        raise handle_unauthorized_access(
            resource_type="book",
            resource_id=book_id,
            user_id=current_user.get("auth_id"),
            required_permission="owner",
            request_id=request_id
        )

    question_service = get_question_generation_service()

    try:
        result = await question_service.regenerate_single_question(
            book_id=book_id,
            chapter_id=chapter_id,
            question_id=question_id,
            user_id=current_user.get("auth_id"),
            focus=request_data.focus.value if request_data.focus else None,
        )

        await audit_after_commit(
            request=None,
            current_user=current_user,
            action="regenerate_single_question",
            resource_type="question",
            target_id=question_id,
            metadata={
                "book_id": book_id,
                "chapter_id": chapter_id,
                "focus": request_data.focus.value if request_data.focus else None,
                "regeneration_count": result.regeneration_count,
                "request_id": request_id,
            }
        )

        return result

    except QuestionNotFoundError:
        raise handle_question_not_found(question_id, request_id)
    except RegenerationLimitError as e:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "REGENERATION_LIMIT_REACHED",
                "message": str(e),
                "request_id": request_id,
            }
        )
    except Exception as e:
        raise handle_question_generation_error(
            error=e,
            book_id=book_id,
            chapter_id=chapter_id,
            request_id=request_id
        )


@router.get(
    "/{book_id}/chapters/{chapter_id}/question-progress",
    response_model=QuestionProgressResponse
)
async def get_chapter_question_progress(
    book_id: str,
    chapter_id: str,
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    Get progress information for a chapter's questions.

    This endpoint provides statistics about question completion status:
    - Total number of questions
    - Number of completed questions
    - Progress percentage
    - Overall status (not-started, in-progress, completed)

    Used for progress tracking and visual indicators in the chapter tabs.

    Error Codes:
        - BOOK_NOT_FOUND (404): Book does not exist
        - CHAPTER_NOT_FOUND (404): Chapter does not exist
        - FORBIDDEN_OPERATION (403): User is not the book owner
        - OPERATION_FAILED (500): Error retrieving progress
    """
    request_id = generate_request_id()

    # Get the book and verify ownership
    owner_id = await get_book_owner_id(book_id)
    if owner_id is None:
        raise handle_book_not_found(book_id, request_id)

    if owner_id != current_user.get("auth_id"):
        raise handle_unauthorized_access(
            resource_type="book",
            resource_id=book_id,
            user_id=current_user.get("auth_id"),
            required_permission="owner",
            request_id=request_id
        )

    # Get question service
    question_service = get_question_generation_service()

    try:
        # Get progress
        result = await question_service.get_chapter_question_progress(
            book_id=book_id,
            chapter_id=chapter_id,
            user_id=current_user.get("auth_id")
        )

        return result

    except ValueError as e:
        # Handle chapter not found errors
        raise handle_validation_error(
            field="chapter_id",
            message=str(e),
            value=chapter_id,
            request_id=request_id
        )
    except Exception as e:
        # Handle all other errors
        raise handle_generic_error(
            error=e,
            operation="retrieving question progress",
            context={
                "book_id": book_id,
                "chapter_id": chapter_id,
            },
            request_id=request_id
        )


@router.post(
    "/{book_id}/chapters/{chapter_id}/regenerate-questions",
    response_model=GenerateQuestionsResponse,
    dependencies=[Depends(get_ai_usage_quota()), Depends(get_entitlement_checker("regenerate_questions"))],
)
async def regenerate_chapter_questions(
    book_id: str,
    chapter_id: str,
    request_data: GenerateQuestionsRequest = Body(...),
    preserve_responses: bool = Query(True, description="Preserve questions with responses"),
    current_user: Dict = Depends(get_current_user_from_session),
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=2, window=180)), # 2 per 3 minutes
):
    """
    Regenerate questions for a chapter, optionally preserving existing responses.

    This endpoint allows authors to get fresh questions while keeping their progress:
    - Can preserve questions that already have responses
    - Deletes questions without responses
    - Generates new questions to replace deleted ones
    - Applies the same filtering options as the generation endpoint

    Error Codes:
        - BOOK_NOT_FOUND (404): Book does not exist
        - CHAPTER_NOT_FOUND (404): Chapter does not exist
        - FORBIDDEN_OPERATION (403): User is not the book owner
        - VALIDATION_FAILED (422): Invalid request parameters
        - QUESTION_GENERATION_FAILED (500/503): Question regeneration failed
        - RATE_LIMIT_EXCEEDED (429): Too many requests
    """
    request_id = generate_request_id()

    # Validate request parameters
    if request_data.count and (request_data.count < 1 or request_data.count > 50):
        raise handle_validation_error(
            field="count",
            message="Question count must be between 1 and 50",
            value=request_data.count,
            request_id=request_id
        )

    # Get the book and verify ownership
    owner_id = await get_book_owner_id(book_id)
    if owner_id is None:
        raise handle_book_not_found(book_id, request_id)

    if owner_id != current_user.get("auth_id"):
        raise handle_unauthorized_access(
            resource_type="book",
            resource_id=book_id,
            user_id=current_user.get("auth_id"),
            required_permission="owner",
            request_id=request_id
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
            user_id=current_user.get("auth_id"),
            preserve_responses=preserve_responses
        )

        # Log question regeneration
        await audit_after_commit(
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
                "preserved_count": getattr(result, "preserved_count", 0),
                "new_count": getattr(result, "new_count", 0),
                "total_count": result.total,
                "request_id": request_id,
            }
        )

        return result

    except ValueError as e:
        # Handle validation errors from the service
        raise handle_validation_error(
            field="chapter_id",
            message=str(e),
            value=chapter_id,
            request_id=request_id
        )
    except Exception as e:
        # Handle all other errors including AI service errors
        raise handle_question_generation_error(
            error=e,
            book_id=book_id,
            chapter_id=chapter_id,
            request_id=request_id
        )


@router.post(
    "/{book_id}/chapters/{chapter_id}/questions/responses/batch",
    response_model=Dict[str, Any]
)
async def save_question_responses_batch_endpoint(
    book_id: str,
    chapter_id: str,
    responses: List[Dict[str, Any]] = Body(...),
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    Save multiple question responses in a single batch operation.

    This endpoint provides efficient batch saving of question responses:
    - Validates all responses before saving
    - Uses bulk write operations for better performance
    - Handles partial failures gracefully
    - Returns detailed results for each response
    - Tracks edit history for updates
    - Auto-calculates word counts

    Request body:
        responses: Array of objects with:
            - question_id: The question being answered
            - response_text: The response content
            - status: "draft" or "completed" (defaults to "draft")

    Returns:
        - success: Overall operation success (false if any response failed)
        - total: Total number of responses provided
        - saved: Number of responses successfully saved
        - failed: Number of responses that failed
        - results: Array of per-response results with success status
        - errors: Array of error details for failed responses (if any)

    Error Codes:
        - BOOK_NOT_FOUND (404): Book does not exist
        - FORBIDDEN_OPERATION (403): User is not the book owner
        - VALIDATION_FAILED (422): Invalid request data
        - RESPONSE_SAVE_FAILED (500): Error saving batch responses
    """
    # Generate request ID for tracking
    request_id = generate_request_id()

    # Import the batch save function
    from app.db.questions import save_question_responses_batch as db_save_batch

    # Validate request - check for empty responses
    if not responses:
        raise handle_validation_error(
            field="responses",
            message="No responses provided",
            value=responses,
            request_id=request_id
        )

    # Validate batch size
    if len(responses) > 100:
        raise handle_validation_error(
            field="responses",
            message="Batch size exceeds maximum of 100 responses",
            value=len(responses),
            request_id=request_id
        )

    # The cap a single saved answer has (#800); an answer comes back as model input.
    if any(len(str(item.get("response_text") or "")) > MAX_ANSWER_CHARS for item in responses):
        raise handle_validation_error(
            field="responses",
            message=f"A response is longer than the limit of {MAX_ANSWER_CHARS} characters",
            request_id=request_id
        )

    # Get the book and verify ownership
    owner_id = await get_book_owner_id(book_id)
    if owner_id is None:
        raise handle_book_not_found(book_id, request_id)

    if owner_id != current_user.get("auth_id"):
        raise handle_unauthorized_access(
            resource_type="book",
            resource_id=book_id,
            user_id=current_user.get("auth_id"),
            required_permission="owner",
            request_id=request_id
        )

    try:
        # Save responses using batch function
        result = await db_save_batch(
            responses=responses,
            user_id=current_user.get("auth_id"),
            book_id=book_id,
            chapter_id=chapter_id,
        )

        # Log batch save operation
        await audit_after_commit(
            request=None,
            current_user=current_user,
            action="save_question_responses_batch",
            resource_type="question_responses",
            target_id=chapter_id,
            metadata={
                "book_id": book_id,
                "chapter_id": chapter_id,
                "total": result["total"],
                "saved": result["saved"],
                "failed": result["failed"],
                "success": result["success"],
                "request_id": request_id,
            }
        )

        return {
            "success": result["success"],
            "total": result["total"],
            "saved": result["saved"],
            "failed": result["failed"],
            "results": result["results"],
            "errors": result.get("errors"),
            "message": f"Batch save completed: {result['saved']}/{result['total']} responses saved successfully",
            "request_id": request_id
        }

    except ValueError as e:
        # Handle validation errors from the database layer
        raise handle_validation_error(
            field="responses",
            message=str(e),
            value=None,
            request_id=request_id
        )
    except Exception as e:
        # Handle all other errors with centralized error handler
        raise handle_response_save_error(
            error=e,
            question_id=None,  # Batch operation, no single question
            user_id=current_user.get("auth_id"),
            request_id=request_id
        )
