"""
Test Cloud Storage Service functionality
Tests S3, Cloudinary, and factory pattern
"""
import sys
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError
from app.services.cloud_storage_service import (
    S3StorageService, 
    CloudinaryStorageService, 
    CloudStorageFactory,
    get_cloud_storage_service
)


class TestS3StorageService:
    """Test S3 storage service implementation."""
    
    @pytest.fixture
    def mock_s3_client(self):
        """Mock S3 client."""
        with patch('boto3.client') as mock_client:
            mock_s3 = Mock()
            mock_client.return_value = mock_s3
            yield mock_s3
    
    @pytest.fixture
    def s3_service(self, mock_s3_client):
        """Create S3 storage service with mocked client."""
        service = S3StorageService(
            bucket_name='test-bucket',
            region='us-east-1',
            access_key_id='test-key',
            secret_access_key='test-secret'
        )
        service.s3_client = mock_s3_client
        return service
    
    @pytest.mark.asyncio
    async def test_s3_upload_image_success(self, s3_service):
        """Test successful image upload to S3."""
        # Mock successful upload
        s3_service.s3_client.put_object.return_value = {}
        
        url = await s3_service.upload_image(
            file_data=b"fake image data",
            filename="test.jpg",
            content_type="image/jpeg",
            folder="test_folder"
        )
        
        assert url.startswith("https://test-bucket.s3.us-east-1.amazonaws.com/")
        assert "test_folder/" in url
        assert url.endswith(".jpg")
        
        # Verify S3 was called correctly
        s3_service.s3_client.put_object.assert_called_once()
        call_args = s3_service.s3_client.put_object.call_args[1]
        assert call_args['Bucket'] == 'test-bucket'
        assert call_args['ContentType'] == 'image/jpeg'
        assert call_args['Body'] == b"fake image data"
    
    @pytest.mark.asyncio
    async def test_s3_upload_image_failure(self, s3_service):
        """Test S3 upload failure handling."""
        # Mock upload failure
        s3_service.s3_client.put_object.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied'}}, 'PutObject'
        )
        
        with pytest.raises(Exception) as exc_info:
            await s3_service.upload_image(
                file_data=b"fake image",
                filename="test.jpg",
                content_type="image/jpeg"
            )
        
        assert "Failed to upload to S3" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_s3_delete_image_success(self, s3_service):
        """Test successful image deletion from S3."""
        # Mock successful deletion
        s3_service.s3_client.delete_object.return_value = {}
        
        url = "https://test-bucket.s3.us-east-1.amazonaws.com/folder/image.jpg"
        result = await s3_service.delete_image(url)
        
        assert result is True
        s3_service.s3_client.delete_object.assert_called_once_with(
            Bucket='test-bucket',
            Key='folder/image.jpg'
        )
    
    @pytest.mark.asyncio
    async def test_s3_delete_image_invalid_url(self, s3_service):
        """Test deletion with invalid URL."""
        result = await s3_service.delete_image("https://wrong-bucket.com/image.jpg")
        assert result is False
        s3_service.s3_client.delete_object.assert_not_called()


class TestCloudinaryStorageService:
    """Test Cloudinary storage service implementation."""
    
    @pytest.fixture
    def mock_cloudinary(self):
        """Mock cloudinary module."""
        # Create a mock module structure
        mock_cloudinary_module = Mock()
        mock_uploader = Mock()
        mock_cloudinary_module.uploader = mock_uploader
        mock_cloudinary_module.config = Mock()
        
        with patch.dict('sys.modules', {
            'cloudinary': mock_cloudinary_module,
            'cloudinary.uploader': mock_uploader
        }):
            yield mock_cloudinary_module.config, mock_uploader
    
    @pytest.fixture
    def cloudinary_service(self, mock_cloudinary):
        """Create Cloudinary storage service with mocked dependencies."""
        mock_config, mock_uploader = mock_cloudinary
        service = CloudinaryStorageService(
            cloud_name='test-cloud',
            api_key='test-key',
            api_secret='test-secret'
        )
        service.cloudinary_uploader = mock_uploader
        return service
    
    @pytest.mark.asyncio
    async def test_cloudinary_upload_image_success(self, cloudinary_service):
        """Test successful image upload to Cloudinary."""
        # Mock successful upload
        cloudinary_service.cloudinary_uploader.upload.return_value = {
            'secure_url': 'https://res.cloudinary.com/test-cloud/image/upload/v123/folder/image.jpg',
            'public_id': 'folder/image'
        }
        
        url = await cloudinary_service.upload_image(
            file_data=b"fake image data",
            filename="test.jpg",
            content_type="image/jpeg",
            folder="test_folder"
        )
        
        assert url == 'https://res.cloudinary.com/test-cloud/image/upload/v123/folder/image.jpg'
        
        # Verify Cloudinary was called
        cloudinary_service.cloudinary_uploader.upload.assert_called_once()
        call_args = cloudinary_service.cloudinary_uploader.upload.call_args
        assert call_args[0][0] == b"fake image data"
        assert call_args[1]['folder'] == 'test_folder'
    
    @pytest.mark.asyncio
    async def test_cloudinary_upload_image_failure(self, cloudinary_service):
        """Test Cloudinary upload failure handling."""
        # Mock upload failure
        cloudinary_service.cloudinary_uploader.upload.side_effect = Exception("Upload failed")
        
        with pytest.raises(Exception) as exc_info:
            await cloudinary_service.upload_image(
                file_data=b"fake image",
                filename="test.jpg",
                content_type="image/jpeg"
            )
        
        assert "Failed to upload to Cloudinary" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_cloudinary_delete_image_success(self, cloudinary_service):
        """Test successful image deletion from Cloudinary."""
        # Mock successful deletion
        cloudinary_service.cloudinary_uploader.destroy.return_value = {
            'result': 'ok'
        }
        
        url = "https://res.cloudinary.com/test/image/upload/v123/folder/subfolder/image.jpg"
        result = await cloudinary_service.delete_image(url)
        
        assert result is True
        cloudinary_service.cloudinary_uploader.destroy.assert_called_once_with('folder/subfolder/image')
    
    @pytest.mark.asyncio
    async def test_cloudinary_delete_image_invalid_url(self, cloudinary_service):
        """Test deletion with invalid URL."""
        result = await cloudinary_service.delete_image("https://wrongsite.com/image.jpg")
        assert result is False
        cloudinary_service.cloudinary_uploader.destroy.assert_not_called()


