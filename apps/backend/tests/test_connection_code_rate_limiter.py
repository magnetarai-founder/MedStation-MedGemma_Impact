"""
Tests for Connection Code Rate Limiter

SECURITY FEATURE (Dec 2025):
Prevents brute force attacks on connection codes used for P2P pairing.

Tests cover:
- Basic rate limiting (5 attempts per minute)
- Exponential backoff on consecutive failures
- Lockout after 15 total failures
- State cleanup for memory management
"""

import pytest
import time
from unittest.mock import patch

import sys
from pathlib import Path
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))
sys.path.insert(0, str(backend_root / "api"))

from api.rate_limiter import (
    ConnectionCodeLimiter,
    ConnectionCodeState,
    CONNECTION_CODE_MAX_ATTEMPTS,
    CONNECTION_CODE_WINDOW_SECONDS,
    CONNECTION_CODE_LOCKOUT_THRESHOLD,
    CONNECTION_CODE_LOCKOUT_DURATION,
    CONNECTION_CODE_BACKOFF_MULTIPLIER,
    CONNECTION_CODE_MAX_BACKOFF,
    connection_code_limiter
)


# ===== ConnectionCodeState Tests =====

class TestConnectionCodeState:
    """Tests for ConnectionCodeState dataclass"""

    def test_initial_state(self):
        """State should start with zero values"""
        state = ConnectionCodeState()
        assert state.attempts == 0
        assert state.total_failures == 0
        assert state.consecutive_failures == 0
        assert state.lockout_until == 0.0

    def test_is_locked_out_false_initially(self):
        """New state should not be locked out"""
        state = ConnectionCodeState()
        assert state.is_locked_out() is False

    def test_is_locked_out_true_when_set(self):
        """State with future lockout should be locked out"""
        state = ConnectionCodeState()
        state.lockout_until = time.time() + 100
        assert state.is_locked_out() is True

    def test_is_locked_out_false_when_expired(self):
        """State with past lockout should not be locked out"""
        state = ConnectionCodeState()
        state.lockout_until = time.time() - 1
        assert state.is_locked_out() is False

    def test_get_lockout_remaining(self):
        """Lockout remaining should return correct seconds"""
        state = ConnectionCodeState()
        state.lockout_until = time.time() + 60
        remaining = state.get_lockout_remaining()
        assert 58 <= remaining <= 60

    def test_get_lockout_remaining_zero_when_expired(self):
        """Lockout remaining should be 0 when expired"""
        state = ConnectionCodeState()
        state.lockout_until = time.time() - 1
        assert state.get_lockout_remaining() == 0

    def test_get_backoff_delay_zero_initially(self):
        """Backoff should be 0 with no failures"""
        state = ConnectionCodeState()
        assert state.get_backoff_delay() == 0.0

    def test_get_backoff_delay_zero_for_first_failure(self):
        """Backoff should be 0 for first failure"""
        state = ConnectionCodeState()
        state.consecutive_failures = 1
        assert state.get_backoff_delay() == 0.0

    def test_get_backoff_delay_exponential(self):
        """Backoff should increase exponentially"""
        state = ConnectionCodeState()

        # 2 failures: 2^1 = 2 seconds
        state.consecutive_failures = 2
        assert state.get_backoff_delay() == 2.0

        # 3 failures: 2^2 = 4 seconds
        state.consecutive_failures = 3
        assert state.get_backoff_delay() == 4.0

        # 4 failures: 2^3 = 8 seconds
        state.consecutive_failures = 4
        assert state.get_backoff_delay() == 8.0

    def test_get_backoff_delay_capped(self):
        """Backoff should be capped at MAX_BACKOFF"""
        state = ConnectionCodeState()
        state.consecutive_failures = 100  # Would be 2^99 without cap
        assert state.get_backoff_delay() == CONNECTION_CODE_MAX_BACKOFF

    def test_reset_window(self):
        """Reset window should clear attempts and set first_attempt_time"""
        state = ConnectionCodeState()
        state.attempts = 5
        state.reset_window()
        assert state.attempts == 0
        assert state.first_attempt_time > 0


# ===== ConnectionCodeLimiter Tests =====

