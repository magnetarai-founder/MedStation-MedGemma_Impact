"""
Vault API Routes

All vault endpoints for documents, files, folders, sharing, ACL, and automation.
Moved from vault_service.py as part of R1 refactoring.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.responses import FileResponse

from api.auth_middleware import get_current_user
from api.utils import sanitize_filename
from api.permission_engine import require_perm, require_perm_team
from api.team_service import is_team_member
from api.services.vault.core import get_vault_service
from api.services.vault.schemas import (
    VaultDocument,
    VaultDocumentCreate,
    VaultDocumentUpdate,
    VaultListResponse,
    VaultFile,
    VaultFolder,
)

logger = logging.getLogger(__name__)

# Import WebSocket connection manager
try:
    from api.websocket_manager import manager
except ImportError:
    # Fallback if module structure changes
    manager = None
    logger.warning("WebSocket manager not available for vault notifications")

router = APIRouter(
    prefix="/api/v1/vault",
    tags=["Vault"],
    dependencies=[Depends(get_current_user)]  # Require auth for ALL vault endpoints
)


@router.post("/documents", response_model=VaultDocument)
@require_perm_team("vault.documents.create", level="write")
async def create_vault_document(
    vault_type: str,
    document: VaultDocumentCreate,
    team_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    Store encrypted vault document (Phase 3: team-aware)

    Security: All encryption happens client-side
    Server only stores encrypted blobs

    vault_type options:
    - "personal": Personal vault (E2E encrypted, Founder Rights cannot decrypt)
    - "decoy": Decoy vault (plausible deniability)
    - "team": Team vault (requires team_id, Founder Rights can decrypt metadata)
    """
    user_id = current_user["user_id"]

    # Phase 3: Support team vault type
    if vault_type not in ('personal', 'decoy', 'team'):
        raise HTTPException(status_code=400, detail="vault_type must be 'personal', 'decoy', or 'team'")

    # Phase 3: Team vault requires team_id and membership
    if vault_type == 'team':
        if not team_id:
            raise HTTPException(status_code=400, detail="team_id required for team vault")
        if not is_team_member(team_id, user_id):
            raise HTTPException(status_code=403, detail="Not a member of this team")

    # Map API vault_type to DB vault_type for payload validation
    db_vault_type = 'real' if vault_type in ('personal', 'team') else 'decoy'
    if document.vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="document.vault_type must be 'real' or 'decoy'")
    if document.vault_type != db_vault_type:
        raise HTTPException(status_code=400, detail="Vault type mismatch between route and payload")

    service = get_vault_service()
    return service.store_document(user_id, document, team_id=team_id)


