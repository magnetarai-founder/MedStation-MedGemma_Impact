"""
P2P Chat - E2E Encryption Routes

End-to-end encryption key management and device linking endpoints.
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request
import logging

from api.p2p_chat_service import get_p2p_chat_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/e2e/init")
async def initialize_e2e_keys(request: Request, device_id: str, passphrase: str) -> Dict[str, Any]:
    """
    Initialize E2E encryption keys for this device

    Args:
        device_id: Unique device identifier
        passphrase: User's passphrase for Secure Enclave

    Returns:
        Dict with public_key and fingerprint
    """
    service = get_p2p_chat_service()

    if not service:
        raise HTTPException(status_code=503, detail="P2P service not initialized")

    try:
        result = service.init_device_keys(device_id, passphrase)
        return result
    except Exception as e:
        logger.error(f"Failed to initialize E2E keys: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/e2e/peers/{peer_id}/keys")
async def store_peer_public_key(request: Request, peer_id: str, public_key_hex: str, verify_key_hex: str) -> Dict[str, Any]:
    """
    Store a peer's public key and generate safety number

    Args:
        peer_id: Peer's device identifier
        public_key_hex: Peer's Curve25519 public key (hex encoded)
        verify_key_hex: Peer's Ed25519 verify key (hex encoded)

    Returns:
        Dict with safety_number and fingerprint
    """
    service = get_p2p_chat_service()

    if not service:
        raise HTTPException(status_code=503, detail="P2P service not initialized")

    try:
        public_key = bytes.fromhex(public_key_hex)
        verify_key = bytes.fromhex(verify_key_hex)
        result = service.store_peer_key(peer_id, public_key, verify_key)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid key format: {e}")
    except Exception as e:
        logger.error(f"Failed to store peer key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/e2e/peers/{peer_id}/verify")
async def verify_peer(request: Request, peer_id: str) -> Dict[str, str]:
    """
    Mark a peer's fingerprint as verified

    Args:
        peer_id: Peer's device identifier

    Returns:
        Success status
    """
    service = get_p2p_chat_service()

    if not service:
        raise HTTPException(status_code=503, detail="P2P service not initialized")

    try:
        result = service.verify_peer_fingerprint(peer_id)
        return {"status": "verified", "peer_id": peer_id}
    except Exception as e:
        logger.error(f"Failed to verify peer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/e2e/safety-changes")
async def get_safety_changes() -> Dict[str, Any]:
    """
    Get list of unacknowledged safety number changes

    Returns:
        List of safety number changes that need user acknowledgment
    """
    service = get_p2p_chat_service()

    if not service:
        raise HTTPException(status_code=503, detail="P2P service not initialized")

    try:
        changes = service.get_unacknowledged_safety_changes()
        return {"changes": changes, "total": len(changes)}
    except Exception as e:
        logger.error(f"Failed to get safety changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/e2e/safety-changes/{change_id}/acknowledge")
async def acknowledge_safety_change(request: Request, change_id: int) -> Dict[str, Any]:
    """
    Mark a safety number change as acknowledged

    Args:
        change_id: ID of the safety number change

    Returns:
        Success status
    """
    service = get_p2p_chat_service()

    if not service:
        raise HTTPException(status_code=503, detail="P2P service not initialized")

    try:
        result = service.acknowledge_safety_change(change_id)
        return {"status": "acknowledged", "change_id": change_id}
    except Exception as e:
        logger.error(f"Failed to acknowledge safety change: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/e2e/export")
async def export_identity(request: Request, passphrase: str) -> Dict[str, Any]:
    """
    Export identity keypair for linking to another device (QR code)

    Args:
        passphrase: User's passphrase

    Returns:
        Encrypted bundle for QR code scanning
    """
    service = get_p2p_chat_service()

    if not service:
        raise HTTPException(status_code=503, detail="P2P service not initialized")

    try:
        bundle = service.e2e_service.export_identity_for_linking(passphrase)
        return bundle
    except Exception as e:
        logger.error(f"Failed to export identity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/e2e/import")
async def import_identity(
    request: Request,
    encrypted_bundle: str,
    salt: str,
    nonce: str,
    passphrase: str,
    new_device_id: str
) -> Dict[str, str]:
    """
    Import identity keypair from another device (from QR code)

    Args:
        encrypted_bundle: Encrypted bundle (hex)
        salt: Salt (hex)
        nonce: Nonce (hex)
        passphrase: User's passphrase
        new_device_id: Device ID for this device

    Returns:
        Dict with public_key and fingerprint
    """
    service = get_p2p_chat_service()

    if not service:
        raise HTTPException(status_code=503, detail="P2P service not initialized")

    try:
        encrypted_data = {
            "encrypted_bundle": encrypted_bundle,
            "salt": salt,
            "nonce": nonce
        }

        public_key, fingerprint = service.e2e_service.import_identity_from_link(
            encrypted_data,
            passphrase,
            new_device_id
        )

        return {
            "public_key": public_key.hex(),
            "fingerprint": service.e2e_service.format_fingerprint(fingerprint),
            "device_id": new_device_id
        }
    except Exception as e:
        logger.error(f"Failed to import identity: {e}")
        raise HTTPException(status_code=500, detail=str(e))
