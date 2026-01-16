"""
Compatibility Shim for Vault Decoy Documents

The implementation now lives in the `api.vault` package:
- api.vault.decoy_documents: Static decoy document data

This shim maintains backward compatibility.
"""

# Re-export everything from the new package location
from api.vault.decoy_documents import (
    DocumentCategory,
    DECOY_DOCUMENTS,
)

# Also re-export helper functions if they exist
try:
    from api.vault.decoy_documents import (
        get_random_documents,
        get_documents_by_category,
    )
except ImportError:
    pass

__all__ = [
    "DocumentCategory",
    "DECOY_DOCUMENTS",
]
