"""
Database migrations for MedStation

- run_startup_migrations: Runs all pending migrations on app startup
"""

from api.migrations.startup import run_startup_migrations

__all__ = [
    "run_startup_migrations",
]
