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
