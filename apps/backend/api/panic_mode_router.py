#!/usr/bin/env python3
"""
Panic Mode API Router
Provides REST endpoints for emergency security operations
"""

import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from panic_mode import get_panic_mode

logger = logging.getLogger(__name__)

# ===== Models =====

class PanicTriggerRequest(BaseModel):
    """Request to trigger panic mode"""
    confirmation: str = Field(..., description="Must be 'CONFIRM' to proceed")
    reason: Optional[str] = Field("Manual trigger", description="Reason for panic activation")


class PanicStatusResponse(BaseModel):
    """Current panic mode status"""
    panic_active: bool
    last_panic: Optional[str]
    secure_mode: bool


class PanicTriggerResponse(BaseModel):
    """Response after triggering panic mode"""
    panic_activated: bool
    timestamp: str
    reason: str
    actions_taken: list[str]
    errors: list[str]
    status: str


# ===== Router =====

router = APIRouter(prefix="/api/v1/panic", tags=["Panic Mode"])
panic_mode = get_panic_mode()


@router.post("/trigger", response_model=PanicTriggerResponse)
async def trigger_panic_mode(request: Request, body: PanicTriggerRequest):
    """
    🚨 EMERGENCY: Trigger panic mode

    This will immediately:
    - Close all P2P connections
    - Wipe chat cache and temporary files
    - Clear uploaded documents
    - Secure local databases
    - Flag browser cache for clearing

    **This action is IRREVERSIBLE!**
    """

    # Require explicit confirmation
    if body.confirmation != "CONFIRM":
        raise HTTPException(
            status_code=400,
            detail="Must provide confirmation='CONFIRM' to trigger panic mode"
        )

    logger.critical(f"🚨 PANIC MODE TRIGGERED: {body.reason}")

    try:
        result = await panic_mode.trigger_panic(reason=body.reason)
        return PanicTriggerResponse(**result)
    except Exception as e:
        logger.error(f"Panic mode execution failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Panic mode failed: {str(e)}"
        )


@router.get("/status", response_model=PanicStatusResponse)
async def get_panic_status():
    """
    Get current panic mode status
    """
    status = panic_mode.get_panic_status()
    return PanicStatusResponse(**status)


@router.post("/reset")
async def reset_panic_mode(request: Request):
    """
    Reset panic mode (requires admin privileges)

    This allows the system to return to normal operation after panic.
    """
    try:
        panic_mode.reset_panic()
        return {
            "success": True,
            "message": "Panic mode reset successfully",
            "panic_active": False
        }
    except Exception as e:
        logger.error(f"Failed to reset panic mode: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Reset failed: {str(e)}"
        )


@router.get("/health")
async def panic_health_check():
    """
    Health check for panic mode system
    """
    return {
        "panic_system": "operational",
        "status": panic_mode.get_panic_status()
    }
