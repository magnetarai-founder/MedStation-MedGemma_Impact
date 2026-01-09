"""
Cloud Auth - Helper Functions

Token generation, hashing, rate limiting, and audit logging.
"""

import hashlib
import secrets
import sqlite3
import base64
import logging
from datetime import datetime, UTC

from api.rate_limiter import rate_limiter

from api.routes.cloud_auth.db import get_db_path
from api.routes.cloud_auth.models import PAIRING_RATE_LIMIT, PAIRING_WINDOW_SECONDS

logger = logging.getLogger(__name__)


def hash_token(token: str) -> str:
    """Hash token for secure storage using SHA-256"""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_cloud_device_id(user_id: str, device_fingerprint: str) -> str:
    """Generate deterministic cloud device ID from user and device fingerprint"""
    combined = f"{user_id}:{device_fingerprint}"
    hash_bytes = hashlib.sha256(combined.encode()).digest()
    return base64.urlsafe_b64encode(hash_bytes[:16]).decode().rstrip('=')


def generate_cloud_token() -> str:
    """Generate a secure cloud token"""
    return secrets.token_urlsafe(48)


def check_pairing_rate_limit(user_id: str, client_ip: str) -> bool:
    """Check cloud pairing rate limit (5 attempts per hour)"""
    rate_key = f"cloud_pair:{user_id}:{client_ip}"
    return rate_limiter.check_rate_limit(
        rate_key,
        max_requests=PAIRING_RATE_LIMIT,
        window_seconds=PAIRING_WINDOW_SECONDS
    )


def log_sync_operation(
    cloud_device_id: str,
    operation: str,
    success: bool,
    details: str = None
) -> None:
    """Log a sync operation for audit"""
    try:
        with sqlite3.connect(str(get_db_path())) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cloud_sync_log (id, cloud_device_id, operation, timestamp, success, details)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                secrets.token_urlsafe(16),
                cloud_device_id,
                operation,
                datetime.now(UTC).isoformat(),
                1 if success else 0,
                details
            ))
            conn.commit()
    except Exception as e:
        logger.warning(f"Failed to log sync operation: {e}")
