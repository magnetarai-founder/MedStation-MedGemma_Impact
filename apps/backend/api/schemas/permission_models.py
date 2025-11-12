"""
Permission-related Pydantic models for ElohimOS API.

Models for RBAC system including permissions, profiles, and permission sets.
"""

from typing import Optional
from pydantic import BaseModel


class PermissionModel(BaseModel):
    """Permission model"""
    permission_id: str
    permission_key: str
    permission_name: str
    permission_description: Optional[str] = None
    category: str
    subcategory: Optional[str] = None
    permission_type: str  # "boolean", "level", "scope"
    is_system: bool = False
    created_at: str


class PermissionProfileModel(BaseModel):
    """Permission profile model"""
    profile_id: str
    profile_name: str
    profile_description: Optional[str] = None
    team_id: Optional[str] = None
    applies_to_role: Optional[str] = None
    created_by: Optional[str] = None
    created_at: str
    modified_at: str
    is_active: bool = True


class ProfilePermissionGrant(BaseModel):
    """Permission grant for a profile"""
    permission_id: str
    is_granted: bool = True
    permission_level: Optional[str] = None  # "none", "read", "write", "admin"
    permission_scope: Optional[dict] = None


class CreateProfileRequest(BaseModel):
    """Request to create a permission profile"""
    profile_name: str
    profile_description: Optional[str] = None
    team_id: Optional[str] = None
    applies_to_role: Optional[str] = None


class UpdateProfileRequest(BaseModel):
    """Request to update a permission profile"""
    profile_name: Optional[str] = None
    profile_description: Optional[str] = None
    is_active: Optional[bool] = None


class PermissionSetModel(BaseModel):
    """Permission set model"""
    permission_set_id: str
    set_name: str
    set_description: Optional[str] = None
    team_id: Optional[str] = None
    created_by: Optional[str] = None
    created_at: str
    is_active: bool = True


class CreatePermissionSetRequest(BaseModel):
    """Request to create a permission set"""
    set_name: str
    set_description: Optional[str] = None
    team_id: Optional[str] = None


class AssignProfileRequest(BaseModel):
    """Request to assign a profile to a user"""
    user_id: str


class AssignPermissionSetRequest(BaseModel):
    """Request to assign a permission set to a user"""
    user_id: str
    expires_at: Optional[str] = None


class PermissionSetGrant(BaseModel):
    """Permission set grant model (Phase 2.5)"""
    permission_id: str
    is_granted: bool = True
    permission_level: Optional[str] = None  # "none", "read", "write", "admin"
    permission_scope: Optional[str] = None  # JSON string
