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
    BookCreate, BookUpdate, BookResponse, BookDetailResponse, 
    TocItemCreate, TocItemUpdate
)
from app.db.database import (
    create_book, get_book_by_id, get_books_by_user, 
    update_book, delete_book
)
from app.api.dependencies import (
    rate_limit, audit_request, sanitize_input, get_rate_limiter
)
from app.services.ai_service import ai_service
from bson import ObjectId

router = APIRouter()

# Role-based access controls
allow_users_and_admins = RoleChecker(["user", "admin"])


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
    current_user: Dict = Depends(get_current_user),
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
            user_clerk_id=current_user.get("clerk_id")
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
    current_user: Dict = Depends(get_current_user),
    rate_limit_info: Dict = Depends(get_rate_limiter(limit=20, window=60)),
):

    """Get all books for the current user"""
    try:
        books = await get_books_by_user(
            user_clerk_id=current_user.get("clerk_id"),
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
    current_user: Dict = Depends(get_current_user),
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
        if book.get("owner_id") != current_user.get("clerk_id"):
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
    current_user: Dict = Depends(get_current_user),
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
            user_clerk_id=current_user.get("clerk_id")
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
    current_user: Dict = Depends(get_current_user),
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
            user_clerk_id=current_user.get("clerk_id"),
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
    current_user: Dict = Depends(get_current_user),
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
        if book.get("owner_id") != current_user.get("clerk_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this book",
            )

        # Delete the book
        success = await delete_book(
            book_id=book_id,
            user_clerk_id=current_user.get("clerk_id")
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


@router.post("/{book_id}/cover-image", status_code=status.HTTP_202_ACCEPTED)
async def upload_book_cover_image(
    book_id: str,
    file: UploadFile = File(...),
    current_user: Dict = Depends(get_current_user),
    request: Request = None,
):
    """
    Upload a cover image for a book. (TODO: Connect to Cloudinary for actual upload)
    Accepts an image file and returns a placeholder URL or error.
    """
    # TODO: Validate book ownership and permissions
    # TODO: Validate file type and size
    # TODO: Upload to Cloudinary and return the URL
    # For now, just return a stub response
    return {
        "message": "Cover image upload endpoint is not yet implemented. TODO: Connect to Cloudinary.",
        "cover_image_url": None,
    }


@router.get("/{book_id}/summary", status_code=status.HTTP_200_OK)
async def get_book_summary(
    book_id: str,
    current_user: Dict = Depends(get_current_user),
):
    """
    Retrieve the summary and its revision history for a book.
    """
    print(">>> DEBUG summary: current_user", current_user, "book_id", book_id)
    book = await get_book_by_id(book_id)
    print(">>> DEBUG found book:", book)

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
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
    current_user: Dict = Depends(get_current_user),
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
    if book.get("owner_id") != current_user.get("clerk_id"):
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
    await update_book(book_id, update_data, current_user.get("clerk_id"))
    return {"summary": summary, "summary_history": summary_history[-20:]}


@router.patch("/{book_id}/summary", status_code=status.HTTP_200_OK)
async def patch_book_summary(
    book_id: str,
    data: dict = Body(...),
    current_user: Dict = Depends(get_current_user),
):
    """
    Partially update the summary for a book. Only updates the summary field if provided.
    Stores revision history and validates input.
    """
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
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
        await update_book(book_id, update_data, current_user.get("clerk_id"))
        return {"summary": summary, "summary_history": summary_history[-20:]}
    # If no summary provided, return current summary
    return {
        "summary": book.get("summary"),
        "summary_history": book.get("summary_history", []),
    }


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
    Saves user edits to the TOC structure.
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to update this book's TOC"
        )

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

    # Get current TOC to preserve metadata
    current_toc = book.get("table_of_contents", {})

    # Update TOC data
    updated_toc = {
        **toc_data,
        "generated_at": current_toc.get("generated_at"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "status": "edited",
        "version": current_toc.get("version", 1) + 1,
    }

    update_data = {
        "table_of_contents": updated_toc,
        "updated_at": datetime.now(timezone.utc),
    }
    await update_book(book_id, update_data, current_user.get("clerk_id"))

    return {
        "book_id": book_id,
        "toc": toc_data,
        "updated_at": updated_toc["updated_at"],
        "version": updated_toc["version"],
        "chapters_count": len(chapters),
        "success": True,
    }


# Individual Chapter CRUD Operations


@router.post(
    "/{book_id}/chapters", response_model=dict, status_code=status.HTTP_201_CREATED
)
async def create_chapter(
    book_id: str,
    chapter_data: TocItemCreate,
    current_user: Dict = Depends(get_current_user),
):
    """
    Create a new chapter in the book's TOC.
    Can be used to add a new chapter at any level (chapter or subchapter).
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to modify this book's chapters"
        )

    # Get current TOC
    current_toc = book.get("table_of_contents", {})
    chapters = current_toc.get("chapters", [])

    # Generate unique chapter ID
    import uuid

    chapter_id = str(uuid.uuid4())

    # Prepare new chapter data
    new_chapter = {
        "id": chapter_id,
        "title": chapter_data.title,
        "description": chapter_data.description or "",
        "level": chapter_data.level,
        "order": chapter_data.order,
        "subchapters": [],
    }

    # If this is a subchapter (level > 1), add it to the parent
    if chapter_data.level > 1 and chapter_data.parent_id:
        parent_found = False

        def add_to_parent(chapter_list):
            nonlocal parent_found
            for chapter in chapter_list:
                if chapter.get("id") == chapter_data.parent_id:
                    chapter.setdefault("subchapters", []).append(new_chapter)
                    parent_found = True
                    return True
                # Recursively check subchapters
                if chapter.get("subchapters"):
                    if add_to_parent(chapter["subchapters"]):
                        return True
            return False

        if not add_to_parent(chapters):
            raise HTTPException(status_code=400, detail="Parent chapter not found")

    else:
        # This is a top-level chapter
        chapters.append(new_chapter)

    # Update TOC data
    updated_toc = {
        **current_toc,
        "chapters": chapters,
        "total_chapters": len([ch for ch in chapters]),  # Count top-level chapters
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "status": "edited",
        "version": current_toc.get("version", 1) + 1,
    }

    # Save to database
    update_data = {
        "table_of_contents": updated_toc,
        "updated_at": datetime.now(timezone.utc),
    }
    await update_book(book_id, update_data, current_user.get("clerk_id"))

    return {
        "book_id": book_id,
        "chapter": new_chapter,
        "chapter_id": chapter_id,
        "success": True,
        "message": "Chapter created successfully",
    }


@router.get("/{book_id}/chapters/{chapter_id}", response_model=dict)
async def get_chapter(
    book_id: str,
    chapter_id: str,
    current_user: Dict = Depends(get_current_user),
):
    """
    Get a specific chapter by ID from the book's TOC.
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to access this book's chapters"
        )

    # Get TOC and find the chapter
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

    return {"book_id": book_id, "chapter": chapter, "success": True}


@router.put("/{book_id}/chapters/{chapter_id}", response_model=dict)
async def update_chapter(
    book_id: str,
    chapter_id: str,
    chapter_data: TocItemUpdate,
    current_user: Dict = Depends(get_current_user),
):
    """
    Update a specific chapter in the book's TOC.
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to modify this book's chapters"
        )

    # Get current TOC
    current_toc = book.get("table_of_contents", {})
    chapters = current_toc.get("chapters", [])

    def update_chapter_in_list(chapter_list):
        for i, chapter in enumerate(chapter_list):
            if chapter.get("id") == chapter_id:
                # Update the chapter with provided data
                if chapter_data.title is not None:
                    chapter["title"] = chapter_data.title
                if chapter_data.description is not None:
                    chapter["description"] = chapter_data.description
                if chapter_data.level is not None:
                    chapter["level"] = chapter_data.level
                if chapter_data.order is not None:
                    chapter["order"] = chapter_data.order
                if chapter_data.metadata is not None:
                    chapter["metadata"] = chapter_data.metadata
                return True
            # Recursively search subchapters
            if chapter.get("subchapters"):
                if update_chapter_in_list(chapter["subchapters"]):
                    return True
        return False

    if not update_chapter_in_list(chapters):
        raise HTTPException(status_code=404, detail="Chapter not found")

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
    await update_book(book_id, update_data, current_user.get("clerk_id"))

    return {
        "book_id": book_id,
        "chapter_id": chapter_id,
        "success": True,
        "message": "Chapter updated successfully",
    }


@router.delete("/{book_id}/chapters/{chapter_id}", response_model=dict)
async def delete_chapter(
    book_id: str,
    chapter_id: str,
    current_user: Dict = Depends(get_current_user),
):
    """
    Delete a specific chapter from the book's TOC.
    Note: Deleting a chapter will also delete all its subchapters.
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("clerk_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to modify this book's chapters"
        )

    # Get current TOC
    current_toc = book.get("table_of_contents", {})
    chapters = current_toc.get("chapters", [])

    def delete_chapter_from_list(chapter_list):
        for i, chapter in enumerate(chapter_list):
            if chapter.get("id") == chapter_id:
                # Remove the chapter
                deleted_chapter = chapter_list.pop(i)
                return deleted_chapter
            # Recursively search subchapters
            if chapter.get("subchapters"):
                deleted = delete_chapter_from_list(chapter["subchapters"])
                if deleted:
                    return deleted
        return None

    deleted_chapter = delete_chapter_from_list(chapters)
    if not deleted_chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    # Update TOC data
    updated_toc = {
        **current_toc,
        "chapters": chapters,
        "total_chapters": len([ch for ch in chapters]),  # Recount top-level chapters
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "status": "edited",
        "version": current_toc.get("version", 1) + 1,
    }

    # Save to database
    update_data = {
        "table_of_contents": updated_toc,
        "updated_at": datetime.now(timezone.utc),
    }
    await update_book(book_id, update_data, current_user.get("clerk_id"))

    return {
        "book_id": book_id,
        "deleted_chapter": deleted_chapter,
        "success": True,
        "message": "Chapter deleted successfully",
    }


@router.get("/{book_id}/chapters", response_model=dict)
async def list_chapters(
    book_id: str,
    current_user: Dict = Depends(get_current_user),
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
    if book.get("owner_id") != current_user.get("clerk_id"):
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
