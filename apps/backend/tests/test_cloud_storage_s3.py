"""
Tests for S3 Cloud Storage Service

Tests the S3StorageService with mocked boto3 to avoid actual AWS calls.
"""

import io
import sys
import json
import pytest
import hashlib
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from datetime import datetime, UTC

from api.services.cloud_storage_s3 import (
    S3StorageService,
    S3StorageError,
    S3ConfigurationError,
    S3UploadError,
    S3DownloadError,
    get_s3_service,
)

# Path to patch for get_settings - the S3 service imports it inside __init__
SETTINGS_PATCH_PATH = "api.config.get_settings"


# ===== Mock boto3 module =====
# Create a mock boto3 module to inject into sys.modules
# This allows patching boto3.client even when boto3 isn't installed

def _create_mock_boto3_module():
    """Create a mock boto3 module with client function."""
    mock_boto3 = MagicMock()
    mock_boto3.client = MagicMock()
    return mock_boto3


def _create_mock_botocore_module():
    """Create a mock botocore module with Config class."""
    mock_botocore = MagicMock()
    mock_botocore_config = MagicMock()
    mock_botocore_config.Config = MagicMock(return_value=MagicMock())
    mock_botocore.config = mock_botocore_config
    return mock_botocore


@pytest.fixture(autouse=True)
def mock_boto3_module():
    """
    Auto-use fixture that injects mock boto3 into sys.modules.
    This allows tests to patch boto3.client even when boto3 isn't installed.
    """
    mock_boto3 = _create_mock_boto3_module()
    mock_botocore = _create_mock_botocore_module()

    # Store original modules if they exist
    original_boto3 = sys.modules.get("boto3")
    original_botocore = sys.modules.get("botocore")
    original_botocore_config = sys.modules.get("botocore.config")

    # Inject mocks
    sys.modules["boto3"] = mock_boto3
    sys.modules["botocore"] = mock_botocore
    sys.modules["botocore.config"] = mock_botocore.config

    yield mock_boto3

    # Restore original modules
    if original_boto3 is not None:
        sys.modules["boto3"] = original_boto3
    else:
        sys.modules.pop("boto3", None)

    if original_botocore is not None:
        sys.modules["botocore"] = original_botocore
    else:
        sys.modules.pop("botocore", None)

    if original_botocore_config is not None:
        sys.modules["botocore.config"] = original_botocore_config
    else:
        sys.modules.pop("botocore.config", None)


# ===== Fixtures =====

@pytest.fixture
def mock_settings():
    """Create mock settings with S3 enabled."""
    settings = Mock()
    settings.cloud_storage_enabled = True
    settings.cloud_storage_provider = "s3"
    settings.s3_bucket_name = "test-bucket"
    settings.s3_region = "us-east-1"
    settings.s3_access_key_id = "test-access-key"
    settings.s3_secret_access_key = "test-secret-key"
    settings.s3_endpoint_url = ""
    settings.s3_presigned_url_expiry_seconds = 3600
    return settings


@pytest.fixture
def mock_settings_disabled():
    """Create mock settings with S3 disabled."""
    settings = Mock()
    settings.cloud_storage_enabled = False
    settings.cloud_storage_provider = "local"
    settings.s3_bucket_name = ""
    settings.s3_region = "us-east-1"
    settings.s3_access_key_id = ""
    settings.s3_secret_access_key = ""
    settings.s3_endpoint_url = ""
    settings.s3_presigned_url_expiry_seconds = 3600
    return settings


@pytest.fixture
def mock_settings_custom_endpoint():
    """Create mock settings with custom S3 endpoint (MinIO)."""
    settings = Mock()
    settings.cloud_storage_enabled = True
    settings.cloud_storage_provider = "s3"
    settings.s3_bucket_name = "test-bucket"
    settings.s3_region = "us-east-1"
    settings.s3_access_key_id = "minio-access"
    settings.s3_secret_access_key = "minio-secret"
    settings.s3_endpoint_url = "http://localhost:9000"
    settings.s3_presigned_url_expiry_seconds = 3600
    return settings


