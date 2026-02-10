"""
Tests for rate_limiter.py - Token Bucket and Connection Code Rate Limiting

Tests cover:
- SimpleRateLimiter token bucket accuracy
- Rate limit window enforcement
- Token refill over time
- First request always allowed
- get_client_ip function
- is_dev_mode function
- ConnectionCodeState dataclass methods
- ConnectionCodeLimiter check/record/lockout behavior
- Exponential backoff calculation
- Sliding window behavior
- Stale state cleanup
- Edge cases and concurrent usage
"""

import pytest
import time
from unittest.mock import MagicMock, patch
from dataclasses import dataclass

from api.rate_limiter import (
    SimpleRateLimiter,
    rate_limiter,
    get_client_ip,
    is_dev_mode,
    ConnectionCodeState,
    ConnectionCodeLimiter,
    connection_code_limiter,
    CONNECTION_CODE_MAX_ATTEMPTS,
    CONNECTION_CODE_WINDOW_SECONDS,
    CONNECTION_CODE_LOCKOUT_THRESHOLD,
    CONNECTION_CODE_LOCKOUT_DURATION,
    CONNECTION_CODE_BACKOFF_MULTIPLIER,
    CONNECTION_CODE_MAX_BACKOFF,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def limiter():
    """Create a fresh SimpleRateLimiter instance"""
    return SimpleRateLimiter()


@pytest.fixture
def cc_limiter():
    """Create a fresh ConnectionCodeLimiter instance"""
    limiter = ConnectionCodeLimiter()
    yield limiter
    limiter.reset()


@pytest.fixture
def mock_request():
    """Create a mock request object with client IP"""
    request = MagicMock()
    request.client = MagicMock()
    request.client.host = "192.168.1.100"
    return request


@pytest.fixture
def mock_request_localhost():
    """Create a mock request object from localhost"""
    request = MagicMock()
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    return request


@pytest.fixture
def mock_request_no_client():
    """Create a mock request object with no client"""
    request = MagicMock()
    request.client = None
    return request


# =============================================================================
# SimpleRateLimiter Tests
# =============================================================================

class TestSimpleRateLimiter:
    """Tests for the SimpleRateLimiter token bucket implementation"""

    def test_first_request_allowed(self, limiter):
        """Test that the first request for a new key is always allowed"""
        result = limiter.check_rate_limit("test_key", max_requests=5, window_seconds=60)
        assert result is True

    def test_requests_within_limit_allowed(self, limiter):
        """Test that requests within the limit are allowed"""
        for i in range(5):
            result = limiter.check_rate_limit("test_key", max_requests=5, window_seconds=60)
            assert result is True, f"Request {i+1} should be allowed"

    def test_requests_exceeding_limit_blocked(self, limiter):
        """Test that requests exceeding the limit are blocked"""
        # Use up all tokens
        for i in range(5):
            limiter.check_rate_limit("test_key", max_requests=5, window_seconds=60)

        # Next request should be blocked
        result = limiter.check_rate_limit("test_key", max_requests=5, window_seconds=60)
        assert result is False

    def test_different_keys_independent(self, limiter):
        """Test that different keys have independent rate limits"""
        # Exhaust key1
        for _ in range(5):
            limiter.check_rate_limit("key1", max_requests=5, window_seconds=60)

        # key2 should still be allowed
        result = limiter.check_rate_limit("key2", max_requests=5, window_seconds=60)
        assert result is True

    def test_tokens_refill_over_time(self, limiter):
        """Test that tokens refill over time"""
        # Use all tokens
        for _ in range(5):
            limiter.check_rate_limit("test_key", max_requests=5, window_seconds=1)

        # Should be blocked
        assert limiter.check_rate_limit("test_key", max_requests=5, window_seconds=1) is False

        # Wait for refill (1 second window, 5 tokens = 1 token per 0.2 seconds)
        time.sleep(0.25)

        # Should have at least 1 token now
        result = limiter.check_rate_limit("test_key", max_requests=5, window_seconds=1)
        assert result is True

    def test_bucket_initialization(self, limiter):
        """Test that bucket is properly initialized on first use"""
        # Check internal state after first request
        limiter.check_rate_limit("new_key", max_requests=10, window_seconds=60)

        assert "new_key" in limiter.buckets
        bucket = limiter.buckets["new_key"]
        # After one request, tokens should be max_requests - 1 = 9
        assert bucket["tokens"] >= 8  # Allow for small timing variations
        assert bucket["tokens"] <= 10

    def test_tokens_capped_at_max(self, limiter):
        """Test that tokens don't exceed max_requests"""
        # Make one request
        limiter.check_rate_limit("test_key", max_requests=5, window_seconds=1)

        # Wait a long time
        time.sleep(2)

        # Make another request - tokens should be capped at max
        limiter.check_rate_limit("test_key", max_requests=5, window_seconds=1)
        bucket = limiter.buckets["test_key"]

        # After waiting 2 seconds and making 1 request, we should have
        # min(5, many_tokens) - 1 = 4 tokens
        assert bucket["tokens"] <= 5
        assert bucket["tokens"] >= 3

    def test_high_rate_limit(self, limiter):
        """Test with high rate limit values"""
        for i in range(100):
            result = limiter.check_rate_limit("high_rate", max_requests=100, window_seconds=60)
            assert result is True

        # 101st request should be blocked
        result = limiter.check_rate_limit("high_rate", max_requests=100, window_seconds=60)
        assert result is False

    def test_low_rate_limit(self, limiter):
        """Test with very low rate limit (1 request)"""
        # First request allowed
        assert limiter.check_rate_limit("low_rate", max_requests=1, window_seconds=60) is True

        # Second request blocked
        assert limiter.check_rate_limit("low_rate", max_requests=1, window_seconds=60) is False

    def test_short_window(self, limiter):
        """Test with very short time window"""
        # Use token
        limiter.check_rate_limit("short_window", max_requests=1, window_seconds=0.1)

        # Blocked immediately
        assert limiter.check_rate_limit("short_window", max_requests=1, window_seconds=0.1) is False

        # Wait for refill
        time.sleep(0.15)

        # Should be allowed now
        assert limiter.check_rate_limit("short_window", max_requests=1, window_seconds=0.1) is True

    def test_partial_token_refill(self, limiter):
        """Test partial token refill calculation"""
        # 10 requests per 10 seconds = 1 token per second
        for _ in range(10):
            limiter.check_rate_limit("partial", max_requests=10, window_seconds=10)

        # Should be blocked
        assert limiter.check_rate_limit("partial", max_requests=10, window_seconds=10) is False

        # Wait 0.5 seconds (should get ~0.5 tokens)
        time.sleep(0.5)

        # Still blocked (need 1 full token)
        assert limiter.check_rate_limit("partial", max_requests=10, window_seconds=10) is False

        # Wait another 0.6 seconds (total ~1.1 seconds, should have ~1 token)
        time.sleep(0.6)

        # Should be allowed now
        assert limiter.check_rate_limit("partial", max_requests=10, window_seconds=10) is True


# =============================================================================
# Global Rate Limiter Tests
# =============================================================================

class TestGlobalRateLimiter:
    """Tests for the global rate_limiter instance"""

    def test_global_instance_exists(self):
        """Test that global rate_limiter is a SimpleRateLimiter"""
        assert isinstance(rate_limiter, SimpleRateLimiter)

    def test_global_instance_functional(self):
        """Test that global instance works correctly"""
        # Use unique key to avoid conflicts with other tests
        key = f"global_test_{time.time()}"
        result = rate_limiter.check_rate_limit(key, max_requests=5, window_seconds=60)
        assert result is True


# =============================================================================
# get_client_ip Tests
# =============================================================================

class TestGetClientIP:
    """Tests for the get_client_ip helper function"""

    def test_get_client_ip_normal(self, mock_request):
        """Test extracting IP from normal request"""
        ip = get_client_ip(mock_request)
        assert ip == "192.168.1.100"

    def test_get_client_ip_localhost(self, mock_request_localhost):
        """Test extracting localhost IP"""
        ip = get_client_ip(mock_request_localhost)
        assert ip == "127.0.0.1"

    def test_get_client_ip_no_client(self, mock_request_no_client):
        """Test handling request with no client"""
        ip = get_client_ip(mock_request_no_client)
        assert ip == "unknown"

    def test_get_client_ip_ipv6(self):
        """Test extracting IPv6 address"""
        request = MagicMock()
        request.client = MagicMock()
        request.client.host = "2001:db8::1"
        ip = get_client_ip(request)
        assert ip == "2001:db8::1"


# =============================================================================
# is_dev_mode Tests
# =============================================================================

class TestIsDevMode:
    """Tests for the is_dev_mode helper function"""

    def test_dev_mode_env_var(self, mock_request):
        """Test dev mode detection via environment variable"""
        with patch.dict("os.environ", {"MEDSTATION_ENV": "development"}):
            assert is_dev_mode(mock_request) is True

    def test_not_dev_mode_production_env(self, mock_request):
        """Test production mode with env var set"""
        with patch.dict("os.environ", {
            "MEDSTATION_ENV": "production",
            "MEDSTATION_FOUNDER_PASSWORD": "secret123"
        }, clear=True):
            assert is_dev_mode(mock_request) is False

    def test_dev_mode_localhost(self, mock_request_localhost):
        """Test dev mode detection via localhost"""
        with patch.dict("os.environ", {"MEDSTATION_FOUNDER_PASSWORD": "secret"}, clear=True):
            assert is_dev_mode(mock_request_localhost) is True

    def test_dev_mode_ipv6_localhost(self):
        """Test dev mode detection via IPv6 localhost"""
        request = MagicMock()
        request.client = MagicMock()
        request.client.host = "::1"
        with patch.dict("os.environ", {"MEDSTATION_FOUNDER_PASSWORD": "secret"}, clear=True):
            assert is_dev_mode(request) is True

    def test_dev_mode_no_founder_password(self, mock_request):
        """Test dev mode when no founder password is set"""
        with patch.dict("os.environ", {}, clear=True):
            assert is_dev_mode(mock_request) is True


# =============================================================================
# ConnectionCodeState Tests
# =============================================================================

class TestConnectionCodeState:
    """Tests for the ConnectionCodeState dataclass"""

    def test_default_values(self):
        """Test default values for ConnectionCodeState"""
        state = ConnectionCodeState()
        assert state.attempts == 0
        assert state.first_attempt_time == 0.0
        assert state.last_attempt_time == 0.0
        assert state.total_failures == 0
        assert state.consecutive_failures == 0
        assert state.lockout_until == 0.0

    def test_reset_window(self):
        """Test reset_window method"""
        state = ConnectionCodeState(attempts=5, first_attempt_time=1000.0)
        state.reset_window()
        assert state.attempts == 0
        assert state.first_attempt_time > 0  # Should be set to current time

    def test_is_locked_out_false(self):
        """Test is_locked_out returns False when not locked"""
        state = ConnectionCodeState()
        assert state.is_locked_out() is False

    def test_is_locked_out_true(self):
        """Test is_locked_out returns True when locked"""
        state = ConnectionCodeState(lockout_until=time.time() + 100)
        assert state.is_locked_out() is True

    def test_is_locked_out_expired(self):
        """Test is_locked_out returns False when lockout expired"""
        state = ConnectionCodeState(lockout_until=time.time() - 1)
        assert state.is_locked_out() is False

    def test_get_lockout_remaining(self):
        """Test get_lockout_remaining calculation"""
        state = ConnectionCodeState(lockout_until=time.time() + 60)
        remaining = state.get_lockout_remaining()
        assert 58 <= remaining <= 60

    def test_get_lockout_remaining_expired(self):
        """Test get_lockout_remaining when expired"""
        state = ConnectionCodeState(lockout_until=time.time() - 10)
        assert state.get_lockout_remaining() == 0

    def test_get_backoff_delay_no_failures(self):
        """Test backoff delay with no failures"""
        state = ConnectionCodeState(consecutive_failures=0)
        assert state.get_backoff_delay() == 0.0

    def test_get_backoff_delay_first_failure(self):
        """Test backoff delay after first failure"""
        state = ConnectionCodeState(consecutive_failures=1)
        # 2^(1-1) = 2^0 = 1 second
        assert state.get_backoff_delay() == 1.0

    def test_get_backoff_delay_second_failure(self):
        """Test backoff delay after second failure"""
        state = ConnectionCodeState(consecutive_failures=2)
        # 2^(2-1) = 2^1 = 2 seconds
        assert state.get_backoff_delay() == 2.0

    def test_get_backoff_delay_exponential(self):
        """Test exponential backoff pattern"""
        delays = []
        for failures in range(1, 6):
            state = ConnectionCodeState(consecutive_failures=failures)
            delays.append(state.get_backoff_delay())

        # Should be 1, 2, 4, 8, 16
        assert delays == [1.0, 2.0, 4.0, 8.0, 16.0]

    def test_get_backoff_delay_capped(self):
        """Test that backoff delay is capped at max"""
        state = ConnectionCodeState(consecutive_failures=10)
        delay = state.get_backoff_delay()
        assert delay == CONNECTION_CODE_MAX_BACKOFF  # 30 seconds max


# =============================================================================
# ConnectionCodeLimiter Tests
# =============================================================================

class TestConnectionCodeLimiter:
    """Tests for the ConnectionCodeLimiter class"""

    def test_first_attempt_allowed(self, cc_limiter):
        """Test that first attempt is always allowed"""
        allowed, error = cc_limiter.check_attempt("192.168.1.1")
        assert allowed is True
        assert error is None

    def test_attempts_within_limit_allowed(self, cc_limiter):
        """Test that attempts within limit are allowed"""
        for i in range(CONNECTION_CODE_MAX_ATTEMPTS):
            allowed, error = cc_limiter.check_attempt("192.168.1.1")
            assert allowed is True, f"Attempt {i+1} should be allowed"
            assert error is None

    def test_attempts_exceeding_limit_blocked(self, cc_limiter):
        """Test that attempts exceeding limit are blocked"""
        # Use up all attempts
        for _ in range(CONNECTION_CODE_MAX_ATTEMPTS):
            cc_limiter.check_attempt("192.168.1.1")

        # Next attempt should be blocked
        allowed, error = cc_limiter.check_attempt("192.168.1.1")
        assert allowed is False
        assert "Rate limit exceeded" in error

    def test_different_ips_independent(self, cc_limiter):
        """Test that different IPs have independent limits"""
        # Exhaust IP1
        for _ in range(CONNECTION_CODE_MAX_ATTEMPTS + 1):
            cc_limiter.check_attempt("192.168.1.1")

        # IP2 should still be allowed
        allowed, error = cc_limiter.check_attempt("192.168.1.2")
        assert allowed is True

    def test_record_failure_increments_counters(self, cc_limiter):
        """Test that record_failure increments failure counters"""
        cc_limiter.check_attempt("192.168.1.1")
        cc_limiter.record_failure("192.168.1.1")

        status = cc_limiter.get_status("192.168.1.1")
        assert status["total_failures"] == 1
        assert status["consecutive_failures"] == 1

    def test_record_success_resets_consecutive(self, cc_limiter):
        """Test that record_success resets consecutive failures"""
        cc_limiter.check_attempt("192.168.1.1")
        cc_limiter.record_failure("192.168.1.1")
        cc_limiter.record_failure("192.168.1.1")

        status = cc_limiter.get_status("192.168.1.1")
        assert status["consecutive_failures"] == 2

        cc_limiter.record_success("192.168.1.1")

        status = cc_limiter.get_status("192.168.1.1")
        assert status["consecutive_failures"] == 0
        assert status["total_failures"] == 2  # Total not reset

    def test_lockout_after_threshold(self, cc_limiter):
        """Test that lockout is triggered after threshold failures"""
        # Record enough failures to trigger lockout
        for _ in range(CONNECTION_CODE_LOCKOUT_THRESHOLD):
            cc_limiter.check_attempt("192.168.1.1")
            cc_limiter.record_failure("192.168.1.1")

        status = cc_limiter.get_status("192.168.1.1")
        assert status["is_locked_out"] is True
        assert status["lockout_remaining"] > 0

    def test_lockout_blocks_attempts(self, cc_limiter):
        """Test that lockout blocks all attempts"""
        # Trigger lockout
        for _ in range(CONNECTION_CODE_LOCKOUT_THRESHOLD):
            cc_limiter.check_attempt("192.168.1.1")
            cc_limiter.record_failure("192.168.1.1")

        # Attempt should be blocked
        allowed, error = cc_limiter.check_attempt("192.168.1.1")
        assert allowed is False
        assert "Too many failed attempts" in error

    def test_backoff_blocks_rapid_attempts(self, cc_limiter):
        """Test that backoff blocks rapid attempts after failure"""
        cc_limiter.check_attempt("192.168.1.1")
        cc_limiter.record_failure("192.168.1.1")

        # Immediate retry should be blocked due to backoff
        allowed, error = cc_limiter.check_attempt("192.168.1.1")
        assert allowed is False
        assert "wait" in error.lower()

    def test_backoff_allows_after_delay(self, cc_limiter):
        """Test that attempt is allowed after backoff delay"""
        cc_limiter.check_attempt("192.168.1.1")
        cc_limiter.record_failure("192.168.1.1")

        # Wait for backoff (1 second for first failure)
        time.sleep(1.1)

        allowed, error = cc_limiter.check_attempt("192.168.1.1")
        assert allowed is True

    def test_sliding_window_reset(self, cc_limiter):
        """Test that sliding window resets after window expires"""
        # Use all attempts
        for _ in range(CONNECTION_CODE_MAX_ATTEMPTS):
            cc_limiter.check_attempt("192.168.1.1")

        # Should be blocked
        allowed, _ = cc_limiter.check_attempt("192.168.1.1")
        assert allowed is False

        # Mock time passing beyond window
        state = cc_limiter._get_state("192.168.1.1")
        state.first_attempt_time = time.time() - CONNECTION_CODE_WINDOW_SECONDS - 1

        # Should be allowed now (window reset)
        allowed, error = cc_limiter.check_attempt("192.168.1.1")
        assert allowed is True

    def test_get_status(self, cc_limiter):
        """Test get_status returns correct information"""
        cc_limiter.check_attempt("192.168.1.1")
        cc_limiter.record_failure("192.168.1.1")

        status = cc_limiter.get_status("192.168.1.1")

        assert status["client_ip"] == "192.168.1.1"
        assert status["attempts_in_window"] == 1
        assert status["max_attempts"] == CONNECTION_CODE_MAX_ATTEMPTS
        assert status["total_failures"] == 1
        assert status["consecutive_failures"] == 1
        assert status["is_locked_out"] is False
        assert status["lockout_remaining"] == 0
        assert status["backoff_delay"] == 1.0

    def test_reset_clears_all_states(self, cc_limiter):
        """Test that reset() clears all states"""
        cc_limiter.check_attempt("192.168.1.1")
        cc_limiter.check_attempt("192.168.1.2")

        cc_limiter.reset()

        # Both should be fresh
        status1 = cc_limiter.get_status("192.168.1.1")
        status2 = cc_limiter.get_status("192.168.1.2")

        assert status1["attempts_in_window"] == 0
        assert status2["attempts_in_window"] == 0

    def test_cleanup_stale_states(self, cc_limiter):
        """Test that stale states are cleaned up"""
        # Create some states
        cc_limiter.check_attempt("192.168.1.1")
        cc_limiter.check_attempt("192.168.1.2")

        # Make state stale
        stale_threshold = time.time() - (CONNECTION_CODE_WINDOW_SECONDS * 10 + 1)
        cc_limiter._states["192.168.1.1"].last_attempt_time = stale_threshold

        # Force cleanup by setting last_cleanup to old time
        cc_limiter._last_cleanup = time.time() - cc_limiter._cleanup_interval - 1

        # Trigger cleanup via check_attempt
        cc_limiter.check_attempt("192.168.1.3")

        # Stale state should be removed (192.168.1.1)
        # Fresh state should remain (192.168.1.2)
        assert "192.168.1.1" not in cc_limiter._states
        assert "192.168.1.2" in cc_limiter._states

    def test_locked_out_state_not_cleaned(self, cc_limiter):
        """Test that locked out states are not cleaned up"""
        # Create locked out state
        cc_limiter.check_attempt("192.168.1.1")
        for _ in range(CONNECTION_CODE_LOCKOUT_THRESHOLD):
            cc_limiter.record_failure("192.168.1.1")

        # Make it "stale" by timestamp
        stale_threshold = time.time() - (CONNECTION_CODE_WINDOW_SECONDS * 10 + 1)
        cc_limiter._states["192.168.1.1"].last_attempt_time = stale_threshold

        # Force cleanup
        cc_limiter._last_cleanup = time.time() - cc_limiter._cleanup_interval - 1
        cc_limiter.check_attempt("192.168.1.2")

        # Locked out state should NOT be removed
        assert "192.168.1.1" in cc_limiter._states


# =============================================================================
# Global ConnectionCodeLimiter Tests
# =============================================================================

class TestGlobalConnectionCodeLimiter:
    """Tests for the global connection_code_limiter instance"""

    def test_global_instance_exists(self):
        """Test that global connection_code_limiter exists"""
        assert isinstance(connection_code_limiter, ConnectionCodeLimiter)

    def test_global_instance_functional(self):
        """Test that global instance works correctly"""
        # Use unique IP to avoid conflicts
        test_ip = f"test_{time.time()}"
        allowed, error = connection_code_limiter.check_attempt(test_ip)
        assert allowed is True


# =============================================================================
# Integration Tests
# =============================================================================

class TestRateLimiterIntegration:
    """Integration tests for rate limiting scenarios"""

    def test_api_endpoint_pattern(self, limiter, mock_request):
        """Test typical API endpoint rate limiting pattern"""
        client_ip = get_client_ip(mock_request)
        endpoint = "my_endpoint"

        # Simulate 10 requests (limit is 10)
        for i in range(10):
            key = f"{endpoint}:{client_ip}"
            result = limiter.check_rate_limit(key, max_requests=10, window_seconds=60)
            assert result is True, f"Request {i+1} should be allowed"

        # 11th request blocked
        result = limiter.check_rate_limit(f"{endpoint}:{client_ip}", max_requests=10, window_seconds=60)
        assert result is False

    def test_connection_code_brute_force_protection(self, cc_limiter):
        """Test protection against connection code brute force"""
        client_ip = "attacker_ip"

        # Simulate brute force attempt - rapid-fire requests
        blocked_count = 0
        failure_count = 0
        for i in range(20):
            allowed, error = cc_limiter.check_attempt(client_ip)
            if not allowed:
                blocked_count += 1
            else:
                # Only record failure when attempt was allowed (simulates wrong code entered)
                cc_limiter.record_failure(client_ip)
                failure_count += 1

        # Should have been blocked multiple times by exponential backoff
        # After the first failure, backoff kicks in and blocks rapid-fire attempts
        assert blocked_count > 0, "Brute force attempts should be blocked by backoff"

        # At least one failure should have been recorded (the first attempt)
        assert failure_count >= 1, "At least one failure should be recorded"

        # Verify the limiter is correctly enforcing backoff/lockout
        status = cc_limiter.get_status(client_ip)
        # The key metric is that rapid attempts are being blocked
        assert status["consecutive_failures"] >= 1, "Consecutive failures should be tracked"

    def test_legitimate_user_pattern(self, cc_limiter):
        """Test that legitimate users are not blocked"""
        client_ip = "legit_user"

        # User tries once, fails, waits appropriately, tries again, succeeds
        allowed1, _ = cc_limiter.check_attempt(client_ip)
        assert allowed1 is True

        cc_limiter.record_failure(client_ip)

        # Wait for backoff
        time.sleep(1.1)

        allowed2, _ = cc_limiter.check_attempt(client_ip)
        assert allowed2 is True

        cc_limiter.record_success(client_ip)

        # After success, no more backoff
        allowed3, _ = cc_limiter.check_attempt(client_ip)
        assert allowed3 is True


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""

    def test_zero_max_requests(self, limiter):
        """Test behavior with zero max requests"""
        # This is an edge case - should block all requests
        result = limiter.check_rate_limit("zero_limit", max_requests=0, window_seconds=60)
        assert result is False

    def test_empty_key(self, limiter):
        """Test behavior with empty key"""
        result = limiter.check_rate_limit("", max_requests=5, window_seconds=60)
        assert result is True  # Should still work

    def test_special_characters_in_key(self, limiter):
        """Test keys with special characters"""
        special_key = "endpoint:192.168.1.1:user@example.com"
        result = limiter.check_rate_limit(special_key, max_requests=5, window_seconds=60)
        assert result is True

    def test_unicode_key(self, limiter):
        """Test keys with unicode characters"""
        unicode_key = "endpoint:日本語:テスト"
        result = limiter.check_rate_limit(unicode_key, max_requests=5, window_seconds=60)
        assert result is True

    def test_very_large_window(self, limiter):
        """Test with very large window"""
        result = limiter.check_rate_limit("large_window", max_requests=5, window_seconds=86400)
        assert result is True

    def test_concurrent_access(self, limiter):
        """Test concurrent access doesn't cause issues"""
        import threading

        results = []
        key = "concurrent_test"

        def make_request():
            result = limiter.check_rate_limit(key, max_requests=10, window_seconds=60)
            results.append(result)

        threads = [threading.Thread(target=make_request) for _ in range(15)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have 10 True and 5 False
        assert results.count(True) == 10
        assert results.count(False) == 5

    def test_connection_code_concurrent_access(self, cc_limiter):
        """Test ConnectionCodeLimiter with concurrent access"""
        import threading

        results = []
        client_ip = "concurrent_cc_test"

        def make_attempt():
            allowed, _ = cc_limiter.check_attempt(client_ip)
            results.append(allowed)

        threads = [threading.Thread(target=make_attempt) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have CONNECTION_CODE_MAX_ATTEMPTS True results
        assert results.count(True) == CONNECTION_CODE_MAX_ATTEMPTS
