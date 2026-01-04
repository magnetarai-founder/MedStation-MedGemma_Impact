"""
Tests for P2P Chunked File Transfer

Tests the libp2p-based peer-to-peer file transfer functionality:
- Chunk hashing and verification
- Transfer initialization and progress tracking
- File sending and receiving logic
- Storage operations for transfers
"""

import asyncio
import hashlib
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from api.services.p2p_chat import files as file_ops
from api.services.p2p_chat import storage


# ===== Test Fixtures =====

@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test_p2p.db"
    storage.init_db(db_path)
    return db_path


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary test file."""
    file_path = tmp_path / "test_file.txt"
    # Create a 3MB file (3 chunks at 1MB each)
    content = b"x" * (3 * 1024 * 1024)
    file_path.write_bytes(content)
    return file_path


@pytest.fixture
def small_file(tmp_path):
    """Create a small test file (< 1 chunk)."""
    file_path = tmp_path / "small_file.txt"
    content = b"Hello, P2P file transfer!"
    file_path.write_bytes(content)
    return file_path


@pytest.fixture
def mock_service(temp_db, tmp_path):
    """Create a mock P2P service for testing."""
    service = MagicMock()
    service.db_path = temp_db
    service.peer_id = "QmTestPeer123"
    service.is_running = True
    service.host = MagicMock()
    return service


# ===== Hash Function Tests =====

class TestHashFunctions:
    """Test chunk and file hashing."""

    def test_compute_file_hash(self, small_file):
        """Test file hash computation."""
        expected_hash = hashlib.sha256(small_file.read_bytes()).hexdigest()
        actual_hash = file_ops.compute_file_hash(small_file)
        assert actual_hash == expected_hash

    def test_compute_chunk_hash(self):
        """Test chunk hash computation."""
        data = b"test chunk data"
        expected_hash = hashlib.sha256(data).hexdigest()
        actual_hash = file_ops.compute_chunk_hash(data)
        assert actual_hash == expected_hash

    def test_compute_file_hash_large_file(self, temp_file):
        """Test file hash computation for large files."""
        # Compute expected hash
        sha256 = hashlib.sha256()
        with open(temp_file, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        expected_hash = sha256.hexdigest()

        actual_hash = file_ops.compute_file_hash(temp_file)
        assert actual_hash == expected_hash


# ===== Transfer Initialization Tests =====

class TestTransferInitiation:
    """Test transfer initialization and metadata."""

    @pytest.mark.asyncio
    async def test_initiate_file_transfer(self, mock_service):
        """Test initiating a file transfer."""
        result = await file_ops.initiate_file_transfer(
            mock_service,
            file_name="test.txt",
            file_size=3 * 1024 * 1024,  # 3MB
            mime_type="text/plain",
            channel_id="channel-123",
            recipient_ids=["peer-1", "peer-2"]
        )

        assert "transfer_id" in result
        assert result["file_name"] == "test.txt"
        assert result["file_size"] == 3 * 1024 * 1024
        assert result["chunks_total"] == 3
        assert result["status"] == "initiated"

    @pytest.mark.asyncio
    async def test_initiate_small_file_transfer(self, mock_service):
        """Test initiating transfer for file smaller than chunk size."""
        result = await file_ops.initiate_file_transfer(
            mock_service,
            file_name="small.txt",
            file_size=1000,  # 1KB
            mime_type="text/plain",
            channel_id="channel-123",
            recipient_ids=["peer-1"]
        )

        assert result["chunks_total"] == 1

    @pytest.mark.asyncio
    async def test_get_transfer_status(self, mock_service):
        """Test getting transfer status."""
        # First initiate a transfer
        init_result = await file_ops.initiate_file_transfer(
            mock_service,
            file_name="test.txt",
            file_size=1024 * 1024,
            mime_type="text/plain",
            channel_id="channel-123",
            recipient_ids=["peer-1"]
        )

        # Get status
        status = await file_ops.get_transfer_status(
            mock_service, init_result["transfer_id"]
        )

        assert status is not None
        assert status["file_name"] == "test.txt"
        assert status["status"] == "active"


# ===== Storage Operations Tests =====

class TestStorageOperations:
    """Test storage layer operations."""

    def test_save_file_transfer(self, temp_db):
        """Test saving file transfer metadata."""
        storage.save_file_transfer(
            temp_db,
            transfer_id="transfer-123",
            file_name="test.txt",
            file_size=1024,
            mime_type="text/plain",
            sender_id="sender-1",
            channel_id="channel-1",
            recipient_ids=["peer-1", "peer-2"],
            chunks_total=1
        )

        transfer = storage.get_file_transfer(temp_db, "transfer-123")
        assert transfer is not None
        assert transfer["file_name"] == "test.txt"
        assert transfer["recipient_ids"] == ["peer-1", "peer-2"]

    def test_update_transfer_progress(self, temp_db):
        """Test updating transfer progress."""
        # Save initial transfer
        storage.save_file_transfer(
            temp_db,
            transfer_id="transfer-456",
            file_name="test.txt",
            file_size=3 * 1024 * 1024,
            mime_type="text/plain",
            sender_id="sender-1",
            channel_id="channel-1",
            recipient_ids=["peer-1"],
            chunks_total=3
        )

        # Update progress
        storage.update_file_transfer_progress(
            temp_db, "transfer-456", chunks_received=2, progress_percent=66.7
        )

        transfer = storage.get_file_transfer(temp_db, "transfer-456")
        assert transfer["chunks_received"] == 2
        assert transfer["progress_percent"] == 66.7

    def test_list_active_transfers(self, temp_db):
        """Test listing active transfers."""
        # Create multiple transfers
        storage.save_file_transfer(
            temp_db, "active-1", "file1.txt", 1024, "text/plain",
            "sender", "channel", ["peer"], 1
        )
        storage.save_file_transfer(
            temp_db, "active-2", "file2.txt", 2048, "text/plain",
            "sender", "channel", ["peer"], 2
        )

        # Complete one
        storage.update_file_transfer_progress(
            temp_db, "active-1", 1, 100.0, "completed"
        )

        # List active
        active = storage.list_active_transfers(temp_db)
        assert len(active) == 1
        assert active[0]["id"] == "active-2"

    def test_cancel_transfer(self, temp_db):
        """Test cancelling a transfer."""
        storage.save_file_transfer(
            temp_db, "cancel-me", "file.txt", 1024, "text/plain",
            "sender", "channel", ["peer"], 1
        )

        storage.cancel_transfer(temp_db, "cancel-me")

        transfer = storage.get_file_transfer(temp_db, "cancel-me")
        assert transfer["status"] == "cancelled"
        assert transfer["completed_at"] is not None

    def test_set_transfer_hash(self, temp_db):
        """Test setting file hash."""
        storage.save_file_transfer(
            temp_db, "hash-test", "file.txt", 1024, "text/plain",
            "sender", "channel", ["peer"], 1
        )

        storage.set_transfer_hash(temp_db, "hash-test", "abc123def456")

        transfer = storage.get_file_transfer(temp_db, "hash-test")
        assert transfer["file_hash"] == "abc123def456"

    def test_set_transfer_local_path(self, temp_db):
        """Test setting local path for received file."""
        storage.save_file_transfer(
            temp_db, "path-test", "file.txt", 1024, "text/plain",
            "sender", "channel", ["peer"], 1
        )

        storage.set_transfer_local_path(temp_db, "path-test", "/tmp/received/file.txt")

        transfer = storage.get_file_transfer(temp_db, "path-test")
        assert transfer["local_path"] == "/tmp/received/file.txt"


# ===== Chunk Handling Tests =====

class TestChunkHandling:
    """Test chunk receiving and verification."""

    @pytest.mark.asyncio
    async def test_handle_chunk_success(self, mock_service, tmp_path):
        """Test successful chunk handling."""
        # Setup transfer
        transfer_id = "chunk-test"
        storage.save_file_transfer(
            mock_service.db_path, transfer_id, "file.txt", 2048, "text/plain",
            "sender", "channel", ["peer"], 2
        )
        local_path = tmp_path / "receiving.txt"
        storage.set_transfer_local_path(mock_service.db_path, transfer_id, str(local_path))
        storage.set_transfer_hash(mock_service.db_path, transfer_id, "expected_hash")

        # Create chunk data
        chunk_data = b"test chunk content"
        chunk_hash = file_ops.compute_chunk_hash(chunk_data)

        chunk_header = {
            "transfer_id": transfer_id,
            "chunk_index": 0,
            "chunk_hash": chunk_hash,
            "is_last": False
        }

        # Handle chunk
        result = await file_ops.handle_chunk(mock_service, chunk_header, chunk_data)

        assert result["status"] == "ok"
        assert result["chunk_index"] == 0
        assert local_path.exists()
        assert local_path.read_bytes() == chunk_data

    @pytest.mark.asyncio
    async def test_handle_chunk_hash_mismatch(self, mock_service, tmp_path):
        """Test chunk rejection on hash mismatch."""
        transfer_id = "hash-mismatch"
        storage.save_file_transfer(
            mock_service.db_path, transfer_id, "file.txt", 1024, "text/plain",
            "sender", "channel", ["peer"], 1
        )
        local_path = tmp_path / "receiving.txt"
        storage.set_transfer_local_path(mock_service.db_path, transfer_id, str(local_path))

        chunk_data = b"actual data"
        chunk_header = {
            "transfer_id": transfer_id,
            "chunk_index": 0,
            "chunk_hash": "wrong_hash",
            "is_last": False
        }

        result = await file_ops.handle_chunk(mock_service, chunk_header, chunk_data)

        assert result["status"] == "error"
        assert result["error"] == "hash_mismatch"

    @pytest.mark.asyncio
    async def test_handle_chunk_unknown_transfer(self, mock_service):
        """Test chunk rejection for unknown transfer."""
        chunk_data = b"data"
        chunk_hash = file_ops.compute_chunk_hash(chunk_data)  # Use valid hash
        chunk_header = {
            "transfer_id": "nonexistent",
            "chunk_index": 0,
            "chunk_hash": chunk_hash,
            "is_last": False
        }

        result = await file_ops.handle_chunk(mock_service, chunk_header, chunk_data)

        assert result["status"] == "error"
        assert result["error"] == "unknown_transfer"


# ===== Cancel Transfer Tests =====

class TestCancelTransfer:
    """Test transfer cancellation."""

    @pytest.mark.asyncio
    async def test_cancel_active_transfer(self, mock_service, tmp_path):
        """Test cancelling an active transfer."""
        transfer_id = "to-cancel"
        local_path = tmp_path / "partial.txt"
        local_path.write_bytes(b"partial content")

        storage.save_file_transfer(
            mock_service.db_path, transfer_id, "file.txt", 1024, "text/plain",
            "sender", "channel", ["peer"], 2
        )
        storage.set_transfer_local_path(mock_service.db_path, transfer_id, str(local_path))

        result = await file_ops.cancel_file_transfer(mock_service, transfer_id)

        assert result["success"] is True
        assert not local_path.exists()  # Partial file should be deleted

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_transfer(self, mock_service):
        """Test cancelling a nonexistent transfer."""
        result = await file_ops.cancel_file_transfer(mock_service, "nonexistent")

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_cancel_completed_transfer(self, mock_service):
        """Test cancelling an already completed transfer."""
        transfer_id = "completed"
        storage.save_file_transfer(
            mock_service.db_path, transfer_id, "file.txt", 1024, "text/plain",
            "sender", "channel", ["peer"], 1
        )
        storage.update_file_transfer_progress(
            mock_service.db_path, transfer_id, 1, 100.0, "completed"
        )

        result = await file_ops.cancel_file_transfer(mock_service, transfer_id)

        assert result["success"] is False
        assert "already" in result["error"].lower()


# ===== List Transfers Tests =====

class TestListTransfers:
    """Test listing active transfers."""

    @pytest.mark.asyncio
    async def test_list_active_transfers(self, mock_service):
        """Test listing active transfers via service."""
        # Create transfers
        storage.save_file_transfer(
            mock_service.db_path, "t1", "file1.txt", 1024, "text/plain",
            "sender", "channel", ["peer"], 1
        )
        storage.save_file_transfer(
            mock_service.db_path, "t2", "file2.txt", 2048, "text/plain",
            "sender", "channel", ["peer"], 2
        )

        transfers = await file_ops.list_active_transfers(mock_service)

        assert len(transfers) == 2
        assert any(t["id"] == "t1" for t in transfers)
        assert any(t["id"] == "t2" for t in transfers)


# ===== Integration Tests =====

class TestIntegration:
    """Integration tests for file transfer flow."""

    @pytest.mark.asyncio
    async def test_full_receive_flow(self, mock_service, tmp_path):
        """Test complete file receive flow with multiple chunks."""
        transfer_id = "full-flow"
        file_content = b"chunk1" + b"chunk2" + b"chunk3"
        expected_hash = hashlib.sha256(file_content).hexdigest()

        # Setup transfer
        local_path = tmp_path / "received.txt"
        storage.save_file_transfer(
            mock_service.db_path, transfer_id, "file.txt",
            len(file_content), "text/plain",
            "sender", "channel", [mock_service.peer_id], 3
        )
        storage.set_transfer_local_path(mock_service.db_path, transfer_id, str(local_path))
        storage.set_transfer_hash(mock_service.db_path, transfer_id, expected_hash)

        # Receive chunks
        chunks = [b"chunk1", b"chunk2", b"chunk3"]
        for i, chunk_data in enumerate(chunks):
            chunk_header = {
                "transfer_id": transfer_id,
                "chunk_index": i,
                "chunk_hash": file_ops.compute_chunk_hash(chunk_data),
                "is_last": i == len(chunks) - 1
            }
            result = await file_ops.handle_chunk(mock_service, chunk_header, chunk_data)
            assert result["status"] == "ok"

        # Verify final file
        assert local_path.exists()
        assert local_path.read_bytes() == file_content

        # Check transfer marked complete
        transfer = storage.get_file_transfer(mock_service.db_path, transfer_id)
        assert transfer["status"] == "completed"

    @pytest.mark.asyncio
    async def test_progress_tracking(self, mock_service):
        """Test progress is tracked correctly during transfer."""
        transfer_id = "progress-test"
        storage.save_file_transfer(
            mock_service.db_path, transfer_id, "file.txt",
            10 * 1024 * 1024, "text/plain",  # 10MB = 10 chunks
            "sender", "channel", ["peer"], 10
        )

        # Simulate receiving 5 chunks
        for i in range(5):
            progress = ((i + 1) / 10) * 100
            await file_ops.update_transfer_progress(
                mock_service, transfer_id, i + 1, progress
            )

        transfer = storage.get_file_transfer(mock_service.db_path, transfer_id)
        assert transfer["chunks_received"] == 5
        assert transfer["progress_percent"] == 50.0
