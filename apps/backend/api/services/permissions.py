"""
Permissions Service - Thin Façade over api.permissions.admin

This module provides async service functions for RBAC management.
The implementation now lives in api.permissions.admin.

This module delegates all calls to the permissions package while maintaining
backwards compatibility for existing imports.

Extracted from permissions_admin.py endpoints during Phase 3 migration.
Refactored into thin façade during Phase 6.1 modularization.
"""

from typing import Dict, List, Optional, Any

# Import admin functions from permissions package
from api.permissions import admin as perm_admin


# ===== Permission Registry Functions =====

async def get_all_permissions(category: Optional[str] = None) -> List[Dict]:
    """
    Get all permissions from the registry.

    Args:
        category: Optional filter by category (feature, resource, system)

    Returns:
        List of permission dictionaries
    """
    return await perm_admin.get_all_permissions(category)


# ===== Profile Management Functions =====

async def get_all_profiles() -> List[Dict]:
    """
    Get all permission profiles.

    Returns:
        List of profile dictionaries
    """
    return await perm_admin.get_all_profiles()


async def create_profile(
    name: str,
    description: str,
    role_baseline: str,
    scope: str = "system",
    team_id: Optional[str] = None
) -> Dict:
    """
    Create a new permission profile.

    Args:
        name: Profile name
        description: Profile description
        role_baseline: Base role (admin, member, guest)
        scope: system or team (default: system)
        team_id: Team ID if scope is team

    Returns:
        Created profile dictionary
    """
    return await perm_admin.create_profile(name, description, role_baseline, scope, team_id)


async def get_profile(profile_id: str) -> Optional[Dict]:
    """
    Get a specific profile by ID.

    Args:
        profile_id: Profile identifier

    Returns:
        Profile dictionary or None if not found
    """
    return await perm_admin.get_profile(profile_id)


async def update_profile(
    profile_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    role_baseline: Optional[str] = None
) -> Dict:
    """
    Update profile metadata.

    Args:
        profile_id: Profile identifier
        name: New name
        description: New description
        role_baseline: New role baseline

    Returns:
        Updated profile dictionary
    """
    return await perm_admin.update_profile(profile_id, name, description, role_baseline)


async def update_profile_grants(profile_id: str, grants: Dict[str, Any]) -> None:
    """
    Upsert permission grants for a profile.

    Args:
        profile_id: Profile identifier
        grants: Dictionary of permission_key -> value mappings
    """
    return await perm_admin.update_profile_grants(profile_id, grants)


async def get_profile_grants(profile_id: str) -> Dict[str, Any]:
    """
    Get all permission grants for a profile.

    Args:
        profile_id: Profile identifier

    Returns:
        Dictionary of permission_key -> value mappings
    """
    return await perm_admin.get_profile_grants(profile_id)


# ===== User Assignment Functions =====

async def assign_profile_to_user(
    user_id: str,
    profile_id: str,
    team_id: Optional[str] = None
) -> None:
    """
    Assign a profile to a user.

    Args:
        user_id: User identifier
        profile_id: Profile identifier
        team_id: Optional team context
    """
    return await perm_admin.assign_profile_to_user(user_id, profile_id, team_id)


async def unassign_profile_from_user(
    user_id: str,
    profile_id: str,
    team_id: Optional[str] = None
) -> None:
    """
    Remove a profile from a user.

    Args:
        user_id: User identifier
        profile_id: Profile identifier
        team_id: Optional team context
    """
    return await perm_admin.unassign_profile_from_user(user_id, profile_id, team_id)


async def get_user_profiles(user_id: str, team_id: Optional[str] = None) -> List[Dict]:
    """
    Get all profiles assigned to a user.

    Args:
        user_id: User identifier
        team_id: Optional team filter

    Returns:
        List of assigned profile dictionaries
    """
    return await perm_admin.get_user_profiles(user_id, team_id)


# ===== Permission Set Functions =====

async def get_all_permission_sets(team_id: Optional[str] = None) -> List[Dict]:
    """
    Get all permission sets.

    Args:
        team_id: Optional team filter

    Returns:
        List of permission set dictionaries
    """
    return await perm_admin.get_all_permission_sets(team_id)


async def create_permission_set(
    name: str,
    description: str,
    scope: str = "system",
    team_id: Optional[str] = None
) -> Dict:
    """
    Create a new permission set.

    Args:
        name: Set name
        description: Set description
        scope: system or team (default: system)
        team_id: Team ID if scope is team

    Returns:
        Created permission set dictionary
    """
    return await perm_admin.create_permission_set(name, description, scope, team_id)


async def assign_permission_set_to_user(
    user_id: str,
    set_id: str,
    team_id: Optional[str] = None
) -> None:
    """
    Assign a permission set to a user.

    Args:
        user_id: User identifier
        set_id: Permission set identifier
        team_id: Optional team context
    """
    return await perm_admin.assign_permission_set_to_user(user_id, set_id, team_id)


async def unassign_permission_set_from_user(
    user_id: str,
    set_id: str,
    team_id: Optional[str] = None
) -> None:
    """
    Remove a permission set from a user.

    Args:
        user_id: User identifier
        set_id: Permission set identifier
        team_id: Optional team context
    """
    return await perm_admin.unassign_permission_set_from_user(user_id, set_id, team_id)


async def update_permission_set_grants(set_id: str, grants: Dict[str, Any]) -> None:
    """
    Upsert permission grants for a set.

    Args:
        set_id: Permission set identifier
        grants: Dictionary of permission_key -> value mappings
    """
    return await perm_admin.update_permission_set_grants(set_id, grants)


async def get_permission_set_grants(set_id: str) -> Dict[str, Any]:
    """
    Get all permission grants for a set.

    Args:
        set_id: Permission set identifier

    Returns:
        Dictionary of permission_key -> value mappings
    """
    return await perm_admin.get_permission_set_grants(set_id)


async def delete_permission_set_grant(set_id: str, permission_key: str) -> None:
    """
    Delete a specific permission grant from a set.

    Args:
        set_id: Permission set identifier
        permission_key: Permission key to delete
    """
    return await perm_admin.delete_permission_set_grant(set_id, permission_key)


# ===== Cache Management =====

async def invalidate_user_permissions(user_id: str) -> None:
    """
    Invalidate cached permissions for a user.

    Args:
        user_id: User identifier
    """
    return await perm_admin.invalidate_user_permissions(user_id)
