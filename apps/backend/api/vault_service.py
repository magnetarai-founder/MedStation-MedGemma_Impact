#!/usr/bin/env python3
"""
Vault Service - DEPRECATED FACADE

⚠️  DEPRECATION NOTICE ⚠️

This module is deprecated and will be removed in v2.0.

Please update your imports:

  OLD (deprecated):
    from vault_service import router
    from vault_service import create_vault_document

  NEW (preferred):
    from api.vault import routes
    # Use routes.router for the APIRouter

    from api.services.vault import get_vault_service
    # Use get_vault_service() for business logic

This facade maintains backwards compatibility by re-exporting the router
and key functions with deprecation warnings.

Migrated as part of R1 Vault Service Split refactoring.

STATUS: All internal callers migrated (Dec 23, 2025)
- service_container.py → api.services.vault.core
- monitoring_routes.py → api.services.vault.core
This facade can be removed once external integrations are verified.
"""

import functools
import warnings
import logging
from typing import Optional, List, Dict, Any, Callable, TypeVar

F = TypeVar('F', bound=Callable[..., Any])

logger = logging.getLogger(__name__)

# ===== Router Re-export =====

# Import the real router from api.routes.vault (via api.vault.routes shim)
try:
    from api.routes import vault as _vault_routes
except ImportError:
    from routes import vault as _vault_routes

router = _vault_routes.router

# Router is the same object; no deprecation warning needed for router itself
# since it's the actual implementation, not a wrapper

# ===== Deprecation Decorator =====

def deprecated(new_path: str) -> Callable[[F], F]:
    """
    Decorator to mark functions as deprecated with migration guidance.

    Args:
        new_path: The new import path to use

    Returns:
        Decorated function that emits DeprecationWarning
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            warnings.warn(
                f"{func.__name__} is deprecated. Import from {new_path} instead.",
                DeprecationWarning,
                stacklevel=2
            )
            return func(*args, **kwargs)
        return wrapper  # type: ignore[return-value]
    return decorator


# ===== Service Function Wrappers =====

# These wrappers provide backwards compatibility for code that imports
# functions directly from vault_service. They forward to the actual
# implementation in services.vault.core

@deprecated("api.services.vault.core")
def get_vault_service() -> Any:
    """Get vault service instance - DEPRECATED"""
    from api.services.vault.core import get_vault_service as _get_vault_service
    return _get_vault_service()


@deprecated("api.services.vault.core.VaultService.store_document")
def create_vault_document(user_id: str, document: Dict[str, Any], team_id: Optional[str] = None) -> Dict[str, Any]:
    """Store vault document - DEPRECATED"""
    from api.services.vault.core import get_vault_service as _get_vault_service
    service = _get_vault_service()
    return service.store_document(
        user_id=user_id,
        doc_id=document.get('id'),
        vault_type=document.get('vault_type'),
        encrypted_blob=document.get('encrypted_blob'),
        encrypted_metadata=document.get('encrypted_metadata'),
        team_id=team_id
    )


@deprecated("api.services.vault.core.VaultService.get_document")
def get_document(user_id: str, doc_id: str, vault_type: str, team_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get vault document - DEPRECATED"""
    from api.services.vault.core import get_vault_service as _get_vault_service
    service = _get_vault_service()
    return service.get_document(user_id=user_id, doc_id=doc_id, vault_type=vault_type, team_id=team_id)


