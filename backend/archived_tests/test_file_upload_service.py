"""
Test script for the file upload service functionality.
This script tests the image validation and processing capabilities.
"""

import asyncio
import os
from pathlib import Path
from PIL import Image
import io
from fastapi import UploadFile

# Add the app directory to the Python path
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.file_upload_service import file_upload_service


async def create_test_image(filename: str, size: tuple = (800, 600), format: str = "PNG") -> UploadFile:
    """Create a test image file for upload testing."""
    # Create a test image
    image = Image.new('RGB', size, color='red')
    
    # Save to bytes
    img_bytes = io.BytesIO()
    image.save(img_bytes, format=format)
    img_bytes.seek(0)
    
    # Create UploadFile object
    content_type = f"image/{format.lower()}"
    return UploadFile(
        filename=filename,
        file=img_bytes,
        content_type=content_type
    )


async def test_file_upload_service():
    """Test the file upload service functionality."""
    print("Testing File Upload Service...")
    print("-" * 50)
    
    # Test 1: Valid image upload
    print("\n1. Testing valid image upload:")
    try:
        valid_image = await create_test_image("test_cover.png", (1000, 1500), "PNG")
        is_valid, error_msg = await file_upload_service.validate_image_upload(valid_image)
        print(f"   Validation result: {is_valid}")
        print(f"   Error message: {error_msg}")
        assert is_valid == True
        print("   ✅ Valid image test passed")
    except Exception as e:
        print(f"   ❌ Valid image test failed: {e}")
    
    # Test 2: Invalid file type
    print("\n2. Testing invalid file type:")
    try:
        invalid_file = UploadFile(
            filename="test.txt",
            file=io.BytesIO(b"This is not an image"),
            content_type="text/plain"
        )
        is_valid, error_msg = await file_upload_service.validate_image_upload(invalid_file)
        print(f"   Validation result: {is_valid}")
        print(f"   Error message: {error_msg}")
        assert is_valid == False
        assert "Invalid file type" in error_msg
        print("   ✅ Invalid file type test passed")
    except Exception as e:
        print(f"   ❌ Invalid file type test failed: {e}")
    
    # Test 3: File too large
    print("\n3. Testing file size validation:")
    try:
        # Create a large fake file
        large_file = UploadFile(
            filename="large.jpg",
            file=io.BytesIO(b"x" * (6 * 1024 * 1024)),  # 6MB
            content_type="image/jpeg"
        )
        is_valid, error_msg = await file_upload_service.validate_image_upload(large_file)
        print(f"   Validation result: {is_valid}")
        print(f"   Error message: {error_msg}")
        assert is_valid == False
        assert "too large" in error_msg
        print("   ✅ File size test passed")
    except Exception as e:
        print(f"   ❌ File size test failed: {e}")
    
    # Test 4: Process and save image
    print("\n4. Testing image processing and saving:")
    try:
        test_image = await create_test_image("book_cover.jpg", (1200, 1800), "JPEG")
        image_url, thumb_url = await file_upload_service.process_and_save_cover_image(
            file=test_image,
            book_id="test_book_123"
        )
        print(f"   Image URL: {image_url}")
        print(f"   Thumbnail URL: {thumb_url}")
        
        # Check if files were created
        upload_dir = Path("uploads/cover_images")
        image_filename = image_url.split("/")[-1]
        thumb_filename = thumb_url.split("/")[-1]
        
        image_path = upload_dir / image_filename
        thumb_path = upload_dir / thumb_filename
        
        assert image_path.exists(), "Main image file not created"
        assert thumb_path.exists(), "Thumbnail file not created"
        
        # Check thumbnail size
        with Image.open(thumb_path) as img:
            print(f"   Thumbnail size: {img.size}")
            assert img.width <= 300 and img.height <= 450
        
        # Clean up test files
        image_path.unlink()
        thumb_path.unlink()
        
        print("   ✅ Image processing test passed")
    except Exception as e:
        print(f"   ❌ Image processing test failed: {e}")
    
    # Test 5: Get upload statistics
    print("\n5. Testing upload statistics:")
    try:
        stats = file_upload_service.get_upload_stats()
        print(f"   Total files: {stats['total_files']}")
        print(f"   Total size: {stats['total_size_mb']} MB")
        print(f"   Upload directory: {stats['upload_directory']}")
        print("   ✅ Statistics test passed")
    except Exception as e:
        print(f"   ❌ Statistics test failed: {e}")
    
    print("\n" + "-" * 50)
    print("File Upload Service Testing Complete!")


if __name__ == "__main__":
    asyncio.run(test_file_upload_service())
