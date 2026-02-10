"""
Comprehensive tests for api/auth_bootstrap.py

Tests cover:
- Password hashing with PBKDF2-HMAC-SHA256 (600k iterations)
- Dev mode founder user creation (ensure_dev_founder_user)
- Explicit founder user creation (create_founder_user_explicit)
- Environment-based behavior (development vs production)
- Idempotent user creation
- Role updates for existing users
- Race condition handling
- Error handling
"""

import pytest
import sqlite3
import secrets
import hashlib
import os
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.auth_bootstrap import (
    _hash_password_pbkdf2,
    ensure_dev_founder_user,
    create_founder_user_explicit,
)


# ========== Password Hashing Tests ==========

class TestPasswordHashing:
    """Tests for PBKDF2 password hashing"""

    def test_hash_returns_combined_format(self):
        """Test hash returns salt:hash format"""
        combined, salt_hex = _hash_password_pbkdf2("password123")

        assert ":" in combined
        parts = combined.split(":")
        assert len(parts) == 2

        # Salt should be 64 hex chars (32 bytes)
        assert len(parts[0]) == 64
        # Hash should be 64 hex chars (32 bytes SHA256)
        assert len(parts[1]) == 64

    def test_hash_with_provided_salt(self):
        """Test hashing with a specific salt"""
        salt = secrets.token_bytes(32)
        combined1, salt_hex1 = _hash_password_pbkdf2("password", salt)
        combined2, salt_hex2 = _hash_password_pbkdf2("password", salt)

        # Same salt should produce same hash
        assert combined1 == combined2
        assert salt_hex1 == salt_hex2
        assert salt_hex1 == salt.hex()

    def test_hash_is_deterministic(self):
        """Test same password + salt produces same hash"""
        salt = b"0" * 32
        combined1, _ = _hash_password_pbkdf2("mypassword", salt)
        combined2, _ = _hash_password_pbkdf2("mypassword", salt)

        assert combined1 == combined2

    def test_different_passwords_different_hashes(self):
        """Test different passwords produce different hashes"""
        salt = b"0" * 32
        combined1, _ = _hash_password_pbkdf2("password1", salt)
        combined2, _ = _hash_password_pbkdf2("password2", salt)

        assert combined1 != combined2

    def test_different_salts_different_hashes(self):
        """Test different salts produce different hashes"""
        combined1, _ = _hash_password_pbkdf2("password")
        combined2, _ = _hash_password_pbkdf2("password")

        # With random salts, hashes should differ
        assert combined1 != combined2

    def test_hash_unicode_password(self):
        """Test hashing unicode passwords"""
        combined, salt_hex = _hash_password_pbkdf2("пароль123")

        assert ":" in combined
        assert len(salt_hex) == 64

    def test_hash_empty_password(self):
        """Test hashing empty password (edge case)"""
        combined, salt_hex = _hash_password_pbkdf2("")

        assert ":" in combined
        assert len(salt_hex) == 64

    def test_hash_long_password(self):
        """Test hashing very long password"""
        long_password = "x" * 10000
        combined, salt_hex = _hash_password_pbkdf2(long_password)

        assert ":" in combined
        assert len(salt_hex) == 64


# ========== Dev Founder User Tests ==========

