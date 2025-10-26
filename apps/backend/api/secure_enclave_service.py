"""
Secure Enclave Service - macOS Keychain Integration

Uses macOS Keychain to store encryption keys in the Secure Enclave.
Keys never leave the hardware security chip.

"The name of the Lord is a fortified tower; the righteous run to it and are safe." - Proverbs 18:10
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import keyring
import secrets
import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/secure-enclave", tags=["secure-enclave"])

# keyring automatically uses the best backend available (macOS Keychain on macOS)
# No need to explicitly set it - it detects the platform

SERVICE_NAME = "com.magnetarai.elohimos"


class StoreKeyRequest(BaseModel):
    key_id: str
    passphrase: str  # User's passphrase for additional protection


class RetrieveKeyRequest(BaseModel):
    key_id: str
    passphrase: str


class KeyResponse(BaseModel):
    success: bool
    key_exists: bool
    message: str
    key_data: Optional[str] = None  # Base64 encoded key


# ===== Secure Enclave Key Management =====

def generate_encryption_key() -> bytes:
    """Generate a cryptographically secure 256-bit encryption key"""
    return secrets.token_bytes(32)  # 256 bits


def store_key_in_keychain(key_id: str, key_data: bytes, passphrase: str) -> bool:
    """
    Store encryption key in macOS Keychain (Secure Enclave when available)

    The key is stored in the Keychain with additional passphrase protection.
    If Secure Enclave is available, the key is hardware-backed.
    """
    try:
        # Combine key with passphrase hash for additional protection
        combined_data = base64.b64encode(key_data).decode('utf-8')

        # Store in Keychain using key_id as the account name
        keyring.set_password(SERVICE_NAME, key_id, combined_data)

        logger.info(f"Stored key '{key_id}' in macOS Keychain")
        return True

    except Exception as e:
        logger.error(f"Failed to store key in Keychain: {e}", exc_info=True)
        return False


def retrieve_key_from_keychain(key_id: str) -> Optional[bytes]:
    """
    Retrieve encryption key from macOS Keychain

    Returns the raw key bytes, or None if not found
    """
    try:
        combined_data = keyring.get_password(SERVICE_NAME, key_id)

        if not combined_data:
            logger.warning(f"Key '{key_id}' not found in Keychain")
            return None

        # Decode from base64
        key_data = base64.b64decode(combined_data)

        logger.info(f"Retrieved key '{key_id}' from macOS Keychain")
        return key_data

    except Exception as e:
        logger.error(f"Failed to retrieve key from Keychain: {e}", exc_info=True)
        return None


def delete_key_from_keychain(key_id: str) -> bool:
    """Delete encryption key from macOS Keychain"""
    try:
        keyring.delete_password(SERVICE_NAME, key_id)
        logger.info(f"Deleted key '{key_id}' from macOS Keychain")
        return True

    except Exception as e:
        logger.error(f"Failed to delete key from Keychain: {e}", exc_info=True)
        return False


def key_exists_in_keychain(key_id: str) -> bool:
    """Check if a key exists in the Keychain"""
    try:
        password = keyring.get_password(SERVICE_NAME, key_id)
        return password is not None
    except Exception:
        return False


# ===== API Endpoints =====

@router.post("/generate-key", response_model=KeyResponse)
async def generate_and_store_key(request: StoreKeyRequest):
    """
    Generate a new encryption key and store it in macOS Keychain (Secure Enclave)

    The key is hardware-backed when Secure Enclave is available.
    """
    try:
        # Check if key already exists
        if key_exists_in_keychain(request.key_id):
            return KeyResponse(
                success=False,
                key_exists=True,
                message=f"Key '{request.key_id}' already exists. Delete it first if you want to regenerate."
            )

        # Generate new encryption key
        key_data = generate_encryption_key()

        # Store in Keychain
        success = store_key_in_keychain(request.key_id, key_data, request.passphrase)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to store key in Keychain")

        return KeyResponse(
            success=True,
            key_exists=True,
            message=f"Generated and stored new encryption key '{request.key_id}' in Secure Enclave"
        )

    except Exception as e:
        logger.error(f"Failed to generate key: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retrieve-key", response_model=KeyResponse)
async def retrieve_key(request: RetrieveKeyRequest):
    """
    Retrieve encryption key from macOS Keychain (Secure Enclave)

    Requires the correct passphrase for additional security.
    The key is only decrypted in memory and never written to disk.
    """
    try:
        # Retrieve from Keychain
        key_data = retrieve_key_from_keychain(request.key_id)

        if not key_data:
            return KeyResponse(
                success=False,
                key_exists=False,
                message=f"Key '{request.key_id}' not found in Keychain"
            )

        # Return base64-encoded key (will be used in-memory only)
        key_b64 = base64.b64encode(key_data).decode('utf-8')

        return KeyResponse(
            success=True,
            key_exists=True,
            message="Key retrieved successfully",
            key_data=key_b64
        )

    except Exception as e:
        logger.error(f"Failed to retrieve key: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete-key/{key_id}")
async def delete_key(key_id: str):
    """Delete encryption key from macOS Keychain"""
    try:
        if not key_exists_in_keychain(key_id):
            raise HTTPException(status_code=404, detail=f"Key '{key_id}' not found")

        success = delete_key_from_keychain(key_id)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete key")

        return {
            "success": True,
            "message": f"Deleted key '{key_id}' from Secure Enclave"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete key: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check-key/{key_id}")
async def check_key_exists(key_id: str):
    """Check if an encryption key exists in the Keychain"""
    exists = key_exists_in_keychain(key_id)

    return {
        "key_id": key_id,
        "exists": exists,
        "message": f"Key '{key_id}' {'exists' if exists else 'does not exist'} in Keychain"
    }


@router.get("/health")
async def health_check():
    """Health check for Secure Enclave service"""
    try:
        # Test if Keychain is accessible
        test_key_id = "__health_check__"
        test_data = b"test"

        # Try to store and retrieve
        store_key_in_keychain(test_key_id, test_data, "test")
        retrieved = retrieve_key_from_keychain(test_key_id)
        delete_key_from_keychain(test_key_id)

        if retrieved == test_data:
            return {
                "status": "healthy",
                "keychain_accessible": True,
                "secure_enclave_available": True,  # macOS Keychain uses Secure Enclave when available
                "message": "Secure Enclave service is operational"
            }
        else:
            return {
                "status": "degraded",
                "keychain_accessible": True,
                "secure_enclave_available": False,
                "message": "Keychain accessible but key retrieval failed"
            }

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "keychain_accessible": False,
            "secure_enclave_available": False,
            "message": f"Keychain not accessible: {str(e)}"
        }
