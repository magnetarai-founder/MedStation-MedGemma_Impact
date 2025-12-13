"""
User service layer for ElohimOS - User profile management.

Contains business logic for user operations with lazy imports to avoid cycles.
All functions use lazy imports to break circular dependencies.
"""

import os
import uuid
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


async def get_or_create_user_profile():
    """
    Get the current user profile or create one if none exists.

    Returns UserProfile model with user data from user_profiles + auth.users tables.
    Cached for 10 minutes to reduce database load.
    """
    # Lazy imports to avoid cycles
    from config_paths import get_config_paths
    from api.schemas.user_models import UserProfile
    from api.cache_service import get_cache

    # Check cache first (10 minute TTL)
    cache = get_cache()
    cache_key = "user:profile:current"
    cached_profile = cache.get(cache_key)

    if cached_profile is not None:
        logger.debug("✅ User profile from cache")
        # Reconstruct UserProfile from cached dict
        return UserProfile(**cached_profile)

    PATHS = get_config_paths()
    USER_DB_PATH = PATHS.app_db

    conn = sqlite3.connect(USER_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Join user_profiles with auth.users to get role and job_role
    cursor.execute("""
        SELECT
            p.user_id,
            p.display_name,
            p.device_name,
            p.created_at,
            p.avatar_color,
            p.bio,
            u.role,
            p.role_changed_at,
            p.role_changed_by,
            u.job_role
        FROM user_profiles p
        LEFT JOIN users u ON p.user_id = u.user_id
        LIMIT 1
    """)
    row = cursor.fetchone()

    if row:
        conn.close()
        profile = UserProfile(
            user_id=row['user_id'],
            display_name=row['display_name'],
            device_name=row['device_name'],
            created_at=row['created_at'],
            avatar_color=row['avatar_color'],
            bio=row['bio'],
            role=row['role'] or "member",
            role_changed_at=row['role_changed_at'],
            role_changed_by=row['role_changed_by'],
            job_role=row['job_role'] or "unassigned"
        )

        # Cache for 10 minutes
        cache.set(cache_key, profile.dict(), ttl=600)
        logger.debug("🔄 Cached user profile")

        return profile

    # No profile exists - create a default one
    user_id = str(uuid.uuid4())
    display_name = "Field Worker"
    device_name = os.uname().nodename if hasattr(os, 'uname') else "ElohimOS Device"
    created_at = datetime.utcnow().isoformat()
    avatar_color = "#3b82f6"  # Default blue

    cursor.execute("""
        INSERT INTO user_profiles (user_id, display_name, device_name, created_at, avatar_color)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, display_name, device_name, created_at, avatar_color))

    conn.commit()
    conn.close()

    logger.info(f"Created new user profile: {user_id} ({display_name})")

    new_profile = UserProfile(
        user_id=user_id,
        display_name=display_name,
        device_name=device_name,
        created_at=created_at,
        avatar_color=avatar_color,
        role="member",
        job_role="unassigned"
    )

    # Cache the newly created profile
    cache.set(cache_key, new_profile.dict(), ttl=600)
    logger.debug("🔄 Cached new user profile")

    return new_profile


async def update_user_profile(updates: Dict[str, Any]):
    """
    Update the user profile.

    Updates user_profiles table for profile fields, auth.users for job_role.
    """
    # Lazy imports
    from config_paths import get_config_paths

    PATHS = get_config_paths()
    USER_DB_PATH = PATHS.app_db

    # Get current user first
    user = await get_or_create_user_profile()

    conn = sqlite3.connect(USER_DB_PATH)
    cursor = conn.cursor()

    # Build UPDATE query for user_profiles table
    profile_fields = []
    profile_values = []

    if 'display_name' in updates:
        profile_fields.append("display_name = ?")
        profile_values.append(updates['display_name'])

    if 'device_name' in updates:
        profile_fields.append("device_name = ?")
        profile_values.append(updates['device_name'])

    if 'avatar_color' in updates:
        profile_fields.append("avatar_color = ?")
        profile_values.append(updates['avatar_color'])

    if 'bio' in updates:
        profile_fields.append("bio = ?")
        profile_values.append(updates['bio'])

    if profile_fields:
        profile_values.append(user.user_id)
        query = f"UPDATE user_profiles SET {', '.join(profile_fields)} WHERE user_id = ?"
        cursor.execute(query, profile_values)

    # Update job_role in auth.users table
    if 'job_role' in updates:
        cursor.execute("""
            UPDATE users SET job_role = ? WHERE user_id = ?
        """, (updates['job_role'], user.user_id))

    conn.commit()
    conn.close()

    # Invalidate cache since profile was updated
    from api.cache_service import get_cache
    cache = get_cache()
    cache.delete("user:profile:current")
    logger.debug("🗑️  Invalidated user profile cache after update")

    # Return updated user
    return await get_or_create_user_profile()


async def reset_user_profile():
    """
    Reset user profile (for testing/dev).

    Phase 0: Only clears profiles, not auth credentials.
    """
    # Lazy imports
    from config_paths import get_config_paths

    PATHS = get_config_paths()
    USER_DB_PATH = PATHS.app_db

    conn = sqlite3.connect(USER_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_profiles")
    conn.commit()
    conn.close()

    # Create new user profile
    new_user = await get_or_create_user_profile()
    return {"message": "User profile reset", "user": new_user}


def init_user_db():
    """
    Initialize the user_profiles table in app_db.

    Called on module import to ensure table exists.
    """
    try:
        from api.config_paths import get_config_paths
    except ImportError:
        from config_paths import get_config_paths

    PATHS = get_config_paths()
    USER_DB_PATH = PATHS.app_db
    USER_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(USER_DB_PATH)
    cursor = conn.cursor()

    # Create user_profiles table (not 'users' - that's for auth)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            device_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            avatar_color TEXT,
            bio TEXT,
            role_changed_at TEXT,
            role_changed_by TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


# Initialize database on module load
init_user_db()
