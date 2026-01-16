"""
Compatibility Shim for Team Cryptography

The implementation now lives in the `api.security` package:
- api.security.team_crypto: Team key derivation and HMAC signing

This shim maintains backward compatibility.

Note: Requires 'cryptography' package to be installed.
"""

try:
    from api.security.team_crypto import (
        get_device_secret,
        derive_team_key,
        sign_team_payload,
        verify_team_payload,
        rotate_team_key,
    )
except ImportError:
    get_device_secret = None
    derive_team_key = None
    sign_team_payload = None
    verify_team_payload = None
    rotate_team_key = None

__all__ = [
    "get_device_secret",
    "derive_team_key",
    "sign_team_payload",
    "verify_team_payload",
    "rotate_team_key",
]
