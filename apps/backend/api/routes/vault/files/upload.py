"""
Vault Files Upload Routes

Handles file upload operations with encryption (single and chunked).

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request, Depends, status
from pydantic import BaseModel

from api.auth_middleware import get_current_user
from api.utils import sanitize_filename, file_lock, get_user_id
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

router = APIRouter(prefix="/api/v1/vault", tags=["vault-upload"])


@router.post(
    "/upload",
    response_model=SuccessResponse[VaultFile],
    status_code=status.HTTP_201_CREATED,
    name="vault_upload_file",
    summary="Upload file",
    description="Upload and encrypt file to vault (supports real and decoy vaults)"
)
async def upload_vault_file(
    request: Request,
    file: UploadFile = File(...),
    vault_passphrase: str = Form(...),
    vault_type: str = Form(default="real"),
    folder_path: str = Form(default="/"),
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[VaultFile]:
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

        # Read file data
        file_data = await file.read()

        if not file_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="Empty file"
                ).model_dump()
            )

        # Get MIME type
        mime_type = file.content_type or "application/octet-stream"

        # Upload and encrypt
        service = get_vault_service()
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

        return SuccessResponse(
            data=vault_file,
            message=f"File '{safe_filename}' uploaded successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"File upload failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to upload file"
            ).model_dump()
        )


class ChunkUploadResponse(BaseModel):
    status: str
    chunks_received: int
    total_chunks: int
    file: VaultFile | None = None


@router.post(
    "/upload-chunk",
    response_model=SuccessResponse[ChunkUploadResponse],
    status_code=status.HTTP_200_OK,
    name="vault_upload_chunk",
    summary="Upload file chunk",
    description="Upload file in chunks for large files (chunks assembled when complete)"
)
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
) -> SuccessResponse[ChunkUploadResponse]:
    """
    Upload file in chunks for large files

    Chunks are stored temporarily and assembled when all chunks are received
    """
    import shutil
    import mimetypes

    try:
        user_id = get_user_id(current_user)
        service = get_vault_service()

        # Create temp directory for chunks
        temp_dir = service.files_path / "temp_chunks" / file_id
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Read chunk data before acquiring lock
        chunk_data = await chunk.read()

        # SECURITY: Use file lock to prevent TOCTOU race conditions
        # This ensures concurrent chunk uploads don't corrupt the upload state
        with file_lock(temp_dir, ".upload.lock"):
            # Save chunk
            chunk_path = temp_dir / f"chunk_{chunk_index}"
            with open(chunk_path, 'wb') as f:
                f.write(chunk_data)

            # Check if all chunks received
            received_chunks = list(temp_dir.glob("chunk_*"))
            # Exclude lock file from count
            received_chunks = [c for c in received_chunks if not c.name.startswith(".")]

        if len(received_chunks) == total_chunks:
            # SECURITY: Lock during assembly to prevent concurrent assembly attempts
            with file_lock(temp_dir, ".assembly.lock"):
                # Re-check chunk count inside lock (may have changed)
                received_chunks = [c for c in temp_dir.glob("chunk_*") if not c.name.startswith(".")]
                if len(received_chunks) != total_chunks:
                    # Another request already assembled, return uploading status
                    return SuccessResponse(
                        data=ChunkUploadResponse(
                            status="uploading",
                            chunks_received=len(received_chunks),
                            total_chunks=total_chunks,
                            file=None
                        ),
                        message=f"Chunk {chunk_index + 1}/{total_chunks} received"
                    )

                # Assemble complete file
                complete_file = b""
                for i in range(total_chunks):
                    chunk_file = temp_dir / f"chunk_{i}"
                    if not chunk_file.exists():
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=ErrorResponse(
                                error_code=ErrorCode.VALIDATION_ERROR,
                                message=f"Missing chunk {i}"
                            ).model_dump()
                        )
                    with open(chunk_file, 'rb') as f:
                        complete_file += f.read()

                # Detect MIME type from filename
                mime_type, _ = mimetypes.guess_type(filename)
                if not mime_type:
                    mime_type = "application/octet-stream"

                # Upload assembled file
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

                return SuccessResponse(
                    data=ChunkUploadResponse(
                        status="complete",
                        file=vault_file,
                        chunks_received=total_chunks,
                        total_chunks=total_chunks
                    ),
                    message=f"File '{safe_filename}' uploaded successfully ({total_chunks} chunks)"
                )

        # Still uploading
        return SuccessResponse(
            data=ChunkUploadResponse(
                status="uploading",
                chunks_received=len(received_chunks),
                total_chunks=total_chunks,
                file=None
            ),
            message=f"Chunk {chunk_index + 1}/{total_chunks} received"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Chunked upload failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to upload chunk"
            ).model_dump()
        )
