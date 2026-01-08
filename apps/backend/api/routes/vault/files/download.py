"""
Vault Files Download Routes

Handles file download operations:
- File download with decryption
- Thumbnail generation for images

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
import sqlite3
from pathlib import Path
from typing import Dict
from fastapi import APIRouter, HTTPException, Request, Depends, status
from fastapi.responses import FileResponse, Response
from cryptography.fernet import Fernet

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from api.auth_middleware import get_current_user
from api.utils import get_user_id
from api.services.vault.core import get_vault_service
from api.rate_limiter import get_client_ip, rate_limiter
from api.audit_logger import get_audit_logger
from api.routes.schemas import ErrorResponse, ErrorCode

logger = logging.getLogger(__name__)
audit_logger = get_audit_logger()

router = APIRouter(prefix="/api/v1/vault", tags=["vault-download"])


@router.get(
    "/files/{file_id}/thumbnail",
    response_class=Response,
    status_code=status.HTTP_200_OK,
    name="vault_get_file_thumbnail",
    summary="Get file thumbnail",
    description="Get thumbnail for image files (200x200 max)"
)
async def get_file_thumbnail(
    file_id: str,
    vault_type: str = "real",
    vault_passphrase: str = "",
    current_user: Dict = Depends(get_current_user)
) -> Response:
    """
    Get thumbnail for image files

    Args:
        file_id: File ID to generate thumbnail for
        vault_type: 'real' or 'decoy' (default: 'real')
        vault_passphrase: Vault passphrase for decryption

    Returns:
        JPEG thumbnail image (200x200 max)
    """
    try:
        user_id = current_user["user_id"]
        service = get_vault_service()

        if vault_type not in ('real', 'decoy'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="vault_type must be 'real' or 'decoy'"
                ).model_dump()
            )

        if not vault_passphrase:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="vault_passphrase is required"
                ).model_dump()
            )

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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="File not found"
                ).model_dump()
            )

        # Check if file is an image
        if not file_row['mime_type'].startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="File is not an image"
                ).model_dump()
            )

        # Read and decrypt file
        encrypted_path = file_row['encrypted_path']
        file_path = service.files_path / encrypted_path

        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="File data not found"
                ).model_dump()
            )

        with open(file_path, 'rb') as f:
            encrypted_data = f.read()

        # Decrypt file
        encryption_key, _ = service._get_encryption_key(vault_passphrase)
        fernet = Fernet(encryption_key)

        try:
            decrypted_data = fernet.decrypt(encrypted_data)
        except Exception as e:
            logger.error(f"Decryption failed for file {file_id}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="Decryption failed - invalid passphrase"
                ).model_dump()
            )

        # Generate thumbnail
        thumbnail = service.generate_thumbnail(decrypted_data, max_size=(200, 200))

        if not thumbnail:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error_code=ErrorCode.INTERNAL_ERROR,
                    message="Thumbnail generation failed"
                ).model_dump()
            )

        return Response(content=thumbnail, media_type="image/jpeg")

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to generate thumbnail for file {file_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to generate thumbnail"
            ).model_dump()
        )


@router.get(
    "/files/{file_id}/download",
    response_class=FileResponse,
    status_code=status.HTTP_200_OK,
    name="vault_download_file",
    summary="Download file",
    description="Download and decrypt a vault file (rate limited: 120 requests/minute)"
)
async def download_vault_file(
    request: Request,
    file_id: str,
    vault_type: str = "real",
    vault_passphrase: str = "",
    current_user: Dict = Depends(get_current_user)
) -> FileResponse:
    """
    Download and decrypt a vault file

    Args:
        file_id: File ID to download
        vault_type: 'real' or 'decoy' (default: 'real')
        vault_passphrase: Vault passphrase for decryption

    Returns:
        Decrypted file as attachment

    Rate limit: 120 requests per minute per user
    """
    try:
        # Rate limiting: 120 requests per minute per user
        ip = get_client_ip(request)
        key = f"vault:file:download:{get_user_id(current_user)}:{ip}"
        if not rate_limiter.check_rate_limit(key, max_requests=120, window_seconds=60):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=ErrorResponse(
                    error_code=ErrorCode.RATE_LIMIT,
                    message="Rate limit exceeded. Max 120 downloads per minute"
                ).model_dump()
            )

        user_id = current_user["user_id"]

        if vault_type not in ('real', 'decoy'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="vault_type must be 'real' or 'decoy'"
                ).model_dump()
            )

        if not vault_passphrase:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="vault_passphrase is required"
                ).model_dump()
            )

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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="File not found"
                ).model_dump()
            )

        # SECURITY: Path containment check - ensure file is within vault directory
        vault_files_dir = service.files_path.resolve()
        encrypted_file_path = Path(file_row['encrypted_path']).resolve()

        if not str(encrypted_file_path).startswith(str(vault_files_dir)):
            logger.error(f"SECURITY: Path traversal attempt: {file_row['encrypted_path']}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ErrorResponse(
                    error_code=ErrorCode.FORBIDDEN,
                    message="Invalid file path"
                ).model_dump()
            )

        if not encrypted_file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Encrypted file not found on disk"
                ).model_dump()
            )

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

        # SECURITY: Sanitize filename for HTTP header injection prevention
        import re
        safe_filename = re.sub(r'[\r\n\x00-\x1f\x7f"]', '_', file_row['filename'])

        return FileResponse(
            path=temp_file.name,
            filename=safe_filename,
            media_type=file_row['mime_type'] or 'application/octet-stream',
            headers={"Content-Disposition": f"attachment; filename=\"{safe_filename}\""}
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to download file {file_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to decrypt and download file"
            ).model_dump()
        )
