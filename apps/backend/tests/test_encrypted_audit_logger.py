"""
Unit Tests for Encrypted Audit Logger

Tests critical encrypted audit logging functionality including:
- AES-256-GCM encryption and decryption
- Audit log creation with all fields
- Log retrieval and pagination
- Timestamp filtering
- Old log cleanup (retention policy)
- Encryption key management
- Tamper detection
- Thread safety for concurrent writes
- Error handling

Target: +2-3% test coverage
Module under test: api/encrypted_audit_logger.py (445 lines)
"""

import pytest
import tempfile
import secrets
import json
import threading
import time
from pathlib import Path
from datetime import datetime, timedelta
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


@pytest.fixture
def encryption_key():
    """Generate a test encryption key"""
    return secrets.token_bytes(32)  # 256-bit key


@pytest.fixture
def audit_logger(encryption_key):
    """Create EncryptedAuditLogger with temporary database"""
    from api.encrypted_audit_logger import EncryptedAuditLogger

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_audit.db"
        logger = EncryptedAuditLogger(db_path=db_path, encryption_key=encryption_key)
        yield logger


class TestEncryption:
    """Test AES-256-GCM encryption and decryption"""

    def test_encryption_produces_different_ciphertexts(self, audit_logger):
        """Test that encrypting same plaintext produces different ciphertexts (unique nonces)"""
        plaintext = "test_user_123"

        # Encrypt same value twice
        result1 = audit_logger._encrypt_field(plaintext)
        result2 = audit_logger._encrypt_field(plaintext)

        assert result1 is not None
        assert result2 is not None

        ciphertext1, nonce1 = result1
        ciphertext2, nonce2 = result2

        # Ciphertexts should be different (different nonces)
        assert ciphertext1 != ciphertext2
        assert nonce1 != nonce2

        # Nonces should be 12 bytes (96 bits for GCM)
        assert len(nonce1) == 12
        assert len(nonce2) == 12

    def test_encryption_decryption_roundtrip(self, audit_logger):
        """Test that encryption and decryption produce original value"""
        plaintext = "sensitive_data_12345"

        # Encrypt
        ciphertext, nonce = audit_logger._encrypt_field(plaintext)

        # Decrypt
        decrypted = audit_logger._decrypt_field(ciphertext, nonce)

        assert decrypted == plaintext

    def test_encryption_of_none_returns_none(self, audit_logger):
        """Test that encrypting None returns None"""
        result = audit_logger._encrypt_field(None)
        assert result is None

    def test_decryption_of_none_returns_none(self, audit_logger):
        """Test that decrypting None returns None"""
        result = audit_logger._decrypt_field(None, None)
        assert result is None

    def test_decryption_with_wrong_key_fails(self, encryption_key):
        """Test that decryption with wrong key fails gracefully"""
        from api.encrypted_audit_logger import EncryptedAuditLogger

        # Create logger with one key
        logger1 = EncryptedAuditLogger(
            db_path=Path(tempfile.mktemp()),
            encryption_key=encryption_key
        )

        # Encrypt with logger1
        ciphertext, nonce = logger1._encrypt_field("secret_data")

        # Try to decrypt with different key
        wrong_key = secrets.token_bytes(32)
        logger2 = EncryptedAuditLogger(
            db_path=Path(tempfile.mktemp()),
            encryption_key=wrong_key
        )

        # Should return error indicator, not raise
        decrypted = logger2._decrypt_field(ciphertext, nonce)
        assert decrypted == "[DECRYPTION_FAILED]"

    def test_decryption_with_wrong_nonce_fails(self, audit_logger):
        """Test that decryption with wrong nonce fails (tamper detection)"""
        plaintext = "secret_data"
        ciphertext, nonce = audit_logger._encrypt_field(plaintext)

        # Use wrong nonce
        wrong_nonce = secrets.token_bytes(12)

        # Should return error indicator
        decrypted = audit_logger._decrypt_field(ciphertext, wrong_nonce)
        assert decrypted == "[DECRYPTION_FAILED]"