class TestConnectionCodeLimiter:
    """Tests for ConnectionCodeLimiter class"""

    @pytest.fixture
    def limiter(self):
        """Create a fresh limiter for each test"""
        return ConnectionCodeLimiter()

    def test_first_attempt_allowed(self, limiter):
        """First attempt should always be allowed"""
        allowed, error = limiter.check_attempt("192.168.1.1")
        assert allowed is True
        assert error is None

    def test_attempts_within_limit_allowed(self, limiter):
        """Attempts within limit should be allowed"""
        for i in range(CONNECTION_CODE_MAX_ATTEMPTS):
            allowed, error = limiter.check_attempt("192.168.1.1")
            assert allowed is True, f"Attempt {i+1} should be allowed"
            assert error is None

    def test_attempts_exceed_limit_blocked(self, limiter):
        """Attempts exceeding limit should be blocked"""
        # Use up all attempts
        for _ in range(CONNECTION_CODE_MAX_ATTEMPTS):
            limiter.check_attempt("192.168.1.1")

        # Next attempt should be blocked
        allowed, error = limiter.check_attempt("192.168.1.1")
        assert allowed is False
        assert "Rate limit exceeded" in error

    def test_different_ips_independent(self, limiter):
        """Different IPs should have independent limits"""
        # Use up all attempts for IP 1
        for _ in range(CONNECTION_CODE_MAX_ATTEMPTS):
            limiter.check_attempt("192.168.1.1")

        allowed, _ = limiter.check_attempt("192.168.1.1")
        assert allowed is False  # IP 1 blocked

        # IP 2 should still be allowed
        allowed, error = limiter.check_attempt("192.168.1.2")
        assert allowed is True
        assert error is None

    def test_record_failure_increments_counts(self, limiter):
        """Recording failure should increment failure counts"""
        limiter.check_attempt("192.168.1.1")
        limiter.record_failure("192.168.1.1")

        status = limiter.get_status("192.168.1.1")
        assert status["total_failures"] == 1
        assert status["consecutive_failures"] == 1

    def test_record_success_resets_consecutive(self, limiter):
        """Recording success should reset consecutive failures"""
        limiter.check_attempt("192.168.1.1")
        limiter.record_failure("192.168.1.1")
        limiter.record_failure("192.168.1.1")
        limiter.record_failure("192.168.1.1")

        status = limiter.get_status("192.168.1.1")
        assert status["consecutive_failures"] == 3

        limiter.record_success("192.168.1.1")

        status = limiter.get_status("192.168.1.1")
        assert status["consecutive_failures"] == 0
        # Total failures not reset
        assert status["total_failures"] == 3

    def test_lockout_after_threshold(self, limiter):
        """Lockout should trigger after threshold failures"""
        # Record failures up to threshold
        for _ in range(CONNECTION_CODE_LOCKOUT_THRESHOLD):
            limiter.check_attempt("192.168.1.1")
            limiter.record_failure("192.168.1.1")

        # Should now be locked out
        allowed, error = limiter.check_attempt("192.168.1.1")
        assert allowed is False
        assert "Too many failed attempts" in error

        status = limiter.get_status("192.168.1.1")
        assert status["is_locked_out"] is True

    def test_backoff_blocks_rapid_attempts(self, limiter):
        """Backoff should block rapid attempts after failures"""
        # Record some failures
        for _ in range(3):
            limiter.check_attempt("192.168.1.1")
            limiter.record_failure("192.168.1.1")

        # Next attempt should be blocked by backoff
        # (3 consecutive failures = 4 second backoff)
        allowed, error = limiter.check_attempt("192.168.1.1")
        assert allowed is False
        assert "Please wait" in error

    def test_window_resets_after_time(self, limiter):
        """Window should reset after WINDOW_SECONDS"""
        # Use up all attempts
        for _ in range(CONNECTION_CODE_MAX_ATTEMPTS):
            limiter.check_attempt("192.168.1.1")

        # Mock time to simulate window expiry
        state = limiter._get_state("192.168.1.1")
        state.first_attempt_time = time.time() - CONNECTION_CODE_WINDOW_SECONDS - 1

        # Should be allowed again
        allowed, error = limiter.check_attempt("192.168.1.1")
        assert allowed is True
        assert error is None

    def test_reset_clears_all_states(self, limiter):
        """Reset should clear all tracked states"""
        limiter.check_attempt("192.168.1.1")
        limiter.check_attempt("192.168.1.2")
        limiter.record_failure("192.168.1.1")

        limiter.reset()

        # States should be cleared
        allowed, _ = limiter.check_attempt("192.168.1.1")
        assert allowed is True

        status = limiter.get_status("192.168.1.1")
        assert status["total_failures"] == 0

    def test_get_status_returns_all_fields(self, limiter):
        """get_status should return complete status info"""
        limiter.check_attempt("192.168.1.1")
        limiter.record_failure("192.168.1.1")

        status = limiter.get_status("192.168.1.1")

        assert "client_ip" in status
        assert "attempts_in_window" in status
        assert "max_attempts" in status
        assert "total_failures" in status
        assert "consecutive_failures" in status
        assert "is_locked_out" in status
        assert "lockout_remaining" in status
        assert "backoff_delay" in status