@deprecated("api.services.vault.core.VaultService.list_documents")
def list_documents(user_id: str, vault_type: str, team_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List vault documents - DEPRECATED"""
    from api.services.vault.core import get_vault_service as _get_vault_service
    service = _get_vault_service()
    return service.list_documents(user_id=user_id, vault_type=vault_type, team_id=team_id)


@deprecated("api.services.vault.core.VaultService.update_document")
def update_document(user_id: str, doc_id: str, vault_type: str,
                   encrypted_blob: str, encrypted_metadata: str, team_id: Optional[str] = None) -> Dict[str, Any]:
    """Update vault document - DEPRECATED"""
    from api.services.vault.core import get_vault_service as _get_vault_service
    service = _get_vault_service()
    return service.update_document(
        user_id=user_id,
        doc_id=doc_id,
        vault_type=vault_type,
        encrypted_blob=encrypted_blob,
        encrypted_metadata=encrypted_metadata,
        team_id=team_id
    )


@deprecated("api.services.vault.core.VaultService.delete_document")
def delete_document(user_id: str, doc_id: str, vault_type: str, team_id: Optional[str] = None) -> bool:
    """Delete vault document - DEPRECATED"""
    from api.services.vault.core import get_vault_service as _get_vault_service
    service = _get_vault_service()
    return service.delete_document(user_id=user_id, doc_id=doc_id, vault_type=vault_type, team_id=team_id)


@deprecated("api.services.vault.core.VaultService.upload_file")
def upload_file(user_id: str, filename: str, file_data: bytes, vault_type: str,
               mime_type: str, folder_path: str = "/", team_id: Optional[str] = None) -> Dict[str, Any]:
    """Upload file to vault - DEPRECATED"""
    from api.services.vault.core import get_vault_service as _get_vault_service
    service = _get_vault_service()
    return service.upload_file(
        user_id=user_id,
        filename=filename,
        file_data=file_data,
        vault_type=vault_type,
        mime_type=mime_type,
        folder_path=folder_path,
        team_id=team_id
    )


@deprecated("api.services.vault.core.VaultService.list_files")
def list_files(user_id: str, vault_type: str, folder_path: Optional[str] = None, team_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List vault files - DEPRECATED"""
    from api.services.vault.core import get_vault_service as _get_vault_service
    service = _get_vault_service()
    return service.list_files(user_id=user_id, vault_type=vault_type, folder_path=folder_path, team_id=team_id)


@deprecated("api.services.vault.core.VaultService.delete_file")
def delete_file(user_id: str, file_id: str, vault_type: str, team_id: Optional[str] = None) -> bool:
    """Delete vault file - DEPRECATED"""
    from api.services.vault.core import get_vault_service as _get_vault_service
    service = _get_vault_service()
    return service.delete_file(user_id=user_id, file_id=file_id, vault_type=vault_type, team_id=team_id)


@deprecated("api.services.vault.core.VaultService.create_folder")
def create_folder(user_id: str, vault_type: str, folder_name: str,
                 parent_path: str = "/", team_id: Optional[str] = None) -> Dict[str, Any]:
    """Create vault folder - DEPRECATED"""
    from api.services.vault.core import get_vault_service as _get_vault_service
    service = _get_vault_service()
    return service.create_folder(
        user_id=user_id,
        vault_type=vault_type,
        folder_name=folder_name,
        parent_path=parent_path,
        team_id=team_id
    )


@deprecated("api.services.vault.core.VaultService.list_folders")
def list_folders(user_id: str, vault_type: str, parent_path: Optional[str] = None, team_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List vault folders - DEPRECATED"""
    from api.services.vault.core import get_vault_service as _get_vault_service
    service = _get_vault_service()
    return service.list_folders(user_id=user_id, vault_type=vault_type, parent_path=parent_path, team_id=team_id)


@deprecated("api.services.vault.core.VaultService.get_vault_stats")
def get_vault_stats(user_id: str, vault_type: str, team_id: Optional[str] = None) -> Dict[str, Any]:
    """Get vault statistics - DEPRECATED"""
    from api.services.vault.core import get_vault_service as _get_vault_service
    service = _get_vault_service()
    return service.get_vault_stats(user_id=user_id, vault_type=vault_type, team_id=team_id)


# ===== Legacy Model Re-exports =====

# Re-export schemas for backwards compatibility
from api.services.vault.schemas import (
    VaultDocument,
    VaultDocumentCreate,
    VaultDocumentUpdate,
    VaultListResponse,
    VaultFile,
    VaultFolder,
)

# Note: Models don't need deprecation warnings as they're just type definitions

logger.info("vault_service.py loaded as compatibility facade (DEPRECATED)")
