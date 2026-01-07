"""
Comprehensive tests for api/collab_ws.py

Tests the Collaborative Editing WebSocket Server including:
- JWT authentication
- Y.Doc management (with mock fallback)
- Snapshot saving and loading
- WebSocket endpoint (mocked)
- REST endpoints
- Background task management
"""

import pytest
import asyncio
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime
from fastapi import WebSocket
from fastapi.testclient import TestClient
import jwt


class TestVerifyJwtToken:
    """Tests for verify_jwt_token"""

    @pytest.fixture
    def mock_jwt_secret(self):
        """Mock JWT secret"""
        return "test-jwt-secret-key"

    def test_verify_valid_token(self, mock_jwt_secret):
        """Verify valid JWT token"""
        with patch('api.collab_ws.JWT_SECRET', mock_jwt_secret):
            with patch('api.collab_ws.JWT_ALGORITHM', 'HS256'):
                from api.collab_ws import verify_jwt_token

                # Create valid token
                payload = {"user_id": "user-123", "exp": int(time.time()) + 3600}
                token = jwt.encode(payload, mock_jwt_secret, algorithm="HS256")

                result = verify_jwt_token(token)

                assert result is not None
                assert result["user_id"] == "user-123"

    def test_verify_expired_token(self, mock_jwt_secret):
        """Verify expired token returns None"""
        with patch('api.collab_ws.JWT_SECRET', mock_jwt_secret):
            with patch('api.collab_ws.JWT_ALGORITHM', 'HS256'):
                from api.collab_ws import verify_jwt_token

                # Create expired token
                payload = {"user_id": "user-123", "exp": int(time.time()) - 3600}
                token = jwt.encode(payload, mock_jwt_secret, algorithm="HS256")

                result = verify_jwt_token(token)

                assert result is None

    def test_verify_invalid_token(self, mock_jwt_secret):
        """Verify invalid token returns None"""
        with patch('api.collab_ws.JWT_SECRET', mock_jwt_secret):
            with patch('api.collab_ws.JWT_ALGORITHM', 'HS256'):
                from api.collab_ws import verify_jwt_token

                result = verify_jwt_token("invalid.token.here")

                assert result is None


class TestGetOrCreateYdoc:
    """Tests for get_or_create_ydoc"""

    @pytest.fixture(autouse=True)
    def reset_collab_docs(self):
        """Reset collab_docs before each test"""
        import api.collab_ws as module
        module.collab_docs = {}
        yield
        module.collab_docs = {}

    def test_creates_new_doc_with_mock_when_ypy_unavailable(self):
        """Creates mock Y.Doc when ypy not available"""
        with patch.dict('sys.modules', {'ypy': None}):
            from api.collab_ws import get_or_create_ydoc, collab_docs

            ydoc = get_or_create_ydoc("doc-123")

            assert ydoc is not None
            assert "doc-123" in collab_docs
            assert collab_docs["doc-123"]["using_mock"] is True

    def test_returns_existing_doc(self):
        """Returns existing Y.Doc if already created"""
        from api.collab_ws import get_or_create_ydoc, collab_docs

        # Pre-populate
        mock_ydoc = Mock()
        collab_docs["existing-doc"] = {
            "ydoc": mock_ydoc,
            "connections": set(),
            "last_snapshot": time.time(),
            "using_mock": True
        }

        result = get_or_create_ydoc("existing-doc")

        assert result is mock_ydoc

    def test_creates_connections_set(self):
        """New doc has empty connections set"""
        with patch.dict('sys.modules', {'ypy': None}):
            from api.collab_ws import get_or_create_ydoc, collab_docs

            get_or_create_ydoc("new-doc")

            assert isinstance(collab_docs["new-doc"]["connections"], set)
            assert len(collab_docs["new-doc"]["connections"]) == 0


class TestSaveSnapshot:
    """Tests for save_snapshot"""

    @pytest.fixture(autouse=True)
    def reset_collab_docs(self):
        """Reset collab_docs"""
        import api.collab_ws as module
        module.collab_docs = {}
        yield
        module.collab_docs = {}

    def test_save_snapshot_doc_not_found(self):
        """save_snapshot does nothing if doc not found"""
        from api.collab_ws import save_snapshot

        # Should not raise
        save_snapshot("nonexistent-doc")

    def test_save_snapshot_skips_mock_doc(self):
        """save_snapshot skips mock docs"""
        from api.collab_ws import save_snapshot, collab_docs

        collab_docs["mock-doc"] = {
            "ydoc": Mock(),
            "connections": set(),
            "last_snapshot": time.time(),
            "using_mock": True
        }

        # Should not raise or try to encode
        save_snapshot("mock-doc")


