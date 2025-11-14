"""
Vault Files Routes - File upload/download/list/delete operations
"""

import logging
import sqlite3
from pathlib import Path
from typing import Dict, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request, Depends
from fastapi.responses import FileResponse, Response
from cryptography.fernet import Fernet

from api.auth_middleware import get_current_user
from api.utils import sanitize_filename
from api.services.vault.core import get_vault_service
from api.services.vault.schemas import VaultFile
from api.rate_limiter import get_client_ip, rate_limiter
from api.audit_logger import get_audit_logger

logger = logging.getLogger(__name__)
audit_logger = get_audit_logger()

# Import WebSocket connection manager
try:
    from api.websocket_manager import manager
except ImportError:
    manager = None
    logger.warning("WebSocket manager not available for vault notifications")

router = APIRouter()


@router.post("/upload", response_model=VaultFile)
async def upload_vault_file(
    request: Request,
    file: UploadFile = File(...),
    vault_passphrase: str = Form(...),
    vault_type: str = Form(default="real"),
    folder_path: str = Form(default="/"),
    current_user: Dict = Depends(get_current_user)
):
    """
    Upload and encrypt file to vault

    Args:
        file: File to upload
        vault_passphrase: Vault passphrase for encryption
        vault_type: 'real' or 'decoy' (default: 'real')
        folder_path: Folder path to upload to (default: '/')

    Returns:
        VaultFile metadata
    """
    user_id = current_user["user_id"]

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    # Read file data
    file_data = await file.read()

    if not file_data:
        raise HTTPException(status_code=400, detail="Empty file")

    # Get MIME type
    mime_type = file.content_type or "application/octet-stream"

    # Upload and encrypt
    service = get_vault_service()
    try:
        # Sanitize filename to prevent path traversal (HIGH-01)
        safe_filename = sanitize_filename(file.filename or "untitled")
        vault_file = service.upload_file(
            user_id=user_id,
            file_data=file_data,
            filename=safe_filename,
            mime_type=mime_type,
            vault_type=vault_type,
            passphrase=vault_passphrase,
            folder_path=folder_path
        )

        # Broadcast file upload event to connected clients
        if manager:
            await manager.broadcast_file_event(
                event_type="file_uploaded",
                file_data=vault_file,
                vault_type=vault_type,
                user_id=user_id
            )

        return vault_file
    except Exception as e:
        logger.error(f"File upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/upload-chunk")
