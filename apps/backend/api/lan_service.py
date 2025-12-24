"""
LAN Discovery API Endpoints

FastAPI routes for LAN discovery and central hub management.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import logging

from .lan_discovery import lan_service

logger = logging.getLogger(__name__)

from fastapi import Depends
from api.auth_middleware import get_current_user

router = APIRouter(
    prefix="/api/v1/lan",
    tags=["LAN Discovery"],
    dependencies=[Depends(get_current_user)]  # Require auth
)


class StartHubRequest(BaseModel):
    """Request to start hub"""
    port: Optional[int] = 8765
    device_name: Optional[str] = None


class JoinDeviceRequest(BaseModel):
    """Request to join a discovered device"""
    device_id: str


class RegisterClientRequest(BaseModel):
    """Request from a client to register with this hub"""
    client_id: str
    client_name: str
    client_ip: str


class UnregisterClientRequest(BaseModel):
    """Request from a client to unregister from this hub"""
    client_id: str


@router.post("/discovery/start")
async def start_discovery(request: Request) -> Dict[str, Any]:
    """
    Start discovering ElohimOS instances on the local network

    Returns:
        Status of discovery service
    """
    try:
        await lan_service.start_discovery()
        return {
            "status": "success",
            "message": "LAN discovery started",
            "service_info": lan_service.get_status()
        }
    except Exception as e:
        logger.error(f"Failed to start discovery: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discovery/stop")
async def stop_discovery(request: Request) -> Dict[str, Any]:
    """
    Stop LAN discovery

    Returns:
        Status message
    """
    try:
        await lan_service.stop_discovery()
        return {
            "status": "success",
            "message": "LAN discovery stopped"
        }
    except Exception as e:
        logger.error(f"Failed to stop discovery: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices")
async def get_discovered_devices() -> Dict[str, Any]:
    """
    Get list of discovered ElohimOS instances on the network

    Returns:
        List of discovered devices
    """
    try:
        devices = lan_service.get_discovered_devices()
        return {
            "status": "success",
            "devices": devices,
            "count": len(devices)
        }
    except Exception as e:
        logger.error(f"Failed to get devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hub/start")
async def start_hub(request: Request, body: StartHubRequest) -> Dict[str, Any]:
    """
    Start this instance as a central hub
    Other devices can discover and connect to this hub

    Args:
        request: Hub configuration (port, device_name)

    Returns:
        Hub status
    """
    try:
        # Update device name if provided
        if body.device_name:
            lan_service.device_name = body.device_name

        await lan_service.start_hub(port=body.port)

        return {
            "status": "success",
            "message": "Hub started successfully",
            "hub_info": {
                "device_id": lan_service.device_id,
                "device_name": lan_service.device_name,
                "port": body.port,
                "local_ip": lan_service._get_local_ip()
            }
        }
    except Exception as e:
        logger.error(f"Failed to start hub: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hub/stop")
async def stop_hub(request: Request) -> Dict[str, Any]:
    """
    Stop broadcasting as hub

    Returns:
        Status message
    """
    try:
        await lan_service.stop_hub()
        return {
            "status": "success",
            "message": "Hub stopped"
        }
    except Exception as e:
        logger.error(f"Failed to stop hub: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connect")
async def connect_to_device(request: Request, body: JoinDeviceRequest) -> Dict[str, Any]:
    """
    Connect to a discovered hub device

    Args:
        body: Device ID to connect to

    Returns:
        Connection status with hub info
    """
    try:
        result = await lan_service.connect_to_device(body.device_id)

        return {
            "status": "success",
            "message": f"Connected to {result['hub']['name']}",
            **result
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to connect to device: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disconnect")
async def disconnect_from_hub(request: Request) -> Dict[str, Any]:
    """
    Disconnect from the currently connected hub

    Returns:
        Disconnection status
    """
    try:
        result = await lan_service.disconnect_from_hub()

        if result["status"] == "not_connected":
            return {
                "status": "success",
                "message": "Not connected to any hub"
            }

        return {
            "status": "success",
            "message": f"Disconnected from {result['hub']['name']}",
            **result
        }

    except Exception as e:
        logger.error(f"Failed to disconnect: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_lan_status() -> Dict[str, Any]:
    """
    Get current LAN discovery status

    Returns:
        Current status including hub state, discovered devices, etc.
    """
    try:
        status = lan_service.get_status()
        devices = lan_service.get_discovered_devices()

        return {
            "status": "success",
            "service": status,
            "devices": devices
        }
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Hub-side endpoints (for receiving client connections) ==========


@router.post("/register-client")
async def register_client(request: Request, body: RegisterClientRequest) -> Dict[str, Any]:
    """
    Register a client connection (called by connecting clients)

    This endpoint is called by other instances when they want to connect to this hub.

    Args:
        body: Client registration info

    Returns:
        Registration confirmation
    """
    try:
        client = lan_service.register_client(
            client_id=body.client_id,
            client_name=body.client_name,
            client_ip=body.client_ip
        )

        return {
            "status": "success",
            "message": f"Client {body.client_name} registered",
            "client": client.to_dict(),
            "hub": {
                "device_id": lan_service.device_id,
                "device_name": lan_service.device_name
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to register client: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/unregister-client")
async def unregister_client(request: Request, body: UnregisterClientRequest) -> Dict[str, Any]:
    """
    Unregister a client (called when client disconnects)

    Args:
        body: Client ID to unregister

    Returns:
        Unregistration confirmation
    """
    try:
        removed = lan_service.unregister_client(body.client_id)

        if removed:
            return {
                "status": "success",
                "message": "Client unregistered"
            }
        else:
            return {
                "status": "success",
                "message": "Client was not registered"
            }

    except Exception as e:
        logger.error(f"Failed to unregister client: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clients")
async def get_connected_clients() -> Dict[str, Any]:
    """
    Get list of connected clients (when running as hub)

    Returns:
        List of connected clients
    """
    try:
        if not lan_service.is_hub:
            raise HTTPException(status_code=400, detail="Not running as hub")

        clients = lan_service.get_connected_clients()

        return {
            "status": "success",
            "clients": clients,
            "count": len(clients)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get clients: {e}")
        raise HTTPException(status_code=500, detail=str(e))