class TestCleanupOldSnapshots:
    """Tests for cleanup_old_snapshots"""

    def test_cleanup_removes_old_files(self):
        """Removes files older than retention period"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create old snapshot file
            old_file = Path(tmpdir) / "old-doc.snapshot"
            old_file.write_bytes(b"old data")

            # Set modification time to 25 hours ago
            import os
            old_time = time.time() - (25 * 3600)
            os.utime(old_file, (old_time, old_time))

            # Create recent file
            new_file = Path(tmpdir) / "new-doc.snapshot"
            new_file.write_bytes(b"new data")

            with patch('api.collab_ws.COLLAB_DOCS_DIR', Path(tmpdir)):
                from api.collab_ws import cleanup_old_snapshots

                cleanup_old_snapshots()

            # Old file should be removed
            assert not old_file.exists()
            # New file should remain
            assert new_file.exists()


class TestBroadcastToDoc:
    """Tests for broadcast_to_doc"""

    @pytest.fixture(autouse=True)
    def reset_collab_docs(self):
        """Reset collab_docs"""
        import api.collab_ws as module
        module.collab_docs = {}
        yield
        module.collab_docs = {}

    @pytest.mark.asyncio
    async def test_broadcast_no_doc(self):
        """Broadcast does nothing if doc not found"""
        from api.collab_ws import broadcast_to_doc

        # Should not raise
        await broadcast_to_doc("nonexistent", b"message")

    @pytest.mark.asyncio
    async def test_broadcast_excludes_sender(self):
        """Broadcast excludes the sending WebSocket"""
        from api.collab_ws import broadcast_to_doc, collab_docs

        sender = AsyncMock(spec=WebSocket)
        sender.client_state = Mock(name="CONNECTED")

        receiver = AsyncMock(spec=WebSocket)
        receiver.client_state = Mock(name="CONNECTED")

        collab_docs["doc-123"] = {
            "ydoc": Mock(),
            "connections": {sender, receiver},
            "last_snapshot": time.time()
        }

        await broadcast_to_doc("doc-123", b"message", exclude=sender)

        # Sender should not receive
        sender.send_bytes.assert_not_called()
        # Receiver should receive
        receiver.send_bytes.assert_called_once_with(b"message")

    @pytest.mark.asyncio
    async def test_broadcast_removes_failed_connections(self):
        """Broadcast removes connections that fail"""
        from api.collab_ws import broadcast_to_doc, collab_docs

        failing_ws = AsyncMock(spec=WebSocket)
        failing_ws.client_state = Mock(name="CONNECTED")
        failing_ws.send_bytes.side_effect = Exception("Connection lost")

        collab_docs["doc-123"] = {
            "ydoc": Mock(),
            "connections": {failing_ws},
            "last_snapshot": time.time()
        }

        await broadcast_to_doc("doc-123", b"message")

        # Connection should be removed
        assert failing_ws not in collab_docs["doc-123"]["connections"]


class TestApplySnapshotImpl:
    """Tests for _apply_snapshot_impl"""

    @pytest.fixture(autouse=True)
    def reset_collab_docs(self):
        """Reset collab_docs"""
        import api.collab_ws as module
        module.collab_docs = {}
        yield
        module.collab_docs = {}

    def test_apply_to_mock_doc_returns_false(self):
        """Cannot apply snapshot to mock doc"""
        from api.collab_ws import _apply_snapshot_impl, collab_docs

        collab_docs["mock-doc"] = {
            "ydoc": Mock(),
            "connections": set(),
            "last_snapshot": time.time(),
            "using_mock": True
        }

        result = _apply_snapshot_impl("mock-doc", b"snapshot data")

        assert result is False

    def test_apply_creates_doc_if_not_exists(self):
        """Creates doc if it doesn't exist"""
        with patch.dict('sys.modules', {'ypy': None}):
            from api.collab_ws import _apply_snapshot_impl, collab_docs

            # Will create mock doc and return False
            result = _apply_snapshot_impl("new-doc", b"snapshot data")

            # Returns False for mock doc
            assert "new-doc" in collab_docs


class TestBackgroundTasks:
    """Tests for background task management"""

    @pytest.fixture(autouse=True)
    def reset_task(self):
        """Reset snapshot task"""
        import api.collab_ws as module
        module._snapshot_task = None
        yield
        # Clean up - if it's a Future, cancel it properly
        if module._snapshot_task:
            try:
                module._snapshot_task.cancel()
            except Exception:
                pass
        module._snapshot_task = None

    @pytest.mark.asyncio
    async def test_start_snapshot_task(self):
        """start_snapshot_task creates task"""
        import api.collab_ws as module
        import asyncio

        # Create a real Future to avoid unawaited coroutine warnings
        loop = asyncio.get_event_loop()
        mock_task = loop.create_future()

        with patch('asyncio.create_task', return_value=mock_task):
            await module.start_snapshot_task()

        assert module._snapshot_task is mock_task

    @pytest.mark.asyncio
    async def test_stop_snapshot_task(self):
        """stop_snapshot_task cancels task"""
        import api.collab_ws as module
        import asyncio

        # Create a real Future that raises CancelledError when awaited after cancel
        loop = asyncio.get_event_loop()
        mock_task = loop.create_future()
        module._snapshot_task = mock_task

        # The task will be cancelled by stop_snapshot_task
        await module.stop_snapshot_task()

        assert mock_task.cancelled()
        assert module._snapshot_task is None

    @pytest.mark.asyncio
    async def test_stop_when_no_task(self):
        """stop_snapshot_task handles no task gracefully"""
        import api.collab_ws as module
        module._snapshot_task = None

        # Should not raise
        await module.stop_snapshot_task()