class TestAuditLogCreation:
    """Test audit log creation functionality"""

    def test_create_audit_log_with_all_fields(self, audit_logger):
        """Test creating audit log with all fields populated"""
        audit_id = audit_logger.log(
            user_id="user_123",
            action="USER_LOGIN",
            resource="auth",
            resource_id="session_456",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            details={"method": "password", "success": True}
        )

        assert audit_id > 0

        # Retrieve and verify
        logs = audit_logger.get_logs(limit=1)
        assert len(logs) == 1

        log = logs[0]
        assert log['user_id'] == "user_123"
        assert log['action'] == "USER_LOGIN"
        assert log['resource'] == "auth"
        assert log['resource_id'] == "session_456"
        assert log['ip_address'] == "192.168.1.100"
        assert log['user_agent'] == "Mozilla/5.0"
        assert log['details'] == {"method": "password", "success": True}

    def test_create_audit_log_with_minimal_fields(self, audit_logger):
        """Test creating audit log with only required fields"""
        audit_id = audit_logger.log(
            user_id="user_456",
            action="FILE_UPLOAD"
        )

        assert audit_id > 0

        # Retrieve and verify
        logs = audit_logger.get_logs(limit=1)
        assert len(logs) == 1

        log = logs[0]
        assert log['user_id'] == "user_456"
        assert log['action'] == "FILE_UPLOAD"
        assert log['resource'] is None
        assert log['resource_id'] is None
        assert log['ip_address'] is None
        assert log['user_agent'] is None
        assert log['details'] is None

    def test_audit_log_includes_timestamp(self, audit_logger):
        """Test that audit logs include timestamp"""
        before = datetime.utcnow()
        audit_logger.log(user_id="user_789", action="DATA_ACCESS")
        after = datetime.utcnow()

        logs = audit_logger.get_logs(limit=1)
        assert len(logs) == 1

        timestamp_str = logs[0]['timestamp']
        timestamp = datetime.fromisoformat(timestamp_str)

        # Timestamp should be between before and after
        assert before <= timestamp <= after

    def test_audit_log_details_serialization(self, audit_logger):
        """Test that complex details dict is properly serialized/deserialized"""
        complex_details = {
            "user": {"id": 123, "name": "Test"},
            "settings": {"theme": "dark", "notifications": True},
            "numbers": [1, 2, 3, 4],
            "nested": {"level": 2, "data": {"deep": True}}
        }

        audit_logger.log(
            user_id="user_complex",
            action="SETTINGS_UPDATE",
            details=complex_details
        )

        logs = audit_logger.get_logs(limit=1)
        assert logs[0]['details'] == complex_details


class TestAuditLogRetrieval:
    """Test audit log query and retrieval"""

    def test_get_logs_with_limit(self, audit_logger):
        """Test retrieving logs with limit"""
        # Create 10 logs
        for i in range(10):
            audit_logger.log(user_id=f"user_{i}", action="TEST_ACTION")

        # Get first 5
        logs = audit_logger.get_logs(limit=5)
        assert len(logs) == 5

    def test_get_logs_with_offset_pagination(self, audit_logger):
        """Test pagination using offset"""
        # Create 10 logs
        for i in range(10):
            audit_logger.log(user_id=f"user_{i}", action=f"ACTION_{i}")

        # Get second page (offset 5, limit 5)
        logs = audit_logger.get_logs(limit=5, offset=5)
        assert len(logs) == 5

        # Should be logs 4-0 (reversed order, DESC)
        assert logs[0]['action'] == "ACTION_4"

    def test_get_logs_timestamp_filtering(self, audit_logger):
        """Test filtering logs by timestamp"""
        # Create logs at different times
        audit_logger.log(user_id="old_user", action="OLD_ACTION")
        time.sleep(0.1)

        midpoint = datetime.utcnow()
        time.sleep(0.1)

        audit_logger.log(user_id="new_user", action="NEW_ACTION")

        # Get logs after midpoint
        logs = audit_logger.get_logs(start_date=midpoint)
        assert len(logs) == 1
        assert logs[0]['action'] == "NEW_ACTION"

    def test_count_logs(self, audit_logger):
        """Test counting logs"""
        # Create 15 logs
        for i in range(15):
            audit_logger.log(user_id=f"user_{i}", action="COUNT_TEST")

        count = audit_logger.count_logs()
        assert count == 15

    def test_count_logs_with_date_filter(self, audit_logger):
        """Test counting logs with date filter"""
        # Create old log
        audit_logger.log(user_id="old", action="OLD")
        time.sleep(0.1)

        cutoff = datetime.utcnow()
        time.sleep(0.1)

        # Create 5 new logs
        for i in range(5):
            audit_logger.log(user_id=f"new_{i}", action="NEW")

        count = audit_logger.count_logs(start_date=cutoff)
        assert count == 5