@pytest.fixture
def mock_boto3_client():
    """Create a mock boto3 S3 client."""
    client = MagicMock()

    # Mock head_object response
    client.head_object.return_value = {
        "ETag": '"abc123"',
        "VersionId": "v1",
        "ContentLength": 1024,
        "ContentType": "application/octet-stream",
        "LastModified": datetime.now(UTC),
        "StorageClass": "STANDARD",
        "Metadata": {"custom": "value"},
    }

    # Mock generate_presigned_url
    client.generate_presigned_url.return_value = "https://test-bucket.s3.amazonaws.com/test-key?signature=xyz"

    # Mock generate_presigned_post
    client.generate_presigned_post.return_value = {
        "url": "https://test-bucket.s3.amazonaws.com",
        "fields": {"key": "test-key", "AWSAccessKeyId": "xxx"},
    }

    # Mock delete_object
    client.delete_object.return_value = {}

    # Mock upload_file (no return value)
    client.upload_file.return_value = None

    # Mock upload_fileobj (no return value)
    client.upload_fileobj.return_value = None

    # Mock multipart upload
    client.create_multipart_upload.return_value = {"UploadId": "test-upload-id"}
    client.upload_part.return_value = {"ETag": '"part-etag"'}
    client.complete_multipart_upload.return_value = {
        "ETag": '"complete-etag"',
        "VersionId": "v1",
    }
    client.abort_multipart_upload.return_value = {}

    # Mock exceptions
    client.exceptions = Mock()
    client.exceptions.ClientError = type("ClientError", (Exception,), {})

    return client


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary test file."""
    file_path = tmp_path / "test_file.txt"
    content = b"Hello, S3 World! This is test content."
    file_path.write_bytes(content)
    return file_path


@pytest.fixture
def large_temp_file(tmp_path):
    """Create a large temporary file (simulated for testing)."""
    file_path = tmp_path / "large_file.bin"
    # Create a small file but we'll mock the size check
    content = b"x" * 1024
    file_path.write_bytes(content)
    return file_path


# ===== Test Classes =====

class TestS3ServiceInitialization:
    """Test S3StorageService initialization and configuration."""

    def test_service_init_with_settings(self, mock_settings):
        """Test service initializes with settings."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            service = S3StorageService()
            assert service._settings == mock_settings
            assert service._client is None
            assert service._initialized is False

    def test_is_enabled_when_configured(self, mock_settings):
        """Test is_enabled returns True when properly configured."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            service = S3StorageService()
            assert service.is_enabled is True

    def test_is_enabled_when_disabled(self, mock_settings_disabled):
        """Test is_enabled returns False when disabled."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings_disabled):
            service = S3StorageService()
            assert service.is_enabled is False

    def test_is_enabled_requires_bucket_name(self, mock_settings):
        """Test is_enabled requires bucket name."""
        mock_settings.s3_bucket_name = ""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            service = S3StorageService()
            assert service.is_enabled is False

    def test_bucket_name_property(self, mock_settings):
        """Test bucket_name property returns configured bucket."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            service = S3StorageService()
            assert service.bucket_name == "test-bucket"


class TestS3ClientCreation:
    """Test boto3 client creation and configuration."""

    def test_get_client_creates_boto3_client(self, mock_settings, mock_boto3_client):
        """Test _get_client creates boto3 client."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            with patch("boto3.client", return_value=mock_boto3_client) as mock_boto:
                service = S3StorageService()
                client = service._get_client()

                assert client == mock_boto3_client
                mock_boto.assert_called_once()

                # Verify client kwargs
                call_kwargs = mock_boto.call_args[1]
                assert call_kwargs["service_name"] == "s3"
                assert call_kwargs["region_name"] == "us-east-1"
                assert call_kwargs["aws_access_key_id"] == "test-access-key"
                assert call_kwargs["aws_secret_access_key"] == "test-secret-key"

    def test_get_client_with_custom_endpoint(self, mock_settings_custom_endpoint, mock_boto3_client):
        """Test _get_client with custom endpoint URL."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings_custom_endpoint):
            with patch("boto3.client", return_value=mock_boto3_client) as mock_boto:
                service = S3StorageService()
                service._get_client()

                call_kwargs = mock_boto.call_args[1]
                assert call_kwargs["endpoint_url"] == "http://localhost:9000"

    def test_get_client_reuses_existing_client(self, mock_settings, mock_boto3_client):
        """Test _get_client reuses existing client."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            with patch("boto3.client", return_value=mock_boto3_client) as mock_boto:
                service = S3StorageService()

                # First call creates client
                client1 = service._get_client()
                # Second call reuses
                client2 = service._get_client()

                assert client1 is client2
                assert mock_boto.call_count == 1

    def test_get_client_raises_when_disabled(self, mock_settings_disabled):
        """Test _get_client raises error when S3 disabled."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings_disabled):
            service = S3StorageService()

            with pytest.raises(S3ConfigurationError) as exc_info:
                service._get_client()

            assert "not enabled" in str(exc_info.value)

    def test_get_client_raises_when_boto3_missing(self, mock_settings):
        """Test _get_client raises error when boto3 not installed."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            with patch.dict("sys.modules", {"boto3": None}):
                service = S3StorageService()

                # Force reimport attempt
                with patch("builtins.__import__", side_effect=ImportError("No module named 'boto3'")):
                    with pytest.raises(S3ConfigurationError) as exc_info:
                        service._get_client()

                    assert "boto3 is not installed" in str(exc_info.value)


