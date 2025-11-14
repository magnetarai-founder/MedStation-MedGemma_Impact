"""
Vault Sharing Routes - Share/unshare/ACL management
"""

"""
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
# Import WebSocket connection manager
    from api.websocket_manager import manager
    # Fallback if module structure changes

router = APIRouter()


