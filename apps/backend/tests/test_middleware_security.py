"""
Module: test_middleware_security.py
Purpose: Test middleware security features, rate limiting, error handling, and observability

Coverage:
- Request timing middleware
- Request metrics tracking
- Error handler responses (4xx, 5xx)
- Rate limiting (token bucket)
- Error format consistency
- Security best practices

Priority: 2.1 (Middleware & Infrastructure)
Expected Coverage Gain: +2-3%
"""

import os
import sys
import pytest
import time
from datetime import datetime, UTC
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from starlette.responses import Response

# Ensure test environment
os.environ["MEDSTATION_ENV"] = "test"

# Add backend to path
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))
sys.path.insert(0, str(backend_root / "api"))

from api.observability_middleware import (
    RequestTimingMiddleware,
    RequestMetrics,
    add_observability_middleware,
    get_request_metrics,
    get_endpoint_metrics,
    get_error_metrics,
    reset_metrics,
    SLOW_REQUEST_THRESHOLD_MS,
    VERY_SLOW_REQUEST_THRESHOLD_MS,
)
from api.rate_limiter import (
    SimpleRateLimiter,
    rate_limiter,
    get_client_ip,
    is_dev_mode,
)
from api.middleware.error_handlers import register_error_handlers


class TestRequestTimingMiddleware:
    """Test request timing middleware functionality"""

    @pytest.fixture
    def app_with_middleware(self):
        """Create a FastAPI app with timing middleware"""
        app = FastAPI()
        add_observability_middleware(app)

        @app.get("/fast")
        async def fast_endpoint():
            return {"status": "ok"}

        @app.get("/slow")
        async def slow_endpoint():
            time.sleep(0.1)  # 100ms delay
            return {"status": "slow"}

        @app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")

        return app

    def test_response_time_header_added(self, app_with_middleware):
        """Test that X-Response-Time header is added to responses"""
        client = TestClient(app_with_middleware)
        response = client.get("/fast")

        assert "X-Response-Time" in response.headers
        assert "ms" in response.headers["X-Response-Time"]

    def test_fast_request_timing(self, app_with_middleware):
        """Test that fast requests are timed correctly"""
        client = TestClient(app_with_middleware)
        response = client.get("/fast")

        response_time = response.headers.get("X-Response-Time", "")
        # Extract milliseconds value
        ms_value = float(response_time.replace("ms", ""))

        # Fast request should be under slow threshold
        assert ms_value < SLOW_REQUEST_THRESHOLD_MS

    def test_slow_request_threshold(self):
        """Test slow request threshold constants"""
        assert SLOW_REQUEST_THRESHOLD_MS == 1000  # 1 second
        assert VERY_SLOW_REQUEST_THRESHOLD_MS == 5000  # 5 seconds
        assert VERY_SLOW_REQUEST_THRESHOLD_MS > SLOW_REQUEST_THRESHOLD_MS


class TestRequestMetrics:
    """Test request metrics tracking"""

    def setup_method(self):
        """Reset metrics before each test"""
        RequestMetrics.reset()

    def test_record_request_increments_count(self):
        """Test that recording requests increments total count"""
        initial_stats = RequestMetrics.get_stats()
        initial_count = initial_stats["total_requests"]

        RequestMetrics.record_request(
            method="GET",
            path="/test",
            status_code=200,
            elapsed_ms=50.0
        )

        stats = RequestMetrics.get_stats()
        assert stats["total_requests"] == initial_count + 1

    def test_record_request_tracks_slow_requests(self):
        """Test that slow requests are tracked separately"""
        RequestMetrics.reset()

        # Record a slow request (> 1000ms)
        RequestMetrics.record_request(
            method="GET",
            path="/slow",
            status_code=200,
            elapsed_ms=1500.0
        )

        stats = RequestMetrics.get_stats()
        assert stats["slow_requests"] == 1

    def test_record_request_tracks_very_slow_requests(self):
        """Test that very slow requests are tracked"""
        RequestMetrics.reset()

        # Record a very slow request (> 5000ms)
        RequestMetrics.record_request(
            method="GET",
            path="/very-slow",
            status_code=200,
            elapsed_ms=6000.0
        )

        stats = RequestMetrics.get_stats()
        assert stats["very_slow_requests"] == 1

    def test_record_error_increments_failed_count(self):
        """Test that errors increment failed request count"""
        RequestMetrics.reset()

        RequestMetrics.record_error(
            method="GET",
            path="/error",
            error_type="ValueError",
            elapsed_ms=100.0
        )

        stats = RequestMetrics.get_stats()
        assert stats["failed_requests"] == 1

    def test_record_error_stores_recent_errors(self):
        """Test that recent errors are stored"""
        RequestMetrics.reset()

        RequestMetrics.record_error(
            method="POST",
            path="/api/fail",
            error_type="DatabaseError",
            elapsed_ms=200.0
        )

        error_stats = RequestMetrics.get_error_stats()
        assert "DatabaseError" in error_stats["error_counts"]
        assert len(error_stats["recent_errors"]) >= 1

    def test_get_endpoint_stats(self):
        """Test endpoint-specific statistics"""
        RequestMetrics.reset()

        # Record multiple requests to same endpoint
        for i in range(5):
            RequestMetrics.record_request(
                method="GET",
                path="/api/users",
                status_code=200,
                elapsed_ms=50.0
            )

        endpoint_stats = RequestMetrics.get_endpoint_stats(limit=10)

        # Find our endpoint
        users_endpoint = next(
            (e for e in endpoint_stats if e["endpoint"] == "GET /api/users"),
            None
        )

        assert users_endpoint is not None
        assert users_endpoint["count"] == 5

    def test_average_time_calculation(self):
        """Test average response time calculation"""
        RequestMetrics.reset()

        # Record requests with known times
        RequestMetrics.record_request("GET", "/test", 200, 100.0)
        RequestMetrics.record_request("GET", "/test", 200, 200.0)
        RequestMetrics.record_request("GET", "/test", 200, 300.0)

        stats = RequestMetrics.get_stats()

        # Average should be 200ms
        assert stats["average_time_ms"] == 200.0

    def test_reset_clears_all_metrics(self):
        """Test that reset clears all metrics"""
        # Add some data
        RequestMetrics.record_request("GET", "/test", 200, 100.0)
        RequestMetrics.record_error("GET", "/error", "Error", 50.0)

        # Reset
        RequestMetrics.reset()

        stats = RequestMetrics.get_stats()
        assert stats["total_requests"] == 0
        assert stats["failed_requests"] == 0