@router.get("/documents", response_model=VaultListResponse)
@require_perm_team("vault.documents.read", level="read")
async def list_vault_documents(
    vault_type: str,
    team_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    List all vault documents (Phase 3: team-aware)

    Returns encrypted blobs that must be decrypted client-side

    vault_type options:
    - "personal": Personal vault documents
    - "decoy": Decoy vault documents
    - "team": Team vault documents (requires team_id and membership)
    """
    user_id = current_user["user_id"]

    # Phase 3: Support team vault type
    if vault_type not in ('personal', 'decoy', 'team'):
        raise HTTPException(status_code=400, detail="vault_type must be 'personal', 'decoy', or 'team'")

    # Phase 3: Team vault requires team_id and membership
    if vault_type == 'team':
        if not team_id:
            raise HTTPException(status_code=400, detail="team_id required for team vault")
        if not is_team_member(team_id, user_id):
            raise HTTPException(status_code=403, detail="Not a member of this team")

    # Legacy compatibility: 'real' -> 'personal'
    if vault_type == 'real':
        vault_type = 'personal'

    service = get_vault_service()
    return service.list_documents(user_id, vault_type, team_id=team_id)


@router.get("/documents/{doc_id}", response_model=VaultDocument)
@require_perm_team("vault.documents.read", level="read")
async def get_vault_document(
    doc_id: str,
    vault_type: str,
    team_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get single vault document (Phase 3: team-aware)

    vault_type options:
    - "personal": Personal vault document
    - "decoy": Decoy vault document
    - "team": Team vault document (requires team_id and membership)
    """
    user_id = current_user["user_id"]

    # Phase 3: Support team vault type
    if vault_type not in ('personal', 'decoy', 'team'):
        raise HTTPException(status_code=400, detail="vault_type must be 'personal', 'decoy', or 'team'")

    # Phase 3: Team vault requires team_id and membership
    if vault_type == 'team':
        if not team_id:
            raise HTTPException(status_code=400, detail="team_id required for team vault")
        if not is_team_member(team_id, user_id):
            raise HTTPException(status_code=403, detail="Not a member of this team")

    # Legacy compatibility: 'real' -> 'personal'
    db_vault_type = 'real' if vault_type in ('personal', 'team') else 'decoy'

    service = get_vault_service()
    doc = service.get_document(user_id, doc_id, db_vault_type, team_id=team_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return doc


@router.put("/documents/{doc_id}", response_model=VaultDocument)
@require_perm_team("vault.documents.update", level="write")
async def update_vault_document(
    doc_id: str,
    vault_type: str,
    update: VaultDocumentUpdate,
    team_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    Update vault document (Phase 3: team-aware)

    vault_type options:
    - "personal": Personal vault document
    - "decoy": Decoy vault document
    - "team": Team vault document (requires team_id and membership)
    """
    user_id = current_user["user_id"]

    # Phase 3: Support team vault type
    if vault_type not in ('personal', 'decoy', 'team'):
        raise HTTPException(status_code=400, detail="vault_type must be 'personal', 'decoy', or 'team'")

    # Phase 3: Team vault requires team_id and membership
    if vault_type == 'team':
        if not team_id:
            raise HTTPException(status_code=400, detail="team_id required for team vault")
        if not is_team_member(team_id, user_id):
            raise HTTPException(status_code=403, detail="Not a member of this team")

    # Legacy compatibility: 'real' -> 'personal'
    db_vault_type = 'real' if vault_type in ('personal', 'team') else 'decoy'

    service = get_vault_service()
    return service.update_document(user_id, doc_id, db_vault_type, update, team_id=team_id)


@router.delete("/documents/{doc_id}")
@require_perm_team("vault.documents.delete", level="write")
async def delete_vault_document(
    doc_id: str,
    vault_type: str,
    team_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    """
    Delete vault document (soft delete, Phase 3: team-aware)

    vault_type options:
    - "personal": Personal vault document
    - "decoy": Decoy vault document
    - "team": Team vault document (requires team_id and membership)
    """
    user_id = current_user["user_id"]

    # Phase 3: Support team vault type
    if vault_type not in ('personal', 'decoy', 'team'):
        raise HTTPException(status_code=400, detail="vault_type must be 'personal', 'decoy', or 'team'")

    # Phase 3: Team vault requires team_id and membership
    if vault_type == 'team':
        if not team_id:
            raise HTTPException(status_code=400, detail="team_id required for team vault")
        if not is_team_member(team_id, user_id):
            raise HTTPException(status_code=403, detail="Not a member of this team")

    # Legacy compatibility: 'real' -> 'personal'
    db_vault_type = 'real' if vault_type in ('personal', 'team') else 'decoy'

    service = get_vault_service()
    success = service.delete_document(user_id, doc_id, db_vault_type, team_id=team_id)

    if not success:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"success": True, "message": "Document deleted"}


@router.get("/stats")
@require_perm("vault.use")
async def get_vault_stats(
    vault_type: str,
    current_user: Dict = Depends(get_current_user)
):
    """Get vault statistics (Phase 1: uses authenticated user_id)"""
    user_id = current_user["user_id"]

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    service = get_vault_service()
    return service.get_vault_stats(user_id, vault_type)


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

    Args:
        chunk: File chunk to upload
        chunk_index: Index of this chunk (0-based)
        total_chunks: Total number of chunks for this file
        file_id: Unique identifier for this file (should be same for all chunks)
        filename: Original filename
        vault_passphrase: Vault passphrase for encryption
        vault_type: 'real' or 'decoy' (default: 'real')
        folder_path: Folder path to upload to (default: '/')

    Returns:
        Status and progress information
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
    """
    Get vault files with pagination

    Args:
        vault_type: 'real' or 'decoy'
        folder_path: Folder path to list files from
        page: Page number (1-indexed)
        page_size: Number of files per page
        sort_by: Sort field ('name', 'date', or 'size')

    Returns:
        Paginated list of files with metadata
    """
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
    """
    Get thumbnail for image files

    Decrypts the file and generates a thumbnail on the fly.
    Returns 200x200 JPEG thumbnail.
    """
    from fastapi.responses import Response

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


@router.post("/folders", response_model=VaultFolder)
async def create_vault_folder(
    folder_name: str = Form(...),
    vault_type: str = Form(default="real"),
    parent_path: str = Form(default="/"),
    current_user: Dict = Depends(get_current_user)
):
    """Create a new folder in the vault"""
    user_id = current_user["user_id"]

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    service = get_vault_service()
    try:
        folder = service.create_folder(user_id, vault_type, folder_name, parent_path)
        return folder
    except Exception as e:
        logger.error(f"Folder creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Folder creation failed: {str(e)}")


@router.get("/folders", response_model=List[VaultFolder])
async def list_vault_folders(vault_type: str = "real", parent_path: str = None, current_user: Dict = Depends(get_current_user)):
    """List folders, optionally filtered by parent path"""
    user_id = current_user["user_id"]

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    service = get_vault_service()
    return service.list_folders(user_id, vault_type, parent_path)


@router.delete("/folders")
async def delete_vault_folder(folder_path: str, vault_type: str = "real", current_user: Dict = Depends(get_current_user)):
    """Delete a folder (and all its contents)"""
    user_id = current_user["user_id"]

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    service = get_vault_service()
    success = service.delete_folder(user_id, vault_type, folder_path)

    if not success:
        raise HTTPException(status_code=404, detail="Folder not found")

    return {"success": True, "message": "Folder deleted"}


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
    await manager.broadcast_file_event(
        event_type="file_moved",
        file_data={"id": file_id, "new_folder_path": new_folder_path},
        vault_type=vault_type,
        user_id=user_id
    )

    return {"success": True, "message": "File moved", "new_folder_path": new_folder_path}


@router.put("/folders/rename")
async def rename_vault_folder(old_path: str, new_name: str, vault_type: str = "real", current_user: Dict = Depends(get_current_user)):
    """Rename a folder"""
    user_id = current_user["user_id"]

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    if not new_name or not new_name.strip():
        raise HTTPException(status_code=400, detail="new_name is required")

    service = get_vault_service()
    success = service.rename_folder(user_id, vault_type, old_path, new_name.strip())

    if not success:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Calculate new path for response
    parent_path = old_path.rsplit('/', 1)[0] if old_path.count('/') > 0 else '/'
    new_path = f"{parent_path}/{new_name.strip()}" if parent_path != '/' else f"/{new_name.strip()}"

    return {"success": True, "message": "Folder renamed", "new_path": new_path}


@router.get("/health")
async def vault_health():
    """Health check for vault service"""
    return {
        "vault_service": "operational",
        "encryption": "server-side with Fernet (AES-128)",
        "storage": "SQLite + encrypted files on disk",
        "file_uploads": "supported"
    }


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


# ===== Day 4: File Versioning Endpoints =====

@router.get("/files/{file_id}/versions")
async def get_file_versions_endpoint(
    file_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
):
    """Get all versions of a file"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        versions = service.get_file_versions(user_id, vault_type, file_id)
        return {"versions": versions}
    except Exception as e:
        logger.error(f"Failed to get file versions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/{file_id}/versions/{version_id}/restore")
async def restore_file_version_endpoint(
    file_id: str,
    version_id: str,
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
):
    """Restore a file to a previous version"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.restore_file_version(user_id, vault_type, file_id, version_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to restore file version: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_id}/versions/{version_id}")
async def delete_file_version_endpoint(
    file_id: str,
    version_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
):
    """Delete a specific file version"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        success = service.delete_file_version(user_id, vault_type, version_id)
        if not success:
            raise HTTPException(status_code=404, detail="Version not found")
        return {"success": True, "message": "Version deleted"}
    except Exception as e:
        logger.error(f"Failed to delete file version: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Day 4: Trash/Recycle Bin Endpoints =====

@router.post("/files/{file_id}/trash")
async def move_to_trash_endpoint(
    file_id: str,
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
):
    """Move a file to trash (soft delete)"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.move_to_trash(user_id, vault_type, file_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to move file to trash: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/{file_id}/restore")
async def restore_from_trash_endpoint(
    file_id: str,
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
):
    """Restore a file from trash"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.restore_from_trash(user_id, vault_type, file_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to restore file from trash: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trash")
async def get_trash_files_endpoint(vault_type: str = "real", current_user: Dict = Depends(get_current_user)):
    """Get all files in trash"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        trash_files = service.get_trash_files(user_id, vault_type)
        return {"trash_files": trash_files}
    except Exception as e:
        logger.error(f"Failed to get trash files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/trash/empty")
async def empty_trash_endpoint(vault_type: str = "real", current_user: Dict = Depends(get_current_user)):
    """Permanently delete all files in trash"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.empty_trash(user_id, vault_type)
        return result
    except Exception as e:
        logger.error(f"Failed to empty trash: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Day 4: Advanced Search Endpoints =====

@router.get("/search")
async def search_files_endpoint(
    vault_type: str = "real",
    query: str = None,
    mime_type: str = None,
    tags: str = None,  # Comma-separated tags
    date_from: str = None,
    date_to: str = None,
    min_size: int = None,
    max_size: int = None,
    folder_path: str = None,
    current_user: Dict = Depends(get_current_user)
):
    """Advanced file search with multiple filters"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        # Parse tags if provided
        tags_list = tags.split(",") if tags else None

        results = service.search_files(
            user_id, vault_type, query, mime_type, tags_list,
            date_from, date_to, min_size, max_size, folder_path
        )
        return {"results": results}
    except Exception as e:
        logger.error(f"Failed to search files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Day 4: File Sharing Endpoints =====

@router.post("/files/{file_id}/share")
async def create_share_link_endpoint(
    file_id: str,
    vault_type: str = Form("real"),
    password: str = Form(None),
    expires_at: str = Form(None),
    max_downloads: int = Form(None),
    permissions: str = Form("download"),
    current_user: Dict = Depends(get_current_user)
):
    """Create a shareable link for a file"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.create_share_link(
            user_id, vault_type, file_id, password,
            expires_at, max_downloads, permissions
        )
        return result
    except Exception as e:
        logger.error(f"Failed to create share link: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{file_id}/shares")
async def get_file_shares_endpoint(
    file_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
):
    """Get all share links for a file"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        shares = service.get_file_shares(user_id, vault_type, file_id)
        return {"shares": shares}
    except Exception as e:
        logger.error(f"Failed to get file shares: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/shares/{share_id}")
async def revoke_share_link_endpoint(
    share_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
):
    """Revoke a share link"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        success = service.revoke_share_link(user_id, vault_type, share_id)
        if not success:
            raise HTTPException(status_code=404, detail="Share link not found")
        return {"success": True, "message": "Share link revoked"}
    except Exception as e:
        logger.error(f"Failed to revoke share link: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/share/{share_token}")
async def access_share_link_endpoint(
    share_token: str,
    password: str = None
):
    """Access a shared file via share token"""
    service = get_vault_service()

    try:
        # Get share details
        share_info = service.get_share_link(share_token)

        # Verify password if required
        if share_info["requires_password"]:
            if not password:
                raise HTTPException(status_code=401, detail="Password required")
            if not service.verify_share_password(share_token, password):
                raise HTTPException(status_code=401, detail="Invalid password")

        return share_info
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to access share link: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Day 4: Audit Logs Endpoints =====

@router.get("/audit-logs")
async def get_audit_logs_endpoint(
    vault_type: str = None,
    action: str = None,
    resource_type: str = None,
    date_from: str = None,
    date_to: str = None,
    limit: int = 100,
    current_user: Dict = Depends(get_current_user)
):
    """Get audit logs with filters"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        logs = service.get_audit_logs(
            user_id, vault_type, action, resource_type,
            date_from, date_to, limit
        )
        return {"logs": logs}
    except Exception as e:
        logger.error(f"Failed to get audit logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Day 4: File Comments Endpoints =====

@router.post("/files/{file_id}/comments")
async def add_file_comment_endpoint(
    file_id: str,
    comment_text: str = Form(...),
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
):
    """Add a comment to a file"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.add_file_comment(user_id, vault_type, file_id, comment_text)
        return result
    except Exception as e:
        logger.error(f"Failed to add comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{file_id}/comments")
async def get_file_comments_endpoint(
    file_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
):
    """Get all comments for a file"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        comments = service.get_file_comments(user_id, vault_type, file_id)
        return {"comments": comments}
    except Exception as e:
        logger.error(f"Failed to get comments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/comments/{comment_id}")
async def update_file_comment_endpoint(
    comment_id: str,
    comment_text: str = Form(...),
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
):
    """Update a comment"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.update_file_comment(user_id, vault_type, comment_id, comment_text)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/comments/{comment_id}")
async def delete_file_comment_endpoint(
    comment_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
):
    """Delete a comment"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        success = service.delete_file_comment(user_id, vault_type, comment_id)
        if not success:
            raise HTTPException(status_code=404, detail="Comment not found")
        return {"success": True, "message": "Comment deleted"}
    except Exception as e:
        logger.error(f"Failed to delete comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Day 4: File Metadata Endpoints =====

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


# ===== Day 4: Organization Features Endpoints =====

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


@router.post("/folders/{folder_id}/color")
async def set_folder_color_endpoint(
    folder_id: str,
    color: str = Form(...),
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
):
    """Set color for a folder"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        result = service.set_folder_color(user_id, vault_type, folder_id, color)
        return result
    except Exception as e:
        logger.error(f"Failed to set folder color: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/folder-colors")
async def get_folder_colors_endpoint(vault_type: str = "real", current_user: Dict = Depends(get_current_user)):
    """Get all folder colors"""
    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        colors = service.get_folder_colors(user_id, vault_type)
        return {"folder_colors": colors}
    except Exception as e:
        logger.error(f"Failed to get folder colors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Day 4: Backup & Export Endpoints =====

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


# ===== Day 5: Analytics & Insights =====

@router.get("/analytics/storage-trends")
async def get_storage_trends(
    vault_type: str = "real",
    days: int = 30,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get storage usage trends over time

    Args:
        vault_type: 'real' or 'decoy'
        days: Number of days to look back (default: 30)

    Returns:
        Daily storage growth data
    """
    user_id = current_user["user_id"]
    service = get_vault_service()

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="days must be between 1 and 365")

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
async def get_access_patterns(vault_type: str = "real", limit: int = 10, current_user: Dict = Depends(get_current_user)):
    """
    Get file access patterns and most accessed files

    Args:
        vault_type: 'real' or 'decoy'
        limit: Number of top files to return

    Returns:
        Most accessed files and access statistics
    """
    user_id = current_user["user_id"]
    service = get_vault_service()

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

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
    vault_type: str = "real",
    hours: int = 24,
    limit: int = 50,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get recent activity timeline

    Args:
        vault_type: 'real' or 'decoy'
        hours: Hours to look back
        limit: Max activities to return

    Returns:
        Recent activity events
    """
    user_id = current_user["user_id"]
    service = get_vault_service()

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

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


# ===== Day 5: Real-Time Collaboration (WebSocket) =====

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    vault_type: str = "real",
    token: str = None  # Auth token from query param
):
    """
    WebSocket endpoint for real-time vault updates

    Supports:
    - Real-time file upload/delete/update notifications
    - User presence tracking
    - Activity broadcasting

    Security: Requires valid JWT token for authentication
    """
    # Verify authentication before accepting connection
    if not token:
        await websocket.close(code=1008, reason="Missing authentication token")
        return

    try:
        # Verify JWT token
        import jwt
        from auth_middleware import JWT_SECRET, JWT_ALGORITHM
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        authenticated_user_id = payload.get("user_id")

        # Verify user_id matches token
        if authenticated_user_id != user_id:
            await websocket.close(code=1008, reason="User ID mismatch")
            return
    except jwt.ExpiredSignatureError:
        await websocket.close(code=1008, reason="Token expired")
        return
    except jwt.InvalidTokenError:
        await websocket.close(code=1008, reason="Invalid token")
        return

    await manager.connect(websocket, user_id, vault_type)

    try:
        while True:
            # Receive messages for keepalive and client-initiated events
            data = await websocket.receive_text()

            # Parse incoming message
            try:
                import json
                message = json.loads(data)

                # Handle different message types
                if message.get("type") == "ping":
                    # Respond to keepalive ping
                    await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})

                elif message.get("type") == "activity_update":
                    # Update user's last activity timestamp
                    if user_id in manager.user_presence:
                        manager.user_presence[user_id]["last_activity"] = datetime.utcnow().isoformat()

                else:
                    # Echo unknown messages for debugging
                    await websocket.send_json({"type": "echo", "received": message})

            except json.JSONDecodeError:
                # If not JSON, treat as simple keepalive string
                await websocket.send_text(f"Message received: {data}")

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id, vault_type)
        logger.info(f"WebSocket disconnected: user={user_id}, vault={vault_type}")