async def upload_chunk(
    request: Request,
    chunk: UploadFile = File(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    file_id: str = Form(...),
    filename: str = Form(...),
    vault_passphrase: str = Form(...),
    vault_type: str = Form(default="real"),
    folder_path: str = Form(default="/"),
    current_user: Dict = Depends(get_current_user)
):
    """
    Upload file in chunks for large files

    Chunks are stored temporarily and assembled when all chunks are received
    """
    import shutil

    user_id = current_user["user_id"]
    service = get_vault_service()

    # Create temp directory for chunks
    temp_dir = service.files_path / "temp_chunks" / file_id
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Save chunk
    chunk_path = temp_dir / f"chunk_{chunk_index}"
    chunk_data = await chunk.read()
    with open(chunk_path, 'wb') as f:
        f.write(chunk_data)

    # Check if all chunks received
    received_chunks = list(temp_dir.glob("chunk_*"))

    if len(received_chunks) == total_chunks:
        # Assemble complete file
        complete_file = b""
        for i in range(total_chunks):
            chunk_file = temp_dir / f"chunk_{i}"
            if not chunk_file.exists():
                raise HTTPException(status_code=400, detail=f"Missing chunk {i}")
            with open(chunk_file, 'rb') as f:
                complete_file += f.read()

        # Detect MIME type from filename
        import mimetypes
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            mime_type = "application/octet-stream"

        # Upload assembled file
        try:
            # Sanitize filename to prevent path traversal (HIGH-01)
            safe_filename = sanitize_filename(filename)
            vault_file = service.upload_file(
                user_id=user_id,
                file_data=complete_file,
                filename=safe_filename,
                mime_type=mime_type,
                vault_type=vault_type,
                passphrase=vault_passphrase,
                folder_path=folder_path
            )

            # Cleanup temp chunks
            shutil.rmtree(temp_dir)

            return {
                "status": "complete",
                "file": vault_file,
                "chunks_received": len(received_chunks),
                "total_chunks": total_chunks
            }
        except Exception as e:
            logger.error(f"Chunked upload assembly failed: {e}")
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    return {
        "status": "uploading",
        "chunks_received": len(received_chunks),
        "total_chunks": total_chunks
    }


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


@router.get("/files/{file_id}/thumbnail")
async def get_file_thumbnail(
    file_id: str,
    vault_type: str = "real",
    vault_passphrase: str = "",
    current_user: Dict = Depends(get_current_user)
):
    """Get thumbnail for image files"""
    user_id = current_user["user_id"]
    service = get_vault_service()

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    if not vault_passphrase:
        raise HTTPException(status_code=400, detail="vault_passphrase is required")

    # Get file metadata
    conn = sqlite3.connect(service.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM vault_files
        WHERE id = ? AND user_id = ? AND vault_type = ? AND is_deleted = 0
    """, (file_id, user_id, vault_type))

    file_row = cursor.fetchone()
    conn.close()

    if not file_row:
        raise HTTPException(status_code=404, detail="File not found")

    # Check if file is an image
    if not file_row['mime_type'].startswith('image/'):
        raise HTTPException(status_code=400, detail="File is not an image")

    # Read and decrypt file
    encrypted_path = file_row['encrypted_path']
    file_path = service.files_path / encrypted_path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File data not found")

    with open(file_path, 'rb') as f:
        encrypted_data = f.read()

    # Decrypt file
    encryption_key, _ = service._get_encryption_key(vault_passphrase)
    fernet = Fernet(encryption_key)

    try:
        decrypted_data = fernet.decrypt(encrypted_data)
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise HTTPException(status_code=400, detail="Decryption failed - invalid passphrase?")

    # Generate thumbnail
    thumbnail = service.generate_thumbnail(decrypted_data, max_size=(200, 200))

    if not thumbnail:
        raise HTTPException(status_code=500, detail="Thumbnail generation failed")

    return Response(content=thumbnail, media_type="image/jpeg")


@router.get("/files/{file_id}/download")
async def download_vault_file(
    request: Request,
    file_id: str,
    vault_type: str = "real",
    vault_passphrase: str = "",
    current_user: Dict = Depends(get_current_user)
):
    """Download and decrypt a vault file"""
    # Rate limiting: 120 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:file:download:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=120, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.file.downloaded")

    user_id = current_user["user_id"]

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    if not vault_passphrase:
        raise HTTPException(status_code=400, detail="vault_passphrase is required")

    service = get_vault_service()

    # Get file metadata
    conn = sqlite3.connect(service.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM vault_files
        WHERE id = ? AND user_id = ? AND vault_type = ? AND is_deleted = 0
    """, (file_id, user_id, vault_type))

    file_row = cursor.fetchone()
    conn.close()

    if not file_row:
        raise HTTPException(status_code=404, detail="File not found")

    # Read encrypted file from disk
    encrypted_file_path = Path(file_row['encrypted_path'])

    if not encrypted_file_path.exists():
        raise HTTPException(status_code=404, detail="Encrypted file not found on disk")

    try:
        with open(encrypted_file_path, 'rb') as f:
            encrypted_data = f.read()

        # Decrypt the file
        key, _ = service._get_encryption_key(vault_passphrase)
        fernet = Fernet(key)
        decrypted_data = fernet.decrypt(encrypted_data)

        # Write decrypted data to temporary file
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file_row['filename']}")
        temp_file.write(decrypted_data)
        temp_file.close()

        # Audit logging after successful download
        audit_logger.log(
            user_id=user_id,
            action="vault.file.downloaded",
            resource="vault",
            resource_id=file_id,
            details={"file_id": file_id, "vault_type": vault_type}
        )

        return FileResponse(
            path=temp_file.name,
            filename=file_row['filename'],
            media_type=file_row['mime_type'] or 'application/octet-stream',
            headers={"Content-Disposition": f"attachment; filename=\"{file_row['filename']}\""}
        )

    except Exception as e:
        logger.error(f"Failed to download file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to decrypt file: {str(e)}")


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


