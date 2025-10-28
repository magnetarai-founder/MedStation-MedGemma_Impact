"""
E2E Encryption API Router
Exposes endpoints for the E2E encryption service
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/e2e", tags=["e2e-encryption"])


class DeviceInfo(BaseModel):
    device_id: str
    fingerprint: str
    public_key: str
    created_at: str


class PeerKeyInfo(BaseModel):
    peer_device_id: str
    public_key: str
    fingerprint: str
    verified: bool
    safety_number: str


@router.get("/device", response_model=DeviceInfo)
async def get_device_info():
    """
    Get current device's E2E encryption information

    Returns device ID, fingerprint, and public key
    """
    try:
        from e2e_encryption_service import get_e2e_service

        service = get_e2e_service()
        device_id = service.device_id
        keypair = service.get_device_keypair()

        if not keypair:
            raise HTTPException(status_code=404, detail="Device keypair not found")

        return DeviceInfo(
            device_id=device_id,
            fingerprint=keypair["fingerprint"],
            public_key=keypair["public_key"].hex(),
            created_at=keypair["created_at"]
        )
    except ImportError:
        raise HTTPException(status_code=503, detail="E2E encryption service not available")
    except Exception as e:
        logger.error(f"Error getting device info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/peers", response_model=list[PeerKeyInfo])
async def get_peer_keys():
    """
    Get all known peer public keys

    Returns list of peer devices and their verification status
    """
    try:
        from e2e_encryption_service import get_e2e_service

        service = get_e2e_service()
        peers = service.get_all_peer_keys()

        result = []
        for peer_id, peer_data in peers.items():
            result.append(PeerKeyInfo(
                peer_device_id=peer_id,
                public_key=peer_data["public_key"].hex(),
                fingerprint=peer_data["fingerprint"],
                verified=peer_data.get("verified", False),
                safety_number=peer_data.get("safety_number", "")
            ))

        return result
    except ImportError:
        raise HTTPException(status_code=503, detail="E2E encryption service not available")
    except Exception as e:
        logger.error(f"Error getting peer keys: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/peers/{peer_device_id}/verify")
async def verify_peer(peer_device_id: str):
    """
    Mark a peer device as verified

    Args:
        peer_device_id: The peer's device ID to verify
    """
    try:
        from e2e_encryption_service import get_e2e_service

        service = get_e2e_service()
        service.verify_peer(peer_device_id)

        return {"success": True, "message": f"Peer {peer_device_id} verified"}
    except ImportError:
        raise HTTPException(status_code=503, detail="E2E encryption service not available")
    except Exception as e:
        logger.error(f"Error verifying peer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/device/qr")
async def get_device_qr():
    """
    Get QR code for device linking

    Returns base64 encoded QR code image
    """
    try:
        from e2e_encryption_service import get_e2e_service
        import qrcode
        from io import BytesIO
        import base64

        service = get_e2e_service()
        keypair = service.get_device_keypair()

        if not keypair:
            raise HTTPException(status_code=404, detail="Device keypair not found")

        # Create QR code data
        qr_data = {
            "device_id": service.device_id,
            "public_key": keypair["public_key"].hex(),
            "fingerprint": keypair["fingerprint"]
        }

        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(str(qr_data))
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode()

        return {"qr_code": f"data:image/png;base64,{img_str}"}
    except ImportError as e:
        if "qrcode" in str(e):
            raise HTTPException(status_code=503, detail="QR code generation not available (install qrcode)")
        raise HTTPException(status_code=503, detail="E2E encryption service not available")
    except Exception as e:
        logger.error(f"Error generating QR code: {e}")
        raise HTTPException(status_code=500, detail=str(e))
