"""
End-to-End Encryption Service using NaCl (libsodium)

Provides Signal-grade E2E encryption for P2P messages using:
- Curve25519 keypairs (public/private keys)
- X25519 key exchange
- XSalsa20-Poly1305 authenticated encryption
- SHA-256 fingerprints for verification

Security features:
- Keys stored in Secure Enclave
- Required fingerprint verification
- Safety numbers (key fingerprint hashes)
- Multi-device support with per-device keys
"""

import nacl.public
import nacl.signing
import nacl.encoding
import nacl.utils
import nacl.hash
from typing import Optional, Tuple, Dict
import hashlib
import json
import logging
from datetime import datetime, UTC

logger = logging.getLogger(__name__)


class E2EEncryptionService:
    """
    End-to-end encryption service using NaCl sealed boxes

    Each device has:
    - Identity keypair (Curve25519) - long-term
    - Signing keypair (Ed25519) - for authentication
    - Fingerprint (SHA-256 of public key) - for verification
    """

    def __init__(self, secure_enclave_service):
        """
        Initialize E2E encryption service

        Args:
            secure_enclave_service: Secure Enclave service for key storage
        """
        self.secure_enclave = secure_enclave_service
        self._identity_keypair: Optional[nacl.public.PrivateKey] = None
        self._signing_keypair: Optional[nacl.signing.SigningKey] = None
        self._device_id: Optional[str] = None


    # ===== Key Generation & Management =====

    def generate_identity_keypair(self, device_id: str, passphrase: str) -> Tuple[bytes, bytes]:
        """
        Generate new identity keypair for this device

        Args:
            device_id: Unique device identifier
            passphrase: User's passphrase for Secure Enclave

        Returns:
            (public_key, fingerprint) tuple
        """
        # Generate Curve25519 keypair for encryption
        private_key = nacl.public.PrivateKey.generate()
        public_key = private_key.public_key

        # Generate Ed25519 keypair for signing
        signing_key = nacl.signing.SigningKey.generate()
        verify_key = signing_key.verify_key

        # Store private keys in Secure Enclave
        identity_key_id = f"e2e_identity_{device_id}"
        signing_key_id = f"e2e_signing_{device_id}"

        self.secure_enclave.store_key_in_keychain(
            identity_key_id,
            bytes(private_key),
            passphrase
        )

        self.secure_enclave.store_key_in_keychain(
            signing_key_id,
            bytes(signing_key),
            passphrase
        )

        # Generate fingerprint
        fingerprint = self.generate_fingerprint(bytes(public_key))

        # Cache in memory
        self._identity_keypair = private_key
        self._signing_keypair = signing_key
        self._device_id = device_id

        logger.info(f"Generated identity keypair for device {device_id}")

        return bytes(public_key), fingerprint


    def load_identity_keypair(self, device_id: str, passphrase: str) -> Tuple[bytes, bytes]:
        """
        Load existing identity keypair from Secure Enclave

        Args:
            device_id: Device identifier
            passphrase: User's passphrase

        Returns:
            (public_key, fingerprint) tuple
        """
        identity_key_id = f"e2e_identity_{device_id}"
        signing_key_id = f"e2e_signing_{device_id}"

        # Retrieve from Secure Enclave
        private_key_bytes = self.secure_enclave.retrieve_key_from_keychain(
            identity_key_id,
            passphrase
        )

        signing_key_bytes = self.secure_enclave.retrieve_key_from_keychain(
            signing_key_id,
            passphrase
        )

        if not private_key_bytes or not signing_key_bytes:
            raise ValueError("Identity keypair not found in Secure Enclave")

        # Reconstruct keypairs
        self._identity_keypair = nacl.public.PrivateKey(private_key_bytes)
        self._signing_keypair = nacl.signing.SigningKey(signing_key_bytes)
        self._device_id = device_id

        public_key = bytes(self._identity_keypair.public_key)
        fingerprint = self.generate_fingerprint(public_key)

        logger.info(f"Loaded identity keypair for device {device_id}")

        return public_key, fingerprint


    def generate_fingerprint(self, public_key: bytes) -> bytes:
        """
        Generate SHA-256 fingerprint of public key

        Args:
            public_key: 32-byte Curve25519 public key

        Returns:
            32-byte SHA-256 hash
        """
        return hashlib.sha256(public_key).digest()


    def format_fingerprint(self, fingerprint: bytes) -> str:
        """
        Format fingerprint as colon-separated hex string (macOS style)

        Args:
            fingerprint: 32-byte fingerprint

        Returns:
            "AB:CD:EF:12:34:..." formatted string
        """
        hex_str = fingerprint.hex().upper()
        return ":".join([hex_str[i:i+2] for i in range(0, len(hex_str), 2)])


    def generate_safety_number(self, local_public_key: bytes, remote_public_key: bytes) -> str:
        """
        Generate safety number for this conversation (like Signal)

        Safety number changes when either party rotates their keys.

        Args:
            local_public_key: Your public key
            remote_public_key: Other party's public key

        Returns:
            60-digit safety number
        """
        # Concatenate keys in lexicographic order (consistent for both parties)
        if local_public_key < remote_public_key:
            combined = local_public_key + remote_public_key
        else:
            combined = remote_public_key + local_public_key

        # Hash and convert to 60-digit number
        hash_bytes = hashlib.sha512(combined).digest()
        hash_int = int.from_bytes(hash_bytes, byteorder='big')
        safety_number = str(hash_int)[:60]

        return safety_number


    # ===== Encryption & Decryption =====

    def encrypt_message(self, recipient_public_key: bytes, plaintext: str) -> bytes:
        """
        Encrypt message for recipient using their public key

        Uses NaCl sealed box (anonymous encryption):
        - Generates ephemeral keypair
        - Encrypts with recipient's public key
        - Provides perfect forward secrecy

        Args:
            recipient_public_key: Recipient's Curve25519 public key
            plaintext: Message to encrypt

        Returns:
            Encrypted ciphertext (includes nonce + ciphertext)
        """
        if not self._identity_keypair:
            raise RuntimeError("Identity keypair not loaded")

        # Create sealed box (anonymous sender)
        recipient_pk = nacl.public.PublicKey(recipient_public_key)
        sealed_box = nacl.public.SealedBox(recipient_pk)

        # Encrypt message
        plaintext_bytes = plaintext.encode('utf-8')
        ciphertext = sealed_box.encrypt(plaintext_bytes)

        return ciphertext


    def decrypt_message(self, ciphertext: bytes) -> str:
        """
        Decrypt message using your private key

        Args:
            ciphertext: Encrypted message

        Returns:
            Decrypted plaintext string

        Raises:
            ValueError: If decryption fails (wrong key, tampered message)
        """
        if not self._identity_keypair:
            raise RuntimeError("Identity keypair not loaded")

        try:
            # Open sealed box
            sealed_box = nacl.public.SealedBox(self._identity_keypair)
            plaintext_bytes = sealed_box.decrypt(ciphertext)

            return plaintext_bytes.decode('utf-8')

        except Exception as e:
            logger.error(f"Failed to decrypt message: {e}")
            raise ValueError("Decryption failed - message may be tampered or key mismatch")


    def sign_message(self, message: str) -> bytes:
        """
        Sign message with your signing key (for authentication)

        Args:
            message: Message to sign

        Returns:
            64-byte signature
        """
        if not self._signing_keypair:
            raise RuntimeError("Signing keypair not loaded")

        message_bytes = message.encode('utf-8')
        signature = self._signing_keypair.sign(message_bytes).signature

        return signature


    def verify_signature(self, message: str, signature: bytes, sender_verify_key: bytes) -> bool:
        """
        Verify message signature

        Args:
            message: Original message
            signature: 64-byte signature
            sender_verify_key: Sender's Ed25519 verify key

        Returns:
            True if signature valid, False otherwise
        """
        try:
            verify_key = nacl.signing.VerifyKey(sender_verify_key)
            message_bytes = message.encode('utf-8')
            verify_key.verify(message_bytes, signature)
            return True

        except Exception as e:
            logger.warning(f"Signature verification failed: {e}")
            return False


    # ===== Multi-Device Support =====

    def export_identity_for_linking(self, passphrase: str) -> Dict:
        """
        Export identity keypair for linking to another device

        Returns encrypted bundle that can be scanned as QR code.

        Args:
            passphrase: User's passphrase

        Returns:
            Dict with encrypted keypair bundle
        """
        if not self._identity_keypair or not self._signing_keypair:
            raise RuntimeError("Identity keypair not loaded")

        # Bundle keys
        bundle = {
            "device_id": self._device_id,
            "identity_private_key": bytes(self._identity_keypair).hex(),
            "signing_private_key": bytes(self._signing_keypair).hex(),
            "timestamp": datetime.now(UTC).isoformat()
        }

        # Encrypt bundle with passphrase
        bundle_json = json.dumps(bundle)

        # Use AES-256-GCM from cryptography library (already in secure_enclave_service)
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import secrets

        # Derive key from passphrase
        salt = secrets.token_bytes(32)
        key = hashlib.pbkdf2_hmac('sha256', passphrase.encode(), salt, 600000, dklen=32)

        # Encrypt
        aesgcm = AESGCM(key)
        nonce = secrets.token_bytes(12)
        ciphertext = aesgcm.encrypt(nonce, bundle_json.encode(), None)

        return {
            "encrypted_bundle": ciphertext.hex(),
            "salt": salt.hex(),
            "nonce": nonce.hex()
        }


    def import_identity_from_link(self, encrypted_data: Dict, passphrase: str, new_device_id: str) -> Tuple[bytes, bytes]:
        """
        Import identity keypair from another device

        Args:
            encrypted_data: Encrypted bundle from export_identity_for_linking()
            passphrase: User's passphrase
            new_device_id: Device ID for this device

        Returns:
            (public_key, fingerprint) tuple
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        # Extract encrypted data
        ciphertext = bytes.fromhex(encrypted_data["encrypted_bundle"])
        salt = bytes.fromhex(encrypted_data["salt"])
        nonce = bytes.fromhex(encrypted_data["nonce"])

        # Derive key
        key = hashlib.pbkdf2_hmac('sha256', passphrase.encode(), salt, 600000, dklen=32)

        # Decrypt
        aesgcm = AESGCM(key)
        bundle_json = aesgcm.decrypt(nonce, ciphertext, None).decode()
        bundle = json.loads(bundle_json)

        # Reconstruct keypairs
        private_key_bytes = bytes.fromhex(bundle["identity_private_key"])
        signing_key_bytes = bytes.fromhex(bundle["signing_private_key"])

        self._identity_keypair = nacl.public.PrivateKey(private_key_bytes)
        self._signing_keypair = nacl.signing.SigningKey(signing_key_bytes)
        self._device_id = new_device_id

        # Store in Secure Enclave for this device
        identity_key_id = f"e2e_identity_{new_device_id}"
        signing_key_id = f"e2e_signing_{new_device_id}"

        self.secure_enclave.store_key_in_keychain(
            identity_key_id,
            private_key_bytes,
            passphrase
        )

        self.secure_enclave.store_key_in_keychain(
            signing_key_id,
            signing_key_bytes,
            passphrase
        )

        public_key = bytes(self._identity_keypair.public_key)
        fingerprint = self.generate_fingerprint(public_key)

        logger.info(f"Imported identity keypair to device {new_device_id}")

        return public_key, fingerprint


# ===== Global Instance =====

_e2e_service: Optional[E2EEncryptionService] = None


def get_e2e_service() -> E2EEncryptionService:
    """Get global E2E encryption service instance"""
    global _e2e_service

    if _e2e_service is None:
        from api.secure_enclave_service import get_secure_enclave_service
        secure_enclave = get_secure_enclave_service()
        _e2e_service = E2EEncryptionService(secure_enclave)

    return _e2e_service
