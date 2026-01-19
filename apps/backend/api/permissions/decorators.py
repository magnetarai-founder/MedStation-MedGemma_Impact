"""
Permission Decorators

FastAPI decorators for requiring specific permissions on route handlers.
"""

import logging
from typing import Optional, Callable
from functools import wraps
from api.errors import http_401, http_403
from .engine import get_permission_engine

logger = logging.getLogger(__name__)


def require_perm(permission_key: str, level: Optional[str] = None) -> Callable:
    """
    FastAPI decorator to require a specific permission

    Usage:
        from .auth_middleware import get_current_user

        @router.get("/documents")
        @require_perm("vault.documents.read", level="read")
        async def list_documents(current_user: Dict = Depends(get_current_user)):
            ...

    Args:
        permission_key: Permission to check (e.g., "vault.documents.read")
        level: Optional level requirement ("read", "write", "admin")

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user from kwargs (must be injected by get_current_user dependency)
            current_user = kwargs.get('current_user')

            if not current_user:
                raise http_401("Authentication required")

            user_id = current_user.get('user_id')
            if not user_id:
                raise http_401("Invalid authentication: user_id missing")

            # Founder Rights bypass: founder_rights users always allowed
            if current_user.get('role') == 'founder_rights':
                logger.debug(f"Founder Rights bypass in decorator: {current_user.get('username')} allowed {permission_key}")
                return await func(*args, **kwargs)

            # Load user context
            engine = get_permission_engine()
            try:
                user_ctx = engine.load_user_context(user_id)
            except ValueError as e:
                logger.error(f"Failed to load user context: {e}")
                raise http_403("User context not found")

            # Check permission
            if not engine.has_permission(user_ctx, permission_key, required_level=level):
                logger.warning(
                    f"Permission denied: {user_ctx.username} ({user_ctx.role}) "
                    f"attempted {permission_key} (level={level})"
                )
                raise http_403(f"Missing required permission: {permission_key}" +
                           (f" (level: {level})" if level else ""))

            # Permission granted: proceed
            return await func(*args, **kwargs)

        return wrapper
    return decorator


def require_perm_team(permission_key: str, level: Optional[str] = None, team_kw: str = "team_id") -> Callable:
    """
    FastAPI decorator to require a specific permission with team context (Phase 3)

    Similar to require_perm, but loads user context with team_id from kwargs.
    This allows permission resolution to be team-aware.

    Usage:
        from .auth_middleware import get_current_user

        @router.post("/documents")
        @require_perm_team("docs.create", level="write")
        async def create_document(
            team_id: Optional[str] = None,
            current_user: Dict = Depends(get_current_user)
        ):
            ...

    Args:
        permission_key: Permission to check (e.g., "docs.create")
        level: Optional level requirement ("read", "write", "admin")
        team_kw: Keyword argument name for team_id (default: "team_id")

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user from kwargs
            current_user = kwargs.get('current_user')

            if not current_user:
                raise http_401("Authentication required")

            user_id = current_user.get('user_id')
            if not user_id:
                raise http_401("Invalid authentication: user_id missing")

            # Founder Rights bypass: founder_rights users always allowed
            if current_user.get('role') == 'founder_rights':
                logger.debug(f"Founder Rights bypass in decorator: {current_user.get('username')} allowed {permission_key}")
                return await func(*args, **kwargs)

            # Extract team_id from kwargs (may be None for solo mode)
            team_id = kwargs.get(team_kw) or None

            # Load user context with team context
            engine = get_permission_engine()
            try:
                user_ctx = engine.load_user_context(user_id, team_id=team_id)
            except ValueError as e:
                logger.error(f"Failed to load user context: {e}")
                raise http_403("User context not found")

            # Check permission
            if not engine.has_permission(user_ctx, permission_key, required_level=level):
                logger.warning(
                    f"Permission denied: {user_ctx.username} ({user_ctx.role}) "
                    f"attempted {permission_key} (level={level}) in team={team_id}"
                )
                raise http_403(f"Missing required permission: {permission_key}" +
                           (f" (level: {level})" if level else ""))

            # Permission granted: proceed
            return await func(*args, **kwargs)

        return wrapper
    return decorator
