"""
Vault Auth Pydantic Models

Request/response models for vault authentication endpoints.
"""

from typing import Optional
from pydantic import BaseModel, Field


# ===== Request Models =====

class BiometricSetupRequest(BaseModel):
    """Setup biometric unlock for vault"""
    vault_id: str = Field(..., description="Vault UUID")
    passphrase: str = Field(..., min_length=8, description="Master passphrase (for KEK derivation)")
    webauthn_credential_id: str = Field(..., description="WebAuthn credential ID (base64)")
    webauthn_public_key: str = Field(..., description="WebAuthn public key (base64)")


class BiometricUnlockRequest(BaseModel):
    """Unlock vault with biometric"""
    vault_id: str = Field(..., description="Vault UUID")
    webauthn_assertion: str = Field(..., description="WebAuthn assertion response (base64)")
    signature: str = Field(..., description="WebAuthn signature (base64)")


class DualPasswordSetupRequest(BaseModel):
    """Setup dual-password mode (sensitive vs unsensitive)"""
    vault_id: str = Field(..., description="Vault UUID")
    password_sensitive: str = Field(..., min_length=8, description="Sensitive vault password")
    password_unsensitive: str = Field(..., min_length=8, description="Unsensitive vault password")


# ===== Response Models =====

class UnlockResponse(BaseModel):
    """Unlock response"""
    success: bool
    vault_type: Optional[str] = None  # Never disclosed to maintain plausible deniability
    session_id: str
    message: str


class ChallengeResponse(BaseModel):
    """WebAuthn challenge for biometric verification"""
    challenge: str = Field(..., description="Base64url-encoded challenge")
    timeout: int = Field(default=300000, description="Challenge timeout in milliseconds")
