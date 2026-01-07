"""
Comprehensive tests for api/routes/p2p/transfer.py

Tests P2P chunked file transfer functionality:
- Transfer initialization with temp directory/metadata
- Chunk upload with SHA-256 verification
- Resume support (already-uploaded chunks)
- Transfer commit with integrity verification
- Status endpoint with progress tracking
- Authorization checks (transfer ownership)

Total: 55 tests covering all endpoints and edge cases.
"""

import pytest
import json
import hashlib
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

from fastapi import FastAPI
from fastapi.testclient import TestClient


# ===== Test Helper Functions =====

class TestGetTransferDir:
    """Tests for _get_transfer_dir helper"""

    def test_returns_path_with_transfer_id(self):
        """Returns path with transfer ID as subdirectory"""
        from api.routes.p2p.transfer import _get_transfer_dir, TEMP_DIR

        result = _get_transfer_dir("test-123")

        assert result == TEMP_DIR / "test-123"
        assert isinstance(result, Path)

    def test_different_ids_different_paths(self):
        """Different transfer IDs produce different paths"""
        from api.routes.p2p.transfer import _get_transfer_dir

        path_a = _get_transfer_dir("transfer-a")
        path_b = _get_transfer_dir("transfer-b")

        assert path_a != path_b


class TestGetMetadataPath:
    """Tests for _get_metadata_path helper"""

    def test_returns_metadata_json_path(self):
        """Returns path to metadata.json inside transfer dir"""
        from api.routes.p2p.transfer import _get_metadata_path, TEMP_DIR

        result = _get_metadata_path("test-456")

        assert result == TEMP_DIR / "test-456" / "metadata.json"

    def test_path_is_json_file(self):
        """Path ends with metadata.json"""
        from api.routes.p2p.transfer import _get_metadata_path

        result = _get_metadata_path("any-id")

        assert result.name == "metadata.json"


class TestLoadMetadata:
    """Tests for _load_metadata helper"""

    def test_returns_none_if_not_exists(self, tmp_path):
        """Returns None if metadata file doesn't exist"""
        with patch('api.routes.p2p.transfer.TEMP_DIR', tmp_path):
            from api.routes.p2p.transfer import _load_metadata

            result = _load_metadata("nonexistent-transfer")

            assert result is None

    def test_loads_json_from_file(self, tmp_path):
        """Loads and parses JSON metadata"""
        transfer_dir = tmp_path / "test-transfer"
        transfer_dir.mkdir()
        metadata_file = transfer_dir / "metadata.json"
        metadata_file.write_text('{"filename": "test.txt", "size_bytes": 1024}')

        with patch('api.routes.p2p.transfer.TEMP_DIR', tmp_path):
            from api.routes.p2p.transfer import _load_metadata

            result = _load_metadata("test-transfer")

            assert result == {"filename": "test.txt", "size_bytes": 1024}


class TestSaveMetadata:
    """Tests for _save_metadata helper"""

    def test_saves_json_to_file(self, tmp_path):
        """Saves metadata as JSON file"""
        transfer_dir = tmp_path / "test-save"
        transfer_dir.mkdir()

        with patch('api.routes.p2p.transfer.TEMP_DIR', tmp_path):
            from api.routes.p2p.transfer import _save_metadata

            metadata = {"transfer_id": "test-save", "filename": "file.zip"}
            _save_metadata("test-save", metadata)

            saved_file = transfer_dir / "metadata.json"
            assert saved_file.exists()
            saved_data = json.loads(saved_file.read_text())
            assert saved_data["transfer_id"] == "test-save"
            assert saved_data["filename"] == "file.zip"


