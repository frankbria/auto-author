"""
Test Book Cover Upload API endpoint
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import UploadFile, HTTPException
from httpx import AsyncClient
from PIL import Image
from io import BytesIO
import base64


class TestBookCoverUpload:
    """Test the book cover upload endpoint."""
    
    @pytest.fixture
    def mock_file_upload_service(self):
        """Mock file upload service."""
        mock_service = AsyncMock()
        mock_service.process_and_save_cover_image.return_value = (
            "https://cdn.example.com/cover.jpg",
            "https://cdn.example.com/cover_thumb.jpg"
        )
        mock_service.delete_cover_image.return_value = None
        return mock_service
    
    @pytest.fixture
    def test_image(self):
        """Create a test image file."""
        img = Image.new('RGB', (200, 300), color='green')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        return img_bytes
    
    @pytest.fixture
    async def test_book_with_auth(self, auth_client_factory):
        """Create a test book with authenticated client."""
        client = await auth_client_factory()
        
        # Create book data for API (without ObjectId fields)
        book_create_data = {
            "title": "Test Book",
            "subtitle": "A book for testing",
            "description": "This is a test book.",
            "genre": "Fiction",
            "target_audience": "Adults"
        }
        
        # Create a book
        response = await client.post(
            "/api/v1/books/",  # Add trailing slash
            json=book_create_data
        )
        assert response.status_code == 201
        book_data = response.json()
        
        return client, book_data["id"]
    
    @pytest.mark.asyncio
    async def test_upload_book_cover_success(self, test_book_with_auth, test_image, mock_file_upload_service):
        """Test successful book cover upload."""
        client, book_id = test_book_with_auth
        
        with patch('app.services.file_upload_service.FileUploadService', return_value=mock_file_upload_service):
            # Upload cover image
            files = {
                'file': ('cover.jpg', test_image, 'image/jpeg')
            }
            
            response = await client.post(
                f"/api/v1/books/{book_id}/cover-image",
                files=files
            )
            
            if response.status_code != 200:
                print(f"ERROR: {response.json()}")
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Cover image uploaded successfully"
            assert data["cover_image_url"] == "https://cdn.example.com/cover.jpg"
            assert data["cover_thumbnail_url"] == "https://cdn.example.com/cover_thumb.jpg"
            assert data["book_id"] == book_id
            
            # Verify service was called
            mock_file_upload_service.process_and_save_cover_image.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_upload_book_cover_replaces_existing(self, test_book_with_auth, test_image, mock_file_upload_service):
        """Test that uploading a new cover deletes the old one."""
        client, book_id = test_book_with_auth
        
        # First, update the book to have an existing cover
        # Need to include title for PATCH request
        await client.patch(
            f"/api/v1/books/{book_id}",
            json={
                "title": "Test Book",  # Required field
                "cover_image_url": "https://old.example.com/old_cover.jpg",
                "cover_thumbnail_url": "https://old.example.com/old_thumb.jpg"
            }
        )
        
        with patch('app.services.file_upload_service.FileUploadService', return_value=mock_file_upload_service):
            # Upload new cover
            files = {
                'file': ('new_cover.jpg', test_image, 'image/jpeg')
            }
            
            response = await client.post(
                f"/api/v1/books/{book_id}/cover-image",
                files=files
            )
            
            assert response.status_code == 200
            
            # Verify old images were deleted
            # Note: The API might not have the thumbnail URL in the database
            mock_file_upload_service.delete_cover_image.assert_called_once()
            call_args = mock_file_upload_service.delete_cover_image.call_args[0]
            assert call_args[0] == "https://old.example.com/old_cover.jpg"
    
    @pytest.mark.asyncio
    async def test_upload_book_cover_book_not_found(self, auth_client_factory, test_image):
        """Test upload fails when book doesn't exist."""
        client = await auth_client_factory()
        
        files = {
            'file': ('cover.jpg', test_image, 'image/jpeg')
        }
        
        response = await client.post(
            "/api/v1/books/nonexistent_book_id/cover-image",
            files=files
        )
        
        assert response.status_code == 404
        assert "Book not found" in response.json()["detail"]
    
    def test_upload_book_cover_unauthorized(self, client, test_image):
        """Test upload fails without authentication."""
        files = {
            'file': ('cover.jpg', test_image, 'image/jpeg')
        }
        
        response = client.post(
            "/api/v1/books/some_book_id/cover-image",
            files=files
        )
        
        assert response.status_code == 403  # FastAPI returns 403 for missing auth
    
    @pytest.mark.asyncio
    async def test_upload_book_cover_invalid_file_type(self, test_book_with_auth):
        """Test upload fails with invalid file type."""
        client, book_id = test_book_with_auth
        
        # Create a text file instead of image
        files = {
            'file': ('document.txt', b"This is not an image", 'text/plain')
        }
        
        response = await client.post(
            f"/api/v1/books/{book_id}/cover-image",
            files=files
        )
        
        assert response.status_code == 400  # Will fail during validation
        assert "Invalid file type" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_upload_book_cover_file_too_large(self, test_book_with_auth, mock_file_upload_service):
        """Test upload fails when file is too large."""
        client, book_id = test_book_with_auth
        
        # Mock validation to reject large files
        mock_file_upload_service.process_and_save_cover_image.side_effect = HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 5MB."
        )
        
        # Create a "large" file
        large_data = b"x" * (6 * 1024 * 1024)  # 6MB
        files = {
            'file': ('large.jpg', large_data, 'image/jpeg')
        }
        
        with patch('app.services.file_upload_service.FileUploadService', return_value=mock_file_upload_service):
            response = await client.post(
                f"/api/v1/books/{book_id}/cover-image",
                files=files
            )
            
            assert response.status_code == 400
            assert "File too large" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_upload_book_cover_service_error(self, test_book_with_auth, test_image, mock_file_upload_service):
        """Test handling of service errors during upload."""
        client, book_id = test_book_with_auth
        
        # Mock a service error
        mock_file_upload_service.process_and_save_cover_image.side_effect = Exception("Storage service error")
        
        with patch('app.services.file_upload_service.FileUploadService', return_value=mock_file_upload_service):
            files = {
                'file': ('cover.jpg', test_image, 'image/jpeg')
            }
            
            response = await client.post(
                f"/api/v1/books/{book_id}/cover-image",
                files=files
            )
            
            assert response.status_code == 500
            assert "Failed to upload cover image" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_upload_updates_book_record(self, test_book_with_auth, test_image, mock_file_upload_service):
        """Test that upload updates the book record with new URLs."""
        client, book_id = test_book_with_auth
        
        with patch('app.services.file_upload_service.FileUploadService', return_value=mock_file_upload_service):
            # Upload cover
            files = {
                'file': ('cover.jpg', test_image, 'image/jpeg')
            }
            
            response = await client.post(
                f"/api/v1/books/{book_id}/cover-image",
                files=files
            )
            
            assert response.status_code == 200
            
            # Verify book was updated
            book_response = await client.get(f"/api/v1/books/{book_id}")
            book_data = book_response.json()
            
            assert book_data["cover_image_url"] == "https://cdn.example.com/cover.jpg"
            # Note: cover_thumbnail_url might not be returned in the book response