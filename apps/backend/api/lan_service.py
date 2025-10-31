"""
LAN Discovery API Endpoints

FastAPI routes for LAN discovery and central hub management.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Optional
import logging

from .lan_discovery import lan_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/lan", tags=["LAN Discovery"])


class StartHubRequest(BaseModel):
    """Request to start hub"""
    port: Optional[int] = 8765
    device_name: Optional[str] = None


class JoinDeviceRequest(BaseModel):
    """Request to join a discovered device"""
    device_id: str


@router.post("/discovery/start")
async def start_discovery(request: Request):
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
async def stop_discovery(request: Request):
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
async def get_discovered_devices():
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
async def start_hub(request: Request, body: StartHubRequest):
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
async def stop_hub(request: Request):
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
async def connect_to_device(request: Request, body: JoinDeviceRequest):
    """
    Connect to a discovered device

    Args:
        request: Device ID to connect to

    Returns:
        Connection status
    """
    try:
        devices = lan_service.discovered_devices

        if body.device_id not in devices:
            raise HTTPException(status_code=404, detail="Device not found")

        device = devices[body.device_id]

        # TODO: Implement actual connection logic
        # For now, just return success
        logger.info(f"Connecting to device: {device.name} at {device.ip}:{device.port}")

        return {
            "status": "success",
            "message": f"Connected to {device.name}",
            "device": device.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to connect to device: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_lan_status():
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
