"""Backward Compatibility Shim - use api.ml.metal4 instead."""

from api.ml.metal4.sql_engine import (
    Metal4SQLEngine,
    get_sql_engine,
    validate_sql_engine,
    logger,
)

# Alias for backward compatibility
get_metal4_sql_engine = get_sql_engine

__all__ = ["Metal4SQLEngine", "get_sql_engine", "get_metal4_sql_engine", "validate_sql_engine", "logger"]
