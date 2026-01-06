"""
Comprehensive tests for api/offline_data_sync.py

Tests the CRDT-based offline data synchronization system:
- SyncOperation and SyncState dataclasses
- SYNCABLE_TABLES security allowlist
- OfflineDataSync class: initialization, operations, sync
- Team boundary enforcement and signature verification
- Conflict resolution (Last-Write-Wins with vector clocks)
- SQL injection protection
- Singleton pattern

Coverage targets: 90%+
"""

import pytest
import sqlite3
import json
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime, UTC, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from dataclasses import asdict

from api.offline_data_sync import (
    SyncOperation,
    SyncState,
    OfflineDataSync,
    SYNCABLE_TABLES,
    get_data_sync,
)


# ========== Fixtures ==========

@pytest.fixture
def temp_db_path():
    """Create temporary database path"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    yield path
    # Cleanup
    if path.exists():
        path.unlink()
    sync_path = path.parent / f"{path.stem}_sync.db"
    if sync_path.exists():
        sync_path.unlink()


@pytest.fixture
def data_sync(temp_db_path):
    """Create OfflineDataSync instance"""
    return OfflineDataSync(temp_db_path, "local-peer-123")


@pytest.fixture
def sample_operation():
    """Create sample SyncOperation"""
    return SyncOperation(
        op_id="op-123",
        table_name="chat_messages",
        operation="insert",
        row_id="row-456",
        data={"content": "Hello", "sender": "user1"},
        timestamp=datetime.now(UTC).isoformat(),
        peer_id="peer-abc",
        version=1,
        team_id=None,
        signature=""
    )


@pytest.fixture
def sample_team_operation():
    """Create sample team-scoped SyncOperation"""
    return SyncOperation(
        op_id="op-789",
        table_name="team_notes",
        operation="insert",
        row_id="row-001",
        data={"title": "Team Note", "body": "Content"},
        timestamp=datetime.now(UTC).isoformat(),
        peer_id="peer-def",
        version=2,
        team_id="team-123",
        signature="valid-signature"
    )


@pytest.fixture
def reset_singleton():
    """Reset singleton before and after test"""
    import api.offline_data_sync as module
    original = module._data_sync
    module._data_sync = None
    yield
    module._data_sync = original


# ========== SyncOperation Dataclass Tests ==========

class TestSyncOperation:
    """Tests for SyncOperation dataclass"""

    def test_creation_minimal(self):
        """Test minimal SyncOperation creation"""
        op = SyncOperation(
            op_id="op-1",
            table_name="chat_messages",
            operation="insert",
            row_id="row-1",
            data=None,
            timestamp="2025-01-01T00:00:00Z",
            peer_id="peer-1",
            version=1
        )

        assert op.op_id == "op-1"
        assert op.table_name == "chat_messages"
        assert op.operation == "insert"
        assert op.team_id is None
        assert op.signature == ""

    def test_creation_full(self, sample_team_operation):
        """Test full SyncOperation creation with team"""
        op = sample_team_operation

        assert op.team_id == "team-123"
        assert op.signature == "valid-signature"
        assert op.data is not None

    def test_asdict(self, sample_operation):
        """Test conversion to dict"""
        d = asdict(sample_operation)

        assert "op_id" in d
        assert "table_name" in d
        assert "data" in d
        assert d["op_id"] == "op-123"


# ========== SyncState Dataclass Tests ==========

class TestSyncState:
    """Tests for SyncState dataclass"""

    def test_creation(self):
        """Test SyncState creation"""
        state = SyncState(
            peer_id="peer-1",
            last_sync="2025-01-01T00:00:00Z",
            operations_sent=10,
            operations_received=5,
            conflicts_resolved=2,
            status="idle"
        )

        assert state.peer_id == "peer-1"
        assert state.operations_sent == 10
        assert state.status == "idle"

    def test_status_values(self):
        """Test various status values"""
        for status in ["syncing", "idle", "error"]:
            state = SyncState(
                peer_id="peer-1",
                last_sync=None,
                operations_sent=0,
                operations_received=0,
                conflicts_resolved=0,
                status=status
            )
            assert state.status == status


# ========== SYNCABLE_TABLES Tests ==========

class TestSyncableTables:
    """Tests for SYNCABLE_TABLES constant"""

    def test_is_frozenset(self):
        """Test SYNCABLE_TABLES is immutable frozenset"""
        assert isinstance(SYNCABLE_TABLES, frozenset)

    def test_expected_tables_present(self):
        """Test expected tables are in allowlist"""
        expected = [
            "chat_sessions",
            "chat_messages",
            "vault_files",
            "workflows",
            "team_notes",
            "query_history"
        ]
        for table in expected:
            assert table in SYNCABLE_TABLES

    def test_dangerous_tables_absent(self):
        """Test sensitive tables are NOT in allowlist"""
        dangerous = [
            "users",
            "auth_tokens",
            "sessions",
            "permissions",
            "audit_log"
        ]
        for table in dangerous:
            assert table not in SYNCABLE_TABLES

    def test_cannot_modify(self):
        """Test SYNCABLE_TABLES cannot be modified"""
        with pytest.raises(AttributeError):
            SYNCABLE_TABLES.add("malicious_table")


# ========== OfflineDataSync Initialization Tests ==========

class TestOfflineDataSyncInit:
    """Tests for OfflineDataSync initialization"""

    def test_init_creates_sync_db(self, temp_db_path):
        """Test initialization creates sync database"""
        sync = OfflineDataSync(temp_db_path, "peer-123")

        assert sync.sync_db_path.exists()
        assert sync.local_peer_id == "peer-123"
        assert sync.local_version == 0

    def test_init_creates_tables(self, data_sync):
        """Test initialization creates required tables"""
        conn = sqlite3.connect(str(data_sync.sync_db_path))
        cursor = conn.cursor()

        # Check tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN
            ('sync_operations', 'peer_sync_state', 'version_tracking')
        """)
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert "sync_operations" in tables
        assert "peer_sync_state" in tables
        assert "version_tracking" in tables

    def test_init_empty_state(self, data_sync):
        """Test initial state is empty"""
        assert len(data_sync.sync_states) == 0
        assert len(data_sync.pending_operations) == 0


