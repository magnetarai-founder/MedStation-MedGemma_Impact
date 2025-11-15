"""
WebAuthn verification helpers (registration and assertion).

Skeleton wiring to integrate a proper library such as `webauthn`/`py_webauthn`.
Fill in with concrete calls during Phase 2.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class VerifiedRegistration:
    credential_id: str
    public_key_pem: str
    sign_count: int


@dataclass
class VerifiedAssertion:
    credential_id: str
    user_handle: str | None
    sign_count: int


def verify_registration(create_response: Dict[str, Any], rp_id: str, origin: str) -> VerifiedRegistration:
    """Verify WebAuthn registration (platform authenticator).

    Args:
        create_response: JSON collected from navigator.credentials.create()
        rp_id: relying party ID (e.g., "localhost")
        origin: origin (e.g., "http://localhost")
    Returns:
        VerifiedRegistration with credential_id, public key, and sign counter
    """
    # TODO: implement using py_webauthn / webauthn
    # Placeholder raises to signal implementation is required.
    raise NotImplementedError("Implement WebAuthn registration verification with py_webauthn")


def verify_assertion(assert_response: Dict[str, Any], rp_id: str, origin: str, public_key_pem: str) -> VerifiedAssertion:
    """Verify WebAuthn assertion for Touch ID unlock.

    Args:
        assert_response: JSON from navigator.credentials.get()
        rp_id: relying party ID
        origin: origin
        public_key_pem: previously registered public key
    Returns:
        VerifiedAssertion details
    """
    # TODO: implement using py_webauthn / webauthn
    raise NotImplementedError("Implement WebAuthn assertion verification with py_webauthn")

