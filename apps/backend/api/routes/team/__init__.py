"""
Team Routes Package

This package contains modularized team-related endpoints:
- teams.py: Team CRUD operations (create, get, list)
- members.py: Member management (add, remove, roles, promotions)
- invitations.py: Invitation management (invite codes, join flows)
- permissions.py: Permission management (workflows, queues, vault, god rights)
- chat.py: Team chat endpoints (placeholder)
- workspaces.py: Team workspaces endpoints (placeholder)
- analytics.py: Team analytics endpoints (placeholder)
"""

from fastapi import APIRouter, Depends

from api.auth_middleware import get_current_user

# Create aggregated router with prefix
router = APIRouter(
    prefix="/api/v1/teams",
    tags=["teams"],
    dependencies=[Depends(get_current_user)]
)

# Import and include per-area routers
from . import teams, members, invitations, permissions, chat, workspaces, analytics

router.include_router(teams.router)
router.include_router(members.router)
router.include_router(invitations.router)
router.include_router(permissions.router)
router.include_router(chat.router)
router.include_router(workspaces.router)
router.include_router(analytics.router)

__all__ = ["router"]
