"""
User-related Pydantic models for MedStation API.
"""

from typing import Optional
from pydantic import BaseModel


class UserProfile(BaseModel):
    """User profile model"""
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
    """Update payload for user profile"""
    display_name: Optional[str] = None
    device_name: Optional[str] = None
    avatar_color: Optional[str] = None
    bio: Optional[str] = None
    job_role: Optional[str] = None