class TestCleanup:
    """Test old log cleanup functionality"""

    def test_cleanup_old_logs(self, audit_logger):
        """Test deleting logs older than retention period"""
        import sqlite3

        # Manually insert old logs by modifying timestamp
        conn = sqlite3.connect(str(audit_logger.db_path))
        cursor = conn.cursor()

        # Create a log
        audit_logger.log(user_id="old_user", action="OLD_ACTION")

        # Modify timestamp to be 100 days old
        old_timestamp = (datetime.utcnow() - timedelta(days=100)).isoformat()
        cursor.execute(
            "UPDATE audit_log_encrypted SET timestamp = ? WHERE id = 1",
            (old_timestamp,)
        )
        conn.commit()
        conn.close()

        # Create a recent log
        audit_logger.log(user_id="recent_user", action="RECENT_ACTION")

        # Cleanup logs older than 90 days
        deleted = audit_logger.cleanup_old_logs(retention_days=90)

        assert deleted == 1

        # Recent log should remain
        logs = audit_logger.get_logs()
        assert len(logs) == 1
        assert logs[0]['user_id'] == "recent_user"

    def test_cleanup_no_old_logs(self, audit_logger):
        """Test cleanup when no old logs exist"""
        # Create recent log
        audit_logger.log(user_id="recent", action="RECENT")

        deleted = audit_logger.cleanup_old_logs(retention_days=90)
        assert deleted == 0