class TestRateLimiter:
    """Test rate limiting functionality"""

    def test_rate_limiter_allows_first_request(self):
        """Test that first request is always allowed"""
        limiter = SimpleRateLimiter()

        # First request should always be allowed
        result = limiter.check_rate_limit(
            key="test:first:request",
            max_requests=1,
            window_seconds=60
        )

        assert result is True

    def test_rate_limiter_blocks_over_limit(self):
        """Test that requests over limit are blocked"""
        limiter = SimpleRateLimiter()
        key = "test:block:limit"

        # Use all tokens
        for i in range(5):
            limiter.check_rate_limit(key, max_requests=5, window_seconds=60)

        # Next request should be blocked
        result = limiter.check_rate_limit(key, max_requests=5, window_seconds=60)
        assert result is False

    def test_rate_limiter_refills_tokens(self):
        """Test that tokens refill over time"""
        limiter = SimpleRateLimiter()
        key = "test:refill:tokens"

        # Use all tokens
        for i in range(3):
            limiter.check_rate_limit(key, max_requests=3, window_seconds=1)

        # Wait for refill
        time.sleep(1.1)  # Wait slightly more than window

        # Should have tokens again
        result = limiter.check_rate_limit(key, max_requests=3, window_seconds=1)
        assert result is True

    def test_rate_limiter_separate_keys(self):
        """Test that different keys have separate buckets"""
        limiter = SimpleRateLimiter()

        # Exhaust one key
        for i in range(2):
            limiter.check_rate_limit("user:1", max_requests=2, window_seconds=60)

        # Other key should still have tokens
        result = limiter.check_rate_limit("user:2", max_requests=2, window_seconds=60)
        assert result is True

    def test_global_rate_limiter_instance(self):
        """Test that global rate_limiter instance works"""
        # Global instance should be SimpleRateLimiter
        assert isinstance(rate_limiter, SimpleRateLimiter)

        # Should be able to check rate limits
        result = rate_limiter.check_rate_limit(
            "global:test:instance",
            max_requests=10,
            window_seconds=60
        )
        assert result is True


class TestGetClientIP:
    """Test client IP extraction"""

    def test_get_client_ip_from_request(self):
        """Test extracting client IP from request"""
        mock_request = MagicMock()
        mock_request.client = MagicMock()
        mock_request.client.host = "192.168.1.100"

        ip = get_client_ip(mock_request)
        assert ip == "192.168.1.100"

    def test_get_client_ip_no_client(self):
        """Test handling request with no client"""
        mock_request = MagicMock()
        mock_request.client = None

        ip = get_client_ip(mock_request)
        assert ip == "unknown"


class TestDevModeDetection:
    """Test development mode detection"""

    def test_dev_mode_from_env(self):
        """Test dev mode detection from environment"""
        mock_request = MagicMock()
        mock_request.client = MagicMock()
        mock_request.client.host = "10.0.0.5"  # Non-localhost

        with patch.dict(os.environ, {"MEDSTATION_ENV": "development"}):
            result = is_dev_mode(mock_request)

        assert result is True

    def test_dev_mode_from_localhost(self):
        """Test dev mode detection from localhost"""
        mock_request = MagicMock()
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        with patch.dict(os.environ, {"MEDSTATION_ENV": "production"}, clear=False):
            # Remove MEDSTATION_FOUNDER_PASSWORD to ensure we're testing localhost detection
            os.environ.pop("MEDSTATION_FOUNDER_PASSWORD", None)
            result = is_dev_mode(mock_request)

        assert result is True


