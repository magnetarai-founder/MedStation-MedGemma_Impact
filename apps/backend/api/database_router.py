"""
Database Encryption API Router
Exposes endpoints for database encryption and backup codes
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/database", tags=["database-encryption"])


class BackupCode(BaseModel):
    code: str
    used: bool


class BackupCodeResponse(BaseModel):
    codes: list[BackupCode]
    total: int
    unused: int


class EncryptionStatus(BaseModel):
    encrypted: bool
    algorithm: str
    key_derivation: str
    iterations: int


@router.get("/status", response_model=EncryptionStatus)
async def get_encryption_status():
    """
    Get database encryption status

    Returns encryption algorithm and key derivation info
    """
    try:
        from database_encryption_service import get_database_service

        service = get_database_service()

        return EncryptionStatus(
            encrypted=True,
            algorithm="AES-256-GCM",
            key_derivation="PBKDF2-SHA256",
            iterations=600000
        )
    except ImportError:
        raise HTTPException(status_code=503, detail="Database encryption service not available")
    except Exception as e:
        logger.error(f"Error getting encryption status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backup-codes", response_model=list[BackupCode])
async def get_backup_codes():
    """
    Get all backup codes (used and unused)

    Returns list of backup codes with usage status
    """
    try:
        from database_encryption_service import get_database_service

        service = get_database_service()
        codes = service.get_backup_codes()

        result = []
        for code_data in codes:
            result.append(BackupCode(
                code=code_data["code"],
                used=code_data["used"]
            ))

        return result
    except ImportError:
        raise HTTPException(status_code=503, detail="Database encryption service not available")
    except Exception as e:
        logger.error(f"Error getting backup codes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backup-codes/regenerate", response_model=BackupCodeResponse)
async def regenerate_backup_codes():
    """
    Regenerate all backup codes

    WARNING: This invalidates all existing codes!

    Returns new set of backup codes
    """
    try:
        from database_encryption_service import get_database_service

        service = get_database_service()
        new_codes = service.regenerate_backup_codes()

        codes = []
        for code in new_codes:
            codes.append(BackupCode(code=code, used=False))

        return BackupCodeResponse(
            codes=codes,
            total=len(codes),
            unused=len(codes)
        )
    except ImportError:
        raise HTTPException(status_code=503, detail="Database encryption service not available")
    except Exception as e:
        logger.error(f"Error regenerating backup codes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backup-codes/verify")
async def verify_backup_code(code: str):
    """
    Verify a backup code

    Args:
        code: The backup code to verify

    Returns success if code is valid and unused
    """
    try:
        from database_encryption_service import get_database_service

        service = get_database_service()
        valid = service.verify_backup_code(code)

        if not valid:
            raise HTTPException(status_code=401, detail="Invalid or already used backup code")

        return {"success": True, "message": "Backup code verified"}
    except ImportError:
        raise HTTPException(status_code=503, detail="Database encryption service not available")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying backup code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backup-codes/{code}/use")
async def use_backup_code(code: str):
    """
    Mark a backup code as used

    Args:
        code: The backup code to mark as used

    Returns success if code was marked as used
    """
    try:
        from database_encryption_service import get_database_service

        service = get_database_service()
        success = service.use_backup_code(code)

        if not success:
            raise HTTPException(status_code=404, detail="Backup code not found or already used")

        return {"success": True, "message": "Backup code marked as used"}
    except ImportError:
        raise HTTPException(status_code=503, detail="Database encryption service not available")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error using backup code: {e}")
        raise HTTPException(status_code=500, detail=str(e))
