"""
Chat routes package - Aggregates all chat sub-routers
"""

__all__ = ["router", "public_router"]

from fastapi import APIRouter, Depends
try:
    from api.auth_middleware import get_current_user
except ImportError:
    from api.auth_middleware import get_current_user

from . import sessions, messages, files, models, model_tags

# Authenticated router
router = APIRouter(
    prefix="/api/v1/chat",
    tags=["chat"],
    dependencies=[Depends(get_current_user)]
)

# Public router (health checks, model list)
public_router = APIRouter(
    prefix="/api/v1/chat",
    tags=["chat-public"]
)

# Include sub-routers
router.include_router(sessions.router)
router.include_router(messages.router)
router.include_router(files.router)
router.include_router(model_tags.router)  # Model tags management

# Models router is public (function-level auth on protected endpoints)
# router.include_router(models.router)  # REMOVED - was causing 403 shadowing
public_router.include_router(models.router)
