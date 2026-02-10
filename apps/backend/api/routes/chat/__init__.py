"""
Chat routes package - Aggregates all chat sub-routers
"""

__all__ = ["router", "public_router"]

from fastapi import APIRouter, Depends
from api.auth_middleware import get_current_user

from . import sessions, messages, files
from .models import router as models_router

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

# Models router is public
public_router.include_router(models_router)