@router.get("/ws/online-users")
async def get_online_users(vault_type: Optional[str] = None):
    """Get list of currently online users"""
    return {
        "online_users": manager.get_online_users(vault_type),
        "total_connections": manager.get_connection_count(),
        "vault_type": vault_type
    }


# ===== Phase B & G: User Management & Multi-User Features =====

@router.post("/users/register")
async def register_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    """Register a new user"""
    service = get_vault_service()

    # Generate user ID
    import uuid
    user_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    # Hash password with PBKDF2
    password_key, salt = service._get_encryption_key(password)
    password_hash = base64.b64encode(password_key).decode('utf-8')
    salt_b64 = base64.b64encode(salt).decode('utf-8')

    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO vault_users (user_id, username, email, password_hash, salt, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, username, email, password_hash, salt_b64, now, now))

        conn.commit()

        return {
            "user_id": user_id,
            "username": username,
            "email": email,
            "created_at": now
        }
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=f"User already exists: {str(e)}")
    finally:
        conn.close()


@router.post("/users/login")
async def login_user(
    username: str = Form(...),
    password: str = Form(...)
):
    """Login user and return user info"""
    service = get_vault_service()

    conn = sqlite3.connect(service.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT * FROM vault_users WHERE username = ? AND is_active = 1
        """, (username,))

        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Verify password
        stored_salt = base64.b64decode(user['salt'])
        password_key, _ = service._get_encryption_key(password, stored_salt)
        password_hash = base64.b64encode(password_key).decode('utf-8')

        if password_hash != user['password_hash']:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Update last login
        now = datetime.utcnow().isoformat()
        cursor.execute("""
            UPDATE vault_users SET last_login = ? WHERE user_id = ?
        """, (now, user['user_id']))
        conn.commit()

        return {
            "user_id": user['user_id'],
            "username": user['username'],
            "email": user['email'],
            "last_login": now
        }
    finally:
        conn.close()


@router.post("/acl/grant-file-permission")
async def grant_file_permission(
    file_id: str = Form(...),
    user_id: str = Form(...),
    permission: str = Form(...),
    granted_by: str = Form(...),
    expires_at: Optional[str] = Form(None)
):
    """Grant permission to a user for a specific file"""
    service = get_vault_service()

    if permission not in ['read', 'write', 'delete', 'share']:
        raise HTTPException(status_code=400, detail="Invalid permission type")

    acl_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO vault_file_acl (id, file_id, user_id, permission, granted_by, granted_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (acl_id, file_id, user_id, permission, granted_by, now, expires_at))

        conn.commit()

        return {
            "acl_id": acl_id,
            "file_id": file_id,
            "user_id": user_id,
            "permission": permission,
            "granted_at": now
        }
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Permission already exists")
    finally:
        conn.close()


@router.post("/acl/check-permission")
async def check_file_permission(
    file_id: str = Form(...),
    user_id: str = Form(...),
    permission: str = Form(...)
):
    """Check if user has specific permission for a file"""
    service = get_vault_service()

    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()

    try:
        # Check for unexpired permission
        cursor.execute("""
            SELECT * FROM vault_file_acl
            WHERE file_id = ? AND user_id = ? AND permission = ?
              AND (expires_at IS NULL OR expires_at > datetime('now'))
        """, (file_id, user_id, permission))

        has_permission = cursor.fetchone() is not None

        return {
            "file_id": file_id,
            "user_id": user_id,
            "permission": permission,
            "has_permission": has_permission
        }
    finally:
        conn.close()


@router.get("/acl/file-permissions/{file_id}")
async def get_file_permissions(file_id: str):
    """Get all permissions for a file"""
    service = get_vault_service()

    conn = sqlite3.connect(service.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT acl.*, u.username
            FROM vault_file_acl acl
            JOIN vault_users u ON acl.user_id = u.user_id
            WHERE acl.file_id = ?
              AND (acl.expires_at IS NULL OR acl.expires_at > datetime('now'))
        """, (file_id,))

        permissions = []
        for row in cursor.fetchall():
            permissions.append({
                "acl_id": row['id'],
                "user_id": row['user_id'],
                "username": row['username'],
                "permission": row['permission'],
                "granted_by": row['granted_by'],
                "granted_at": row['granted_at'],
                "expires_at": row['expires_at']
            })

        return {"file_id": file_id, "permissions": permissions}
    finally:
        conn.close()


