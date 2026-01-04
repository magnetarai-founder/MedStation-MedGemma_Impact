"""
Security and utility functions for ElohimOS backend
"""

import os
import re
from typing import Dict, Any

# MED-02: Compile regex patterns once at module load (not per function call)
_FILENAME_DANGEROUS_CHARS = re.compile(r'[^\w\-_.]')
_SECRET_PATTERNS_COMPILED = [
    (re.compile(r'password\s*[=:]\s*\S+', re.IGNORECASE), 'password=***REDACTED***'),
    (re.compile(r'token\s*[=:]\s*\S+', re.IGNORECASE), 'token=***REDACTED***'),
    (re.compile(r'api[_-]?key\s*[=:]\s*\S+', re.IGNORECASE), 'api_key=***REDACTED***'),
    (re.compile(r'secret\s*[=:]\s*\S+', re.IGNORECASE), 'secret=***REDACTED***'),
    (re.compile(r'bearer\s+\S+', re.IGNORECASE), 'bearer ***REDACTED***'),
    (re.compile(r'sk-[a-zA-Z0-9]{20,}'), '***REDACTED_API_KEY***'),
    (re.compile(r'ghp_[a-zA-Z0-9]{36}'), '***REDACTED_GITHUB_TOKEN***'),
    (re.compile(r'xox[baprs]-[a-zA-Z0-9\-]+'), '***REDACTED_SLACK_TOKEN***'),
]


def sanitize_filename(filename: str) -> str:
    """
    Remove path traversal characters and dangerous names from filename

    Security: Prevents path traversal attacks (HIGH-01)
    - Removes directory components (../, ./, etc.)
    - Strips dangerous characters
    - Limits length to 255 characters
    - Prevents empty filenames

    Args:
        filename: User-provided filename (untrusted input)

    Returns:
        Safe filename suitable for filesystem operations

    Example:
        >>> sanitize_filename("../../etc/passwd")
        'etc_passwd'
        >>> sanitize_filename("normal-file.xlsx")
        'normal-file.xlsx'
    """
    # Get basename only (removes directory components like ../)
    safe_name = os.path.basename(filename)

    # Remove dangerous characters (keep only alphanumeric, dash, underscore, dot)
    # MED-02: Use pre-compiled regex
    safe_name = _FILENAME_DANGEROUS_CHARS.sub('_', safe_name)

    # Limit length to 255 characters (filesystem limit)
    safe_name = safe_name[:255]

    # Prevent empty filename
    if not safe_name or safe_name == '.':
        safe_name = "upload"

    # Prevent files starting with dot (hidden files)
    if safe_name.startswith('.'):
        safe_name = 'file' + safe_name

    return safe_name


def sanitize_for_log(data: Any, max_length: int = 500) -> Any:
    """
    Remove sensitive keys and truncate long strings before logging

    Security: Prevents credential leakage in logs (HIGH-03)
    - Redacts passwords, tokens, API keys, secrets
    - Works with dicts, lists, and nested structures
    - Truncates long strings to prevent log bloat
    - Masks potential secrets in string content
    - Preserves data structure for debugging

    Args:
        data: Data structure to sanitize (dict, list, string, or primitive)
        max_length: Maximum length for string values (default: 500)

    Returns:
        Sanitized copy with sensitive fields redacted

    Example:
        >>> sanitize_for_log({"username": "john", "password": "secret123"})
        {"username": "john", "password": "***REDACTED***"}
        >>> sanitize_for_log("my password is secret123")
        "my password is ***REDACTED***"
    """
    SENSITIVE_KEYS = {
        'password', 'passwd', 'pwd',
        'token', 'access_token', 'refresh_token', 'auth_token', 'jwt',
        'api_key', 'apikey',
        'secret', 'secret_key',
        'passphrase',
        'auth_key', 'authorization', 'bearer',
        'private_key', 'priv_key', 'ssh_key',
        'credit_card', 'card_number', 'cvv', 'cvc',
        'ssn', 'social_security',
        'decoy_password', 'vault_password',
        'encryption_key', 'master_key'
    }

    if isinstance(data, dict):
        return {
            k: '***REDACTED***' if k.lower() in SENSITIVE_KEYS else sanitize_for_log(v, max_length)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [sanitize_for_log(item, max_length) for item in data]
    elif isinstance(data, tuple):
        return tuple(sanitize_for_log(item, max_length) for item in data)
    elif isinstance(data, str):
        # Check for secret patterns in string content
        # MED-02: Use pre-compiled regex patterns
        result = data
        for pattern, replacement in _SECRET_PATTERNS_COMPILED:
            result = pattern.sub(replacement, result)

        # Truncate if too long
        if len(result) > max_length:
            result = result[:max_length] + '...(truncated)'

        return result
    else:
        return data


# ===== File Locking Utilities =====

import fcntl
import logging
from pathlib import Path
from contextlib import contextmanager

_lock_logger = logging.getLogger(__name__)


@contextmanager
def file_lock(lock_dir: Path, lock_name: str = ".lock"):
    """
    Advisory file lock for preventing TOCTOU race conditions.

    SECURITY: Prevents race conditions in chunked uploads where multiple
    concurrent requests could corrupt files or metadata.

    Usage:
        with file_lock(upload_dir):
            # Critical section - only one process at a time
            write_chunk(...)
            update_metadata(...)

    Args:
        lock_dir: Directory to place the lock file in
        lock_name: Name of the lock file (default: ".lock")

    Note:
        - Uses fcntl.LOCK_EX for exclusive locking
        - Lock is automatically released when context exits
        - Works on Unix systems (macOS, Linux)
        - On Windows, consider using msvcrt.locking or portalocker
    """
    lock_dir = Path(lock_dir)
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_file = lock_dir / lock_name

    # Create lock file if it doesn't exist
    lock_file.touch(exist_ok=True)

    with open(lock_file, 'w') as f:
        try:
            # Acquire exclusive lock (blocks until available)
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            _lock_logger.debug(f"Acquired lock: {lock_file}")
            yield
        finally:
            # Release lock
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            _lock_logger.debug(f"Released lock: {lock_file}")


@contextmanager
def file_lock_nonblocking(lock_dir: Path, lock_name: str = ".lock"):
    """
    Non-blocking file lock - raises exception if lock unavailable.

    Use when you want to fail fast rather than wait for the lock.

    Raises:
        BlockingIOError: If lock is already held by another process
    """
    lock_dir = Path(lock_dir)
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_file = lock_dir / lock_name

    lock_file.touch(exist_ok=True)

    with open(lock_file, 'w') as f:
        try:
            # Try to acquire lock without blocking
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            _lock_logger.debug(f"Acquired non-blocking lock: {lock_file}")
            yield
        except BlockingIOError:
            _lock_logger.warning(f"Lock unavailable (non-blocking): {lock_file}")
            raise
        finally:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass  # Best effort unlock
