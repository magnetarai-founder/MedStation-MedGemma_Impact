"""
Compatibility Shim for Vault Seed Data

The implementation now lives in the `api.vault` package:
- api.vault.seed_data: DecoyVaultSeeder class

This shim maintains backward compatibility.
"""

# Re-export everything from the new package location
from api.vault.seed_data import (
    DecoyVaultSeeder,
    get_seeder,
)

# Re-export decoy documents for backwards compatibility
from api.vault.decoy_documents import DECOY_DOCUMENTS

__all__ = [
    "DecoyVaultSeeder",
    "get_seeder",
    "DECOY_DOCUMENTS",
]
