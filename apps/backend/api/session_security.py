"""
Compatibility Shim for Session Security

The implementation now lives in the `api.security` package:
- api.security.session: SessionSecurityManager class

This shim maintains backward compatibility.
"""

from api.security.session import (
    SessionFingerprint,
    SessionAnomalyResult,
    SessionSecurityManager,
    get_session_security_manager,
)

__all__ = [
    "SessionFingerprint",
    "SessionAnomalyResult",
    "SessionSecurityManager",
    "get_session_security_manager",
]
