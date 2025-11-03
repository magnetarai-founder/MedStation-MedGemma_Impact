"""
User Identity Service

Simple UUID-based user identity system.
Stores user profile locally for offline-first operation.
"""

import os
import json
import uuid
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Storage paths - use centralized config_paths
from config_paths import get_config_paths
PATHS = get_config_paths()
# Phase 0: Use app_db for user_profiles (consolidated from legacy users.db)
USER_DB_PATH = PATHS.app_db
USER_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

from fastapi import Depends
from auth_middleware import get_current_user_optional

# Public router for offline-first user management (no auth required for single-user system)
router = APIRouter(
    prefix="/api/v1/users",
    tags=["Users"]
)


# ===== Models =====

class UserProfile(BaseModel):
    user_id: str
    display_name: str
    device_name: str
    created_at: str
    avatar_color: Optional[str] = None
    bio: Optional[str] = None
    role: Optional[str] = "member"
    role_changed_at: Optional[str] = None
    role_changed_by: Optional[str] = None
    job_role: Optional[str] = "unassigned"


class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    device_name: Optional[str] = None
    avatar_color: Optional[str] = None
    bio: Optional[str] = None
    job_role: Optional[str] = None


# ===== Database =====

def init_db():
    """
    Initialize the user_profiles table in app_db

    Phase 0: user_profiles table stores profile data, separate from auth.users
    which stores authentication credentials and roles.
    """
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


def get_conn():
    """Get database connection"""
    return sqlite3.connect(USER_DB_PATH)


# Initialize database on module load
init_db()


# ===== User Management =====

def get_or_create_user() -> UserProfile:
    """
    Get the current user profile or create one if none exists.

    Phase 0: Reads profile from user_profiles table, role/job_role from auth.users
    """
    conn = get_conn()
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
        return UserProfile(
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

    # No profile exists - create a default one
    # Note: This should typically not happen in Phase 0 multi-user system
    # as profiles should be created during registration
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

    return UserProfile(
        user_id=user_id,
        display_name=display_name,
        device_name=device_name,
        created_at=created_at,
        avatar_color=avatar_color,
        role="member",
        job_role="unassigned"
    )


def update_user_profile(updates: Dict[str, Any]) -> UserProfile:
    """
    Update the user profile

    Phase 0: Updates user_profiles table for profile fields, auth.users for job_role
    """
    user = get_or_create_user()

    conn = get_conn()
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

    # Return updated user
    return get_or_create_user()


# ===== API Endpoints =====

@router.get("/me", response_model=UserProfile)
async def get_current_user():
    """Get or create the current user profile"""
    return get_or_create_user()


@router.put("/me", response_model=UserProfile)
async def update_current_user(request: Request, updates: UserProfileUpdate):
    """Update the current user profile"""
    return update_user_profile(updates.dict(exclude_unset=True))


@router.post("/reset")
async def reset_user(request: Request):
    """Reset user profile (for testing/dev) - Phase 0: only clears profiles, not auth"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_profiles")
    conn.commit()
    conn.close()

    # Create new user profile
    new_user = get_or_create_user()
    return {"message": "User profile reset", "user": new_user}
