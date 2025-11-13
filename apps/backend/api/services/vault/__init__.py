"""
Vault Service Package

Modular vault service for encrypted document and file storage.

Public API:
- Schemas: VaultDocument, VaultFile, VaultFolder, etc.
- Core: VaultService class, get_vault_service()
- Encryption: Key generation and crypto helpers
- Sharing: Share links, invitations, ACL
- Permissions: Permission checking and team membership

Usage:
    from api.services.vault import get_vault_service, VaultDocument
    from api.services.vault.core import VaultService
    from api.services.vault.schemas import VaultFile, VaultFolder
"""

# Re-export schemas
from .schemas import (
    VaultDocument,
    VaultDocumentCreate,
    VaultDocumentUpdate,
    VaultListResponse,
    VaultFile,
    VaultFolder,
)

# Re-export core
from .core import VaultService, get_vault_service

# Re-export encryption helpers
from .encryption import (
    get_encryption_key,
    generate_file_key,
    generate_share_token,
)

# Re-export sharing helpers
from .sharing import (
    validate_share_permissions,
    generate_share_link_data,
)

# Re-export permission helpers
from .permissions import (
    check_vault_permission,
    check_team_membership,
    require_vault_access,
)

__all__ = [
    # Schemas
    "VaultDocument",
    "VaultDocumentCreate",
    "VaultDocumentUpdate",
    "VaultListResponse",
    "VaultFile",
    "VaultFolder",
    # Core
    "VaultService",
    "get_vault_service",
    # Encryption
    "get_encryption_key",
    "generate_file_key",
    "generate_share_token",
    # Sharing
    "validate_share_permissions",
    "generate_share_link_data",
    # Permissions
    "check_vault_permission",
    "check_team_membership",
    "require_vault_access",
]
