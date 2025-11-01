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
USER_DB_PATH = PATHS.data_dir / "users.db"
USER_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

from fastapi import Depends
from auth_middleware import get_current_user

router = APIRouter(
    prefix="/api/v1/users",
    tags=["Users"],
    dependencies=[Depends(get_current_user)]  # Require auth
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


class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    device_name: Optional[str] = None
    avatar_color: Optional[str] = None
    bio: Optional[str] = None


# ===== Database =====

def init_db():
    """Initialize the users database"""
    conn = sqlite3.connect(USER_DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            device_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            avatar_color TEXT,
            bio TEXT,
            role TEXT DEFAULT 'member',
            role_changed_at TEXT,
            role_changed_by TEXT
        )
    """)

    # Migrate existing users table if role column doesn't exist
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'role' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'member'")
        cursor.execute("ALTER TABLE users ADD COLUMN role_changed_at TEXT")
        cursor.execute("ALTER TABLE users ADD COLUMN role_changed_by TEXT")

        # Set first user as super_admin
        cursor.execute("SELECT user_id FROM users LIMIT 1")
        first_user = cursor.fetchone()
        if first_user:
            cursor.execute("""
                UPDATE users
                SET role = 'super_admin', role_changed_at = ?
                WHERE user_id = ?
            """, (datetime.utcnow().isoformat(), first_user[0]))
            logger.info(f"Migrated first user to super_admin: {first_user[0]}")

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
    Get the current user or create one if none exists.
    ElohimOS is single-user per device, so we store one user profile.
    """
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users LIMIT 1")
    row = cursor.fetchone()

    if row:
        conn.close()
        return UserProfile(
            user_id=row[0],
            display_name=row[1],
            device_name=row[2],
            created_at=row[3],
            avatar_color=row[4],
            bio=row[5],
            role=row[6] if len(row) > 6 else "member",
            role_changed_at=row[7] if len(row) > 7 else None,
            role_changed_by=row[8] if len(row) > 8 else None
        )

    # Create new user
    user_id = str(uuid.uuid4())
    display_name = "Field Worker"
    device_name = os.uname().nodename if hasattr(os, 'uname') else "ElohimOS Device"
    created_at = datetime.utcnow().isoformat()
    avatar_color = "#3b82f6"  # Default blue

    cursor.execute("""
        INSERT INTO users (user_id, display_name, device_name, created_at, avatar_color, role)
        VALUES (?, ?, ?, ?, ?, 'super_admin')
    """, (user_id, display_name, device_name, created_at, avatar_color))

    conn.commit()
    conn.close()

    logger.info(f"Created new user: {user_id} ({display_name})")

    return UserProfile(
        user_id=user_id,
        display_name=display_name,
        device_name=device_name,
        created_at=created_at,
        avatar_color=avatar_color,
        role="super_admin"
    )


def update_user_profile(updates: Dict[str, Any]) -> UserProfile:
    """Update the user profile"""
    user = get_or_create_user()

    conn = get_conn()
    cursor = conn.cursor()

    # Build UPDATE query dynamically
    update_fields = []
    values = []

    if 'display_name' in updates:
        update_fields.append("display_name = ?")
        values.append(updates['display_name'])

    if 'device_name' in updates:
        update_fields.append("device_name = ?")
        values.append(updates['device_name'])

    if 'avatar_color' in updates:
        update_fields.append("avatar_color = ?")
        values.append(updates['avatar_color'])

    if 'bio' in updates:
        update_fields.append("bio = ?")
        values.append(updates['bio'])

    if update_fields:
        values.append(user.user_id)
        query = f"UPDATE users SET {', '.join(update_fields)} WHERE user_id = ?"
        cursor.execute(query, values)
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
    """Reset user identity (for testing/dev)"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users")
    conn.commit()
    conn.close()

    # Create new user
    new_user = get_or_create_user()
    return {"message": "User identity reset", "user": new_user}
