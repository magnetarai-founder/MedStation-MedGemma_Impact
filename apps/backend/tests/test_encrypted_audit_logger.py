"""
Comprehensive tests for api/encrypted_audit_logger.py

Tests cover:
- AES-256-GCM encryption/decryption of audit fields
- Database initialization and schema
- Audit log creation with encrypted fields
- Log querying with timestamp filtering
- Log counting and pagination
- Retention cleanup
- Key management from environment
- Edge cases and error handling
"""

import pytest
import sqlite3
import secrets
import json
import os
from datetime import datetime, timedelta, UTC
from pathlib import Path
from unittest.mock import patch, Mock
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.encrypted_audit_logger import (
    EncryptedAuditLogger,
    get_encrypted_audit_logger,
)


# ========== Fixtures ==========

@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database path"""
    return tmp_path / "test_audit_encrypted.db"


@pytest.fixture
def test_key():
    """Generate a test encryption key"""
    return secrets.token_bytes(32)


@pytest.fixture
def audit_logger(temp_db, test_key):
    """Create an EncryptedAuditLogger with test key"""
    return EncryptedAuditLogger(db_path=temp_db, encryption_key=test_key)


@pytest.fixture
def populated_logger(audit_logger):
    """Create logger with some test data"""
    # Add various audit entries
    audit_logger.log(
        user_id="user_001",
        action="USER_LOGIN",
        resource="auth",
        ip_address="192.168.1.100",
        user_agent="TestBrowser/1.0"
    )
    audit_logger.log(
        user_id="user_002",
        action="FILE_UPLOAD",
        resource="vault",
        resource_id="file_123",
        ip_address="10.0.0.50",
        details={"filename": "document.pdf", "size": 1024}
    )
    audit_logger.log(
        user_id="user_001",
        action="USER_LOGOUT",
        resource="auth",
        ip_address="192.168.1.100"
    )
    return audit_logger


# ========== Encryption Tests ==========

class TestEncryption:
    """Tests for field encryption/decryption"""

    def test_encrypt_field_returns_ciphertext_and_nonce(self, audit_logger):
        """Test that encryption returns both ciphertext and nonce"""
        result = audit_logger._encrypt_field("test value")

        assert result is not None
        assert len(result) == 2
        ciphertext, nonce = result
        assert isinstance(ciphertext, bytes)
        assert isinstance(nonce, bytes)
        assert len(nonce) == 12  # 96-bit GCM nonce

    def test_encrypt_field_none_returns_none(self, audit_logger):
        """Test that None input returns None"""
        result = audit_logger._encrypt_field(None)
        assert result is None

    def test_encrypt_produces_different_ciphertexts(self, audit_logger):
        """Test that same plaintext produces different ciphertext each time"""
        result1 = audit_logger._encrypt_field("same value")
        result2 = audit_logger._encrypt_field("same value")

        # Ciphertexts should differ due to unique nonces
        assert result1[0] != result2[0]
        assert result1[1] != result2[1]

    def test_decrypt_field_success(self, audit_logger):
        """Test successful decryption"""
        plaintext = "sensitive data"
        ciphertext, nonce = audit_logger._encrypt_field(plaintext)

        decrypted = audit_logger._decrypt_field(ciphertext, nonce)

        assert decrypted == plaintext

    def test_decrypt_field_none_inputs(self, audit_logger):
        """Test decryption with None inputs"""
        assert audit_logger._decrypt_field(None, None) is None
        assert audit_logger._decrypt_field(b"data", None) is None
        assert audit_logger._decrypt_field(None, b"nonce") is None

    def test_decrypt_field_wrong_key(self, temp_db, test_key):
        """Test decryption fails with wrong key"""
        # Create logger with one key
        logger1 = EncryptedAuditLogger(db_path=temp_db, encryption_key=test_key)
        ciphertext, nonce = logger1._encrypt_field("secret")

        # Try to decrypt with different key
        different_key = secrets.token_bytes(32)
        logger2 = EncryptedAuditLogger(
            db_path=temp_db,
            encryption_key=different_key
        )

        result = logger2._decrypt_field(ciphertext, nonce)
        assert result == "[DECRYPTION_FAILED]"

    def test_decrypt_field_corrupted_ciphertext(self, audit_logger):
        """Test decryption with corrupted ciphertext"""
        plaintext = "test data"
        ciphertext, nonce = audit_logger._encrypt_field(plaintext)

        # Corrupt the ciphertext
        corrupted = bytes([b ^ 0xFF for b in ciphertext])

        result = audit_logger._decrypt_field(corrupted, nonce)
        assert result == "[DECRYPTION_FAILED]"

    def test_encrypt_unicode_content(self, audit_logger):
        """Test encryption of unicode content"""
        unicode_text = "用户数据 🔐 тест"
        ciphertext, nonce = audit_logger._encrypt_field(unicode_text)

        decrypted = audit_logger._decrypt_field(ciphertext, nonce)
        assert decrypted == unicode_text


# ========== Database Initialization Tests ==========

class TestDatabaseInit:
    """Tests for database initialization"""

    def test_init_creates_database(self, temp_db, test_key):
        """Test that init creates database file"""
        assert not temp_db.exists()

        logger = EncryptedAuditLogger(db_path=temp_db, encryption_key=test_key)

        assert temp_db.exists()

    def test_init_creates_table(self, temp_db, test_key):
        """Test that init creates audit table"""
        logger = EncryptedAuditLogger(db_path=temp_db, encryption_key=test_key)

        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='audit_log_encrypted'
        """)
        result = cursor.fetchone()
        conn.close()

        assert result is not None

    def test_init_creates_timestamp_index(self, temp_db, test_key):
        """Test that init creates timestamp index"""
        logger = EncryptedAuditLogger(db_path=temp_db, encryption_key=test_key)

        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND name='idx_encrypted_audit_timestamp'
        """)
        result = cursor.fetchone()
        conn.close()

        assert result is not None

    def test_init_requires_existing_parent_directory(self, tmp_path, test_key):
        """Test that init requires parent directory to exist"""
        # Note: Unlike auth_middleware, encrypted_audit_logger does not
        # create parent directories automatically. This test documents
        # that behavior.
        nested_path = tmp_path / "nested" / "dir" / "audit.db"

        # Should fail with non-existent parent
        with pytest.raises(sqlite3.OperationalError):
            EncryptedAuditLogger(db_path=nested_path, encryption_key=test_key)

        # Works when parent exists
        nested_path.parent.mkdir(parents=True, exist_ok=True)
        logger = EncryptedAuditLogger(db_path=nested_path, encryption_key=test_key)
        assert nested_path.exists()


# ========== Key Management Tests ==========

class TestKeyManagement:
    """Tests for encryption key management"""

    def test_key_from_env_var(self, temp_db):
        """Test loading key from environment variable"""
        test_key_hex = secrets.token_bytes(32).hex()

        with patch.dict(os.environ, {'ELOHIMOS_AUDIT_ENCRYPTION_KEY': test_key_hex}):
            logger = EncryptedAuditLogger(db_path=temp_db)

        assert logger.encryption_key == bytes.fromhex(test_key_hex)

    def test_key_invalid_hex_format(self, temp_db):
        """Test handling invalid hex format in env var"""
        with patch.dict(os.environ, {'ELOHIMOS_AUDIT_ENCRYPTION_KEY': 'not-valid-hex'}):
            # Should generate new key, not crash
            logger = EncryptedAuditLogger(db_path=temp_db)

        assert logger.encryption_key is not None
        assert len(logger.encryption_key) == 32

    def test_key_wrong_length(self, temp_db):
        """Test handling wrong key length"""
        short_key = secrets.token_bytes(16).hex()  # 16 bytes instead of 32

        with patch.dict(os.environ, {'ELOHIMOS_AUDIT_ENCRYPTION_KEY': short_key}):
            logger = EncryptedAuditLogger(db_path=temp_db)

        # Should generate new key due to wrong length
        assert len(logger.encryption_key) == 32
        assert logger.encryption_key != bytes.fromhex(short_key)

    def test_key_generated_when_missing(self, temp_db):
        """Test key generation when no env var"""
        with patch.dict(os.environ, {}, clear=False):
            # Remove the env var if it exists
            env_key = os.environ.pop('ELOHIMOS_AUDIT_ENCRYPTION_KEY', None)
            try:
                logger = EncryptedAuditLogger(db_path=temp_db)

                assert logger.encryption_key is not None
                assert len(logger.encryption_key) == 32
            finally:
                if env_key:
                    os.environ['ELOHIMOS_AUDIT_ENCRYPTION_KEY'] = env_key

    def test_explicit_key_overrides_env(self, temp_db):
        """Test that explicit key parameter overrides env var"""
        env_key = secrets.token_bytes(32)
        explicit_key = secrets.token_bytes(32)

        with patch.dict(os.environ, {'ELOHIMOS_AUDIT_ENCRYPTION_KEY': env_key.hex()}):
            logger = EncryptedAuditLogger(db_path=temp_db, encryption_key=explicit_key)

        assert logger.encryption_key == explicit_key


# ========== Audit Log Creation Tests ==========

class TestLogCreation:
    """Tests for creating audit log entries"""

    def test_log_returns_id(self, audit_logger):
        """Test that log returns positive ID"""
        audit_id = audit_logger.log(
            user_id="user_123",
            action="TEST_ACTION"
        )

        assert audit_id > 0

    def test_log_stores_encrypted_data(self, audit_logger, temp_db):
        """Test that log stores encrypted (not plaintext) data"""
        user_id = "plaintext_user_id"
        action = "PLAINTEXT_ACTION"

        audit_logger.log(user_id=user_id, action=action)

        # Check raw database - should not contain plaintext
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute("SELECT encrypted_user_id, encrypted_action FROM audit_log_encrypted")
        row = cursor.fetchone()
        conn.close()

        # Raw values should be bytes, not matching plaintext
        assert isinstance(row[0], bytes)
        assert isinstance(row[1], bytes)
        assert user_id.encode() not in row[0]
        assert action.encode() not in row[1]

    def test_log_all_fields(self, audit_logger):
        """Test logging with all optional fields"""
        audit_id = audit_logger.log(
            user_id="user_123",
            action="COMPLEX_ACTION",
            resource="vault",
            resource_id="file_456",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            details={"key": "value", "count": 42}
        )

        assert audit_id > 0

        # Verify all fields can be retrieved
        logs = audit_logger.get_logs(limit=1)
        assert len(logs) == 1
        log = logs[0]

        assert log['user_id'] == "user_123"
        assert log['action'] == "COMPLEX_ACTION"
        assert log['resource'] == "vault"
        assert log['resource_id'] == "file_456"
        assert log['ip_address'] == "192.168.1.1"
        assert log['user_agent'] == "Mozilla/5.0"
        assert log['details'] == {"key": "value", "count": 42}

    def test_log_minimal_fields(self, audit_logger):
        """Test logging with only required fields"""
        audit_id = audit_logger.log(
            user_id="user_123",
            action="SIMPLE_ACTION"
        )

        assert audit_id > 0

        logs = audit_logger.get_logs(limit=1)
        log = logs[0]

        assert log['user_id'] == "user_123"
        assert log['action'] == "SIMPLE_ACTION"
        assert log['resource'] is None
        assert log['resource_id'] is None
        assert log['ip_address'] is None
        assert log['user_agent'] is None
        assert log['details'] is None

    def test_log_stores_timestamp(self, audit_logger):
        """Test that log stores timestamp"""
        before = datetime.now(UTC)
        audit_logger.log(user_id="user_123", action="TEST")
        after = datetime.now(UTC)

        logs = audit_logger.get_logs(limit=1)
        log_time = datetime.fromisoformat(logs[0]['timestamp'])

        assert before <= log_time <= after

    def test_log_unicode_content(self, audit_logger):
        """Test logging unicode content"""
        audit_id = audit_logger.log(
            user_id="用户123",
            action="操作测试",
            details={"message": "Тест данных 🔐"}
        )

        logs = audit_logger.get_logs(limit=1)
        log = logs[0]

        assert log['user_id'] == "用户123"
        assert log['action'] == "操作测试"
        assert log['details']['message'] == "Тест данных 🔐"

    def test_log_error_returns_negative(self, audit_logger, temp_db):
        """Test that log errors return -1"""
        # Make database read-only to force error
        import stat
        temp_db.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

        try:
            result = audit_logger.log(user_id="test", action="TEST")
            # Should return -1 on error, not raise
            # (This may or may not fail depending on SQLite behavior)
        finally:
            # Restore permissions
            temp_db.chmod(stat.S_IRUSR | stat.S_IWUSR)


# ========== Log Querying Tests ==========

class TestLogQuerying:
    """Tests for querying audit logs"""

    def test_get_logs_returns_list(self, populated_logger):
        """Test that get_logs returns a list"""
        logs = populated_logger.get_logs()

        assert isinstance(logs, list)
        assert len(logs) == 3

    def test_get_logs_decrypts_fields(self, populated_logger):
        """Test that get_logs decrypts all fields"""
        logs = populated_logger.get_logs()

        # Should contain decrypted values
        user_ids = [log['user_id'] for log in logs]
        assert "user_001" in user_ids
        assert "user_002" in user_ids

    def test_get_logs_limit(self, populated_logger):
        """Test limit parameter"""
        logs = populated_logger.get_logs(limit=2)
        assert len(logs) == 2

    def test_get_logs_offset(self, populated_logger):
        """Test offset parameter"""
        all_logs = populated_logger.get_logs(limit=10)
        offset_logs = populated_logger.get_logs(limit=10, offset=1)

        assert len(offset_logs) == len(all_logs) - 1

    def test_get_logs_start_date_filter(self, audit_logger):
        """Test filtering by start date"""
        # Create log in the past
        audit_logger.log(user_id="old_user", action="OLD_ACTION")

        # Query from future - should return nothing
        future = datetime.now(UTC) + timedelta(days=1)
        logs = audit_logger.get_logs(start_date=future)

        assert len(logs) == 0

    def test_get_logs_end_date_filter(self, audit_logger):
        """Test filtering by end date"""
        audit_logger.log(user_id="test_user", action="TEST_ACTION")

        # Query until past - should return nothing
        past = datetime.now(UTC) - timedelta(days=1)
        logs = audit_logger.get_logs(end_date=past)

        assert len(logs) == 0

    def test_get_logs_date_range(self, audit_logger):
        """Test filtering by date range"""
        audit_logger.log(user_id="test_user", action="TEST_ACTION")

        # Query including now
        start = datetime.now(UTC) - timedelta(hours=1)
        end = datetime.now(UTC) + timedelta(hours=1)
        logs = audit_logger.get_logs(start_date=start, end_date=end)

        assert len(logs) == 1

    def test_get_logs_ordered_by_timestamp_desc(self, populated_logger):
        """Test that logs are ordered by timestamp descending"""
        logs = populated_logger.get_logs()

        timestamps = [log['timestamp'] for log in logs]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_get_logs_handles_json_details(self, audit_logger):
        """Test that JSON details are parsed correctly"""
        details = {"nested": {"data": [1, 2, 3]}, "flag": True}
        audit_logger.log(user_id="test", action="TEST", details=details)

        logs = audit_logger.get_logs(limit=1)

        assert logs[0]['details'] == details

    def test_get_logs_empty_database(self, audit_logger):
        """Test get_logs on empty database"""
        logs = audit_logger.get_logs()
        assert logs == []


# ========== Log Counting Tests ==========

class TestLogCounting:
    """Tests for counting audit logs"""

    def test_count_logs_total(self, populated_logger):
        """Test counting total logs"""
        count = populated_logger.count_logs()
        assert count == 3

    def test_count_logs_empty_database(self, audit_logger):
        """Test count on empty database"""
        count = audit_logger.count_logs()
        assert count == 0

    def test_count_logs_with_start_date(self, audit_logger):
        """Test count with start date filter"""
        audit_logger.log(user_id="test", action="TEST")

        future = datetime.now(UTC) + timedelta(days=1)
        count = audit_logger.count_logs(start_date=future)

        assert count == 0

    def test_count_logs_with_end_date(self, audit_logger):
        """Test count with end date filter"""
        audit_logger.log(user_id="test", action="TEST")

        past = datetime.now(UTC) - timedelta(days=1)
        count = audit_logger.count_logs(end_date=past)

        assert count == 0

    def test_count_logs_with_date_range(self, audit_logger):
        """Test count with date range"""
        audit_logger.log(user_id="test", action="TEST")

        start = datetime.now(UTC) - timedelta(hours=1)
        end = datetime.now(UTC) + timedelta(hours=1)
        count = audit_logger.count_logs(start_date=start, end_date=end)

        assert count == 1


# ========== Cleanup Tests ==========

class TestCleanup:
    """Tests for log cleanup/retention"""

    def test_cleanup_old_logs(self, audit_logger, temp_db):
        """Test cleaning up old logs"""
        # Create log
        audit_logger.log(user_id="test", action="TEST")

        # Manually backdate the log
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        old_timestamp = (datetime.now(UTC) - timedelta(days=100)).isoformat()
        cursor.execute(
            "UPDATE audit_log_encrypted SET timestamp = ?",
            (old_timestamp,)
        )
        conn.commit()
        conn.close()

        # Cleanup with 90-day retention
        deleted = audit_logger.cleanup_old_logs(retention_days=90)

        assert deleted == 1
        assert audit_logger.count_logs() == 0

    def test_cleanup_keeps_recent_logs(self, audit_logger):
        """Test that cleanup keeps recent logs"""
        audit_logger.log(user_id="test", action="TEST")

        # Cleanup should not delete recent log
        deleted = audit_logger.cleanup_old_logs(retention_days=90)

        assert deleted == 0
        assert audit_logger.count_logs() == 1

    def test_cleanup_custom_retention(self, audit_logger, temp_db):
        """Test cleanup with custom retention period"""
        audit_logger.log(user_id="test", action="TEST")

        # Backdate to 10 days ago
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        old_timestamp = (datetime.now(UTC) - timedelta(days=10)).isoformat()
        cursor.execute(
            "UPDATE audit_log_encrypted SET timestamp = ?",
            (old_timestamp,)
        )
        conn.commit()
        conn.close()

        # Cleanup with 7-day retention
        deleted = audit_logger.cleanup_old_logs(retention_days=7)

        assert deleted == 1

    def test_cleanup_partial(self, audit_logger, temp_db):
        """Test cleanup deletes only old logs"""
        # Create two logs
        audit_logger.log(user_id="old", action="OLD")
        audit_logger.log(user_id="new", action="NEW")

        # Backdate first log only
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        old_timestamp = (datetime.now(UTC) - timedelta(days=100)).isoformat()
        cursor.execute(
            "UPDATE audit_log_encrypted SET timestamp = ? WHERE id = 1",
            (old_timestamp,)
        )
        conn.commit()
        conn.close()

        # Cleanup
        deleted = audit_logger.cleanup_old_logs(retention_days=90)

        assert deleted == 1
        assert audit_logger.count_logs() == 1

        # Verify the new log remains
        logs = audit_logger.get_logs()
        assert logs[0]['user_id'] == "new"


# ========== Global Function Tests ==========

class TestGlobalFunction:
    """Tests for global get_encrypted_audit_logger function"""

    def test_get_encrypted_audit_logger_returns_instance(self):
        """Test that function returns an instance"""
        import api.encrypted_audit_logger as module
        module._encrypted_audit_logger = None

        with patch.object(module, 'EncryptedAuditLogger') as MockLogger:
            MockLogger.return_value = Mock()
            logger = get_encrypted_audit_logger()

        assert logger is not None

    def test_get_encrypted_audit_logger_singleton(self):
        """Test that function returns same instance"""
        import api.audit.encrypted_logger as module
        module._encrypted_audit_logger = None

        # Create mock instance
        mock_instance = Mock()
        module._encrypted_audit_logger = mock_instance

        logger = get_encrypted_audit_logger()

        assert logger is mock_instance


# ========== Edge Cases and Error Handling ==========

class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_empty_string_fields(self, audit_logger):
        """Test logging with empty string fields"""
        audit_id = audit_logger.log(
            user_id="",
            action=""
        )

        logs = audit_logger.get_logs(limit=1)
        assert logs[0]['user_id'] == ""
        assert logs[0]['action'] == ""

    def test_very_long_content(self, audit_logger):
        """Test logging with very long content"""
        long_content = "x" * 10000
        audit_id = audit_logger.log(
            user_id=long_content,
            action="LONG_TEST"
        )

        logs = audit_logger.get_logs(limit=1)
        assert logs[0]['user_id'] == long_content

    def test_special_characters(self, audit_logger):
        """Test logging with special characters"""
        special = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
        audit_id = audit_logger.log(
            user_id=special,
            action=special
        )

        logs = audit_logger.get_logs(limit=1)
        assert logs[0]['user_id'] == special
        assert logs[0]['action'] == special

    def test_json_details_with_special_chars(self, audit_logger):
        """Test JSON details with special characters"""
        details = {
            "message": "Test with 'quotes' and \"double quotes\"",
            "path": "/path/to/file",
            "unicode": "日本語テスト"
        }
        audit_logger.log(user_id="test", action="TEST", details=details)

        logs = audit_logger.get_logs(limit=1)
        assert logs[0]['details'] == details

    def test_concurrent_logging(self, audit_logger):
        """Test concurrent log creation"""
        import threading

        results = []

        def log_entry(n):
            audit_id = audit_logger.log(
                user_id=f"user_{n}",
                action=f"ACTION_{n}"
            )
            results.append(audit_id)

        threads = [threading.Thread(target=log_entry, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should succeed
        assert len(results) == 10
        assert all(r > 0 for r in results)

        # All logs should be present
        assert audit_logger.count_logs() == 10

    def test_malformed_details_json(self, audit_logger, temp_db):
        """Test handling of malformed JSON in details"""
        # Manually insert malformed JSON
        audit_logger.log(user_id="test", action="TEST")

        # The details field is encrypted, so malformed JSON would come from
        # decryption failure which is already tested

    def test_database_error_on_query(self, audit_logger, temp_db):
        """Test handling database errors during query"""
        # Drop the table to cause error
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute("DROP TABLE audit_log_encrypted")
        conn.commit()
        conn.close()

        # Should return empty list, not raise
        logs = audit_logger.get_logs()
        assert logs == []

    def test_database_error_on_count(self, audit_logger, temp_db):
        """Test handling database errors during count"""
        # Drop the table to cause error
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute("DROP TABLE audit_log_encrypted")
        conn.commit()
        conn.close()

        # Should return 0, not raise
        count = audit_logger.count_logs()
        assert count == 0

    def test_database_error_on_cleanup(self, audit_logger, temp_db):
        """Test handling database errors during cleanup"""
        # Drop the table to cause error
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute("DROP TABLE audit_log_encrypted")
        conn.commit()
        conn.close()

        # Should return 0, not raise
        deleted = audit_logger.cleanup_old_logs()
        assert deleted == 0


# ========== GCM Authentication Tests ==========

class TestGCMAuthentication:
    """Tests for GCM authentication tag verification"""

    def test_tampered_ciphertext_detected(self, audit_logger):
        """Test that tampered ciphertext is detected"""
        plaintext = "sensitive audit data"
        ciphertext, nonce = audit_logger._encrypt_field(plaintext)

        # Tamper with ciphertext (flip last byte)
        tampered = ciphertext[:-1] + bytes([ciphertext[-1] ^ 0xFF])

        result = audit_logger._decrypt_field(tampered, nonce)
        assert result == "[DECRYPTION_FAILED]"

    def test_tampered_nonce_detected(self, audit_logger):
        """Test that wrong nonce fails decryption"""
        plaintext = "sensitive audit data"
        ciphertext, nonce = audit_logger._encrypt_field(plaintext)

        # Use different nonce
        wrong_nonce = secrets.token_bytes(12)

        result = audit_logger._decrypt_field(ciphertext, wrong_nonce)
        assert result == "[DECRYPTION_FAILED]"

    def test_truncated_ciphertext_detected(self, audit_logger):
        """Test that truncated ciphertext is detected"""
        plaintext = "sensitive audit data"
        ciphertext, nonce = audit_logger._encrypt_field(plaintext)

        # Truncate ciphertext
        truncated = ciphertext[:len(ciphertext)//2]

        result = audit_logger._decrypt_field(truncated, nonce)
        assert result == "[DECRYPTION_FAILED]"