class TestS3Upload:
    """Test S3 upload functionality."""

    def test_upload_file_success(self, mock_settings, mock_boto3_client, temp_file):
        """Test successful file upload."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            with patch("boto3.client", return_value=mock_boto3_client):
                service = S3StorageService()

                result = service.upload_file(
                    file_path=temp_file,
                    s3_key="uploads/test.txt",
                    content_type="text/plain",
                )

                assert result["bucket"] == "test-bucket"
                assert result["key"] == "uploads/test.txt"
                assert result["storage_class"] == "STANDARD"
                assert result["encrypted"] is True
                assert "sha256" in result
                assert "uploaded_at" in result

                mock_boto3_client.upload_file.assert_called_once()

    def test_upload_file_with_metadata(self, mock_settings, mock_boto3_client, temp_file):
        """Test file upload with custom metadata."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            with patch("boto3.client", return_value=mock_boto3_client):
                service = S3StorageService()

                result = service.upload_file(
                    file_path=temp_file,
                    s3_key="uploads/test.txt",
                    metadata={"user_id": "123", "filename": "test.txt"},
                )

                # Verify metadata was passed
                call_args = mock_boto3_client.upload_file.call_args
                extra_args = call_args[1]["ExtraArgs"]
                assert extra_args["Metadata"] == {"user_id": "123", "filename": "test.txt"}

    def test_upload_file_without_encryption(self, mock_settings, mock_boto3_client, temp_file):
        """Test file upload without encryption."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            with patch("boto3.client", return_value=mock_boto3_client):
                service = S3StorageService()

                result = service.upload_file(
                    file_path=temp_file,
                    s3_key="uploads/test.txt",
                    encrypt=False,
                )

                assert result["encrypted"] is False

                call_args = mock_boto3_client.upload_file.call_args
                extra_args = call_args[1]["ExtraArgs"]
                assert "ServerSideEncryption" not in extra_args

    def test_upload_file_error_raises_s3_upload_error(self, mock_settings, mock_boto3_client, temp_file):
        """Test upload failure raises S3UploadError."""
        mock_boto3_client.upload_file.side_effect = Exception("Network error")

        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            with patch("boto3.client", return_value=mock_boto3_client):
                service = S3StorageService()

                with pytest.raises(S3UploadError) as exc_info:
                    service.upload_file(file_path=temp_file, s3_key="test.txt")

                assert "Network error" in str(exc_info.value)

    def test_upload_fileobj_success(self, mock_settings, mock_boto3_client):
        """Test successful file object upload."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            with patch("boto3.client", return_value=mock_boto3_client):
                service = S3StorageService()

                fileobj = io.BytesIO(b"Test content")
                result = service.upload_fileobj(
                    fileobj=fileobj,
                    s3_key="uploads/test.txt",
                    content_type="text/plain",
                )

                assert result["bucket"] == "test-bucket"
                assert result["key"] == "uploads/test.txt"
                mock_boto3_client.upload_fileobj.assert_called_once()


