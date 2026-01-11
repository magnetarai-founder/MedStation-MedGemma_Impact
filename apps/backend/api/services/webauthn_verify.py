"""
WebAuthn verification helpers (registration and assertion).

Provides full WebAuthn verification using the webauthn library.
Supports platform authenticators (Touch ID, Face ID, Windows Hello).

Module structure (P2 decomposition):
- webauthn_types.py: VerifiedRegistration, VerifiedAssertion dataclasses
- webauthn_verify.py: Verification functions (this file)
"""

from __future__ import annotations

import base64
import logging
from typing import Any, Dict

# Import from extracted module (P2 decomposition)
from api.services.webauthn_types import VerifiedRegistration, VerifiedAssertion

logger = logging.getLogger(__name__)

# Graceful degradation for webauthn package
try:
    from webauthn import (
        verify_registration_response,
        verify_authentication_response,
        options_to_json,
    )
    from webauthn.helpers import (
        base64url_to_bytes,
        bytes_to_base64url,
        parse_registration_credential_json,
        parse_authentication_credential_json,
    )
    from webauthn.helpers.structs import (
        PublicKeyCredentialDescriptor,
        AuthenticatorSelectionCriteria,
        UserVerificationRequirement,
        AuthenticatorAttachment,
    )
    WEBAUTHN_AVAILABLE = True
except ImportError:
    WEBAUTHN_AVAILABLE = False
    logger.warning("webauthn package not available - WebAuthn features disabled. Install with: pip install webauthn")
    # Stub types for type hints
    verify_registration_response = None
    verify_authentication_response = None
    options_to_json = None
    base64url_to_bytes = None
    bytes_to_base64url = None
    parse_registration_credential_json = None
    parse_authentication_credential_json = None
    PublicKeyCredentialDescriptor = None
    AuthenticatorSelectionCriteria = None
    UserVerificationRequirement = None
    AuthenticatorAttachment = None


def verify_registration(
    create_response: Dict[str, Any],
    rp_id: str,
    origin: str,
    challenge: bytes
) -> VerifiedRegistration:
    """Verify WebAuthn registration (platform authenticator).

    Args:
        create_response: JSON collected from navigator.credentials.create()
        rp_id: relying party ID (e.g., "localhost")
        origin: origin (e.g., "http://localhost:3000")
        challenge: original challenge bytes sent to client

    Returns:
        VerifiedRegistration with credential_id, public key, and sign counter

    Raises:
        Exception: if verification fails (invalid signature, wrong RP ID, etc.)
    """
    try:
        # Parse the registration credential from client response
        credential = parse_registration_credential_json(create_response)

        # Verify the registration response
        verification = verify_registration_response(
            credential=credential,
            expected_challenge=challenge,
            expected_rp_id=rp_id,
            expected_origin=origin,
            require_user_verification=True,  # Platform authenticators should verify user
        )

        # Extract credential ID and public key
        credential_id = bytes_to_base64url(verification.credential_id)
        public_key_bytes = verification.credential_public_key

        # Convert public key to PEM format for storage
        # The public_key_bytes is in COSE format, we'll store it as base64 for simplicity
        public_key_pem = base64.b64encode(public_key_bytes).decode('utf-8')

        logger.info(
            "WebAuthn registration verified",
            extra={
                "credential_id": credential_id[:16] + "...",  # Truncate for logs
                "sign_count": verification.sign_count,
                "rp_id": rp_id
            }
        )

        return VerifiedRegistration(
            credential_id=credential_id,
            public_key_pem=public_key_pem,
            sign_count=verification.sign_count
        )

    except Exception as e:
        logger.error(f"WebAuthn registration verification failed: {e}", exc_info=True)
        raise Exception(f"WebAuthn registration verification failed: {str(e)}")


def verify_assertion(
    assert_response: Dict[str, Any],
    rp_id: str,
    origin: str,
    public_key_pem: str,
    challenge: bytes,
    credential_id: str,
    current_sign_count: int = 0
) -> VerifiedAssertion:
    """Verify WebAuthn assertion for Touch ID unlock.

    Args:
        assert_response: JSON from navigator.credentials.get()
        rp_id: relying party ID (e.g., "localhost")
        origin: origin (e.g., "http://localhost:3000")
        public_key_pem: previously registered public key (base64-encoded COSE)
        challenge: original challenge bytes sent to client
        credential_id: expected credential ID (base64url)
        current_sign_count: last known sign count (for replay attack detection)

    Returns:
        VerifiedAssertion with credential_id, user_handle, and new sign_count

    Raises:
        Exception: if verification fails (invalid signature, wrong RP ID, replay attack, etc.)
    """
    try:
        # Parse the authentication credential from client response
        credential = parse_authentication_credential_json(assert_response)

        # Decode the stored public key from base64
        public_key_bytes = base64.b64decode(public_key_pem)

        # Verify the authentication response
        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=challenge,
            expected_rp_id=rp_id,
            expected_origin=origin,
            credential_public_key=public_key_bytes,
            credential_current_sign_count=current_sign_count,
            require_user_verification=True,  # Platform authenticators should verify user
        )

        # Extract user handle (optional, may be None)
        user_handle = None
        if verification.user_handle:
            user_handle = bytes_to_base64url(verification.user_handle)

        logger.info(
            "WebAuthn assertion verified",
            extra={
                "credential_id": credential_id[:16] + "...",  # Truncate for logs
                "new_sign_count": verification.new_sign_count,
                "rp_id": rp_id
            }
        )

        return VerifiedAssertion(
            credential_id=credential_id,
            user_handle=user_handle,
            sign_count=verification.new_sign_count
        )

    except Exception as e:
        logger.error(f"WebAuthn assertion verification failed: {e}", exc_info=True)
        raise Exception(f"WebAuthn assertion verification failed: {str(e)}")