class TestDevFounderUser:
    """Tests for ensure_dev_founder_user"""

    @pytest.fixture
    def db_with_users_table(self):
        """Create database with users table"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    device_id TEXT,
                    created_at TEXT NOT NULL,
                    role TEXT DEFAULT 'member',
                    is_active INTEGER DEFAULT 1
                )
            """)
            conn.commit()
            yield conn
            conn.close()

    def test_skips_in_production(self, db_with_users_table):
        """Test founder creation is skipped in production"""
        with patch.dict(os.environ, {"MEDSTATION_ENV": "production"}, clear=False):
            ensure_dev_founder_user(db_with_users_table)

        cur = db_with_users_table.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        count = cur.fetchone()[0]

        assert count == 0

    def test_skips_when_env_not_set(self, db_with_users_table):
        """Test founder creation skipped when MEDSTATION_ENV not development"""
        # Ensure MEDSTATION_ENV is not set or not "development"
        env_copy = os.environ.copy()
        env_copy.pop("MEDSTATION_ENV", None)

        with patch.dict(os.environ, env_copy, clear=True):
            ensure_dev_founder_user(db_with_users_table)

        cur = db_with_users_table.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        count = cur.fetchone()[0]

        assert count == 0

    def test_creates_founder_in_dev_mode(self, db_with_users_table):
        """Test founder user is created in development mode"""
        with patch.dict(os.environ, {
            "MEDSTATION_ENV": "development",
            "MEDSTATION_FOUNDER_USERNAME": "test_founder",
            "MEDSTATION_FOUNDER_PASSWORD": "TestPassword123!"
        }, clear=False):
            ensure_dev_founder_user(db_with_users_table)

        cur = db_with_users_table.cursor()
        cur.execute("SELECT username, role, is_active FROM users WHERE username = ?",
                   ("test_founder",))
        row = cur.fetchone()

        assert row is not None
        assert row[0] == "test_founder"
        assert row[1] == "founder_rights"
        assert row[2] == 1

    def test_uses_default_username(self, db_with_users_table):
        """Test default username is used when not provided"""
        env_vars = {
            "MEDSTATION_ENV": "development",
            "MEDSTATION_FOUNDER_PASSWORD": "TestPassword123!"
        }
        # Remove MEDSTATION_FOUNDER_USERNAME if set
        with patch.dict(os.environ, env_vars, clear=False):
            # Ensure the username env var is not set
            os.environ.pop("MEDSTATION_FOUNDER_USERNAME", None)
            ensure_dev_founder_user(db_with_users_table)

        cur = db_with_users_table.cursor()
        cur.execute("SELECT username FROM users WHERE username = ?",
                   ("medstation_founder",))
        row = cur.fetchone()

        assert row is not None
        assert row[0] == "medstation_founder"

    def test_generates_password_when_not_provided(self, db_with_users_table):
        """Test random password is generated when not provided"""
        env_vars = {
            "MEDSTATION_ENV": "development",
            "MEDSTATION_FOUNDER_USERNAME": "gen_pass_founder"
        }
        with patch.dict(os.environ, env_vars, clear=False):
            os.environ.pop("MEDSTATION_FOUNDER_PASSWORD", None)
            ensure_dev_founder_user(db_with_users_table)

        cur = db_with_users_table.cursor()
        cur.execute("SELECT user_id, password_hash FROM users WHERE username = ?",
                   ("gen_pass_founder",))
        row = cur.fetchone()

        assert row is not None
        # Password hash should exist
        assert row[1] is not None
        assert ":" in row[1]

    def test_idempotent_does_not_duplicate(self, db_with_users_table):
        """Test calling multiple times doesn't create duplicates"""
        with patch.dict(os.environ, {
            "MEDSTATION_ENV": "development",
            "MEDSTATION_FOUNDER_USERNAME": "idempotent_founder",
            "MEDSTATION_FOUNDER_PASSWORD": "TestPassword123!"
        }, clear=False):
            # Call twice
            ensure_dev_founder_user(db_with_users_table)
            ensure_dev_founder_user(db_with_users_table)

        cur = db_with_users_table.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE username = ?",
                   ("idempotent_founder",))
        count = cur.fetchone()[0]

        assert count == 1

    def test_updates_role_if_wrong(self, db_with_users_table):
        """Test existing user's role is updated to founder_rights"""
        # Create user with wrong role
        cur = db_with_users_table.cursor()
        cur.execute("""
            INSERT INTO users (user_id, username, password_hash, device_id, created_at, role, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("existing-123", "role_update_founder", "hash", "device",
              datetime.utcnow().isoformat(), "member", 1))
        db_with_users_table.commit()

        with patch.dict(os.environ, {
            "MEDSTATION_ENV": "development",
            "MEDSTATION_FOUNDER_USERNAME": "role_update_founder",
            "MEDSTATION_FOUNDER_PASSWORD": "TestPassword123!"
        }, clear=False):
            ensure_dev_founder_user(db_with_users_table)

        cur.execute("SELECT role FROM users WHERE username = ?", ("role_update_founder",))
        role = cur.fetchone()[0]

        assert role == "founder_rights"

    def test_skips_update_if_role_correct(self, db_with_users_table):
        """Test no update when role is already founder_rights"""
        # Create user with correct role
        cur = db_with_users_table.cursor()
        cur.execute("""
            INSERT INTO users (user_id, username, password_hash, device_id, created_at, role, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("existing-456", "correct_role_founder", "hash", "device",
              datetime.utcnow().isoformat(), "founder_rights", 1))
        db_with_users_table.commit()

        with patch.dict(os.environ, {
            "MEDSTATION_ENV": "development",
            "MEDSTATION_FOUNDER_USERNAME": "correct_role_founder",
            "MEDSTATION_FOUNDER_PASSWORD": "TestPassword123!"
        }, clear=False):
            ensure_dev_founder_user(db_with_users_table)

        # Should still have only one user
        cur.execute("SELECT COUNT(*) FROM users WHERE username = ?",
                   ("correct_role_founder",))
        count = cur.fetchone()[0]
        assert count == 1


# ========== Explicit Founder Creation Tests ==========

class TestExplicitFounderCreation:
    """Tests for create_founder_user_explicit"""

    @pytest.fixture
    def db_with_users_table(self):
        """Create database with users table"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    device_id TEXT,
                    created_at TEXT NOT NULL,
                    role TEXT DEFAULT 'member',
                    is_active INTEGER DEFAULT 1
                )
            """)
            conn.commit()
            yield conn
            conn.close()

    def test_creates_founder_successfully(self, db_with_users_table):
        """Test explicit founder creation succeeds"""
        user_id = create_founder_user_explicit(
            db_with_users_table,
            username="explicit_founder",
            password="SecurePassword123!"
        )

        assert user_id.startswith("founder_")

        cur = db_with_users_table.cursor()
        cur.execute("SELECT username, role, device_id FROM users WHERE user_id = ?",
                   (user_id,))
        row = cur.fetchone()

        assert row[0] == "explicit_founder"
        assert row[1] == "founder_rights"
        assert row[2] == "founder_device"  # Default device_id

    def test_creates_with_custom_device_id(self, db_with_users_table):
        """Test explicit creation with custom device_id"""
        user_id = create_founder_user_explicit(
            db_with_users_table,
            username="custom_device_founder",
            password="SecurePassword123!",
            device_id="custom-device-001"
        )

        cur = db_with_users_table.cursor()
        cur.execute("SELECT device_id FROM users WHERE user_id = ?", (user_id,))
        device_id = cur.fetchone()[0]

        assert device_id == "custom-device-001"

    def test_fails_if_user_exists(self, db_with_users_table):
        """Test explicit creation fails if user already exists"""
        # Create existing user
        cur = db_with_users_table.cursor()
        cur.execute("""
            INSERT INTO users (user_id, username, password_hash, device_id, created_at, role, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("existing-789", "existing_founder", "hash", "device",
              datetime.utcnow().isoformat(), "member", 1))
        db_with_users_table.commit()

        with pytest.raises(ValueError, match="already exists"):
            create_founder_user_explicit(
                db_with_users_table,
                username="existing_founder",
                password="NewPassword123!"
            )

    def test_works_in_any_environment(self, db_with_users_table):
        """Test explicit creation works regardless of environment"""
        # Test in production
        with patch.dict(os.environ, {"MEDSTATION_ENV": "production"}, clear=False):
            user_id = create_founder_user_explicit(
                db_with_users_table,
                username="prod_founder",
                password="ProdPassword123!"
            )

        assert user_id.startswith("founder_")

    def test_password_is_hashed(self, db_with_users_table):
        """Test password is properly hashed, not stored plain"""
        user_id = create_founder_user_explicit(
            db_with_users_table,
            username="hashed_founder",
            password="PlainTextPassword!"
        )

        cur = db_with_users_table.cursor()
        cur.execute("SELECT password_hash FROM users WHERE user_id = ?", (user_id,))
        password_hash = cur.fetchone()[0]

        # Should not contain plain password
        assert "PlainTextPassword!" not in password_hash
        # Should be in salt:hash format
        assert ":" in password_hash

    def test_returns_user_id(self, db_with_users_table):
        """Test returns the created user_id"""
        user_id = create_founder_user_explicit(
            db_with_users_table,
            username="return_id_founder",
            password="Password123!"
        )

        assert isinstance(user_id, str)
        assert user_id.startswith("founder_")
        assert len(user_id) > len("founder_")

    def test_sets_is_active_to_true(self, db_with_users_table):
        """Test created user is active"""
        user_id = create_founder_user_explicit(
            db_with_users_table,
            username="active_founder",
            password="Password123!"
        )

        cur = db_with_users_table.cursor()
        cur.execute("SELECT is_active FROM users WHERE user_id = ?", (user_id,))
        is_active = cur.fetchone()[0]

        assert is_active == 1


# ========== Edge Cases Tests ==========

class TestEdgeCases:
    """Tests for edge cases"""

    @pytest.fixture
    def db_with_users_table(self):
        """Create database with users table"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    device_id TEXT,
                    created_at TEXT NOT NULL,
                    role TEXT DEFAULT 'member',
                    is_active INTEGER DEFAULT 1
                )
            """)
            conn.commit()
            yield conn
            conn.close()

    def test_unicode_username(self, db_with_users_table):
        """Test handling unicode username"""
        user_id = create_founder_user_explicit(
            db_with_users_table,
            username="基础用户",
            password="Password123!"
        )

        cur = db_with_users_table.cursor()
        cur.execute("SELECT username FROM users WHERE user_id = ?", (user_id,))
        username = cur.fetchone()[0]

        assert username == "基础用户"

    def test_unicode_password(self, db_with_users_table):
        """Test handling unicode password"""
        user_id = create_founder_user_explicit(
            db_with_users_table,
            username="unicode_pass_founder",
            password="密码123!"
        )

        assert user_id.startswith("founder_")

    def test_special_chars_in_username(self, db_with_users_table):
        """Test handling special characters in username"""
        user_id = create_founder_user_explicit(
            db_with_users_table,
            username="founder+test@example.com",
            password="Password123!"
        )

        cur = db_with_users_table.cursor()
        cur.execute("SELECT username FROM users WHERE user_id = ?", (user_id,))
        username = cur.fetchone()[0]

        assert username == "founder+test@example.com"

    def test_very_long_password(self, db_with_users_table):
        """Test handling very long password"""
        long_password = "x" * 10000
        user_id = create_founder_user_explicit(
            db_with_users_table,
            username="long_pass_founder",
            password=long_password
        )

        assert user_id.startswith("founder_")

    def test_empty_password_explicit(self, db_with_users_table):
        """Test explicit creation with empty password (allowed but not recommended)"""
        user_id = create_founder_user_explicit(
            db_with_users_table,
            username="empty_pass_founder",
            password=""
        )

        assert user_id.startswith("founder_")


# ========== Race Condition Tests ==========

class TestRaceConditions:
    """Tests for race condition handling"""

    @pytest.fixture
    def db_with_users_table(self):
        """Create database with users table"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    device_id TEXT,
                    created_at TEXT NOT NULL,
                    role TEXT DEFAULT 'member',
                    is_active INTEGER DEFAULT 1
                )
            """)
            conn.commit()
            yield conn
            conn.close()

    def test_dev_founder_handles_integrity_error(self, db_with_users_table):
        """Test dev founder creation handles race condition gracefully"""
        # Create user to simulate race condition
        cur = db_with_users_table.cursor()
        cur.execute("""
            INSERT INTO users (user_id, username, password_hash, device_id, created_at, role, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("race-123", "race_founder", "hash", "device",
              datetime.utcnow().isoformat(), "founder_rights", 1))
        db_with_users_table.commit()

        # Now call ensure_dev_founder_user - should not raise
        with patch.dict(os.environ, {
            "MEDSTATION_ENV": "development",
            "MEDSTATION_FOUNDER_USERNAME": "race_founder",
            "MEDSTATION_FOUNDER_PASSWORD": "TestPassword123!"
        }, clear=False):
            # Should not raise, should detect existing user
            ensure_dev_founder_user(db_with_users_table)

        # Should still have only one user
        cur.execute("SELECT COUNT(*) FROM users WHERE username = ?", ("race_founder",))
        count = cur.fetchone()[0]
        assert count == 1