# ===== Global Instance Tests =====

class TestGlobalConnectionCodeLimiter:
    """Tests for the global connection_code_limiter instance"""

    def setup_method(self):
        """Reset limiter before each test"""
        connection_code_limiter.reset()

    def test_global_instance_exists(self):
        """Global instance should be available"""
        assert connection_code_limiter is not None

    def test_global_instance_works(self):
        """Global instance should function correctly"""
        allowed, error = connection_code_limiter.check_attempt("10.0.0.1")
        assert allowed is True
        assert error is None


# ===== Integration Tests =====

class TestConnectionCodeRateLimiterIntegration:
    """Integration tests simulating real attack scenarios"""

    @pytest.fixture
    def limiter(self):
        """Create a fresh limiter for each test"""
        return ConnectionCodeLimiter()

    def test_brute_force_attack_blocked(self, limiter):
        """Simulated brute force attack should be blocked"""
        attacker_ip = "evil.attacker.com"

        # Directly record failures to simulate brute force attack
        # In reality, these would come from failed code lookups
        for i in range(CONNECTION_CODE_LOCKOUT_THRESHOLD):
            # Simulate a valid attempt followed by failure
            state = limiter._get_state(attacker_ip)
            state.consecutive_failures = 0  # Clear backoff to allow attempt
            state.first_attempt_time = 0  # Reset window

            allowed, _ = limiter.check_attempt(attacker_ip)
            if allowed:
                limiter.record_failure(attacker_ip)

        # Attacker should now be locked out
        status = limiter.get_status(attacker_ip)
        assert status["total_failures"] >= CONNECTION_CODE_LOCKOUT_THRESHOLD
        assert status["is_locked_out"] is True

        # Further attempts should be blocked
        allowed, error = limiter.check_attempt(attacker_ip)
        assert allowed is False
        assert "Too many failed attempts" in error

    def test_legitimate_user_not_affected(self, limiter):
        """Legitimate user making occasional attempts should not be blocked"""
        legitimate_ip = "good.user.home"

        # Simulate 3 failed attempts (typos)
        for _ in range(3):
            limiter.check_attempt(legitimate_ip)
            limiter.record_failure(legitimate_ip)

        # Wait for backoff (simulated)
        state = limiter._get_state(legitimate_ip)
        state.last_attempt_time = time.time() - CONNECTION_CODE_MAX_BACKOFF - 1

        # Should still be allowed
        allowed, error = limiter.check_attempt(legitimate_ip)
        assert allowed is True
        assert error is None

    def test_lockout_expires(self, limiter):
        """Lockout should expire after duration"""
        ip = "192.168.1.1"

        # Trigger lockout by recording threshold failures
        for _ in range(CONNECTION_CODE_LOCKOUT_THRESHOLD):
            state = limiter._get_state(ip)
            state.consecutive_failures = 0  # Clear backoff
            state.first_attempt_time = 0  # Reset window

            allowed, _ = limiter.check_attempt(ip)
            if allowed:
                limiter.record_failure(ip)

        # Verify locked out
        assert limiter.get_status(ip)["is_locked_out"] is True
        allowed, error = limiter.check_attempt(ip)
        assert allowed is False
        assert "Too many failed attempts" in error

        # Simulate lockout expiry
        state = limiter._get_state(ip)
        state.lockout_until = time.time() - 1  # Expired
        state.consecutive_failures = 0  # Clear backoff
        state.first_attempt_time = 0  # Reset window

        # Should be allowed again after lockout expires
        allowed, error = limiter.check_attempt(ip)
        assert allowed is True
        assert error is None
