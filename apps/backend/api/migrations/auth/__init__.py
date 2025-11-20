"""
Auth-specific migrations module

This module contains migrations for authentication and authorization schema only.
All auth/permissions tables are managed through this migration system.
"""

__all__ = ["run_auth_migrations"]

from .runner import run_auth_migrations

# Import migration modules with aliases (can't import names starting with digits directly)
import importlib
auth_0001_initial = importlib.import_module(".0001_initial", package="api.migrations.auth")
