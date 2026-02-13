"""
Shared fixtures for MedStation backend tests.

These tests validate the API layer WITHOUT loading the MedGemma model
(no torch/transformers required). The model service is mocked.
"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from api.app_factory import create_app
from api.router_registry import register_routers


@pytest.fixture
def app():
    """Create a fresh FastAPI app with routes registered (bypasses lifespan)."""
    application = create_app()
    register_routers(application)
    return application


@pytest.fixture
async def client(app):
    """Async HTTP client for testing FastAPI endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture
def mock_medgemma_not_loaded():
    """Mock MedGemma service that fails to load (simulates missing model)."""
    mock_svc = AsyncMock()
    mock_svc.loaded = False
    mock_svc.load = AsyncMock(return_value=False)
    mock_svc.device = "cpu"

    with patch("api.services.medgemma.get_medgemma", return_value=mock_svc):
        yield mock_svc


@pytest.fixture
def mock_medgemma_loaded():
    """Mock MedGemma service that is loaded and returns a test response."""
    mock_svc = AsyncMock()
    mock_svc.loaded = True
    mock_svc.device = "mps"
    mock_svc.generate = AsyncMock(return_value="Test medical response from MedGemma.")

    async def mock_stream():
        for token in ["Test ", "streaming ", "response."]:
            yield token

    mock_svc.stream_generate = mock_stream

    with patch("api.services.medgemma.get_medgemma", return_value=mock_svc):
        yield mock_svc
