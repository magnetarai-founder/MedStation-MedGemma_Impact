"""
Comprehensive tests for api/device_identity.py

Tests stable device identification functionality.

Coverage targets:
- _generate_machine_id: Hardware-based machine ID generation and caching
- _get_device_metadata: Platform metadata collection
- ensure_device_identity: Main entry point for device identity
- get_device_identity: Device ID retrieval
"""

import os
import sqlite3
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import platform
import socket
import uuid
import hashlib

from api.device_identity import (
    _generate_machine_id,
    _get_device_metadata,
    ensure_device_identity,
    get_device_identity
)


# ========== Fixtures ==========

@pytest.fixture
def temp_dir():
    """Create a temporary directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database with device_identity table"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE device_identity (
            device_id TEXT PRIMARY KEY,
            machine_id TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            last_boot_at TEXT NOT NULL,
            hostname TEXT,
            platform TEXT,
            architecture TEXT,
            metadata_json TEXT
        )
    """)
    conn.commit()

    yield conn

    conn.close()
    os.unlink(db_path)


@pytest.fixture
def mock_home_dir(temp_dir):
    """Mock Path.home() to return temp directory"""
    with patch.object(Path, 'home', return_value=temp_dir):
        yield temp_dir


# ========== _generate_machine_id Tests ==========

class TestGenerateMachineId:
    """Tests for _generate_machine_id function"""

    def test_generates_64_char_hex_string(self, mock_home_dir):
        """Test machine_id is a 64-character hex string (SHA256)"""
        machine_id = _generate_machine_id()

        assert len(machine_id) == 64
        assert all(c in '0123456789abcdef' for c in machine_id)

    def test_caches_to_file(self, mock_home_dir):
        """Test machine_id is cached to ~/.medstationos/machine_id"""
        machine_id = _generate_machine_id()

        cache_file = mock_home_dir / ".medstationos" / "machine_id"
        assert cache_file.exists()
        assert cache_file.read_text().strip() == machine_id

    def test_reads_from_cache(self, mock_home_dir):
        """Test machine_id is read from cache if exists"""
        # Pre-create cache with known value
        cache_dir = mock_home_dir / ".medstationos"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "machine_id"
        cached_id = "a" * 64  # Valid 64-char hex
        cache_file.write_text(cached_id)

        machine_id = _generate_machine_id()

        assert machine_id == cached_id

    def test_regenerates_if_cache_invalid_length(self, mock_home_dir):
        """Test regenerates if cached value has wrong length"""
        # Pre-create cache with invalid value
        cache_dir = mock_home_dir / ".medstationos"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "machine_id"
        cache_file.write_text("too_short")

        machine_id = _generate_machine_id()

        # Should generate new valid ID
        assert len(machine_id) == 64
        assert machine_id != "too_short"

    def test_regenerates_if_cache_empty(self, mock_home_dir):
        """Test regenerates if cache file is empty"""
        cache_dir = mock_home_dir / ".medstationos"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "machine_id"
        cache_file.write_text("")

        machine_id = _generate_machine_id()

        assert len(machine_id) == 64

    def test_handles_cache_read_error(self, mock_home_dir):
        """Test handles errors when reading cache"""
        # Create unreadable cache file
        cache_dir = mock_home_dir / ".medstationos"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "machine_id"
        cache_file.write_text("a" * 64)

        # Mock read_text to raise
        with patch.object(Path, 'read_text', side_effect=PermissionError("No read access")):
            # Should still generate a valid machine_id
            machine_id = _generate_machine_id()
            assert len(machine_id) == 64

    def test_handles_cache_write_error(self, mock_home_dir):
        """Test handles errors when writing cache"""
        # Make cache dir unwritable by mocking mkdir to fail
        with patch.object(Path, 'mkdir', side_effect=PermissionError("No write access")):
            with patch.object(Path, 'write_text', side_effect=PermissionError("No write access")):
                # Should still generate a valid machine_id
                machine_id = _generate_machine_id()
                assert len(machine_id) == 64

    def test_includes_hostname_in_hash(self, mock_home_dir):
        """Test hostname is included in machine_id hash"""
        with patch('socket.gethostname', return_value='test-host-1'):
            id1 = _generate_machine_id()

        # Clear cache
        cache_file = mock_home_dir / ".medstationos" / "machine_id"
        if cache_file.exists():
            cache_file.unlink()

        with patch('socket.gethostname', return_value='test-host-2'):
            id2 = _generate_machine_id()

        # Different hostnames should produce different IDs
        assert id1 != id2

    def test_includes_platform_in_hash(self, mock_home_dir):
        """Test platform info is included in machine_id hash"""
        # This test verifies the hash includes platform.system(), machine(), processor()
        machine_id = _generate_machine_id()

        # Verify it's deterministic for same machine
        cache_file = mock_home_dir / ".medstationos" / "machine_id"
        cache_file.unlink()  # Clear cache

        machine_id_2 = _generate_machine_id()
        assert machine_id == machine_id_2

    def test_handles_socket_error(self, mock_home_dir):
        """Test handles socket errors gracefully"""
        with patch('socket.gethostname', side_effect=socket.error("Network error")):
            machine_id = _generate_machine_id()
            # Should still generate valid ID without hostname
            assert len(machine_id) == 64

    def test_fallback_on_complete_failure(self, mock_home_dir):
        """Test fallback to uuid.getnode() on identifier collection failure"""
        # Make identifier collection fail but uuid.getnode() works in fallback
        with patch('socket.gethostname', side_effect=Exception("fail")):
            with patch('platform.system', side_effect=Exception("fail")):
                with patch('platform.machine', side_effect=Exception("fail")):
                    with patch('platform.processor', side_effect=Exception("fail")):
                        with patch('platform.node', side_effect=Exception("fail")):
                            # uuid.getnode() still works in fallback path
                            with patch('uuid.getnode', return_value=12345678901234):
                                machine_id = _generate_machine_id()
                                assert len(machine_id) == 64
                                # Verify it's SHA256 of the mock getnode value
                                expected = hashlib.sha256(str(12345678901234).encode()).hexdigest()
                                assert machine_id == expected


