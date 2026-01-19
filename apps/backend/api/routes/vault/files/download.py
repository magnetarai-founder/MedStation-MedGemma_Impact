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

from api.auth_middleware import get_current_user
from api.utils import get_user_id
from api.services.vault.core import get_vault_service
from api.rate_limiter import get_client_ip, rate_limiter
from api.audit_logger import get_audit_logger
from api.errors import http_400, http_403, http_404, http_429, http_500

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
        user_id = get_user_id(current_user)
        service = get_vault_service()

        if vault_type not in ('real', 'decoy'):
            raise http_400("vault_type must be 'real' or 'decoy'")

        if not vault_passphrase:
            raise http_400("vault_passphrase is required")

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
            raise http_404("File not found", resource="file")

        # Check if file is an image
        if not file_row['mime_type'].startswith('image/'):
            raise http_400("File is not an image")

        # Read and decrypt file
        encrypted_path = file_row['encrypted_path']
        file_path = service.files_path / encrypted_path

        if not file_path.exists():
            raise http_404("File data not found", resource="file")

        with open(file_path, 'rb') as f:
            encrypted_data = f.read()

        # Decrypt file
        encryption_key, _ = service._get_encryption_key(vault_passphrase)
        fernet = Fernet(encryption_key)

        try:
            decrypted_data = fernet.decrypt(encrypted_data)
        except Exception as e:
            logger.error(f"Decryption failed for file {file_id}", exc_info=True)
            raise http_400("Decryption failed - invalid passphrase")

        # Generate thumbnail
        thumbnail = service.generate_thumbnail(decrypted_data, max_size=(200, 200))

        if not thumbnail:
            raise http_500("Thumbnail generation failed")

        return Response(content=thumbnail, media_type="image/jpeg")

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to generate thumbnail for file {file_id}", exc_info=True)
        raise http_500("Failed to generate thumbnail")


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
            raise http_429("Rate limit exceeded. Max 120 downloads per minute")

        user_id = get_user_id(current_user)

        if vault_type not in ('real', 'decoy'):
            raise http_400("vault_type must be 'real' or 'decoy'")

        if not vault_passphrase:
            raise http_400("vault_passphrase is required")

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
            raise http_404("File not found", resource="file")

        # SECURITY: Path containment check - ensure file is within vault directory
        vault_files_dir = service.files_path.resolve()
        encrypted_file_path = Path(file_row['encrypted_path']).resolve()

        if not str(encrypted_file_path).startswith(str(vault_files_dir)):
            logger.error(f"SECURITY: Path traversal attempt: {file_row['encrypted_path']}")
            raise http_403("Invalid file path")

        if not encrypted_file_path.exists():
            raise http_404("Encrypted file not found on disk", resource="file")

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
        raise http_500("Failed to decrypt and download file")
