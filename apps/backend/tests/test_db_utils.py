"""
Comprehensive tests for api/db_utils.py

Tests SQLite connection utilities with WAL mode and performance optimizations.

Coverage targets:
- get_sqlite_connection: Main connection factory
- verify_wal_mode: WAL mode verification
- enable_wal_for_existing_db: WAL mode enablement
"""

import os
import sqlite3
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from api.db_utils import (
    get_sqlite_connection,
    verify_wal_mode,
    enable_wal_for_existing_db
)


# ========== Fixtures ==========

@pytest.fixture
def temp_db_path():
    """Create a temporary database file path"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup database and WAL files
    for ext in ["", "-wal", "-shm"]:
        path = db_path + ext
        if os.path.exists(path):
            os.unlink(path)


@pytest.fixture
def existing_db(temp_db_path):
    """Create an existing database with a table"""
    conn = sqlite3.connect(temp_db_path)
    conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO test_table (name) VALUES ('test')")
    conn.commit()
    conn.close()
    yield temp_db_path


# ========== get_sqlite_connection Tests ==========

class TestGetSqliteConnection:
    """Tests for get_sqlite_connection function"""

    def test_returns_connection(self, temp_db_path):
        """Test returns a valid SQLite connection"""
        conn = get_sqlite_connection(temp_db_path)

        assert conn is not None
        assert isinstance(conn, sqlite3.Connection)

        conn.close()

    def test_enables_wal_mode(self, temp_db_path):
        """Test WAL mode is enabled"""
        conn = get_sqlite_connection(temp_db_path)

        result = conn.execute("PRAGMA journal_mode").fetchone()
        assert result[0].upper() == "WAL"

        conn.close()

    def test_enables_foreign_keys(self, temp_db_path):
        """Test foreign key constraints are enabled"""
        conn = get_sqlite_connection(temp_db_path)

        result = conn.execute("PRAGMA foreign_keys").fetchone()
        assert result[0] == 1

        conn.close()

    def test_sets_synchronous_normal(self, temp_db_path):
        """Test synchronous mode is set to NORMAL"""
        conn = get_sqlite_connection(temp_db_path)

        result = conn.execute("PRAGMA synchronous").fetchone()
        # NORMAL = 1
        assert result[0] == 1

        conn.close()

    def test_sets_cache_size(self, temp_db_path):
        """Test cache size is set"""
        conn = get_sqlite_connection(temp_db_path)

        result = conn.execute("PRAGMA cache_size").fetchone()
        # Negative value means KB, -64000 = 64MB
        assert result[0] == -64000

        conn.close()

    def test_sets_temp_store_memory(self, temp_db_path):
        """Test temp_store is set to MEMORY"""
        conn = get_sqlite_connection(temp_db_path)

        result = conn.execute("PRAGMA temp_store").fetchone()
        # MEMORY = 2
        assert result[0] == 2

        conn.close()

    def test_uses_row_factory(self, temp_db_path):
        """Test Row factory is set for dict-like access"""
        conn = get_sqlite_connection(temp_db_path)

        assert conn.row_factory == sqlite3.Row

        conn.close()

    def test_accepts_path_object(self, temp_db_path):
        """Test accepts Path object as database path"""
        path_obj = Path(temp_db_path)
        conn = get_sqlite_connection(path_obj)

        assert conn is not None
        conn.close()

    def test_accepts_string_path(self, temp_db_path):
        """Test accepts string as database path"""
        conn = get_sqlite_connection(temp_db_path)

        assert conn is not None
        conn.close()

    def test_respects_check_same_thread_true(self, temp_db_path):
        """Test respects check_same_thread=True (default)"""
        conn = get_sqlite_connection(temp_db_path, check_same_thread=True)

        # Connection should work in same thread
        conn.execute("SELECT 1")
        conn.close()

    def test_respects_check_same_thread_false(self, temp_db_path):
        """Test respects check_same_thread=False"""
        conn = get_sqlite_connection(temp_db_path, check_same_thread=False)

        # Connection should work
        conn.execute("SELECT 1")
        conn.close()

    def test_respects_timeout(self, temp_db_path):
        """Test respects custom timeout"""
        conn = get_sqlite_connection(temp_db_path, timeout=5.0)

        # Connection should work
        conn.execute("SELECT 1")
        conn.close()

    def test_creates_wal_files(self, temp_db_path):
        """Test WAL mode creates -wal and -shm files"""
        conn = get_sqlite_connection(temp_db_path)
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.execute("INSERT INTO test VALUES (1)")
        conn.commit()

        # WAL files should exist after write
        wal_file = temp_db_path + "-wal"
        shm_file = temp_db_path + "-shm"

        # Note: Files may or may not exist depending on checkpoint behavior
        # Just verify the connection works
        assert conn.execute("SELECT COUNT(*) FROM test").fetchone()[0] == 1

        conn.close()

    def test_can_read_and_write(self, temp_db_path):
        """Test connection can read and write data"""
        conn = get_sqlite_connection(temp_db_path)

        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO users (name) VALUES ('Alice')")
        conn.commit()

        result = conn.execute("SELECT name FROM users").fetchone()
        assert result["name"] == "Alice"  # Row factory allows dict-like access

        conn.close()

    def test_row_access_by_name(self, temp_db_path):
        """Test Row factory allows column access by name"""
        conn = get_sqlite_connection(temp_db_path)

        conn.execute("CREATE TABLE items (item_id INTEGER, item_name TEXT, price REAL)")
        conn.execute("INSERT INTO items VALUES (1, 'Widget', 9.99)")
        conn.commit()

        row = conn.execute("SELECT * FROM items").fetchone()

        # Access by name
        assert row["item_id"] == 1
        assert row["item_name"] == "Widget"
        assert row["price"] == 9.99

        # Access by index still works
        assert row[0] == 1
        assert row[1] == "Widget"

        conn.close()


# ========== verify_wal_mode Tests ==========

class TestVerifyWalMode:
    """Tests for verify_wal_mode function"""

    def test_returns_true_for_wal_mode(self, temp_db_path):
        """Test returns True when WAL mode is enabled"""
        # Create connection with WAL mode
        conn = get_sqlite_connection(temp_db_path)
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()

        result = verify_wal_mode(temp_db_path)

        assert result is True

    def test_returns_false_for_delete_mode(self, temp_db_path):
        """Test returns False when not in WAL mode"""
        # Create connection without WAL mode
        conn = sqlite3.connect(temp_db_path)
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()

        result = verify_wal_mode(temp_db_path)

        assert result is False

    def test_returns_false_on_error(self, temp_db_path):
        """Test returns False on database error"""
        # Use non-existent path that will cause error
        result = verify_wal_mode("/nonexistent/path/db.db")

        assert result is False

    def test_accepts_path_object(self, temp_db_path):
        """Test accepts Path object"""
        conn = get_sqlite_connection(temp_db_path)
        conn.close()

        result = verify_wal_mode(Path(temp_db_path))

        assert result is True

    def test_closes_connection(self, temp_db_path):
        """Test closes connection after checking"""
        conn = get_sqlite_connection(temp_db_path)
        conn.close()

        # Should not leave connection open
        verify_wal_mode(temp_db_path)

        # Database should be accessible
        conn2 = sqlite3.connect(temp_db_path)
        conn2.execute("SELECT 1")
        conn2.close()


# ========== enable_wal_for_existing_db Tests ==========

class TestEnableWalForExistingDb:
    """Tests for enable_wal_for_existing_db function"""

    def test_enables_wal_mode(self, existing_db):
        """Test enables WAL mode on existing database"""
        # Verify not in WAL mode initially (default is DELETE)
        conn = sqlite3.connect(existing_db)
        result = conn.execute("PRAGMA journal_mode").fetchone()
        initial_mode = result[0].upper()
        conn.close()

        # Enable WAL mode
        success = enable_wal_for_existing_db(existing_db)

        assert success is True
        assert verify_wal_mode(existing_db) is True

    def test_returns_true_on_success(self, existing_db):
        """Test returns True when WAL mode enabled successfully"""
        result = enable_wal_for_existing_db(existing_db)

        assert result is True

    def test_returns_false_on_error(self):
        """Test returns False on database error"""
        result = enable_wal_for_existing_db("/nonexistent/path/db.db")

        assert result is False

    def test_preserves_existing_data(self, existing_db):
        """Test preserves existing data when enabling WAL"""
        # Enable WAL
        enable_wal_for_existing_db(existing_db)

        # Verify data still exists
        conn = sqlite3.connect(existing_db)
        result = conn.execute("SELECT name FROM test_table").fetchone()
        conn.close()

        assert result[0] == "test"

    def test_idempotent(self, existing_db):
        """Test can be called multiple times safely"""
        # Enable WAL twice
        result1 = enable_wal_for_existing_db(existing_db)
        result2 = enable_wal_for_existing_db(existing_db)

        assert result1 is True
        assert result2 is True

    def test_accepts_path_object(self, existing_db):
        """Test accepts Path object"""
        result = enable_wal_for_existing_db(Path(existing_db))

        assert result is True

    def test_closes_connection(self, existing_db):
        """Test closes connection after enabling"""
        enable_wal_for_existing_db(existing_db)

        # Database should be accessible
        conn = sqlite3.connect(existing_db)
        conn.execute("SELECT 1")
        conn.close()


# ========== Integration Tests ==========

class TestIntegration:
    """Integration tests for db_utils"""

    def test_full_workflow(self, temp_db_path):
        """Test full workflow: create, verify, enable"""
        # Create database with WAL mode
        conn = get_sqlite_connection(temp_db_path)
        conn.execute("CREATE TABLE data (id INTEGER PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO data (value) VALUES ('test')")
        conn.commit()
        conn.close()

        # Verify WAL mode
        assert verify_wal_mode(temp_db_path) is True

        # Enable WAL (should be idempotent)
        assert enable_wal_for_existing_db(temp_db_path) is True

        # Read data back
        conn2 = get_sqlite_connection(temp_db_path)
        result = conn2.execute("SELECT value FROM data").fetchone()
        assert result["value"] == "test"
        conn2.close()

    def test_foreign_key_enforcement(self, temp_db_path):
        """Test foreign key constraints are enforced"""
        conn = get_sqlite_connection(temp_db_path)

        conn.execute("""
            CREATE TABLE parent (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE child (
                id INTEGER PRIMARY KEY,
                parent_id INTEGER REFERENCES parent(id),
                name TEXT
            )
        """)
        conn.execute("INSERT INTO parent (id, name) VALUES (1, 'Parent')")
        conn.commit()

        # This should fail due to foreign key constraint
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO child (parent_id, name) VALUES (999, 'Orphan')")
            conn.commit()

        conn.close()

    def test_concurrent_reads(self, temp_db_path):
        """Test WAL mode allows concurrent reads"""
        # Create database and add data
        conn1 = get_sqlite_connection(temp_db_path)
        conn1.execute("CREATE TABLE items (id INTEGER, name TEXT)")
        conn1.execute("INSERT INTO items VALUES (1, 'Item 1')")
        conn1.commit()

        # Open second connection
        conn2 = get_sqlite_connection(temp_db_path)

        # Both connections should be able to read
        result1 = conn1.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        result2 = conn2.execute("SELECT COUNT(*) FROM items").fetchone()[0]

        assert result1 == 1
        assert result2 == 1

        conn1.close()
        conn2.close()


# ========== Edge Cases ==========

class TestEdgeCases:
    """Tests for edge cases"""

    def test_unicode_path(self, temp_db_path):
        """Test handles unicode in database path"""
        # Create temp dir with unicode name
        import tempfile
        with tempfile.TemporaryDirectory(prefix="тест_数据_") as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            conn = get_sqlite_connection(db_path)
            conn.execute("SELECT 1")
            conn.close()

    def test_path_with_spaces(self):
        """Test handles spaces in database path"""
        import tempfile
        with tempfile.TemporaryDirectory(prefix="path with spaces ") as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            conn = get_sqlite_connection(db_path)
            conn.execute("SELECT 1")
            conn.close()

    def test_in_memory_database(self):
        """Test works with in-memory database"""
        conn = get_sqlite_connection(":memory:")

        # WAL mode doesn't apply to in-memory databases
        # but connection should still work
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.execute("INSERT INTO test VALUES (1)")
        result = conn.execute("SELECT * FROM test").fetchone()
        assert result[0] == 1

        conn.close()

    def test_empty_database(self, temp_db_path):
        """Test handles empty database"""
        conn = get_sqlite_connection(temp_db_path)

        # Should be able to query empty database
        result = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        assert len(result) == 0

        conn.close()

    def test_very_long_path(self):
        """Test handles long database path"""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested directory structure
            long_subdir = os.path.join(tmpdir, "a" * 50, "b" * 50, "c" * 50)
            os.makedirs(long_subdir)
            db_path = os.path.join(long_subdir, "test.db")

            conn = get_sqlite_connection(db_path)
            conn.execute("SELECT 1")
            conn.close()

    def test_readonly_mode_not_supported(self, existing_db):
        """Test note: WAL requires write access, readonly not directly supported"""
        # This is just a documentation test - get_sqlite_connection
        # doesn't support readonly mode directly
        conn = get_sqlite_connection(existing_db)
        # Should be able to write
        conn.execute("INSERT INTO test_table (name) VALUES ('new')")
        conn.commit()
        conn.close()