class TestErrorHandlers:
    """Test error handler functionality"""

    @pytest.fixture
    def app_with_error_handlers(self):
        """Create FastAPI app with error handlers"""
        app = FastAPI()
        register_error_handlers(app)

        @app.get("/http-error")
        async def http_error():
            raise HTTPException(status_code=400, detail="Bad request")

        @app.get("/server-error")
        async def server_error():
            raise HTTPException(status_code=500, detail="Internal error")

        @app.get("/value-error")
        async def value_error():
            raise ValueError("Invalid value")

        @app.get("/permission-error")
        async def permission_error():
            raise PermissionError("Access denied")

        @app.get("/not-found-error")
        async def not_found_error():
            raise FileNotFoundError("File not found")

        @app.get("/unhandled-error")
        async def unhandled_error():
            raise RuntimeError("Unexpected error")

        return app

    def test_http_exception_400_returns_detail(self, app_with_error_handlers):
        """Test that 4xx errors return the error detail"""
        client = TestClient(app_with_error_handlers)
        response = client.get("/http-error")

        assert response.status_code == 400
        data = response.json()
        assert data["error"] is True
        assert data["status_code"] == 400
        assert data["message"] == "Bad request"

    def test_http_exception_500_hides_detail(self, app_with_error_handlers):
        """Test that 5xx errors hide internal details"""
        client = TestClient(app_with_error_handlers)
        response = client.get("/server-error")

        assert response.status_code == 500
        data = response.json()
        assert data["error"] is True
        assert "internal" in data["message"].lower()
        assert "Internal error" not in data["message"]  # Original detail hidden

    def test_value_error_returns_400(self, app_with_error_handlers):
        """Test that ValueError returns 400 Bad Request"""
        client = TestClient(app_with_error_handlers)
        response = client.get("/value-error")

        assert response.status_code == 400
        data = response.json()
        assert data["status_code"] == 400

    def test_permission_error_returns_403(self, app_with_error_handlers):
        """Test that PermissionError returns 403 Forbidden"""
        client = TestClient(app_with_error_handlers)
        response = client.get("/permission-error")

        assert response.status_code == 403
        data = response.json()
        assert data["status_code"] == 403
        assert "permission" in data["message"].lower()

    def test_file_not_found_returns_404(self, app_with_error_handlers):
        """Test that FileNotFoundError returns 404"""
        client = TestClient(app_with_error_handlers)
        response = client.get("/not-found-error")

        assert response.status_code == 404
        data = response.json()
        assert data["status_code"] == 404

    def test_unhandled_exception_returns_500(self, app_with_error_handlers):
        """Test that unhandled exceptions return 500"""
        # Use raise_server_exceptions=False to test error handler behavior
        client = TestClient(app_with_error_handlers, raise_server_exceptions=False)
        response = client.get("/unhandled-error")

        assert response.status_code == 500
        data = response.json()
        assert data["error"] is True
        # Should not expose internal error message
        assert "RuntimeError" not in data["message"]
        assert "Unexpected error" not in data["message"]

    def test_error_response_format_consistency(self, app_with_error_handlers):
        """Test that all error responses have consistent format"""
        client = TestClient(app_with_error_handlers)

        # Test multiple error types
        endpoints = ["/http-error", "/value-error", "/permission-error", "/not-found-error"]

        for endpoint in endpoints:
            response = client.get(endpoint)
            data = response.json()

            # All should have these fields
            assert "error" in data
            assert "status_code" in data
            assert "message" in data

            # error should be boolean True
            assert data["error"] is True

            # status_code should match response
            assert data["status_code"] == response.status_code


class TestMetricsAPI:
    """Test metrics retrieval functions"""

    def test_get_request_metrics(self):
        """Test get_request_metrics function"""
        RequestMetrics.reset()
        RequestMetrics.record_request("GET", "/test", 200, 100.0)

        metrics = get_request_metrics()

        assert "total_requests" in metrics
        assert "failed_requests" in metrics
        assert "average_time_ms" in metrics

    def test_get_endpoint_metrics(self):
        """Test get_endpoint_metrics function"""
        RequestMetrics.reset()
        RequestMetrics.record_request("GET", "/api/test", 200, 50.0)

        metrics = get_endpoint_metrics(limit=5)

        assert isinstance(metrics, list)
        if metrics:
            assert "endpoint" in metrics[0]
            assert "count" in metrics[0]

    def test_get_error_metrics(self):
        """Test get_error_metrics function"""
        RequestMetrics.reset()
        RequestMetrics.record_error("POST", "/fail", "TestError", 100.0)

        metrics = get_error_metrics()

        assert "error_counts" in metrics
        assert "recent_errors" in metrics
        assert "total_error_types" in metrics

    def test_reset_metrics_function(self):
        """Test reset_metrics function"""
        RequestMetrics.record_request("GET", "/test", 200, 100.0)

        reset_metrics()

        stats = RequestMetrics.get_stats()
        assert stats["total_requests"] == 0
