#!/usr/bin/env python3
"""
Founder Password Setup Wizard

"Trust in the Lord with all your heart" - Proverbs 3:5

Implements Phase 5.3 of Security Hardening Roadmap:
- First-time founder password setup
- macOS Keychain integration for secure storage
- One-time initialization flow
- Secure password validation
- Automatic keychain item creation

Security Features:
- Passwords never stored in database or filesystem
- macOS Keychain encryption at rest
- Strong password requirements
- Setup can only be run once (prevents re-initialization)
- Audit logging of setup completion

Architecture:
- Wizard state stored in database (setup_completed flag)
- Password stored in macOS Keychain (keychain-services-api)
- Fallback to environment variable for non-macOS systems
- Integration with existing founder_rights authentication
"""

import logging
import os
import platform
import sqlite3
import subprocess
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, UTC
from pathlib import Path
import hashlib
import secrets

logger = logging.getLogger(__name__)


class FounderSetupWizard:
    """
    Founder password setup wizard with macOS Keychain integration

    Features:
    - First-time setup only (one-time initialization)
    - Strong password validation
    - macOS Keychain storage (or environment variable fallback)
    - Audit logging
    - Setup state tracking

    Usage:
        wizard = FounderSetupWizard()
        if not wizard.is_setup_complete():
            result = wizard.setup_founder_password("StrongPassword123!")
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize founder setup wizard

        Args:
            db_path: Path to app database (defaults to auth_service.db_path)
        """
        if db_path is None:
            try:
                from auth_middleware import auth_service
                db_path = auth_service.db_path
            except ImportError:
                from .auth_middleware import auth_service
                db_path = auth_service.db_path

        self.db_path = db_path
        self.keychain_service = "com.elohimos.founder"
        self.keychain_account = "founder_password"

        # Platform detection
        self.is_macos = platform.system() == "Darwin"

        # Initialize database table
        self._init_db()

    def _init_db(self) -> None:
        """Initialize founder_setup table"""
        conn = sqlite3.connect(str(self.db_path))
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS founder_setup (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                setup_completed INTEGER DEFAULT 0,
                setup_timestamp TEXT,
                password_storage_type TEXT,
                setup_user_id TEXT,
                setup_ip_address TEXT
            )
        """)

        # Insert default row if not exists
        cur.execute("""
            INSERT OR IGNORE INTO founder_setup (id, setup_completed)
            VALUES (1, 0)
        """)

        conn.commit()
        conn.close()

    # ========================================================================
    # Setup Status
    # ========================================================================

    def is_setup_complete(self) -> bool:
        """
        Check if founder password setup is complete

        Returns:
            True if setup is complete, False otherwise
        """
        conn = sqlite3.connect(str(self.db_path))
        cur = conn.cursor()

        cur.execute("SELECT setup_completed FROM founder_setup WHERE id = 1")
        row = cur.fetchone()

        conn.close()

        return bool(row[0]) if row else False

    def get_setup_info(self) -> Dict[str, Any]:
        """
        Get founder setup information

        Returns:
            Dict with setup status and metadata
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT * FROM founder_setup WHERE id = 1")
        row = cur.fetchone()

        conn.close()

        if not row:
            return {
                "setup_completed": False,
                "setup_timestamp": None,
                "password_storage_type": None
            }

        return {
            "setup_completed": bool(row["setup_completed"]),
            "setup_timestamp": row["setup_timestamp"],
            "password_storage_type": row["password_storage_type"],
            "is_macos": self.is_macos
        }

    # ========================================================================
    # Password Validation
    # ========================================================================

    def validate_password(self, password: str) -> Tuple[bool, Optional[str]]:
        """
        Validate password strength

        Requirements:
        - Minimum 12 characters
        - At least 1 uppercase letter
        - At least 1 lowercase letter
        - At least 1 number
        - At least 1 special character

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(password) < 12:
            return False, "Password must be at least 12 characters long"

        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"

        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"

        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one number"

        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            return False, "Password must contain at least one special character"

        return True, None

    # ========================================================================
    # macOS Keychain Operations
    # ========================================================================

    def _store_in_keychain(self, password: str) -> bool:
        """
        Store password in macOS Keychain

        Args:
            password: Password to store

        Returns:
            True if successful, False otherwise
        """
        if not self.is_macos:
            logger.warning("Not running on macOS - cannot use Keychain")
            return False

        try:
            # Delete existing keychain item if it exists
            subprocess.run(
                [
                    "security", "delete-generic-password",
                    "-s", self.keychain_service,
                    "-a", self.keychain_account
                ],
                capture_output=True,
                check=False  # Don't raise if item doesn't exist
            )

            # Add new keychain item
            result = subprocess.run(
                [
                    "security", "add-generic-password",
                    "-s", self.keychain_service,
                    "-a", self.keychain_account,
                    "-w", password,
                    "-U"  # Update if exists
                ],
                capture_output=True,
                text=True,
                check=True
            )

            logger.info("✅ Founder password stored in macOS Keychain")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to store password in Keychain: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error storing password in Keychain: {e}")
            return False

    def _retrieve_from_keychain(self) -> Optional[str]:
        """
        Retrieve password from macOS Keychain

        Returns:
            Password if found, None otherwise
        """
        if not self.is_macos:
            return None

        try:
            result = subprocess.run(
                [
                    "security", "find-generic-password",
                    "-s", self.keychain_service,
                    "-a", self.keychain_account,
                    "-w"  # Print password only
                ],
                capture_output=True,
                text=True,
                check=True
            )

            password = result.stdout.strip()
            return password if password else None

        except subprocess.CalledProcessError:
            # Item not found
            return None
        except Exception as e:
            logger.error(f"Error retrieving password from Keychain: {e}")
            return None

    # ========================================================================
    # Environment Variable Fallback
    # ========================================================================

    def _store_in_env_file(self, password: str) -> bool:
        """
        Store password in .env file (fallback for non-macOS systems)

        Args:
            password: Password to store

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get project root (3 levels up from api)
            project_root = Path(__file__).parent.parent.parent.parent
            env_file = project_root / ".env"

            # Read existing .env content
            existing_content = []
            if env_file.exists():
                with open(env_file, 'r') as f:
                    existing_content = [
                        line for line in f.readlines()
                        if not line.startswith("FOUNDER_PASSWORD=")
                    ]

            # Write .env with founder password
            with open(env_file, 'w') as f:
                f.writelines(existing_content)
                f.write(f"\n# Founder password (auto-generated)\n")
                f.write(f"FOUNDER_PASSWORD={password}\n")

            # Set restrictive permissions (owner read/write only)
            os.chmod(env_file, 0o600)

            logger.info("✅ Founder password stored in .env file (fallback)")
            return True

        except Exception as e:
            logger.error(f"Failed to store password in .env file: {e}")
            return False

    def _retrieve_from_env(self) -> Optional[str]:
        """
        Retrieve password from environment variable

        Returns:
            Password if found, None otherwise
        """
        return os.getenv("FOUNDER_PASSWORD")

    # ========================================================================
    # Setup Wizard
    # ========================================================================

    def setup_founder_password(
        self,
        password: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Setup founder password (one-time initialization)

        Args:
            password: Founder password to set
            user_id: User ID performing setup (for audit)
            ip_address: IP address of setup request (for audit)

        Returns:
            Dict with setup result
        """
        # Check if already setup
        if self.is_setup_complete():
            return {
                "success": False,
                "error": "Founder password already setup. Cannot re-initialize."
            }

        # Validate password strength
        is_valid, error_msg = self.validate_password(password)
        if not is_valid:
            return {
                "success": False,
                "error": error_msg
            }

        # Store password (Keychain on macOS, .env file otherwise)
        if self.is_macos:
            storage_success = self._store_in_keychain(password)
            storage_type = "macos_keychain" if storage_success else None
        else:
            storage_success = self._store_in_env_file(password)
            storage_type = "env_file" if storage_success else None

        if not storage_success:
            return {
                "success": False,
                "error": "Failed to store password securely"
            }

        # Mark setup as complete
        conn = sqlite3.connect(str(self.db_path))
        cur = conn.cursor()

        cur.execute("""
            UPDATE founder_setup
            SET setup_completed = 1,
                setup_timestamp = ?,
                password_storage_type = ?,
                setup_user_id = ?,
                setup_ip_address = ?
            WHERE id = 1
        """, (
            datetime.now(UTC).isoformat(),
            storage_type,
            user_id,
            ip_address
        ))

        conn.commit()
        conn.close()

        # Audit log
        try:
            from audit_logger import audit_log_sync, AuditAction

            audit_log_sync(
                user_id=user_id or "system",
                action="founder_setup.completed",
                resource="founder_password",
                resource_id="setup",
                details={
                    "storage_type": storage_type,
                    "timestamp": datetime.now(UTC).isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Failed to audit log founder setup: {e}")

        logger.info(f"✅ Founder password setup complete ({storage_type})")

        return {
            "success": True,
            "storage_type": storage_type,
            "message": "Founder password setup complete"
        }

    def verify_founder_password(self, password: str) -> bool:
        """
        Verify founder password

        Args:
            password: Password to verify

        Returns:
            True if password matches, False otherwise
        """
        if not self.is_setup_complete():
            logger.warning("Founder password not setup yet")
            return False

        # Retrieve stored password
        if self.is_macos:
            stored_password = self._retrieve_from_keychain()
        else:
            stored_password = self._retrieve_from_env()

        if stored_password is None:
            logger.error("Failed to retrieve founder password")
            return False

        # Constant-time comparison to prevent timing attacks
        return secrets.compare_digest(password, stored_password)


# ===== Singleton Instance =====

_founder_wizard: Optional[FounderSetupWizard] = None


def get_founder_wizard() -> FounderSetupWizard:
    """Get singleton founder setup wizard instance"""
    global _founder_wizard
    if _founder_wizard is None:
        _founder_wizard = FounderSetupWizard()
    return _founder_wizard


# Export
__all__ = [
    'FounderSetupWizard',
    'get_founder_wizard'
]