# ========== Password Verification Tests ==========

class TestPasswordVerification:
    """Tests to verify password hashing matches auth_middleware format"""

    def test_hash_format_matches_auth_middleware(self):
        """Test hash format is compatible with auth_middleware verification"""
        password = "TestPassword123!"
        combined, salt_hex = _hash_password_pbkdf2(password)

        # Parse the combined hash
        parts = combined.split(":")
        stored_salt_hex = parts[0]
        stored_hash_hex = parts[1]

        # Verify we can reproduce the hash with the same salt
        salt = bytes.fromhex(stored_salt_hex)
        expected_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 600_000)

        assert stored_hash_hex == expected_hash.hex()

    def test_iteration_count_is_owasp_compliant(self):
        """Test that we use OWASP 2023 recommended iteration count"""
        # The function uses 600,000 iterations (OWASP 2023 recommendation)
        # We can't directly test this, but we verify the hash is different
        # from what lower iterations would produce
        password = "test"
        salt = b"0" * 32

        combined, _ = _hash_password_pbkdf2(password, salt)
        stored_hash_hex = combined.split(":")[1]

        # Hash with 600k iterations
        expected_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 600_000)

        # Hash with different iterations would be different
        wrong_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100_000)

        assert stored_hash_hex == expected_hash.hex()
        assert stored_hash_hex != wrong_hash.hex()


