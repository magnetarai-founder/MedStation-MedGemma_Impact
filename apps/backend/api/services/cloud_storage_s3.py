"""
S3 Cloud Storage Service

Provides S3-compatible cloud storage operations:
- Multipart upload for large files
- Presigned URLs for secure downloads
- Encryption integration (AES-256-GCM)
- Storage class management

Supports AWS S3 and S3-compatible services (MinIO, LocalStack, etc.)

Configuration via environment variables:
- ELOHIMOS_CLOUD_STORAGE_ENABLED=true
- ELOHIMOS_CLOUD_STORAGE_PROVIDER=s3
- ELOHIMOS_S3_BUCKET_NAME=my-bucket
- ELOHIMOS_S3_REGION=us-east-1
- ELOHIMOS_S3_ACCESS_KEY_ID=xxx (optional, uses IAM roles if empty)
- ELOHIMOS_S3_SECRET_ACCESS_KEY=xxx (optional)
- ELOHIMOS_S3_ENDPOINT_URL=http://localhost:9000 (for MinIO/LocalStack)
"""

from __future__ import annotations

import logging
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, BinaryIO
from datetime import datetime, UTC
from functools import lru_cache

logger = logging.getLogger(__name__)


class S3StorageError(Exception):
    """Base exception for S3 storage operations."""
    pass


class S3ConfigurationError(S3StorageError):
    """S3 is not properly configured."""
    pass


class S3UploadError(S3StorageError):
    """Failed to upload to S3."""
    pass


class S3DownloadError(S3StorageError):
    """Failed to download from S3."""
    pass