@router.delete("/acl/revoke-permission/{acl_id}")
async def revoke_permission(acl_id: str):
    """Revoke a specific permission"""
    service = get_vault_service()

    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM vault_file_acl WHERE id = ?", (acl_id,))
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Permission not found")

        return {"success": True, "acl_id": acl_id}
    finally:
        conn.close()


@router.post("/sharing/create-invitation")
async def create_sharing_invitation(
    resource_type: str = Form(...),
    resource_id: str = Form(...),
    from_user_id: str = Form(...),
    to_user_email: str = Form(...),
    permission: str = Form(...),
    expires_in_days: int = Form(7)
):
    """Create a sharing invitation"""
    service = get_vault_service()

    if resource_type not in ['file', 'folder']:
        raise HTTPException(status_code=400, detail="Invalid resource type")

    if permission not in ['read', 'write', 'delete', 'share']:
        raise HTTPException(status_code=400, detail="Invalid permission")

    import secrets
    invitation_id = str(uuid.uuid4())
    invitation_token = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    expires_at = (now + timedelta(days=expires_in_days)).isoformat()
    now_iso = now.isoformat()

    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO vault_share_invitations
            (id, resource_type, resource_id, from_user_id, to_user_email, permission,
             invitation_token, status, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
        """, (invitation_id, resource_type, resource_id, from_user_id, to_user_email,
              permission, invitation_token, now_iso, expires_at))

        conn.commit()

        return {
            "invitation_id": invitation_id,
            "invitation_token": invitation_token,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "to_user_email": to_user_email,
            "permission": permission,
            "expires_at": expires_at,
            "share_url": f"/api/v1/vault/sharing/accept/{invitation_token}"
        }
    finally:
        conn.close()


@router.post("/sharing/accept/{invitation_token}")
async def accept_sharing_invitation(invitation_token: str, user_id: str = Form(...)):
    """Accept a sharing invitation"""
    service = get_vault_service()

    conn = sqlite3.connect(service.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Get invitation
        cursor.execute("""
            SELECT * FROM vault_share_invitations
            WHERE invitation_token = ? AND status = 'pending'
              AND expires_at > datetime('now')
        """, (invitation_token,))

        invitation = cursor.fetchone()

        if not invitation:
            raise HTTPException(status_code=404, detail="Invalid or expired invitation")

        # Create ACL entry
        acl_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        if invitation['resource_type'] == 'file':
            cursor.execute("""
                INSERT INTO vault_file_acl (id, file_id, user_id, permission, granted_by, granted_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (acl_id, invitation['resource_id'], user_id, invitation['permission'],
                  invitation['from_user_id'], now))

        # Update invitation status
        cursor.execute("""
            UPDATE vault_share_invitations
            SET status = 'accepted', accepted_at = ?
            WHERE id = ?
        """, (now, invitation['id']))

        conn.commit()

        return {
            "success": True,
            "resource_type": invitation['resource_type'],
            "resource_id": invitation['resource_id'],
            "permission": invitation['permission']
        }
    finally:
        conn.close()


@router.post("/sharing/decline/{invitation_token}")
async def decline_sharing_invitation(invitation_token: str):
    """Decline a sharing invitation"""
    service = get_vault_service()

    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE vault_share_invitations
            SET status = 'declined'
            WHERE invitation_token = ? AND status = 'pending'
        """, (invitation_token,))

        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Invitation not found")

        return {"success": True}
    finally:
        conn.close()


@router.get("/sharing/my-invitations")
async def get_my_invitations(user_email: str):
    """Get all pending invitations for a user"""
    service = get_vault_service()

    conn = sqlite3.connect(service.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT i.*, u.username as from_username
            FROM vault_share_invitations i
            JOIN vault_users u ON i.from_user_id = u.user_id
            WHERE i.to_user_email = ? AND i.status = 'pending'
              AND i.expires_at > datetime('now')
            ORDER BY i.created_at DESC
        """, (user_email,))

        invitations = []
        for row in cursor.fetchall():
            invitations.append({
                "invitation_id": row['id'],
                "invitation_token": row['invitation_token'],
                "resource_type": row['resource_type'],
                "resource_id": row['resource_id'],
                "from_username": row['from_username'],
                "permission": row['permission'],
                "created_at": row['created_at'],
                "expires_at": row['expires_at']
            })

        return {"invitations": invitations}
    finally:
        conn.close()


