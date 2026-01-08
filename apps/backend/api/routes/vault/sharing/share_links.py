"""
Vault Share Links Routes

Create, access, and revoke share links for vault files.
"""

import logging
from datetime import datetime, timedelta, UTC
from typing import Dict

from fastapi import APIRouter, HTTPException, Form, Depends, Request, status

from api.auth_middleware import get_current_user
from api.audit_logger import get_audit_logger
from api.rate_limiter import get_client_ip, rate_limiter
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode
from api.services.vault.core import get_vault_service
from api.utils import get_user_id

logger = logging.getLogger(__name__)
audit_logger = get_audit_logger()

router = APIRouter()


@router.post(
    "/files/{file_id}/share",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_201_CREATED,
    name="vault_create_share_link",
    summary="Create share link",
    description="Create a shareable link for a file with optional password protection and expiration (rate limited: 10/min)"
)
async def create_share_link_endpoint(
    request: Request,
    file_id: str,
    vault_type: str = Form("real"),
    password: str = Form(None),
    expires_at: str = Form(None),
    max_downloads: int = Form(None),
    permissions: str = Form("download"),
    one_time: bool = Form(False),
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Create a shareable link for a file

    Defaults:
    - TTL: 24 hours if expires_at not provided
    - One-time links: Set max_downloads=1 if one_time=True
    """
    # Rate limiting: 10 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:share:create:{get_user_id(current_user)}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=10, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded for vault.share.created"
            ).model_dump()
        )

    try:
        service = get_vault_service()
        user_id = get_user_id(current_user)

        # Apply default 24h TTL if not provided
        if not expires_at:
            now = datetime.now(UTC)
            default_expiry = now + timedelta(hours=24)
            expires_at = default_expiry.isoformat()

        # One-time link: force max_downloads=1
        if one_time and max_downloads is None:
            max_downloads = 1

        result = service.create_share_link(
            user_id, vault_type, file_id, password,
            expires_at, max_downloads, permissions
        )

        # Audit logging after success
        audit_logger.log(
            user_id=user_id,
            action="vault.share.created",
            resource="vault",
            resource_id=file_id,
            details={
                "file_id": file_id,
                "share_id": result.get("id"),
                "expires_at": expires_at,
                "max_downloads": max_downloads,
                "one_time": one_time
            }
        )

        return SuccessResponse(
            data=result,
            message="Share link created successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create share link", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to create share link"
            ).model_dump()
        )


@router.get(
    "/files/{file_id}/shares",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_get_file_shares",
    summary="Get file share links",
    description="Get all share links for a file (rate limited: 60/min)"
)
async def get_file_shares_endpoint(
    request: Request,
    file_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """Get all share links for a file"""
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:share:list:{get_user_id(current_user)}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded for vault.share.list"
            ).model_dump()
        )

    try:
        service = get_vault_service()
        user_id = get_user_id(current_user)

        shares = service.get_file_shares(user_id, vault_type, file_id)
        shares_data = {"shares": shares}

        return SuccessResponse(
            data=shares_data,
            message=f"Retrieved {len(shares)} share link{'s' if len(shares) != 1 else ''}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get file shares", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve file shares"
            ).model_dump()
        )


@router.delete(
    "/shares/{share_id}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_revoke_share_link",
    summary="Revoke share link",
    description="Revoke a share link (rate limited: 30/min)"
)
async def revoke_share_link_endpoint(
    request: Request,
    share_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """Revoke a share link"""
    # Rate limiting: 30 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:share:revoke:{get_user_id(current_user)}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=30, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded for vault.share.revoked"
            ).model_dump()
        )

    try:
        service = get_vault_service()
        user_id = get_user_id(current_user)

        success = service.revoke_share_link(user_id, vault_type, share_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Share link not found"
                ).model_dump()
            )

        # Audit logging after success
        audit_logger.log(
            user_id=user_id,
            action="vault.share.revoked",
            resource="vault",
            resource_id=share_id,
            details={"share_id": share_id}
        )

        return SuccessResponse(
            data={"success": True},
            message="Share link revoked"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to revoke share link", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to revoke share link"
            ).model_dump()
        )


@router.get(
    "/share/{share_token}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_access_share_link",
    summary="Access shared file",
    description="Access a shared file via share token - PUBLIC endpoint (rate limited: 5/min per IP, 50/day per IP)"
)
async def access_share_link_endpoint(
    request: Request,
    share_token: str,
    password: str = None
) -> SuccessResponse[Dict]:
    """
    Access a shared file via share token - PUBLIC endpoint

    Enforces per-token IP throttles:
    - 5 downloads per minute per IP
    - 50 downloads per day per IP
    """
    # Per-token IP throttles
    ip = get_client_ip(request)
    key_min = f"vault:share.download.min:{share_token[:8]}:{ip}"
    key_day = f"vault:share.download.day:{share_token[:8]}:{ip}"

    if not rate_limiter.check_rate_limit(key_min, max_requests=5, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "rate_limited",
                "message": "Too many downloads for this link from your IP (1 min)",
                "retry_after": 60
            }
        )

    if not rate_limiter.check_rate_limit(key_day, max_requests=50, window_seconds=86400):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "rate_limited",
                "message": "Too many downloads for this link from your IP (24h)",
                "retry_after": 3600
            }
        )

    try:
        service = get_vault_service()

        # Get share details
        share_info = service.get_share_link(share_token)

        # Verify password if required
        if share_info["requires_password"]:
            if not password:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"code": "password_required", "message": "Password required"}
                )
            if not service.verify_share_password(share_token, password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"code": "password_incorrect", "message": "Incorrect password"}
                )

        return SuccessResponse(
            data=share_info,
            message="Share link accessed successfully"
        )

    except ValueError as e:
        error_msg = str(e).lower()

        if "expired" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail={"code": "expired", "message": "Share link has expired"}
            )
        elif "download limit" in error_msg or "max" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail={"code": "max_downloads_reached", "message": "Download limit reached"}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "invalid_token", "message": "Invalid or revoked share token"}
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to access share link (token: {share_token[:6]}...)", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to access share link"
            ).model_dump()
        )
