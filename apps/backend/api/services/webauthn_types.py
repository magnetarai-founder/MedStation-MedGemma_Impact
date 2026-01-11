"""
WebAuthn Types - Dataclasses for verification results

Extracted from webauthn_verify.py during P2 decomposition.
Contains:
- VerifiedRegistration (registration result)
- VerifiedAssertion (assertion result)
"""

from dataclasses import dataclass


@dataclass
class VerifiedRegistration:
    """Result of WebAuthn registration verification"""
    credential_id: str
    public_key_pem: str
    sign_count: int


@dataclass
class VerifiedAssertion:
    """Result of WebAuthn assertion verification"""
    credential_id: str
    user_handle: str | None
    sign_count: int


__all__ = [
    "VerifiedRegistration",
    "VerifiedAssertion",
]