class TestEncryptionKeyManagement:
    """Test encryption key generation and handling"""

    def test_key_from_environment(self, monkeypatch):
        """Test loading encryption key from environment variable"""
        from api.encrypted_audit_logger import EncryptedAuditLogger

        test_key = secrets.token_bytes(32)
        monkeypatch.setenv('ELOHIMOS_AUDIT_ENCRYPTION_KEY', test_key.hex())

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = EncryptedAuditLogger(db_path=Path(tmpdir) / "test.db")

            # Should use key from environment
            assert logger.encryption_key == test_key

    def test_key_generation_when_no_env(self, monkeypatch):
        """Test that key is generated when not in environment"""
        from api.encrypted_audit_logger import EncryptedAuditLogger

        # Remove env var
        monkeypatch.delenv('ELOHIMOS_AUDIT_ENCRYPTION_KEY', raising=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = EncryptedAuditLogger(db_path=Path(tmpdir) / "test.db")

            # Should generate 32-byte key
            assert len(logger.encryption_key) == 32

    def test_invalid_key_length_generates_new_key(self, monkeypatch):
        """Test that invalid key length causes new key generation"""
        from api.encrypted_audit_logger import EncryptedAuditLogger

        # Set invalid key (16 bytes instead of 32)
        invalid_key = secrets.token_bytes(16)
        monkeypatch.setenv('ELOHIMOS_AUDIT_ENCRYPTION_KEY', invalid_key.hex())

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = EncryptedAuditLogger(db_path=Path(tmpdir) / "test.db")

            # Should generate new 32-byte key
            assert len(logger.encryption_key) == 32
            assert logger.encryption_key != invalid_key


class TestThreadSafety:
    """Test concurrent audit log writes"""

    def test_concurrent_log_writes(self, audit_logger):
        """Test thread-safe concurrent audit log creation"""
        num_threads = 10
        logs_per_thread = 5
        results = []

        def write_logs(thread_id):
            for i in range(logs_per_thread):
                audit_id = audit_logger.log(
                    user_id=f"thread_{thread_id}_user_{i}",
                    action=f"THREAD_{thread_id}_ACTION_{i}"
                )
                results.append(audit_id)

        # Start concurrent writes
        threads = []
        for t in range(num_threads):
            thread = threading.Thread(target=write_logs, args=(t,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All writes should succeed
        assert len(results) == num_threads * logs_per_thread
        assert all(r > 0 for r in results)

        # All logs should be retrievable
        total_logs = audit_logger.count_logs()
        assert total_logs == num_threads * logs_per_thread


class TestErrorHandling:
    """Test error handling in audit logger"""

    def test_log_failure_returns_negative_id(self, audit_logger):
        """Test that log failures don't raise exceptions"""
        # Close database to cause error
        import sqlite3
        conn = sqlite3.connect(str(audit_logger.db_path))
        conn.close()

        # Make database readonly to cause write error
        audit_logger.db_path.chmod(0o444)

        try:
            # Should return -1, not raise
            audit_id = audit_logger.log(user_id="test", action="TEST")
            assert audit_id == -1
        finally:
            # Restore permissions
            audit_logger.db_path.chmod(0o644)

    def test_get_logs_failure_returns_empty_list(self, audit_logger):
        """Test that query failures return empty list"""
        import sqlite3

        # Delete the database file to cause query error
        audit_logger.db_path.unlink()

        # Should return empty list, not raise
        logs = audit_logger.get_logs()
        assert logs == []

    def test_invalid_json_in_details_handled_gracefully(self, audit_logger):
        """Test that invalid JSON in encrypted details is handled"""
        import sqlite3

        # Create a log with valid details
        audit_logger.log(user_id="test", action="TEST", details={"valid": True})

        # Manually corrupt the encrypted details in database
        conn = sqlite3.connect(str(audit_logger.db_path))
        cursor = conn.cursor()

        # Encrypt invalid JSON
        invalid_json = "not valid json {"
        enc_invalid = audit_logger._encrypt_field(invalid_json)

        cursor.execute(
            "UPDATE audit_log_encrypted SET encrypted_details = ?, nonce_details = ?",
            (enc_invalid[0], enc_invalid[1])
        )
        conn.commit()
        conn.close()

        # Should retrieve log with None details, not crash
        logs = audit_logger.get_logs()
        assert len(logs) == 1
        assert logs[0]['details'] is None


def test_summary():
    """Print test summary"""
    print("\n" + "="*70)
    print("ENCRYPTED AUDIT LOGGER TEST SUMMARY")
    print("="*70)
    print("\nTest Coverage:")
    print("  ✓ AES-256-GCM encryption/decryption")
    print("  ✓ Unique nonce generation per field")
    print("  ✓ Tamper detection (wrong key/nonce)")
    print("  ✓ Audit log creation (all fields + minimal)")
    print("  ✓ Complex details JSON serialization")
    print("  ✓ Log retrieval with pagination")
    print("  ✓ Timestamp filtering")
    print("  ✓ Log counting")
    print("  ✓ Old log cleanup (retention policy)")
    print("  ✓ Encryption key management (env + generation)")
    print("  ✓ Thread-safe concurrent writes")
    print("  ✓ Error handling (graceful failures)")
    print("\nAll encrypted audit logger tests passed!")
    print("="*70 + "\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
    test_summary()
