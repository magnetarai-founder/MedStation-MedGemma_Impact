"""
Secret Manager for JWT

Manages JWT secret key with persistence across restarts.
Stores secret in secure file with proper permissions.
"""

import os
import secrets
from pathlib import Path

# Store secret in data directory
DATA_DIR = Path(os.getenv("DATA_DIR", os.path.expanduser("~/.magnetarcode")))
SECRET_FILE = DATA_DIR / ".jwt_secret"


def get_or_create_secret() -> str:
    """
    Get existing JWT secret or create and persist a new one.

    Returns:
        str: The JWT secret key

    Security:
        - Data directory has 0o700 permissions (owner only)
        - Secret file has 0o600 permissions (owner read/write only)
        - Secret persists across application restarts
        - Prevents token invalidation on restart
    """
    # Create data directory if it doesn't exist
    # SECURITY: Set restrictive permissions on the directory
    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.chmod(0o700)  # Owner only - rwx------
    else:
        # Verify existing directory has safe permissions
        current_mode = DATA_DIR.stat().st_mode & 0o777
        if current_mode & 0o077:  # Group or other has any access
            # Fix permissions
            DATA_DIR.chmod(0o700)

    # Check if secret file exists
    if SECRET_FILE.exists():
        # Verify file permissions before reading
        file_mode = SECRET_FILE.stat().st_mode & 0o777
        if file_mode & 0o077:  # Group or other has any access
            # Fix permissions
            SECRET_FILE.chmod(0o600)

        secret = SECRET_FILE.read_text().strip()
        if secret:  # Verify it's not empty
            return secret

    # Generate new secret
    secret = secrets.token_urlsafe(32)

    # SECURITY: Write to file with secure permissions
    # Create file with restrictive permissions from the start
    old_umask = os.umask(0o077)  # Temporarily restrict permissions
    try:
        SECRET_FILE.write_text(secret)
    finally:
        os.umask(old_umask)  # Restore original umask

    # Ensure permissions are correct (belt and suspenders)
    SECRET_FILE.chmod(0o600)  # Owner read/write only

    return secret
