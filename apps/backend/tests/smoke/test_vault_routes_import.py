"""
Smoke test for vault routes import.

Verifies that both old and new import paths work and point to the same router.
"""

import pytest

# Skip test if FastAPI is not installed
fastapi = pytest.importorskip("fastapi")

from fastapi import APIRouter


def test_vault_routes_import():
    """Test that api.vault.routes imports successfully and exposes a router."""
    from api.vault import routes as vault_routes

    assert hasattr(vault_routes, "router"), "vault routes should expose 'router' attribute"
    assert isinstance(vault_routes.router, APIRouter), "router should be an APIRouter instance"


def test_vault_service_facade_import():
    """Test that vault_service facade imports and exposes the same router."""
    import vault_service

    assert hasattr(vault_service, "router"), "vault_service should expose 'router' attribute"
    assert isinstance(vault_service.router, APIRouter), "router should be an APIRouter instance"


def test_router_identity():
    """Verify that vault_service.router is the same object as api.vault.routes.router."""
    from api.vault import routes as vault_routes
    import vault_service

    # Both should point to the exact same router object (not a copy)
    assert id(vault_service.router) == id(vault_routes.router), \
        "vault_service.router should be the same object as api.vault.routes.router"


def test_vault_models_import():
    """Test that vault models can be imported from both locations."""
    # New location (preferred)
    from api.services.vault.schemas import VaultDocument, VaultFile, VaultFolder

    assert VaultDocument is not None
    assert VaultFile is not None
    assert VaultFolder is not None

    # Old location (facade re-export)
    from vault_service import VaultDocument as VD, VaultFile as VF, VaultFolder as VFO

    # Should be the same classes
    assert VD is VaultDocument
    assert VF is VaultFile
    assert VFO is VaultFolder


def test_get_vault_service_import():
    """Test that get_vault_service can be imported from both locations."""
    from api.services.vault import get_vault_service

    assert callable(get_vault_service), "get_vault_service should be callable"

    # Also test facade import (should emit deprecation warning)
    with pytest.warns(DeprecationWarning):
        from vault_service import get_vault_service as get_vault_service_old
        assert callable(get_vault_service_old)
