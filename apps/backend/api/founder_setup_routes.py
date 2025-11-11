"""
Founder Setup Wizard API Routes

API endpoints for first-time founder password setup.

Endpoints:
- GET /api/v1/founder-setup/status - Check if setup is complete
- POST /api/v1/founder-setup/initialize - Initialize founder password (one-time only)
- POST /api/v1/founder-setup/verify - Verify founder password

Security:
- Setup can only be run once
- Strong password validation
- Audit logging of all operations
- Rate limiting on verify endpoint
"""

import logging
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel

try:
    from .founder_setup_wizard import get_founder_wizard
    from .audit_logger import audit_log_sync
except ImportError:
    from founder_setup_wizard import get_founder_wizard
    from audit_logger import audit_log_sync

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/founder-setup", tags=["founder-setup"])


# ===== Pydantic Models =====

class SetupStatusResponse(BaseModel):
    """Setup status response"""
    setup_completed: bool
    setup_timestamp: Optional[str] = None
    password_storage_type: Optional[str] = None
    is_macos: bool


class InitializeSetupRequest(BaseModel):
    """Initialize setup request"""
    password: str
    confirm_password: str


class InitializeSetupResponse(BaseModel):
    """Initialize setup response"""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    storage_type: Optional[str] = None


class VerifyPasswordRequest(BaseModel):
    """Verify password request"""
    password: str


class VerifyPasswordResponse(BaseModel):
    """Verify password response"""
    valid: bool


# ===== API Endpoints =====

@router.get("/status", response_model=SetupStatusResponse)
async def get_setup_status():
    """
    Get founder setup status

    Returns whether founder password has been initialized.
    Public endpoint - no authentication required.
    """
    try:
        wizard = get_founder_wizard()
        info = wizard.get_setup_info()

        return SetupStatusResponse(
            setup_completed=info["setup_completed"],
            setup_timestamp=info["setup_timestamp"],
            password_storage_type=info["password_storage_type"],
            is_macos=info["is_macos"]
        )

    except Exception as e:
        logger.error(f"Failed to get setup status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get setup status")


@router.post("/initialize", response_model=InitializeSetupResponse)
async def initialize_founder_setup(
    request: Request,
    body: InitializeSetupRequest
):
    """
    Initialize founder password (one-time only)

    This endpoint can only be called once. After setup is complete,
    all subsequent calls will be rejected.

    Security:
    - Strong password validation (12+ chars, mixed case, numbers, special chars)
    - Password confirmation required
    - Stored in macOS Keychain (or .env file fallback)
    - Audit logged

    Public endpoint - no authentication required (first-time setup)
    """
    try:
        wizard = get_founder_wizard()

        # Check if already setup
        if wizard.is_setup_complete():
            audit_log_sync(
                user_id="anonymous",
                action="founder_setup.rejected",
                resource="founder_password",
                resource_id="setup",
                details={"reason": "already_setup"}
            )

            raise HTTPException(
                status_code=403,
                detail="Founder password already setup. Cannot re-initialize."
            )

        # Validate password confirmation
        if body.password != body.confirm_password:
            return InitializeSetupResponse(
                success=False,
                error="Passwords do not match"
            )

        # Get client IP
        client_ip = request.client.host if request.client else None

        # Setup password
        result = wizard.setup_founder_password(
            password=body.password,
            user_id="setup_wizard",
            ip_address=client_ip
        )

        if result["success"]:
            return InitializeSetupResponse(
                success=True,
                message=result["message"],
                storage_type=result["storage_type"]
            )
        else:
            return InitializeSetupResponse(
                success=False,
                error=result["error"]
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to initialize founder setup: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialize setup")


@router.post("/verify", response_model=VerifyPasswordResponse)
async def verify_founder_password(
    request: Request,
    body: VerifyPasswordRequest
):
    """
    Verify founder password

    Used internally by authentication system to verify founder_rights login.

    Note: This endpoint should be rate-limited to prevent brute force attacks.
    """
    try:
        wizard = get_founder_wizard()

        # Check if setup is complete
        if not wizard.is_setup_complete():
            # Audit log
            audit_log_sync(
                user_id="anonymous",
                action="founder_setup.verify_failed",
                resource="founder_password",
                resource_id="verify",
                details={"reason": "setup_not_complete"}
            )

            raise HTTPException(
                status_code=400,
                detail="Founder password not setup yet"
            )

        # Verify password
        is_valid = wizard.verify_founder_password(body.password)

        # Audit log failed attempts
        if not is_valid:
            client_ip = request.client.host if request.client else None

            audit_log_sync(
                user_id="anonymous",
                action="founder_setup.verify_failed",
                resource="founder_password",
                resource_id="verify",
                details={
                    "reason": "invalid_password",
                    "ip_address": client_ip
                }
            )

        return VerifyPasswordResponse(valid=is_valid)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to verify founder password: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify password")
