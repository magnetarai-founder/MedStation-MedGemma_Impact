"""
Compatibility Shim for Data Engine

The implementation now lives in the `api.data` package:
- api.data.engine: DataEngine class

This shim maintains backward compatibility.
"""

from api.data.engine import (
    DataEngine,
    get_data_engine,
)

__all__ = [
    "DataEngine",
    "get_data_engine",
]