class TestS3MultipartUpload:
    """Test multipart upload for large files."""

    def test_multipart_upload_called_for_large_files(self, mock_settings, mock_boto3_client, large_temp_file):
        """Test multipart upload is used for large files."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            with patch("boto3.client", return_value=mock_boto3_client):
                service = S3StorageService()

                # Mock file size to be > 100MB
                with patch.object(Path, "stat") as mock_stat:
                    mock_stat.return_value.st_size = 150 * 1024 * 1024  # 150 MB

                    result = service.upload_file(
                        file_path=large_temp_file,
                        s3_key="uploads/large.bin",
                    )

                    mock_boto3_client.create_multipart_upload.assert_called_once()
                    mock_boto3_client.complete_multipart_upload.assert_called_once()

    def test_multipart_upload_aborts_on_failure(self, mock_settings, mock_boto3_client, large_temp_file):
        """Test multipart upload aborts on failure."""
        mock_boto3_client.upload_part.side_effect = Exception("Part upload failed")

        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            with patch("boto3.client", return_value=mock_boto3_client):
                service = S3StorageService()

                with patch.object(Path, "stat") as mock_stat:
                    mock_stat.return_value.st_size = 150 * 1024 * 1024

                    with pytest.raises(S3UploadError):
                        service.upload_file(
                            file_path=large_temp_file,
                            s3_key="uploads/large.bin",
                        )

                    mock_boto3_client.abort_multipart_upload.assert_called_once()


class TestS3PresignedUrls:
    """Test presigned URL generation."""

    def test_generate_presigned_url_success(self, mock_settings, mock_boto3_client):
        """Test successful presigned URL generation."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            with patch("boto3.client", return_value=mock_boto3_client):
                service = S3StorageService()

                url = service.generate_presigned_url(s3_key="uploads/test.txt")

                assert "https://" in url
                mock_boto3_client.generate_presigned_url.assert_called_once()

    def test_generate_presigned_url_with_custom_expiry(self, mock_settings, mock_boto3_client):
        """Test presigned URL with custom expiration."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            with patch("boto3.client", return_value=mock_boto3_client):
                service = S3StorageService()

                service.generate_presigned_url(s3_key="test.txt", expires_in=7200)

                call_args = mock_boto3_client.generate_presigned_url.call_args
                assert call_args[1]["ExpiresIn"] == 7200

    def test_generate_presigned_url_with_response_headers(self, mock_settings, mock_boto3_client):
        """Test presigned URL with response headers."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            with patch("boto3.client", return_value=mock_boto3_client):
                service = S3StorageService()

                service.generate_presigned_url(
                    s3_key="test.txt",
                    response_content_type="application/pdf",
                    response_content_disposition='attachment; filename="doc.pdf"',
                )

                call_args = mock_boto3_client.generate_presigned_url.call_args
                params = call_args[1]["Params"]
                assert "Params" in params
                assert params["Params"]["ResponseContentType"] == "application/pdf"

    def test_generate_presigned_url_error(self, mock_settings, mock_boto3_client):
        """Test presigned URL generation error."""
        mock_boto3_client.generate_presigned_url.side_effect = Exception("URL generation failed")

        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            with patch("boto3.client", return_value=mock_boto3_client):
                service = S3StorageService()

                with pytest.raises(S3StorageError) as exc_info:
                    service.generate_presigned_url(s3_key="test.txt")

                assert "Failed to generate presigned URL" in str(exc_info.value)

    def test_generate_presigned_upload_url_success(self, mock_settings, mock_boto3_client):
        """Test presigned upload URL generation."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            with patch("boto3.client", return_value=mock_boto3_client):
                service = S3StorageService()

                result = service.generate_presigned_upload_url(
                    s3_key="uploads/new-file.txt",
                    content_type="text/plain",
                )

                assert "url" in result
                assert "fields" in result
                mock_boto3_client.generate_presigned_post.assert_called_once()


class TestS3FileOperations:
    """Test S3 file operations (delete, exists, get_info)."""

    def test_delete_file_success(self, mock_settings, mock_boto3_client):
        """Test successful file deletion."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            with patch("boto3.client", return_value=mock_boto3_client):
                service = S3StorageService()

                result = service.delete_file(s3_key="uploads/test.txt")

                assert result is True
                mock_boto3_client.delete_object.assert_called_once_with(
                    Bucket="test-bucket",
                    Key="uploads/test.txt"
                )

    def test_delete_file_error(self, mock_settings, mock_boto3_client):
        """Test file deletion error."""
        mock_boto3_client.delete_object.side_effect = Exception("Delete failed")

        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            with patch("boto3.client", return_value=mock_boto3_client):
                service = S3StorageService()

                with pytest.raises(S3StorageError) as exc_info:
                    service.delete_file(s3_key="test.txt")

                assert "Failed to delete" in str(exc_info.value)

    def test_file_exists_returns_true(self, mock_settings, mock_boto3_client):
        """Test file_exists returns True for existing file."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            with patch("boto3.client", return_value=mock_boto3_client):
                service = S3StorageService()

                result = service.file_exists(s3_key="uploads/test.txt")

                assert result is True
                mock_boto3_client.head_object.assert_called()

    def test_file_exists_returns_false_for_missing(self, mock_settings, mock_boto3_client):
        """Test file_exists returns False for missing file."""
        # Create a proper ClientError mock
        error_response = {"Error": {"Code": "404", "Message": "Not Found"}}
        client_error = type("ClientError", (Exception,), {"response": error_response})()
        mock_boto3_client.head_object.side_effect = client_error
        mock_boto3_client.exceptions.ClientError = type(client_error)

        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            with patch("boto3.client", return_value=mock_boto3_client):
                service = S3StorageService()

                result = service.file_exists(s3_key="nonexistent.txt")

                assert result is False

    def test_get_file_info_success(self, mock_settings, mock_boto3_client):
        """Test get_file_info returns file metadata."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            with patch("boto3.client", return_value=mock_boto3_client):
                service = S3StorageService()

                result = service.get_file_info(s3_key="uploads/test.txt")

                assert result["key"] == "uploads/test.txt"
                assert result["size_bytes"] == 1024
                assert result["content_type"] == "application/octet-stream"
                assert result["storage_class"] == "STANDARD"

    def test_get_file_info_returns_none_for_missing(self, mock_settings, mock_boto3_client):
        """Test get_file_info returns None for missing file."""
        error_response = {"Error": {"Code": "404", "Message": "Not Found"}}
        client_error = type("ClientError", (Exception,), {"response": error_response})()
        mock_boto3_client.head_object.side_effect = client_error
        mock_boto3_client.exceptions.ClientError = type(client_error)

        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            with patch("boto3.client", return_value=mock_boto3_client):
                service = S3StorageService()

                result = service.get_file_info(s3_key="nonexistent.txt")

                assert result is None


