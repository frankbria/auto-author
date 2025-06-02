"""
File upload service for handling book cover images and other file uploads.
Currently uses local storage, but designed to be easily extended for cloud storage (S3, Cloudinary, etc.)
"""

import os
import uuid
import shutil
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
from fastapi import UploadFile, HTTPException, status

# Configuration
UPLOAD_DIR = Path("uploads")
COVER_IMAGES_DIR = UPLOAD_DIR / "cover_images"
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png", 
    "image/webp",
    "image/gif"
}

# Image processing settings
MAX_IMAGE_WIDTH = 1200
MAX_IMAGE_HEIGHT = 1800
THUMBNAIL_SIZE = (300, 450)


class FileUploadService:
    """Service for handling file uploads with validation and storage."""
    
    def __init__(self):
        """Initialize the upload service and ensure directories exist."""
        COVER_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    
    async def validate_image_upload(
        self, 
        file: UploadFile
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate an uploaded image file.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_IMAGE_EXTENSIONS:
            return False, f"Invalid file type. Allowed types: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
        
        # Check MIME type
        if file.content_type not in ALLOWED_MIME_TYPES:
            return False, f"Invalid content type. Allowed types: {', '.join(ALLOWED_MIME_TYPES)}"
        
        # Check file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        if file_size > MAX_FILE_SIZE:
            return False, f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        
        # Validate it's actually an image
        try:
            file.file.seek(0)
            image = Image.open(file.file)
            image.verify()
            file.file.seek(0)  # Reset after verify
        except Exception:
            return False, "Invalid image file"
        
        return True, None
    
    async def process_and_save_cover_image(
        self,
        file: UploadFile,
        book_id: str
    ) -> Tuple[str, str]:
        """
        Process and save a cover image for a book.
        
        Returns:
            Tuple of (image_url, thumbnail_url)
        """
        # Validate the upload
        is_valid, error_msg = await self.validate_image_upload(file)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Generate unique filename
        file_ext = Path(file.filename).suffix.lower()
        unique_filename = f"{book_id}_{uuid.uuid4().hex}{file_ext}"
        thumbnail_filename = f"{book_id}_{uuid.uuid4().hex}_thumb{file_ext}"
        
        # Paths for saving
        image_path = COVER_IMAGES_DIR / unique_filename
        thumbnail_path = COVER_IMAGES_DIR / thumbnail_filename
        
        try:
            # Save and process the main image
            file.file.seek(0)
            image = Image.open(file.file)
            
            # Convert RGBA to RGB if necessary (for JPEG)
            if image.mode in ('RGBA', 'LA', 'P'):
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = rgb_image
            
            # Resize if too large
            if image.width > MAX_IMAGE_WIDTH or image.height > MAX_IMAGE_HEIGHT:
                image.thumbnail((MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT), Image.Resampling.LANCZOS)
            
            # Save main image
            image.save(image_path, quality=85, optimize=True)
            
            # Create and save thumbnail
            thumbnail = image.copy()
            thumbnail.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
            thumbnail.save(thumbnail_path, quality=85, optimize=True)
            
            # Return URLs (in production, these would be CDN URLs)
            # For now, return relative paths that can be served by FastAPI
            image_url = f"/uploads/cover_images/{unique_filename}"
            thumbnail_url = f"/uploads/cover_images/{thumbnail_filename}"
            
            return image_url, thumbnail_url
            
        except Exception as e:
            # Clean up any partially saved files
            if image_path.exists():
                image_path.unlink()
            if thumbnail_path.exists():
                thumbnail_path.unlink()
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process image: {str(e)}"
            )
    
    async def delete_cover_image(self, image_url: str, thumbnail_url: Optional[str] = None):
        """Delete a cover image and its thumbnail."""
        try:
            # Extract filename from URL
            if image_url.startswith("/uploads/cover_images/"):
                filename = image_url.replace("/uploads/cover_images/", "")
                image_path = COVER_IMAGES_DIR / filename
                if image_path.exists():
                    image_path.unlink()
            
            if thumbnail_url and thumbnail_url.startswith("/uploads/cover_images/"):
                thumb_filename = thumbnail_url.replace("/uploads/cover_images/", "")
                thumb_path = COVER_IMAGES_DIR / thumb_filename
                if thumb_path.exists():
                    thumb_path.unlink()
                    
        except Exception as e:
            # Log error but don't fail the operation
            print(f"Error deleting image files: {e}")
    
    def get_upload_stats(self) -> dict:
        """Get statistics about uploaded files."""
        total_files = 0
        total_size = 0
        
        if COVER_IMAGES_DIR.exists():
            for file_path in COVER_IMAGES_DIR.iterdir():
                if file_path.is_file():
                    total_files += 1
                    total_size += file_path.stat().st_size
        
        return {
            "total_files": total_files,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "upload_directory": str(UPLOAD_DIR.absolute())
        }


# Create a singleton instance
file_upload_service = FileUploadService()