# ===== Phase 3: File Organization Automation =====

@router.post("/automation/create-rule")
async def create_organization_rule(
    user_id: str = Form(...),
    vault_type: str = Form(...),
    rule_name: str = Form(...),
    rule_type: str = Form(...),
    condition_value: str = Form(...),
    action_type: str = Form(...),
    action_value: str = Form(...),
    priority: int = Form(0)
):
    """Create a file organization rule"""
    service = get_vault_service()
    
    valid_rule_types = ['mime_type', 'file_extension', 'file_size', 'filename_pattern', 'date']
    valid_action_types = ['move_to_folder', 'add_tag', 'set_color']
    
    if rule_type not in valid_rule_types:
        raise HTTPException(status_code=400, detail=f"Invalid rule_type. Must be one of: {valid_rule_types}")
    
    if action_type not in valid_action_types:
        raise HTTPException(status_code=400, detail=f"Invalid action_type. Must be one of: {valid_action_types}")
    
    rule_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO vault_organization_rules
            (id, user_id, vault_type, rule_name, rule_type, condition_value,
             action_type, action_value, priority, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (rule_id, user_id, vault_type, rule_name, rule_type, condition_value,
              action_type, action_value, priority, now))
        
        conn.commit()
        
        return {
            "rule_id": rule_id,
            "rule_name": rule_name,
            "rule_type": rule_type,
            "action_type": action_type,
            "is_enabled": True,
            "created_at": now
        }
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Rule with this name already exists")
    finally:
        conn.close()