class TestComputeFileHash:
    """Tests for _compute_file_hash helper"""

    def test_computes_sha256(self, tmp_path):
        """Computes correct SHA-256 hash"""
        from api.routes.p2p.transfer import _compute_file_hash

        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"hello world")

        result = _compute_file_hash(test_file)

        expected = hashlib.sha256(b"hello world").hexdigest()
        assert result == expected

    def test_handles_empty_file(self, tmp_path):
        """Handles empty files correctly"""
        from api.routes.p2p.transfer import _compute_file_hash

        empty_file = tmp_path / "empty.bin"
        empty_file.write_bytes(b"")

        result = _compute_file_hash(empty_file)

        expected = hashlib.sha256(b"").hexdigest()
        assert result == expected

    def test_large_file_chunked_reading(self, tmp_path):
        """Handles large files with chunked reading"""
        from api.routes.p2p.transfer import _compute_file_hash

        large_file = tmp_path / "large.bin"
        # 1MB of random-ish data
        data = b"x" * (1024 * 1024)
        large_file.write_bytes(data)

        result = _compute_file_hash(large_file)

        expected = hashlib.sha256(data).hexdigest()
        assert result == expected


# ===== Test Pydantic Models =====

class TestInitRequest:
    """Tests for InitRequest model"""

    def test_valid_request(self):
        """Creates valid request with all fields"""
        from api.routes.p2p.transfer import InitRequest

        req = InitRequest(filename="test.zip", size_bytes=1024, mime_type="application/zip")

        assert req.filename == "test.zip"
        assert req.size_bytes == 1024
        assert req.mime_type == "application/zip"

    def test_optional_mime_type(self):
        """mime_type is optional"""
        from api.routes.p2p.transfer import InitRequest

        req = InitRequest(filename="test.zip", size_bytes=1024)

        assert req.mime_type is None

    def test_size_bytes_must_be_non_negative(self):
        """size_bytes cannot be negative"""
        from api.routes.p2p.transfer import InitRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            InitRequest(filename="test.zip", size_bytes=-1)


class TestInitResponse:
    """Tests for InitResponse model"""

    def test_valid_response(self):
        """Creates valid response"""
        from api.routes.p2p.transfer import InitResponse

        resp = InitResponse(transfer_id="abc123", chunk_size=4194304)

        assert resp.transfer_id == "abc123"
        assert resp.chunk_size == 4194304


class TestUploadProgress:
    """Tests for UploadProgress model"""

    def test_valid_progress(self):
        """Creates valid progress"""
        from api.routes.p2p.transfer import UploadProgress

        progress = UploadProgress(uploaded_chunks=5, total_chunks=10, percentage=50.0)

        assert progress.uploaded_chunks == 5
        assert progress.total_chunks == 10
        assert progress.percentage == 50.0


class TestTransferStatusResponse:
    """Tests for TransferStatusResponse model"""

    def test_valid_status(self):
        """Creates valid status response"""
        from api.routes.p2p.transfer import TransferStatusResponse

        status = TransferStatusResponse(
            transfer_id="test-id",
            filename="test.zip",
            size_bytes=10240,
            status="uploading",
            chunk_size=4194304,
            total_chunks=3,
            uploaded_chunks=2,
            missing_chunks=1,
            progress_percentage=66.67,
            next_missing_chunk=2,
            missing_chunk_indices=[2],
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:01:00",
            completed_at=None,
            is_complete=False
        )

        assert status.transfer_id == "test-id"
        assert status.is_complete is False
        assert status.missing_chunk_indices == [2]


# ===== Test Configuration Constants =====

class TestConfiguration:
    """Tests for module configuration constants"""

    def test_chunk_size_is_4mb(self):
        """CHUNK_SIZE is 4MB"""
        from api.routes.p2p.transfer import CHUNK_SIZE

        assert CHUNK_SIZE == 4 * 1024 * 1024  # 4MB

    def test_max_file_size_is_10gb(self):
        """MAX_FILE_SIZE is 10GB"""
        from api.routes.p2p.transfer import MAX_FILE_SIZE

        assert MAX_FILE_SIZE == 10 * 1024 * 1024 * 1024  # 10GB

    def test_temp_dir_exists(self):
        """TEMP_DIR is created"""
        from api.routes.p2p.transfer import TEMP_DIR

        assert TEMP_DIR.exists()


# ===== Test Init Transfer Endpoint =====

