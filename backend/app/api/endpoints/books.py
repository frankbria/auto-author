import logging
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Request,
    Query,
)
from typing import List, Dict
from datetime import datetime, timezone

# Error handling utilities

from app.core.security import get_current_user_from_session
from app.schemas.book import (
    BookCreate,
    BookUpdate,
    BookResponse,
    BookDetailResponse,
)
from app.db.database import (
    create_book, get_book_by_id, get_book_fields, get_book_metadata_by_id,
    get_books_by_user,
    update_book, delete_book
)
from app.api.dependencies import (
    audit_after_commit, get_rate_limiter
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
