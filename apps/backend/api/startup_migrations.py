"""
Compatibility Shim for Startup Migrations

The implementation now lives in the `api.migrations` package:
- api.migrations.startup: run_startup_migrations

This shim maintains backward compatibility.
"""

from api.migrations.startup import run_startup_migrations

__all__ = [
    "run_startup_migrations",
]