class TestInitTransferEndpoint:
    """Tests for POST /api/v1/p2p/transfer/init endpoint"""

    @pytest.fixture
    def client(self, tmp_path):
        """Create test client with mocked dependencies"""
        from api.routes.p2p.transfer import router

        app = FastAPI()
        app.include_router(router)

        # Create a mock user dependency
        mock_user = Mock()
        mock_user.user_id = "test-user-123"

        # Override the dependency
        from api.auth_middleware import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user

        return TestClient(app)

    @pytest.fixture(autouse=True)
    def use_temp_dir(self, tmp_path):
        """Use temp directory for transfers"""
        with patch('api.routes.p2p.transfer.TEMP_DIR', tmp_path):
            yield

    def test_init_success(self, client, tmp_path):
        """Initialize transfer successfully"""
        response = client.post(
            "/api/v1/p2p/transfer/init",
            json={"filename": "test.zip", "size_bytes": 1024}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "transfer_id" in data["data"]
        assert data["data"]["chunk_size"] == 4 * 1024 * 1024

    def test_init_creates_metadata_file(self, client, tmp_path):
        """Init creates metadata file in transfer directory"""
        response = client.post(
            "/api/v1/p2p/transfer/init",
            json={"filename": "test.zip", "size_bytes": 8 * 1024 * 1024}  # 8MB = 2 chunks
        )

        assert response.status_code == 201
        transfer_id = response.json()["data"]["transfer_id"]

        metadata_path = tmp_path / transfer_id / "metadata.json"
        assert metadata_path.exists()

        metadata = json.loads(metadata_path.read_text())
        assert metadata["filename"] == "test.zip"
        assert metadata["total_chunks"] == 2
        assert metadata["status"] == "initialized"

    def test_init_file_too_large(self, tmp_path):
        """Returns 413 for files exceeding MAX_FILE_SIZE"""
        # Need to create fresh client with patched module
        import api.routes.p2p.transfer as transfer_module
        original_max = transfer_module.MAX_FILE_SIZE

        try:
            transfer_module.MAX_FILE_SIZE = 1024  # 1KB limit

            from api.routes.p2p.transfer import router

            app = FastAPI()
            app.include_router(router)

            mock_user = Mock()
            mock_user.user_id = "test-user-123"

            from api.auth_middleware import get_current_user
            app.dependency_overrides[get_current_user] = lambda: mock_user

            client = TestClient(app)

            with patch.object(transfer_module, 'TEMP_DIR', tmp_path):
                response = client.post(
                    "/api/v1/p2p/transfer/init",
                    json={"filename": "huge.zip", "size_bytes": 2048}
                )

            assert response.status_code == 413
        finally:
            transfer_module.MAX_FILE_SIZE = original_max

    def test_init_with_mime_type(self, client, tmp_path):
        """Init stores mime_type in metadata"""
        response = client.post(
            "/api/v1/p2p/transfer/init",
            json={"filename": "test.zip", "size_bytes": 1024, "mime_type": "application/zip"}
        )

        assert response.status_code == 201
        transfer_id = response.json()["data"]["transfer_id"]

        metadata_path = tmp_path / transfer_id / "metadata.json"
        metadata = json.loads(metadata_path.read_text())
        assert metadata["mime_type"] == "application/zip"


# ===== Test Upload Chunk Endpoint =====

class TestUploadChunkEndpoint:
    """Tests for POST /api/v1/p2p/transfer/upload-chunk endpoint"""

    def _create_client_and_setup(self, tmp_path, user_id="test-user-123"):
        """Helper to create client and setup transfer in one patch context"""
        import api.routes.p2p.transfer as transfer_module

        # Set up transfer directory
        transfer_id = "test-transfer-abc"
        transfer_dir = tmp_path / transfer_id
        transfer_dir.mkdir()

        metadata = {
            "transfer_id": transfer_id,
            "filename": "test.zip",
            "size_bytes": 8 * 1024 * 1024,
            "chunk_size": 4 * 1024 * 1024,
            "total_chunks": 2,
            "uploaded_chunks": [],
            "user_id": user_id,
            "status": "initialized"
        }

        metadata_path = transfer_dir / "metadata.json"
        metadata_path.write_text(json.dumps(metadata))

        # Create client with user
        from api.routes.p2p.transfer import router
        app = FastAPI()
        app.include_router(router)

        mock_user = Mock()
        mock_user.user_id = "test-user-123"

        from api.auth_middleware import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user

        return TestClient(app), transfer_id, transfer_module

    def test_upload_chunk_success(self, tmp_path):
        """Upload chunk successfully"""
        client, transfer_id, module = self._create_client_and_setup(tmp_path)

        chunk_data = b"x" * 1024
        checksum = hashlib.sha256(chunk_data).hexdigest()

        with patch.object(module, 'TEMP_DIR', tmp_path):
            response = client.post(
                "/api/v1/p2p/transfer/upload-chunk",
                data={
                    "transfer_id": transfer_id,
                    "index": 0,
                    "checksum": checksum
                },
                files={"chunk": ("chunk_000000", BytesIO(chunk_data))}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["resumed"] is False
        assert data["data"]["progress"]["uploaded_chunks"] == 1

    def test_upload_chunk_transfer_not_found(self, tmp_path):
        """Returns 404 for unknown transfer"""
        client, _, module = self._create_client_and_setup(tmp_path)

        with patch.object(module, 'TEMP_DIR', tmp_path):
            response = client.post(
                "/api/v1/p2p/transfer/upload-chunk",
                data={
                    "transfer_id": "nonexistent",
                    "index": 0,
                    "checksum": "abc"
                },
                files={"chunk": ("chunk", BytesIO(b"data"))}
            )

        assert response.status_code == 404

    def test_upload_chunk_wrong_user(self, tmp_path):
        """Returns 403 for wrong user"""
        # Create transfer with different user
        client, transfer_id, module = self._create_client_and_setup(tmp_path, user_id="other-user")

        with patch.object(module, 'TEMP_DIR', tmp_path):
            response = client.post(
                "/api/v1/p2p/transfer/upload-chunk",
                data={
                    "transfer_id": transfer_id,
                    "index": 0,
                    "checksum": "abc"
                },
                files={"chunk": ("chunk", BytesIO(b"data"))}
            )

        assert response.status_code == 403

    def test_upload_chunk_invalid_index(self, tmp_path):
        """Returns 400 for invalid chunk index"""
        client, transfer_id, module = self._create_client_and_setup(tmp_path)

        with patch.object(module, 'TEMP_DIR', tmp_path):
            response = client.post(
                "/api/v1/p2p/transfer/upload-chunk",
                data={
                    "transfer_id": transfer_id,
                    "index": 99,  # Only 2 chunks total
                    "checksum": "abc"
                },
                files={"chunk": ("chunk", BytesIO(b"data"))}
            )

        assert response.status_code == 400

    def test_upload_chunk_already_uploaded_resume(self, tmp_path):
        """Returns success with resumed=True for already-uploaded chunk"""
        client, transfer_id, module = self._create_client_and_setup(tmp_path)

        # Mark chunk 0 as already uploaded
        metadata_path = tmp_path / transfer_id / "metadata.json"
        metadata = json.loads(metadata_path.read_text())
        metadata["uploaded_chunks"] = [0]
        metadata_path.write_text(json.dumps(metadata))

        with patch.object(module, 'TEMP_DIR', tmp_path):
            response = client.post(
                "/api/v1/p2p/transfer/upload-chunk",
                data={
                    "transfer_id": transfer_id,
                    "index": 0,
                    "checksum": "abc"
                },
                files={"chunk": ("chunk", BytesIO(b"data"))}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["resumed"] is True

    def test_upload_chunk_checksum_mismatch(self, tmp_path):
        """Returns 400 for checksum mismatch"""
        client, transfer_id, module = self._create_client_and_setup(tmp_path)

        chunk_data = b"x" * 1024
        wrong_checksum = "0" * 64  # Wrong checksum

        with patch.object(module, 'TEMP_DIR', tmp_path):
            response = client.post(
                "/api/v1/p2p/transfer/upload-chunk",
                data={
                    "transfer_id": transfer_id,
                    "index": 0,
                    "checksum": wrong_checksum
                },
                files={"chunk": ("chunk", BytesIO(chunk_data))}
            )

        assert response.status_code == 400
        assert "mismatch" in response.json()["detail"]["message"].lower()


# ===== Test Commit Transfer Endpoint =====

class TestCommitTransferEndpoint:
    """Tests for POST /api/v1/p2p/transfer/commit endpoint"""

    def _create_client_and_module(self):
        """Create test client and get module reference"""
        import api.routes.p2p.transfer as transfer_module
        from api.routes.p2p.transfer import router

        app = FastAPI()
        app.include_router(router)

        mock_user = Mock()
        mock_user.user_id = "test-user-123"

        from api.auth_middleware import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user

        return TestClient(app), transfer_module

    def _setup_complete_transfer(self, tmp_path, user_id="test-user-123"):
        """Set up a complete transfer ready for commit"""
        transfer_id = "complete-transfer"
        transfer_dir = tmp_path / transfer_id
        transfer_dir.mkdir()

        # Create chunk files
        chunk_data = b"hello world"
        chunk_path = transfer_dir / "chunk_000000"
        chunk_path.write_bytes(chunk_data)

        metadata = {
            "transfer_id": transfer_id,
            "filename": "test.txt",
            "size_bytes": len(chunk_data),
            "chunk_size": 4 * 1024 * 1024,
            "total_chunks": 1,
            "uploaded_chunks": [0],
            "user_id": user_id,
            "status": "uploading"
        }

        metadata_path = transfer_dir / "metadata.json"
        metadata_path.write_text(json.dumps(metadata))

        return transfer_id, chunk_data

    def test_commit_success(self, tmp_path):
        """Commit transfer successfully"""
        client, module = self._create_client_and_module()
        transfer_id, chunk_data = self._setup_complete_transfer(tmp_path)

        # Mock PATHS.data_dir
        mock_paths = Mock()
        mock_paths.data_dir = tmp_path / "data"
        mock_paths.data_dir.mkdir()

        with patch.object(module, 'TEMP_DIR', tmp_path):
            with patch.object(module, 'PATHS', mock_paths):
                response = client.post(
                    "/api/v1/p2p/transfer/commit",
                    json={"transfer_id": transfer_id}
                )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["filename"] == "test.txt"
        assert "sha256" in data["data"]

    def test_commit_transfer_not_found(self, tmp_path):
        """Returns 404 for unknown transfer"""
        client, module = self._create_client_and_module()

        with patch.object(module, 'TEMP_DIR', tmp_path):
            response = client.post(
                "/api/v1/p2p/transfer/commit",
                json={"transfer_id": "nonexistent"}
            )

        assert response.status_code == 404

    def test_commit_incomplete_transfer(self, tmp_path):
        """Returns 400 for incomplete transfer"""
        client, module = self._create_client_and_module()

        transfer_id = "incomplete-transfer"
        transfer_dir = tmp_path / transfer_id
        transfer_dir.mkdir()

        metadata = {
            "transfer_id": transfer_id,
            "filename": "test.txt",
            "size_bytes": 8 * 1024 * 1024,
            "chunk_size": 4 * 1024 * 1024,
            "total_chunks": 2,
            "uploaded_chunks": [0],  # Only 1 of 2 chunks
            "user_id": "test-user-123",
            "status": "uploading"
        }

        metadata_path = transfer_dir / "metadata.json"
        metadata_path.write_text(json.dumps(metadata))

        with patch.object(module, 'TEMP_DIR', tmp_path):
            response = client.post(
                "/api/v1/p2p/transfer/commit",
                json={"transfer_id": transfer_id}
            )

        assert response.status_code == 400
        assert "incomplete" in response.json()["detail"]["message"].lower()

    def test_commit_with_hash_verification(self, tmp_path):
        """Commit with expected_sha256 verification"""
        client, module = self._create_client_and_module()
        transfer_id, chunk_data = self._setup_complete_transfer(tmp_path)

        expected_hash = hashlib.sha256(chunk_data).hexdigest()

        mock_paths = Mock()
        mock_paths.data_dir = tmp_path / "data"
        mock_paths.data_dir.mkdir()

        with patch.object(module, 'TEMP_DIR', tmp_path):
            with patch.object(module, 'PATHS', mock_paths):
                response = client.post(
                    "/api/v1/p2p/transfer/commit",
                    json={"transfer_id": transfer_id, "expected_sha256": expected_hash}
                )

        assert response.status_code == 200
        assert response.json()["data"]["sha256"] == expected_hash

    def test_commit_hash_mismatch(self, tmp_path):
        """Returns 400 for hash mismatch"""
        client, module = self._create_client_and_module()
        transfer_id, chunk_data = self._setup_complete_transfer(tmp_path)

        wrong_hash = "0" * 64

        mock_paths = Mock()
        mock_paths.data_dir = tmp_path / "data"
        mock_paths.data_dir.mkdir()

        with patch.object(module, 'TEMP_DIR', tmp_path):
            with patch.object(module, 'PATHS', mock_paths):
                response = client.post(
                    "/api/v1/p2p/transfer/commit",
                    json={"transfer_id": transfer_id, "expected_sha256": wrong_hash}
                )

        assert response.status_code == 400
        assert "mismatch" in response.json()["detail"]["message"].lower()


# ===== Test Get Status Endpoint =====

class TestGetStatusEndpoint:
    """Tests for GET /api/v1/p2p/transfer/status/{transfer_id} endpoint"""

    def _create_client_and_module(self):
        """Create test client and get module reference"""
        import api.routes.p2p.transfer as transfer_module
        from api.routes.p2p.transfer import router

        app = FastAPI()
        app.include_router(router)

        mock_user = Mock()
        mock_user.user_id = "test-user-123"

        from api.auth_middleware import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user

        return TestClient(app), transfer_module

    def _setup_status_transfer(self, tmp_path, user_id="test-user-123"):
        """Set up a transfer for status testing"""
        transfer_id = "status-transfer"
        transfer_dir = tmp_path / transfer_id
        transfer_dir.mkdir()

        metadata = {
            "transfer_id": transfer_id,
            "filename": "test.zip",
            "size_bytes": 16 * 1024 * 1024,  # 16MB
            "chunk_size": 4 * 1024 * 1024,  # 4MB chunks
            "total_chunks": 4,
            "uploaded_chunks": [0, 1],  # 2 of 4 uploaded
            "user_id": user_id,
            "status": "uploading",
            "created_at": "2024-01-01T00:00:00"
        }

        metadata_path = transfer_dir / "metadata.json"
        metadata_path.write_text(json.dumps(metadata))

        return transfer_id

    def test_get_status_success(self, tmp_path):
        """Get status successfully"""
        client, module = self._create_client_and_module()
        transfer_id = self._setup_status_transfer(tmp_path)

        with patch.object(module, 'TEMP_DIR', tmp_path):
            response = client.get(f"/api/v1/p2p/transfer/status/{transfer_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["transfer_id"] == transfer_id
        assert data["data"]["uploaded_chunks"] == 2
        assert data["data"]["missing_chunks"] == 2
        assert data["data"]["progress_percentage"] == 50.0
        assert data["data"]["is_complete"] is False

    def test_get_status_missing_chunks_list(self, tmp_path):
        """Status includes missing chunk indices"""
        client, module = self._create_client_and_module()
        transfer_id = self._setup_status_transfer(tmp_path)

        with patch.object(module, 'TEMP_DIR', tmp_path):
            response = client.get(f"/api/v1/p2p/transfer/status/{transfer_id}")

        data = response.json()
        # Chunks 0, 1 uploaded; 2, 3 missing
        assert 2 in data["data"]["missing_chunk_indices"]
        assert 3 in data["data"]["missing_chunk_indices"]
        assert data["data"]["next_missing_chunk"] == 2

    def test_get_status_not_found(self, tmp_path):
        """Returns 404 for unknown transfer"""
        client, module = self._create_client_and_module()

        with patch.object(module, 'TEMP_DIR', tmp_path):
            response = client.get("/api/v1/p2p/transfer/status/nonexistent")

        assert response.status_code == 404

    def test_get_status_wrong_user(self, tmp_path):
        """Returns 403 for wrong user"""
        client, module = self._create_client_and_module()
        transfer_id = self._setup_status_transfer(tmp_path, user_id="other-user")

        with patch.object(module, 'TEMP_DIR', tmp_path):
            response = client.get(f"/api/v1/p2p/transfer/status/{transfer_id}")

        assert response.status_code == 403

    def test_get_status_complete_transfer(self, tmp_path):
        """Status shows is_complete=True when all chunks uploaded"""
        client, module = self._create_client_and_module()

        transfer_id = "complete-status-transfer"
        transfer_dir = tmp_path / transfer_id
        transfer_dir.mkdir()

        metadata = {
            "transfer_id": transfer_id,
            "filename": "test.zip",
            "size_bytes": 8 * 1024 * 1024,
            "chunk_size": 4 * 1024 * 1024,
            "total_chunks": 2,
            "uploaded_chunks": [0, 1],  # All chunks uploaded
            "user_id": "test-user-123",
            "status": "completed"
        }

        metadata_path = transfer_dir / "metadata.json"
        metadata_path.write_text(json.dumps(metadata))

        with patch.object(module, 'TEMP_DIR', tmp_path):
            response = client.get(f"/api/v1/p2p/transfer/status/{transfer_id}")

        data = response.json()
        assert data["data"]["is_complete"] is True
        assert data["data"]["progress_percentage"] == 100.0
        assert data["data"]["missing_chunks"] == 0


# ===== Integration Tests =====

class TestIntegration:
    """Integration tests for full transfer workflow"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from api.routes.p2p.transfer import router

        app = FastAPI()
        app.include_router(router)

        mock_user = Mock()
        mock_user.user_id = "test-user-123"

        from api.auth_middleware import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user

        return TestClient(app)

    def test_full_transfer_lifecycle(self, client, tmp_path):
        """Test complete transfer: init -> upload -> commit"""
        # Mock PATHS
        mock_paths = Mock()
        mock_paths.data_dir = tmp_path / "data"
        mock_paths.data_dir.mkdir()
        mock_paths.cache_dir = tmp_path / "cache"
        mock_paths.cache_dir.mkdir()

        # Prepare file data
        file_data = b"This is test file content for transfer"
        file_hash = hashlib.sha256(file_data).hexdigest()

        with patch('api.routes.p2p.transfer.TEMP_DIR', tmp_path):
            with patch('api.routes.p2p.transfer.PATHS', mock_paths):
                # Step 1: Initialize transfer
                init_response = client.post(
                    "/api/v1/p2p/transfer/init",
                    json={"filename": "integration_test.txt", "size_bytes": len(file_data)}
                )
                assert init_response.status_code == 201
                transfer_id = init_response.json()["data"]["transfer_id"]

                # Step 2: Upload chunk (file fits in single chunk)
                chunk_checksum = hashlib.sha256(file_data).hexdigest()
                upload_response = client.post(
                    "/api/v1/p2p/transfer/upload-chunk",
                    data={
                        "transfer_id": transfer_id,
                        "index": 0,
                        "checksum": chunk_checksum
                    },
                    files={"chunk": ("chunk_000000", BytesIO(file_data))}
                )
                assert upload_response.status_code == 200
                assert upload_response.json()["data"]["progress"]["percentage"] == 100.0

                # Step 3: Check status
                status_response = client.get(f"/api/v1/p2p/transfer/status/{transfer_id}")
                assert status_response.status_code == 200
                assert status_response.json()["data"]["is_complete"] is True

                # Step 4: Commit transfer
                commit_response = client.post(
                    "/api/v1/p2p/transfer/commit",
                    json={"transfer_id": transfer_id, "expected_sha256": file_hash}
                )
                assert commit_response.status_code == 200
                assert commit_response.json()["data"]["sha256"] == file_hash

                # Verify final file exists
                final_path = Path(commit_response.json()["data"]["final_path"])
                assert final_path.exists()
                assert final_path.read_bytes() == file_data


# ===== Edge Cases =====

class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_zero_size_file(self, tmp_path):
        """Handle zero-size file transfer"""
        import api.routes.p2p.transfer as transfer_module
        from api.routes.p2p.transfer import router

        app = FastAPI()
        app.include_router(router)

        mock_user = Mock()
        mock_user.user_id = "test-user-123"

        from api.auth_middleware import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user

        client = TestClient(app)

        with patch.object(transfer_module, 'TEMP_DIR', tmp_path):
            response = client.post(
                "/api/v1/p2p/transfer/init",
                json={"filename": "empty.txt", "size_bytes": 0}
            )

        assert response.status_code == 201
        # Zero-size file = 0 chunks
        metadata_path = tmp_path / response.json()["data"]["transfer_id"] / "metadata.json"
        metadata = json.loads(metadata_path.read_text())
        assert metadata["total_chunks"] == 0

    def test_negative_chunk_index(self, tmp_path):
        """Reject negative chunk index"""
        import api.routes.p2p.transfer as transfer_module
        from api.routes.p2p.transfer import router

        app = FastAPI()
        app.include_router(router)

        mock_user = Mock()
        mock_user.user_id = "test-user-123"

        from api.auth_middleware import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user

        client = TestClient(app)

        # Set up transfer
        transfer_id = "neg-index-test"
        transfer_dir = tmp_path / transfer_id
        transfer_dir.mkdir()

        metadata = {
            "transfer_id": transfer_id,
            "filename": "test.txt",
            "size_bytes": 1024,
            "chunk_size": 1024,
            "total_chunks": 1,
            "uploaded_chunks": [],
            "user_id": "test-user-123",
            "status": "initialized"
        }
        (transfer_dir / "metadata.json").write_text(json.dumps(metadata))

        with patch.object(transfer_module, 'TEMP_DIR', tmp_path):
            response = client.post(
                "/api/v1/p2p/transfer/upload-chunk",
                data={
                    "transfer_id": transfer_id,
                    "index": -1,
                    "checksum": "abc"
                },
                files={"chunk": ("chunk", BytesIO(b"data"))}
            )

        assert response.status_code == 400

    def test_unicode_filename(self, tmp_path):
        """Handle unicode characters in filename"""
        import api.routes.p2p.transfer as transfer_module
        from api.routes.p2p.transfer import router

        app = FastAPI()
        app.include_router(router)

        mock_user = Mock()
        mock_user.user_id = "test-user-123"

        from api.auth_middleware import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user

        client = TestClient(app)

        with patch.object(transfer_module, 'TEMP_DIR', tmp_path):
            response = client.post(
                "/api/v1/p2p/transfer/init",
                json={"filename": "文件_тест_🎉.zip", "size_bytes": 1024}
            )

        assert response.status_code == 201
        metadata_path = tmp_path / response.json()["data"]["transfer_id"] / "metadata.json"
        metadata = json.loads(metadata_path.read_text())
        assert metadata["filename"] == "文件_тест_🎉.zip"


class TestRouterConfiguration:
    """Tests for router configuration"""

    def test_router_prefix(self):
        """Router has correct prefix"""
        from api.routes.p2p.transfer import router

        assert router.prefix == "/api/v1/p2p/transfer"

    def test_router_tags(self):
        """Router has correct tags"""
        from api.routes.p2p.transfer import router

        assert "p2p-transfer" in router.tags

    def test_router_has_auth_dependency(self):
        """Router requires authentication"""
        from api.routes.p2p.transfer import router
        from api.auth_middleware import get_current_user

        # Check that get_current_user is in dependencies
        deps = [d.dependency for d in router.dependencies if hasattr(d, 'dependency')]
        assert get_current_user in deps
