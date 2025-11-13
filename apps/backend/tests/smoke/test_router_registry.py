"""
Smoke test for router_registry.

Verifies that register_routers can be imported and called without errors.
"""

import pytest

# Skip test if FastAPI is not installed
fastapi = pytest.importorskip("fastapi")

from fastapi import FastAPI


def test_router_registry_import():
    """Test that router_registry can be imported."""
    from api.router_registry import register_routers

    assert callable(register_routers), "register_routers should be callable"


def test_register_routers_returns_tuple():
    """Test that register_routers returns a tuple of (loaded, failed) lists."""
    from api.router_registry import register_routers

    # Create a fresh FastAPI app
    app = FastAPI()

    # Call register_routers
    result = register_routers(app)

    # Verify return type
    assert isinstance(result, tuple), "register_routers should return a tuple"
    assert len(result) == 2, "register_routers should return a 2-tuple"

    loaded, failed = result

    # Verify both are lists
    assert isinstance(loaded, list), "services_loaded should be a list"
    assert isinstance(failed, list), "services_failed should be a list"

    # Note: We don't assert non-empty because the test environment
    # may lack dependencies, causing some/all routers to fail to load


def test_register_routers_no_duplicates():
    """Test that register_routers doesn't add duplicate routes."""
    from api.router_registry import register_routers

    # Create a fresh FastAPI app
    app = FastAPI()

    # Call register_routers
    loaded, failed = register_routers(app)

    # Get all routes from the app
    routes = [route.path for route in app.routes]

    # Check for duplicates (same path registered twice)
    # Note: Some paths may legitimately appear multiple times if they have
    # different methods (GET, POST, etc.), so we check path+method combos
    route_signatures = [(route.path, ",".join(route.methods) if hasattr(route, 'methods') else "")
                        for route in app.routes]

    duplicates = [sig for sig in route_signatures if route_signatures.count(sig) > 1]

    # If there are duplicates, show them for debugging
    if duplicates:
        unique_duplicates = list(set(duplicates))
        pytest.fail(f"Duplicate routes found: {unique_duplicates[:5]}")  # Show first 5