# ===== Tags Endpoints =====

@router.post("/files/{file_id}/tags")
async def add_file_tag(
    file_id: str,
    tag_name: str = Form(...),
    tag_color: str = Form("#3B82F6"),
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
):
    """Add a tag to a file"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.add_tag_to_file(user_id, vault_type, file_id, tag_name, tag_color)
        return result
    except Exception as e:
        logger.error(f"Failed to add tag: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_id}/tags/{tag_name}")
async def remove_file_tag(
    file_id: str,
    tag_name: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
):
    """Remove a tag from a file"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        success = service.remove_tag_from_file(user_id, vault_type, file_id, tag_name)
        if not success:
            raise HTTPException(status_code=404, detail="Tag not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove tag: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{file_id}/tags")
async def get_file_tags(
    file_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
):
    """Get all tags for a file"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        tags = service.get_file_tags(user_id, vault_type, file_id)
        return {"tags": tags}
    except Exception as e:
        logger.error(f"Failed to get tags: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Favorites Endpoints =====

@router.post("/files/{file_id}/favorite")
async def add_favorite_file(
    file_id: str,
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
):
    """Add file to favorites"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.add_favorite(user_id, vault_type, file_id)
        return result
    except Exception as e:
        logger.error(f"Failed to add favorite: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_id}/favorite")
