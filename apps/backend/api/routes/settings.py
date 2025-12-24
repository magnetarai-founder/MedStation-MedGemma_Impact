"""
Application Settings Routes

Provides endpoints for managing user application settings.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, Depends, status
from pydantic import BaseModel

from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

try:
    from api.auth_middleware import get_current_user, User
except ImportError:
    from api.auth_middleware import get_current_user, User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/settings",
    tags=["settings"]
)

# Import shared instances and functions from main.py
def get_app_settings() -> Any:
    from api import main
    return main.app_settings

def set_app_settings(settings) -> None:
    import api.main as main
    main.app_settings = settings

def get_save_app_settings() -> Any:
    from api import main
    return main.save_app_settings

def get_elohimos_memory() -> Any:
    from api import main
    return main.elohimos_memory

# Models
class AppSettings(BaseModel):
    # Performance & Memory
    max_file_size_mb: int = 1000
    enable_chunked_processing: bool = True
    chunk_size_rows: int = 50000
    app_memory_percent: int = 35
    processing_memory_percent: int = 50
    cache_memory_percent: int = 15

    # Default Download Options
    sql_default_format: str = "excel"
    json_default_format: str = "excel"
    json_auto_safe: bool = True
    json_max_depth: int = 5
    json_flatten_arrays: bool = False
    json_preserve_nulls: bool = True

    # Naming Patterns
    naming_pattern_global: str = "{name}_{YYYYMMDD}"
    naming_pattern_sql_excel: str | None = None
    naming_pattern_sql_csv: str | None = None
    naming_pattern_sql_tsv: str | None = None
    naming_pattern_sql_parquet: str | None = None
    naming_pattern_sql_json: str | None = None
    naming_pattern_json_excel: str | None = None
    naming_pattern_json_csv: str | None = None
    naming_pattern_json_tsv: str | None = None
    naming_pattern_json_parquet: str | None = None

    # Automation & Workflows
    automation_enabled: bool = True
    auto_save_interval_seconds: int = 300
    auto_backup_enabled: bool = True
    workflow_execution_enabled: bool = True

    # Database Performance
    database_cache_size_mb: int = 256
    max_query_timeout_seconds: int = 300
    enable_query_optimization: bool = True

    # Power User Features
    enable_semantic_search: bool = False
    semantic_similarity_threshold: float = 0.7
    show_keyboard_shortcuts: bool = False
    enable_bulk_operations: bool = False

    # Session
    session_timeout_hours: int = 24
    clear_temp_on_close: bool = True

@router.get(
    "",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    name="get_settings",
    summary="Get settings",
    description="Get current application settings"
)
async def get_settings(
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict[str, Any]]:
    """Get current app settings"""
    try:
        app_settings = get_app_settings()
        return SuccessResponse(
            data=app_settings.dict(),
            message="Settings retrieved successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get settings", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve settings"
            ).model_dump()
        )

@router.post(
    "",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    name="update_settings",
    summary="Update settings",
    description="Update application settings"
)
async def update_settings(
    request: Request,
    settings: AppSettings,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict[str, Any]]:
    """Update app settings"""
    try:
        set_app_settings(settings)
        save_func = get_save_app_settings()
        save_func(settings)

        return SuccessResponse(
            data={"settings": settings.dict()},
            message="Settings updated successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to update settings", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to update settings"
            ).model_dump()
        )

@router.get(
    "/memory-status",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    name="get_memory_status",
    summary="Get memory status",
    description="Get current memory usage and allocation"
)
async def get_memory_status(
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict[str, Any]]:
    """Get current memory usage and allocation"""
    try:
        app_settings = get_app_settings()

        try:
            import psutil
            process = psutil.Process()
            mem_info = process.memory_info()
            system_mem = psutil.virtual_memory()

            data = {
                "process_memory_mb": mem_info.rss / (1024 * 1024),
                "system_total_mb": system_mem.total / (1024 * 1024),
                "system_available_mb": system_mem.available / (1024 * 1024),
                "system_percent_used": system_mem.percent,
                "settings": {
                    "app_percent": app_settings.app_memory_percent,
                    "processing_percent": app_settings.processing_memory_percent,
                    "cache_percent": app_settings.cache_memory_percent,
                }
            }
            message = "Memory status retrieved successfully"

        except ImportError:
            data = {
                "psutil_available": False,
                "settings": {
                    "app_percent": app_settings.app_memory_percent,
                    "processing_percent": app_settings.processing_memory_percent,
                    "cache_percent": app_settings.cache_memory_percent,
                }
            }
            message = "Memory status retrieved (psutil not available)"

        return SuccessResponse(
            data=data,
            message=message
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get memory status", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve memory status"
            ).model_dump()
        )
