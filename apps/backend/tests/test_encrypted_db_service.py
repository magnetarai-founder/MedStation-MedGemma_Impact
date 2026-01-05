"""
Comprehensive tests for api/encrypted_db_service.py

Tests cover:
- EncryptedDatabase class
  - Key derivation from passphrase (PBKDF2-HMAC-SHA256)
  - Database encryption with AES-256-GCM
  - Database decryption
  - Connect/close lifecycle
  - Migration from plaintext
- BackupCodesService
  - Code generation format
  - Code hashing
  - Code verification (timing-safe)
  - Code storage in database
- Global functions
- Edge cases and error handling
"""

import pytest
import sqlite3
import secrets
import os
from pathlib import Path
from unittest.mock import Mock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.encrypted_db_service import (
    EncryptedDatabase,
    BackupCodesService,
    get_encrypted_database,
)


# ========== Fixtures ==========

@pytest.fixture
def temp_db_dir(tmp_path):
    """Create a temporary directory for databases"""
    db_dir = tmp_path / "databases"
    db_dir.mkdir()
    return db_dir


@pytest.fixture
def temp_db_path(temp_db_dir):
    """Create a temporary database path"""
    return temp_db_dir / "test.db"


@pytest.fixture
def test_passphrase():
    """Standard test passphrase"""
    return "SecureTestPassphrase123!"


