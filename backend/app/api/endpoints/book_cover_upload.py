"""
Cover image upload endpoint implementation.
This is a temporary file to implement the cover upload functionality.
The content will be integrated into books.py.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from typing import Dict
from datetime import datetime, timezone

from app.core.security import get_current_user_from_session
from app.db.database import get_book_by_id, update_book
from app.api.dependencies import get_rate_limiter, audit_request
from app.services.file_upload_service import file_upload_service

router = APIRouter()


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

    Accepts image files (JPEG, PNG, WebP, GIF) up to 5MB.
    Returns URLs for the uploaded image and thumbnail.
    """
    # Get the book and verify ownership
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.get("owner_id") != current_user.get("auth_id"):
        raise HTTPException(
            status_code=403, detail="Not authorized to upload cover image for this book"
        )

    try:
        # Process and save the cover image
        image_url, thumbnail_url = await file_upload_service.process_and_save_cover_image(
            file=file,
            book_id=book_id
        )

        # Delete old cover image if exists
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