async def remove_favorite_file(
    file_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
):
    """Remove file from favorites"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        success = service.remove_favorite(user_id, vault_type, file_id)
        if not success:
            raise HTTPException(status_code=404, detail="Favorite not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove favorite: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/favorites")
async def get_favorite_files(vault_type: str = "real", current_user: Dict = Depends(get_current_user)):
    """Get list of favorite file IDs"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        favorites = service.get_favorites(user_id, vault_type)
        return {"favorites": favorites}
    except Exception as e:
        logger.error(f"Failed to get favorites: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Recent Files Endpoints =====

@router.post("/files/{file_id}/log-access")
async def log_file_access_endpoint(
    file_id: str,
    access_type: str = Form("view"),
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
):
    """Log file access (for recent files tracking)"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        service.log_file_access(user_id, vault_type, file_id, access_type)
        return {"success": True}
    except Exception as e:
        logger.warning(f"Failed to log file access: {e}")
        return {"success": False}


@router.get("/recent-files")
async def get_recent_files_endpoint(
    vault_type: str = "real",
    limit: int = 10,
    current_user: Dict = Depends(get_current_user)
):
    """Get recently accessed files"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        recent = service.get_recent_files(user_id, vault_type, limit)
        return {"recent_files": recent}
    except Exception as e:
        logger.error(f"Failed to get recent files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Storage Statistics Endpoint =====

@router.get("/storage-stats")
async def get_storage_statistics(vault_type: str = "real", current_user: Dict = Depends(get_current_user)):
    """Get storage statistics and analytics"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        stats = service.get_storage_stats(user_id, vault_type)
        return stats
    except Exception as e:
        logger.error(f"Failed to get storage stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Secure Deletion Endpoint =====

@router.delete("/files/{file_id}/secure")
async def secure_delete_file_endpoint(
    file_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
):
    """Securely delete a file (overwrites with random data before deletion)"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        success = service.secure_delete_file(user_id, vault_type, file_id)
        if not success:
            raise HTTPException(status_code=404, detail="File not found")
        return {"success": True, "message": "File securely deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to securely delete file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== File Versioning Endpoints =====

@router.get("/files/{file_id}/versions")
async def get_file_versions_endpoint(
    request: Request,
    file_id: str,
    vault_type: str = "real",
    limit: int = 50,
    offset: int = 0,
    current_user: Dict = Depends(get_current_user)
):
    """Get file versions with pagination"""
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:versions:list:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.versions.list")

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        all_versions = service.get_file_versions(user_id, vault_type, file_id)
        # Apply pagination
        total = len(all_versions)
        versions = all_versions[offset:offset + limit]
        has_more = (offset + limit) < total

        return {
            "versions": versions,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": has_more
        }
    except Exception as e:
        logger.error(f"Failed to get file versions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/{file_id}/versions/{version_id}/restore")
async def restore_file_version_endpoint(
    request: Request,
    file_id: str,
    version_id: str,
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
):
    """Restore a file to a previous version"""
    # Rate limiting: 20 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:version:restore:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=20, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.version.restored")

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.restore_file_version(user_id, vault_type, file_id, version_id)

        # Audit logging after success
        audit_logger.log(
            user_id=user_id,
            action="vault.version.restored",
            resource="vault",
            resource_id=file_id,
            details={"file_id": file_id, "version_id": version_id}
        )

        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to restore file version: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_id}/versions/{version_id}")
async def delete_file_version_endpoint(
    request: Request,
    file_id: str,
    version_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
):
    """Delete a specific file version"""
    # Rate limiting: 20 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:version:delete:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=20, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.version.deleted")

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        success = service.delete_file_version(user_id, vault_type, version_id)
        if not success:
            raise HTTPException(status_code=404, detail="Version not found")

        # Audit logging after success
        audit_logger.log(
            user_id=user_id,
            action="vault.version.deleted",
            resource="vault",
            resource_id=file_id,
            details={"file_id": file_id, "version_id": version_id}
        )

        return {"success": True, "message": "Version deleted"}
    except Exception as e:
        logger.error(f"Failed to delete file version: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Trash/Recycle Bin Endpoints =====

@router.post("/files/{file_id}/trash")
async def move_to_trash_endpoint(
    request: Request,
    file_id: str,
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
):
    """Move a file to trash (soft delete)"""
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:file:trash:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.file.trashed")

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.move_to_trash(user_id, vault_type, file_id)

        # Audit logging after success
        audit_logger.log(
            user_id=user_id,
            action="vault.file.trashed",
            resource="vault",
            resource_id=file_id,
            details={"file_id": file_id}
        )

        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to move file to trash: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/{file_id}/restore")
async def restore_from_trash_endpoint(
    request: Request,
    file_id: str,
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
):
    """Restore a file from trash"""
    # Rate limiting: 30 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:file:restore:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=30, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.file.restored")

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.restore_from_trash(user_id, vault_type, file_id)

        # Audit logging after success
        audit_logger.log(
            user_id=user_id,
            action="vault.file.restored",
            resource="vault",
            resource_id=file_id,
            details={"file_id": file_id}
        )

        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to restore file from trash: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trash")
async def get_trash_files_endpoint(
    request: Request,
    vault_type: str = "real",
    limit: int = 50,
    offset: int = 0,
    current_user: Dict = Depends(get_current_user)
):
    """Get trash files with pagination"""
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:trash:list:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.trash.list")

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        all_trash_files = service.get_trash_files(user_id, vault_type)
        # Apply pagination
        total = len(all_trash_files)
        trash_files = all_trash_files[offset:offset + limit]
        has_more = (offset + limit) < total

        return {
            "trash_files": trash_files,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": has_more
        }
    except Exception as e:
        logger.error(f"Failed to get trash files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/trash/empty")
async def empty_trash_endpoint(
    request: Request,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
):
    """Permanently delete all files in trash"""
    # Rate limiting: 5 requests per minute per user (destructive operation)
    ip = get_client_ip(request)
    key = f"vault:trash:empty:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=5, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.trash.emptied")

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.empty_trash(user_id, vault_type)

        # Audit logging after success
        deleted_count = result.get("deleted_count", 0)
        audit_logger.log(
            user_id=user_id,
            action="vault.trash.emptied",
            resource="vault",
            resource_id=user_id,  # User-level operation
            details={"count": deleted_count}
        )

        return result
    except Exception as e:
        logger.error(f"Failed to empty trash: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Advanced Search Endpoints =====

@router.get("/search")
async def search_files_endpoint(
    request: Request,
    vault_type: str = "real",
    query: str = None,
    mime_type: str = None,
    tags: str = None,  # Comma-separated tags
    date_from: str = None,
    date_to: str = None,
    min_size: int = None,
    max_size: int = None,
    folder_path: str = None,
    limit: int = 100,
    offset: int = 0,
    current_user: Dict = Depends(get_current_user)
):
    """Advanced file search with pagination"""
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:search:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.search")

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        # Parse tags if provided
        tags_list = tags.split(",") if tags else None

        all_results = service.search_files(
            user_id, vault_type, query, mime_type, tags_list,
            date_from, date_to, min_size, max_size, folder_path
        )
        # Apply pagination
        total = len(all_results)
        results = all_results[offset:offset + limit]
        has_more = (offset + limit) < total

        return {
            "results": results,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": has_more
        }
    except Exception as e:
        logger.error(f"Failed to search files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Audit Logs Endpoints =====

@router.get("/audit-logs")
async def get_audit_logs_endpoint(
    vault_type: str = None,
    action: str = None,
    resource_type: str = None,
    date_from: str = None,
    date_to: str = None,
    limit: int = 100,
    offset: int = 0,
    current_user: Dict = Depends(get_current_user)
):
    """Get audit logs with pagination and filters"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        # Get all matching logs first (service applies limit internally)
        # We'll need to modify this to handle pagination properly
        all_logs = service.get_audit_logs(
            user_id, vault_type, action, resource_type,
            date_from, date_to, limit + offset  # Get enough to paginate
        )
        # Apply pagination
        total = len(all_logs)
        logs = all_logs[offset:offset + limit]
        has_more = (offset + limit) < total

        return {
            "logs": logs,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": has_more
        }
    except Exception as e:
        logger.error(f"Failed to get audit logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== File Comments Endpoints =====

@router.post("/files/{file_id}/comments")
async def add_file_comment_endpoint(
    request: Request,
    file_id: str,
    comment_text: str = Form(...),
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
):
    """Add a comment to a file"""
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:comment:add:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.comment.added")

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.add_file_comment(user_id, vault_type, file_id, comment_text)

        # Audit logging after success
        audit_logger.log(
            user_id=user_id,
            action="vault.comment.added",
            resource="vault",
            resource_id=file_id,
            details={"file_id": file_id, "comment_id": result.get("comment_id")}
        )

        return result
    except Exception as e:
        logger.error(f"Failed to add comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{file_id}/comments")
async def get_file_comments_endpoint(
    request: Request,
    file_id: str,
    vault_type: str = "real",
    limit: int = 50,
    offset: int = 0,
    current_user: Dict = Depends(get_current_user)
):
    """Get file comments with pagination"""
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:comment:list:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.comment.list")

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        all_comments = service.get_file_comments(user_id, vault_type, file_id)
        # Apply pagination
        total = len(all_comments)
        comments = all_comments[offset:offset + limit]
        has_more = (offset + limit) < total

        return {
            "comments": comments,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": has_more
        }
    except Exception as e:
        logger.error(f"Failed to get comments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/comments/{comment_id}")
async def update_file_comment_endpoint(
    request: Request,
    comment_id: str,
    comment_text: str = Form(...),
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
):
    """Update a comment"""
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:comment:update:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.comment.updated")

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.update_file_comment(user_id, vault_type, comment_id, comment_text)

        # Audit logging after success
        audit_logger.log(
            user_id=user_id,
            action="vault.comment.updated",
            resource="vault",
            resource_id=comment_id,
            details={"comment_id": comment_id}
        )

        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/comments/{comment_id}")
async def delete_file_comment_endpoint(
    request: Request,
    comment_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
):
    """Delete a comment"""
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:comment:delete:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.comment.deleted")

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        success = service.delete_file_comment(user_id, vault_type, comment_id)
        if not success:
            raise HTTPException(status_code=404, detail="Comment not found")

        # Audit logging after success
        audit_logger.log(
            user_id=user_id,
            action="vault.comment.deleted",
            resource="vault",
            resource_id=comment_id,
            details={"comment_id": comment_id}
        )

        return {"success": True, "message": "Comment deleted"}
    except Exception as e:
        logger.error(f"Failed to delete comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== File Metadata Endpoints =====

@router.post("/files/{file_id}/metadata")
async def set_file_metadata_endpoint(
    file_id: str,
    key: str = Form(...),
    value: str = Form(...),
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
):
    """Set custom metadata for a file"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.set_file_metadata(user_id, vault_type, file_id, key, value)

        # Audit logging after success
        audit_logger.log(
            user_id=user_id,
            action="vault.file.metadata.set",
            resource="vault",
            resource_id=file_id,
            details={"file_id": file_id, "key": key}
        )

        return result
    except Exception as e:
        logger.error(f"Failed to set metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{file_id}/metadata")
async def get_file_metadata_endpoint(
    file_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
):
    """Get all metadata for a file"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        metadata = service.get_file_metadata(user_id, vault_type, file_id)
        return {"metadata": metadata}
    except Exception as e:
        logger.error(f"Failed to get metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Organization Features Endpoints =====

@router.post("/files/{file_id}/pin")
async def pin_file_endpoint(
    file_id: str,
    pin_order: int = Form(0),
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
):
    """Pin a file for quick access"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.pin_file(user_id, vault_type, file_id, pin_order)
        return result
    except Exception as e:
        logger.error(f"Failed to pin file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_id}/pin")
async def unpin_file_endpoint(
    file_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
):
    """Unpin a file"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        success = service.unpin_file(user_id, vault_type, file_id)
        if not success:
            raise HTTPException(status_code=404, detail="File not pinned")
        return {"success": True, "message": "File unpinned"}
    except Exception as e:
        logger.error(f"Failed to unpin file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pinned-files")
async def get_pinned_files_endpoint(vault_type: str = "real", current_user: Dict = Depends(get_current_user)):
    """Get all pinned files"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        pinned = service.get_pinned_files(user_id, vault_type)
        return {"pinned_files": pinned}
    except Exception as e:
        logger.error(f"Failed to get pinned files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Backup & Export Endpoints =====

@router.get("/export")
async def export_vault_data_endpoint(vault_type: str = "real", current_user: Dict = Depends(get_current_user)):
    """Export vault metadata for backup"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        export_data = service.export_vault_data(user_id, vault_type)
        return export_data
    except Exception as e:
        logger.error(f"Failed to export vault data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Analytics & Insights =====

@router.get("/analytics/storage-trends")
async def get_storage_trends(
    request: Request,
    vault_type: str = "real",
    days: int = 30,
    current_user: Dict = Depends(get_current_user)
):
    """Get storage usage trends over time"""
    # Rate limiting: 120 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:analytics:storage:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=120, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.analytics.storage")

    user_id = current_user["user_id"]
    service = get_vault_service()

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="days must be between 1 and 365")

    import sqlite3
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        # Daily storage growth
        cursor.execute("""
            SELECT
                DATE(created_at) as date,
                COUNT(*) as files_added,
                SUM(file_size) as bytes_added
            FROM vault_files
            WHERE user_id = ? AND vault_type = ? AND is_deleted = 0
              AND created_at >= datetime('now', '-' || ? || ' days')
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """, (user_id, vault_type, days))

        trends = []
        for row in cursor.fetchall():
            trends.append({
                "date": row[0],
                "files_added": row[1],
                "bytes_added": row[2] or 0
            })

        # Get current totals
        cursor.execute("""
            SELECT COUNT(*), COALESCE(SUM(file_size), 0)
            FROM vault_files
            WHERE user_id = ? AND vault_type = ? AND is_deleted = 0
        """, (user_id, vault_type))

        total_row = cursor.fetchone()
        total_files = total_row[0]
        total_bytes = total_row[1]

        return {
            "trends": trends,
            "total_files": total_files,
            "total_bytes": total_bytes,
            "days": days
        }
    finally:
        conn.close()


@router.get("/analytics/access-patterns")
async def get_access_patterns(
    request: Request,
    vault_type: str = "real",
    limit: int = 10,
    current_user: Dict = Depends(get_current_user)
):
    """Get file access patterns and most accessed files"""
    # Rate limiting: 120 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:analytics:access:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=120, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.analytics.access")

    user_id = current_user["user_id"]
    service = get_vault_service()

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    import sqlite3
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        # Most accessed files
        cursor.execute("""
            SELECT
                f.id,
                f.filename,
                f.mime_type,
                f.file_size,
                COUNT(a.id) as access_count,
                MAX(a.accessed_at) as last_accessed
            FROM vault_files f
            LEFT JOIN vault_file_access_logs a ON f.id = a.file_id
            WHERE f.user_id = ? AND f.vault_type = ? AND f.is_deleted = 0
            GROUP BY f.id
            ORDER BY access_count DESC
            LIMIT ?
        """, (user_id, vault_type, limit))

        most_accessed = []
        for row in cursor.fetchall():
            most_accessed.append({
                "id": row[0],
                "filename": row[1],
                "mime_type": row[2],
                "file_size": row[3],
                "access_count": row[4],
                "last_accessed": row[5]
            })

        # Access by type
        cursor.execute("""
            SELECT
                access_type,
                COUNT(*) as count
            FROM vault_file_access_logs
            WHERE user_id = ? AND vault_type = ?
            GROUP BY access_type
        """, (user_id, vault_type))

        access_by_type = {}
        for row in cursor.fetchall():
            access_by_type[row[0]] = row[1]

        # Recent access activity (last 24 hours)
        cursor.execute("""
            SELECT COUNT(*)
            FROM vault_file_access_logs
            WHERE user_id = ? AND vault_type = ?
              AND accessed_at >= datetime('now', '-1 day')
        """, (user_id, vault_type))

        recent_access_count = cursor.fetchone()[0]

        return {
            "most_accessed": most_accessed,
            "access_by_type": access_by_type,
            "recent_access_24h": recent_access_count
        }
    finally:
        conn.close()


@router.get("/analytics/activity-timeline")
async def get_activity_timeline(
    request: Request,
    vault_type: str = "real",
    hours: int = 24,
    limit: int = 50,
    current_user: Dict = Depends(get_current_user)
):
    """Get recent activity timeline"""
    # Rate limiting: 120 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:analytics:activity:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=120, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.analytics.activity")

    user_id = current_user["user_id"]
    service = get_vault_service()

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    import sqlite3
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        # Get recent audit logs
        cursor.execute("""
            SELECT
                action,
                resource_type,
                resource_id,
                details,
                created_at
            FROM vault_audit_logs
            WHERE user_id = ? AND vault_type = ?
              AND created_at >= datetime('now', '-' || ? || ' hours')
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, vault_type, hours, limit))

        activities = []
        for row in cursor.fetchall():
            activities.append({
                "action": row[0],
                "resource_type": row[1],
                "resource_id": row[2],
                "details": row[3],
                "timestamp": row[4]
            })

        # Get activity summary
        cursor.execute("""
            SELECT
                action,
                COUNT(*) as count
            FROM vault_audit_logs
            WHERE user_id = ? AND vault_type = ?
              AND created_at >= datetime('now', '-' || ? || ' hours')
            GROUP BY action
        """, (user_id, vault_type, hours))

        action_summary = {}
        for row in cursor.fetchall():
            action_summary[row[0]] = row[1]

        return {
            "activities": activities,
            "action_summary": action_summary,
            "hours": hours,
            "total_activities": len(activities)
        }
    finally:
        conn.close()
