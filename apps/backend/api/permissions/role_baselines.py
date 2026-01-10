"""
Role Baseline Permissions

Default permission baselines for each role.
Extracted from engine.py during P2 decomposition.

These define the starting permissions before any profiles or permission sets
are applied. Later grants (profiles, sets) override these baselines.

Roles (in order of privilege):
- founder_rights: Full bypass (never checked against baselines)
- super_admin: All features and resources granted
- admin: Most features, limited system permissions
- member: Core features, own resources only
- guest: Read-only access
"""

from typing import Dict, Any

from .types import PermissionLevel


def get_founder_rights_baseline() -> Dict[str, Any]:
    """
    Get baseline permissions for founder_rights role.

    Founder Rights bypasses all permission checks, so the baseline
    is empty (never actually checked).

    Returns:
        Empty dict (bypassed at evaluation time)
    """
    return {}


def get_super_admin_baseline() -> Dict[str, Any]:
    """
    Get baseline permissions for super_admin role.

    Super Admin has full access to all features and resources.
    Can be explicitly denied via profiles/sets.

    Returns:
        Dict with all permissions granted at ADMIN level
    """
    return {
        # Features
        'chat.use': True,
        'vault.use': True,
        'workflows.use': True,
        'docs.use': True,
        'data.run_sql': True,
        'data.export': True,
        'insights.use': True,
        'code.use': True,
        'team.use': True,
        'panic.use': True,
        'backups.use': True,

        # Vault resources (level-based)
        'vault.documents.create': PermissionLevel.ADMIN,
        'vault.documents.read': PermissionLevel.ADMIN,
        'vault.documents.update': PermissionLevel.ADMIN,
        'vault.documents.delete': PermissionLevel.ADMIN,
        'vault.documents.share': PermissionLevel.ADMIN,

        # Workflow resources
        'workflows.create': PermissionLevel.ADMIN,
        'workflows.view': PermissionLevel.ADMIN,
        'workflows.edit': PermissionLevel.ADMIN,
        'workflows.delete': PermissionLevel.ADMIN,
        'workflows.manage': PermissionLevel.ADMIN,

        # Docs resources
        'docs.create': PermissionLevel.ADMIN,
        'docs.read': PermissionLevel.ADMIN,
        'docs.update': PermissionLevel.ADMIN,
        'docs.delete': PermissionLevel.ADMIN,
        'docs.share': PermissionLevel.ADMIN,

        # System permissions
        'system.view_admin_dashboard': True,
        'system.manage_users': True,
        'system.view_audit_logs': True,
        'system.manage_permissions': True,
        'system.manage_settings': True,
    }


def get_admin_baseline() -> Dict[str, Any]:
    """
    Get baseline permissions for admin role.

    Admin has most features with WRITE-level resource access.
    Some system permissions require explicit grant via profile/set.

    Returns:
        Dict with admin-level permissions
    """
    return {
        # Features
        'chat.use': True,
        'vault.use': True,
        'workflows.use': True,
        'docs.use': True,
        'data.run_sql': True,
        'data.export': True,
        'insights.use': True,
        'code.use': True,
        'team.use': True,
        'panic.use': True,
        'backups.use': False,  # Require explicit grant via profile/set

        # Vault resources (write level)
        'vault.documents.create': PermissionLevel.WRITE,
        'vault.documents.read': PermissionLevel.WRITE,
        'vault.documents.update': PermissionLevel.WRITE,
        'vault.documents.delete': PermissionLevel.WRITE,
        'vault.documents.share': PermissionLevel.READ,

        # Workflow resources
        'workflows.create': PermissionLevel.WRITE,
        'workflows.view': PermissionLevel.WRITE,
        'workflows.edit': PermissionLevel.WRITE,
        'workflows.delete': PermissionLevel.WRITE,
        'workflows.manage': PermissionLevel.READ,

        # Docs resources
        'docs.create': PermissionLevel.WRITE,
        'docs.read': PermissionLevel.WRITE,
        'docs.update': PermissionLevel.WRITE,
        'docs.delete': PermissionLevel.WRITE,
        'docs.share': PermissionLevel.READ,

        # System permissions (limited)
        'system.view_admin_dashboard': True,
        'system.manage_users': True,
        'system.view_audit_logs': True,
        'system.manage_permissions': False,  # Not by default
        'system.manage_settings': True,
    }


