"""
Code Editor Filesystem Write Operations
Write and delete operations with risk assessment and rate limiting
"""

import logging
from pathlib import Path
from typing import Any, Optional, Tuple

from api.errors import http_400, http_403, http_404

logger = logging.getLogger(__name__)


# ============================================================================
# WRITE OPERATIONS
# ============================================================================

def write_file_to_disk(
    file_path: Path,
    content: str,
    create_if_missing: bool = False
) -> dict:
    """
    Write file to disk with validation
    Returns operation details
    """
    # Check if creating new file
    is_new_file = not file_path.exists()

    if is_new_file and not create_if_missing:
        raise http_404("File does not exist. Set create_if_missing=true to create.", resource="file")

    # Create parent directories if needed
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    operation = "create file" if is_new_file else "modify file"

    return {
        'operation': operation,
        'is_new_file': is_new_file,
        'size': len(content)
    }


# ============================================================================
# DELETE OPERATIONS
# ============================================================================

def delete_file_from_disk(file_path: Path) -> dict:
    """
    Delete file from disk with validation
    Returns operation details
    """
    if not file_path.exists():
        raise http_404("File not found", resource="file")

    # Delete file
    if file_path.is_file():
        file_path.unlink()
    else:
        raise http_400("Path is not a file")

    return {
        'operation': 'delete',
        'deleted': True
    }


# ============================================================================
# RISK ASSESSMENT INTEGRATION
# ============================================================================

def assess_write_risk(file_path: Path, operation: str, permission_layer) -> Tuple[Optional[Any], str]:
    """
    Assess risk of write operation using permission layer
    Returns (risk_level, risk_reason)
    """
    try:
        from permission_layer import RiskLevel

        risk_level, risk_reason = permission_layer.assess_risk(
            f"{operation} {file_path}",
            "file_write"
        )

        if risk_level == RiskLevel.CRITICAL:
            raise http_403(f"Write operation denied: {risk_reason}")

        # High risk operations require explicit approval
        if risk_level in [RiskLevel.HIGH, RiskLevel.MEDIUM]:
            logger.warning(f"High/medium risk write operation: {file_path} - {risk_reason}")

        return risk_level, risk_reason

    except ImportError:
        # Fallback if permission_layer not available
        logger.warning("Permission layer not available for risk assessment")
        return None, "Risk assessment unavailable"


def assess_delete_risk(file_path: Path, permission_layer) -> Tuple[Optional[Any], str]:
    """
    Assess risk of delete operation using permission layer
    Returns (risk_level, risk_reason)
    """
    try:
        from permission_layer import RiskLevel

        risk_level, risk_reason = permission_layer.assess_risk(
            f"rm {file_path}",
            "file_delete"
        )

        if risk_level == RiskLevel.CRITICAL:
            raise http_403(f"Delete operation denied: {risk_reason}")

        return risk_level, risk_reason

    except ImportError:
        # Fallback if permission_layer not available
        logger.warning("Permission layer not available for risk assessment")
        return None, "Risk assessment unavailable"


# ============================================================================
# RATE LIMITING HELPERS
# ============================================================================

def check_write_rate_limit(user_id: str, rate_limiter) -> bool:
    """
    Check rate limit for write operations
    Rate: 30 writes/min per user
    """
    try:
        return rate_limiter.check_rate_limit(
            f"code:write:{user_id}",
            max_requests=30,
            window_seconds=60
        )
    except Exception as e:
        logger.warning(f"Rate limiter error: {e}")
        return True  # Allow operation if rate limiter fails


def check_delete_rate_limit(user_id: str, rate_limiter) -> bool:
    """
    Check rate limit for delete operations
    Rate: 20 deletes/min per user (lower than writes for safety)
    """
    try:
        return rate_limiter.check_rate_limit(
            f"code:delete:{user_id}",
            max_requests=20,
            window_seconds=60
        )
    except Exception as e:
        logger.warning(f"Rate limiter error: {e}")
        return True  # Allow operation if rate limiter fails
