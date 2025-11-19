"""
Vault Files Management Routes

Handles file CRUD operations:
- List files (simple and paginated)
- Delete files
- Rename files
- Move files to different folders
"""

import logging
import sqlite3
from typing import Dict, List
from fastapi import APIRouter, HTTPException, Depends

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from auth_middleware import get_current_user
from api.services.vault.core import get_vault_service
from api.services.vault.schemas import VaultFile

logger = logging.getLogger(__name__)

# Import WebSocket connection manager
try:
    from api.websocket_manager import manager
except ImportError:
    manager = None
    logger.warning("WebSocket manager not available for vault notifications")

router = APIRouter()


@router.get("/files", response_model=List[VaultFile])
async def list_vault_files(vault_type: str = "real", folder_path: str = None, current_user: Dict = Depends(get_current_user)):
    """List all uploaded vault files, optionally filtered by folder"""
    user_id = current_user["user_id"]

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    service = get_vault_service()
    return service.list_files(user_id, vault_type, folder_path)


@router.get("/files-paginated")
async def get_vault_files_paginated(
    vault_type: str = "real",
    folder_path: str = "/",
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "name",
    current_user: Dict = Depends(get_current_user)
):
    """Get vault files with pagination"""
    user_id = current_user["user_id"]
    service = get_vault_service()

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    if page < 1:
        raise HTTPException(status_code=400, detail="page must be >= 1")

    if page_size < 1 or page_size > 100:
        raise HTTPException(status_code=400, detail="page_size must be between 1 and 100")

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

        # Get paginated files
        order_clause = {
            'name': 'filename ASC',
            'date': 'created_at DESC',
            'size': 'file_size DESC'
        }.get(sort_by, 'filename ASC')

        cursor.execute(f"""
            SELECT * FROM vault_files
            WHERE user_id = ? AND vault_type = ? AND folder_path = ? AND is_deleted = 0
            ORDER BY {order_clause}
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

        return {
            "files": files,
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    finally:
        conn.close()


@router.delete("/files/{file_id}")
async def delete_vault_file(file_id: str, vault_type: str = "real", current_user: Dict = Depends(get_current_user)):
    """Delete a file"""
    user_id = current_user["user_id"]

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    service = get_vault_service()
    success = service.delete_file(user_id, vault_type, file_id)

    if not success:
        raise HTTPException(status_code=404, detail="File not found")

    # Broadcast file deletion event
    if manager:
        await manager.broadcast_file_event(
            event_type="file_deleted",
            file_data={"id": file_id},
            vault_type=vault_type,
            user_id=user_id
        )

    return {"success": True, "message": "File deleted"}


@router.put("/files/{file_id}/rename")
async def rename_vault_file(file_id: str, new_filename: str, vault_type: str = "real", current_user: Dict = Depends(get_current_user)):
    """Rename a file"""
    user_id = current_user["user_id"]

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    if not new_filename or not new_filename.strip():
        raise HTTPException(status_code=400, detail="new_filename is required")

    service = get_vault_service()
    success = service.rename_file(user_id, vault_type, file_id, new_filename.strip())

    if not success:
        raise HTTPException(status_code=404, detail="File not found")

    # Broadcast file rename event
    if manager:
        await manager.broadcast_file_event(
            event_type="file_renamed",
            file_data={"id": file_id, "new_filename": new_filename.strip()},
            vault_type=vault_type,
            user_id=user_id
        )

    return {"success": True, "message": "File renamed", "new_filename": new_filename.strip()}


@router.put("/files/{file_id}/move")
async def move_vault_file(file_id: str, new_folder_path: str, vault_type: str = "real", current_user: Dict = Depends(get_current_user)):
    """Move a file to a different folder"""
    user_id = current_user["user_id"]

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    service = get_vault_service()
    success = service.move_file(user_id, vault_type, file_id, new_folder_path)

    if not success:
        raise HTTPException(status_code=404, detail="File not found")

    # Broadcast file move event
    if manager:
        await manager.broadcast_file_event(
            event_type="file_moved",
            file_data={"id": file_id, "new_folder_path": new_folder_path},
            vault_type=vault_type,
            user_id=user_id
        )

    return {"success": True, "message": "File moved", "new_folder_path": new_folder_path}
