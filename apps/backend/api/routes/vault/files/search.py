"""
Vault Files Search & Analytics Routes

Handles file search and analytics:
- Advanced file search with filters
- Storage trends analytics
- Access patterns analytics
- Activity timeline

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
import sqlite3
from typing import Dict, List, Any
from fastapi import APIRouter, HTTPException, Request, Depends, status
from pydantic import BaseModel

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from api.auth_middleware import get_current_user
from api.utils import get_user_id
from api.services.vault.core import get_vault_service
from api.rate_limiter import get_client_ip, rate_limiter
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/vault", tags=["vault-search"])


class SearchResultsResponse(BaseModel):
    """Search results with pagination"""
    results: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int
    has_more: bool


class StorageTrendItem(BaseModel):
    """Storage trend data point"""
    date: str
    files_added: int
    bytes_added: int


class StorageTrendsResponse(BaseModel):
    """Storage usage trends"""
    trends: List[StorageTrendItem]
    total_files: int
    total_bytes: int
    days: int


class AccessedFile(BaseModel):
    """File access information"""
    id: str
    filename: str
    mime_type: str
    file_size: int
    access_count: int
    last_accessed: str | None


class AccessPatternsResponse(BaseModel):
    """File access patterns"""
    most_accessed: List[AccessedFile]
    access_by_type: Dict[str, int]
    recent_access_24h: int


class ActivityItem(BaseModel):
    """Activity timeline item"""
    action: str
    resource_type: str
    resource_id: str
    details: str | None
    timestamp: str


class ActivityTimelineResponse(BaseModel):
    """Activity timeline"""
    activities: List[ActivityItem]
    action_summary: Dict[str, int]
    hours: int
    total_activities: int


@router.get(
    "/search",
    response_model=SuccessResponse[SearchResultsResponse],
    status_code=status.HTTP_200_OK,
    name="vault_search_files",
    summary="Search files",
    description="Advanced file search with filters and pagination (rate limited: 60 requests/minute)"
)
async def search_files_endpoint(
    request: Request,
    vault_type: str = "real",
    query: str = None,
    mime_type: str = None,
    tags: str = None,
    date_from: str = None,
    date_to: str = None,
    min_size: int = None,
    max_size: int = None,
    folder_path: str = None,
    limit: int = 100,
    offset: int = 0,
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[SearchResultsResponse]:
    """
    Advanced file search with pagination

    Args:
        vault_type: 'real' or 'decoy' (default: 'real')
        query: Search query (filename or content)
        mime_type: Filter by MIME type
        tags: Comma-separated tags to filter by
        date_from: Start date filter (ISO format)
        date_to: End date filter (ISO format)
        min_size: Minimum file size in bytes
        max_size: Maximum file size in bytes
        folder_path: Filter by folder path
        limit: Results per page (default: 100)
        offset: Results offset (default: 0)

    Returns:
        Paginated search results

    Rate limit: 60 requests per minute per user
    """
    try:
        # Rate limiting: 60 requests per minute per user
        ip = get_client_ip(request)
        key = f"vault:search:{get_user_id(current_user)}:{ip}"
        if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=ErrorResponse(
                    error_code=ErrorCode.RATE_LIMITED,
                    message="Rate limit exceeded. Max 60 searches per minute"
                ).model_dump()
            )

        service = get_vault_service()
        user_id = get_user_id(current_user)

        # Parse tags if provided
        tags_list = tags.split(",") if tags else None

        all_results = service.search_files(
            user_id, vault_type, query, mime_type, tags_list,
            date_from, date_to, min_size, max_size, folder_path
        )

        # Apply pagination
        total = len(all_results)
        results = all_results[offset:offset + limit]
        has_more = (offset + limit) < total

        result_data = SearchResultsResponse(
            results=results,
            total=total,
            limit=limit,
            offset=offset,
            has_more=has_more
        )

        return SuccessResponse(
            data=result_data,
            message=f"Found {total} file{'s' if total != 1 else ''}"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to search files", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to search files"
            ).model_dump()
        )


@router.get(
    "/analytics/storage-trends",
    response_model=SuccessResponse[StorageTrendsResponse],
    status_code=status.HTTP_200_OK,
    name="vault_get_storage_trends",
    summary="Get storage trends",
    description="Get storage usage trends over time (rate limited: 120 requests/minute)"
)
async def get_storage_trends(
    request: Request,
    vault_type: str = "real",
    days: int = 30,
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[StorageTrendsResponse]:
    """
    Get storage usage trends over time

    Args:
        vault_type: 'real' or 'decoy' (default: 'real')
        days: Number of days to analyze (1-365, default: 30)

    Returns:
        Daily storage trends with totals

    Rate limit: 120 requests per minute per user
    """
    try:
        # Rate limiting: 120 requests per minute per user
        ip = get_client_ip(request)
        key = f"vault:analytics:storage:{get_user_id(current_user)}:{ip}"
        if not rate_limiter.check_rate_limit(key, max_requests=120, window_seconds=60):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=ErrorResponse(
                    error_code=ErrorCode.RATE_LIMITED,
                    message="Rate limit exceeded. Max 120 requests per minute"
                ).model_dump()
            )

        user_id = get_user_id(current_user)
        service = get_vault_service()

        if vault_type not in ('real', 'decoy'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="vault_type must be 'real' or 'decoy'"
                ).model_dump()
            )

        if days < 1 or days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="days must be between 1 and 365"
                ).model_dump()
            )

        conn = sqlite3.connect(str(service.db_path))
        cursor = conn.cursor()

        try:
            # Daily storage growth
            cursor.execute("""
                SELECT
                    DATE(created_at) as date,
                    COUNT(*) as files_added,
                    SUM(file_size) as bytes_added
                FROM vault_files
                WHERE user_id = ? AND vault_type = ? AND is_deleted = 0
                  AND created_at >= datetime('now', '-' || ? || ' days')
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """, (user_id, vault_type, days))

            trends = []
            for row in cursor.fetchall():
                trends.append(StorageTrendItem(
                    date=row[0],
                    files_added=row[1],
                    bytes_added=row[2] or 0
                ))

            # Get current totals
            cursor.execute("""
                SELECT COUNT(*), COALESCE(SUM(file_size), 0)
                FROM vault_files
                WHERE user_id = ? AND vault_type = ? AND is_deleted = 0
            """, (user_id, vault_type))

            total_row = cursor.fetchone()
            total_files = total_row[0]
            total_bytes = total_row[1]

            result_data = StorageTrendsResponse(
                trends=trends,
                total_files=total_files,
                total_bytes=total_bytes,
                days=days
            )

            return SuccessResponse(
                data=result_data,
                message=f"Retrieved {days}-day storage trends"
            )

        finally:
            conn.close()

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get storage trends", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve storage trends"
            ).model_dump()
        )


@router.get(
    "/analytics/access-patterns",
    response_model=SuccessResponse[AccessPatternsResponse],
    status_code=status.HTTP_200_OK,
    name="vault_get_access_patterns",
    summary="Get access patterns",
    description="Get file access patterns and most accessed files (rate limited: 120 requests/minute)"
)
async def get_access_patterns(
    request: Request,
    vault_type: str = "real",
    limit: int = 10,
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[AccessPatternsResponse]:
    """
    Get file access patterns and most accessed files

    Args:
        vault_type: 'real' or 'decoy' (default: 'real')
        limit: Number of most-accessed files to return (default: 10)

    Returns:
        Access patterns including most accessed files, access by type, and recent activity

    Rate limit: 120 requests per minute per user
    """
    try:
        # Rate limiting: 120 requests per minute per user
        ip = get_client_ip(request)
        key = f"vault:analytics:access:{get_user_id(current_user)}:{ip}"
        if not rate_limiter.check_rate_limit(key, max_requests=120, window_seconds=60):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=ErrorResponse(
                    error_code=ErrorCode.RATE_LIMITED,
                    message="Rate limit exceeded. Max 120 requests per minute"
                ).model_dump()
            )

        user_id = get_user_id(current_user)
        service = get_vault_service()

        if vault_type not in ('real', 'decoy'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="vault_type must be 'real' or 'decoy'"
                ).model_dump()
            )

        conn = sqlite3.connect(str(service.db_path))
        cursor = conn.cursor()

        try:
            # Most accessed files
            cursor.execute("""
                SELECT
                    f.id,
                    f.filename,
                    f.mime_type,
                    f.file_size,
                    COUNT(a.id) as access_count,
                    MAX(a.accessed_at) as last_accessed
                FROM vault_files f
                LEFT JOIN vault_file_access_logs a ON f.id = a.file_id
                WHERE f.user_id = ? AND f.vault_type = ? AND f.is_deleted = 0
                GROUP BY f.id
                ORDER BY access_count DESC
                LIMIT ?
            """, (user_id, vault_type, limit))

            most_accessed = []
            for row in cursor.fetchall():
                most_accessed.append(AccessedFile(
                    id=row[0],
                    filename=row[1],
                    mime_type=row[2],
                    file_size=row[3],
                    access_count=row[4],
                    last_accessed=row[5]
                ))

            # Access by type
            cursor.execute("""
                SELECT
                    access_type,
                    COUNT(*) as count
                FROM vault_file_access_logs
                WHERE user_id = ? AND vault_type = ?
                GROUP BY access_type
            """, (user_id, vault_type))

            access_by_type = {}
            for row in cursor.fetchall():
                access_by_type[row[0]] = row[1]

            # Recent access activity (last 24 hours)
            cursor.execute("""
                SELECT COUNT(*)
                FROM vault_file_access_logs
                WHERE user_id = ? AND vault_type = ?
                  AND accessed_at >= datetime('now', '-1 day')
            """, (user_id, vault_type))

            recent_access_count = cursor.fetchone()[0]

            result_data = AccessPatternsResponse(
                most_accessed=most_accessed,
                access_by_type=access_by_type,
                recent_access_24h=recent_access_count
            )

            return SuccessResponse(
                data=result_data,
                message="Retrieved access patterns"
            )

        finally:
            conn.close()

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get access patterns", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve access patterns"
            ).model_dump()
        )


@router.get(
    "/analytics/activity-timeline",
    response_model=SuccessResponse[ActivityTimelineResponse],
    status_code=status.HTTP_200_OK,
    name="vault_get_activity_timeline",
    summary="Get activity timeline",
    description="Get recent activity timeline (rate limited: 120 requests/minute)"
)
async def get_activity_timeline(
    request: Request,
    vault_type: str = "real",
    hours: int = 24,
    limit: int = 50,
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[ActivityTimelineResponse]:
    """
    Get recent activity timeline

    Args:
        vault_type: 'real' or 'decoy' (default: 'real')
        hours: Number of hours to look back (default: 24)
        limit: Maximum activities to return (default: 50)

    Returns:
        Recent activities with action summary

    Rate limit: 120 requests per minute per user
    """
    try:
        # Rate limiting: 120 requests per minute per user
        ip = get_client_ip(request)
        key = f"vault:analytics:activity:{get_user_id(current_user)}:{ip}"
        if not rate_limiter.check_rate_limit(key, max_requests=120, window_seconds=60):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=ErrorResponse(
                    error_code=ErrorCode.RATE_LIMITED,
                    message="Rate limit exceeded. Max 120 requests per minute"
                ).model_dump()
            )

        user_id = get_user_id(current_user)
        service = get_vault_service()

        if vault_type not in ('real', 'decoy'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="vault_type must be 'real' or 'decoy'"
                ).model_dump()
            )

        conn = sqlite3.connect(str(service.db_path))
        cursor = conn.cursor()

        try:
            # Get recent audit logs
            cursor.execute("""
                SELECT
                    action,
                    resource_type,
                    resource_id,
                    details,
                    created_at
                FROM vault_audit_logs
                WHERE user_id = ? AND vault_type = ?
                  AND created_at >= datetime('now', '-' || ? || ' hours')
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, vault_type, hours, limit))

            activities = []
            for row in cursor.fetchall():
                activities.append(ActivityItem(
                    action=row[0],
                    resource_type=row[1],
                    resource_id=row[2],
                    details=row[3],
                    timestamp=row[4]
                ))

            # Get activity summary
            cursor.execute("""
                SELECT
                    action,
                    COUNT(*) as count
                FROM vault_audit_logs
                WHERE user_id = ? AND vault_type = ?
                  AND created_at >= datetime('now', '-' || ? || ' hours')
                GROUP BY action
            """, (user_id, vault_type, hours))

            action_summary = {}
            for row in cursor.fetchall():
                action_summary[row[0]] = row[1]

            result_data = ActivityTimelineResponse(
                activities=activities,
                action_summary=action_summary,
                hours=hours,
                total_activities=len(activities)
            )

            return SuccessResponse(
                data=result_data,
                message=f"Retrieved {len(activities)} activities from last {hours} hours"
            )

        finally:
            conn.close()

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get activity timeline", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve activity timeline"
            ).model_dump()
        )
