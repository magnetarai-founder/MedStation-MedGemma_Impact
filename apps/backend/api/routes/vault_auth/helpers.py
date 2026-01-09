"""
Vault Auth - Helper Functions

Session management, rate limiting, and audit logging.
"""

import secrets
import sqlite3
import time
from datetime import datetime
from typing import Dict, Any

from api.config_paths import get_config_paths
from api.rate_limiter import rate_limiter

# Database path
PATHS = get_config_paths()
VAULT_DB_PATH = PATHS.data_dir / "vault.db"

# Rate limiting for unlock attempts
UNLOCK_RATE_LIMIT = 5  # attempts
UNLOCK_WINDOW_SECONDS = 300  # 5 minutes

# In-memory session storage for unlocked vaults (KEK is kept in memory)
# Format: {(user_id, vault_id): {'kek': bytes, 'vault_type': str, 'unlocked_at': timestamp}}
vault_sessions: Dict[tuple, Dict[str, Any]] = {}


def check_rate_limit(user_id: str, vault_id: str, client_ip: str) -> bool:
    """Check unlock rate limit (5 attempts per 5 minutes)"""
    # Runtime import to allow test mocking via api.routes.vault_auth.rate_limiter
    from api.routes import vault_auth as pkg
    rate_key = f"vault_unlock:{user_id}:{vault_id}:{client_ip}"
    return pkg.rate_limiter.check_rate_limit(
        rate_key,
        max_requests=UNLOCK_RATE_LIMIT,
        window_seconds=UNLOCK_WINDOW_SECONDS
    )


def record_unlock_attempt(user_id: str, vault_id: str, success: bool, method: str) -> None:
    """Record unlock attempt for audit"""
    # Runtime import to allow test mocking via api.routes.vault_auth.VAULT_DB_PATH
    from api.routes import vault_auth as pkg
    with sqlite3.connect(str(pkg.VAULT_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO vault_unlock_attempts (id, user_id, vault_id, attempt_time, success, method)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            secrets.token_urlsafe(16),
            user_id,
            vault_id,
            datetime.now().isoformat(),
            1 if success else 0,
            method
        ))
        conn.commit()


def get_session(user_id: str, vault_id: str) -> Dict[str, Any] | None:
    """Get vault session if it exists and is valid (< 1 hour old)"""
    session_key = (user_id, vault_id)
    if session_key in vault_sessions:
        session = vault_sessions[session_key]
        if time.time() - session['unlocked_at'] < 3600:
            return session
        else:
            # Session expired
            del vault_sessions[session_key]
    return None


def create_session(user_id: str, vault_id: str, kek: bytes, vault_type: str) -> str:
    """Create a new vault session, returns session_id"""
    session_id = secrets.token_urlsafe(32)
    vault_sessions[(user_id, vault_id)] = {
        'kek': kek,
        'vault_type': vault_type,
        'unlocked_at': time.time(),
        'session_id': session_id
    }
    return session_id


def delete_session(user_id: str, vault_id: str) -> bool:
    """Delete vault session, returns True if session existed"""
    session_key = (user_id, vault_id)
    if session_key in vault_sessions:
        del vault_sessions[session_key]
        return True
    return False


# Backwards compatibility aliases (underscore-prefixed)
_check_rate_limit = check_rate_limit
_record_unlock_attempt = record_unlock_attempt
