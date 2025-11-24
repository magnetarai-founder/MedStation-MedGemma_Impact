"""
Core utilities for MagnetarStudio backend.

This module provides foundational functionality:
- Database session management
- Security (JWT, password hashing)
- Dependencies (FastAPI dependency injection)
- Custom exceptions
- Event bus
"""

__all__ = [
    'database',
    'security',
    'dependencies',
    'exceptions',
    'events',
]
