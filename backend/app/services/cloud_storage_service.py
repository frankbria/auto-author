"""
Cloud storage service for handling file uploads to AWS S3 or Cloudinary.
Provides a unified interface for cloud storage operations.
"""

import asyncio
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, NamedTuple, Optional, Protocol

from app.core.config import settings
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


def _is_owned_key(key: str, key_prefix: str) -> bool:
    """True when ``key`` sits under ``key_prefix``.

    A stored URL is not proof of ownership (#797): it was once client-writable.
    The caller names the owner's prefix and nothing outside it is deleted.
    """
    return bool(key_prefix) and key.startswith(key_prefix) and ".." not in key.split("/")


class StoredObject(NamedTuple):
    """One object found by ``list_objects``: its key, a URL ``delete_image``
    accepts for it, and when it was last written (timezone-aware)."""

    key: str
    url: str
    modified: datetime


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

    def owned_key(self, url: str, key_prefix: str) -> Optional[str]:
        """The storage key ``url`` names, if this provider wrote it under ``key_prefix``."""
        ...

    async def delete_images(self, items: list[tuple[str, str]]) -> list[str]:
        """Delete many ``(url, key_prefix)`` images in batched calls. Returns the
        URLs not deleted, refused ones included."""
        ...

    async def delete_image(self, url: str, key_prefix: str) -> bool:
        """Delete an image by URL, only if its key is under ``key_prefix``."""
        ...

    async def list_objects(self, prefix: str) -> List[StoredObject]:
        """Every object whose key starts with ``prefix``, all pages."""
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

            # boto3 is synchronous — a multi-second S3 round-trip inside
            # `async def` freezes the event loop for every other request on
            # this worker (#346). Offload it.
            await asyncio.to_thread(
                self.s3_client.put_object,
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

    def owned_key(self, url: str, key_prefix: str) -> Optional[str]:
        """The key of this bucket's ``url`` if it sits under ``key_prefix``."""
        # Format: https://bucket.s3.region.amazonaws.com/folder/file.jpg
        try:
            parsed = urlparse(url)
        except ValueError:  # urlparse rejects some malformed stored values
            return None
        if parsed.hostname != f"{self.bucket_name}.s3.{self.region}.amazonaws.com":
            return None
        key = parsed.path.lstrip("/")
        return key if _is_owned_key(key, key_prefix) else None

    async def delete_images(self, items: list[tuple[str, str]]) -> list[str]:
        """Delete in DeleteObjects calls of up to 1,000 keys, the API's cap."""
        urls = {}
        failed = []
        for url, key_prefix in items:
            key = self.owned_key(url, key_prefix)
            if key is None:
                failed.append(url)
            else:
                urls[key] = url
        keys = list(urls)
        for start in range(0, len(keys), 1000):
            chunk = keys[start:start + 1000]
            try:
                response = await asyncio.to_thread(
                    self.s3_client.delete_objects,
                    Bucket=self.bucket_name,
                    Delete={"Objects": [{"Key": key} for key in chunk], "Quiet": True},
                )
            except self.ClientError as e:
                logger.error(f"S3 batch delete failed: {str(e)}")
                failed += [urls[key] for key in chunk]
                continue
            failed += [urls[error["Key"]] for error in response.get("Errors", [])]
        return failed

    async def delete_image(self, url: str, key_prefix: str) -> bool:
        """Delete an image from S3 by URL, only if its key is under ``key_prefix``."""
        try:
            key = self.owned_key(url, key_prefix)
            if key is None:
                logger.warning("Refusing to delete S3 key outside %s", key_prefix)
                return False

            await asyncio.to_thread(
                self.s3_client.delete_object,
                Bucket=self.bucket_name,
                Key=key
            )
            logger.info(f"Deleted image from S3: {key}")
            return True

        # ValueError: urlparse rejects some malformed stored values.
        except (self.ClientError, ValueError) as e:
            logger.error(f"S3 delete failed: {str(e)}")
            return False

    async def list_objects(self, prefix: str) -> List[StoredObject]:
        """Every key under ``prefix``; the paginator follows the 1000-key pages."""

        def _list():
            pages = self.s3_client.get_paginator("list_objects_v2").paginate(
                Bucket=self.bucket_name, Prefix=prefix
            )
            return [
                StoredObject(
                    item["Key"],
                    f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{item['Key']}",
                    item["LastModified"],
                )
                for page in pages
                for item in page.get("Contents", [])
            ]

        return await asyncio.to_thread(_list)


class CloudinaryStorageService:
    """Cloudinary storage service implementation."""

    def __init__(self, cloud_name: str, api_key: str, api_secret: str):
        import cloudinary
        import cloudinary.api
        import cloudinary.uploader

        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )
        self.cloudinary_uploader = cloudinary.uploader
        self.cloudinary_api = cloudinary.api

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

            # The Cloudinary SDK is synchronous — same offload as S3 (#346).
            result = await asyncio.to_thread(
                self.cloudinary_uploader.upload,
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

    def owned_key(self, url: str, key_prefix: str) -> Optional[str]:
        """The public_id of a Cloudinary ``url`` if it sits under ``key_prefix``."""
        # Format: https://res.cloudinary.com/<cloud>/image/upload/v123/<public_id>.<ext>
        try:
            parsed = urlparse(url)
        except ValueError:
            return None
        if parsed.hostname != "res.cloudinary.com" or "/image/upload/" not in parsed.path:
            return None
        parts = parsed.path.split("/image/upload/", 1)[1].split("/")
        if re.fullmatch(r"v\d+", parts[0]):
            parts = parts[1:]
        public_id = "/".join(parts).rsplit(".", 1)[0]  # Remove extension
        return public_id if _is_owned_key(public_id, key_prefix) else None

    async def delete_images(self, items: list[tuple[str, str]]) -> list[str]:
        """Delete in Admin API delete_resources calls of up to 100 public_ids,
        the API's cap. Anything not answered "deleted" is reported."""
        urls = {}
        failed = []
        for url, key_prefix in items:
            public_id = self.owned_key(url, key_prefix)
            if public_id is None:
                failed.append(url)
            else:
                urls[public_id] = url
        ids = list(urls)
        for start in range(0, len(ids), 100):
            chunk = ids[start:start + 100]
            try:
                result = await asyncio.to_thread(
                    self.cloudinary_api.delete_resources,
                    chunk, resource_type="image", type="upload",
                )
                deleted = result.get("deleted", {})
            except Exception as e:
                logger.error(f"Cloudinary batch delete failed: {str(e)}")
                deleted = {}
            failed += [urls[i] for i in chunk if deleted.get(i) != "deleted"]
        return failed

    async def delete_image(self, url: str, key_prefix: str) -> bool:
        """Delete an image from Cloudinary by URL, only if its public_id is
        under ``key_prefix``."""
        try:
            public_id = self.owned_key(url, key_prefix)
            if public_id is None:
                logger.warning("Refusing to destroy Cloudinary id outside %s", key_prefix)
                return False

            result = await asyncio.to_thread(
                self.cloudinary_uploader.destroy, public_id
            )

            if result.get('result') == 'ok':
                logger.info(f"Deleted image from Cloudinary: {public_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Cloudinary delete failed: {str(e)}")
            return False

    async def list_objects(self, prefix: str) -> List[StoredObject]:
        """Every uploaded image whose public_id starts with ``prefix`` (Admin
        API, 500 per page). The key is the public_id, which has no extension."""

        def _list():
            objects, cursor = [], None
            while True:
                options = {"type": "upload", "prefix": prefix, "max_results": 500}
                if cursor:
                    options["next_cursor"] = cursor
                page = self.cloudinary_api.resources(**options)
                objects += [
                    StoredObject(
                        r["public_id"],
                        r["secure_url"],
                        datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")),
                    )
                    for r in page.get("resources", [])
                ]
                cursor = page.get("next_cursor")
                if not cursor:
                    return objects

        return await asyncio.to_thread(_list)


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
        # settings.storage_provider is the one place the provider is decided (#806).
        provider = settings.storage_provider
        if provider == "cloudinary":
            logger.info("Using Cloudinary for image storage")
            _storage_service = CloudStorageFactory.create_storage_service(
                provider="cloudinary",
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET,
            )
        elif provider == "s3":
            logger.info("Using AWS S3 for image storage")
            _storage_service = CloudStorageFactory.create_storage_service(
                provider="s3",
                bucket_name=settings.AWS_S3_BUCKET,
                region=settings.AWS_REGION,
                access_key_id=settings.AWS_ACCESS_KEY_ID,
                secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
        else:
            missing = settings.storage_fields_missing
            logger.warning(
                "No complete cloud storage configuration%s, using local storage",
                f" (not set: {', '.join(missing)})" if missing else "",
            )
            _storage_service = None

    return _storage_service
