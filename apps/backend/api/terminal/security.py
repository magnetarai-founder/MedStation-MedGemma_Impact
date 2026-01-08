"""
Terminal Security Utilities

Secret redaction for audit logging.
"""

import re
from typing import List, Pattern

# Regex patterns for secret detection (basic)
SECRET_PATTERNS: List[Pattern] = [
    re.compile(r'(?i)(password|pwd|passwd)\s*[=:]\s*["\']?([^\s"\']+)', re.IGNORECASE),
    re.compile(r'(?i)(token|secret|key|api[_-]?key)\s*[=:]\s*["\']?([^\s"\']+)', re.IGNORECASE),
    re.compile(r'(?i)(aws_access_key|aws_secret)', re.IGNORECASE),
    re.compile(r'[A-Za-z0-9+/]{40,}={0,2}', re.IGNORECASE),  # Base64-ish strings
]


def redact_secrets(text: str) -> str:
    """
    Redact potential secrets from audit logs

    Args:
        text: Text that may contain secrets

    Returns:
        Text with secrets replaced by [REDACTED]
    """
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub('[REDACTED]', redacted)
    return redacted
