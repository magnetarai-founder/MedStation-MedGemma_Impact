#!/usr/bin/env python3
"""
Team Cryptography Utilities for Phase 3

Provides team key derivation and P2P payload signing for team sync.

Security model:
- Team keys are derived from team_id + device secret (ephemeral)
- HMAC signing ensures team data integrity and authenticity
- Cross-team data is rejected via signature validation

"Two are better than one... for if they fall, one will lift up his companion"
- Ecclesiastes 4:9-10
"""

import os
import hmac
import hashlib
import json
import logging
from datetime import datetime, UTC
from typing import Optional, Dict, Any

from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


def get_device_secret() -> bytes:
    """
    Get device secret for key derivation

    In production, this should be stored in:
    - iOS/macOS: Secure Enclave via Keychain
    - Linux: Secret Service API or hardware token
    - Fallback: Environment variable

    For MVP, uses environment variable with fallback to runtime generation
    (which means keys won't persist across restarts - acceptable for Phase 3 MVP)

    Returns:
        32-byte device secret
    """
    secret = os.getenv("ELOHIMOS_DEVICE_SECRET")

    if not secret:
        logger.warning(
            "ELOHIMOS_DEVICE_SECRET not set - generating ephemeral device secret. "
            "Team keys will not persist across restarts."
        )
        # Generate ephemeral secret (not persisted)
        return os.urandom(32)

    # If secret is provided as hex string, decode it
    if isinstance(secret, str):
        try:
            return bytes.fromhex(secret)
        except ValueError:
            # If not hex, treat as UTF-8 string
            return secret.encode("utf-8")

    return secret


def derive_team_key(team_id: str) -> bytes:
    """
    Derive team key from team_id and device secret (Phase 3)

    Uses PBKDF2-HMAC-SHA256 with:
    - Salt: team_id (unique per team)
    - Secret: Device secret
    - Iterations: 100,000 (OWASP recommendation)
    - Output: 32 bytes

    Security properties:
    - Different teams get different keys (salt = team_id)
    - Same device gets consistent keys (secret = device_secret)
    - Computationally expensive to brute force (100k iterations)

    Phase 3.5 improvement:
    - Store encrypted team keys in app_db with rotation support
    - Use Secure Enclave for key protection on supported platforms

    Args:
        team_id: Team identifier

    Returns:
        32-byte derived team key
    """
    device_secret = get_device_secret()

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=team_id.encode("utf-8"),
        iterations=100000,
        backend=default_backend(),
    )

    team_key = kdf.derive(device_secret)

    logger.debug(f"Derived team key for team {team_id} (key_fingerprint: {hashlib.sha256(team_key).hexdigest()[:16]})")

    return team_key


def sign_payload(payload: Dict[str, Any], team_id: Optional[str]) -> str:
    """
    Sign P2P payload with team key for integrity and authenticity (Phase 3)

    If team_id is None (personal/solo mode), returns empty string.
    If team_id is provided, signs payload with HMAC-SHA256.

    The signature ensures:
    - Data integrity: payload hasn't been tampered with
    - Authenticity: payload came from team member with team key
    - Replay protection: should include timestamp in payload

    Usage:
        payload = {
            "action": "doc.create",
            "doc_id": "doc_123",
            "timestamp": datetime.now(UTC).isoformat(),
            "team_id": "team_abc"
        }
        signature = sign_payload(payload, "team_abc")

        # Include signature in sync message
        sync_message = {"payload": payload, "signature": signature}

    Args:
        payload: Dictionary to sign (will be JSON-serialized with sorted keys)
        team_id: Optional team ID (None for personal mode)

    Returns:
        Hex-encoded HMAC signature (empty string if team_id is None)
    """
    if not team_id:
        return ""

    team_key = derive_team_key(team_id)

    # Serialize payload with sorted keys for deterministic signing
    message = json.dumps(payload, sort_keys=True).encode("utf-8")

    # HMAC-SHA256 signature
    signature = hmac.new(team_key, message, hashlib.sha256).hexdigest()

    logger.debug(f"Signed payload for team {team_id} (sig: {signature[:16]}...)")

    return signature


def verify_payload(payload: Dict[str, Any], signature: str, team_id: str) -> bool:
    """
    Verify P2P payload signature (Phase 3)

    Validates that:
    - Signature matches payload
    - Payload came from team member with team key

    Args:
        payload: Dictionary to verify
        signature: Hex-encoded HMAC signature
        team_id: Team ID for key derivation

    Returns:
        True if signature is valid, False otherwise
    """
    if not signature or not team_id:
        return False

    try:
        expected_signature = sign_payload(payload, team_id)
        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        logger.error(f"Failed to verify payload signature: {e}")
        return False


def rotate_team_key(team_id: str, new_device_secret: bytes) -> bytes:
    """
    Rotate team key with new device secret (Phase 3.5)

    This is a placeholder for Phase 3.5 key rotation support.
    In Phase 3 MVP, keys are ephemeral and don't need rotation.

    Phase 3.5 implementation:
    - Store encrypted team keys in app_db
    - Re-encrypt with new device secret
    - Update all team members' local keys
    - Maintain key version for backward compatibility

    Args:
        team_id: Team identifier
        new_device_secret: New device secret for re-derivation

    Returns:
        New derived team key

    Raises:
        NotImplementedError: Phase 3.5 feature
    """
    raise NotImplementedError(
        "Team key rotation is a Phase 3.5 feature. "
        "Phase 3 MVP uses ephemeral keys derived from ELOHIMOS_DEVICE_SECRET."
    )