class TestStorageClassNormalization:
    """Test storage class normalization."""

    def test_normalize_standard(self, mock_settings):
        """Test standard storage class."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            service = S3StorageService()
            assert service._normalize_storage_class("standard") == "STANDARD"
            assert service._normalize_storage_class("STANDARD") == "STANDARD"

    def test_normalize_archive(self, mock_settings):
        """Test archive storage class maps to GLACIER."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            service = S3StorageService()
            assert service._normalize_storage_class("archive") == "GLACIER"

    def test_normalize_cold(self, mock_settings):
        """Test cold storage class maps to GLACIER_IR."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            service = S3StorageService()
            assert service._normalize_storage_class("cold") == "GLACIER_IR"

    def test_normalize_intelligent(self, mock_settings):
        """Test intelligent storage class."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            service = S3StorageService()
            assert service._normalize_storage_class("intelligent") == "INTELLIGENT_TIERING"

    def test_normalize_infrequent(self, mock_settings):
        """Test infrequent access storage class."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            service = S3StorageService()
            assert service._normalize_storage_class("infrequent") == "STANDARD_IA"

    def test_normalize_unknown_uppercase(self, mock_settings):
        """Test unknown storage class is uppercased."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            service = S3StorageService()
            assert service._normalize_storage_class("custom_class") == "CUSTOM_CLASS"


