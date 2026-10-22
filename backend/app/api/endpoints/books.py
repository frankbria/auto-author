import json
import logging
import uuid
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

# Error handling utilities
from app.utils.error_handlers import (
    ai_error_http_exception,
)

from app.core.security import get_current_user_from_session
from app.schemas.book import (
    BookCreate,
    BookUpdate,
    BookResponse,
    BookDetailResponse,
    MAX_TOC_BODY_BYTES,
)
from pymongo.errors import OperationFailure
from app.db.database import (
    create_book, get_book_by_id, get_book_fields, get_book_metadata_by_id,
    get_books_by_user,
    update_book, delete_book
)
from app.db.toc_transactions import (
    update_toc_with_transaction,
    _walk_toc,
)
from app.api.dependencies import (
    audit_after_commit, get_rate_limiter, get_ai_usage_quota,
    get_entitlement_checker
)
from pydantic import ValidationError
from app.schemas.ai_input import (
    GenerateTocRequest,
    SaveQuestionResponsesRequest,
)
from app.services.ai_service import ai_service
from app.services.ai_errors import (
    AIServiceError
)
from bson import ObjectId

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_new_book(
    book: BookCreate,
    request: Request,
    current_user: Dict = Depends(get_current_user_from_session),
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=10, window=60)),
):
    """Create a new book"""
    # Validate user has permission to create books
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    # Create book data dictionary
    book_data = book.model_dump()

    # Create the book in the database
    try:
        new_book = await create_book(
            book_data=book_data,
            user_auth_id=current_user.get("auth_id")
        )

        # Log the book creation
        await audit_after_commit(
            request=request,
            current_user=current_user,
            action="book_create",
            resource_type="book",
            target_id=str(new_book.get("_id")),
        )

        # Convert ObjectId to str for the response
        if "_id" in new_book:
            new_book["id"] = str(new_book["_id"])
        # Remove the raw ObjectId for JSON serialization
        new_book.pop("_id", None)

        if "created_at" not in new_book:
            new_book["created_at"] = datetime.now(timezone.utc)
        if "updated_at" not in new_book:
            new_book["updated_at"] = datetime.now(timezone.utc)

        return new_book

    except Exception:
        logger.error("Failed to create book", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create book",
        )


@router.get("/", response_model=List[BookResponse])
async def get_user_books(
    request: Request,
    # skip is capped as well as limit, matching the admin users route: Mongo walks
    # every skipped document, so an unbounded offset turns a cheap indexed query into
    # a full scan the caller controls. The dashboard now drives skip from its pager
    # (#493), which makes this a reachable input rather than a theoretical one.
    # 100k is ~4000 pages, far past any real library.
    skip: int = Query(0, ge=0, le=100_000),
    limit: int = Query(100, ge=1, le=100),
    current_user: Dict = Depends(get_current_user_from_session),
    # 60/min, not the 20 this route carried when a dashboard visit cost exactly one
    # GET. The pager (#493) makes every page click, delete refetch and focus-driven
    # session refresh its own request, so a user paging through a 21-page library
    # tripped the old budget just by browsing. Still bounded well below what a
    # scripted enumeration would want.
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=60, window=60)),
):

    """Get all books for the current user"""
    try:
        books = await get_books_by_user(
            user_auth_id=current_user.get("auth_id"),
            skip=skip,
            limit=limit
        )

        # Convert ObjectId to str for all books
        for book in books:
            if "_id" in book:
                book["id"] = str(book["_id"])

        return books

    except Exception:
        logger.error("Failed to retrieve books", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve books",
        )


@router.get("/{book_id}", response_model=BookDetailResponse)
async def get_book(
    book_id: str,
    request: Request,
    current_user: Dict = Depends(get_current_user_from_session),
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=20, window=60)),
):
    """Get a specific book by ID"""
    try:
        # Validate book_id format
        try:
            ObjectId(book_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid book ID format",
            )

        # Get the book from the database
        book = await get_book_metadata_by_id(book_id)

        # Check if book exists
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found",
            )

        # Check if user has access to this book
        if book.get("owner_id") != current_user.get("auth_id"):
            # Check for collaborator access later
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this book",
            )

        # Convert ObjectId to str
        if "_id" in book:
            book["id"] = str(book["_id"])

        return book

    except HTTPException:
        raise

    except Exception:
        logger.error("Failed to retrieve book", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve book",
        )


@router.put("/{book_id}", response_model=BookResponse)
async def update_book_details(
    book_id: str,
    book_update: BookUpdate,
    request: Request,
    current_user: Dict = Depends(get_current_user_from_session),
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=15, window=60)),
):
    """Update a book's details"""
    try:
        # Validate book_id format
        try:
            ObjectId(book_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid book ID format",
            )

        # Get only the fields that were provided
        update_data = {
            k: v for k, v in book_update.model_dump().items() if v is not None
        }

        # Add updated_at timestamp
        update_data["updated_at"] = datetime.now(timezone.utc)

        # Update the book
        updated_book = await update_book(
            book_id=book_id,
            book_data=update_data,
            user_auth_id=current_user.get("auth_id")
        )

        # Check if book was found and updated
        if not updated_book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found or you don't have permission to update it",
            )

        # Convert ObjectId to str
        if "_id" in updated_book:
            updated_book["id"] = str(updated_book["_id"])
            del updated_book["_id"]  # Remove raw ObjectId for JSON serialization

        # Log the book update
        await audit_after_commit(
            request=request,
            current_user=current_user,
            action="book_update",
            resource_type="book",
            target_id=book_id,
        )

        # Fetch the full book after update to ensure all fields are present
        full_book = await get_book_by_id(book_id)
        if not full_book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found after update",
            )
        if "_id" in full_book:
            full_book["id"] = str(full_book["_id"])
            del full_book["_id"]
        # Ensure required fields with defaults are present
        if "toc_items" not in full_book:
            full_book["toc_items"] = []
        if "published" not in full_book:
            full_book["published"] = False
        if "collaborators" not in full_book:
            full_book["collaborators"] = []

        try:
            return BookResponse.model_validate(full_book)
        except Exception:
            logger.error("BookResponse parse error", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to parse book response",
            )

    except HTTPException:
        raise

    except Exception:
        logger.error("Failed to update book", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update book",
        )


