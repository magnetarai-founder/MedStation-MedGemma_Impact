"""
Mesh Relay Security - Signed Handshakes and Verification

SECURITY (Dec 2025):
- Handshakes require Ed25519 signatures proving peer identity
- Replay protection via timestamp validation (5 minute window)
- Prevents MITM impersonation attacks on mesh network
"""

import base64
import logging
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import List, Optional

# Cryptography imports for signed handshakes
try:
    import nacl.signing
    import nacl.exceptions
    NACL_AVAILABLE = True
except ImportError:
    NACL_AVAILABLE = False

logger = logging.getLogger(__name__)

# Security constants
HANDSHAKE_TIMESTAMP_TOLERANCE_SECONDS = 300  # 5 minutes
HANDSHAKE_NONCE_CACHE_MAX_SIZE = 5000  # Maximum nonces to track

# Nonce tracking for replay protection
_handshake_nonces: set = set()


def _check_handshake_nonce(nonce: str) -> bool:
    """Check if handshake nonce has been used before."""
    global _handshake_nonces

    if not nonce:
        return True  # Empty nonce allowed for backwards compatibility

    if nonce in _handshake_nonces:
        return False

    _handshake_nonces.add(nonce)

    # Limit cache size
    if len(_handshake_nonces) > HANDSHAKE_NONCE_CACHE_MAX_SIZE:
        nonces_list = list(_handshake_nonces)
        _handshake_nonces = set(nonces_list[HANDSHAKE_NONCE_CACHE_MAX_SIZE // 2:])

    return True


@dataclass
class SignedHandshake:
    """
    Cryptographically signed handshake for mesh peer authentication.

    Prevents MITM impersonation attacks by requiring proof of private key ownership.

    Replay Protection:
    - timestamp: Must be within 5 minutes (prevents old signature reuse)
    - nonce: Random value (prevents replay within timestamp window)
    """
    peer_id: str
    public_key: str  # Base64-encoded Ed25519 public key
    display_name: str
    capabilities: List[str]
    timestamp: str  # ISO 8601 for replay protection
    nonce: str = ""  # Random value for replay protection
    signature: str = ""  # Base64-encoded Ed25519 signature

    def get_canonical_payload(self) -> str:
        """
        Get canonical payload for signing/verification.
        Format: nonce|timestamp|public_key|peer_id|display_name|capabilities
        """
        caps_str = ",".join(sorted(self.capabilities))
        return f"{self.nonce}|{self.timestamp}|{self.public_key}|{self.peer_id}|{self.display_name}|{caps_str}"

    @classmethod
    def create(cls, signing_key: "nacl.signing.SigningKey", display_name: str,
               capabilities: List[str]) -> "SignedHandshake":
        """Create a signed handshake with the given signing key."""
        if not NACL_AVAILABLE:
            raise RuntimeError("nacl library required for signed handshakes")

        import secrets
        import hashlib

        # Get public key
        public_key_bytes = bytes(signing_key.verify_key)
        public_key_b64 = base64.b64encode(public_key_bytes).decode('utf-8')

        # Generate peer_id from public key (cryptographic binding)
        peer_id = hashlib.sha256(public_key_bytes).hexdigest()[:16]

        # Timestamp for replay protection
        timestamp = datetime.now(UTC).isoformat()

        # Generate random nonce for additional replay protection
        nonce = secrets.token_hex(16)

        # Create handshake (without signature yet)
        handshake = cls(
            peer_id=peer_id,
            public_key=public_key_b64,
            display_name=display_name,
            capabilities=capabilities,
            timestamp=timestamp,
            nonce=nonce,
            signature=""  # Will be set below
        )

        # Sign the canonical payload
        payload = handshake.get_canonical_payload()
        signature = signing_key.sign(payload.encode('utf-8'))
        handshake.signature = base64.b64encode(signature.signature).decode('utf-8')

        return handshake


def verify_handshake_signature(handshake_data: dict) -> Optional[SignedHandshake]:
    """
    Verify an incoming handshake signature.

    Returns SignedHandshake if valid, None if invalid or verification fails.
    Logs warnings for security-relevant failures.
    """
    if not NACL_AVAILABLE:
        logger.warning("nacl not available - cannot verify handshake signatures")
        return None

    try:
        import hashlib

        # Parse handshake
        handshake = SignedHandshake(
            peer_id=handshake_data.get('peer_id', ''),
            public_key=handshake_data.get('public_key', ''),
            display_name=handshake_data.get('display_name', ''),
            capabilities=handshake_data.get('capabilities', []),
            timestamp=handshake_data.get('timestamp', ''),
            nonce=handshake_data.get('nonce', ''),
            signature=handshake_data.get('signature', '')
        )

        # Validate required fields
        if not handshake.public_key or not handshake.signature or not handshake.timestamp:
            logger.warning(f"Handshake missing required fields from peer {handshake.peer_id[:8]}...")
            return None

        # Decode public key
        public_key_bytes = base64.b64decode(handshake.public_key)

        if len(public_key_bytes) != 32:
            logger.warning(f"Invalid public key length from peer {handshake.peer_id[:8]}...")
            return None

        # Verify peer_id matches public key (cryptographic binding)
        expected_peer_id = hashlib.sha256(public_key_bytes).hexdigest()[:16]
        if handshake.peer_id != expected_peer_id:
            logger.warning(f"Peer ID mismatch: claimed {handshake.peer_id[:8]}, expected {expected_peer_id[:8]}")
            return None

        # Validate timestamp (replay protection)
        try:
            handshake_time = datetime.fromisoformat(handshake.timestamp.replace('Z', '+00:00'))
        except ValueError:
            logger.warning(f"Invalid timestamp format from peer {handshake.peer_id[:8]}...")
            return None

        now = datetime.now(UTC)
        time_diff = abs((now - handshake_time).total_seconds())

        if time_diff > HANDSHAKE_TIMESTAMP_TOLERANCE_SECONDS:
            logger.warning(f"Handshake timestamp expired from peer {handshake.peer_id[:8]}... ({time_diff:.0f}s old)")
            return None

        # Check nonce for replay protection (prevents replay within timestamp window)
        if handshake.nonce and not _check_handshake_nonce(handshake.nonce):
            logger.warning(f"Replay attack: nonce already used from peer {handshake.peer_id[:8]}...")
            return None

        # Verify signature
        signature_bytes = base64.b64decode(handshake.signature)
        payload = handshake.get_canonical_payload()
        payload_bytes = payload.encode('utf-8')

        verify_key = nacl.signing.VerifyKey(public_key_bytes)
        verify_key.verify(payload_bytes, signature_bytes)

        logger.info(f"Handshake verified from peer {handshake.peer_id[:8]}... ({handshake.display_name})")
        return handshake

    except (nacl.exceptions.BadSignatureError, nacl.exceptions.ValueError) as e:
        logger.warning(f"Invalid handshake signature: {e}")
        return None
    except base64.binascii.Error:
        logger.warning("Invalid base64 encoding in handshake")
        return None
    except Exception as e:
        logger.error(f"Handshake verification error: {e}")
        return None


# Clear nonce cache for testing
def _clear_nonce_cache() -> None:
    """Clear the nonce cache - for testing only."""
    global _handshake_nonces
    _handshake_nonces = set()