@router.get("/automation/rules")
async def get_organization_rules(user_id: str, vault_type: str = "real"):
    """Get all organization rules for a user"""
    service = get_vault_service()
    
    conn = sqlite3.connect(service.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT * FROM vault_organization_rules
            WHERE user_id = ? AND vault_type = ?
            ORDER BY priority DESC, created_at ASC
        """, (user_id, vault_type))
        
        rules = []
        for row in cursor.fetchall():
            rules.append({
                "rule_id": row['id'],
                "rule_name": row['rule_name'],
                "rule_type": row['rule_type'],
                "condition_value": row['condition_value'],
                "action_type": row['action_type'],
                "action_value": row['action_value'],
                "is_enabled": bool(row['is_enabled']),
                "priority": row['priority'],
                "files_processed": row['files_processed'],
                "last_run": row['last_run'],
                "created_at": row['created_at']
            })
        
        return {"rules": rules}
    finally:
        conn.close()


@router.post("/automation/run-rules")
async def run_organization_rules(user_id: str = Form(...), vault_type: str = Form("real")):
    """Run all enabled organization rules on existing files"""
    service = get_vault_service()
    
    conn = sqlite3.connect(service.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Get enabled rules
        cursor.execute("""
            SELECT * FROM vault_organization_rules
            WHERE user_id = ? AND vault_type = ? AND is_enabled = 1
            ORDER BY priority DESC
        """, (user_id, vault_type))
        
        rules = cursor.fetchall()
        total_processed = 0
        results = []
        
        for rule in rules:
            files_matched = 0
            
            # Get all files for this user/vault
            cursor.execute("""
                SELECT * FROM vault_files
                WHERE user_id = ? AND vault_type = ? AND is_deleted = 0
            """, (user_id, vault_type))
            
            files = cursor.fetchall()
            
            for file in files:
                matched = False
                
                # Check rule condition
                if rule['rule_type'] == 'mime_type':
                    matched = file['mime_type'].startswith(rule['condition_value'])
                
                elif rule['rule_type'] == 'file_extension':
                    matched = file['filename'].endswith(rule['condition_value'])
                
                elif rule['rule_type'] == 'file_size':
                    # Format: ">1000000" for files larger than 1MB
                    operator = rule['condition_value'][0]
                    size_limit = int(rule['condition_value'][1:])
                    if operator == '>':
                        matched = file['file_size'] > size_limit
                    elif operator == '<':
                        matched = file['file_size'] < size_limit
                
                elif rule['rule_type'] == 'filename_pattern':
                    import re
                    matched = bool(re.search(rule['condition_value'], file['filename']))
                
                # Apply action if matched
                if matched:
                    if rule['action_type'] == 'move_to_folder':
                        cursor.execute("""
                            UPDATE vault_files
                            SET folder_path = ?, updated_at = ?
                            WHERE id = ?
                        """, (rule['action_value'], datetime.utcnow().isoformat(), file['id']))
                    
                    elif rule['action_type'] == 'add_tag':
                        # Add tag if it doesn't exist
                        tag_id = str(uuid.uuid4())
                        try:
                            cursor.execute("""
                                INSERT INTO vault_file_tags
                                (id, file_id, user_id, vault_type, tag_name, created_at)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (tag_id, file['id'], user_id, vault_type,
                                  rule['action_value'], datetime.utcnow().isoformat()))
                        except sqlite3.IntegrityError:
                            pass  # Tag already exists
                    
                    files_matched += 1
            
            # Update rule stats
            now = datetime.utcnow().isoformat()
            cursor.execute("""
                UPDATE vault_organization_rules
                SET last_run = ?, files_processed = files_processed + ?
                WHERE id = ?
            """, (now, files_matched, rule['id']))
            
            results.append({
                "rule_name": rule['rule_name'],
                "files_matched": files_matched
            })
            total_processed += files_matched
        
        conn.commit()
        
        return {
            "total_rules_run": len(rules),
            "total_files_processed": total_processed,
            "results": results
        }
    finally:
        conn.close()


