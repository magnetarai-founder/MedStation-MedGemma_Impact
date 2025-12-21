"""
Admin router for ElohimOS - Danger Zone administrative operations.

Thin router that delegates to api/services/admin.py for business logic.
Uses lazy imports in endpoints to avoid circular dependencies.

AUTH-P4: All endpoints now protected with @require_perm decorators to prevent
unauthorized access to dangerous operations.

AUTH-P5: All operations now audited to audit.db for security accountability.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from api.permissions import require_perm
from api.audit_helper import record_audit_event
from api.audit_logger import AuditAction
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# Helper to get current user without importing at module level
def get_current_user_dep() -> Any:
    """Lazy import of get_current_user dependency"""
    from api.auth_middleware import get_current_user
    return get_current_user


# Response models
class AdminOperationResponse(BaseModel):
    """Response for admin operations"""
    success: bool
    message: str
    details: dict = {}


# AUTH-P4: Tightened per AUTH-P4 - Extreme danger zone operations
# These operations are destructive and irreversible - require system.manage_settings permission
# Only founder_rights and explicitly granted admins can access

@router.post(
    "/reset-all",
    response_model=SuccessResponse[AdminOperationResponse],
    status_code=status.HTTP_200_OK,
    name="admin_reset_all",
    summary="Reset all data (DANGER)",
    description="Reset all app data - clears database and temp files (requires system.manage_settings)"
)
@require_perm("system.manage_settings")
async def admin_reset_all_endpoint(
    request: Request,
    current_user: dict = Depends(get_current_user_dep)
) -> SuccessResponse[AdminOperationResponse]:
    """
    Reset all app data - clears database and temp files (DANGER ZONE)

    ⚠️ WARNING: This operation is destructive and irreversible

    Returns:
        Success confirmation with operation details
    """
    from api.services import admin
    import logging
    logger = logging.getLogger(__name__)

    try:
        result = await admin.reset_all_data()
        # AUTH-P5: Audit this dangerous operation
        record_audit_event(
            user_id=current_user.get('user_id', 'system'),
            action=AuditAction.ADMIN_RESET_ALL,
            resource='system',
            details={'status': 'success'}
        )

        return SuccessResponse(
            data=AdminOperationResponse(
                success=result.get("success", True),
                message=result.get("message", "All data reset successfully"),
                details=result
            ),
            message="All app data has been reset"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Reset all failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to reset all data"
            ).model_dump()
        )


@router.post(
    "/uninstall",
    response_model=SuccessResponse[AdminOperationResponse],
    status_code=status.HTTP_200_OK,
    name="admin_uninstall",
    summary="Uninstall app (DANGER)",
    description="Uninstall app - removes all data directories (requires system.manage_settings)"
)
@require_perm("system.manage_settings")
async def admin_uninstall_endpoint(
    request: Request,
    current_user: dict = Depends(get_current_user_dep)
) -> SuccessResponse[AdminOperationResponse]:
    """
    Uninstall app - removes all data directories (DANGER ZONE)

    ⚠️ WARNING: This operation is destructive and irreversible

    Returns:
        Success confirmation with operation details
    """
    from api.services import admin
    import logging
    logger = logging.getLogger(__name__)

    try:
        result = await admin.uninstall_app()
        record_audit_event(
            user_id=current_user.get('user_id', 'system'),
            action=AuditAction.ADMIN_UNINSTALL,
            resource='system',
            details={'status': 'success'}
        )

        return SuccessResponse(
            data=AdminOperationResponse(
                success=result.get("success", True),
                message=result.get("message", "App uninstalled successfully"),
                details=result
            ),
            message="App has been uninstalled"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Uninstall failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to uninstall app"
            ).model_dump()
        )


@router.post(
    "/clear-chats",
    response_model=SuccessResponse[AdminOperationResponse],
    status_code=status.HTTP_200_OK,
    name="admin_clear_chats",
    summary="Clear AI chat history (DANGER)",
    description="Clear all AI chat history (requires system.manage_settings)"
)
@require_perm("system.manage_settings")
async def admin_clear_chats_endpoint(
    request: Request,
    current_user: dict = Depends(get_current_user_dep)
) -> SuccessResponse[AdminOperationResponse]:
    """
    Clear all AI chat history (DANGER ZONE)

    ⚠️ WARNING: This operation is destructive and irreversible

    Returns:
        Success confirmation with operation details
    """
    from api.services import admin
    import logging
    logger = logging.getLogger(__name__)

    try:
        result = await admin.clear_chats()
        record_audit_event(
            user_id=current_user.get('user_id', 'system'),
            action=AuditAction.ADMIN_CLEAR_CHATS,
            resource='chats',
            details={'status': 'success'}
        )

        return SuccessResponse(
            data=AdminOperationResponse(
                success=result.get("success", True),
                message=result.get("message", "AI chat history cleared successfully"),
                details=result
            ),
            message="AI chat history has been cleared"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Clear chats failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to clear AI chat history"
            ).model_dump()
        )


@router.post(
    "/clear-team-messages",
    response_model=SuccessResponse[AdminOperationResponse],
    status_code=status.HTTP_200_OK,
    name="admin_clear_team_messages",
    summary="Clear team chat history (DANGER)",
    description="Clear P2P team chat history (requires system.manage_settings)"
)
@require_perm("system.manage_settings")
async def admin_clear_team_messages_endpoint(
    request: Request,
    current_user: dict = Depends(get_current_user_dep)
) -> SuccessResponse[AdminOperationResponse]:
    """
    Clear P2P team chat history (DANGER ZONE)

    ⚠️ WARNING: This operation is destructive and irreversible

    Returns:
        Success confirmation with operation details
    """
    from api.services import admin
    import logging
    logger = logging.getLogger(__name__)

    try:
        result = await admin.clear_team_messages()
        record_audit_event(
            user_id=current_user.get('user_id', 'system'),
            action=AuditAction.ADMIN_CLEAR_TEAM_MESSAGES,
            resource='team_messages',
            details={'status': 'success'}
        )

        return SuccessResponse(
            data=AdminOperationResponse(
                success=result.get("success", True),
                message=result.get("message", "Team chat history cleared successfully"),
                details=result
            ),
            message="Team chat history has been cleared"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Clear team messages failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to clear team chat history"
            ).model_dump()
        )


@router.post(
    "/clear-query-library",
    response_model=SuccessResponse[AdminOperationResponse],
    status_code=status.HTTP_200_OK,
    name="admin_clear_query_library",
    summary="Clear query library (DANGER)",
    description="Clear all saved SQL queries (requires system.manage_settings)"
)
@require_perm("system.manage_settings")
async def admin_clear_query_library_endpoint(
    request: Request,
    current_user: dict = Depends(get_current_user_dep)
) -> SuccessResponse[AdminOperationResponse]:
    """
    Clear all saved SQL queries (DANGER ZONE)

    ⚠️ WARNING: This operation is destructive and irreversible

    Returns:
        Success confirmation with operation details
    """
    from api.services import admin
    import logging
    logger = logging.getLogger(__name__)

    try:
        result = await admin.clear_query_library()
        record_audit_event(
            user_id=current_user.get('user_id', 'system'),
            action=AuditAction.ADMIN_CLEAR_QUERY_LIBRARY,
            resource='query_library',
            details={'status': 'success'}
        )

        return SuccessResponse(
            data=AdminOperationResponse(
                success=result.get("success", True),
                message=result.get("message", "Query library cleared successfully"),
                details=result
            ),
            message="Query library has been cleared"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Clear query library failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to clear query library"
            ).model_dump()
        )


@router.post(
    "/clear-query-history",
    response_model=SuccessResponse[AdminOperationResponse],
    status_code=status.HTTP_200_OK,
    name="admin_clear_query_history",
    summary="Clear query history (DANGER)",
    description="Clear SQL execution history (requires system.manage_settings)"
)
@require_perm("system.manage_settings")
async def admin_clear_query_history_endpoint(
    request: Request,
    current_user: dict = Depends(get_current_user_dep)
) -> SuccessResponse[AdminOperationResponse]:
    """
    Clear SQL execution history (DANGER ZONE)

    ⚠️ WARNING: This operation is destructive and irreversible

    Returns:
        Success confirmation with operation details
    """
    from api.services import admin
    import logging
    logger = logging.getLogger(__name__)

    try:
        result = await admin.clear_query_history()
        record_audit_event(
            user_id=current_user.get('user_id', 'system'),
            action=AuditAction.ADMIN_CLEAR_QUERY_HISTORY,
            resource='query_history',
            details={'status': 'success'}
        )

        return SuccessResponse(
            data=AdminOperationResponse(
                success=result.get("success", True),
                message=result.get("message", "Query history cleared successfully"),
                details=result
            ),
            message="Query history has been cleared"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Clear query history failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to clear query history"
            ).model_dump()
        )


@router.post(
    "/clear-temp-files",
    response_model=SuccessResponse[AdminOperationResponse],
    status_code=status.HTTP_200_OK,
    name="admin_clear_temp_files",
    summary="Clear temporary files",
    description="Clear uploaded files and exports (requires system.manage_settings)"
)
@require_perm("system.manage_settings")
async def admin_clear_temp_files_endpoint(
    request: Request,
    current_user: dict = Depends(get_current_user_dep)
) -> SuccessResponse[AdminOperationResponse]:
    """
    Clear uploaded files and exports

    Returns:
        Success confirmation with operation details
    """
    from api.services import admin
    import logging
    logger = logging.getLogger(__name__)

    try:
        result = await admin.clear_temp_files()
        record_audit_event(
            user_id=current_user.get('user_id', 'system'),
            action=AuditAction.ADMIN_CLEAR_TEMP_FILES,
            resource='temp_files',
            details={'status': 'success'}
        )

        return SuccessResponse(
            data=AdminOperationResponse(
                success=result.get("success", True),
                message=result.get("message", "Temporary files cleared successfully"),
                details=result
            ),
            message="Temporary files have been cleared"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Clear temp files failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to clear temporary files"
            ).model_dump()
        )


@router.post(
    "/clear-code-files",
    response_model=SuccessResponse[AdminOperationResponse],
    status_code=status.HTTP_200_OK,
    name="admin_clear_code_files",
    summary="Clear code editor files",
    description="Clear saved code editor files (requires system.manage_settings)"
)
@require_perm("system.manage_settings")
async def admin_clear_code_files_endpoint(
    request: Request,
    current_user: dict = Depends(get_current_user_dep)
) -> SuccessResponse[AdminOperationResponse]:
    """
    Clear saved code editor files

    Returns:
        Success confirmation with operation details
    """
    from api.services import admin
    import logging
    logger = logging.getLogger(__name__)

    try:
        result = await admin.clear_code_files()
        record_audit_event(
            user_id=current_user.get('user_id', 'system'),
            action=AuditAction.ADMIN_CLEAR_CODE_FILES,
            resource='code_files',
            details={'status': 'success'}
        )

        return SuccessResponse(
            data=AdminOperationResponse(
                success=result.get("success", True),
                message=result.get("message", "Code editor files cleared successfully"),
                details=result
            ),
            message="Code editor files have been cleared"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Clear code files failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to clear code editor files"
            ).model_dump()
        )


@router.post(
    "/reset-settings",
    response_model=SuccessResponse[AdminOperationResponse],
    status_code=status.HTTP_200_OK,
    name="admin_reset_settings",
    summary="Reset settings (DANGER)",
    description="Reset all settings to defaults (requires system.manage_settings)"
)
@require_perm("system.manage_settings")
async def admin_reset_settings_endpoint(
    request: Request,
    current_user: dict = Depends(get_current_user_dep)
) -> SuccessResponse[AdminOperationResponse]:
    """
    Reset all settings to defaults (DANGER ZONE)

    ⚠️ WARNING: This operation is destructive and irreversible

    Returns:
        Success confirmation with operation details
    """
    from api.services import admin
    import logging
    logger = logging.getLogger(__name__)

    try:
        result = await admin.reset_settings()
        record_audit_event(
            user_id=current_user.get('user_id', 'system'),
            action=AuditAction.ADMIN_RESET_SETTINGS,
            resource='settings',
            details={'status': 'success'}
        )

        return SuccessResponse(
            data=AdminOperationResponse(
                success=result.get("success", True),
                message=result.get("message", "Settings reset successfully"),
                details=result
            ),
            message="Settings have been reset to defaults"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Reset settings failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to reset settings"
            ).model_dump()
        )


@router.post(
    "/reset-data",
    response_model=SuccessResponse[AdminOperationResponse],
    status_code=status.HTTP_200_OK,
    name="admin_reset_data",
    summary="Reset data (DANGER)",
    description="Delete all data but keep settings (requires system.manage_settings)"
)
@require_perm("system.manage_settings")
async def admin_reset_data_endpoint(
    request: Request,
    current_user: dict = Depends(get_current_user_dep)
) -> SuccessResponse[AdminOperationResponse]:
    """
    Delete all data but keep settings (DANGER ZONE)

    ⚠️ WARNING: This operation is destructive and irreversible

    Returns:
        Success confirmation with operation details
    """
    from api.services import admin
    import logging
    logger = logging.getLogger(__name__)

    try:
        result = await admin.reset_data()
        record_audit_event(
            user_id=current_user.get('user_id', 'system'),
            action=AuditAction.ADMIN_RESET_DATA,
            resource='data',
            details={'status': 'success'}
        )

        return SuccessResponse(
            data=AdminOperationResponse(
                success=result.get("success", True),
                message=result.get("message", "Data reset successfully"),
                details=result
            ),
            message="All data has been reset (settings preserved)"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Reset data failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to reset data"
            ).model_dump()
        )


# AUTH-P4: Export operations require data.export permission
# AUTH-P5: All export operations audited
@router.post(
    "/export-all",
    response_model=SuccessResponse[AdminOperationResponse],
    status_code=status.HTTP_200_OK,
    name="admin_export_all",
    summary="Export complete backup",
    description="Export complete backup as ZIP (requires data.export permission)"
)
@require_perm("data.export")
async def admin_export_all_endpoint(
    request: Request,
    current_user: dict = Depends(get_current_user_dep)
) -> SuccessResponse[AdminOperationResponse]:
    """
    Export complete backup as ZIP

    Requires data.export permission

    Returns:
        Success confirmation with export details
    """
    from api.services import admin
    import logging
    logger = logging.getLogger(__name__)

    try:
        result = await admin.export_all_data(current_user)
        record_audit_event(
            user_id=current_user.get('user_id', 'system'),
            action=AuditAction.ADMIN_EXPORT_ALL,
            resource='backup',
            details={'type': 'full', 'format': 'zip'}
        )

        return SuccessResponse(
            data=AdminOperationResponse(
                success=result.get("success", True),
                message=result.get("message", "Complete backup exported successfully"),
                details=result
            ),
            message="Complete backup has been exported"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Export all failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to export complete backup"
            ).model_dump()
        )


@router.post(
    "/export-chats",
    response_model=SuccessResponse[AdminOperationResponse],
    status_code=status.HTTP_200_OK,
    name="admin_export_chats",
    summary="Export AI chat history",
    description="Export AI chat history as JSON (requires data.export permission)"
)
@require_perm("data.export")
async def admin_export_chats_endpoint(
    request: Request,
    current_user: dict = Depends(get_current_user_dep)
) -> SuccessResponse[AdminOperationResponse]:
    """
    Export AI chat history as JSON

    Requires data.export permission

    Returns:
        Success confirmation with export details
    """
    from api.services import admin
    import logging
    logger = logging.getLogger(__name__)

    try:
        result = await admin.export_chats()
        record_audit_event(
            user_id=current_user.get('user_id', 'system'),
            action=AuditAction.ADMIN_EXPORT_CHATS,
            resource='chats',
            details={'type': 'chats', 'format': 'json'}
        )

        return SuccessResponse(
            data=AdminOperationResponse(
                success=result.get("success", True),
                message=result.get("message", "AI chat history exported successfully"),
                details=result
            ),
            message="AI chat history has been exported"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Export chats failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to export AI chat history"
            ).model_dump()
        )


@router.post(
    "/export-queries",
    response_model=SuccessResponse[AdminOperationResponse],
    status_code=status.HTTP_200_OK,
    name="admin_export_queries",
    summary="Export query library",
    description="Export query library as JSON (requires data.export permission)"
)
@require_perm("data.export")
async def admin_export_queries_endpoint(
    request: Request,
    current_user: dict = Depends(get_current_user_dep)
) -> SuccessResponse[AdminOperationResponse]:
    """
    Export query library as JSON

    Requires data.export permission

    Returns:
        Success confirmation with export details
    """
    from api.services import admin
    import logging
    logger = logging.getLogger(__name__)

    try:
        result = await admin.export_queries()
        record_audit_event(
            user_id=current_user.get('user_id', 'system'),
            action=AuditAction.ADMIN_EXPORT_QUERIES,
            resource='queries',
            details={'type': 'queries', 'format': 'json'}
        )

        return SuccessResponse(
            data=AdminOperationResponse(
                success=result.get("success", True),
                message=result.get("message", "Query library exported successfully"),
                details=result
            ),
            message="Query library has been exported"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Export queries failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to export query library"
            ).model_dump()
        )