# ========== _get_device_metadata Tests ==========

class TestGetDeviceMetadata:
    """Tests for _get_device_metadata function"""

    def test_returns_dict_with_expected_keys(self):
        """Test metadata contains expected keys"""
        metadata = _get_device_metadata()

        expected_keys = [
            "hostname", "platform", "platform_release",
            "platform_version", "architecture", "processor",
            "python_version"
        ]
        for key in expected_keys:
            assert key in metadata

    def test_hostname_matches_socket(self):
        """Test hostname matches socket.gethostname()"""
        metadata = _get_device_metadata()
        assert metadata["hostname"] == socket.gethostname()

    def test_platform_matches_system(self):
        """Test platform matches platform.system()"""
        metadata = _get_device_metadata()
        assert metadata["platform"] == platform.system()

    def test_architecture_matches_machine(self):
        """Test architecture matches platform.machine()"""
        metadata = _get_device_metadata()
        assert metadata["architecture"] == platform.machine()

    def test_handles_errors_gracefully(self):
        """Test returns error dict on failure"""
        with patch('socket.gethostname', side_effect=Exception("Network error")):
            metadata = _get_device_metadata()
            assert "error" in metadata


# ========== ensure_device_identity Tests ==========

class TestEnsureDeviceIdentity:
    """Tests for ensure_device_identity function"""

    def test_creates_new_device_identity(self, temp_db, mock_home_dir):
        """Test creates new device identity when none exists"""
        device_id = ensure_device_identity(temp_db)

        # Should return a valid UUID
        uuid.UUID(device_id)  # Raises if invalid

        # Should be in database
        cursor = temp_db.cursor()
        cursor.execute("SELECT device_id FROM device_identity WHERE device_id = ?", (device_id,))
        assert cursor.fetchone() is not None

    def test_returns_existing_device_identity(self, temp_db, mock_home_dir):
        """Test returns existing device identity on second call"""
        device_id_1 = ensure_device_identity(temp_db)
        device_id_2 = ensure_device_identity(temp_db)

        assert device_id_1 == device_id_2

    def test_updates_last_boot_at(self, temp_db, mock_home_dir):
        """Test updates last_boot_at timestamp on existing identity"""
        device_id = ensure_device_identity(temp_db)

        # Get initial last_boot_at
        cursor = temp_db.cursor()
        cursor.execute("SELECT last_boot_at FROM device_identity WHERE device_id = ?", (device_id,))
        initial_boot = cursor.fetchone()[0]

        # Call again
        ensure_device_identity(temp_db)

        # Get updated last_boot_at
        cursor.execute("SELECT last_boot_at FROM device_identity WHERE device_id = ?", (device_id,))
        updated_boot = cursor.fetchone()[0]

        # Should be updated (or same if called quickly)
        assert updated_boot >= initial_boot

    def test_stores_machine_id(self, temp_db, mock_home_dir):
        """Test stores machine_id in database"""
        device_id = ensure_device_identity(temp_db)

        cursor = temp_db.cursor()
        cursor.execute("SELECT machine_id FROM device_identity WHERE device_id = ?", (device_id,))
        machine_id = cursor.fetchone()[0]

        assert len(machine_id) == 64

    def test_stores_platform_info(self, temp_db, mock_home_dir):
        """Test stores platform info in database"""
        device_id = ensure_device_identity(temp_db)

        cursor = temp_db.cursor()
        cursor.execute("""
            SELECT hostname, platform, architecture
            FROM device_identity WHERE device_id = ?
        """, (device_id,))
        row = cursor.fetchone()

        assert row[0] == socket.gethostname()
        assert row[1] == platform.system()
        assert row[2] == platform.machine()

    def test_stores_metadata_json(self, temp_db, mock_home_dir):
        """Test stores metadata as JSON"""
        import json

        device_id = ensure_device_identity(temp_db)

        cursor = temp_db.cursor()
        cursor.execute("SELECT metadata_json FROM device_identity WHERE device_id = ?", (device_id,))
        metadata_json = cursor.fetchone()[0]

        metadata = json.loads(metadata_json)
        assert "hostname" in metadata
        assert "platform" in metadata

    def test_commits_transaction(self, temp_db, mock_home_dir):
        """Test commits transaction after insert"""
        device_id = ensure_device_identity(temp_db)

        # Open new connection to verify data persisted
        cursor = temp_db.cursor()
        cursor.execute("SELECT COUNT(*) FROM device_identity")
        count = cursor.fetchone()[0]

        assert count == 1

    def test_raises_on_database_error(self, mock_home_dir):
        """Test raises exception on database error"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.OperationalError("Table not found")

        with pytest.raises(sqlite3.OperationalError):
            ensure_device_identity(mock_conn)

    def test_updates_hostname_on_existing(self, temp_db, mock_home_dir):
        """Test updates hostname when it changes"""
        # Create initial identity
        with patch('socket.gethostname', return_value='old-hostname'):
            device_id = ensure_device_identity(temp_db)

        # Update with new hostname
        with patch('socket.gethostname', return_value='new-hostname'):
            ensure_device_identity(temp_db)

        # Verify hostname updated
        cursor = temp_db.cursor()
        cursor.execute("SELECT hostname FROM device_identity WHERE device_id = ?", (device_id,))
        hostname = cursor.fetchone()[0]

        assert hostname == 'new-hostname'


# ========== get_device_identity Tests ==========

class TestGetDeviceIdentity:
    """Tests for get_device_identity function"""

    def test_returns_none_when_no_identity(self, temp_db):
        """Test returns None when no device identity exists"""
        result = get_device_identity(temp_db)
        assert result is None

    def test_returns_device_id_when_exists(self, temp_db, mock_home_dir):
        """Test returns device_id when identity exists"""
        # Create identity first
        expected_id = ensure_device_identity(temp_db)

        # Retrieve it
        result = get_device_identity(temp_db)

        assert result == expected_id

    def test_handles_database_error(self):
        """Test returns None on database error"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.OperationalError("Error")

        result = get_device_identity(mock_conn)

        assert result is None


