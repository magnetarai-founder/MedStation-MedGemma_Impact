"""
Security and utility functions for ElohimOS backend
"""

import os
import re
from typing import Dict, Any


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
    safe_name = re.sub(r'[^\w\-_.]', '_', safe_name)

    # Limit length to 255 characters (filesystem limit)
    safe_name = safe_name[:255]

    # Prevent empty filename
    if not safe_name or safe_name == '.':
        safe_name = "upload"

    # Prevent files starting with dot (hidden files)
    if safe_name.startswith('.'):
        safe_name = 'file' + safe_name

    return safe_name


def sanitize_for_log(data: Any) -> Any:
    """
    Remove sensitive keys before logging

    Security: Prevents credential leakage in logs (HIGH-03)
    - Redacts passwords, tokens, API keys, secrets
    - Works with dicts, lists, and nested structures
    - Preserves data structure for debugging

    Args:
        data: Data structure to sanitize (dict, list, or primitive)

    Returns:
        Sanitized copy with sensitive fields redacted

    Example:
        >>> sanitize_for_log({"username": "john", "password": "secret123"})
        {"username": "john", "password": "***REDACTED***"}
    """
    SENSITIVE_KEYS = {
        'password', 'passwd', 'pwd',
        'token', 'access_token', 'refresh_token', 'auth_token',
        'api_key', 'apikey',
        'secret', 'secret_key',
        'passphrase',
        'auth_key', 'authorization',
        'private_key', 'priv_key',
        'credit_card', 'card_number', 'cvv',
        'ssn', 'social_security',
        'decoy_password', 'vault_password'
    }

    if isinstance(data, dict):
        return {
            k: '***REDACTED***' if k.lower() in SENSITIVE_KEYS else sanitize_for_log(v)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [sanitize_for_log(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(sanitize_for_log(item) for item in data)
    else:
        return data