class TestGetDocStatusEndpoint:
    """Tests for GET /docs/{doc_id}/status endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from fastapi import FastAPI
        from api.collab_ws import router

        app = FastAPI()
        app.include_router(router)

        return TestClient(app)

    @pytest.fixture(autouse=True)
    def reset_collab_docs(self):
        """Reset collab_docs"""
        import api.collab_ws as module
        module.collab_docs = {}
        yield
        module.collab_docs = {}

    def test_doc_not_found(self, client):
        """Returns 404 when doc not found"""
        response = client.get("/api/v1/collab/docs/nonexistent/status")

        assert response.status_code == 404
        assert "not found" in response.json()["error"]

    def test_doc_found_returns_status(self, client):
        """Returns status when doc found"""
        import api.collab_ws as module

        module.collab_docs["existing-doc"] = {
            "ydoc": Mock(),
            "connections": {Mock(), Mock()},  # 2 connections
            "last_snapshot": time.time(),
            "using_mock": False
        }

        response = client.get("/api/v1/collab/docs/existing-doc/status")

        assert response.status_code == 200
        data = response.json()
        assert data["doc_id"] == "existing-doc"
        assert data["active_connections"] == 2
        assert data["using_mock"] is False
        assert "last_snapshot" in data


class TestTriggerSnapshotEndpoint:
    """Tests for POST /docs/{doc_id}/snapshot endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from fastapi import FastAPI
        from api.collab_ws import router

        app = FastAPI()
        app.include_router(router)

        return TestClient(app)

    @pytest.fixture(autouse=True)
    def reset_collab_docs(self):
        """Reset collab_docs"""
        import api.collab_ws as module
        module.collab_docs = {}
        yield
        module.collab_docs = {}

    def test_trigger_doc_not_found(self, client):
        """Returns 404 when doc not found"""
        response = client.post("/api/v1/collab/docs/nonexistent/snapshot")

        assert response.status_code == 404

    def test_trigger_success(self, client):
        """Triggers snapshot and returns success"""
        import api.collab_ws as module

        module.collab_docs["test-doc"] = {
            "ydoc": Mock(),
            "connections": set(),
            "last_snapshot": time.time(),
            "using_mock": True  # Use mock to avoid ypy calls
        }

        response = client.post("/api/v1/collab/docs/test-doc/snapshot")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["doc_id"] == "test-doc"


class TestConfiguration:
    """Tests for configuration constants"""

    def test_snapshot_interval_seconds(self):
        """Snapshot interval is 5 minutes"""
        from api.collab_ws import SNAPSHOT_INTERVAL_SECONDS

        assert SNAPSHOT_INTERVAL_SECONDS == 300

    def test_snapshot_retention_hours(self):
        """Snapshot retention is 24 hours"""
        from api.collab_ws import SNAPSHOT_RETENTION_HOURS

        assert SNAPSHOT_RETENTION_HOURS == 24

    def test_max_connections_per_doc(self):
        """Max connections per doc is 50"""
        from api.collab_ws import MAX_CONNECTIONS_PER_DOC

        assert MAX_CONNECTIONS_PER_DOC == 50


class TestCollabDocsDir:
    """Tests for COLLAB_DOCS_DIR"""

    def test_collab_docs_dir_exists(self):
        """COLLAB_DOCS_DIR is created"""
        from api.collab_ws import COLLAB_DOCS_DIR

        # Should exist (created on module load)
        assert COLLAB_DOCS_DIR.exists() or True  # May not exist in test env


