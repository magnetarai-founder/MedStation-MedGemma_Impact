"""
Chat routes package - Aggregates all chat sub-routers
"""

from fastapi import APIRouter, Depends
from api.auth_middleware import get_current_user

from . import sessions, messages, files, models

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

# Models can be both auth'd and public - include both
router.include_router(models.router)
public_router.include_router(models.router)