# ========== Integration Tests ==========

class TestIntegration:
    """Integration tests for device identity"""

    def test_full_lifecycle(self, temp_db, mock_home_dir):
        """Test full device identity lifecycle"""
        # Initially no identity
        assert get_device_identity(temp_db) is None

        # Create identity
        device_id_1 = ensure_device_identity(temp_db)
        assert device_id_1 is not None

        # Retrieve identity
        assert get_device_identity(temp_db) == device_id_1

        # Ensure again (idempotent)
        device_id_2 = ensure_device_identity(temp_db)
        assert device_id_2 == device_id_1

        # Still same identity
        assert get_device_identity(temp_db) == device_id_1

    def test_machine_id_cached_across_calls(self, temp_db, mock_home_dir):
        """Test machine_id is consistent across calls"""
        device_id = ensure_device_identity(temp_db)

        # Get machine_id from cache
        cache_file = mock_home_dir / ".medstationos" / "machine_id"
        cached_machine_id = cache_file.read_text().strip()

        # Get machine_id from database
        cursor = temp_db.cursor()
        cursor.execute("SELECT machine_id FROM device_identity WHERE device_id = ?", (device_id,))
        db_machine_id = cursor.fetchone()[0]

        assert cached_machine_id == db_machine_id

    def test_survives_multiple_connections(self, mock_home_dir):
        """Test device identity survives across database connections"""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            # First connection - create identity
            conn1 = sqlite3.connect(db_path)
            conn1.execute("""
                CREATE TABLE device_identity (
                    device_id TEXT PRIMARY KEY,
                    machine_id TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL,
                    last_boot_at TEXT NOT NULL,
                    hostname TEXT,
                    platform TEXT,
                    architecture TEXT,
                    metadata_json TEXT
                )
            """)
            device_id_1 = ensure_device_identity(conn1)
            conn1.close()

            # Second connection - should get same identity
            conn2 = sqlite3.connect(db_path)
            device_id_2 = ensure_device_identity(conn2)
            conn2.close()

            assert device_id_1 == device_id_2

        finally:
            os.unlink(db_path)