@pytest.fixture
def plaintext_db(temp_db_path):
    """Create a plaintext SQLite database with test data"""
    conn = sqlite3.connect(str(temp_db_path))
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE test_table (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            value INTEGER
        )
    """)

    cursor.executemany(
        "INSERT INTO test_table (name, value) VALUES (?, ?)",
        [("row1", 100), ("row2", 200), ("row3", 300)]
    )

    conn.commit()
    conn.close()

    return temp_db_path


@pytest.fixture
def encrypted_db(temp_db_path, test_passphrase):
    """Create an EncryptedDatabase instance"""
    return EncryptedDatabase(str(temp_db_path), test_passphrase)


@pytest.fixture
def backup_service():
    """Create a BackupCodesService instance"""
    return BackupCodesService()


# ========== Key Derivation Tests ==========

class TestKeyDerivation:
    """Tests for key derivation from passphrase"""

    def test_derive_key_returns_32_bytes(self, encrypted_db):
        """Test that key derivation returns 32-byte key"""
        assert len(encrypted_db.encryption_key) == 32

    def test_derive_key_deterministic(self, temp_db_path, test_passphrase):
        """Test that same passphrase produces same key"""
        db1 = EncryptedDatabase(str(temp_db_path), test_passphrase)
        db2 = EncryptedDatabase(str(temp_db_path), test_passphrase)

        assert db1.encryption_key == db2.encryption_key

    def test_derive_key_different_passphrase(self, temp_db_path):
        """Test that different passphrases produce different keys"""
        db1 = EncryptedDatabase(str(temp_db_path), "passphrase1")
        db2 = EncryptedDatabase(str(temp_db_path), "passphrase2")

        assert db1.encryption_key != db2.encryption_key

    def test_derive_key_different_db_path(self, temp_db_dir, test_passphrase):
        """Test that different db paths produce different keys"""
        db1 = EncryptedDatabase(str(temp_db_dir / "db1.db"), test_passphrase)
        db2 = EncryptedDatabase(str(temp_db_dir / "db2.db"), test_passphrase)

        # Same passphrase but different salt (db path)
        assert db1.encryption_key != db2.encryption_key

    def test_derive_key_unicode_passphrase(self, temp_db_path):
        """Test key derivation with unicode passphrase"""
        db = EncryptedDatabase(str(temp_db_path), "密码🔐тест")

        assert len(db.encryption_key) == 32


# ========== Database Encryption Tests ==========

class TestDatabaseEncryption:
    """Tests for database encryption"""

    def test_encrypt_database_creates_file(self, encrypted_db, plaintext_db):
        """Test that encryption creates .db.encrypted file"""
        success = encrypted_db._encrypt_database(plaintext_db)

        assert success is True
        assert encrypted_db.encrypted_path.exists()

    def test_encrypt_database_file_different_from_plaintext(self, encrypted_db, plaintext_db):
        """Test that encrypted file differs from plaintext"""
        with open(plaintext_db, 'rb') as f:
            plaintext_data = f.read()

        encrypted_db._encrypt_database(plaintext_db)

        with open(encrypted_db.encrypted_path, 'rb') as f:
            encrypted_data = f.read()

        # Should not be the same (and encrypted should be slightly larger due to auth tag)
        assert encrypted_data != plaintext_data
        assert len(encrypted_data) > len(plaintext_data)

    def test_encrypt_database_contains_nonce(self, encrypted_db, plaintext_db):
        """Test that encrypted file starts with 12-byte nonce"""
        encrypted_db._encrypt_database(plaintext_db)

        with open(encrypted_db.encrypted_path, 'rb') as f:
            data = f.read()

        # File should be at least nonce (12) + some ciphertext + auth tag (16)
        assert len(data) >= 28

    def test_encrypt_database_returns_false_on_error(self, encrypted_db):
        """Test that encryption returns False on error"""
        non_existent = Path("/nonexistent/path/db.db")

        success = encrypted_db._encrypt_database(non_existent)

        assert success is False


# ========== Database Decryption Tests ==========

class TestDatabaseDecryption:
    """Tests for database decryption"""

    def test_decrypt_database_returns_path(self, encrypted_db, plaintext_db):
        """Test that decryption returns path to temp database"""
        # First encrypt
        encrypted_db._encrypt_database(plaintext_db)

        # Then decrypt
        decrypted_path = encrypted_db._decrypt_database()

        assert decrypted_path is not None
        assert decrypted_path.exists()

    def test_decrypt_database_restores_data(self, encrypted_db, plaintext_db):
        """Test that decryption restores original data"""
        with open(plaintext_db, 'rb') as f:
            original_data = f.read()

        # Encrypt then decrypt
        encrypted_db._encrypt_database(plaintext_db)
        decrypted_path = encrypted_db._decrypt_database()

        with open(decrypted_path, 'rb') as f:
            restored_data = f.read()

        assert restored_data == original_data

    def test_decrypt_database_fallback_to_plaintext(self, encrypted_db, plaintext_db):
        """Test decryption falls back to plaintext if no encrypted file"""
        # No encryption done, should use plaintext
        decrypted_path = encrypted_db._decrypt_database()

        assert decrypted_path == plaintext_db

    def test_decrypt_database_returns_none_if_no_file(self, encrypted_db):
        """Test decryption returns None if no database exists"""
        decrypted_path = encrypted_db._decrypt_database()

        assert decrypted_path is None

    def test_decrypt_database_wrong_key(self, temp_db_path, plaintext_db, test_passphrase):
        """Test decryption fails with wrong passphrase"""
        # Encrypt with one passphrase
        db1 = EncryptedDatabase(str(temp_db_path), test_passphrase)
        db1._encrypt_database(plaintext_db)

        # Try to decrypt with different passphrase
        db2 = EncryptedDatabase(str(temp_db_path), "wrong_passphrase")
        decrypted_path = db2._decrypt_database()

        # Should fail (return None due to authentication failure)
        assert decrypted_path is None

    def test_decrypt_database_temp_file_permissions(self, encrypted_db, plaintext_db):
        """Test that decrypted temp file has restrictive permissions"""
        encrypted_db._encrypt_database(plaintext_db)
        decrypted_path = encrypted_db._decrypt_database()

        # Check permissions (should be 0o600 - owner read/write only)
        mode = os.stat(decrypted_path).st_mode & 0o777
        assert mode == 0o600


# ========== Connect/Close Lifecycle Tests ==========

class TestConnectClose:
    """Tests for database connection lifecycle"""

    def test_connect_returns_connection(self, encrypted_db, plaintext_db):
        """Test that connect returns SQLite connection"""
        encrypted_db._encrypt_database(plaintext_db)

        conn = encrypted_db.connect()

        assert conn is not None
        assert isinstance(conn, sqlite3.Connection)

        encrypted_db.close(conn)

    def test_connect_allows_queries(self, encrypted_db, plaintext_db):
        """Test that connection allows SQL queries"""
        encrypted_db._encrypt_database(plaintext_db)

        conn = encrypted_db.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM test_table")
        count = cursor.fetchone()[0]

        assert count == 3

        encrypted_db.close(conn)

    def test_connect_row_factory_is_row(self, encrypted_db, plaintext_db):
        """Test that connection has Row factory"""
        encrypted_db._encrypt_database(plaintext_db)

        conn = encrypted_db.connect()

        assert conn.row_factory == sqlite3.Row

        encrypted_db.close(conn)

    def test_close_commits_changes(self, encrypted_db, plaintext_db):
        """Test that close commits pending changes"""
        encrypted_db._encrypt_database(plaintext_db)

        # Make changes
        conn = encrypted_db.connect()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO test_table (name, value) VALUES (?, ?)", ("new", 400))
        encrypted_db.close(conn)

        # Verify changes persisted
        conn2 = encrypted_db.connect()
        cursor2 = conn2.cursor()
        cursor2.execute("SELECT COUNT(*) FROM test_table")
        count = cursor2.fetchone()[0]

        assert count == 4

        encrypted_db.close(conn2)

    def test_close_re_encrypts(self, encrypted_db, plaintext_db):
        """Test that close re-encrypts the database"""
        encrypted_db._encrypt_database(plaintext_db)

        # Get encrypted file modification time
        mtime_before = encrypted_db.encrypted_path.stat().st_mtime

        # Connect, modify, close
        conn = encrypted_db.connect()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO test_table (name, value) VALUES (?, ?)", ("test", 999))

        import time
        time.sleep(0.1)  # Ensure different mtime

        encrypted_db.close(conn)

        # Encrypted file should be updated
        mtime_after = encrypted_db.encrypted_path.stat().st_mtime
        assert mtime_after > mtime_before

    def test_close_deletes_temp_file(self, encrypted_db, plaintext_db):
        """Test that close deletes temporary plaintext file"""
        encrypted_db._encrypt_database(plaintext_db)

        conn = encrypted_db.connect()
        temp_path = encrypted_db.temp_db_path

        assert temp_path.exists()

        encrypted_db.close(conn)

        assert not temp_path.exists()

    def test_connect_returns_none_if_decryption_fails(self, encrypted_db):
        """Test connect returns None if decryption fails"""
        conn = encrypted_db.connect()

        assert conn is None


# ========== Migration Tests ==========

class TestMigration:
    """Tests for plaintext to encrypted migration"""

    def test_migrate_encrypts_database(self, encrypted_db, plaintext_db):
        """Test that migration encrypts the database"""
        success = encrypted_db.migrate_from_plaintext()

        assert success is True
        assert encrypted_db.encrypted_path.exists()

    def test_migrate_removes_plaintext(self, encrypted_db, plaintext_db):
        """Test that migration removes plaintext database"""
        success = encrypted_db.migrate_from_plaintext()

        assert success is True
        assert not plaintext_db.exists()

    def test_migrate_creates_backup(self, encrypted_db, plaintext_db):
        """Test that migration creates backup"""
        success = encrypted_db.migrate_from_plaintext()

        backup_path = plaintext_db.with_suffix('.db.backup')

        assert success is True
        assert backup_path.exists()

    def test_migrate_fails_if_no_plaintext(self, encrypted_db):
        """Test migration fails if plaintext doesn't exist"""
        success = encrypted_db.migrate_from_plaintext()

        assert success is False

    def test_migrate_fails_if_encrypted_exists(self, encrypted_db, plaintext_db):
        """Test migration fails if encrypted already exists"""
        # First migration
        encrypted_db.migrate_from_plaintext()

        # Recreate plaintext
        conn = sqlite3.connect(str(plaintext_db))
        conn.execute("CREATE TABLE dummy (id INTEGER)")
        conn.close()

        # Second migration should fail
        success = encrypted_db.migrate_from_plaintext()

        assert success is False


