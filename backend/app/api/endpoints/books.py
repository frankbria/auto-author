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

# Error handling utilities
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
from app.schemas.errors import ErrorCode

from app.core.security import get_current_user_from_session, SessionRoleChecker
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
from app.services.ai_errors import (
    AIServiceError,
    AIRateLimitError,
    AINetworkError,
    AIServiceUnavailableError,
    AIInvalidRequestError
)
from app.services.chapter_access_service import chapter_access_service
from app.services.chapter_status_service import chapter_status_service
from app.services.question_generation_service import get_question_generation_service
from bson import ObjectId

router = APIRouter()

# Role-based access controls
allow_users_and_admins = SessionRoleChecker(["user", "admin"])


# Helper to load offensive words from JSON
OFFENSIVE_WORDS_PATH = os.path.join(
    os.path.dirname(__file__), "../../utils/offensive_words.json"
)
with open(OFFENSIVE_WORDS_PATH, encoding="utf-8") as f:
    OFFENSIVE_WORDS = json.load(f)


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
        await audit_request(
            request=request,
            current_user=current_user,
            action="book_create",
            resource_type="book",
            target_id=str(new_book.get("_id")),
            metadata={"title": book_data.get("title")}
        )

        # Convert ObjectId to str for the response
        if "_id" in new_book:
            new_book["id"] = str(new_book["_id"])
        print("->new_book", new_book)
        # Remove the raw ObjectId for JSON serialization
        new_book.pop("_id", None)

        if "created_at" not in new_book:
            new_book["created_at"] = datetime.now(timezone.utc)
        if "updated_at" not in new_book:
            new_book["updated_at"] = datetime.now(timezone.utc)

        return new_book

    except Exception as e:
        print("->create_book_error", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create book: {str(e)}",
        )


@router.get("/", response_model=List[BookResponse])
async def get_user_books(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: Dict = Depends(get_current_user_from_session),
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=20, window=60)),
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

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve books: {str(e)}",
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
        print("->get_book", book_id)

        # Get the book from the database
        book = await get_book_by_id(book_id)

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

        # Log the book view
        await audit_request(
            request=request,
            current_user=current_user,
            action="book_view",
            resource_type="book",
            target_id=book_id,
        )

        return book

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve book: {str(e)}",
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
        await audit_request(
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
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BookResponse parse error: {str(e)}",
            )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update book: {str(e)}",
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

        # Only include provided fields
        update_data = {
            k: v
            for k, v in book_update.model_dump(exclude_unset=True).items()
            if v is not None
        }
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

        await audit_request(
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
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"BookResponse parse error: {str(e)}",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to patch update book: {str(e)}",
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
        book = await get_book_by_id(book_id)
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
        await audit_request(
            request=request,
            current_user=current_user,
            action="book_delete",
            resource_type="book",
            target_id=book_id,
            metadata={"title": book.get("title", "Untitled")}
        )

        return None

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete book: {str(e)}",
        )


@router.post("/{book_id}/cover-image", status_code=status.HTTP_200_OK)
async def upload_book_cover_image(
    book_id: str,
    file: UploadFile = File(...),
    current_user: Dict = Depends(get_current_user_from_session),
    request: Request = None,
):
    """
    Upload a cover image for a book.
    Accepts an image file, processes it, and stores it in cloud storage (S3/Cloudinary) or local storage.
    """
    try:
        # Validate book ownership
        book = await get_book_by_id(book_id)
        if not book or book.get("owner_id") != current_user.get("auth_id"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found"
            )

        # Process and save the cover image
        from app.services.file_upload_service import FileUploadService
        file_upload_service = FileUploadService()
        image_url, thumbnail_url = await file_upload_service.process_and_save_cover_image(
            file,
            book_id
        )

        # Delete old cover images if they exist
        old_cover_url = book.get("cover_image_url")
        old_thumbnail_url = book.get("cover_thumbnail_url")
        if old_cover_url:
            await file_upload_service.delete_cover_image(
                old_cover_url,
                old_thumbnail_url
            )

        # Update book with new cover image URLs
        update_data = {
            "cover_image_url": image_url,
            "cover_thumbnail_url": thumbnail_url,
            "updated_at": datetime.now(timezone.utc),
        }
        await update_book(book_id, update_data, current_user.get("auth_id"))

        # Log the upload
        if request:
            await audit_request(
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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload cover image: {str(e)}"
        )