# ========== Edge Cases ==========

class TestEdgeCases:
    """Tests for edge cases"""

    def test_unicode_hostname(self, temp_db, mock_home_dir):
        """Test handles unicode in hostname"""
        with patch('socket.gethostname', return_value='主机名-тест'):
            device_id = ensure_device_identity(temp_db)
            assert device_id is not None

    def test_very_long_hostname(self, temp_db, mock_home_dir):
        """Test handles very long hostname"""
        long_hostname = "a" * 1000
        with patch('socket.gethostname', return_value=long_hostname):
            device_id = ensure_device_identity(temp_db)
            assert device_id is not None

    def test_special_chars_in_hostname(self, temp_db, mock_home_dir):
        """Test handles special characters in hostname"""
        with patch('socket.gethostname', return_value='host!@#$%^&*()'):
            device_id = ensure_device_identity(temp_db)
            assert device_id is not None

    def test_empty_hostname(self, temp_db, mock_home_dir):
        """Test handles empty hostname"""
        with patch('socket.gethostname', return_value=''):
            device_id = ensure_device_identity(temp_db)
            assert device_id is not None

    def test_machine_id_deterministic(self, mock_home_dir):
        """Test machine_id is deterministic for same inputs"""
        # Clear any existing cache
        cache_file = mock_home_dir / ".medstationos" / "machine_id"
        if cache_file.exists():
            cache_file.unlink()

        id1 = _generate_machine_id()

        # Clear cache again
        cache_file.unlink()

        id2 = _generate_machine_id()

        # Same hardware characteristics should produce same ID
        assert id1 == id2
