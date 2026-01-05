"""
Comprehensive tests for api/workspace_session.py

Tests cover:
- WorkspaceSessionManager initialization
- Thread-local connection management
- Session CRUD operations
- Session linking (chat, terminal)
- Activity tracking
- User session listing
- Singleton pattern
- Edge cases and error handling
"""

import pytest
import sqlite3
import tempfile
import threading
import time
import json
from pathlib import Path
from datetime import datetime, UTC
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.workspace_session import (
    WorkspaceSessionManager,
    get_workspace_session_manager,
)
import api.workspace_session as workspace_session_module


# ========== Fixtures ==========

@pytest.fixture
def temp_db_path():
    """Create a temporary database path"""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp) / "test_sessions.db"


@pytest.fixture
def manager(temp_db_path):
    """Create a WorkspaceSessionManager with temp database"""
    mgr = WorkspaceSessionManager(db_path=temp_db_path)
    yield mgr
    mgr.close()


# ========== Initialization Tests ==========

class TestWorkspaceSessionManagerInit:
    """Tests for WorkspaceSessionManager initialization"""

    def test_init_with_default_path(self):
        """Test initialization with default database path"""
        with patch.object(workspace_session_module, 'PATHS') as mock_paths:
            mock_paths.data_dir = Path(tempfile.gettempdir())
            manager = WorkspaceSessionManager()
            assert manager.db_path.name == "workspace_sessions.db"
            manager.close()

    def test_init_with_custom_path(self, temp_db_path):
        """Test initialization with custom database path"""
        manager = WorkspaceSessionManager(db_path=temp_db_path)
        assert manager.db_path == temp_db_path
        manager.close()

    def test_init_creates_parent_directories(self):
        """Test initialization creates parent directories if needed"""
        with tempfile.TemporaryDirectory() as tmp:
            nested_path = Path(tmp) / "nested" / "dir" / "sessions.db"
            manager = WorkspaceSessionManager(db_path=nested_path)
            assert nested_path.parent.exists()
            manager.close()

    def test_init_creates_tables(self, temp_db_path):
        """Test initialization creates required tables"""
        manager = WorkspaceSessionManager(db_path=temp_db_path)

        # Verify table exists
        conn = sqlite3.connect(str(temp_db_path))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='workspace_sessions'
        """)
        assert cursor.fetchone() is not None
        conn.close()
        manager.close()

    def test_init_creates_indexes(self, temp_db_path):
        """Test initialization creates required indexes"""
        manager = WorkspaceSessionManager(db_path=temp_db_path)

        conn = sqlite3.connect(str(temp_db_path))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND name='idx_workspace_user'
        """)
        assert cursor.fetchone() is not None

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND name='idx_workspace_root'
        """)
        assert cursor.fetchone() is not None
        conn.close()
        manager.close()


# ========== Connection Management Tests ==========

class TestConnectionManagement:
    """Tests for thread-local connection management"""

    def test_get_connection_creates_connection(self, manager):
        """Test _get_connection creates a connection"""
        conn = manager._get_connection()
        assert conn is not None
        assert isinstance(conn, sqlite3.Connection)

    def test_get_connection_reuses_connection(self, manager):
        """Test _get_connection returns same connection in same thread"""
        conn1 = manager._get_connection()
        conn2 = manager._get_connection()
        assert conn1 is conn2

    def test_connection_context_manager_commits(self, manager):
        """Test _connection context manager commits on success"""
        with manager._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO workspace_sessions
                (session_id, user_id, created_at, last_activity)
                VALUES ('test1', 'user1', '2024-01-01', '2024-01-01')
            """)

        # Verify data was committed
        with manager._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT session_id FROM workspace_sessions WHERE session_id = 'test1'")
            assert cursor.fetchone() is not None

    def test_connection_context_manager_rollbacks_on_error(self, manager):
        """Test _connection context manager rolls back on exception"""
        try:
            with manager._connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO workspace_sessions
                    (session_id, user_id, created_at, last_activity)
                    VALUES ('rollback_test', 'user1', '2024-01-01', '2024-01-01')
                """)
                raise Exception("Simulated error")
        except Exception:
            pass

        # Verify data was rolled back
        with manager._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT session_id FROM workspace_sessions WHERE session_id = 'rollback_test'")
            assert cursor.fetchone() is None

    def test_close_closes_connection(self, temp_db_path):
        """Test close() closes the thread-local connection"""
        manager = WorkspaceSessionManager(db_path=temp_db_path)

        # Force connection creation
        manager._get_connection()
        assert hasattr(manager._local, 'connection')
        assert manager._local.connection is not None

        manager.close()
        assert manager._local.connection is None

    def test_close_handles_no_connection(self, temp_db_path):
        """Test close() handles case when no connection exists"""
        manager = WorkspaceSessionManager(db_path=temp_db_path)
        # Don't create connection, just close
        manager.close()  # Should not raise

    def test_wal_mode_enabled(self, temp_db_path):
        """Test WAL mode is enabled for connections"""
        manager = WorkspaceSessionManager(db_path=temp_db_path)

        conn = manager._get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]

        assert mode.lower() == "wal"
        manager.close()


# ========== Session Creation Tests ==========

class TestSessionCreation:
    """Tests for session creation"""

    def test_create_session_basic(self, manager):
        """Test basic session creation"""
        session_id = manager.create_session(user_id="user123")

        assert session_id is not None
        assert session_id.startswith("ws_")
        assert len(session_id) == 15  # "ws_" + 12 hex chars

    def test_create_session_with_workspace_root(self, manager):
        """Test session creation with workspace root"""
        session_id = manager.create_session(
            user_id="user123",
            workspace_root="/path/to/workspace"
        )

        session = manager.get_session(session_id)
        assert session['workspace_root'] == "/path/to/workspace"

    def test_create_session_with_chat_id(self, manager):
        """Test session creation with chat ID"""
        session_id = manager.create_session(
            user_id="user123",
            chat_id="chat_abc123"
        )

        session = manager.get_session(session_id)
        assert session['chat_id'] == "chat_abc123"

    def test_create_session_sets_timestamps(self, manager):
        """Test session creation sets created_at and last_activity"""
        before = datetime.now(UTC)
        session_id = manager.create_session(user_id="user123")
        after = datetime.now(UTC)

        session = manager.get_session(session_id)

        created = datetime.fromisoformat(session['created_at'])
        last_activity = datetime.fromisoformat(session['last_activity'])

        # Timestamps should be between before and after
        assert before <= created <= after
        assert before <= last_activity <= after

    def test_create_session_is_active_by_default(self, manager):
        """Test created sessions are active by default"""
        session_id = manager.create_session(user_id="user123")
        session = manager.get_session(session_id)
        assert session['is_active'] is True

    def test_create_multiple_sessions(self, manager):
        """Test creating multiple sessions"""
        session1 = manager.create_session(user_id="user123")
        session2 = manager.create_session(user_id="user123")
        session3 = manager.create_session(user_id="user456")

        assert session1 != session2
        assert session1 != session3
        assert session2 != session3


# ========== Get or Create Tests ==========

class TestGetOrCreate:
    """Tests for get_or_create methods"""

    def test_get_or_create_for_workspace_creates_new(self, manager):
        """Test get_or_create_for_workspace creates new session"""
        session_id = manager.get_or_create_for_workspace(
            user_id="user123",
            workspace_root="/new/workspace"
        )

        assert session_id is not None
        session = manager.get_session(session_id)
        assert session['workspace_root'] == "/new/workspace"

    def test_get_or_create_for_workspace_returns_existing(self, manager):
        """Test get_or_create_for_workspace returns existing active session"""
        # Create first session
        session1 = manager.get_or_create_for_workspace(
            user_id="user123",
            workspace_root="/existing/workspace"
        )

        # Get or create should return same session
        session2 = manager.get_or_create_for_workspace(
            user_id="user123",
            workspace_root="/existing/workspace"
        )

        assert session1 == session2

    def test_get_or_create_for_workspace_different_users(self, manager):
        """Test different users get different sessions for same workspace"""
        session1 = manager.get_or_create_for_workspace(
            user_id="user1",
            workspace_root="/shared/workspace"
        )
        session2 = manager.get_or_create_for_workspace(
            user_id="user2",
            workspace_root="/shared/workspace"
        )

        assert session1 != session2

    def test_get_or_create_for_chat_creates_new(self, manager):
        """Test get_or_create_for_chat creates new session"""
        session_id = manager.get_or_create_for_chat(
            user_id="user123",
            chat_id="chat_new"
        )

        assert session_id is not None
        session = manager.get_session(session_id)
        assert session['chat_id'] == "chat_new"

    def test_get_or_create_for_chat_returns_existing(self, manager):
        """Test get_or_create_for_chat returns existing session"""
        session1 = manager.get_or_create_for_chat(
            user_id="user123",
            chat_id="chat_existing"
        )
        session2 = manager.get_or_create_for_chat(
            user_id="user123",
            chat_id="chat_existing"
        )

        assert session1 == session2

    def test_get_or_create_for_chat_with_workspace(self, manager):
        """Test get_or_create_for_chat with workspace root"""
        session_id = manager.get_or_create_for_chat(
            user_id="user123",
            chat_id="chat_with_ws",
            workspace_root="/path/to/ws"
        )

        session = manager.get_session(session_id)
        assert session['workspace_root'] == "/path/to/ws"

    def test_get_or_create_updates_activity(self, manager):
        """Test get_or_create updates last_activity when returning existing"""
        session_id = manager.get_or_create_for_workspace(
            user_id="user123",
            workspace_root="/workspace"
        )

        session1 = manager.get_session(session_id)
        time.sleep(0.01)  # Small delay

        # Get again (should update activity)
        manager.get_or_create_for_workspace(
            user_id="user123",
            workspace_root="/workspace"
        )

        session2 = manager.get_session(session_id)

        # Last activity should be updated
        assert session2['last_activity'] >= session1['last_activity']


# ========== Session Linking Tests ==========

class TestSessionLinking:
    """Tests for linking chat and terminal to sessions"""

    def test_link_chat(self, manager):
        """Test linking chat to session"""
        session_id = manager.create_session(user_id="user123")
        manager.link_chat(session_id, "chat_linked")

        session = manager.get_session(session_id)
        assert session['chat_id'] == "chat_linked"

    def test_link_terminal(self, manager):
        """Test linking terminal to session"""
        session_id = manager.create_session(user_id="user123")
        manager.link_terminal(session_id, "terminal_linked")

        session = manager.get_session(session_id)
        assert session['terminal_id'] == "terminal_linked"

    def test_link_updates_activity(self, manager):
        """Test linking updates last_activity"""
        session_id = manager.create_session(user_id="user123")
        session1 = manager.get_session(session_id)

        time.sleep(0.01)
        manager.link_chat(session_id, "chat_new")

        session2 = manager.get_session(session_id)
        assert session2['last_activity'] > session1['last_activity']


# ========== Update Tests ==========

class TestSessionUpdates:
    """Tests for session update methods"""

    def test_update_workspace_root(self, manager):
        """Test updating workspace root"""
        session_id = manager.create_session(user_id="user123")
        manager.update_workspace_root(session_id, "/new/root")

        session = manager.get_session(session_id)
        assert session['workspace_root'] == "/new/root"

    def test_update_active_files(self, manager):
        """Test updating active files"""
        session_id = manager.create_session(user_id="user123")
        files = ["/path/to/file1.py", "/path/to/file2.py"]
        manager.update_active_files(session_id, files)

        session = manager.get_session(session_id)
        assert session['active_files'] == files

    def test_update_active_files_empty_list(self, manager):
        """Test updating active files with empty list"""
        session_id = manager.create_session(user_id="user123")
        manager.update_active_files(session_id, [])

        session = manager.get_session(session_id)
        assert session['active_files'] == []

    def test_update_activity(self, manager):
        """Test updating activity timestamp"""
        session_id = manager.create_session(user_id="user123")
        session1 = manager.get_session(session_id)

        time.sleep(0.01)
        manager.update_activity(session_id)

        session2 = manager.get_session(session_id)
        assert session2['last_activity'] > session1['last_activity']


# ========== Get Session Tests ==========

class TestGetSession:
    """Tests for get_session method"""

    def test_get_session_returns_all_fields(self, manager):
        """Test get_session returns all expected fields"""
        session_id = manager.create_session(
            user_id="user123",
            workspace_root="/workspace",
            chat_id="chat123"
        )
        manager.link_terminal(session_id, "terminal123")
        manager.update_active_files(session_id, ["/file1.py"])

        session = manager.get_session(session_id)

        assert 'session_id' in session
        assert 'user_id' in session
        assert 'workspace_root' in session
        assert 'chat_id' in session
        assert 'terminal_id' in session
        assert 'active_files' in session
        assert 'created_at' in session
        assert 'last_activity' in session
        assert 'is_active' in session

    def test_get_session_nonexistent(self, manager):
        """Test get_session returns None for nonexistent session"""
        session = manager.get_session("nonexistent_session")
        assert session is None

    def test_get_session_active_files_json(self, manager):
        """Test active_files is properly deserialized from JSON"""
        session_id = manager.create_session(user_id="user123")
        files = ["/path/with spaces/file.py", "/unicode/文件.py"]
        manager.update_active_files(session_id, files)

        session = manager.get_session(session_id)
        assert session['active_files'] == files
        assert isinstance(session['active_files'], list)

    def test_get_session_null_active_files(self, manager):
        """Test get_session handles null active_files"""
        session_id = manager.create_session(user_id="user123")
        # active_files is NULL by default
        session = manager.get_session(session_id)
        assert session['active_files'] == []


# ========== List User Sessions Tests ==========

class TestListUserSessions:
    """Tests for list_user_sessions method"""

    def test_list_user_sessions_empty(self, manager):
        """Test listing sessions for user with no sessions"""
        sessions = manager.list_user_sessions("no_sessions_user")
        assert sessions == []

    def test_list_user_sessions_returns_all(self, manager):
        """Test listing returns all user sessions"""
        manager.create_session(user_id="listuser")
        manager.create_session(user_id="listuser")
        manager.create_session(user_id="listuser")

        sessions = manager.list_user_sessions("listuser")
        assert len(sessions) == 3

    def test_list_user_sessions_active_only_default(self, manager):
        """Test listing only returns active sessions by default"""
        session1 = manager.create_session(user_id="activeuser")
        session2 = manager.create_session(user_id="activeuser")
        manager.close_session(session1)

        sessions = manager.list_user_sessions("activeuser")
        assert len(sessions) == 1
        assert sessions[0]['session_id'] == session2

    def test_list_user_sessions_include_inactive(self, manager):
        """Test listing with active_only=False includes inactive"""
        session1 = manager.create_session(user_id="alluser")
        session2 = manager.create_session(user_id="alluser")
        manager.close_session(session1)

        sessions = manager.list_user_sessions("alluser", active_only=False)
        assert len(sessions) == 2

    def test_list_user_sessions_ordered_by_activity(self, manager):
        """Test sessions are ordered by last_activity descending"""
        session1 = manager.create_session(user_id="orderuser")
        time.sleep(0.01)
        session2 = manager.create_session(user_id="orderuser")
        time.sleep(0.01)
        session3 = manager.create_session(user_id="orderuser")

        sessions = manager.list_user_sessions("orderuser")

        # Most recent first
        assert sessions[0]['session_id'] == session3
        assert sessions[1]['session_id'] == session2
        assert sessions[2]['session_id'] == session1

    def test_list_user_sessions_isolation(self, manager):
        """Test listing only returns sessions for specified user"""
        manager.create_session(user_id="user_a")
        manager.create_session(user_id="user_a")
        manager.create_session(user_id="user_b")

        sessions_a = manager.list_user_sessions("user_a")
        sessions_b = manager.list_user_sessions("user_b")

        assert len(sessions_a) == 2
        assert len(sessions_b) == 1


# ========== Close Session Tests ==========

class TestCloseSession:
    """Tests for close_session method"""

    def test_close_session_marks_inactive(self, manager):
        """Test close_session marks session as inactive"""
        session_id = manager.create_session(user_id="user123")
        manager.close_session(session_id)

        session = manager.get_session(session_id)
        assert session['is_active'] is False

    def test_close_session_updates_activity(self, manager):
        """Test close_session updates last_activity"""
        session_id = manager.create_session(user_id="user123")
        session1 = manager.get_session(session_id)

        time.sleep(0.01)
        manager.close_session(session_id)

        session2 = manager.get_session(session_id)
        assert session2['last_activity'] > session1['last_activity']

    def test_closed_session_not_returned_by_get_or_create(self, manager):
        """Test closed sessions are not returned by get_or_create"""
        session1 = manager.get_or_create_for_workspace(
            user_id="user123",
            workspace_root="/workspace"
        )
        manager.close_session(session1)

        session2 = manager.get_or_create_for_workspace(
            user_id="user123",
            workspace_root="/workspace"
        )

        # Should create a new session, not return closed one
        assert session1 != session2


# ========== Singleton Tests ==========

class TestSingleton:
    """Tests for singleton pattern"""

    def test_get_workspace_session_manager_returns_instance(self):
        """Test get_workspace_session_manager returns an instance"""
        # Reset singleton
        workspace_session_module._workspace_session_manager = None

        manager = get_workspace_session_manager()
        assert isinstance(manager, WorkspaceSessionManager)

    def test_get_workspace_session_manager_returns_same_instance(self):
        """Test get_workspace_session_manager returns same instance"""
        # Reset singleton
        workspace_session_module._workspace_session_manager = None

        manager1 = get_workspace_session_manager()
        manager2 = get_workspace_session_manager()

        assert manager1 is manager2


# ========== Thread Safety Tests ==========

class TestThreadSafety:
    """Tests for thread safety"""

    def test_concurrent_session_creation(self, temp_db_path):
        """Test concurrent session creation from multiple threads"""
        manager = WorkspaceSessionManager(db_path=temp_db_path)
        sessions = []
        errors = []

        def create_session(user_id):
            try:
                session_id = manager.create_session(user_id=user_id)
                sessions.append(session_id)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=create_session, args=(f"user_{i}",))
            for i in range(10)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(sessions) == 10
        assert len(set(sessions)) == 10  # All unique

        manager.close()

    def test_thread_local_connections(self, temp_db_path):
        """Test each thread gets its own connection"""
        manager = WorkspaceSessionManager(db_path=temp_db_path)
        connection_ids = []

        def get_connection_id():
            conn = manager._get_connection()
            connection_ids.append(id(conn))

        threads = [
            threading.Thread(target=get_connection_id)
            for _ in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Each thread should have gotten a different connection
        assert len(set(connection_ids)) == 5

        manager.close()


# ========== Edge Cases ==========

class TestEdgeCases:
    """Tests for edge cases"""

    def test_unicode_workspace_root(self, manager):
        """Test handling unicode in workspace root"""
        session_id = manager.create_session(
            user_id="user123",
            workspace_root="/путь/к/工作区"
        )

        session = manager.get_session(session_id)
        assert session['workspace_root'] == "/путь/к/工作区"

    def test_unicode_user_id(self, manager):
        """Test handling unicode in user ID"""
        session_id = manager.create_session(user_id="用户名")

        session = manager.get_session(session_id)
        assert session['user_id'] == "用户名"

    def test_very_long_workspace_root(self, manager):
        """Test handling very long workspace root"""
        long_path = "/a" * 1000
        session_id = manager.create_session(
            user_id="user123",
            workspace_root=long_path
        )

        session = manager.get_session(session_id)
        assert session['workspace_root'] == long_path

    def test_special_chars_in_paths(self, manager):
        """Test handling special characters in paths"""
        special_path = "/path/with spaces/and'quotes/and\"double"
        session_id = manager.create_session(
            user_id="user123",
            workspace_root=special_path
        )

        session = manager.get_session(session_id)
        assert session['workspace_root'] == special_path

    def test_empty_active_files_list(self, manager):
        """Test handling empty active files list"""
        session_id = manager.create_session(user_id="user123")
        manager.update_active_files(session_id, [])

        session = manager.get_session(session_id)
        assert session['active_files'] == []

    def test_large_active_files_list(self, manager):
        """Test handling large active files list"""
        session_id = manager.create_session(user_id="user123")
        files = [f"/path/to/file_{i}.py" for i in range(100)]
        manager.update_active_files(session_id, files)

        session = manager.get_session(session_id)
        assert len(session['active_files']) == 100


# ========== Integration Tests ==========

class TestIntegration:
    """Integration tests for complete workflows"""

    def test_full_session_lifecycle(self, manager):
        """Test complete session lifecycle"""
        # Create session
        session_id = manager.create_session(
            user_id="lifecycle_user",
            workspace_root="/project"
        )

        # Link chat and terminal
        manager.link_chat(session_id, "chat_1")
        manager.link_terminal(session_id, "terminal_1")

        # Update active files
        manager.update_active_files(session_id, ["/project/main.py"])

        # Verify session state
        session = manager.get_session(session_id)
        assert session['workspace_root'] == "/project"
        assert session['chat_id'] == "chat_1"
        assert session['terminal_id'] == "terminal_1"
        assert session['active_files'] == ["/project/main.py"]
        assert session['is_active'] is True

        # Close session
        manager.close_session(session_id)

        session = manager.get_session(session_id)
        assert session['is_active'] is False

    def test_workspace_switching(self, manager):
        """Test switching between workspaces"""
        user = "switch_user"

        # Work in first workspace
        session1 = manager.get_or_create_for_workspace(user, "/workspace1")
        manager.update_active_files(session1, ["/workspace1/file.py"])

        # Switch to second workspace
        session2 = manager.get_or_create_for_workspace(user, "/workspace2")
        manager.update_active_files(session2, ["/workspace2/file.py"])

        # Go back to first workspace (should reuse session)
        session1_again = manager.get_or_create_for_workspace(user, "/workspace1")

        assert session1 == session1_again
        assert session1 != session2

        # Verify files are preserved
        s1 = manager.get_session(session1)
        assert s1['active_files'] == ["/workspace1/file.py"]

    def test_multi_user_isolation(self, manager):
        """Test multiple users have isolated sessions"""
        # User A creates session
        session_a = manager.create_session(user_id="user_a", workspace_root="/shared")
        manager.update_active_files(session_a, ["/shared/a_file.py"])

        # User B creates session for same workspace
        session_b = manager.create_session(user_id="user_b", workspace_root="/shared")
        manager.update_active_files(session_b, ["/shared/b_file.py"])

        # Verify isolation
        s_a = manager.get_session(session_a)
        s_b = manager.get_session(session_b)

        assert s_a['active_files'] == ["/shared/a_file.py"]
        assert s_b['active_files'] == ["/shared/b_file.py"]
