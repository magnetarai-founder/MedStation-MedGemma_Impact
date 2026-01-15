"""Backward Compatibility Shim - use api.ml.metal4 instead."""

from api.ml.metal4.duckdb_bridge import (
    Metal4DuckDBBridge,
    get_duckdb_bridge,
    validate_duckdb_bridge,
    logger,
)

__all__ = ["Metal4DuckDBBridge", "get_duckdb_bridge", "validate_duckdb_bridge", "logger"]