@router.get("/{book_id}/summary", status_code=status.HTTP_200_OK)
async def get_book_summary(
    book_id: str,
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    Retrieve the summary and its revision history for a book.
    """
    print(">>> DEBUG summary: current_user", current_user, "book_id", book_id)
    book = await get_book_by_id(book_id)
    print(">>> DEBUG found book:", book)

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
    print(">>> DEBUG summary: current_user", current_user, "book_id", book_id)
    book = await get_book_by_id(book_id)
    print(">>> DEBUG found book:", book)

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
        r"\\b(" + "|".join(map(re.escape, OFFENSIVE_WORDS)) + r")\\b", re.IGNORECASE
    )
    if pattern.search(summary):
        raise HTTPException(
            status_code=400, detail="Summary contains inappropriate language."
        )
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("auth_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to update this book"
        )
    # Store revision history
    summary_history = book.get("summary_history", [])
    if book.get("summary") and book["summary"] != summary:
        summary_history.append(
            {
                "summary": book["summary"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    update_data = {
        "summary": summary,
        "summary_history": summary_history[-20:],  # Keep last 20 revisions
        "updated_at": datetime.now(timezone.utc),
    }
    await update_book(book_id, update_data, current_user.get("auth_id"))
    return {"summary": summary, "summary_history": summary_history[-20:]}


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
    book = await get_book_by_id(book_id)
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
        # Store revision history if changed
        summary_history = book.get("summary_history", [])
        if book.get("summary") and book["summary"] != summary:
            summary_history.append(
                {
                    "summary": book["summary"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
        update_data = {
            "summary": summary,
            "summary_history": summary_history[-20:],
            "updated_at": datetime.now(timezone.utc),
        }
        await update_book(book_id, update_data, current_user.get("auth_id"))
        return {"summary": summary, "summary_history": summary_history[-20:]}
    # If no summary provided, return current summary
    return {
        "summary": book.get("summary"),
        "summary_history": book.get("summary_history", []),
    }


@router.post("/{book_id}/analyze-summary", status_code=status.HTTP_200_OK)
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
    book = await get_book_by_id(book_id)
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

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error analyzing summary: {str(e)}"
        )


@router.post("/{book_id}/generate-questions", status_code=status.HTTP_200_OK)
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
    book = await get_book_by_id(book_id)
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

    except AIRateLimitError as e:
        # Rate limit error - return 429 with retry information
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": e.message,
                "error_code": e.error_code,
                "retry_after": e.retry_after,
                "cached_content_available": e.cached_content_available,
                "correlation_id": e.correlation_id
            }
        )
    except AIServiceUnavailableError as e:
        # Service unavailable - return 503
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": e.message,
                "error_code": e.error_code,
                "retry_after": e.retry_after,
                "cached_content_available": e.cached_content_available,
                "correlation_id": e.correlation_id
            }
        )
    except AINetworkError as e:
        # Network error - return 503
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": e.message,
                "error_code": e.error_code,
                "retryable": e.retryable,
                "correlation_id": e.correlation_id
            }
        )
    except AIInvalidRequestError as e:
        # Invalid request - return 400
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": e.message,
                "error_code": e.error_code,
                "correlation_id": e.correlation_id
            }
        )
    except AIServiceError as e:
        # Generic AI service error - return 500 with structured info
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": e.message,
                "error_code": e.error_code,
                "retryable": e.retryable,
                "correlation_id": e.correlation_id
            }
        )
    except Exception as e:
        # Unexpected error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error generating questions: {str(e)}"
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
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("auth_id"):
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
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    Save user responses to clarifying questions for TOC generation.
    Stores responses that will be used to generate the table of contents.
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("auth_id"):
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
    await update_book(book_id, update_data, current_user.get("auth_id"))

    return {
        "book_id": book_id,
        "responses_saved": len(responses),
        "answered_at": responses_data["answered_at"],
        "ready_for_toc_generation": True,
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
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("auth_id"):
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
        await update_book(book_id, update_data, current_user.get("auth_id"))

        return {
            "book_id": book_id,
            "toc": toc_result["toc"],
            "generated_at": toc_data["generated_at"],
            "chapters_count": toc_result["chapters_count"],
            "has_subchapters": toc_result["has_subchapters"],
            "success": toc_result["success"],
        }

    except AIRateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": e.message,
                "error_code": e.error_code,
                "retry_after": e.retry_after,
                "cached_content_available": e.cached_content_available,
                "correlation_id": e.correlation_id
            }
        )
    except AIServiceUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": e.message,
                "error_code": e.error_code,
                "retry_after": e.retry_after,
                "cached_content_available": e.cached_content_available,
                "correlation_id": e.correlation_id
            }
        )
    except AINetworkError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": e.message,
                "error_code": e.error_code,
                "retryable": e.retryable,
                "correlation_id": e.correlation_id
            }
        )
    except AIInvalidRequestError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": e.message,
                "error_code": e.error_code,
                "correlation_id": e.correlation_id
            }
        )
    except AIServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": e.message,
                "error_code": e.error_code,
                "retryable": e.retryable,
                "correlation_id": e.correlation_id
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error generating TOC: {str(e)}"
        )


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
    book = await get_book_by_id(book_id)
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
    current_user: Dict = Depends(get_current_user_from_session),
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
        logger.info(f"Updating TOC for book_id={book_id}, user_auth_id={current_user.get('auth_id')}")

        # Update TOC with transaction
        updated_toc = await update_toc_with_transaction(
            book_id=book_id,
            toc_data=toc_data,
            user_auth_id=current_user.get("auth_id")
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


@router.post(
    "/{book_id}/chapters", response_model=dict, status_code=status.HTTP_201_CREATED
)
async def create_chapter(
    book_id: str,
    chapter_data: TocItemCreate,
    current_user: Dict = Depends(get_current_user_from_session),
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
            parent_id=chapter_data.parent_id if chapter_data.level > 1 else None,
            user_auth_id=current_user.get("auth_id")
        )

        # Log chapter creation
        await chapter_access_service.log_access(
            user_id=current_user.get("auth_id"),
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
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    Get a specific chapter by ID from the book's TOC.
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("auth_id"):
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
        user_id=current_user.get("auth_id"),
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
    current_user: Dict = Depends(get_current_user_from_session),
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
            updates=updates,
            user_auth_id=current_user.get("auth_id")
        )

        # Log chapter update
        await chapter_access_service.log_access(
            user_id=current_user.get("auth_id"),
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
    current_user: Dict = Depends(get_current_user_from_session),
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
            user_auth_id=current_user.get("auth_id")
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
    current_user: Dict = Depends(get_current_user_from_session),
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
    if book.get("owner_id") != current_user.get("auth_id"):
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
    current_user: Dict = Depends(get_current_user_from_session),
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
    if book.get("owner_id") != current_user.get("auth_id"):
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
        current_user.get("auth_id"), book_id, limit=1
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
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    Update status for multiple chapters simultaneously.
    Useful for tab operations like "Mark selected as completed".
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("auth_id"):
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
    await update_book(book_id, update_book_data, current_user.get("auth_id"))

    # Log the bulk status change
    for chapter_id in updated_chapters:
        await chapter_access_service.log_access(
            user_id=current_user.get("auth_id"),
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
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    Save current tab state for persistence across sessions.
    """
    # Verify book ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("auth_id"):
        print(
            f"User {current_user.get('auth_id')} is not authorized to access book {book_id}"
        )
        raise HTTPException(
            status_code=403, detail="Not authorized to access this book"
        )

    # Save tab state via access logging service
    log_id = await chapter_access_service.save_tab_state(
        user_id=current_user.get("auth_id"),
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
async def get_tab_state(book_id: str, current_user: Dict = Depends(get_current_user_from_session)):
    """
    Retrieve saved tab state for restoration.
    """
    # Verify book ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("auth_id"):
        print(
            f"User {current_user.get('auth_id')} is not authorized to access book {book_id}"
        )
        raise HTTPException(
            status_code=403, detail="Not authorized to access this book"
        )

    # Get latest tab state
    tab_state = await chapter_access_service.get_user_tab_state(
        current_user.get("auth_id"), book_id
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
    current_user: Dict = Depends(get_current_user_from_session),
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
    current_user: Dict = Depends(get_current_user_from_session),
):
    """
    Update chapter content with automatic metadata updates.
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("auth_id"):
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
            user_id=current_user.get("auth_id"),
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
    await update_book(book_id, update_data, current_user.get("auth_id"))

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
    current_user: Dict = Depends(get_current_user_from_session),
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
    if book.get("owner_id") != current_user.get("auth_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to access this book's analytics"
        )

    try:
        # Get chapter analytics
        analytics = await chapter_access_service.get_chapter_analytics(
            user_id=current_user.get("auth_id"),
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
    book = await get_book_by_id(book_id)
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

@router.post("/{book_id}/chapters/{chapter_id}/generate-questions", response_model=GenerateQuestionsResponse)
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
    book = await get_book_by_id(book_id)
    if not book:
        raise handle_book_not_found(book_id, request_id)

    if book.get("owner_id") != current_user.get("auth_id"):
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
    book = await get_book_by_id(book_id)
    if not book:
        raise handle_book_not_found(book_id, request_id)

    if book.get("owner_id") != current_user.get("auth_id"):
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
    book = await get_book_by_id(book_id)
    if not book:
        raise handle_book_not_found(book_id, request_id)

    if book.get("owner_id") != current_user.get("auth_id"):
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
    book = await get_book_by_id(book_id)
    if not book:
        raise handle_book_not_found(book_id, request_id)

    if book.get("owner_id") != current_user.get("auth_id"):
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
        - QUESTION_NOT_FOUND (404): Question does not exist
        - FORBIDDEN_OPERATION (403): User is not the book owner
        - VALIDATION_FAILED (422): Invalid rating value
        - RATING_SAVE_FAILED (500): Error saving rating
    """
    request_id = generate_request_id()

    # Validate rating value
    if rating_data.rating < 1 or rating_data.rating > 5:
        raise handle_validation_error(
            field="rating",
            message="Rating must be between 1 and 5",
            value=rating_data.rating,
            request_id=request_id
        )

    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise handle_book_not_found(book_id, request_id)

    if book.get("owner_id") != current_user.get("auth_id"):
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
    book = await get_book_by_id(book_id)
    if not book:
        raise handle_book_not_found(book_id, request_id)

    if book.get("owner_id") != current_user.get("auth_id"):
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
    response_model=GenerateQuestionsResponse
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
    book = await get_book_by_id(book_id)
    if not book:
        raise handle_book_not_found(book_id, request_id)

    if book.get("owner_id") != current_user.get("auth_id"):
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


@router.post("/{book_id}/chapters/{chapter_id}/generate-draft", response_model=dict)
async def generate_chapter_draft(
    book_id: str,
    chapter_id: str,
    data: dict = Body(default={}),
    current_user: Dict = Depends(get_current_user_from_session),
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
    if book.get("owner_id") != current_user.get("auth_id"):
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

    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise handle_book_not_found(book_id, request_id)

    if book.get("owner_id") != current_user.get("auth_id"):
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
            user_id=current_user.get("auth_id")
        )

        # Log batch save operation
        await audit_request(
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
