"""
Database Abstraction Layer

Provides centralized database connection management and repository patterns:
- DatabaseConnection: Thread-local connection pooling with WAL mode
- BaseRepository: CRUD helpers with consistent patterns
"""

from .base_repository import BaseRepository
from .connection import DatabaseConnection

__all__ = [
    "DatabaseConnection",
    "BaseRepository",
]
