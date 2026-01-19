"""
Vault routes package - Aggregates all vault sub-routers
"""

__all__ = ["router"]

from fastapi import APIRouter, Depends
from api.auth_middleware import get_current_user

from . import documents, files, folders, sharing, ws, automation, semantic_search

router = APIRouter(
    prefix="/api/v1/vault",
    tags=["Vault"],
    dependencies=[Depends(get_current_user)]
)

# Include all sub-routers
router.include_router(documents.router)
router.include_router(files.router)
router.include_router(folders.router)
router.include_router(sharing.router)
router.include_router(ws.router)
router.include_router(automation.router)
router.include_router(semantic_search.router)
