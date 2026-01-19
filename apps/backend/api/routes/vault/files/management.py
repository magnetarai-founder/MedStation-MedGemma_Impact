"""
Vault Files Management Routes

Handles file CRUD operations (list, delete, rename, move).

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
import sqlite3
from typing import Dict, List, Any
from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel

from api.auth_middleware import get_current_user
from api.utils import get_user_id
from api.services.vault.core import get_vault_service
from api.services.vault.schemas import VaultFile
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

logger = logging.getLogger(__name__)

# Import WebSocket connection manager
try:
    from api.websocket_manager import manager
except ImportError:
    manager = None
    logger.warning("WebSocket manager not available for vault notifications")

router = APIRouter(prefix="/api/v1/vault", tags=["vault-files"])


class PaginatedFilesResponse(BaseModel):
    """Paginated files response"""
    files: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class FileOperationResponse(BaseModel):
    """Response for file operations"""
    success: bool
    file_id: str
    message: str


class RenameFileResponse(BaseModel):
    """Response for file rename"""
    success: bool
    file_id: str
    new_filename: str
    message: str


class MoveFileResponse(BaseModel):
    """Response for file move"""
    success: bool
    file_id: str
    new_folder_path: str
    message: str


@router.get(
    "/files",
    response_model=SuccessResponse[List[VaultFile]],
    status_code=status.HTTP_200_OK,
    name="vault_list_files",
    summary="List files",
    description="List vault files, optionally filtered by folder"
)
async def list_vault_files(
    vault_type: str = "real",
    folder_path: str = None,
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[List[VaultFile]]:
    """
    List all uploaded vault files, optionally filtered by folder

    Args:
        vault_type: 'real' or 'decoy' (default: 'real')
        folder_path: Optional folder path to filter by

    Returns:
        List of vault files
    """
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
        files = service.list_files(user_id, vault_type, folder_path)

        return SuccessResponse(
            data=files,
            message=f"Retrieved {len(files)} file{'s' if len(files) != 1 else ''}"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to list vault files", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to list files"
            ).model_dump()
        )


@router.get(
    "/files-paginated",
    response_model=SuccessResponse[PaginatedFilesResponse],
    status_code=status.HTTP_200_OK,
    name="vault_list_files_paginated",
    summary="List files (paginated)",
    description="Get vault files with pagination and sorting"
)
async def get_vault_files_paginated(
    vault_type: str = "real",
    folder_path: str = "/",
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "name",
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[PaginatedFilesResponse]:
    """
    Get vault files with pagination

    Args:
        vault_type: 'real' or 'decoy' (default: 'real')
        folder_path: Folder path to list (default: '/')
        page: Page number (default: 1)
        page_size: Items per page (1-100, default: 50)
        sort_by: Sort field - 'name', 'date', or 'size' (default: 'name')

    Returns:
        Paginated list of files with metadata
    """
    try:
        user_id = get_user_id(current_user)
        service = get_vault_service()

        if vault_type not in ('real', 'decoy'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="vault_type must be 'real' or 'decoy'"
                ).model_dump()
            )

        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="page must be >= 1"
                ).model_dump()
            )

        if page_size < 1 or page_size > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="page_size must be between 1 and 100"
                ).model_dump()
            )

        # Calculate offset
        offset = (page - 1) * page_size

        conn = sqlite3.connect(str(service.db_path))
        cursor = conn.cursor()

        try:
            # Get total count
            cursor.execute("""
                SELECT COUNT(*) FROM vault_files
                WHERE user_id = ? AND vault_type = ? AND folder_path = ? AND is_deleted = 0
            """, (user_id, vault_type, folder_path))
            total_count = cursor.fetchone()[0]

            # SECURITY: Use strict allowlist for ORDER BY to prevent SQL injection
            ALLOWED_SORT_FIELDS = {
                'name': ('filename', 'ASC'),
                'date': ('created_at', 'DESC'),
                'size': ('file_size', 'DESC'),
            }

            if sort_by not in ALLOWED_SORT_FIELDS:
                sort_by = 'name'  # Safe default

            sort_column, sort_direction = ALLOWED_SORT_FIELDS[sort_by]

            # Use parameterized query with safe, validated column names
            cursor.execute(f"""
                SELECT * FROM vault_files
                WHERE user_id = ? AND vault_type = ? AND folder_path = ? AND is_deleted = 0
                ORDER BY {sort_column} {sort_direction}
                LIMIT ? OFFSET ?
            """, (user_id, vault_type, folder_path, page_size, offset))

            files = []
            for row in cursor.fetchall():
                files.append({
                    "id": row[0],
                    "user_id": row[1],
                    "vault_type": row[2],
                    "filename": row[3],
                    "file_size": row[4],
                    "mime_type": row[5],
                    "encrypted_path": row[6],
                    "folder_path": row[7],
                    "created_at": row[8],
                    "updated_at": row[9]
                })

            total_pages = (total_count + page_size - 1) // page_size

            result = PaginatedFilesResponse(
                files=files,
                total=total_count,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1
            )

            return SuccessResponse(
                data=result,
                message=f"Retrieved page {page}/{total_pages} ({len(files)} files)"
            )

        finally:
            conn.close()

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get paginated vault files", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve paginated files"
            ).model_dump()
        )


@router.delete(
    "/files/{file_id}",
    response_model=SuccessResponse[FileOperationResponse],
    status_code=status.HTTP_200_OK,
    name="vault_delete_file",
    summary="Delete file",
    description="Delete a file from the vault"
)
async def delete_vault_file(
    file_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[FileOperationResponse]:
    """
    Delete a file from the vault

    Args:
        file_id: File ID to delete
        vault_type: 'real' or 'decoy' (default: 'real')

    Returns:
        Success confirmation
    """
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
        success = service.delete_file(user_id, vault_type, file_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="File not found"
                ).model_dump()
            )

        # Broadcast file deletion event
        if manager:
            await manager.broadcast_file_event(
                event_type="file_deleted",
                file_data={"id": file_id},
                vault_type=vault_type,
                user_id=user_id
            )

        return SuccessResponse(
            data=FileOperationResponse(
                success=True,
                file_id=file_id,
                message="File deleted"
            ),
            message="File deleted successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to delete vault file {file_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to delete file"
            ).model_dump()
        )


@router.put(
    "/files/{file_id}/rename",
    response_model=SuccessResponse[RenameFileResponse],
    status_code=status.HTTP_200_OK,
    name="vault_rename_file",
    summary="Rename file",
    description="Rename a vault file"
)
async def rename_vault_file(
    file_id: str,
    new_filename: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[RenameFileResponse]:
    """
    Rename a vault file

    Args:
        file_id: File ID to rename
        new_filename: New filename
        vault_type: 'real' or 'decoy' (default: 'real')

    Returns:
        Success confirmation with new filename
    """
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

        if not new_filename or not new_filename.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="new_filename is required"
                ).model_dump()
            )

        service = get_vault_service()
        success = service.rename_file(user_id, vault_type, file_id, new_filename.strip())

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="File not found"
                ).model_dump()
            )

        # Broadcast file rename event
        if manager:
            await manager.broadcast_file_event(
                event_type="file_renamed",
                file_data={"id": file_id, "new_filename": new_filename.strip()},
                vault_type=vault_type,
                user_id=user_id
            )

        return SuccessResponse(
            data=RenameFileResponse(
                success=True,
                file_id=file_id,
                new_filename=new_filename.strip(),
                message="File renamed"
            ),
            message=f"File renamed to '{new_filename.strip()}'"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to rename vault file {file_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to rename file"
            ).model_dump()
        )


@router.put(
    "/files/{file_id}/move",
    response_model=SuccessResponse[MoveFileResponse],
    status_code=status.HTTP_200_OK,
    name="vault_move_file",
    summary="Move file",
    description="Move a file to a different folder"
)
async def move_vault_file(
    file_id: str,
    new_folder_path: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[MoveFileResponse]:
    """
    Move a file to a different folder

    Args:
        file_id: File ID to move
        new_folder_path: Destination folder path
        vault_type: 'real' or 'decoy' (default: 'real')

    Returns:
        Success confirmation with new folder path
    """
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
        success = service.move_file(user_id, vault_type, file_id, new_folder_path)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="File not found"
                ).model_dump()
            )

        # Broadcast file move event
        if manager:
            await manager.broadcast_file_event(
                event_type="file_moved",
                file_data={"id": file_id, "new_folder_path": new_folder_path},
                vault_type=vault_type,
                user_id=user_id
            )

        return SuccessResponse(
            data=MoveFileResponse(
                success=True,
                file_id=file_id,
                new_folder_path=new_folder_path,
                message="File moved"
            ),
            message=f"File moved to '{new_folder_path}'"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to move vault file {file_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to move file"
            ).model_dump()
        )
