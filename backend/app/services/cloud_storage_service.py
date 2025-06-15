"""
Cloud storage service for handling file uploads to AWS S3 or Cloudinary.
Provides a unified interface for cloud storage operations.
"""

import os
import uuid
from pathlib import Path
from typing import Optional, Tuple, Protocol
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class CloudStorageInterface(Protocol):
    """Protocol defining the interface for cloud storage providers."""
    
    async def upload_image(
        self, 
        file_data: bytes,
        filename: str,
        content_type: str,
        folder: str = "cover_images"
    ) -> str:
        """Upload an image and return its URL."""
        ...
    
    async def delete_image(self, url: str) -> bool:
        """Delete an image by URL."""
        ...


class S3StorageService:
    """AWS S3 storage service implementation."""
    
    def __init__(self, bucket_name: str, region: str, access_key_id: str, secret_access_key: str):
        import boto3
        from botocore.exceptions import ClientError
        
        self.bucket_name = bucket_name
        self.region = region
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region
        )
        self.ClientError = ClientError
        
    async def upload_image(
        self, 
        file_data: bytes,
        filename: str,
        content_type: str,
        folder: str = "cover_images"
    ) -> str:
        """Upload an image to S3 and return its URL."""
        try:
            # Generate unique key
            file_ext = Path(filename).suffix.lower()
            unique_key = f"{folder}/{uuid.uuid4().hex}{file_ext}"
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=unique_key,
                Body=file_data,
                ContentType=content_type,
                CacheControl='max-age=86400',  # Cache for 1 day
                ContentDisposition='inline'
            )
            
            # Return the URL
            url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{unique_key}"
            logger.info(f"Uploaded image to S3: {url}")
            return url
            
        except self.ClientError as e:
            logger.error(f"S3 upload failed: {str(e)}")
            raise Exception(f"Failed to upload to S3: {str(e)}")
    
    async def delete_image(self, url: str) -> bool:
        """Delete an image from S3 by URL."""
        try:
            # Extract key from URL
            # Format: https://bucket.s3.region.amazonaws.com/folder/file.jpg
            if f"{self.bucket_name}.s3" in url:
                key = url.split(f"{self.bucket_name}.s3.{self.region}.amazonaws.com/")[-1]
                
                self.s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=key
                )
                logger.info(f"Deleted image from S3: {key}")
                return True
            
            return False
            
        except self.ClientError as e:
            logger.error(f"S3 delete failed: {str(e)}")
            return False


class CloudinaryStorageService:
    """Cloudinary storage service implementation."""
    
    def __init__(self, cloud_name: str, api_key: str, api_secret: str):
        import cloudinary
        import cloudinary.uploader
        
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )
        self.cloudinary_uploader = cloudinary.uploader
        
    async def upload_image(
        self, 
        file_data: bytes,
        filename: str,
        content_type: str,
        folder: str = "cover_images"
    ) -> str:
        """Upload an image to Cloudinary and return its URL."""
        try:
            # Generate unique public_id
            file_ext = Path(filename).suffix.lower()
            public_id = f"{folder}/{uuid.uuid4().hex}"
            
            # Upload to Cloudinary
            result = self.cloudinary_uploader.upload(
                file_data,
                public_id=public_id,
                folder=folder,
                resource_type="image",
                format=file_ext.lstrip('.'),
                transformation=[
                    {'width': 1200, 'height': 1800, 'crop': 'limit'},
                    {'quality': 'auto:good'}
                ]
            )
            
            # Return the secure URL
            url = result.get('secure_url')
            logger.info(f"Uploaded image to Cloudinary: {url}")
            return url
            
        except Exception as e:
            logger.error(f"Cloudinary upload failed: {str(e)}")
            raise Exception(f"Failed to upload to Cloudinary: {str(e)}")
    
    async def delete_image(self, url: str) -> bool:
        """Delete an image from Cloudinary by URL."""
        try:
            # Extract public_id from URL
            # Cloudinary URLs contain the public_id in the path
            if "cloudinary.com" in url and "/image/upload/" in url:
                # Split by /image/upload/ and take the part after it
                parts = url.split("/image/upload/")[-1].split("/")
                # The public_id is usually after the version (v123456789)
                if len(parts) >= 2:
                    public_id = "/".join(parts[1:]).rsplit(".", 1)[0]  # Remove extension
                    
                    result = self.cloudinary_uploader.destroy(public_id)
                    
                    if result.get('result') == 'ok':
                        logger.info(f"Deleted image from Cloudinary: {public_id}")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Cloudinary delete failed: {str(e)}")
            return False


class CloudStorageFactory:
    """Factory for creating cloud storage service instances."""
    
    @staticmethod
    def create_storage_service(
        provider: str = "local",
        **kwargs
    ) -> Optional[CloudStorageInterface]:
        """
        Create a cloud storage service based on available credentials.
        
        Args:
            provider: Storage provider ("s3", "cloudinary", or "local")
            **kwargs: Provider-specific configuration
            
        Returns:
            Storage service instance or None for local storage
        """
        if provider == "s3":
            return S3StorageService(
                bucket_name=kwargs.get('bucket_name'),
                region=kwargs.get('region', 'us-east-1'),
                access_key_id=kwargs.get('access_key_id'),
                secret_access_key=kwargs.get('secret_access_key')
            )
        
        elif provider == "cloudinary":
            return CloudinaryStorageService(
                cloud_name=kwargs.get('cloud_name'),
                api_key=kwargs.get('api_key'),
                api_secret=kwargs.get('api_secret')
            )
        
        else:
            # Local storage - return None
            return None


# Global storage service instance
_storage_service = None


def get_cloud_storage_service() -> Optional[CloudStorageInterface]:
    """Get the configured cloud storage service."""
    global _storage_service
    
    if _storage_service is None:
        # Check for Cloudinary credentials first (better for images)
        if all([
            os.getenv('CLOUDINARY_CLOUD_NAME'),
            os.getenv('CLOUDINARY_API_KEY'),
            os.getenv('CLOUDINARY_API_SECRET')
        ]):
            logger.info("Using Cloudinary for image storage")
            _storage_service = CloudStorageFactory.create_storage_service(
                provider="cloudinary",
                cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
                api_key=os.getenv('CLOUDINARY_API_KEY'),
                api_secret=os.getenv('CLOUDINARY_API_SECRET')
            )
        
        # Check for S3 credentials
        elif all([
            os.getenv('AWS_ACCESS_KEY_ID'),
            os.getenv('AWS_SECRET_ACCESS_KEY'),
            os.getenv('AWS_S3_BUCKET')
        ]):
            logger.info("Using AWS S3 for image storage")
            _storage_service = CloudStorageFactory.create_storage_service(
                provider="s3",
                bucket_name=os.getenv('AWS_S3_BUCKET'),
                region=os.getenv('AWS_REGION', 'us-east-1'),
                access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )
        
        else:
            logger.warning("No cloud storage credentials found, using local storage")
            _storage_service = None
    
    return _storage_service