"""
Vault Package

Secure document storage with plausible deniability features:
- Encrypted document storage (real vault)
- Decoy vault with realistic documents
- File management and sharing
"""

from api.vault.routes import router
from api.vault.decoy_documents import (
    DocumentCategory,
    DECOY_DOCUMENTS,
)
from api.vault.seed_data import (
    DecoyVaultSeeder,
    get_seeder,
)

__all__ = [
    # Routes
    "router",
    # Decoy documents
    "DocumentCategory",
    "DECOY_DOCUMENTS",
    # Seeder
    "DecoyVaultSeeder",
    "get_seeder",
]