# ========== BackupCodesService Tests ==========

class TestBackupCodesGeneration:
    """Tests for backup code generation"""

    def test_generate_returns_list(self, backup_service):
        """Test that generate returns a list"""
        codes = backup_service.generate_backup_codes()

        assert isinstance(codes, list)

    def test_generate_default_count(self, backup_service):
        """Test default code count is 10"""
        codes = backup_service.generate_backup_codes()

        assert len(codes) == 10

    def test_generate_custom_count(self, backup_service):
        """Test custom code count"""
        codes = backup_service.generate_backup_codes(count=5)

        assert len(codes) == 5

    def test_generate_format_xxxx_xxxx_xxxx_xxxx(self, backup_service):
        """Test codes are in XXXX-XXXX-XXXX-XXXX format"""
        codes = backup_service.generate_backup_codes()

        for code in codes:
            parts = code.split('-')
            assert len(parts) == 4
            for part in parts:
                assert len(part) == 4
                assert all(c in '0123456789ABCDEF' for c in part)

    def test_generate_codes_unique(self, backup_service):
        """Test that generated codes are unique"""
        codes = backup_service.generate_backup_codes(count=100)

        assert len(codes) == len(set(codes))

    def test_generate_uppercase(self, backup_service):
        """Test codes are uppercase"""
        codes = backup_service.generate_backup_codes()

        for code in codes:
            assert code == code.upper()


