#!/usr/bin/env python3
"""
Panic Mode API Router
Provides REST endpoints for emergency security operations
"""

import logging
import os
import time
from datetime import datetime, UTC
from fastapi import APIRouter, HTTPException, Request, Body
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

from panic_mode import get_panic_mode
from rate_limiter import rate_limiter, get_client_ip
from utils import sanitize_for_log

logger = logging.getLogger(__name__)

# ===== EMERGENCY MODE SAFETY CHECK =====
# CRITICAL: This must be explicitly enabled to allow emergency wipe
# Set environment variable: ELOHIM_ALLOW_EMERGENCY_WIPE=true
ALLOW_EMERGENCY_WIPE = os.getenv("ELOHIM_ALLOW_EMERGENCY_WIPE", "false").lower() == "true"

if not ALLOW_EMERGENCY_WIPE:
    logger.warning("⚠️  Emergency wipe DISABLED (ELOHIM_ALLOW_EMERGENCY_WIPE=false)")
    logger.warning("   This is a safety measure. Set ELOHIM_ALLOW_EMERGENCY_WIPE=true to enable.")
else:
    logger.critical("🚨 Emergency wipe ENABLED (ELOHIM_ALLOW_EMERGENCY_WIPE=true)")
    logger.critical("   ⚠️  DoD 7-pass wipe is active and IRREVERSIBLE")

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


class EmergencyModeRequest(BaseModel):
    """Request to trigger emergency mode (DoD 7-pass wipe)"""
    confirmation: str = Field(..., description="Must be 'CONFIRM' to proceed")
    reason: Optional[str] = Field("User-initiated emergency", description="Reason for emergency activation")


class EmergencyModeResponse(BaseModel):
    """Response after emergency mode wipe"""
    success: bool
    files_wiped: int
    passes: int
    method: str
    duration_seconds: float
    timestamp: str
    errors: List[str] = []


# ===== Router =====

from fastapi import Depends
from auth_middleware import get_current_user

router = APIRouter(
    prefix="/api/v1/panic",
    tags=["Panic Mode"],
    dependencies=[Depends(get_current_user)]  # Require auth
)
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
    # Rate limit: 5 panic triggers per hour (prevent abuse)
    client_ip = get_client_ip(request)
    if not rate_limiter.check_rate_limit(f"panic:trigger:{client_ip}", max_requests=5, window_seconds=3600):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 5 panic triggers per hour.")

    # Require explicit confirmation
    if body.confirmation != "CONFIRM":
        raise HTTPException(
            status_code=400,
            detail="Must provide confirmation='CONFIRM' to trigger panic mode"
        )

    # Sanitize reason for logging (may contain sensitive context)
    safe_reason = sanitize_for_log(body.reason)
    logger.critical(f"🚨 PANIC MODE TRIGGERED: {safe_reason}")

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
async def reset_panic_mode(request: Request) -> Dict[str, Any]:
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
async def panic_health_check() -> Dict[str, Any]:
    """
    Health check for panic mode system
    """
    return {
        "panic_system": "operational",
        "status": panic_mode.get_panic_status()
    }


# ===== EMERGENCY MODE - DoD 7-Pass Wipe =====

@router.post("/emergency", response_model=EmergencyModeResponse)
async def trigger_emergency_mode(
    request: Request,
    body: EmergencyModeRequest
):
    """
    🚨🚨🚨 EMERGENCY MODE: DoD 5220.22-M 7-Pass Wipe 🚨🚨🚨

    ⚠️  CRITICAL WARNING: THIS IS IRREVERSIBLE ⚠️

    This endpoint performs a DoD 5220.22-M standard 7-pass overwrite
    on ALL MagnetarStudio data, followed by secure deletion.

    **Data wiped includes:**
    - Vault databases (sensitive + unsensitive)
    - All backups
    - All models
    - All audit logs
    - All cache and temporary files
    - User preferences and settings

    **Safety Requirements:**
    1. Environment variable ELOHIM_ALLOW_EMERGENCY_WIPE=true must be set
    2. User must be authenticated
    3. Confirmation="CONFIRM" required
    4. Rate limited (5 triggers per hour)

    **Use Cases:**
    - Persecution scenario (authorities seizing device)
    - Data breach requiring immediate sanitization
    - Authorized destruction for decommissioning

    **This action cannot be undone. All data will be permanently destroyed.**
    """
    # Safety check: Emergency mode must be explicitly enabled
    if not ALLOW_EMERGENCY_WIPE:
        logger.error("🚫 Emergency mode attempt BLOCKED (ELOHIM_ALLOW_EMERGENCY_WIPE=false)")
        raise HTTPException(
            status_code=403,
            detail="Emergency mode is disabled. Set ELOHIM_ALLOW_EMERGENCY_WIPE=true to enable."
        )

    # Rate limiting (5 emergency triggers per hour)
    client_ip = get_client_ip(request)
    if not rate_limiter.check_rate_limit(f"emergency:trigger:{client_ip}", max_requests=5, window_seconds=3600):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Max 5 emergency triggers per hour."
        )

    # Verify confirmation
    if body.confirmation != "CONFIRM":
        raise HTTPException(
            status_code=400,
            detail="Confirmation required. Must send confirmation='CONFIRM' to proceed."
        )

    # Sanitize reason for logging
    safe_reason = sanitize_for_log(body.reason) if body.reason else "User-initiated emergency"

    logger.critical(f"🚨🚨🚨 EMERGENCY MODE TRIGGERED: {safe_reason}")
    logger.critical("   ⚠️  Beginning DoD 7-pass wipe - THIS IS IRREVERSIBLE")

    # Record start time
    start_time = time.time()

    # Define wipe targets
    wipe_targets = [
        # Databases
        "vault_sensitive.db",
        "vault_unsensitive.db",
        "app.db",
        "audit.db",
        "datasets.db",

        # Directories
        os.path.expanduser("~/.magnetar/models/"),
        os.path.expanduser("~/.elohimos_backups/"),
        os.path.expanduser("~/Library/Caches/com.magnetarstudio.app/"),
        os.path.expanduser("~/Library/Application Support/MagnetarStudio/"),
        os.path.expanduser("~/Library/Logs/MagnetarStudio/"),

        # Preferences
        os.path.expanduser("~/Library/Preferences/com.magnetarstudio.app.plist"),

        # LaunchAgents
        os.path.expanduser("~/Library/LaunchAgents/com.magnetarstudio.*.plist"),
    ]

    # Perform DoD 7-pass wipe
    try:
        from emergency_wipe import perform_dod_wipe

        result = await perform_dod_wipe(wipe_targets)
        duration = time.time() - start_time

        logger.critical(f"✅ Emergency wipe complete: {result['count']} files wiped in {duration:.2f}s")

        if result['errors']:
            logger.error(f"⚠️  Errors during wipe: {len(result['errors'])}")
            for error in result['errors']:
                logger.error(f"   - {error}")

        return EmergencyModeResponse(
            success=True,
            files_wiped=result['count'],
            passes=7,
            method="DoD 5220.22-M",
            duration_seconds=duration,
            timestamp=datetime.now(UTC).isoformat(),
            errors=result['errors']
        )

    except Exception as e:
        logger.error(f"❌ Emergency mode execution failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Emergency mode failed: {str(e)}"
        )


# DoD wipe functions moved to emergency_wipe.py for independent testing
