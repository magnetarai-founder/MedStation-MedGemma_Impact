"""
Vault Files Routes Package

This package contains modularized file-related endpoints:
- upload.py: File upload endpoints (single and chunked uploads)
- download.py: File download endpoints (download, thumbnail)
- management.py: File CRUD operations (list, delete, rename, move)
- search.py: File search and analytics endpoints
- metadata.py: File metadata, tags, favorites, versioning, comments
"""

from fastapi import APIRouter, Depends

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from api.auth_middleware import get_current_user

# Create aggregated router with no prefix
# (prefix is already applied at vault level: /api/v1/vault)
router = APIRouter(
    tags=["Vault Files"],
    dependencies=[Depends(get_current_user)]
)

# Import and include per-area routers
from . import upload, download, management, search, metadata

router.include_router(upload.router)
router.include_router(download.router)
router.include_router(management.router)
router.include_router(search.router)
router.include_router(metadata.router)

__all__ = ["router"]