def get_member_baseline() -> Dict[str, Any]:
    """
    Get baseline permissions for member role.

    Member has core features with WRITE access to own resources.
    No system permissions by default.

    Returns:
        Dict with member-level permissions
    """
    return {
        # Features
        'chat.use': True,
        'vault.use': True,
        'workflows.use': True,
        'docs.use': True,
        'data.run_sql': True,
        'data.export': False,  # Not by default
        'insights.use': False,
        'code.use': False,
        'team.use': False,
        'panic.use': False,
        'backups.use': False,

        # Vault resources (read/write on own)
        'vault.documents.create': PermissionLevel.WRITE,
        'vault.documents.read': PermissionLevel.WRITE,
        'vault.documents.update': PermissionLevel.WRITE,
        'vault.documents.delete': PermissionLevel.WRITE,
        'vault.documents.share': PermissionLevel.NONE,

        # Workflow resources
        'workflows.create': PermissionLevel.WRITE,
        'workflows.view': PermissionLevel.WRITE,
        'workflows.edit': PermissionLevel.WRITE,
        'workflows.delete': PermissionLevel.READ,  # Own only
        'workflows.manage': PermissionLevel.NONE,

        # Docs resources
        'docs.create': PermissionLevel.WRITE,
        'docs.read': PermissionLevel.WRITE,
        'docs.update': PermissionLevel.WRITE,
        'docs.delete': PermissionLevel.WRITE,
        'docs.share': PermissionLevel.NONE,

        # System permissions (none)
        'system.view_admin_dashboard': False,
        'system.manage_users': False,
        'system.view_audit_logs': False,
        'system.manage_permissions': False,
        'system.manage_settings': False,
    }


def get_guest_baseline() -> Dict[str, Any]:
    """
    Get baseline permissions for guest role.

    Guest has read-only access to selected features.
    Very limited permissions by design.

    Returns:
        Dict with guest-level (read-only) permissions
    """
    return {
        # Features (very limited)
        'chat.use': True,
        'vault.use': False,
        'workflows.use': False,
        'docs.use': True,
        'data.run_sql': False,
        'data.export': False,
        'insights.use': False,
        'code.use': False,
        'team.use': False,
        'panic.use': False,
        'backups.use': False,

        # Vault resources (none)
        'vault.documents.create': PermissionLevel.NONE,
        'vault.documents.read': PermissionLevel.READ,
        'vault.documents.update': PermissionLevel.NONE,
        'vault.documents.delete': PermissionLevel.NONE,
        'vault.documents.share': PermissionLevel.NONE,

        # Workflow resources (read-only)
        'workflows.create': PermissionLevel.NONE,
        'workflows.view': PermissionLevel.READ,
        'workflows.edit': PermissionLevel.NONE,
        'workflows.delete': PermissionLevel.NONE,
        'workflows.manage': PermissionLevel.NONE,

        # Docs resources (read-only)
        'docs.create': PermissionLevel.NONE,
        'docs.read': PermissionLevel.READ,
        'docs.update': PermissionLevel.NONE,
        'docs.delete': PermissionLevel.NONE,
        'docs.share': PermissionLevel.NONE,

        # System permissions (none)
        'system.view_admin_dashboard': False,
        'system.manage_users': False,
        'system.view_audit_logs': False,
        'system.manage_permissions': False,
        'system.manage_settings': False,
    }


# Role to baseline function mapping
_ROLE_BASELINE_MAP = {
    'founder_rights': get_founder_rights_baseline,
    'super_admin': get_super_admin_baseline,
    'admin': get_admin_baseline,
    'member': get_member_baseline,
    'guest': get_guest_baseline,
}


def get_role_baseline(role: str) -> Dict[str, Any]:
    """
    Get default permission baseline for a role.

    This is the main entry point - use this function instead of
    calling individual role functions directly.

    Args:
        role: User role (founder_rights, super_admin, admin, member, guest)

    Returns:
        Dict of default permissions for the role.
        Returns empty dict for unknown roles (deny all).
    """
    baseline_fn = _ROLE_BASELINE_MAP.get(role)
    if baseline_fn:
        return baseline_fn()

    # Unknown role: empty baseline (deny all)
    return {}


# All permission keys defined in baselines
# Useful for validation and documentation
ALL_PERMISSION_KEYS = frozenset([
    # Features
    'chat.use',
    'vault.use',
    'workflows.use',
    'docs.use',
    'data.run_sql',
    'data.export',
    'insights.use',
    'code.use',
    'team.use',
    'panic.use',
    'backups.use',
    # Vault resources
    'vault.documents.create',
    'vault.documents.read',
    'vault.documents.update',
    'vault.documents.delete',
    'vault.documents.share',
    # Workflow resources
    'workflows.create',
    'workflows.view',
    'workflows.edit',
    'workflows.delete',
    'workflows.manage',
    # Docs resources
    'docs.create',
    'docs.read',
    'docs.update',
    'docs.delete',
    'docs.share',
    # System permissions
    'system.view_admin_dashboard',
    'system.manage_users',
    'system.view_audit_logs',
    'system.manage_permissions',
    'system.manage_settings',
])


__all__ = [
    'get_role_baseline',
    'get_founder_rights_baseline',
    'get_super_admin_baseline',
    'get_admin_baseline',
    'get_member_baseline',
    'get_guest_baseline',
    'ALL_PERMISSION_KEYS',
]