# ========== Error Handling Tests ==========

class TestErrorHandling:
    """Tests for error handling branches"""

    @pytest.fixture
    def db_with_users_table(self):
        """Create database with users table"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    device_id TEXT,
                    created_at TEXT NOT NULL,
                    role TEXT DEFAULT 'member',
                    is_active INTEGER DEFAULT 1
                )
            """)
            conn.commit()
            yield conn
            conn.close()

    def test_dev_founder_handles_general_exception(self):
        """Test dev founder creation handles general exceptions and re-raises"""
        # Create a mock connection that raises on INSERT
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # SELECT returns no existing user
        mock_cursor.fetchone.return_value = None
        # INSERT raises a general exception
        mock_cursor.execute.side_effect = [
            None,  # First call: SELECT (succeeds, returns None via fetchone)
            Exception("Simulated database error")  # Second call: INSERT (fails)
        ]

        with patch.dict(os.environ, {
            "MEDSTATION_ENV": "development",
            "MEDSTATION_FOUNDER_USERNAME": "error_founder",
            "MEDSTATION_FOUNDER_PASSWORD": "TestPassword123!"
        }, clear=False):
            with pytest.raises(Exception, match="Simulated database error"):
                ensure_dev_founder_user(mock_conn)

        # Verify rollback was called
        mock_conn.rollback.assert_called()

    def test_dev_founder_handles_integrity_error_on_insert(self):
        """Test dev founder creation handles IntegrityError during INSERT (race condition)"""
        # This tests the case where SELECT returns no user but INSERT fails due to race
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # SELECT returns no existing user
        mock_cursor.fetchone.return_value = None
        # INSERT raises IntegrityError (race condition)
        mock_cursor.execute.side_effect = [
            None,  # First call: SELECT
            sqlite3.IntegrityError("UNIQUE constraint failed: users.username")  # INSERT
        ]

        with patch.dict(os.environ, {
            "MEDSTATION_ENV": "development",
            "MEDSTATION_FOUNDER_USERNAME": "race_insert_founder",
            "MEDSTATION_FOUNDER_PASSWORD": "TestPassword123!"
        }, clear=False):
            # Should not raise - IntegrityError is caught as race condition
            ensure_dev_founder_user(mock_conn)

        # Verify rollback was called (race condition cleanup)
        mock_conn.rollback.assert_called()

    def test_explicit_founder_handles_database_error(self):
        """Test explicit founder creation wraps database errors as ValueError"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # SELECT returns no existing user (username doesn't exist)
        mock_cursor.fetchone.return_value = None
        # INSERT raises a general exception
        mock_cursor.execute.side_effect = [
            None,  # First call: SELECT
            Exception("Simulated database error")  # Second call: INSERT
        ]

        with pytest.raises(ValueError, match="Failed to create Founder user"):
            create_founder_user_explicit(
                mock_conn,
                username="db_error_founder",
                password="Password123!"
            )

        # Verify rollback was called
        mock_conn.rollback.assert_called()
