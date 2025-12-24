#!/usr/bin/env python3
"""
Team Service - DEPRECATED FACADE

⚠️  DEPRECATION NOTICE ⚠️

This module is deprecated and will be removed in v2.0.

Please update your imports:

  OLD (deprecated):
    from team_service import router
    from team_service import is_team_member, require_team_admin

  NEW (preferred):
    from api.routes import team
    # Use team.router for the APIRouter

    from api.services.team import get_team_manager, is_team_member, require_team_admin
    # Use services.team for business logic

This facade maintains backwards compatibility by re-exporting the router
and key functions with deprecation warnings.

Migrated as part of R2 Team Service Split refactoring.

STATUS: All internal callers migrated (Dec 23, 2025)
- services/vault/permissions.py → api.services.team
- workflows/dependencies.py → api.services.team
- workflow_p2p_sync.py → api.services.team
- offline_data_sync.py → api.services.team
- docs_service.py → api.services.team
- routes/vault/documents.py → api.services.team
This facade can be removed once external integrations are verified.
"""

import functools
import warnings
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# ===== Router Re-export =====

# Import the real router from api.routes.team
try:
    from api.routes import team as _team_routes
except ImportError:
    from routes import team as _team_routes

router = _team_routes.router

# Router is the same object; no deprecation warning needed for router itself
# since it's the actual implementation, not a wrapper

# ===== Deprecation Decorator =====

def deprecated(new_path: str) -> Callable:
    """
    Decorator to mark functions as deprecated with migration guidance.

    Args:
        new_path: The new import path to use

    Returns:
        Decorated function that emits DeprecationWarning
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            warnings.warn(
                f"{func.__name__} is deprecated. Import from {new_path} instead.",
                DeprecationWarning,
                stacklevel=2
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ===== Helper Function Wrappers =====

@deprecated("api.services.team")
def is_team_member(team_id: str, user_id: str) -> Optional[str]:
    """Check if user is team member - DEPRECATED"""
    from api.services.team import is_team_member as _is_team_member
    return _is_team_member(team_id, user_id)


@deprecated("api.services.team")
def require_team_admin(team_id: str, user_id: str) -> None:
    """Require team admin role - DEPRECATED"""
    from api.services.team import require_team_admin as _require_team_admin
    return _require_team_admin(team_id, user_id)


@deprecated("api.services.team")
def get_team_manager() -> Any:
    """Get TeamManager instance - DEPRECATED"""
    from api.services.team import get_team_manager as _get_team_manager
    return _get_team_manager()


@deprecated("api.services.team.helpers")
def _get_app_conn() -> Any:
    """Get app database connection - DEPRECATED"""
    from api.services.team.helpers import _get_app_conn as _get_conn
    return _get_conn()


# ===== Legacy Class Re-export =====

# For code that imports TeamManager directly
@deprecated("api.services.team.core")
class TeamManager:
    """DEPRECATED - Import from api.services.team.core instead"""
    def __init__(self):
        from api.services.team.core import TeamManager as _TeamManager
        self._impl = _TeamManager()

    def __getattr__(self, name):
        return getattr(self._impl, name)


logger.info("team_service.py loaded as compatibility facade (DEPRECATED)")