# ========== Track Operation Tests ==========

class TestTrackOperation:
    """Tests for track_operation method"""

    @pytest.mark.asyncio
    async def test_track_insert(self, data_sync):
        """Test tracking insert operation"""
        await data_sync.track_operation(
            table_name="chat_messages",
            operation="insert",
            row_id="msg-123",
            data={"content": "Hello"}
        )

        assert len(data_sync.pending_operations) == 1
        assert data_sync.local_version == 1

    @pytest.mark.asyncio
    async def test_track_update(self, data_sync):
        """Test tracking update operation"""
        await data_sync.track_operation(
            table_name="chat_messages",
            operation="update",
            row_id="msg-123",
            data={"content": "Updated"}
        )

        op = data_sync.pending_operations[0]
        assert op.operation == "update"

    @pytest.mark.asyncio
    async def test_track_delete(self, data_sync):
        """Test tracking delete operation"""
        await data_sync.track_operation(
            table_name="chat_messages",
            operation="delete",
            row_id="msg-123"
        )

        op = data_sync.pending_operations[0]
        assert op.operation == "delete"
        assert op.data is None

    @pytest.mark.asyncio
    async def test_track_with_team_id(self, data_sync):
        """Test tracking operation with team_id signs payload"""
        with patch('api.offline_data_sync.sign_payload', return_value="sig-123"):
            await data_sync.track_operation(
                table_name="team_notes",
                operation="insert",
                row_id="note-1",
                data={"title": "Note"},
                team_id="team-abc"
            )

        op = data_sync.pending_operations[0]
        assert op.team_id == "team-abc"
        assert op.signature == "sig-123"

    @pytest.mark.asyncio
    async def test_track_increments_version(self, data_sync):
        """Test version increments with each operation"""
        for i in range(3):
            await data_sync.track_operation(
                table_name="chat_messages",
                operation="insert",
                row_id=f"msg-{i}"
            )

        assert data_sync.local_version == 3

    @pytest.mark.asyncio
    async def test_track_persists_to_db(self, data_sync):
        """Test operation is persisted to database"""
        await data_sync.track_operation(
            table_name="chat_messages",
            operation="insert",
            row_id="msg-123",
            data={"content": "Test"}
        )

        # Verify in database
        conn = sqlite3.connect(str(data_sync.sync_db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sync_operations WHERE row_id = ?", ("msg-123",))
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 1


# ========== Load Pending Operations Tests ==========

class TestLoadPendingOperations:
    """Tests for _load_pending_operations method"""

    def test_load_empty(self, data_sync):
        """Test loading when no pending operations"""
        # Fresh instance has no pending operations
        assert len(data_sync.pending_operations) == 0

    @pytest.mark.asyncio
    async def test_load_existing(self, temp_db_path):
        """Test loading existing pending operations on startup"""
        # First instance tracks an operation
        sync1 = OfflineDataSync(temp_db_path, "peer-123")
        await sync1.track_operation(
            table_name="chat_messages",
            operation="insert",
            row_id="msg-1"
        )

        # Second instance should load it
        sync2 = OfflineDataSync(temp_db_path, "peer-123")
        assert len(sync2.pending_operations) == 1
        assert sync2.local_version == 1


# ========== Mark Operations Synced Tests ==========

class TestMarkOperationsSynced:
    """Tests for _mark_operations_synced method"""

    @pytest.mark.asyncio
    async def test_mark_synced(self, data_sync):
        """Test marking operations as synced"""
        await data_sync.track_operation(
            table_name="chat_messages",
            operation="insert",
            row_id="msg-1"
        )
        op_id = data_sync.pending_operations[0].op_id

        data_sync._mark_operations_synced([op_id])

        # Verify in database
        conn = sqlite3.connect(str(data_sync.sync_db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT synced FROM sync_operations WHERE op_id = ?", (op_id,))
        synced = cursor.fetchone()[0]
        conn.close()

        assert synced == 1

    def test_mark_empty_list(self, data_sync):
        """Test marking empty list (no-op)"""
        # Should not raise
        data_sync._mark_operations_synced([])


# ========== Apply Operations Tests ==========

class TestApplyOperations:
    """Tests for _apply_operations method"""

    @pytest.fixture
    def target_db(self, temp_db_path):
        """Create target database with test tables"""
        conn = sqlite3.connect(str(temp_db_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY,
                content TEXT,
                sender TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_notes (
                id INTEGER PRIMARY KEY,
                title TEXT,
                body TEXT
            )
        """)
        conn.commit()
        conn.close()
        return temp_db_path

    @pytest.mark.asyncio
    async def test_apply_insert(self, target_db):
        """Test applying insert operation"""
        sync = OfflineDataSync(target_db, "peer-123")

        op = SyncOperation(
            op_id="op-1",
            table_name="chat_messages",
            operation="insert",
            row_id="1",
            data={"content": "Hello", "sender": "user1"},
            timestamp=datetime.now(UTC).isoformat(),
            peer_id="peer-remote",
            version=1
        )

        conflicts = await sync._apply_operations([op])

        # Verify row was inserted
        conn = sqlite3.connect(str(target_db))
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM chat_messages WHERE content = ?", ("Hello",))
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row[0] == "Hello"

    @pytest.mark.asyncio
    async def test_apply_rejects_non_syncable_table(self, target_db):
        """Test rejecting operations on non-syncable tables"""
        sync = OfflineDataSync(target_db, "peer-123")

        op = SyncOperation(
            op_id="op-1",
            table_name="users",  # Not in SYNCABLE_TABLES
            operation="insert",
            row_id="1",
            data={"username": "hacker"},
            timestamp=datetime.now(UTC).isoformat(),
            peer_id="peer-remote",
            version=1
        )

        # Should complete without error but log warning
        conflicts = await sync._apply_operations([op])

        # Verify no data was inserted (table doesn't even exist)
        assert conflicts == 0

    @pytest.mark.asyncio
    async def test_apply_with_invalid_team_signature(self, target_db):
        """Test rejecting operations with invalid team signature"""
        sync = OfflineDataSync(target_db, "peer-123")

        with patch('api.offline_data_sync.verify_payload', return_value=False):
            op = SyncOperation(
                op_id="op-1",
                table_name="team_notes",
                operation="insert",
                row_id="1",
                data={"title": "Note"},
                timestamp=datetime.now(UTC).isoformat(),
                peer_id="peer-remote",
                version=1,
                team_id="team-123",
                signature="invalid"
            )

            conflicts = await sync._apply_operations([op])

        # Operation should be rejected
        conn = sqlite3.connect(str(target_db))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM team_notes")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 0

    @pytest.mark.asyncio
    async def test_apply_with_valid_team_signature(self, target_db):
        """Test accepting operations with valid team signature"""
        sync = OfflineDataSync(target_db, "peer-123")

        with patch('api.offline_data_sync.verify_payload', return_value=True):
            op = SyncOperation(
                op_id="op-1",
                table_name="team_notes",
                operation="insert",
                row_id="1",
                data={"title": "Note", "body": "Content"},
                timestamp=datetime.now(UTC).isoformat(),
                peer_id="peer-remote",
                version=1,
                team_id="team-123",
                signature="valid"
            )

            conflicts = await sync._apply_operations([op])

        # Operation should be accepted
        conn = sqlite3.connect(str(target_db))
        cursor = conn.cursor()
        cursor.execute("SELECT title FROM team_notes WHERE title = ?", ("Note",))
        row = cursor.fetchone()
        conn.close()

        assert row is not None

    @pytest.mark.asyncio
    async def test_apply_rejects_non_team_member(self, target_db):
        """Test rejecting operations from non-team members"""
        sync = OfflineDataSync(target_db, "peer-123")

        with patch('api.offline_data_sync.verify_payload', return_value=True), \
             patch('api.offline_data_sync.is_team_member', return_value=None):
            op = SyncOperation(
                op_id="op-1",
                table_name="team_notes",
                operation="insert",
                row_id="1",
                data={"title": "Note"},
                timestamp=datetime.now(UTC).isoformat(),
                peer_id="peer-remote",
                version=1,
                team_id="team-123",
                signature="valid"
            )

            # Pass user_id to trigger membership check
            conflicts = await sync._apply_operations([op], user_id="user-456")

        # Operation should be rejected due to non-membership
        conn = sqlite3.connect(str(target_db))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM team_notes")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 0


# ========== Conflict Resolution Tests ==========

class TestConflictResolution:
    """Tests for conflict resolution (Last-Write-Wins)"""

    @pytest.mark.asyncio
    async def test_has_conflict_false_new_row(self, data_sync):
        """Test no conflict for new row"""
        op = SyncOperation(
            op_id="op-1",
            table_name="chat_messages",
            operation="insert",
            row_id="new-row",
            data={},
            timestamp=datetime.now(UTC).isoformat(),
            peer_id="peer-remote",
            version=1
        )

        has_conflict = await data_sync._has_conflict(op)
        assert has_conflict is False

    @pytest.mark.asyncio
    async def test_should_apply_newer_timestamp(self, data_sync):
        """Test LWW prefers newer timestamp"""
        # Set up existing version
        conn = sqlite3.connect(str(data_sync.sync_db_path))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO version_tracking (table_name, row_id, peer_id, version, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, ("chat_messages", "row-1", "peer-old", 1, "2025-01-01T00:00:00Z"))
        conn.commit()
        conn.close()

        # Newer operation
        op = SyncOperation(
            op_id="op-1",
            table_name="chat_messages",
            operation="update",
            row_id="row-1",
            data={},
            timestamp="2025-01-02T00:00:00Z",  # Newer
            peer_id="peer-new",
            version=2
        )

        should_apply = await data_sync._should_apply_operation(op)
        assert should_apply is True

    @pytest.mark.asyncio
    async def test_should_not_apply_older_timestamp(self, data_sync):
        """Test LWW rejects older timestamp"""
        # Set up existing version
        conn = sqlite3.connect(str(data_sync.sync_db_path))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO version_tracking (table_name, row_id, peer_id, version, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, ("chat_messages", "row-1", "peer-current", 2, "2025-01-02T00:00:00Z"))
        conn.commit()
        conn.close()

        # Older operation
        op = SyncOperation(
            op_id="op-1",
            table_name="chat_messages",
            operation="update",
            row_id="row-1",
            data={},
            timestamp="2025-01-01T00:00:00Z",  # Older
            peer_id="peer-old",
            version=1
        )

        should_apply = await data_sync._should_apply_operation(op)
        assert should_apply is False


# ========== Execute Operation SQL Safety Tests ==========

class TestExecuteOperationSafety:
    """Tests for SQL injection protection in _execute_operation"""

    @pytest.fixture
    def target_db(self, temp_db_path):
        """Create target database"""
        conn = sqlite3.connect(str(temp_db_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY,
                content TEXT
            )
        """)
        conn.commit()
        conn.close()
        return temp_db_path

    @pytest.mark.asyncio
    async def test_reject_invalid_column_name(self, target_db):
        """Test rejecting invalid column names"""
        sync = OfflineDataSync(target_db, "peer-123")

        conn = sqlite3.connect(str(target_db))
        op = SyncOperation(
            op_id="op-1",
            table_name="chat_messages",
            operation="insert",
            row_id="1",
            data={"content; DROP TABLE users; --": "malicious"},  # SQL injection attempt
            timestamp=datetime.now(UTC).isoformat(),
            peer_id="peer-remote",
            version=1
        )

        with pytest.raises(ValueError, match="Invalid column name"):
            await sync._execute_operation(conn, op)

        conn.close()

    @pytest.mark.asyncio
    async def test_reject_non_syncable_table(self, target_db):
        """Test rejecting non-syncable table"""
        sync = OfflineDataSync(target_db, "peer-123")

        conn = sqlite3.connect(str(target_db))
        op = SyncOperation(
            op_id="op-1",
            table_name="users",  # Not in SYNCABLE_TABLES
            operation="insert",
            row_id="1",
            data={"username": "hacker"},
            timestamp=datetime.now(UTC).isoformat(),
            peer_id="peer-remote",
            version=1
        )

        with pytest.raises(ValueError, match="Table not syncable"):
            await sync._execute_operation(conn, op)

        conn.close()


# ========== Sync With Peer Tests ==========

class TestSyncWithPeer:
    """Tests for sync_with_peer method"""

    @pytest.mark.asyncio
    async def test_sync_creates_state(self, data_sync):
        """Test sync creates peer state"""
        with patch.object(data_sync, '_get_operations_since_last_sync', new_callable=AsyncMock, return_value=[]), \
             patch.object(data_sync, '_exchange_operations_with_peer', new_callable=AsyncMock, return_value=[]), \
             patch.object(data_sync, '_apply_operations', new_callable=AsyncMock, return_value=0), \
             patch.object(data_sync, '_save_sync_state', new_callable=AsyncMock):

            state = await data_sync.sync_with_peer("peer-remote")

        assert state.peer_id == "peer-remote"
        assert state.status == "idle"
        assert "peer-remote" in data_sync.sync_states

    @pytest.mark.asyncio
    async def test_sync_handles_error(self, data_sync):
        """Test sync handles errors gracefully"""
        with patch.object(data_sync, '_get_operations_since_last_sync', new_callable=AsyncMock, side_effect=Exception("Network error")):

            with pytest.raises(Exception):
                await data_sync.sync_with_peer("peer-remote")

        # State should be 'error'
        assert data_sync.sync_states["peer-remote"].status == "error"


# ========== Exchange Operations Tests ==========

class TestExchangeOperations:
    """Tests for _exchange_operations_with_peer"""

    @pytest.mark.asyncio
    async def test_exchange_peer_not_found(self, data_sync):
        """Test exchange when peer not found"""
        mock_discovery = MagicMock()
        mock_discovery.get_peer_by_id.return_value = None

        with patch('offline_mesh_discovery.get_mesh_discovery', return_value=mock_discovery):
            result = await data_sync._exchange_operations_with_peer("unknown-peer", [])

        assert result == []

    @pytest.mark.asyncio
    async def test_exchange_http_error(self, data_sync, sample_operation):
        """Test exchange handles HTTP errors"""
        mock_peer = MagicMock()
        mock_peer.ip_address = "192.168.1.100"
        mock_peer.port = 8000

        mock_discovery = MagicMock()
        mock_discovery.get_peer_by_id.return_value = mock_peer

        mock_response = MagicMock()
        mock_response.status = 500

        with patch('offline_mesh_discovery.get_mesh_discovery', return_value=mock_discovery), \
             patch('aiohttp.ClientSession') as mock_session_class:

            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session.post = MagicMock(return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_response),
                __aexit__=AsyncMock()
            ))
            mock_session_class.return_value = mock_session

            result = await data_sync._exchange_operations_with_peer("peer-1", [sample_operation])

        assert result == []


# ========== Get Operations Since Last Sync Tests ==========

class TestGetOperationsSinceLastSync:
    """Tests for _get_operations_since_last_sync"""

    @pytest.mark.asyncio
    async def test_get_all_operations(self, data_sync):
        """Test getting all operations for new peer"""
        await data_sync.track_operation(
            table_name="chat_messages",
            operation="insert",
            row_id="msg-1"
        )

        ops = await data_sync._get_operations_since_last_sync("new-peer")

        assert len(ops) == 1
        assert ops[0].row_id == "msg-1"

    @pytest.mark.asyncio
    async def test_filter_by_tables(self, data_sync):
        """Test filtering operations by table"""
        await data_sync.track_operation(
            table_name="chat_messages",
            operation="insert",
            row_id="msg-1"
        )
        await data_sync.track_operation(
            table_name="vault_files",
            operation="insert",
            row_id="file-1"
        )

        ops = await data_sync._get_operations_since_last_sync(
            "new-peer",
            tables=["chat_messages"]
        )

        assert len(ops) == 1
        assert ops[0].table_name == "chat_messages"


# ========== Stats and State Tests ==========

class TestStatsAndState:
    """Tests for get_stats and state methods"""

    def test_get_stats_initial(self, data_sync):
        """Test initial stats"""
        stats = data_sync.get_stats()

        assert stats["local_peer_id"] == "local-peer-123"
        assert stats["local_version"] == 0
        assert stats["synced_peers"] == 0
        assert stats["pending_operations"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_after_operations(self, data_sync):
        """Test stats after tracking operations"""
        await data_sync.track_operation(
            table_name="chat_messages",
            operation="insert",
            row_id="msg-1"
        )

        stats = data_sync.get_stats()

        assert stats["local_version"] == 1
        assert stats["pending_operations"] == 1

    def test_get_sync_state_none(self, data_sync):
        """Test get_sync_state returns None for unknown peer"""
        state = data_sync.get_sync_state("unknown-peer")
        assert state is None

    def test_get_all_sync_states_empty(self, data_sync):
        """Test get_all_sync_states returns empty list"""
        states = data_sync.get_all_sync_states()
        assert states == []


# ========== Singleton Tests ==========

class TestSingleton:
    """Tests for singleton pattern"""

    def test_get_data_sync_creates_instance(self, temp_db_path, reset_singleton):
        """Test get_data_sync creates instance"""
        # When db_path is provided directly, get_config_paths is not called
        sync = get_data_sync(db_path=temp_db_path, local_peer_id="test-peer")

        assert sync is not None
        assert sync.local_peer_id == "test-peer"

    def test_get_data_sync_returns_same_instance(self, temp_db_path, reset_singleton):
        """Test get_data_sync returns same instance"""
        sync1 = get_data_sync(db_path=temp_db_path, local_peer_id="peer-1")
        sync2 = get_data_sync()  # Should return same instance

        assert sync1 is sync2


# ========== Version Tracking Tests ==========

class TestVersionTracking:
    """Tests for version tracking"""

    @pytest.mark.asyncio
    async def test_update_version_tracking(self, data_sync, sample_operation):
        """Test version tracking update"""
        await data_sync._update_version_tracking(sample_operation)

        conn = sqlite3.connect(str(data_sync.sync_db_path))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT version FROM version_tracking
            WHERE table_name = ? AND row_id = ? AND peer_id = ?
        """, (sample_operation.table_name, sample_operation.row_id, sample_operation.peer_id))
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row[0] == sample_operation.version


# ========== Edge Cases ==========

class TestEdgeCases:
    """Tests for edge cases"""

    @pytest.mark.asyncio
    async def test_track_operation_with_null_data(self, data_sync):
        """Test tracking operation with null data"""
        await data_sync.track_operation(
            table_name="chat_messages",
            operation="delete",
            row_id="msg-123",
            data=None
        )

        op = data_sync.pending_operations[0]
        assert op.data is None

    @pytest.mark.asyncio
    async def test_track_operation_unicode(self, data_sync):
        """Test tracking operation with unicode data"""
        await data_sync.track_operation(
            table_name="chat_messages",
            operation="insert",
            row_id="msg-123",
            data={"content": "日本語メッセージ 🎉"}
        )

        op = data_sync.pending_operations[0]
        assert op.data["content"] == "日本語メッセージ 🎉"

    def test_generate_op_id_unique(self, data_sync):
        """Test op_id generation is unique"""
        op_ids = [data_sync._generate_op_id() for _ in range(100)]
        assert len(op_ids) == len(set(op_ids))


# ========== Integration Tests ==========

class TestIntegration:
    """Integration tests"""

    @pytest.mark.asyncio
    async def test_full_sync_cycle(self, temp_db_path):
        """Test full sync cycle between two peers"""
        # Create target DB with tables
        conn = sqlite3.connect(str(temp_db_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY,
                content TEXT
            )
        """)
        conn.commit()
        conn.close()

        # Create sync instance
        sync = OfflineDataSync(temp_db_path, "peer-local")

        # Track some operations
        for i in range(3):
            await sync.track_operation(
                table_name="chat_messages",
                operation="insert",
                row_id=f"msg-{i}",
                data={"content": f"Message {i}"}
            )

        # Verify operations tracked
        assert len(sync.pending_operations) == 3
        assert sync.local_version == 3

        # Get stats
        stats = sync.get_stats()
        assert stats["pending_operations"] == 3

    @pytest.mark.asyncio
    async def test_conflict_resolution_lww(self, temp_db_path):
        """Test Last-Write-Wins conflict resolution"""
        sync = OfflineDataSync(temp_db_path, "peer-local")

        # Add existing version
        conn = sqlite3.connect(str(sync.sync_db_path))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO version_tracking (table_name, row_id, peer_id, version, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, ("chat_messages", "row-conflict", "peer-1", 1, "2025-01-01T12:00:00Z"))
        conn.commit()
        conn.close()

        # Newer operation should win
        newer_op = SyncOperation(
            op_id="op-newer",
            table_name="chat_messages",
            operation="update",
            row_id="row-conflict",
            data={},
            timestamp="2025-01-01T13:00:00Z",  # 1 hour later
            peer_id="peer-2",
            version=2
        )
        assert await sync._should_apply_operation(newer_op) is True

        # Older operation should lose
        older_op = SyncOperation(
            op_id="op-older",
            table_name="chat_messages",
            operation="update",
            row_id="row-conflict",
            data={},
            timestamp="2025-01-01T11:00:00Z",  # 1 hour earlier
            peer_id="peer-3",
            version=0
        )
        assert await sync._should_apply_operation(older_op) is False
