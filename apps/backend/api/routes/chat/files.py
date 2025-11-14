"""
Chat Files Routes - File attachment handling
"""

"""
"""
import logging
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request, Depends, Query, Body
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
# Module-level safe imports
    from api.auth_middleware import get_current_user
    from api.permission_engine import require_perm_team
    # Fallback for standalone execution
    from auth_middleware import get_current_user
    from permission_engine import require_perm_team
# Authenticated router (requires auth for most chat operations)

router = APIRouter()


