"""
Data Package

Data pipeline and storage utilities for MedStation:
- DataEngine: Excel/JSON → Auto-Clean → SQLite → Query Generation
"""

from api.data.engine import (
    DataEngine,
    get_data_engine,
)

__all__ = [
    "DataEngine",
    "get_data_engine",
]
