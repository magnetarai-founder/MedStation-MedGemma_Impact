"""
Tests for MagnetarCloud Storage Service

Tests cover:
- Upload initialization
- Chunk upload with hash verification
- Upload commit and assembly
- Upload status tracking
- Download initialization
- File listing and deletion
- Air-gap mode blocking
- Error handling
"""

import pytest
import json
import hashlib
import io
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, UTC
from fastapi import status
from fastapi.testclient import TestClient

import sys
from pathlib import Path
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))
sys.path.insert(0, str(backend_root / "api"))


# ===== Test Fixtures =====

@pytest.fixture
def mock_user():
    """Create a mock authenticated user dict"""
    return {
        "user_id": "test-user-storage-123",
        "username": "storageuser",
        "device_id": "test-device-storage-456",
        "created_at": "2024-12-01T00:00:00"
    }


@pytest.fixture
def other_user():
    """Create another user for ownership tests"""
    return {
        "user_id": "other-user-999",
        "username": "otheruser",
        "device_id": "other-device-888",
        "created_at": "2024-12-01T00:00:00"
    }


@pytest.fixture
def test_client(mock_user, tmp_path):
    """Create a test client with mocked authentication and temp paths"""
    from fastapi import FastAPI
    from api.auth_middleware import get_current_user

    # Patch paths before importing the module
    mock_paths = MagicMock()
    mock_paths.cache_dir = tmp_path / "cache"
    mock_paths.cache_dir.mkdir(parents=True, exist_ok=True)

    with patch('api.routes.cloud_storage.PATHS', mock_paths):
        with patch('api.routes.cloud_storage.TEMP_DIR', tmp_path / "uploads"):
            (tmp_path / "uploads").mkdir(parents=True, exist_ok=True)

            import importlib
            import api.routes.cloud_storage as storage_module
            importlib.reload(storage_module)

            app = FastAPI()
            app.include_router(storage_module.router)
            app.dependency_overrides[get_current_user] = lambda: mock_user

            yield TestClient(app)


@pytest.fixture
def test_client_airgap(mock_user, tmp_path):
    """Create a test client with air-gap mode enabled"""
    from fastapi import FastAPI
    from api.auth_middleware import get_current_user

    mock_paths = MagicMock()
    mock_paths.cache_dir = tmp_path / "cache"
    mock_paths.cache_dir.mkdir(parents=True, exist_ok=True)

    with patch('api.config.is_airgap_mode', return_value=True):
        with patch('api.routes.cloud_storage.PATHS', mock_paths):
            with patch('api.routes.cloud_storage.TEMP_DIR', tmp_path / "uploads"):
                (tmp_path / "uploads").mkdir(parents=True, exist_ok=True)

                import importlib
                import api.routes.cloud_storage as storage_module
                importlib.reload(storage_module)

                app = FastAPI()
                app.include_router(storage_module.router)
                app.dependency_overrides[get_current_user] = lambda: mock_user

                yield TestClient(app)


# ===== Upload Init Tests =====

