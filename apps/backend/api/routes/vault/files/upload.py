"""
Vault Files Upload Routes

Handles file upload operations:
- Single file upload with encryption
- Chunked upload for large files
"""

import logging
from typing import Dict
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request, Depends

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from auth_middleware import get_current_user
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
