"""
Vault Folders Routes - Folder create/list/navigate/delete operations
"""

import logging
from typing import List, Dict
from fastapi import APIRouter, HTTPException, Form, Depends

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from auth_middleware import get_current_user
from api.services.vault.core import get_vault_service
from api.services.vault.schemas import VaultFolder

logger = logging.getLogger(__name__)

router = APIRouter()


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