class S3StorageService:
    """
    S3-compatible cloud storage service.

    Handles file uploads, downloads, and presigned URL generation.
    Supports AWS S3 and compatible services (MinIO, LocalStack, Backblaze B2, etc.)
    """

    def __init__(self):
        """Initialize S3 storage service from configuration."""
        from api.config import get_settings

        self._settings = get_settings()
        self._client = None
        self._initialized = False

    @property
    def is_enabled(self) -> bool:
        """Check if S3 storage is enabled and configured."""
        return (
            self._settings.cloud_storage_enabled and
            self._settings.cloud_storage_provider == "s3" and
            bool(self._settings.s3_bucket_name)
        )

    @property
    def bucket_name(self) -> str:
        """Get configured bucket name."""
        return self._settings.s3_bucket_name

    def _get_client(self):
        """
        Get or create boto3 S3 client.

        Lazily initializes the client on first use to avoid import
        errors if boto3 is not installed.
        """
        if self._client is not None:
            return self._client

        try:
            import boto3
            from botocore.config import Config
        except ImportError:
            raise S3ConfigurationError(
                "boto3 is not installed. Install with: pip install boto3"
            )

        if not self.is_enabled:
            raise S3ConfigurationError(
                "S3 storage is not enabled. Set ELOHIMOS_CLOUD_STORAGE_ENABLED=true "
                "and ELOHIMOS_S3_BUCKET_NAME=your-bucket"
            )

        # Build client configuration
        client_kwargs: Dict[str, Any] = {
            "service_name": "s3",
            "region_name": self._settings.s3_region,
            "config": Config(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "adaptive"}
            )
        }

        # Use explicit credentials if provided
        if self._settings.s3_access_key_id and self._settings.s3_secret_access_key:
            client_kwargs["aws_access_key_id"] = self._settings.s3_access_key_id
            client_kwargs["aws_secret_access_key"] = self._settings.s3_secret_access_key
            logger.debug("Using explicit AWS credentials")
        else:
            logger.debug("Using IAM role/instance profile for AWS credentials")

        # Custom endpoint for S3-compatible services
        if self._settings.s3_endpoint_url:
            client_kwargs["endpoint_url"] = self._settings.s3_endpoint_url
            logger.info(f"Using custom S3 endpoint: {self._settings.s3_endpoint_url}")

        self._client = boto3.client(**client_kwargs)
        self._initialized = True

        logger.info(f"S3 client initialized for bucket: {self.bucket_name}")
        return self._client

    def upload_file(
        self,
        file_path: Path,
        s3_key: str,
        content_type: str = "application/octet-stream",
        storage_class: str = "STANDARD",
        metadata: Optional[Dict[str, str]] = None,
        encrypt: bool = True
    ) -> Dict[str, Any]:
        """
        Upload a file to S3.

        Args:
            file_path: Local file path to upload
            s3_key: S3 object key (path in bucket)
            content_type: MIME type of the file
            storage_class: S3 storage class (STANDARD, INTELLIGENT_TIERING, etc.)
            metadata: Custom metadata to attach to object
            encrypt: Enable server-side encryption (AES-256)

        Returns:
            Dict with upload details including ETag and version_id

        Raises:
            S3UploadError: If upload fails
        """
        client = self._get_client()

        extra_args: Dict[str, Any] = {
            "ContentType": content_type,
            "StorageClass": self._normalize_storage_class(storage_class),
        }

        if metadata:
            extra_args["Metadata"] = metadata

        if encrypt:
            extra_args["ServerSideEncryption"] = "AES256"

        try:
            # Compute file hash before upload for verification
            file_hash = self._compute_file_hash(file_path)

            # Use multipart upload for large files (>100MB)
            file_size = file_path.stat().st_size

            if file_size > 100 * 1024 * 1024:
                result = self._multipart_upload(
                    file_path, s3_key, extra_args, file_size
                )
            else:
                # Simple upload for smaller files
                client.upload_file(
                    str(file_path),
                    self.bucket_name,
                    s3_key,
                    ExtraArgs=extra_args
                )

                # Get object info after upload
                head = client.head_object(Bucket=self.bucket_name, Key=s3_key)
                result = {
                    "etag": head.get("ETag", "").strip('"'),
                    "version_id": head.get("VersionId"),
                }

            logger.info(f"Uploaded to S3: {s3_key} ({file_size} bytes)")

            return {
                "bucket": self.bucket_name,
                "key": s3_key,
                "size_bytes": file_size,
                "sha256": file_hash,
                "etag": result.get("etag"),
                "version_id": result.get("version_id"),
                "storage_class": extra_args["StorageClass"],
                "encrypted": encrypt,
                "uploaded_at": datetime.now(UTC).isoformat()
            }

        except Exception as e:
            logger.error(f"S3 upload failed for {s3_key}: {e}")
            raise S3UploadError(f"Failed to upload {s3_key}: {e}") from e

    def upload_fileobj(
        self,
        fileobj: BinaryIO,
        s3_key: str,
        content_type: str = "application/octet-stream",
        storage_class: str = "STANDARD",
        metadata: Optional[Dict[str, str]] = None,
        encrypt: bool = True
    ) -> Dict[str, Any]:
        """
        Upload a file-like object to S3.

        Args:
            fileobj: File-like object with read() method
            s3_key: S3 object key
            content_type: MIME type
            storage_class: S3 storage class
            metadata: Custom metadata
            encrypt: Enable server-side encryption

        Returns:
            Dict with upload details
        """
        client = self._get_client()

        extra_args: Dict[str, Any] = {
            "ContentType": content_type,
            "StorageClass": self._normalize_storage_class(storage_class),
        }

        if metadata:
            extra_args["Metadata"] = metadata

        if encrypt:
            extra_args["ServerSideEncryption"] = "AES256"

        try:
            client.upload_fileobj(
                fileobj,
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )

            # Get object info
            head = client.head_object(Bucket=self.bucket_name, Key=s3_key)

            logger.info(f"Uploaded fileobj to S3: {s3_key}")

            return {
                "bucket": self.bucket_name,
                "key": s3_key,
                "size_bytes": head.get("ContentLength", 0),
                "etag": head.get("ETag", "").strip('"'),
                "version_id": head.get("VersionId"),
                "storage_class": extra_args["StorageClass"],
                "encrypted": encrypt,
                "uploaded_at": datetime.now(UTC).isoformat()
            }

        except Exception as e:
            logger.error(f"S3 fileobj upload failed for {s3_key}: {e}")
            raise S3UploadError(f"Failed to upload {s3_key}: {e}") from e

    def _multipart_upload(
        self,
        file_path: Path,
        s3_key: str,
        extra_args: Dict[str, Any],
        file_size: int
    ) -> Dict[str, Any]:
        """
        Perform multipart upload for large files.

        Uses 10MB parts for optimal performance.
        """
        client = self._get_client()
        part_size = 10 * 1024 * 1024  # 10 MB parts

        # Initiate multipart upload
        mpu = client.create_multipart_upload(
            Bucket=self.bucket_name,
            Key=s3_key,
            **extra_args
        )
        upload_id = mpu["UploadId"]

        parts = []
        part_number = 1

        try:
            with open(file_path, "rb") as f:
                while True:
                    data = f.read(part_size)
                    if not data:
                        break

                    response = client.upload_part(
                        Bucket=self.bucket_name,
                        Key=s3_key,
                        UploadId=upload_id,
                        PartNumber=part_number,
                        Body=data
                    )

                    parts.append({
                        "PartNumber": part_number,
                        "ETag": response["ETag"]
                    })

                    part_number += 1

            # Complete multipart upload
            result = client.complete_multipart_upload(
                Bucket=self.bucket_name,
                Key=s3_key,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts}
            )

            return {
                "etag": result.get("ETag", "").strip('"'),
                "version_id": result.get("VersionId"),
            }

        except Exception as e:
            # Abort multipart upload on failure
            client.abort_multipart_upload(
                Bucket=self.bucket_name,
                Key=s3_key,
                UploadId=upload_id
            )
            raise

    def generate_presigned_url(
        self,
        s3_key: str,
        expires_in: Optional[int] = None,
        response_content_type: Optional[str] = None,
        response_content_disposition: Optional[str] = None
    ) -> str:
        """
        Generate a presigned URL for downloading a file.

        Args:
            s3_key: S3 object key
            expires_in: URL expiration in seconds (default: from settings)
            response_content_type: Override Content-Type header in response
            response_content_disposition: Set Content-Disposition header

        Returns:
            Presigned URL string
        """
        client = self._get_client()

        if expires_in is None:
            expires_in = self._settings.s3_presigned_url_expiry_seconds

        params: Dict[str, Any] = {
            "Bucket": self.bucket_name,
            "Key": s3_key,
        }

        response_params = {}
        if response_content_type:
            response_params["ResponseContentType"] = response_content_type
        if response_content_disposition:
            response_params["ResponseContentDisposition"] = response_content_disposition

        if response_params:
            params["Params"] = response_params

        try:
            url = client.generate_presigned_url(
                "get_object",
                Params=params,
                ExpiresIn=expires_in
            )

            logger.debug(f"Generated presigned URL for {s3_key} (expires in {expires_in}s)")
            return url

        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {s3_key}: {e}")
            raise S3StorageError(f"Failed to generate presigned URL: {e}") from e

    def generate_presigned_upload_url(
        self,
        s3_key: str,
        content_type: str = "application/octet-stream",
        expires_in: Optional[int] = None
    ) -> Dict[str, str]:
        """
        Generate a presigned URL for direct upload to S3.

        Allows clients to upload directly to S3 without proxying through the server.

        Args:
            s3_key: S3 object key
            content_type: MIME type of the file
            expires_in: URL expiration in seconds

        Returns:
            Dict with url and fields for POST upload
        """
        client = self._get_client()

        if expires_in is None:
            expires_in = self._settings.s3_presigned_url_expiry_seconds

        try:
            response = client.generate_presigned_post(
                Bucket=self.bucket_name,
                Key=s3_key,
                Fields={"Content-Type": content_type},
                Conditions=[
                    {"Content-Type": content_type},
                    ["content-length-range", 1, 5 * 1024 * 1024 * 1024]  # 1 byte to 5GB
                ],
                ExpiresIn=expires_in
            )

            logger.debug(f"Generated presigned upload URL for {s3_key}")
            return response

        except Exception as e:
            logger.error(f"Failed to generate presigned upload URL for {s3_key}: {e}")
            raise S3StorageError(f"Failed to generate presigned upload URL: {e}") from e

    def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from S3.

        Args:
            s3_key: S3 object key to delete

        Returns:
            True if deleted successfully
        """
        client = self._get_client()

        try:
            client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"Deleted from S3: {s3_key}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete {s3_key} from S3: {e}")
            raise S3StorageError(f"Failed to delete {s3_key}: {e}") from e

    def file_exists(self, s3_key: str) -> bool:
        """Check if a file exists in S3."""
        client = self._get_client()

        try:
            client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise

    def get_file_info(self, s3_key: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a file in S3.

        Returns:
            Dict with file info or None if not found
        """
        client = self._get_client()

        try:
            head = client.head_object(Bucket=self.bucket_name, Key=s3_key)

            return {
                "key": s3_key,
                "size_bytes": head.get("ContentLength", 0),
                "content_type": head.get("ContentType"),
                "etag": head.get("ETag", "").strip('"'),
                "last_modified": head.get("LastModified").isoformat() if head.get("LastModified") else None,
                "storage_class": head.get("StorageClass", "STANDARD"),
                "metadata": head.get("Metadata", {}),
                "version_id": head.get("VersionId"),
            }

        except client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return None
            raise

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _normalize_storage_class(self, storage_class: str) -> str:
        """
        Normalize storage class to valid S3 value.

        Maps friendly names to S3 storage class constants.
        """
        mapping = {
            "standard": "STANDARD",
            "archive": "GLACIER",
            "cold": "GLACIER_IR",  # Glacier Instant Retrieval
            "intelligent": "INTELLIGENT_TIERING",
            "infrequent": "STANDARD_IA",
        }

        return mapping.get(storage_class.lower(), storage_class.upper())


# Singleton instance
_s3_service: Optional[S3StorageService] = None


def get_s3_service() -> S3StorageService:
    """
    Get the singleton S3 storage service instance.

    Returns:
        S3StorageService instance
    """
    global _s3_service
    if _s3_service is None:
        _s3_service = S3StorageService()
    return _s3_service
