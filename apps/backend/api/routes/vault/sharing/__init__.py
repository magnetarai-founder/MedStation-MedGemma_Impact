"""
Vault Sharing Routes Package

Combines all sharing-related routes:
- share_links: Create, access, revoke share links
- acl: Grant, check, revoke file permissions
- invitations: Create, accept, decline sharing invitations
- users: User registration and login
"""

from fastapi import APIRouter

from api.routes.vault.sharing.share_links import router as share_links_router
from api.routes.vault.sharing.acl import router as acl_router
from api.routes.vault.sharing.invitations import router as invitations_router
from api.routes.vault.sharing.users import router as users_router

# Re-export endpoint functions for backwards compatibility
from api.routes.vault.sharing.share_links import (
    create_share_link_endpoint,
    get_file_shares_endpoint,
    revoke_share_link_endpoint,
    access_share_link_endpoint,
)
from api.routes.vault.sharing.acl import (
    grant_file_permission,
    check_file_permission,
    get_file_permissions,
    revoke_permission,
)
from api.routes.vault.sharing.invitations import (
    create_sharing_invitation,
    accept_sharing_invitation,
    decline_sharing_invitation,
    get_my_invitations,
)
from api.routes.vault.sharing.users import (
    register_user,
    login_user,
)

# Combine all sharing-related routes into a single router
router = APIRouter()

# Include sub-routers (no prefix - routes already have full paths)
router.include_router(share_links_router)
router.include_router(acl_router)
router.include_router(invitations_router)
router.include_router(users_router)

__all__ = [
    "router",
    # Share links
    "create_share_link_endpoint",
    "get_file_shares_endpoint",
    "revoke_share_link_endpoint",
    "access_share_link_endpoint",
    # ACL
    "grant_file_permission",
    "check_file_permission",
    "get_file_permissions",
    "revoke_permission",
    # Invitations
    "create_sharing_invitation",
    "accept_sharing_invitation",
    "decline_sharing_invitation",
    "get_my_invitations",
    # Users
    "register_user",
    "login_user",
]
