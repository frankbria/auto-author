import logging
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Request,
    UploadFile,
    File,
)
from typing import Dict
from datetime import datetime, timezone

from app.core.security import get_current_user_from_session
from app.db.database import get_book_fields, update_book
from app.api.dependencies import audit_after_commit, get_rate_limiter

logger = logging.getLogger(__name__)

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
