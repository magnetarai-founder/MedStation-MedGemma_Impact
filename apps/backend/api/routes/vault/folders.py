"""
Vault Folders Routes

Provides folder operations for vault (create, list, rename, delete, color management).

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Form, Depends, status
from pydantic import BaseModel

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from api.auth_middleware import get_current_user
try:
    from api.utils import get_user_id
except ImportError:
    from api.utils import get_user_id
from api.services.vault.core import get_vault_service
from api.services.vault.schemas import VaultFolder
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/vault", tags=["vault-folders"])


@router.post(
    "/folders",
    response_model=SuccessResponse[VaultFolder],
    status_code=status.HTTP_201_CREATED,
    name="create_vault_folder",
    summary="Create folder",
    description="Create a new folder in the vault (real or decoy)"
)
async def create_vault_folder(
    folder_name: str = Form(...),
    vault_type: str = Form(default="real"),
    parent_path: str = Form(default="/"),
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[VaultFolder]:
    """Create a new folder in the vault"""
    try:
        user_id = get_user_id(current_user)

        if vault_type not in ('real', 'decoy'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="vault_type must be 'real' or 'decoy'"
                ).model_dump()
            )

        service = get_vault_service()
        folder = service.create_folder(user_id, vault_type, folder_name, parent_path)

        return SuccessResponse(
            data=folder,
            message=f"Folder '{folder_name}' created successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to create folder '{folder_name}'", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to create folder"
            ).model_dump()
        )


@router.get(
    "/folders",
    response_model=SuccessResponse[List[VaultFolder]],
    status_code=status.HTTP_200_OK,
    name="list_vault_folders",
    summary="List folders",
    description="List folders in vault, optionally filtered by parent path"
)
async def list_vault_folders(
    vault_type: str = "real",
    parent_path: str = None,
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[List[VaultFolder]]:
    """List folders, optionally filtered by parent path"""
    try:
        user_id = get_user_id(current_user)

        if vault_type not in ('real', 'decoy'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="vault_type must be 'real' or 'decoy'"
                ).model_dump()
            )

        service = get_vault_service()
        folders = service.list_folders(user_id, vault_type, parent_path)

        return SuccessResponse(
            data=folders,
            message=f"Retrieved {len(folders)} folder(s)"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to list folders", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve folders"
            ).model_dump()
        )


class DeleteFolderResponse(BaseModel):
    success: bool
    folder_path: str


@router.delete(
    "/folders",
    response_model=SuccessResponse[DeleteFolderResponse],
    status_code=status.HTTP_200_OK,
    name="delete_vault_folder",
    summary="Delete folder",
    description="Delete a folder and all its contents from the vault"
)
async def delete_vault_folder(
    folder_path: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[DeleteFolderResponse]:
    """Delete a folder (and all its contents)"""
    try:
        user_id = get_user_id(current_user)

        if vault_type not in ('real', 'decoy'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="vault_type must be 'real' or 'decoy'"
                ).model_dump()
            )

        service = get_vault_service()
        success = service.delete_folder(user_id, vault_type, folder_path)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Folder not found"
                ).model_dump()
            )

        return SuccessResponse(
            data=DeleteFolderResponse(success=True, folder_path=folder_path),
            message=f"Folder '{folder_path}' deleted successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to delete folder '{folder_path}'", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to delete folder"
            ).model_dump()
        )


class RenameFolderResponse(BaseModel):
    success: bool
    old_path: str
    new_path: str


@router.put(
    "/folders/rename",
    response_model=SuccessResponse[RenameFolderResponse],
    status_code=status.HTTP_200_OK,
    name="rename_vault_folder",
    summary="Rename folder",
    description="Rename a vault folder"
)
async def rename_vault_folder(
    old_path: str,
    new_name: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[RenameFolderResponse]:
    """Rename a folder"""
    try:
        user_id = get_user_id(current_user)

        if vault_type not in ('real', 'decoy'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="vault_type must be 'real' or 'decoy'"
                ).model_dump()
            )

        if not new_name or not new_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="new_name is required"
                ).model_dump()
            )

        service = get_vault_service()
        success = service.rename_folder(user_id, vault_type, old_path, new_name.strip())

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Folder not found"
                ).model_dump()
            )

        # Calculate new path for response
        parent_path = old_path.rsplit('/', 1)[0] if old_path.count('/') > 0 else '/'
        new_path = f"{parent_path}/{new_name.strip()}" if parent_path != '/' else f"/{new_name.strip()}"

        return SuccessResponse(
            data=RenameFolderResponse(success=True, old_path=old_path, new_path=new_path),
            message=f"Folder renamed to '{new_name}' successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to rename folder '{old_path}'", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to rename folder"
            ).model_dump()
        )


class VaultHealthResponse(BaseModel):
    vault_service: str
    encryption: str
    storage: str
    file_uploads: str


@router.get(
    "/health",
    response_model=SuccessResponse[VaultHealthResponse],
    status_code=status.HTTP_200_OK,
    name="vault_health_check",
    summary="Vault health check",
    description="Get vault service health and configuration information"
)
async def vault_health() -> SuccessResponse[VaultHealthResponse]:
    """Health check for vault service"""
    try:
        health_data = VaultHealthResponse(
            vault_service="operational",
            encryption="server-side with Fernet (AES-128)",
            storage="SQLite + encrypted files on disk",
            file_uploads="supported"
        )

        return SuccessResponse(
            data=health_data,
            message="Vault service is operational"
        )

    except Exception as e:
        logger.error(f"Vault health check failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve vault health"
            ).model_dump()
        )


class FolderColorResponse(BaseModel):
    folder_id: str
    color: str


@router.post(
    "/folders/{folder_id}/color",
    response_model=SuccessResponse[FolderColorResponse],
    status_code=status.HTTP_200_OK,
    name="set_folder_color",
    summary="Set folder color",
    description="Set color for a vault folder"
)
async def set_folder_color_endpoint(
    folder_id: str,
    color: str = Form(...),
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[FolderColorResponse]:
    """Set color for a folder"""
    try:
        service = get_vault_service()
        user_id = get_user_id(current_user)

        result = service.set_folder_color(user_id, vault_type, folder_id, color)

        return SuccessResponse(
            data=FolderColorResponse(folder_id=folder_id, color=color),
            message=f"Folder color set to '{color}' successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to set folder color for '{folder_id}'", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to set folder color"
            ).model_dump()
        )


class FolderColorsResponse(BaseModel):
    folder_colors: Dict[str, str]


@router.get(
    "/folder-colors",
    response_model=SuccessResponse[FolderColorsResponse],
    status_code=status.HTTP_200_OK,
    name="get_folder_colors",
    summary="Get folder colors",
    description="Get all folder colors for the vault"
)
async def get_folder_colors_endpoint(
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[FolderColorsResponse]:
    """Get all folder colors"""
    try:
        service = get_vault_service()
        user_id = get_user_id(current_user)

        colors = service.get_folder_colors(user_id, vault_type)

        return SuccessResponse(
            data=FolderColorsResponse(folder_colors=colors),
            message=f"Retrieved {len(colors)} folder color(s)"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get folder colors", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve folder colors"
            ).model_dump()
        )