class TestBackupCodesHashing:
    """Tests for backup code hashing"""

    def test_hash_returns_string(self, backup_service):
        """Test that hash returns a string"""
        code = "AAAA-BBBB-CCCC-DDDD"
        hashed = backup_service.hash_backup_code(code)

        assert isinstance(hashed, str)

    def test_hash_is_sha256(self, backup_service):
        """Test that hash is 64-char SHA-256 hex"""
        code = "AAAA-BBBB-CCCC-DDDD"
        hashed = backup_service.hash_backup_code(code)

        assert len(hashed) == 64
        assert all(c in '0123456789abcdef' for c in hashed)

    def test_hash_deterministic(self, backup_service):
        """Test that same code produces same hash"""
        code = "AAAA-BBBB-CCCC-DDDD"

        hash1 = backup_service.hash_backup_code(code)
        hash2 = backup_service.hash_backup_code(code)

        assert hash1 == hash2

    def test_hash_different_codes_different_hash(self, backup_service):
        """Test different codes produce different hashes"""
        hash1 = backup_service.hash_backup_code("AAAA-BBBB-CCCC-DDDD")
        hash2 = backup_service.hash_backup_code("AAAA-BBBB-CCCC-DDDE")

        assert hash1 != hash2


class TestBackupCodesVerification:
    """Tests for backup code verification"""

    def test_verify_correct_code(self, backup_service):
        """Test verification of correct code"""
        code = "AAAA-BBBB-CCCC-DDDD"
        code_hash = backup_service.hash_backup_code(code)

        result = backup_service.verify_backup_code(code, code_hash)

        assert result is True

    def test_verify_incorrect_code(self, backup_service):
        """Test verification of incorrect code"""
        correct_code = "AAAA-BBBB-CCCC-DDDD"
        wrong_code = "AAAA-BBBB-CCCC-DDDE"
        code_hash = backup_service.hash_backup_code(correct_code)

        result = backup_service.verify_backup_code(wrong_code, code_hash)

        assert result is False

    def test_verify_case_sensitive(self, backup_service):
        """Test that verification is case sensitive"""
        code = "AAAA-BBBB-CCCC-DDDD"
        code_hash = backup_service.hash_backup_code(code)

        result = backup_service.verify_backup_code("aaaa-bbbb-cccc-dddd", code_hash)

        assert result is False

    def test_verify_uses_timing_safe_comparison(self, backup_service):
        """Test that verification uses constant-time comparison"""
        # This is more of a documentation test - actual timing attacks
        # require statistical analysis. We just verify the method exists
        # and uses secrets.compare_digest
        import inspect
        source = inspect.getsource(backup_service.verify_backup_code)

        assert "compare_digest" in source


