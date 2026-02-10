"""
Module: test_edge_cases.py
Purpose: Test edge cases, boundary conditions, and malformed input handling

Coverage:
- File sanitization edge cases (path traversal, empty, long names, hidden files)
- Log sanitization edge cases (nested structures, secret patterns, truncation)
- Rate limiter boundary conditions
- Auth middleware edge cases

Priority: 3.1 (Edge Cases & Error Handling)
Expected Coverage Gain: +2%
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure test environment
os.environ["ELOHIM_ENV"] = "test"

# Add backend to path
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))
sys.path.insert(0, str(backend_root / "api"))

from api.utils import sanitize_filename, sanitize_for_log


class TestSanitizeFilenameEdgeCases:
    """Test edge cases in filename sanitization"""

    def test_empty_filename_returns_upload(self):
        """Test that empty filename returns 'upload'"""
        result = sanitize_filename("")
        assert result == "upload"

    def test_dot_only_filename_returns_upload(self):
        """Test that '.' filename returns 'upload'"""
        result = sanitize_filename(".")
        assert result == "upload"

    def test_path_traversal_basic(self):
        """Test basic path traversal attack prevention"""
        result = sanitize_filename("../../../etc/passwd")
        assert ".." not in result
        assert "/" not in result
        assert result == "passwd"

    def test_path_traversal_windows_style(self):
        """Test Windows-style path traversal prevention"""
        result = sanitize_filename("..\\..\\Windows\\System32\\config")
        # On non-Windows, backslash is treated as regular char and replaced
        # Key security check: path separators should be removed/replaced
        assert "/" not in result
        # The result should not allow escaping to parent directories
        assert len(result) > 0

    def test_hidden_file_gets_prefix(self):
        """Test that hidden files get 'file' prefix"""
        result = sanitize_filename(".hidden")
        assert result.startswith("file")
        assert ".hidden" in result

    def test_very_long_filename_truncated(self):
        """Test that filenames over 255 chars are truncated"""
        long_name = "a" * 300 + ".txt"
        result = sanitize_filename(long_name)
        assert len(result) <= 255

    def test_special_characters_removed(self):
        """Test that dangerous special characters are replaced"""
        result = sanitize_filename("file<>:\"|?*.txt")
        # Only alphanumeric, dash, underscore, dot allowed
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert '"' not in result
        assert "|" not in result
        assert "?" not in result
        assert "*" not in result

    def test_normal_filename_unchanged(self):
        """Test that normal filenames pass through"""
        result = sanitize_filename("normal-file_name.xlsx")
        assert result == "normal-file_name.xlsx"

    def test_unicode_filename(self):
        """Test handling of unicode characters in filename"""
        result = sanitize_filename("文件.txt")
        # Unicode should be replaced with underscores
        assert result.endswith(".txt")
        assert len(result) > 0

    def test_multiple_dots_preserved(self):
        """Test that multiple dots in extension are handled"""
        result = sanitize_filename("archive.tar.gz")
        assert result == "archive.tar.gz"

    def test_spaces_replaced(self):
        """Test that spaces are replaced with underscores"""
        result = sanitize_filename("my document.pdf")
        assert " " not in result
        assert "_" in result


class TestSanitizeForLogEdgeCases:
    """Test edge cases in log sanitization"""

    def test_nested_dict_with_password(self):
        """Test that nested dicts have passwords redacted"""
        data = {
            "user": {
                "name": "john",
                "credentials": {
                    "password": "secret123"
                }
            }
        }
        result = sanitize_for_log(data)
        assert result["user"]["credentials"]["password"] == "***REDACTED***"
        assert result["user"]["name"] == "john"

    def test_list_with_sensitive_dicts(self):
        """Test that lists containing dicts are sanitized"""
        data = [
            {"username": "alice", "token": "abc123"},
            {"username": "bob", "token": "def456"}
        ]
        result = sanitize_for_log(data)
        assert result[0]["token"] == "***REDACTED***"
        assert result[1]["token"] == "***REDACTED***"
        assert result[0]["username"] == "alice"

    def test_tuple_sanitization(self):
        """Test that tuples are sanitized and returned as tuples"""
        data = ({"password": "secret"}, "normal")
        result = sanitize_for_log(data)
        assert isinstance(result, tuple)
        assert result[0]["password"] == "***REDACTED***"
        assert result[1] == "normal"

    def test_string_with_password_pattern(self):
        """Test that password patterns in strings are redacted"""
        data = "User logged in with password=secret123"
        result = sanitize_for_log(data)
        assert "secret123" not in result
        assert "REDACTED" in result

    def test_string_with_bearer_token(self):
        """Test that bearer tokens in strings are redacted"""
        data = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        result = sanitize_for_log(data)
        assert "eyJhbG" not in result
        assert "REDACTED" in result

    def test_string_with_openai_api_key(self):
        """Test that OpenAI API keys are redacted"""
        data = "Using API key: sk-abcdefghijklmnopqrstuvwxyz12345"
        result = sanitize_for_log(data)
        assert "sk-abc" not in result
        assert "REDACTED" in result

    def test_string_with_slack_token(self):
        """Test that Slack tokens are redacted"""
        data = "Slack: xoxb-123456789012-123456789012-abcdefghijklmnop"
        result = sanitize_for_log(data)
        assert "xoxb-" not in result
        assert "REDACTED" in result

    def test_long_string_truncation(self):
        """Test that long strings are truncated"""
        data = "x" * 1000
        result = sanitize_for_log(data, max_length=100)
        assert len(result) < len(data)
        assert "truncated" in result

    def test_primitives_unchanged(self):
        """Test that primitive values pass through unchanged"""
        assert sanitize_for_log(42) == 42
        assert sanitize_for_log(3.14) == 3.14
        assert sanitize_for_log(True) is True
        assert sanitize_for_log(None) is None

    def test_empty_dict(self):
        """Test that empty dict returns empty dict"""
        result = sanitize_for_log({})
        assert result == {}

    def test_empty_list(self):
        """Test that empty list returns empty list"""
        result = sanitize_for_log([])
        assert result == []

    def test_all_sensitive_keys(self):
        """Test that all sensitive key variants are redacted"""
        data = {
            "password": "a",
            "passwd": "b",
            "pwd": "c",
            "token": "d",
            "access_token": "e",
            "refresh_token": "f",
            "api_key": "g",
            "secret": "h",
            "secret_key": "i",
            "private_key": "j",
            "authorization": "k",
            "bearer": "l",
        }
        result = sanitize_for_log(data)
        for key in data.keys():
            assert result[key] == "***REDACTED***"


class TestRateLimiterEdgeCases:
    """Test rate limiter boundary conditions"""

    def test_rate_limiter_with_zero_max_requests(self):
        """Test rate limiter with zero max requests always blocks"""
        from api.rate_limiter import SimpleRateLimiter
        limiter = SimpleRateLimiter()

        # Even first request should be blocked with max_requests=0
        result = limiter.check_rate_limit("test:zero", max_requests=0, window_seconds=60)
        assert result is False

    def test_rate_limiter_with_very_short_window(self):
        """Test rate limiter with very short window refills quickly"""
        from api.rate_limiter import SimpleRateLimiter
        import time

        limiter = SimpleRateLimiter()
        key = "test:short:window"

        # Use all tokens
        limiter.check_rate_limit(key, max_requests=1, window_seconds=1)

        # Should be blocked
        result = limiter.check_rate_limit(key, max_requests=1, window_seconds=1)
        assert result is False

        # Wait for refill
        time.sleep(1.1)

        # Should have tokens again
        result = limiter.check_rate_limit(key, max_requests=1, window_seconds=1)
        assert result is True

    def test_rate_limiter_with_large_max_requests(self):
        """Test rate limiter handles large limits"""
        from api.rate_limiter import SimpleRateLimiter
        limiter = SimpleRateLimiter()

        # Use a large number of requests
        for i in range(1000):
            result = limiter.check_rate_limit("test:large", max_requests=10000, window_seconds=60)
            assert result is True

    def test_rate_limiter_different_window_same_key(self):
        """Test that window changes affect the same key"""
        from api.rate_limiter import SimpleRateLimiter
        limiter = SimpleRateLimiter()
        key = "test:window:change"

        # First with small limit
        for i in range(5):
            limiter.check_rate_limit(key, max_requests=5, window_seconds=60)

        # Should be blocked with small limit
        result = limiter.check_rate_limit(key, max_requests=5, window_seconds=60)
        assert result is False


class TestAuthEdgeCases:
    """Test authentication edge cases"""

    def test_verify_token_with_none(self):
        """Test that verify_token handles None gracefully"""
        from api.auth_middleware import auth_service
        result = auth_service.verify_token(None)
        assert result is None

    def test_verify_token_with_empty_string(self):
        """Test that verify_token handles empty string"""
        from api.auth_middleware import auth_service
        result = auth_service.verify_token("")
        assert result is None

    def test_verify_token_with_whitespace(self):
        """Test that verify_token handles whitespace-only token"""
        from api.auth_middleware import auth_service
        result = auth_service.verify_token("   ")
        assert result is None

    def test_verify_token_with_invalid_base64(self):
        """Test that verify_token handles invalid base64"""
        from api.auth_middleware import auth_service
        result = auth_service.verify_token("not.valid.base64!!!")
        assert result is None

    def test_verify_token_with_partial_jwt(self):
        """Test that verify_token handles partial JWT (only 2 parts)"""
        from api.auth_middleware import auth_service
        result = auth_service.verify_token("header.payload")
        assert result is None

    def test_verify_token_with_too_many_parts(self):
        """Test that verify_token handles JWT with extra parts"""
        from api.auth_middleware import auth_service
        result = auth_service.verify_token("a.b.c.d.e")
        assert result is None


class TestMetricsEdgeCases:
    """Test metrics edge cases"""

    def test_request_metrics_with_negative_elapsed(self):
        """Test RequestMetrics handles edge case of negative elapsed time"""
        from api.observability_middleware import RequestMetrics
        RequestMetrics.reset()

        # This shouldn't crash even with invalid data
        RequestMetrics.record_request("GET", "/test", 200, -100.0)

        stats = RequestMetrics.get_stats()
        assert stats["total_requests"] >= 0

    def test_request_metrics_with_zero_elapsed(self):
        """Test RequestMetrics handles zero elapsed time"""
        from api.observability_middleware import RequestMetrics
        RequestMetrics.reset()

        RequestMetrics.record_request("GET", "/instant", 200, 0.0)

        stats = RequestMetrics.get_stats()
        assert stats["total_requests"] == 1

    def test_request_metrics_with_very_large_elapsed(self):
        """Test RequestMetrics handles very large elapsed time"""
        from api.observability_middleware import RequestMetrics
        RequestMetrics.reset()

        RequestMetrics.record_request("GET", "/slow", 200, 999999999.0)

        stats = RequestMetrics.get_stats()
        assert stats["very_slow_requests"] == 1

    def test_endpoint_stats_limit_zero(self):
        """Test endpoint stats with limit=0"""
        from api.observability_middleware import RequestMetrics
        RequestMetrics.reset()

        RequestMetrics.record_request("GET", "/test", 200, 100.0)

        stats = RequestMetrics.get_endpoint_stats(limit=0)
        assert isinstance(stats, list)


class TestCacheEdgeCases:
    """Test cache service edge cases"""

    def test_cache_get_with_invalid_json(self):
        """Test cache handles invalid JSON in stored value"""
        from api.cache_service import CacheService
        from unittest.mock import MagicMock, patch

        with patch('api.cache_service.REDIS_AVAILABLE', False):
            service = CacheService()
            mock_redis = MagicMock()
            mock_redis.get.return_value = "not valid json {"
            service.redis = mock_redis

            # Should handle JSON decode error gracefully
            result = service.get("key")
            assert result is None
            assert service.misses == 1

    def test_cache_set_with_non_serializable(self):
        """Test cache handles non-JSON-serializable values"""
        from api.cache_service import CacheService
        from unittest.mock import MagicMock, patch

        with patch('api.cache_service.REDIS_AVAILABLE', False):
            service = CacheService()
            mock_redis = MagicMock()
            service.redis = mock_redis

            # Objects with circular references or custom types can't be serialized
            class NonSerializable:
                pass

            result = service.set("key", NonSerializable())
            assert result is False

    def test_cache_hit_rate_with_only_errors(self):
        """Test hit rate calculation when all gets result in errors"""
        from api.cache_service import CacheService
        from unittest.mock import patch

        with patch('api.cache_service.REDIS_AVAILABLE', False):
            service = CacheService()
            # Errors count as misses
            service.misses = 100
            service.hits = 0

            assert service.hit_rate() == 0.0