class TestCloudStorageFactory:
    """Test cloud storage factory pattern."""
    
    def test_create_s3_storage(self):
        """Test S3 storage service creation."""
        with patch('app.services.cloud_storage_service.S3StorageService') as mock_s3:
            service = CloudStorageFactory.create_storage_service(
                provider='s3',
                bucket_name='test-bucket',
                region='us-east-1',
                access_key_id='key',
                secret_access_key='secret'
            )
            
            mock_s3.assert_called_once_with(
                bucket_name='test-bucket',
                region='us-east-1',
                access_key_id='key',
                secret_access_key='secret'
            )
    
    def test_create_cloudinary_storage(self):
        """Test Cloudinary storage service creation."""
        with patch('app.services.cloud_storage_service.CloudinaryStorageService') as mock_cloudinary:
            service = CloudStorageFactory.create_storage_service(
                provider='cloudinary',
                cloud_name='test',
                api_key='key',
                api_secret='secret'
            )
            
            mock_cloudinary.assert_called_once_with(
                cloud_name='test',
                api_key='key',
                api_secret='secret'
            )
    
    def test_create_local_storage(self):
        """Test local storage returns None."""
        service = CloudStorageFactory.create_storage_service(provider='local')
        assert service is None


class TestGetCloudStorageService:
    """Test the global storage service getter."""
    
    @pytest.fixture
    def reset_global_service(self):
        """Reset global storage service between tests."""
        import app.services.cloud_storage_service
        app.services.cloud_storage_service._storage_service = None
        yield
        app.services.cloud_storage_service._storage_service = None
    
    def test_get_storage_with_cloudinary(self, monkeypatch, reset_global_service):
        """Test that Cloudinary is preferred when credentials exist."""
        monkeypatch.setenv('CLOUDINARY_CLOUD_NAME', 'test-cloud')
        monkeypatch.setenv('CLOUDINARY_API_KEY', 'test-key')
        monkeypatch.setenv('CLOUDINARY_API_SECRET', 'test-secret')
        
        with patch('app.services.cloud_storage_service.CloudStorageFactory.create_storage_service') as mock_factory:
            mock_service = Mock()
            mock_factory.return_value = mock_service
            
            service = get_cloud_storage_service()
            
            assert service == mock_service
            mock_factory.assert_called_once_with(
                provider='cloudinary',
                cloud_name='test-cloud',
                api_key='test-key',
                api_secret='test-secret'
            )
    
    def test_get_storage_with_s3(self, monkeypatch, reset_global_service):
        """Test S3 is used when only S3 credentials exist."""
        monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'test-key')
        monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'test-secret')
        monkeypatch.setenv('AWS_S3_BUCKET', 'test-bucket')
        
        with patch('app.services.cloud_storage_service.CloudStorageFactory.create_storage_service') as mock_factory:
            mock_service = Mock()
            mock_factory.return_value = mock_service
            
            service = get_cloud_storage_service()
            
            mock_factory.assert_called_once_with(
                provider='s3',
                bucket_name='test-bucket',
                region='us-east-1',
                access_key_id='test-key',
                secret_access_key='test-secret'
            )
    
    def test_get_storage_returns_none_without_credentials(self, monkeypatch, reset_global_service):
        """Test that None is returned when no credentials exist."""
        # Clear all credentials
        for key in ['CLOUDINARY_CLOUD_NAME', 'CLOUDINARY_API_KEY', 'CLOUDINARY_API_SECRET',
                    'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_S3_BUCKET']:
            monkeypatch.delenv(key, raising=False)
        
        service = get_cloud_storage_service()
        assert service is None