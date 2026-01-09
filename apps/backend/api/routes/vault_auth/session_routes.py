"""
Vault Auth - Session Routes

Vault session status and locking endpoints.
"""

import logging
from typing import Dict

from fastapi import APIRouter, Depends, Query, status

from api.auth_middleware import get_current_user, User
from api.routes.schemas import SuccessResponse
from api.utils import get_user_id

from api.routes.vault_auth import helpers

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/session/status",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    summary="Check session status",
    description="Check if vault is unlocked in current session (sessions expire after 1 hour)"
)
async def get_session_status(
    vault_id: str = Query(..., description="Vault UUID"),
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """Check if vault is unlocked in current session"""
    user_id = get_user_id(current_user)
    session = helpers.get_session(user_id, vault_id)

    if session:
        return SuccessResponse(
            data={"unlocked": True, "session_id": session['session_id']},
            message="Vault is unlocked"
        )

    return SuccessResponse(
        data={"unlocked": False, "session_id": None},
        message="Vault is locked"
    )


@router.post(
    "/session/lock",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    summary="Lock vault",
    description="Lock vault and clear session (KEK removed from memory)"
)
async def lock_vault(
    vault_id: str = Query(..., description="Vault UUID"),
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """Lock vault (clear session)"""
    user_id = get_user_id(current_user)

    if helpers.delete_session(user_id, vault_id):
        logger.info("Vault locked", extra={"user_id": user_id, "vault_id": vault_id})

    return SuccessResponse(
        data={"success": True},
        message="Vault locked successfully"
    )
