"""
Sanitization Patterns - Static security patterns for input validation

Extracted from sanitization.py during P2 decomposition.
Contains:
- XSS prevention patterns (DANGEROUS_PATTERNS)
- SQL injection detection patterns (SQL_INJECTION_PATTERNS)
- Path traversal detection patterns (PATH_TRAVERSAL_PATTERNS)
- Endpoints exempt from sanitization (SKIP_SANITIZATION_PATHS)

Based on OWASP Input Validation and Output Encoding guidelines.
"""

from typing import List


# ============================================================================
# XSS Prevention Patterns
# ============================================================================

# Dangerous patterns that should never appear in user input
DANGEROUS_PATTERNS: List[str] = [
    r'<script[^>]*>.*?</script>',  # Script tags
    r'javascript:',                 # JavaScript protocol
    r'onerror\s*=',                # Event handlers
    r'onload\s*=',
    r'onclick\s*=',
    r'<iframe[^>]*>',              # iframes
    r'<embed[^>]*>',               # embeds
    r'<object[^>]*>',              # objects
]


# ============================================================================
# SQL Injection Detection Patterns
# ============================================================================

# SQL injection patterns (detection only - we use parameterized queries)
# NOTE: These patterns are for logging/alerting, not for blocking.
# Always use parameterized queries as the primary defense.
SQL_INJECTION_PATTERNS: List[str] = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
    r"(--|;|\/\*|\*\/)",  # SQL comments
    r"(\bOR\b.*=.*)",     # OR injection
    r"(\bAND\b.*=.*)",    # AND injection
    r"('|\")\s*\w+\s*=",  # Quote injection
]


# ============================================================================
# Path Traversal Detection Patterns
# ============================================================================

# Path traversal patterns
PATH_TRAVERSAL_PATTERNS: List[str] = [
    r'\.\.',              # Parent directory
    r'%2e%2e',            # URL encoded ..
    r'%252e%252e',        # Double URL encoded ..
    r'\x00',              # Null byte
    r'%00',               # URL encoded null byte
]


# ============================================================================
# Sanitization Skip Paths
# ============================================================================

# Endpoints that should skip sanitization (raw file uploads, etc.)
SKIP_SANITIZATION_PATHS: List[str] = [
    "/api/v1/vault/files/upload",       # File uploads (binary data)
    "/api/v1/vault/files/download",     # File downloads
    "/api/v1/database/import",          # CSV/JSON imports
    "/metrics",                         # Prometheus metrics
]


__all__ = [
    "DANGEROUS_PATTERNS",
    "SQL_INJECTION_PATTERNS",
    "PATH_TRAVERSAL_PATTERNS",
    "SKIP_SANITIZATION_PATHS",
]
