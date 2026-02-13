"""
Tests for health check and app configuration.
"""

import pytest


class TestHealthEndpoint:
    """Verify the health endpoint responds correctly."""

    async def test_health_returns_200(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200

    async def test_health_returns_ok_status(self, client):
        resp = await client.get("/health")
        data = resp.json()
        assert data["status"] == "ok"

    async def test_health_includes_timestamp(self, client):
        resp = await client.get("/health")
        data = resp.json()
        assert "timestamp" in data

    async def test_api_health_alias(self, client):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestCORSConfiguration:
    """Verify CORS is restricted to localhost origins."""

    async def test_cors_allows_localhost_origin(self, client):
        resp = await client.options(
            "/health",
            headers={
                "Origin": "http://127.0.0.1:8000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "http://127.0.0.1:8000"

    async def test_cors_blocks_foreign_origin(self, client):
        resp = await client.options(
            "/health",
            headers={
                "Origin": "http://evil.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Foreign origins should not be reflected
        assert resp.headers.get("access-control-allow-origin") != "http://evil.com"

    async def test_cors_restricts_methods(self, client):
        resp = await client.options(
            "/health",
            headers={
                "Origin": "http://127.0.0.1:8000",
                "Access-Control-Request-Method": "GET",
            },
        )
        allowed = resp.headers.get("access-control-allow-methods", "")
        assert "DELETE" not in allowed
        assert "PUT" not in allowed
