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

logger = logging.getLogger(__name__)

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
    file_id: str,
    vault_type: str = "real",
    vault_passphrase: str = "",
    current_user: Dict = Depends(get_current_user)
):
    """Download and decrypt a vault file"""
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
