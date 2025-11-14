"""
Team routes package - Aggregates all team sub-routers
"""

from fastapi import APIRouter, Depends
from auth_middleware import get_current_user

from . import core, members, roles, invitations, permissions

router = APIRouter(
    prefix="/api/v1/teams",
    tags=["teams"],
    dependencies=[Depends(get_current_user)]
)

# Include all sub-routers
router.include_router(core.router)
router.include_router(members.router)
router.include_router(roles.router)
router.include_router(invitations.router)
router.include_router(permissions.router)