class TestFileHashComputation:
    """Test file hash computation."""

    def test_compute_file_hash(self, mock_settings, temp_file):
        """Test SHA-256 hash computation."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            service = S3StorageService()

            # Compute expected hash
            content = temp_file.read_bytes()
            expected_hash = hashlib.sha256(content).hexdigest()

            result = service._compute_file_hash(temp_file)

            assert result == expected_hash
            assert len(result) == 64  # SHA-256 hex digest length


class TestS3ServiceSingleton:
    """Test singleton pattern for S3 service."""

    def test_get_s3_service_returns_same_instance(self, mock_settings):
        """Test get_s3_service returns singleton."""
        # Reset singleton
        import api.services.cloud_storage_s3 as s3_module
        s3_module._s3_service = None

        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            service1 = get_s3_service()
            service2 = get_s3_service()

            assert service1 is service2

    def test_get_s3_service_creates_new_instance(self, mock_settings):
        """Test get_s3_service creates instance when none exists."""
        import api.services.cloud_storage_s3 as s3_module
        s3_module._s3_service = None

        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            service = get_s3_service()

            assert service is not None
            assert isinstance(service, S3StorageService)


class TestS3UploadWithDifferentStorageClasses:
    """Test uploads with different storage classes."""

    @pytest.mark.parametrize("storage_class,expected", [
        ("standard", "STANDARD"),
        ("archive", "GLACIER"),
        ("cold", "GLACIER_IR"),
        ("intelligent", "INTELLIGENT_TIERING"),
        ("infrequent", "STANDARD_IA"),
    ])
    def test_upload_with_storage_class(
        self, mock_settings, mock_boto3_client, temp_file, storage_class, expected
    ):
        """Test upload with different storage classes."""
        with patch(SETTINGS_PATCH_PATH, return_value=mock_settings):
            with patch("boto3.client", return_value=mock_boto3_client):
                service = S3StorageService()

                result = service.upload_file(
                    file_path=temp_file,
                    s3_key="test.txt",
                    storage_class=storage_class,
                )

                assert result["storage_class"] == expected

                call_args = mock_boto3_client.upload_file.call_args
                extra_args = call_args[1]["ExtraArgs"]
                assert extra_args["StorageClass"] == expected


class TestS3IAMRoleSupport:
    """Test IAM role support (no explicit credentials)."""

    def test_client_created_without_explicit_credentials(self, mock_boto3_client):
        """Test client creation without explicit credentials uses IAM role."""
        settings = Mock()
        settings.cloud_storage_enabled = True
        settings.cloud_storage_provider = "s3"
        settings.s3_bucket_name = "test-bucket"
        settings.s3_region = "us-west-2"
        settings.s3_access_key_id = ""  # Empty = use IAM role
        settings.s3_secret_access_key = ""
        settings.s3_endpoint_url = ""
        settings.s3_presigned_url_expiry_seconds = 3600

        with patch(SETTINGS_PATCH_PATH, return_value=settings):
            with patch("boto3.client", return_value=mock_boto3_client) as mock_boto:
                service = S3StorageService()
                service._get_client()

                call_kwargs = mock_boto.call_args[1]
                # Should NOT have explicit credentials
                assert "aws_access_key_id" not in call_kwargs
                assert "aws_secret_access_key" not in call_kwargs
