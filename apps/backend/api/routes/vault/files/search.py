"""
Vault Files Search & Analytics Routes

Handles file search and analytics:
- Advanced file search with filters
- Storage trends analytics
- Access patterns analytics
- Activity timeline
"""

import logging
import sqlite3
from typing import Dict
from fastapi import APIRouter, HTTPException, Request, Depends

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from auth_middleware import get_current_user
from api.services.vault.core import get_vault_service
from api.rate_limiter import get_client_ip, rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/search")
async def search_files_endpoint(
    request: Request,
    vault_type: str = "real",
    query: str = None,
    mime_type: str = None,
    tags: str = None,  # Comma-separated tags
    date_from: str = None,
    date_to: str = None,
    min_size: int = None,
    max_size: int = None,
    folder_path: str = None,
    limit: int = 100,
    offset: int = 0,
    current_user: Dict = Depends(get_current_user)
):
    """Advanced file search with pagination"""
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:search:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.search")

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
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

        return {
            "results": results,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": has_more
        }
    except Exception as e:
        logger.error(f"Failed to search files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/storage-trends")
async def get_storage_trends(
    request: Request,
    vault_type: str = "real",
    days: int = 30,
    current_user: Dict = Depends(get_current_user)
):
    """Get storage usage trends over time"""
    # Rate limiting: 120 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:analytics:storage:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=120, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.analytics.storage")

    user_id = current_user["user_id"]
    service = get_vault_service()

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="days must be between 1 and 365")

    import sqlite3
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
            trends.append({
                "date": row[0],
                "files_added": row[1],
                "bytes_added": row[2] or 0
            })

        # Get current totals
        cursor.execute("""
            SELECT COUNT(*), COALESCE(SUM(file_size), 0)
            FROM vault_files
            WHERE user_id = ? AND vault_type = ? AND is_deleted = 0
        """, (user_id, vault_type))

        total_row = cursor.fetchone()
        total_files = total_row[0]
        total_bytes = total_row[1]

        return {
            "trends": trends,
            "total_files": total_files,
            "total_bytes": total_bytes,
            "days": days
        }
    finally:
        conn.close()


@router.get("/analytics/access-patterns")
async def get_access_patterns(
    request: Request,
    vault_type: str = "real",
    limit: int = 10,
    current_user: Dict = Depends(get_current_user)
):
    """Get file access patterns and most accessed files"""
    # Rate limiting: 120 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:analytics:access:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=120, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.analytics.access")

    user_id = current_user["user_id"]
    service = get_vault_service()

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    import sqlite3
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
            most_accessed.append({
                "id": row[0],
                "filename": row[1],
                "mime_type": row[2],
                "file_size": row[3],
                "access_count": row[4],
                "last_accessed": row[5]
            })

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

        return {
            "most_accessed": most_accessed,
            "access_by_type": access_by_type,
            "recent_access_24h": recent_access_count
        }
    finally:
        conn.close()


@router.get("/analytics/activity-timeline")
async def get_activity_timeline(
    request: Request,
    vault_type: str = "real",
    hours: int = 24,
    limit: int = 50,
    current_user: Dict = Depends(get_current_user)
):
    """Get recent activity timeline"""
    # Rate limiting: 120 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:analytics:activity:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=120, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.analytics.activity")

    user_id = current_user["user_id"]
    service = get_vault_service()

    if vault_type not in ('real', 'decoy'):
        raise HTTPException(status_code=400, detail="vault_type must be 'real' or 'decoy'")

    import sqlite3
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
            activities.append({
                "action": row[0],
                "resource_type": row[1],
                "resource_id": row[2],
                "details": row[3],
                "timestamp": row[4]
            })

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

        return {
            "activities": activities,
            "action_summary": action_summary,
            "hours": hours,
            "total_activities": len(activities)
        }
    finally:
        conn.close()
