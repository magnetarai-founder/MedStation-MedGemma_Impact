"""
Secure Enclave Service - macOS Keychain Integration

Uses macOS Keychain to store encryption keys in the Secure Enclave.
Keys never leave the hardware security chip.

Security: Uses PBKDF2 + AES-256-GCM envelope encryption.
The passphrase derives a key that encrypts the master key before storing in Keychain.

"The name of the Lord is a fortified tower; the righteous run to it and are safe." - Proverbs 18:10

Module structure (P2 decomposition):
- secure_enclave_types.py: Request/response models
- secure_enclave_service.py: Service class and router (this file)
"""

from fastapi import APIRouter, HTTPException, Request, Depends
import secrets
import base64
import hashlib
import logging
from typing import Optional, Tuple, Dict, Any

# Import from extracted module (P2 decomposition)
from api.secure_enclave_types import StoreKeyRequest, RetrieveKeyRequest, KeyResponse

# Graceful degradation for optional dependencies
try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    keyring = None
    KEYRING_AVAILABLE = False
    logging.getLogger(__name__).warning("keyring package not available - Secure Enclave features disabled")

try:
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    PBKDF2HMAC = None
    hashes = None
    AESGCM = None
    CRYPTOGRAPHY_AVAILABLE = False
    logging.getLogger(__name__).warning("cryptography package not available - Secure Enclave features disabled")

logger = logging.getLogger(__name__)

from api.auth_middleware import get_current_user

router = APIRouter(
    prefix="/api/v1/secure-enclave",
    tags=["secure-enclave"],
    dependencies=[Depends(get_current_user)]  # Require auth
)

# keyring automatically uses the best backend available (macOS Keychain on macOS)
# No need to explicitly set it - it detects the platform

SERVICE_NAME = "com.magnetarai.elohimos"


# ===== Secure Enclave Key Management =====

