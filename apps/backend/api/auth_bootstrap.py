"""
Auth Bootstrap - Founder User Creation

Handles automated creation of the Founder user in development mode.
This replaces the previous hardcoded env-based Founder backdoor with
a proper DB-backed user account.

AUTH-P2: Normalize Founder into DB
"""

import os
import sqlite3
import secrets
import hashlib
import logging
from datetime import datetime, UTC
from typing import Optional

logger = logging.getLogger(__name__)


def _hash_password_pbkdf2(password: str, salt: Optional[bytes] = None) -> tuple[str, str]:
    """
    Hash password using PBKDF2-HMAC-SHA256 (matches auth_middleware.py implementation)

    Args:
        password: Plain text password
        salt: Optional salt bytes (generated if None)

    Returns:
        Tuple of (combined_hash_string, salt_hex)
    """
    if salt is None:
        salt = secrets.token_bytes(32)

    # Use PBKDF2 with 600,000 iterations (OWASP recommendation 2023)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 600_000)

    # Store salt + hash together (format: "salt_hex:hash_hex")
    combined = salt.hex() + ':' + pwd_hash.hex()
    return combined, salt.hex()


def ensure_dev_founder_user(conn: sqlite3.Connection) -> None:
    """
    Ensure Founder user exists in development mode.

    In development (ELOHIM_ENV=development):
    - Creates Founder user if not present
    - Uses env-configurable credentials:
      - ELOHIM_FOUNDER_USERNAME (default: elohim_founder)
      - ELOHIM_FOUNDER_PASSWORD (default: ElohimOS_2024_Founder)
    - Assigns 'founder_rights' role
    - Idempotent: safe to call multiple times

    In production:
    - Does nothing (Founder must be created explicitly via setup wizard)

    Args:
        conn: SQLite database connection

    Raises:
        ValueError: If in production and trying to auto-create Founder
    """
    # Only run in development mode
    env = os.getenv("ELOHIM_ENV")
    if env != "development":
        logger.debug(f"Skipping Founder bootstrap in {env} mode (dev-only feature)")
        return

    # Get Founder credentials from env
    founder_username = os.getenv("ELOHIM_FOUNDER_USERNAME", "elohim_founder")
    founder_password = os.getenv("ELOHIM_FOUNDER_PASSWORD", "ElohimOS_2024_Founder")

    cursor = conn.cursor()

    # Check if Founder user already exists
    cursor.execute("SELECT user_id, role FROM users WHERE username = ?", (founder_username,))
    existing_user = cursor.fetchone()

    if existing_user:
        user_id, current_role = existing_user

        # Ensure Founder has the correct role
        if current_role != "founder_rights":
            logger.info(f"Updating Founder user role from '{current_role}' to 'founder_rights'")
            cursor.execute("""
                UPDATE users
                SET role = 'founder_rights'
                WHERE user_id = ?
            """, (user_id,))
            conn.commit()
            logger.info(f"✅ Founder user '{founder_username}' role updated to 'founder_rights'")
        else:
            logger.debug(f"✅ Founder user '{founder_username}' already exists with correct role")

        return

    # Create Founder user
    logger.info(f"Creating Founder user '{founder_username}' in development mode...")

    user_id = f"founder_{secrets.token_urlsafe(8)}"
    password_hash, _ = _hash_password_pbkdf2(founder_password)
    created_at = datetime.now(UTC).isoformat()
    device_id = "founder_device"

    try:
        cursor.execute("""
            INSERT INTO users (user_id, username, password_hash, device_id, created_at, role, is_active)
            VALUES (?, ?, ?, ?, ?, 'founder_rights', 1)
        """, (user_id, founder_username, password_hash, device_id, created_at))

        conn.commit()

        logger.info("=" * 80)
        logger.info("✅ Founder user created successfully")
        logger.info(f"   Username: {founder_username}")
        logger.info(f"   User ID: {user_id}")
        logger.info(f"   Role: founder_rights")
        logger.info("=" * 80)

    except sqlite3.IntegrityError as e:
        # Race condition: another process created the user
        logger.warning(f"Founder user creation race condition (harmless): {e}")
        conn.rollback()

    except Exception as e:
        logger.error(f"Failed to create Founder user: {e}", exc_info=True)
        conn.rollback()
        raise


def create_founder_user_explicit(
    conn: sqlite3.Connection,
    username: str,
    password: str,
    device_id: str = "founder_device"
) -> str:
    """
    Explicitly create a Founder user (for production setup wizards).

    Unlike ensure_dev_founder_user, this:
    - Works in any environment (including production)
    - Requires explicit username/password (no defaults)
    - Raises error if user already exists
    - Returns the created user_id

    Args:
        conn: SQLite database connection
        username: Founder username
        password: Founder password (plain text, will be hashed)
        device_id: Device identifier (default: "founder_device")

    Returns:
        Created user_id

    Raises:
        ValueError: If user already exists or creation fails
    """
    cursor = conn.cursor()

    # Check if username already exists
    cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        raise ValueError(f"User '{username}' already exists")

    # Create Founder user
    user_id = f"founder_{secrets.token_urlsafe(8)}"
    password_hash, _ = _hash_password_pbkdf2(password)
    created_at = datetime.now(UTC).isoformat()

    try:
        cursor.execute("""
            INSERT INTO users (user_id, username, password_hash, device_id, created_at, role, is_active)
            VALUES (?, ?, ?, ?, ?, 'founder_rights', 1)
        """, (user_id, username, password_hash, device_id, created_at))

        conn.commit()

        logger.info(f"✅ Founder user '{username}' created explicitly (user_id: {user_id})")

        return user_id

    except Exception as e:
        logger.error(f"Failed to create Founder user explicitly: {e}", exc_info=True)
        conn.rollback()
        raise ValueError(f"Failed to create Founder user: {e}")
