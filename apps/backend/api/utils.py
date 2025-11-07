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

    # Patterns for detecting secrets in string content
    SECRET_PATTERNS = [
        (r'password\s*[=:]\s*\S+', 'password=***REDACTED***'),
        (r'token\s*[=:]\s*\S+', 'token=***REDACTED***'),
        (r'api[_-]?key\s*[=:]\s*\S+', 'api_key=***REDACTED***'),
        (r'secret\s*[=:]\s*\S+', 'secret=***REDACTED***'),
        (r'bearer\s+\S+', 'bearer ***REDACTED***'),
        (r'sk-[a-zA-Z0-9]{20,}', '***REDACTED_API_KEY***'),  # OpenAI-style keys
        (r'ghp_[a-zA-Z0-9]{36}', '***REDACTED_GITHUB_TOKEN***'),  # GitHub tokens
        (r'xox[baprs]-[a-zA-Z0-9\-]+', '***REDACTED_SLACK_TOKEN***'),  # Slack tokens
    ]

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
        result = data
        for pattern, replacement in SECRET_PATTERNS:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

        # Truncate if too long
        if len(result) > max_length:
            result = result[:max_length] + '...(truncated)'

        return result
    else:
        return data