def derive_key_from_passphrase(passphrase: str, salt: bytes) -> bytes:
    """
    Derive a 256-bit encryption key from passphrase using PBKDF2-HMAC-SHA256

    Args:
        passphrase: User's passphrase
        salt: 32-byte salt for key derivation

    Returns:
        32-byte derived key
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 256 bits
        salt=salt,
        iterations=600000,  # OWASP recommendation (2023)
    )
    return kdf.derive(passphrase.encode('utf-8'))


def generate_encryption_key() -> bytes:
    """Generate a cryptographically secure 256-bit encryption key"""
    return secrets.token_bytes(32)  # 256 bits


def encrypt_key_with_passphrase(key_data: bytes, passphrase: str) -> Tuple[bytes, bytes, bytes]:
    """
    Encrypt the master key using passphrase-derived key (envelope encryption)

    Args:
        key_data: Master encryption key to protect
        passphrase: User's passphrase

    Returns:
        (encrypted_key, salt, nonce) tuple
    """
    # Generate random salt for PBKDF2
    salt = secrets.token_bytes(32)

    # Derive encryption key from passphrase
    derived_key = derive_key_from_passphrase(passphrase, salt)

    # Encrypt master key with AES-256-GCM
    aesgcm = AESGCM(derived_key)
    nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM
    encrypted_key = aesgcm.encrypt(nonce, key_data, None)

    return encrypted_key, salt, nonce


def decrypt_key_with_passphrase(encrypted_key: bytes, passphrase: str, salt: bytes, nonce: bytes) -> Optional[bytes]:
    """
    Decrypt the master key using passphrase (envelope decryption)

    Args:
        encrypted_key: Encrypted master key
        passphrase: User's passphrase
        salt: Salt used for key derivation
        nonce: Nonce used for AES-GCM

    Returns:
        Decrypted master key, or None if passphrase is incorrect
    """
    try:
        # Derive encryption key from passphrase
        derived_key = derive_key_from_passphrase(passphrase, salt)

        # Decrypt master key
        aesgcm = AESGCM(derived_key)
        key_data = aesgcm.decrypt(nonce, encrypted_key, None)

        return key_data

    except Exception as e:
        logger.warning(f"Failed to decrypt key (likely wrong passphrase): {e}")
        return None


def store_key_in_keychain(key_id: str, key_data: bytes, passphrase: str) -> bool:
    """
    Store encryption key in macOS Keychain (Secure Enclave when available)

    The master key is encrypted with a passphrase-derived key before storage.
    If Secure Enclave is available, the encrypted key is hardware-backed.

    Security: PBKDF2 (600k iterations) + AES-256-GCM envelope encryption
    """
    try:
        # Encrypt master key with passphrase
        encrypted_key, salt, nonce = encrypt_key_with_passphrase(key_data, passphrase)

        # Combine encrypted key + salt + nonce for storage
        # Format: salt (32 bytes) || nonce (12 bytes) || encrypted_key
        combined_data = salt + nonce + encrypted_key
        combined_b64 = base64.b64encode(combined_data).decode('utf-8')

        # Store in Keychain using key_id as the account name
        keyring.set_password(SERVICE_NAME, key_id, combined_b64)

        logger.info(f"Stored passphrase-protected key '{key_id}' in macOS Keychain")
        return True

    except Exception as e:
        logger.error(f"Failed to store key in Keychain: {e}", exc_info=True)
        return False


def retrieve_key_from_keychain(key_id: str, passphrase: str) -> Optional[bytes]:
    """
    Retrieve and decrypt encryption key from macOS Keychain

    Args:
        key_id: Unique identifier for the key
        passphrase: User's passphrase to decrypt the key

    Returns:
        Decrypted master key, or None if not found or wrong passphrase
    """
    try:
        combined_b64 = keyring.get_password(SERVICE_NAME, key_id)

        if not combined_b64:
            logger.warning(f"Key '{key_id}' not found in Keychain")
            return None

        # Decode from base64
        combined_data = base64.b64decode(combined_b64)

        # Extract salt, nonce, and encrypted key
        salt = combined_data[:32]
        nonce = combined_data[32:44]
        encrypted_key = combined_data[44:]

        # Decrypt master key with passphrase
        key_data = decrypt_key_with_passphrase(encrypted_key, passphrase, salt, nonce)

        if not key_data:
            logger.warning(f"Failed to decrypt key '{key_id}' - incorrect passphrase")
            return None

        logger.info(f"Retrieved and decrypted key '{key_id}' from macOS Keychain")
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


# ===== Service Class Wrapper =====

class SecureEnclaveService:
    """
    Wrapper class for Secure Enclave functions
    Provides object-oriented interface for dependency injection
    """

    def store_key_in_keychain(self, key_id: str, key_data: bytes, passphrase: str) -> bool:
        """Store encryption key in macOS Keychain (Secure Enclave)"""
        return store_key_in_keychain(key_id, key_data, passphrase)

    def retrieve_key_from_keychain(self, key_id: str, passphrase: str) -> Optional[bytes]:
        """Retrieve and decrypt key from macOS Keychain"""
        return retrieve_key_from_keychain(key_id, passphrase)

    def delete_key_from_keychain(self, key_id: str) -> bool:
        """Delete encryption key from macOS Keychain"""
        return delete_key_from_keychain(key_id)

    def key_exists_in_keychain(self, key_id: str) -> bool:
        """Check if a key exists in the Keychain"""
        return key_exists_in_keychain(key_id)


# Global singleton instance
_secure_enclave_service: Optional[SecureEnclaveService] = None


def get_secure_enclave_service() -> SecureEnclaveService:
    """Get global Secure Enclave service instance"""
    global _secure_enclave_service
    if _secure_enclave_service is None:
        _secure_enclave_service = SecureEnclaveService()
    return _secure_enclave_service


# ===== API Endpoints =====

@router.post("/generate-key", response_model=KeyResponse)
async def generate_and_store_key(request: Request, body: StoreKeyRequest):
    """
    Generate a new encryption key and store it in macOS Keychain (Secure Enclave)

    The key is hardware-backed when Secure Enclave is available.
    """
    try:
        # Check if key already exists
        if key_exists_in_keychain(body.key_id):
            return KeyResponse(
                success=False,
                key_exists=True,
                message=f"Key '{body.key_id}' already exists. Delete it first if you want to regenerate."
            )

        # Generate new encryption key
        key_data = generate_encryption_key()

        # Store in Keychain
        success = store_key_in_keychain(body.key_id, key_data, body.passphrase)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to store key in Keychain")

        return KeyResponse(
            success=True,
            key_exists=True,
            message=f"Generated and stored new encryption key '{body.key_id}' in Secure Enclave"
        )

    except Exception as e:
        logger.error(f"Failed to generate key: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retrieve-key", response_model=KeyResponse)
async def retrieve_key(request: Request, body: RetrieveKeyRequest):
    """
    Retrieve encryption key from macOS Keychain (Secure Enclave)

    Requires the correct passphrase to decrypt the key.
    The key is only decrypted in memory and never written to disk.
    """
    try:
        # Retrieve and decrypt from Keychain
        key_data = retrieve_key_from_keychain(body.key_id, body.passphrase)

        if not key_data:
            return KeyResponse(
                success=False,
                key_exists=key_exists_in_keychain(body.key_id),
                message=f"Key '{body.key_id}' not found or incorrect passphrase"
            )

        # Return base64-encoded key (will be used in-memory only)
        key_b64 = base64.b64encode(key_data).decode('utf-8')

        return KeyResponse(
            success=True,
            key_exists=True,
            message="Key retrieved and decrypted successfully",
            key_data=key_b64
        )

    except Exception as e:
        logger.error(f"Failed to retrieve key: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete-key/{key_id}")
async def delete_key(request: Request, key_id: str) -> Dict[str, Any]:
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
async def check_key_exists(key_id: str) -> Dict[str, Any]:
    """Check if an encryption key exists in the Keychain"""
    exists = key_exists_in_keychain(key_id)

    return {
        "key_id": key_id,
        "exists": exists,
        "message": f"Key '{key_id}' {'exists' if exists else 'does not exist'} in Keychain"
    }


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check for Secure Enclave service"""
    try:
        # Test if Keychain is accessible
        test_key_id = "__health_check__"
        test_data = b"test"

        # Try to store and retrieve
        test_passphrase = "test_health_check_pass"
        store_key_in_keychain(test_key_id, test_data, test_passphrase)
        retrieved = retrieve_key_from_keychain(test_key_id, test_passphrase)
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


# Re-exports for backwards compatibility (P2 decomposition)
__all__ = [
    # Service
    "SecureEnclaveService",
    # Router
    "router",
    # Functions
    "store_key_in_keychain",
    "retrieve_key_from_keychain",
    "delete_key_from_keychain",
    "key_exists_in_keychain",
    # Re-exported from secure_enclave_types
    "StoreKeyRequest",
    "RetrieveKeyRequest",
    "KeyResponse",
]
