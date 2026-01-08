"""
WebAuthn Challenge Management

In-memory challenge storage with TTL for WebAuthn authentication.

NOTE: For distributed deployments, replace with Redis-backed storage
(see SECURITY_ROADMAP.md).
"""

import secrets
import time
from typing import Dict, Any, Optional

# In-memory challenge storage with TTL (5 minutes)
# Format: {(user_id, vault_id): {'challenge': bytes, 'created_at': timestamp}}
webauthn_challenges: Dict[tuple, Dict[str, Any]] = {}
CHALLENGE_TTL_SECONDS = 300  # 5 minutes


def generate_challenge(user_id: str, vault_id: str) -> bytes:
    """Generate and store a WebAuthn challenge for biometric unlock."""
    challenge = secrets.token_bytes(32)
    webauthn_challenges[(user_id, vault_id)] = {
        'challenge': challenge,
        'created_at': time.time()
    }
    return challenge


def get_challenge(user_id: str, vault_id: str) -> Optional[bytes]:
    """Get stored challenge if still valid (within TTL)."""
    key = (user_id, vault_id)
    if key not in webauthn_challenges:
        return None

    entry = webauthn_challenges[key]
    if time.time() - entry['created_at'] > CHALLENGE_TTL_SECONDS:
        # Challenge expired, remove it
        del webauthn_challenges[key]
        return None

    return entry['challenge']


def consume_challenge(user_id: str, vault_id: str) -> Optional[bytes]:
    """Get and remove challenge (one-time use)."""
    challenge = get_challenge(user_id, vault_id)
    if challenge:
        del webauthn_challenges[(user_id, vault_id)]
    return challenge


def cleanup_expired_challenges() -> None:
    """Remove expired challenges (call periodically)."""
    now = time.time()
    expired = [
        key for key, entry in webauthn_challenges.items()
        if now - entry['created_at'] > CHALLENGE_TTL_SECONDS
    ]
    for key in expired:
        del webauthn_challenges[key]