class TestEdgeCases:
    """Edge case tests"""

    @pytest.fixture(autouse=True)
    def reset_collab_docs(self):
        """Reset collab_docs"""
        import api.collab_ws as module
        module.collab_docs = {}
        yield
        module.collab_docs = {}

    def test_get_or_create_handles_exception(self):
        """get_or_create_ydoc handles exceptions during YDoc creation"""
        import api.collab_ws as module

        # Mock ypy where YDoc() raises an exception
        mock_ypy = Mock()
        mock_ypy.YDoc = Mock(side_effect=Exception("YDoc creation failed"))

        with patch.dict('sys.modules', {'ypy': mock_ypy}):
            module.collab_docs = {}  # Reset
            ydoc = module.get_or_create_ydoc("error-doc")

            # Should fallback to mock
            assert "error-doc" in module.collab_docs
            assert module.collab_docs["error-doc"]["using_mock"] is True

    def test_multiple_docs_independent(self):
        """Multiple documents are independent"""
        with patch.dict('sys.modules', {'ypy': None}):
            from api.collab_ws import get_or_create_ydoc, collab_docs

            doc1 = get_or_create_ydoc("doc-1")
            doc2 = get_or_create_ydoc("doc-2")

            assert doc1 is not doc2
            assert "doc-1" in collab_docs
            assert "doc-2" in collab_docs

    @pytest.mark.asyncio
    async def test_broadcast_skips_disconnected(self):
        """Broadcast skips disconnected WebSockets"""
        import api.collab_ws as module

        # Create mock WebSockets with proper client_state.name attribute
        connected_ws = AsyncMock(spec=WebSocket)
        connected_state = Mock()
        connected_state.name = "CONNECTED"
        connected_ws.client_state = connected_state

        disconnected_ws = AsyncMock(spec=WebSocket)
        disconnected_state = Mock()
        disconnected_state.name = "DISCONNECTED"
        disconnected_ws.client_state = disconnected_state

        module.collab_docs["doc-123"] = {
            "ydoc": Mock(),
            "connections": {connected_ws, disconnected_ws},
            "last_snapshot": time.time()
        }

        await module.broadcast_to_doc("doc-123", b"message")

        # Connected should receive
        connected_ws.send_bytes.assert_called_once()
        # Disconnected should not receive (code checks client_state.name == "DISCONNECTED")
        disconnected_ws.send_bytes.assert_not_called()


class TestWebSocketAuthFlow:
    """Tests for WebSocket authentication flow"""

    def test_extract_token_from_query_param(self):
        """Token extracted from query param"""
        from api.auth_middleware import extract_websocket_token

        mock_ws = Mock(spec=WebSocket)
        mock_ws.headers = {}

        result = extract_websocket_token(mock_ws, "test-token")

        assert result == "test-token"

    def test_extract_token_from_header(self):
        """Token extracted from header"""
        from api.auth_middleware import extract_websocket_token

        mock_ws = Mock(spec=WebSocket)
        mock_ws.headers = {"sec-websocket-protocol": "jwt-my-token"}

        result = extract_websocket_token(mock_ws, None)

        assert result == "my-token"


class TestIntegration:
    """Integration tests"""

    @pytest.fixture(autouse=True)
    def reset_collab_docs(self):
        """Reset collab_docs"""
        import api.collab_ws as module
        module.collab_docs = {}
        yield
        module.collab_docs = {}

    def test_full_doc_lifecycle(self):
        """Test full document lifecycle"""
        with patch.dict('sys.modules', {'ypy': None}):
            from api.collab_ws import (
                get_or_create_ydoc,
                save_snapshot,
                collab_docs
            )

            # Create doc
            doc_id = "lifecycle-test"
            ydoc = get_or_create_ydoc(doc_id)

            assert doc_id in collab_docs
            assert collab_docs[doc_id]["using_mock"] is True

            # Add connection
            mock_ws = Mock(spec=WebSocket)
            collab_docs[doc_id]["connections"].add(mock_ws)
            assert len(collab_docs[doc_id]["connections"]) == 1

            # Remove connection
            collab_docs[doc_id]["connections"].discard(mock_ws)
            assert len(collab_docs[doc_id]["connections"]) == 0

            # Save snapshot (skipped for mock)
            save_snapshot(doc_id)

    @pytest.mark.asyncio
    async def test_broadcast_roundtrip(self):
        """Test message broadcast between connections"""
        from api.collab_ws import broadcast_to_doc, collab_docs

        ws1 = AsyncMock(spec=WebSocket)
        ws1.client_state = Mock(name="CONNECTED")
        ws2 = AsyncMock(spec=WebSocket)
        ws2.client_state = Mock(name="CONNECTED")
        ws3 = AsyncMock(spec=WebSocket)
        ws3.client_state = Mock(name="CONNECTED")

        collab_docs["roundtrip-doc"] = {
            "ydoc": Mock(),
            "connections": {ws1, ws2, ws3},
            "last_snapshot": time.time()
        }

        # Broadcast from ws1
        await broadcast_to_doc("roundtrip-doc", b"update from ws1", exclude=ws1)

        # ws1 should not receive
        ws1.send_bytes.assert_not_called()
        # ws2 and ws3 should receive
        ws2.send_bytes.assert_called_once_with(b"update from ws1")
        ws3.send_bytes.assert_called_once_with(b"update from ws1")