@router.patch("/{book_id}", response_model=BookResponse)
async def patch_book_details(
    book_id: str,
    book_update: BookUpdate,
    request: Request,
    current_user: Dict = Depends(get_current_user_from_session),
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=20, window=60)),
):
    """Partially update a book's details (PATCH)"""
    try:
        # Validate book_id format
        try:
            ObjectId(book_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid book ID format",
            )

        # Only the fields sent; a null among them clears that field (#848)
        update_data = book_update.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now(timezone.utc)

        updated_book = await update_book(
            book_id=book_id,
            book_data=update_data,
            user_auth_id=current_user.get("auth_id"),
        )

        if not updated_book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found or you don't have permission to update it",
            )

        if "_id" in updated_book:
            updated_book["id"] = str(updated_book["_id"])
            del updated_book["_id"]  # Remove raw ObjectId for JSON serialization

        await audit_after_commit(
            request=request,
            current_user=current_user,
            action="book_patch_update",
            resource_type="book",
            target_id=book_id,
        )

        # Fetch the full book after update to ensure all fields are present
        full_book = await get_book_by_id(book_id)
        if not full_book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found after update",
            )
        if "_id" in full_book:
            full_book["id"] = str(full_book["_id"])
            del full_book["_id"]
        # Ensure required fields with defaults are present
        if "toc_items" not in full_book:
            full_book["toc_items"] = []
        if "published" not in full_book:
            full_book["published"] = False
        if "collaborators" not in full_book:
            full_book["collaborators"] = []

        try:
            return BookResponse.model_validate(full_book)
        except Exception:
            logger.error("BookResponse parse error", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to parse book response",
            )

    except HTTPException:
        raise
    except Exception:
        logger.error("Failed to patch update book", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to patch update book",
        )


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book_endpoint(
    book_id: str,
    request: Request,
    current_user: Dict = Depends(get_current_user_from_session),
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=5, window=60)),
):
    """Delete a book"""
    try:
        # Validate book_id format
        try:
            ObjectId(book_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid book ID format",
            )

        # First get the book to log its details
        book = await get_book_fields(book_id, "owner_id")
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found",
            )

        # Check if user has permission to delete this book
        if book.get("owner_id") != current_user.get("auth_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this book",
            )

        # Delete the book
        success = await delete_book(
            book_id=book_id,
            user_auth_id=current_user.get("auth_id")
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete book",
            )

        # Log the book deletion
        await audit_after_commit(
            request=request,
            current_user=current_user,
            action="book_delete",
            resource_type="book",
            target_id=book_id,
        )

        return None

    except HTTPException:
        raise

    except Exception:
        logger.error("Failed to delete book", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete book",
        )


@router.post("/{book_id}/cover-image", status_code=status.HTTP_200_OK)
async def upload_book_cover_image(
    book_id: str,
    file: UploadFile = File(...),
    current_user: Dict = Depends(get_current_user_from_session),
    request: Request = None,
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=5, window=60)),
):
    """
    Upload a cover image for a book.
    Accepts an image file, processes it, and stores it in cloud storage (S3/Cloudinary) or local storage.
    """
    try:
        # Validate book ownership
        book = await get_book_fields(book_id, "owner_id", "cover_image_url", "cover_thumbnail_url")
        if not book or book.get("owner_id") != current_user.get("auth_id"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found"
            )
        # ObjectId() accepts uppercase hex; files are keyed by the canonical id.
        book_id = str(book["_id"])

        # Process and save the cover image
        from app.services.file_upload_service import FileUploadService
        file_upload_service = FileUploadService()
        image_url, thumbnail_url = await file_upload_service.process_and_save_cover_image(
            file,
            book_id
        )

        # Persist first; only remove the previous cover once the new URLs are
        # safely stored (#797). If persistence fails, clean up the just-saved
        # files so the book never points at a deleted image.
        update_data = {
            "cover_image_url": image_url,
            "cover_thumbnail_url": thumbnail_url,
            "updated_at": datetime.now(timezone.utc),
        }
        try:
            updated_book = await update_book(
                book_id, update_data, current_user.get("auth_id")
            )
        except Exception:
            await file_upload_service.delete_cover_image(
                book_id, image_url, thumbnail_url
            )
            raise
        if not updated_book:
            await file_upload_service.delete_cover_image(
                book_id, image_url, thumbnail_url
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found"
            )

        old_cover_url = book.get("cover_image_url")
        old_thumbnail_url = book.get("cover_thumbnail_url")
        if old_cover_url or old_thumbnail_url:
            await file_upload_service.delete_cover_image(
                book_id, old_cover_url, old_thumbnail_url
            )

        # Log the upload
        if request:
            await audit_after_commit(
                request=request,
                current_user=current_user,
                action="cover_image_upload",
                resource_type="book",
                target_id=book_id,
                metadata={
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "image_url": image_url,
                }
            )

        return {
            "message": "Cover image uploaded successfully",
            "cover_image_url": image_url,
            "cover_thumbnail_url": thumbnail_url,
            "book_id": book_id,
        }

    except HTTPException:
        raise
    except Exception:
        logger.error("Failed to upload cover image", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload cover image"
        )


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