class TestUploadInit:
    """Tests for upload initialization"""

    def test_init_upload_success(self, test_client):
        """Should initialize an upload session"""
        response = test_client.post(
            "/api/v1/cloud/storage/upload/init",
            json={
                "filename": "test_file.txt",
                "size_bytes": 1024,
                "content_type": "text/plain"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "upload_id" in data
        assert data["upload_id"].startswith("csu_")
        assert data["chunk_size"] == 4 * 1024 * 1024  # 4 MB
        assert data["total_chunks"] == 1  # 1KB file = 1 chunk
        assert "expires_at" in data
        assert data["storage_class"] == "standard"

    def test_init_upload_large_file(self, test_client):
        """Should calculate correct chunk count for large files"""
        file_size = 10 * 1024 * 1024  # 10 MB
        chunk_size = 4 * 1024 * 1024  # 4 MB

        response = test_client.post(
            "/api/v1/cloud/storage/upload/init",
            json={
                "filename": "large_file.bin",
                "size_bytes": file_size
            }
        )

        assert response.status_code == 200
        data = response.json()
        # 10 MB / 4 MB = 3 chunks (ceil division)
        assert data["total_chunks"] == 3

    def test_init_upload_with_custom_metadata(self, test_client):
        """Should accept custom metadata"""
        response = test_client.post(
            "/api/v1/cloud/storage/upload/init",
            json={
                "filename": "doc.pdf",
                "size_bytes": 2048,
                "content_type": "application/pdf",
                "storage_class": "archive",
                "encrypt": True,
                "metadata": {"project": "test", "version": "1.0"}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["storage_class"] == "archive"

    def test_init_upload_requires_filename(self, test_client):
        """Should require filename"""
        response = test_client.post(
            "/api/v1/cloud/storage/upload/init",
            json={"size_bytes": 1024}
        )
        assert response.status_code == 422

    def test_init_upload_requires_size(self, test_client):
        """Should require size_bytes"""
        response = test_client.post(
            "/api/v1/cloud/storage/upload/init",
            json={"filename": "test.txt"}
        )
        assert response.status_code == 422

    def test_init_upload_rejects_zero_size(self, test_client):
        """Should reject zero-size files"""
        response = test_client.post(
            "/api/v1/cloud/storage/upload/init",
            json={"filename": "empty.txt", "size_bytes": 0}
        )
        assert response.status_code == 422

    def test_init_upload_rejects_oversized_file(self, test_client):
        """Should reject files larger than 5 GB"""
        response = test_client.post(
            "/api/v1/cloud/storage/upload/init",
            json={
                "filename": "huge.bin",
                "size_bytes": 6 * 1024 * 1024 * 1024  # 6 GB
            }
        )
        assert response.status_code == 422


# ===== Chunk Upload Tests =====

class TestChunkUpload:
    """Tests for chunk upload"""

    def test_upload_chunk_success(self, test_client):
        """Should upload a chunk with valid hash"""
        # Initialize upload
        init_resp = test_client.post(
            "/api/v1/cloud/storage/upload/init",
            json={"filename": "test.txt", "size_bytes": 100}
        )
        upload_id = init_resp.json()["upload_id"]

        # Create chunk data and hash
        chunk_data = b"Hello, World! This is test content."
        chunk_hash = hashlib.sha256(chunk_data).hexdigest()

        # Upload chunk
        response = test_client.post(
            "/api/v1/cloud/storage/upload/chunk",
            data={
                "upload_id": upload_id,
                "chunk_index": 0,
                "chunk_hash": chunk_hash
            },
            files={"chunk_data": ("chunk", io.BytesIO(chunk_data))}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["chunk_index"] == 0
        assert data["verified"] is True
        assert data["chunks_uploaded"] == 1

    def test_upload_chunk_hash_mismatch(self, test_client):
        """Should reject chunk with wrong hash"""
        # Initialize upload
        init_resp = test_client.post(
            "/api/v1/cloud/storage/upload/init",
            json={"filename": "test.txt", "size_bytes": 100}
        )
        upload_id = init_resp.json()["upload_id"]

        chunk_data = b"Hello, World!"
        wrong_hash = "a" * 64  # Invalid hash

        response = test_client.post(
            "/api/v1/cloud/storage/upload/chunk",
            data={
                "upload_id": upload_id,
                "chunk_index": 0,
                "chunk_hash": wrong_hash
            },
            files={"chunk_data": ("chunk", io.BytesIO(chunk_data))}
        )

        assert response.status_code == 400
        assert "hash_mismatch" in response.json()["detail"]["error"]

    def test_upload_chunk_not_found(self, test_client):
        """Should return 404 for nonexistent upload"""
        chunk_data = b"test"
        chunk_hash = hashlib.sha256(chunk_data).hexdigest()

        response = test_client.post(
            "/api/v1/cloud/storage/upload/chunk",
            data={
                "upload_id": "nonexistent_upload_id",
                "chunk_index": 0,
                "chunk_hash": chunk_hash
            },
            files={"chunk_data": ("chunk", io.BytesIO(chunk_data))}
        )

        assert response.status_code == 404

    def test_upload_chunk_invalid_index(self, test_client):
        """Should reject chunk with out-of-bounds index"""
        init_resp = test_client.post(
            "/api/v1/cloud/storage/upload/init",
            json={"filename": "test.txt", "size_bytes": 100}  # 1 chunk
        )
        upload_id = init_resp.json()["upload_id"]

        chunk_data = b"test"
        chunk_hash = hashlib.sha256(chunk_data).hexdigest()

        # Try to upload chunk 5 when only 1 is expected
        response = test_client.post(
            "/api/v1/cloud/storage/upload/chunk",
            data={
                "upload_id": upload_id,
                "chunk_index": 5,
                "chunk_hash": chunk_hash
            },
            files={"chunk_data": ("chunk", io.BytesIO(chunk_data))}
        )

        assert response.status_code == 400
        assert "invalid_chunk" in response.json()["detail"]["error"]


# ===== Upload Status Tests =====

class TestUploadStatus:
    """Tests for upload status tracking"""

    def test_get_upload_status(self, test_client):
        """Should return upload status"""
        # Initialize upload
        init_resp = test_client.post(
            "/api/v1/cloud/storage/upload/init",
            json={"filename": "test.txt", "size_bytes": 100}
        )
        upload_id = init_resp.json()["upload_id"]

        response = test_client.get(
            f"/api/v1/cloud/storage/upload/status/{upload_id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["upload_id"] == upload_id
        assert data["filename"] == "test.txt"
        assert data["status"] == "pending"
        assert data["chunks_uploaded"] == 0

    def test_get_upload_status_after_chunk(self, test_client):
        """Should update status after chunk upload"""
        # Initialize upload
        init_resp = test_client.post(
            "/api/v1/cloud/storage/upload/init",
            json={"filename": "test.txt", "size_bytes": 100}
        )
        upload_id = init_resp.json()["upload_id"]

        # Upload a chunk
        chunk_data = b"test content"
        chunk_hash = hashlib.sha256(chunk_data).hexdigest()
        test_client.post(
            "/api/v1/cloud/storage/upload/chunk",
            data={
                "upload_id": upload_id,
                "chunk_index": 0,
                "chunk_hash": chunk_hash
            },
            files={"chunk_data": ("chunk", io.BytesIO(chunk_data))}
        )

        response = test_client.get(
            f"/api/v1/cloud/storage/upload/status/{upload_id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "uploading"
        assert data["chunks_uploaded"] == 1
        assert data["progress_percent"] == 100.0

    def test_get_upload_status_not_found(self, test_client):
        """Should return 404 for nonexistent upload"""
        response = test_client.get(
            "/api/v1/cloud/storage/upload/status/nonexistent"
        )
        assert response.status_code == 404


# ===== Upload Commit Tests =====

class TestUploadCommit:
    """Tests for upload commit"""

    def test_commit_upload_success(self, test_client):
        """Should commit upload after all chunks"""
        # Initialize upload
        init_resp = test_client.post(
            "/api/v1/cloud/storage/upload/init",
            json={"filename": "test.txt", "size_bytes": 12}
        )
        upload_id = init_resp.json()["upload_id"]

        # Upload chunk
        chunk_data = b"test content"
        chunk_hash = hashlib.sha256(chunk_data).hexdigest()
        test_client.post(
            "/api/v1/cloud/storage/upload/chunk",
            data={
                "upload_id": upload_id,
                "chunk_index": 0,
                "chunk_hash": chunk_hash
            },
            files={"chunk_data": ("chunk", io.BytesIO(chunk_data))}
        )

        # Commit
        final_hash = hashlib.sha256(chunk_data).hexdigest()
        response = test_client.post(
            "/api/v1/cloud/storage/upload/commit",
            data={
                "upload_id": upload_id,
                "final_hash": final_hash
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "file_id" in data
        assert data["file_id"].startswith("csf_")
        assert data["filename"] == "test.txt"
        assert data["sha256"] == final_hash

    def test_commit_upload_missing_chunks(self, test_client):
        """Should reject commit with missing chunks"""
        # Initialize upload for 10 MB (3 chunks)
        init_resp = test_client.post(
            "/api/v1/cloud/storage/upload/init",
            json={"filename": "large.bin", "size_bytes": 10 * 1024 * 1024}
        )
        upload_id = init_resp.json()["upload_id"]

        # Only upload 1 chunk (should have 3)
        chunk_data = b"x" * 1000
        chunk_hash = hashlib.sha256(chunk_data).hexdigest()
        test_client.post(
            "/api/v1/cloud/storage/upload/chunk",
            data={
                "upload_id": upload_id,
                "chunk_index": 0,
                "chunk_hash": chunk_hash
            },
            files={"chunk_data": ("chunk", io.BytesIO(chunk_data))}
        )

        # Try to commit
        response = test_client.post(
            "/api/v1/cloud/storage/upload/commit",
            data={
                "upload_id": upload_id,
                "final_hash": "a" * 64
            }
        )

        assert response.status_code == 400
        assert "incomplete_upload" in response.json()["detail"]["error"]

    def test_commit_upload_hash_mismatch(self, test_client):
        """Should reject commit with wrong final hash"""
        # Initialize and upload
        init_resp = test_client.post(
            "/api/v1/cloud/storage/upload/init",
            json={"filename": "test.txt", "size_bytes": 12}
        )
        upload_id = init_resp.json()["upload_id"]

        chunk_data = b"test content"
        chunk_hash = hashlib.sha256(chunk_data).hexdigest()
        test_client.post(
            "/api/v1/cloud/storage/upload/chunk",
            data={
                "upload_id": upload_id,
                "chunk_index": 0,
                "chunk_hash": chunk_hash
            },
            files={"chunk_data": ("chunk", io.BytesIO(chunk_data))}
        )

        # Wrong final hash
        response = test_client.post(
            "/api/v1/cloud/storage/upload/commit",
            data={
                "upload_id": upload_id,
                "final_hash": "wrong" + "a" * 59
            }
        )

        assert response.status_code == 400
        assert "final_hash_mismatch" in response.json()["detail"]["error"]


# ===== File Listing Tests =====

class TestFileListing:
    """Tests for file listing"""

    def test_list_files_returns_valid_structure(self, test_client):
        """Should return files list with valid structure"""
        response = test_client.get("/api/v1/cloud/storage/files")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["files"], list)
        assert isinstance(data["total"], int)
        # Each file should have required fields
        for f in data["files"]:
            assert "file_id" in f
            assert "filename" in f
            assert "size_bytes" in f

    def test_list_files_after_upload(self, test_client):
        """Should list uploaded files"""
        # Upload a file
        init_resp = test_client.post(
            "/api/v1/cloud/storage/upload/init",
            json={"filename": "uploaded.txt", "size_bytes": 12}
        )
        upload_id = init_resp.json()["upload_id"]

        chunk_data = b"test content"
        chunk_hash = hashlib.sha256(chunk_data).hexdigest()
        test_client.post(
            "/api/v1/cloud/storage/upload/chunk",
            data={
                "upload_id": upload_id,
                "chunk_index": 0,
                "chunk_hash": chunk_hash
            },
            files={"chunk_data": ("chunk", io.BytesIO(chunk_data))}
        )

        final_hash = hashlib.sha256(chunk_data).hexdigest()
        test_client.post(
            "/api/v1/cloud/storage/upload/commit",
            data={"upload_id": upload_id, "final_hash": final_hash}
        )

        # List files
        response = test_client.get("/api/v1/cloud/storage/files")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(f["filename"] == "uploaded.txt" for f in data["files"])


# ===== File Deletion Tests =====

class TestFileDeletion:
    """Tests for file deletion"""

    def test_delete_file_success(self, test_client):
        """Should delete an uploaded file"""
        # Upload a file first
        init_resp = test_client.post(
            "/api/v1/cloud/storage/upload/init",
            json={"filename": "to_delete.txt", "size_bytes": 12}
        )
        upload_id = init_resp.json()["upload_id"]

        chunk_data = b"test content"
        chunk_hash = hashlib.sha256(chunk_data).hexdigest()
        test_client.post(
            "/api/v1/cloud/storage/upload/chunk",
            data={
                "upload_id": upload_id,
                "chunk_index": 0,
                "chunk_hash": chunk_hash
            },
            files={"chunk_data": ("chunk", io.BytesIO(chunk_data))}
        )

        commit_resp = test_client.post(
            "/api/v1/cloud/storage/upload/commit",
            data={"upload_id": upload_id, "final_hash": chunk_hash}
        )
        file_id = commit_resp.json()["file_id"]

        # Delete file
        response = test_client.delete(f"/api/v1/cloud/storage/files/{file_id}")

        assert response.status_code == 200

        # Verify deleted
        list_resp = test_client.get("/api/v1/cloud/storage/files")
        assert not any(f["file_id"] == file_id for f in list_resp.json()["files"])

    def test_delete_file_not_found(self, test_client):
        """Should return 404 for nonexistent file"""
        response = test_client.delete("/api/v1/cloud/storage/files/nonexistent")
        assert response.status_code == 404


# ===== Download Tests =====

class TestDownload:
    """Tests for file download"""

    def test_init_download_success(self, test_client):
        """Should initialize download for existing file"""
        # Upload a file first
        init_resp = test_client.post(
            "/api/v1/cloud/storage/upload/init",
            json={"filename": "downloadable.txt", "size_bytes": 12}
        )
        upload_id = init_resp.json()["upload_id"]

        chunk_data = b"test content"
        chunk_hash = hashlib.sha256(chunk_data).hexdigest()
        test_client.post(
            "/api/v1/cloud/storage/upload/chunk",
            data={
                "upload_id": upload_id,
                "chunk_index": 0,
                "chunk_hash": chunk_hash
            },
            files={"chunk_data": ("chunk", io.BytesIO(chunk_data))}
        )

        commit_resp = test_client.post(
            "/api/v1/cloud/storage/upload/commit",
            data={"upload_id": upload_id, "final_hash": chunk_hash}
        )
        file_id = commit_resp.json()["file_id"]

        # Init download
        response = test_client.post(
            "/api/v1/cloud/storage/download/init",
            json={"file_id": file_id}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["file_id"] == file_id
        assert data["filename"] == "downloadable.txt"
        assert "download_url" in data
        assert "expires_at" in data

    def test_init_download_not_found(self, test_client):
        """Should return 404 for nonexistent file"""
        response = test_client.post(
            "/api/v1/cloud/storage/download/init",
            json={"file_id": "nonexistent_file_id"}
        )
        assert response.status_code == 404


# ===== Air-Gap Mode Tests =====

class TestAirGapMode:
    """Tests for air-gap mode blocking"""

    def test_upload_init_blocked_in_airgap(self, test_client_airgap):
        """Upload init should be blocked in air-gap mode"""
        response = test_client_airgap.post(
            "/api/v1/cloud/storage/upload/init",
            json={"filename": "test.txt", "size_bytes": 100}
        )
        assert response.status_code == 503

    def test_list_files_blocked_in_airgap(self, test_client_airgap):
        """File listing should be blocked in air-gap mode"""
        response = test_client_airgap.get("/api/v1/cloud/storage/files")
        assert response.status_code == 503


# ===== Integration Tests =====

class TestStorageIntegration:
    """Integration tests for complete upload/download workflows"""

    def test_full_upload_download_cycle(self, test_client):
        """Test complete upload and download cycle"""
        # 1. Initialize upload
        init_resp = test_client.post(
            "/api/v1/cloud/storage/upload/init",
            json={
                "filename": "integration_test.txt",
                "size_bytes": 20,
                "content_type": "text/plain"
            }
        )
        assert init_resp.status_code == 200
        upload_id = init_resp.json()["upload_id"]

        # 2. Upload chunk
        content = b"Integration test data"
        chunk_hash = hashlib.sha256(content).hexdigest()
        chunk_resp = test_client.post(
            "/api/v1/cloud/storage/upload/chunk",
            data={
                "upload_id": upload_id,
                "chunk_index": 0,
                "chunk_hash": chunk_hash
            },
            files={"chunk_data": ("chunk", io.BytesIO(content))}
        )
        assert chunk_resp.status_code == 200

        # 3. Commit upload
        commit_resp = test_client.post(
            "/api/v1/cloud/storage/upload/commit",
            data={"upload_id": upload_id, "final_hash": chunk_hash}
        )
        assert commit_resp.status_code == 200
        file_id = commit_resp.json()["file_id"]

        # 4. Verify in file list
        list_resp = test_client.get("/api/v1/cloud/storage/files")
        assert any(f["file_id"] == file_id for f in list_resp.json()["files"])

        # 5. Initialize download
        download_init_resp = test_client.post(
            "/api/v1/cloud/storage/download/init",
            json={"file_id": file_id}
        )
        assert download_init_resp.status_code == 200
        download_url = download_init_resp.json()["download_url"]

        # 6. Download file
        download_resp = test_client.get(download_url)
        assert download_resp.status_code == 200
        assert download_resp.content == content

        # 7. Delete file
        delete_resp = test_client.delete(f"/api/v1/cloud/storage/files/{file_id}")
        assert delete_resp.status_code == 200

        # 8. Verify deleted
        final_list = test_client.get("/api/v1/cloud/storage/files")
        assert not any(f["file_id"] == file_id for f in final_list.json()["files"])