@router.put("/automation/toggle-rule/{rule_id}")
async def toggle_rule(rule_id: str, enabled: bool = Form(...)):
    """Enable or disable a rule"""
    service = get_vault_service()
    
    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE vault_organization_rules
            SET is_enabled = ?
            WHERE id = ?
        """, (1 if enabled else 0, rule_id))
        
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        return {"success": True, "rule_id": rule_id, "enabled": enabled}
    finally:
        conn.close()


@router.delete("/automation/delete-rule/{rule_id}")
async def delete_rule(rule_id: str):
    """Delete an organization rule"""
    service = get_vault_service()

    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM vault_organization_rules WHERE id = ?", (rule_id,))
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Rule not found")

        return {"success": True, "rule_id": rule_id}
    finally:
        conn.close()


# ===== Decoy Vault Seeding =====

@router.post("/seed-decoy-vault")
async def seed_decoy_vault_endpoint(request: Request, current_user: Dict = Depends(get_current_user)):
    """
    Seed decoy vault with realistic documents for plausible deniability

    This populates the decoy vault with convincing documents like:
    - Budget spreadsheets
    - WiFi passwords
    - Shopping lists
    - Travel plans
    - Meeting notes

    Only seeds if decoy vault is empty.
    """
    user_id = current_user["user_id"]

    try:
        from vault_seed_data import get_seeder

        seeder = get_seeder()
        result = seeder.seed_decoy_vault(user_id)

        logger.info(f"Decoy vault seeding result: {result['status']}")

        return result

    except Exception as e:
        logger.error(f"Failed to seed decoy vault: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear-decoy-vault")
async def clear_decoy_vault_endpoint(request: Request, current_user: Dict = Depends(get_current_user)):
    """
    Clear all decoy vault documents (for testing/re-seeding)

    WARNING: This will delete all decoy vault documents!
    Use this if you want to re-seed the decoy vault with fresh data.
    """
    user_id = current_user["user_id"]

    try:
        from vault_seed_data import get_seeder

        seeder = get_seeder()
        result = seeder.clear_decoy_vault(user_id)

        logger.info(f"Decoy vault cleared: {result['deleted_count']} documents")

        return result

    except Exception as e:
        logger.error(f"Failed to clear decoy vault: {e}")
        raise HTTPException(status_code=500, detail=str(e))
