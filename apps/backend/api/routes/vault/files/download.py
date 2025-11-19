"""
Vault Files Download Routes

Handles file download operations:
- File download with decryption
- Thumbnail generation for images
"""

import logging
import sqlite3
from pathlib import Path
from typing import Dict
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import FileResponse, Response
from cryptography.fernet import Fernet

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from auth_middleware import get_current_user
from api.services.vault.core import get_vault_service
from api.rate_limiter import get_client_ip, rate_limiter
from api.audit_logger import get_audit_logger

logger = logging.getLogger(__name__)
audit_logger = get_audit_logger()

router = APIRouter()


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
