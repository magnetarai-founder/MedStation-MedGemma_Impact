"""
Tests for MedGemma inference routes.

Validates input validation, error handling, and model availability checks
WITHOUT requiring the actual MedGemma model.
"""

import pytest


class TestGenerateInputValidation:
    """Pydantic Field validators on GenerateRequest."""

    async def test_empty_prompt_rejected(self, client, mock_medgemma_loaded):
        resp = await client.post("/api/v1/chat/medgemma/generate", json={"prompt": ""})
        assert resp.status_code == 422  # Validation error

    async def test_prompt_too_long_rejected(self, client, mock_medgemma_loaded):
        resp = await client.post("/api/v1/chat/medgemma/generate", json={"prompt": "x" * 10001})
        assert resp.status_code == 422

    async def test_valid_prompt_accepted(self, client, mock_medgemma_loaded):
        resp = await client.post("/api/v1/chat/medgemma/generate", json={"prompt": "Patient has chest pain"})
        assert resp.status_code == 200

    async def test_negative_temperature_rejected(self, client, mock_medgemma_loaded):
        resp = await client.post(
            "/api/v1/chat/medgemma/generate",
            json={"prompt": "test", "temperature": -0.5},
        )
        assert resp.status_code == 422

    async def test_temperature_above_max_rejected(self, client, mock_medgemma_loaded):
        resp = await client.post(
            "/api/v1/chat/medgemma/generate",
            json={"prompt": "test", "temperature": 3.0},
        )
        assert resp.status_code == 422

    async def test_temperature_zero_accepted(self, client, mock_medgemma_loaded):
        resp = await client.post(
            "/api/v1/chat/medgemma/generate",
            json={"prompt": "test", "temperature": 0.0},
        )
        assert resp.status_code == 200

    async def test_temperature_max_accepted(self, client, mock_medgemma_loaded):
        resp = await client.post(
            "/api/v1/chat/medgemma/generate",
            json={"prompt": "test", "temperature": 2.0},
        )
        assert resp.status_code == 200

    async def test_max_tokens_zero_rejected(self, client, mock_medgemma_loaded):
        resp = await client.post(
            "/api/v1/chat/medgemma/generate",
            json={"prompt": "test", "max_tokens": 0},
        )
        assert resp.status_code == 422

    async def test_max_tokens_too_high_rejected(self, client, mock_medgemma_loaded):
        resp = await client.post(
            "/api/v1/chat/medgemma/generate",
            json={"prompt": "test", "max_tokens": 5000},
        )
        assert resp.status_code == 422

    async def test_max_tokens_valid_accepted(self, client, mock_medgemma_loaded):
        resp = await client.post(
            "/api/v1/chat/medgemma/generate",
            json={"prompt": "test", "max_tokens": 512},
        )
        assert resp.status_code == 200


class TestModelNotLoaded:
    """503 response when MedGemma model is unavailable."""

    async def test_generate_returns_503_when_model_unavailable(self, client, mock_medgemma_not_loaded):
        resp = await client.post("/api/v1/chat/medgemma/generate", json={"prompt": "test"})
        assert resp.status_code == 503

    async def test_503_includes_error_detail(self, client, mock_medgemma_not_loaded):
        resp = await client.post("/api/v1/chat/medgemma/generate", json={"prompt": "test"})
        data = resp.json()
        assert "error" in data
        assert "not loaded" in data["error"].lower()

    async def test_status_reports_not_loaded(self, client, mock_medgemma_not_loaded):
        resp = await client.get("/api/v1/chat/medgemma/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["loaded"] is False


class TestGenerateResponse:
    """Successful generation with loaded model."""

    async def test_generate_returns_response(self, client, mock_medgemma_loaded):
        resp = await client.post("/api/v1/chat/medgemma/generate", json={"prompt": "Patient has headache"})
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert "model" in data

    async def test_generate_includes_model_name(self, client, mock_medgemma_loaded):
        resp = await client.post("/api/v1/chat/medgemma/generate", json={"prompt": "test"})
        data = resp.json()
        assert data["model"] == "medgemma-1.5-4b-it"

    async def test_status_reports_loaded(self, client, mock_medgemma_loaded):
        resp = await client.get("/api/v1/chat/medgemma/status")
        data = resp.json()
        assert data["loaded"] is True
        assert data["device"] == "mps"

    async def test_invalid_image_returns_400(self, client, mock_medgemma_loaded):
        resp = await client.post(
            "/api/v1/chat/medgemma/generate",
            json={"prompt": "analyze this", "image_base64": "not-valid-base64!!!"},
        )
        assert resp.status_code == 400
        assert "image" in resp.json()["error"].lower()


class TestModelLoadEndpoint:
    """Explicit /api/v1/chat/medgemma/load endpoint."""

    async def test_load_success(self, client, mock_medgemma_loaded):
        resp = await client.post("/api/v1/chat/medgemma/load")
        assert resp.status_code == 200

    async def test_load_failure_returns_500(self, client, mock_medgemma_not_loaded):
        resp = await client.post("/api/v1/chat/medgemma/load")
        assert resp.status_code == 500
        data = resp.json()
        assert data["status"] == "error"
