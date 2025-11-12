"""
Query result cache placeholder.

To be filled with LRU caching logic migrated from main.py.
Mechanical scaffold only — no behavior yet.
"""

from __future__ import annotations

import pandas as pd  # type: ignore


class QueryCache:
    """Placeholder for query result caching service."""

    def __init__(self, max_size_mb: int = 500, max_entries: int = 50):
        self.max_size_mb = max_size_mb
        self.max_entries = max_entries

    def get(self, key: str) -> pd.DataFrame | None:  # pragma: no cover - placeholder
        return None

    def put(self, key: str, df: pd.DataFrame) -> None:  # pragma: no cover - placeholder
        return None

    def clear(self) -> None:  # pragma: no cover - placeholder
        return None