class TestBackupCodesStorage:
    """Tests for backup code storage"""

    def test_store_creates_table(self, backup_service, temp_db_path):
        """Test that storage creates backup_codes table"""
        codes = ["AAAA-BBBB-CCCC-DDDD"]
        backup_service.store_backup_codes(codes, str(temp_db_path))

        conn = sqlite3.connect(str(temp_db_path))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='backup_codes'
        """)
        result = cursor.fetchone()
        conn.close()

        assert result is not None

    def test_store_saves_hashed_codes(self, backup_service, temp_db_path):
        """Test that codes are stored as hashes"""
        codes = ["AAAA-BBBB-CCCC-DDDD", "EEEE-FFFF-0000-1111"]
        backup_service.store_backup_codes(codes, str(temp_db_path))

        conn = sqlite3.connect(str(temp_db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT code_hash FROM backup_codes")
        rows = cursor.fetchall()
        conn.close()

        assert len(rows) == 2

        # Hashes should be stored, not plaintext
        stored_hashes = [r[0] for r in rows]
        for code in codes:
            assert code not in stored_hashes
            assert backup_service.hash_backup_code(code) in stored_hashes

    def test_store_codes_unused_by_default(self, backup_service, temp_db_path):
        """Test that stored codes are marked unused"""
        codes = ["AAAA-BBBB-CCCC-DDDD"]
        backup_service.store_backup_codes(codes, str(temp_db_path))

        conn = sqlite3.connect(str(temp_db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT used FROM backup_codes")
        row = cursor.fetchone()
        conn.close()

        assert row[0] == 0  # False

    def test_store_returns_true_on_success(self, backup_service, temp_db_path):
        """Test store returns True on success"""
        codes = ["AAAA-BBBB-CCCC-DDDD"]
        result = backup_service.store_backup_codes(codes, str(temp_db_path))

        assert result is True

    def test_store_returns_false_on_error(self, backup_service):
        """Test store returns False on error"""
        codes = ["AAAA-BBBB-CCCC-DDDD"]
        result = backup_service.store_backup_codes(codes, "/nonexistent/path.db")

        assert result is False

    def test_store_duplicate_code_fails(self, backup_service, temp_db_path):
        """Test that duplicate codes fail (UNIQUE constraint)"""
        codes = ["AAAA-BBBB-CCCC-DDDD"]

        # First store succeeds
        result1 = backup_service.store_backup_codes(codes, str(temp_db_path))

        # Second store with same codes fails
        result2 = backup_service.store_backup_codes(codes, str(temp_db_path))

        assert result1 is True
        assert result2 is False


# ========== Global Function Tests ==========

class TestGlobalFunction:
    """Tests for global get_encrypted_database function"""

    def test_get_encrypted_database_returns_instance(self, temp_db_dir):
        """Test that function returns an EncryptedDatabase"""
        # Patch the module that gets imported inside the function
        with patch.dict('sys.modules', {
            'config_paths': Mock(
                get_config_paths=Mock(return_value=Mock(data_dir=temp_db_dir))
            )
        }):
            from api.encrypted_db_service import _encrypted_databases
            _encrypted_databases.clear()

            db = get_encrypted_database("test.db", "passphrase")

            assert isinstance(db, EncryptedDatabase)

    def test_get_encrypted_database_caches_instance(self, temp_db_dir):
        """Test that same params return same instance"""
        with patch.dict('sys.modules', {
            'config_paths': Mock(
                get_config_paths=Mock(return_value=Mock(data_dir=temp_db_dir))
            )
        }):
            from api.encrypted_db_service import _encrypted_databases
            _encrypted_databases.clear()

            db1 = get_encrypted_database("test.db", "passphrase")
            db2 = get_encrypted_database("test.db", "passphrase")

            assert db1 is db2

    def test_get_encrypted_database_different_passphrase(self, temp_db_dir):
        """Test that different passphrase returns different instance"""
        with patch.dict('sys.modules', {
            'config_paths': Mock(
                get_config_paths=Mock(return_value=Mock(data_dir=temp_db_dir))
            )
        }):
            from api.encrypted_db_service import _encrypted_databases
            _encrypted_databases.clear()

            db1 = get_encrypted_database("test.db", "passphrase1")
            db2 = get_encrypted_database("test.db", "passphrase2")

            assert db1 is not db2


# ========== Edge Cases and Error Handling ==========

class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_empty_passphrase(self, temp_db_path):
        """Test handling of empty passphrase"""
        db = EncryptedDatabase(str(temp_db_path), "")

        # Should still derive a key
        assert len(db.encryption_key) == 32

    def test_very_long_passphrase(self, temp_db_path):
        """Test handling of very long passphrase"""
        long_pass = "x" * 10000
        db = EncryptedDatabase(str(temp_db_path), long_pass)

        assert len(db.encryption_key) == 32

    def test_special_characters_passphrase(self, temp_db_path):
        """Test handling of special characters in passphrase"""
        special_pass = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
        db = EncryptedDatabase(str(temp_db_path), special_pass)

        assert len(db.encryption_key) == 32

    def test_encrypt_empty_database(self, encrypted_db, temp_db_dir):
        """Test encrypting an empty database"""
        empty_db = temp_db_dir / "empty.db"

        # Create empty database
        conn = sqlite3.connect(str(empty_db))
        conn.close()

        success = encrypted_db._encrypt_database(empty_db)

        assert success is True

    def test_encrypt_large_database(self, encrypted_db, temp_db_dir):
        """Test encrypting a larger database"""
        large_db = temp_db_dir / "large.db"

        # Create database with more data
        conn = sqlite3.connect(str(large_db))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE big_table (
                id INTEGER PRIMARY KEY,
                data TEXT
            )
        """)

        # Insert 1000 rows
        for i in range(1000):
            cursor.execute(
                "INSERT INTO big_table (data) VALUES (?)",
                ("x" * 1000,)  # 1KB per row
            )

        conn.commit()
        conn.close()

        success = encrypted_db._encrypt_database(large_db)
        assert success is True

        # Verify decryption works
        encrypted_db._encrypt_database(large_db)
        decrypted = encrypted_db._decrypt_database()
        assert decrypted is not None

    def test_concurrent_access_same_db(self, temp_db_path, plaintext_db, test_passphrase):
        """Test concurrent access to same encrypted database"""
        db1 = EncryptedDatabase(str(temp_db_path), test_passphrase)
        db1._encrypt_database(plaintext_db)

        db2 = EncryptedDatabase(str(temp_db_path), test_passphrase)

        conn1 = db1.connect()
        conn2 = db2.connect()

        # Both should be able to read
        cursor1 = conn1.cursor()
        cursor2 = conn2.cursor()

        cursor1.execute("SELECT COUNT(*) FROM test_table")
        cursor2.execute("SELECT COUNT(*) FROM test_table")

        assert cursor1.fetchone()[0] == 3
        assert cursor2.fetchone()[0] == 3

        db1.close(conn1)
        db2.close(conn2)

    def test_path_with_spaces(self, tmp_path, test_passphrase):
        """Test database path with spaces"""
        space_dir = tmp_path / "path with spaces"
        space_dir.mkdir()
        db_path = space_dir / "test db.db"

        db = EncryptedDatabase(str(db_path), test_passphrase)

        # Create a simple database
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()

        success = db._encrypt_database(db_path)
        assert success is True

    def test_close_without_connect(self, encrypted_db):
        """Test close without prior connect"""
        # Create a mock connection
        conn = Mock()
        conn.commit = Mock()
        conn.close = Mock()

        # Should not crash
        encrypted_db.close(conn)


# ========== Secure Enclave Integration Tests ==========

class TestSecureEnclaveIntegration:
    """Tests for Secure Enclave integration (mocked)"""

    def test_accepts_secure_enclave_service(self, temp_db_path, test_passphrase):
        """Test that EncryptedDatabase accepts secure_enclave_service"""
        mock_enclave = Mock()

        db = EncryptedDatabase(
            str(temp_db_path),
            test_passphrase,
            secure_enclave_service=mock_enclave
        )

        assert db.secure_enclave is mock_enclave

    def test_backup_service_accepts_secure_enclave(self):
        """Test that BackupCodesService accepts secure_enclave_service"""
        mock_enclave = Mock()

        service = BackupCodesService(secure_enclave_service=mock_enclave)

        assert service.secure_enclave is mock_enclave
