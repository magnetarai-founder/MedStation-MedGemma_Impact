"""
Admin router for ElohimOS - Danger Zone administrative operations.

Thin router that delegates to api/services/admin.py for business logic.
Uses lazy imports in endpoints to avoid circular dependencies.

AUTH-P4: All endpoints now protected with @require_perm decorators to prevent
unauthorized access to dangerous operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from api.permissions import require_perm

router = APIRouter(tags=["admin"])


# Helper to get current user without importing at module level
def get_current_user_dep():
    """Lazy import of get_current_user dependency"""
    from api.auth_middleware import get_current_user
    return get_current_user


# AUTH-P4: Tightened per AUTH-P4 - Extreme danger zone operations
# These operations are destructive and irreversible - require system.manage_settings permission
# Only founder_rights and explicitly granted admins can access

@router.post("/reset-all", name="admin_reset_all")
@require_perm("system.manage_settings")
async def admin_reset_all_endpoint(request: Request, current_user: dict = Depends(get_current_user_dep)):
    """Reset all app data - clears database and temp files (DANGER ZONE)"""
    from api.services import admin
    try:
        return await admin.reset_all_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")


@router.post("/uninstall", name="admin_uninstall")
@require_perm("system.manage_settings")
async def admin_uninstall_endpoint(request: Request, current_user: dict = Depends(get_current_user_dep)):
    """Uninstall app - removes all data directories (DANGER ZONE)"""
    from api.services import admin
    try:
        return await admin.uninstall_app()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Uninstall failed: {str(e)}")


@router.post("/clear-chats", name="admin_clear_chats")
@require_perm("system.manage_settings")
async def admin_clear_chats_endpoint(request: Request, current_user: dict = Depends(get_current_user_dep)):
    """Clear all AI chat history (DANGER ZONE)"""
    from api.services import admin
    try:
        return await admin.clear_chats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear chats failed: {str(e)}")


@router.post("/clear-team-messages", name="admin_clear_team_messages")
@require_perm("system.manage_settings")
async def admin_clear_team_messages_endpoint(request: Request, current_user: dict = Depends(get_current_user_dep)):
    """Clear P2P team chat history (DANGER ZONE)"""
    from api.services import admin
    try:
        return await admin.clear_team_messages()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear team messages failed: {str(e)}")


@router.post("/clear-query-library", name="admin_clear_query_library")
@require_perm("system.manage_settings")
async def admin_clear_query_library_endpoint(request: Request, current_user: dict = Depends(get_current_user_dep)):
    """Clear all saved SQL queries (DANGER ZONE)"""
    from api.services import admin
    try:
        return await admin.clear_query_library()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear library failed: {str(e)}")


@router.post("/clear-query-history", name="admin_clear_query_history")
@require_perm("system.manage_settings")
async def admin_clear_query_history_endpoint(request: Request, current_user: dict = Depends(get_current_user_dep)):
    """Clear SQL execution history (DANGER ZONE)"""
    from api.services import admin
    try:
        return await admin.clear_query_history()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear history failed: {str(e)}")


@router.post("/clear-temp-files", name="admin_clear_temp_files")
@require_perm("system.manage_settings")
async def admin_clear_temp_files_endpoint(request: Request, current_user: dict = Depends(get_current_user_dep)):
    """Clear uploaded files and exports"""
    from api.services import admin
    try:
        return await admin.clear_temp_files()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear temp failed: {str(e)}")


@router.post("/clear-code-files", name="admin_clear_code_files")
@require_perm("system.manage_settings")
async def admin_clear_code_files_endpoint(request: Request, current_user: dict = Depends(get_current_user_dep)):
    """Clear saved code editor files"""
    from api.services import admin
    try:
        return await admin.clear_code_files()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear code failed: {str(e)}")


@router.post("/reset-settings", name="admin_reset_settings")
@require_perm("system.manage_settings")
async def admin_reset_settings_endpoint(request: Request, current_user: dict = Depends(get_current_user_dep)):
    """Reset all settings to defaults (DANGER ZONE)"""
    from api.services import admin
    try:
        return await admin.reset_settings()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset settings failed: {str(e)}")


@router.post("/reset-data", name="admin_reset_data")
@require_perm("system.manage_settings")
async def admin_reset_data_endpoint(request: Request, current_user: dict = Depends(get_current_user_dep)):
    """Delete all data but keep settings (DANGER ZONE)"""
    from api.services import admin
    try:
        return await admin.reset_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset data failed: {str(e)}")


# AUTH-P4: Export operations require data.export permission
@router.post("/export-all", name="admin_export_all")
@require_perm("data.export")
async def admin_export_all_endpoint(request: Request, current_user: dict = Depends(get_current_user_dep)):
    """Export complete backup as ZIP (requires data.export permission)"""
    from api.services import admin
    try:
        return await admin.export_all_data(current_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/export-chats", name="admin_export_chats")
@require_perm("data.export")
async def admin_export_chats_endpoint(request: Request, current_user: dict = Depends(get_current_user_dep)):
    """Export AI chat history as JSON"""
    from api.services import admin
    try:
        return await admin.export_chats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export chats failed: {str(e)}")


@router.post("/export-queries", name="admin_export_queries")
@require_perm("data.export")
async def admin_export_queries_endpoint(request: Request, current_user: dict = Depends(get_current_user_dep)):
    """Export query library as JSON"""
    from api.services import admin
    try:
        return await admin.export_queries()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export queries failed: {str(e)}")
