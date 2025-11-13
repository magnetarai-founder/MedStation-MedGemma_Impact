"""
Smoke test for chat routes import.

Verifies that both old and new import paths work and routers are identical.
"""

import pytest

# Skip test if FastAPI is not installed
fastapi = pytest.importorskip("fastapi")

from fastapi import APIRouter


def test_chat_routes_import():
    """Test that api.routes.chat imports successfully and exposes routers."""
    from api.routes import chat as chat_routes

    assert hasattr(chat_routes, "router"), "chat routes should expose 'router' attribute"
    assert isinstance(chat_routes.router, APIRouter), "router should be an APIRouter instance"

    assert hasattr(chat_routes, "public_router"), "chat routes should expose 'public_router' attribute"
    assert isinstance(chat_routes.public_router, APIRouter), "public_router should be an APIRouter instance"


def test_chat_service_facade_import():
    """Test that chat_service facade imports and exposes the same routers."""
    import chat_service

    assert hasattr(chat_service, "router"), "chat_service should expose 'router' attribute"
    assert isinstance(chat_service.router, APIRouter), "router should be an APIRouter instance"

    assert hasattr(chat_service, "public_router"), "chat_service should expose 'public_router' attribute"
    assert isinstance(chat_service.public_router, APIRouter), "public_router should be an APIRouter instance"


def test_router_identity():
    """Verify that chat_service routers are the same objects as api.routes.chat routers."""
    from api.routes import chat as chat_routes
    import chat_service

    # Both should point to the exact same router object (not a copy)
    assert id(chat_service.router) == id(chat_routes.router), \
        "chat_service.router should be the same object as api.routes.chat.router"

    assert id(chat_service.public_router) == id(chat_routes.public_router), \
        "chat_service.public_router should be the same object as api.routes.chat.public_router"


def test_ollama_client_import():
    """Test that ollama_client can be imported from both locations."""
    # New location (preferred)
    from api.services.chat import get_ollama_client, OllamaClient

    assert callable(get_ollama_client), "get_ollama_client should be callable"

    # Verify OllamaClient is a class
    assert isinstance(OllamaClient, type), "OllamaClient should be a class"

    # Old location (facade) - should work without deprecation warnings for now
    from chat_service import ollama_client, OllamaClient as OllamaClientOld

    assert ollama_client is not None, "ollama_client should be defined"
    assert OllamaClientOld is OllamaClient, "OllamaClient class should be the same from both imports"


def test_services_chat_package_structure():
    """Test that services/chat package has expected structure."""
    # Import package
    from api.services import chat

    # Verify key exports
    assert hasattr(chat, "OllamaClient"), "chat package should expose OllamaClient"
    assert hasattr(chat, "get_ollama_client"), "chat package should expose get_ollama_client"

    # Verify core functions exist
    assert hasattr(chat, "create_session"), "chat package should expose create_session"
    assert hasattr(chat, "send_message_stream"), "chat package should expose send_message_stream"
    assert hasattr(chat, "list_ollama_models"), "chat package should expose list_ollama_models"


def test_services_chat_submodules():
    """Test that services/chat submodules can be imported."""
    # streaming module
    from api.services.chat import streaming
    assert hasattr(streaming, "OllamaClient"), "streaming module should have OllamaClient"

    # core module
    from api.services.chat import core
    assert hasattr(core, "create_session"), "core module should have create_session"
    assert hasattr(core, "send_message_stream"), "core module should have send_message_stream"


def test_routes_chat_import():
    """Test that api.routes.chat can be imported and has routers."""
    from api.routes import chat

    assert hasattr(chat, "router"), "api.routes.chat should have router"
    assert hasattr(chat, "public_router"), "api.routes.chat should have public_router"

    # Both routers should be APIRouter instances
    assert isinstance(chat.router, APIRouter), "router should be APIRouter"
    assert isinstance(chat.public_router, APIRouter), "public_router should be APIRouter"
