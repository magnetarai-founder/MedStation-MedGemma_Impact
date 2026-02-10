"""
LAN Discovery API Endpoints

FastAPI routes for LAN discovery and central hub management.

Module structure (P2 decomposition):
- lan_types.py: Request models
- lan_service.py: API endpoints (this file)
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from typing import Any, Dict, List
import logging

from api.errors import http_400, http_500
from api.lan_discovery.service import lan_service
from api.auth_middleware import get_current_user

# Import from extracted module (P2 decomposition)
from api.lan_discovery.types import (
    StartHubRequest,
    JoinDeviceRequest,
    RegisterClientRequest,
    UnregisterClientRequest,
    HeartbeatConfigRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/lan",
    tags=["LAN Discovery"],
    dependencies=[Depends(get_current_user)]  # Require auth
)


@router.post("/discovery/start")
async def start_discovery(request: Request) -> Dict[str, Any]:
    """
    Start discovering MedStation instances on the local network

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
        raise http_500(str(e))


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
        raise http_500(str(e))


@router.get("/devices")
async def get_discovered_devices() -> Dict[str, Any]:
    """
    Get list of discovered MedStation instances on the network

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
        raise http_500(str(e))


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
        raise http_500(str(e))


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
        raise http_500(str(e))


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
        raise http_400(str(e))
    except Exception as e:
        logger.error(f"Failed to connect to device: {e}")
        raise http_500(str(e))


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
        raise http_500(str(e))


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
        raise http_500(str(e))


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
        raise http_400(str(e))
    except Exception as e:
        logger.error(f"Failed to register client: {e}")
        raise http_500(str(e))


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
        raise http_500(str(e))


@router.get("/clients")
async def get_connected_clients() -> Dict[str, Any]:
    """
    Get list of connected clients (when running as hub)

    Returns:
        List of connected clients
    """
    try:
        if not lan_service.is_hub:
            raise http_400("Not running as hub")

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
        raise http_500(str(e))


# ========== Connection Health & Resilience Endpoints ==========


@router.get("/health")
async def get_connection_health() -> Dict[str, Any]:
    """
    Get detailed connection health information.

    Returns connection state, last heartbeat time, failure counts,
    and auto-reconnect status.
    """
    try:
        return {
            "status": "success",
            "health": lan_service.connection_health.to_dict(),
            "auto_reconnect_enabled": lan_service._auto_reconnect,
            "heartbeat_interval": lan_service._heartbeat_interval,
            "heartbeat_active": (
                lan_service._heartbeat_task is not None
                and not lan_service._heartbeat_task.done()
            ),
        }
    except Exception as e:
        logger.error(f"Failed to get health: {e}")
        raise http_500(str(e))


@router.post("/heartbeat")
async def send_heartbeat() -> Dict[str, Any]:
    """
    Manually trigger a heartbeat ping to the connected hub.

    Useful for testing connection health without waiting for
    the automatic heartbeat interval.
    """
    try:
        if not lan_service.is_connected:
            return {
                "status": "success",
                "heartbeat": "skipped",
                "reason": "not connected to any hub"
            }

        success = await lan_service.send_heartbeat()

        return {
            "status": "success",
            "heartbeat": "ok" if success else "failed",
            "health": lan_service.connection_health.to_dict()
        }
    except Exception as e:
        logger.error(f"Heartbeat error: {e}")
        raise http_500(str(e))


@router.post("/heartbeat/configure")
async def configure_heartbeat(
    request: Request,
    body: HeartbeatConfigRequest
) -> Dict[str, Any]:
    """
    Configure heartbeat and auto-reconnect settings.

    Args:
        body: Configuration options (interval, auto_reconnect)

    Returns:
        Updated configuration
    """
    try:
        if body.interval_seconds is not None:
            lan_service.set_heartbeat_interval(body.interval_seconds)

        if body.auto_reconnect is not None:
            lan_service.set_auto_reconnect(body.auto_reconnect)

        return {
            "status": "success",
            "message": "Heartbeat configuration updated",
            "config": {
                "interval_seconds": lan_service._heartbeat_interval,
                "auto_reconnect": lan_service._auto_reconnect
            }
        }
    except Exception as e:
        logger.error(f"Failed to configure heartbeat: {e}")
        raise http_500(str(e))


@router.post("/reconnect")
async def manual_reconnect(request: Request) -> Dict[str, Any]:
    """
    Manually trigger reconnection to the last known hub.

    Use this if auto-reconnect is disabled or you want to force
    an immediate reconnection attempt.
    """
    try:
        if not lan_service.connected_hub:
            raise http_400("No hub to reconnect to - discover and connect first")

        hub_id = lan_service.connected_hub.id

        # Reset connection state for fresh reconnect
        lan_service.is_connected = False

        result = await lan_service.connect_to_device(
            hub_id,
            with_retry=True,
            start_heartbeat=True
        )

        return {
            "status": "success",
            "message": "Reconnected successfully",
            **result
        }

    except ValueError as e:
        raise http_400(str(e))
    except Exception as e:
        logger.error(f"Reconnect failed: {e}")
        raise http_500(str(e))


# Re-exports for backwards compatibility (P2 decomposition)
__all__ = [
    # Router
    "router",
    # Re-exported from lan_types
    "StartHubRequest",
    "JoinDeviceRequest",
    "RegisterClientRequest",
    "UnregisterClientRequest",
    "HeartbeatConfigRequest",
]
