"""
Smoke test for team routes import.

Verifies that both old and new import paths work and point to the same router.
"""

import pytest

# Skip test if FastAPI is not installed
fastapi = pytest.importorskip("fastapi")

from fastapi import APIRouter


def test_team_routes_import():
    """Test that api.routes.team imports successfully and exposes a router."""
    from api.routes import team as team_routes

    assert hasattr(team_routes, "router"), "team routes should expose 'router' attribute"
    assert isinstance(team_routes.router, APIRouter), "router should be an APIRouter instance"


def test_team_service_facade_import():
    """Test that team_service facade imports and exposes the same router."""
    import team_service

    assert hasattr(team_service, "router"), "team_service should expose 'router' attribute"
    assert isinstance(team_service.router, APIRouter), "router should be an APIRouter instance"


def test_router_identity():
    """Verify that team_service.router is the same object as api.routes.team.router."""
    from api.routes import team as team_routes
    import team_service

    # Both should point to the exact same router object (not a copy)
    assert id(team_service.router) == id(team_routes.router), \
        "team_service.router should be the same object as api.routes.team.router"


def test_team_helpers_import():
    """Test that team helpers can be imported from both locations."""
    # New location (preferred)
    from api.services.team import get_team_manager, is_team_member, require_team_admin

    assert callable(get_team_manager), "get_team_manager should be callable"
    assert callable(is_team_member), "is_team_member should be callable"
    assert callable(require_team_admin), "require_team_admin should be callable"

    # Old location (facade) - should emit deprecation warnings
    with pytest.warns(DeprecationWarning):
        from team_service import get_team_manager as gtm_old
        assert callable(gtm_old)

    with pytest.warns(DeprecationWarning):
        from team_service import is_team_member as itm_old
        assert callable(itm_old)

    with pytest.warns(DeprecationWarning):
        from team_service import require_team_admin as rta_old
        assert callable(rta_old)


def test_team_manager_import():
    """Test that TeamManager can be imported from new location."""
    from api.services.team.core import TeamManager

    assert TeamManager is not None
    # Don't instantiate - may require database setup


def test_duplicate_services_team_removed():
    """Verify that the old duplicate services/team.py file is gone."""
    # This should fail to import as a module (now it's a package)
    with pytest.raises(AttributeError):
        # Try to access something that would exist if it were still the old file
        from api.services import team
        # The old file had TeamManager at module level
        # The new package has it in team.core
        _ = team.TeamManager  # This should raise AttributeError
        # Because team.__init__.py doesn't export TeamManager at top level
        # (only via re-export of the class, which is different)
