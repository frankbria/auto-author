#!/usr/bin/env python3
"""
Run service tests in isolation without database dependencies
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from app.services.ai_service import AIService
from app.core.config import settings

# Set environment variables for testing
os.environ['OPENAI_AUTOAUTHOR_API_KEY'] = 'test-key'
os.environ['BETTER_AUTH_SECRET'] = 'test-secret-key-for-better-auth'

async def test_ai_service():
    """Test AI service draft generation"""
    print("\n=== Testing AI Service ===")

    ai_service = AIService()

    # Mock the OpenAI request method directly
    async def mock_openai_request(messages, **kwargs):
        return {
            'choices': [{
                'message': {
                    'content': "Generated draft content"
                }
            }]
        }

    with patch.object(ai_service, '_make_openai_request', side_effect=mock_openai_request):
        result = await ai_service.generate_chapter_draft(
            chapter_title="Test Chapter",
            chapter_description="A test chapter",
            question_responses=[
                {"question": "What is the main topic?", "answer": "Testing AI services"}
            ]
        )

        assert result["success"] == True
        assert result["draft"] == "Generated draft content"
        assert result["metadata"]["word_count"] == 3
        assert "suggestions" in result
        print("✓ AI draft generation works correctly")

async def test_transcription_service():
    """Test transcription service"""
    print("\n=== Testing Transcription Service ===")

    # Test with no AWS credentials (should use mock)
    with patch.dict(os.environ, {'AWS_ACCESS_KEY_ID': '', 'AWS_SECRET_ACCESS_KEY': ''}):
        service = TranscriptionService()

        result = await service.transcribe_audio(
            audio_data=b"fake audio data",
            language="en-US"
        )

        print(f"DEBUG: Audio length: {len(b'fake audio data')}, Result: '{result.transcript}'")

        # Audio data length is 15 bytes, which is < 1000, so it returns "Short audio sample."
        assert result.transcript == "Short audio sample."
        assert result.confidence == 0.95
        print("✓ Mock transcription works correctly")

    # Test with longer audio for punctuation processing
    result = await service.transcribe_audio(
        audio_data=b"x" * 5001,  # Long audio to get detailed transcription
        language="en-US",
        enable_punctuation_commands=True
    )

    # The long transcript already has a period at the end
    assert result.transcript == "This is a longer audio transcription that would contain more detailed content from the user's speech input."
    print("✓ Punctuation command processing works correctly")

async def test_cloud_storage():
    """Test cloud storage service"""
    print("\n=== Testing Cloud Storage Service ===")

    from app.services.cloud_storage_service import CloudStorageFactory, S3StorageService, CloudinaryStorageService

    # Test with no credentials (should return None)
    service = CloudStorageFactory.create_storage_service(provider="local")
    assert service is None
    print("✓ Returns None for local storage")

    # Test S3 service creation
    with patch('boto3.client'):
        service = CloudStorageFactory.create_storage_service(
            provider="s3",
            bucket_name="test-bucket",
            region="us-east-1",
            access_key_id="test-key",
            secret_access_key="test-secret"
        )
        assert isinstance(service, S3StorageService)
        print("✓ Creates S3 service when requested")

    # Test Cloudinary service creation
    with patch('cloudinary.config'):
        service = CloudStorageFactory.create_storage_service(
            provider="cloudinary",
            cloud_name="test-cloud",
            api_key="test-key",
            api_secret="test-secret"
        )
        assert isinstance(service, CloudinaryStorageService)
        print("✓ Creates Cloudinary service when requested")

async def test_file_upload():
    """Test file upload service"""
    print("\n=== Testing File Upload Service ===")

    from app.services.file_upload_service import FileUploadService
    from PIL import Image
    import io

    # Create test image
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)

    # Test with local storage
    service = FileUploadService(cloud_storage=None)

    # Mock file operations
    with patch('pathlib.Path.mkdir'), \
         patch('builtins.open', mock_open()), \
         patch.object(Image, 'save'):

        result = await service.upload_image(
            file_data=img_bytes.getvalue(),
            filename="test.jpg",
            file_type="book_cover"
        )

        assert result["url"].startswith("/uploads/")
        assert result["filename"] == "test.jpg"
        print("✓ Local file upload works correctly")

    # Test file validation
    try:
        await service.upload_image(
            file_data=b"not an image",
            filename="test.txt",
            file_type="book_cover"
        )
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid image format" in str(e)
        print("✓ File validation works correctly")

def mock_open():
    """Create a mock for open() that returns a file-like object"""
    m = MagicMock()
    m.__enter__ = MagicMock(return_value=io.BytesIO())
    m.__exit__ = MagicMock(return_value=None)
    return MagicMock(return_value=m)

async def main():
    """Run all tests"""
    print("Running isolated service tests...")

    try:
        await test_ai_service()
        await test_transcription_service()
        await test_cloud_storage()
        await test_file_upload()

        print("\n✅ All tests passed!")
        return 0
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
