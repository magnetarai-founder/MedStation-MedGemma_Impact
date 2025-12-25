"""
Simple Token Bucket Rate Limiter for ElohimOS
Provides shared rate limiting across all routers

USAGE PATTERN FOR NEW ENDPOINTS:
================================

1. Import the rate limiter and helper:
   from rate_limiter import rate_limiter, get_client_ip

2. Apply rate limiting in your endpoint:
   @router.post("/sensitive-endpoint")
   async def my_endpoint(request: Request, body: MyRequest):
       # Rate limit check
       client_ip = get_client_ip(request)
       if not rate_limiter.check_rate_limit(
           f"my_endpoint:{client_ip}",
           max_requests=10,
           window_seconds=60
       ):
           raise HTTPException(
               status_code=429,
               detail="Rate limit exceeded. Max 10 requests per minute."
           )

       # Your endpoint logic here
       ...

RECOMMENDED RATE LIMITS:
========================
- Admin/sensitive endpoints: 5-10 requests/minute
- Panic/emergency endpoints: 5 requests/hour
- Monitoring/stats endpoints: 60 requests/minute
- Normal API endpoints: 100 requests/minute
- File uploads: 10 requests/minute

EXAMPLES IN CODEBASE:
=====================
- panic_mode_router.py:71 - 5 triggers/hour
- monitoring_routes.py:36 - 60 health checks/minute
- team_service.py:2996 - 10 join attempts/minute
- main.py:642 - 60 SQL queries/minute

CONNECTION CODE RATE LIMITING (Dec 2025):
=========================================
For connection code verification, use ConnectionCodeLimiter:
- 5 attempts per minute per IP
- Exponential backoff on consecutive failures
- Lockout after 15 total failures (5 min lockout)

Example:
    from rate_limiter import connection_code_limiter, get_client_ip

    client_ip = get_client_ip(request)
    allowed, error = connection_code_limiter.check_attempt(client_ip)
    if not allowed:
        raise HTTPException(status_code=429, detail=error)

    # On failure:
    connection_code_limiter.record_failure(client_ip)

    # On success:
    connection_code_limiter.record_success(client_ip)
"""

from collections import defaultdict
from dataclasses import dataclass, field
from time import time
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class SimpleRateLimiter:
    """
    Token bucket rate limiter

    Usage:
        if not rate_limiter.check_rate_limit(f"endpoint:{client_ip}", max_requests=10, window_seconds=60):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
    """

    def __init__(self):
        # Use an explicit dict so we can properly initialize
        # each bucket with a full token count on first use.
        self.buckets: Dict[str, Dict[str, float]] = {}

    def check_rate_limit(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """
        Check if request is within rate limit

        Args:
            key: Unique identifier for this rate limit bucket (e.g., "panic:192.168.1.1")
            max_requests: Maximum number of requests allowed in the window
            window_seconds: Time window in seconds

        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        now = time()
        bucket = self.buckets.get(key)

        # Initialize bucket on first use with a full token bucket so
        # the very first request is always allowed for a new key.
        if bucket is None:
            bucket = {"tokens": float(max_requests), "last_update": now}
            self.buckets[key] = bucket

        # Refill tokens based on time passed
        time_passed = now - bucket["last_update"]
        bucket["tokens"] = min(
            max_requests,
            bucket["tokens"] + (time_passed * max_requests / window_seconds)
        )
        bucket["last_update"] = now

        # Check if we have tokens
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True
        return False


# Global rate limiter instance
rate_limiter = SimpleRateLimiter()


def get_client_ip(request) -> str:
    """Extract client IP from request"""
    return request.client.host if request.client else "unknown"


def is_dev_mode(request) -> bool:
    """
    Detect if request is from development environment

    Checks for:
    1. ELOHIM_ENV=development env var
    2. Localhost/127.0.0.1 requests
    3. Development security warning (means dev mode)

    Returns:
        True if development mode, False otherwise
    """
    import os

    # Check env var first
    if os.getenv("ELOHIM_ENV") == "development":
        return True

    # Check if request is from localhost
    client_ip = get_client_ip(request)
    if client_ip in ("127.0.0.1", "localhost", "::1"):
        return True

    # If no founder password is set, we're in dev mode
    if not os.getenv("ELOHIM_FOUNDER_PASSWORD"):
        return True

    return False


# ============================================================================
# CONNECTION CODE RATE LIMITING (Dec 2025)
# ============================================================================
# Specialized rate limiting for connection code verification to prevent
# brute force attacks. Features:
# - Per-IP sliding window rate limiting
# - Exponential backoff on consecutive failures
# - Automatic lockout after threshold
# ============================================================================

# Configuration
CONNECTION_CODE_MAX_ATTEMPTS = 5  # Max attempts per window
CONNECTION_CODE_WINDOW_SECONDS = 60  # 1 minute window
CONNECTION_CODE_LOCKOUT_THRESHOLD = 15  # Total failures before lockout
CONNECTION_CODE_LOCKOUT_DURATION = 300  # 5 minute lockout
CONNECTION_CODE_BACKOFF_MULTIPLIER = 2  # Exponential backoff base
CONNECTION_CODE_MAX_BACKOFF = 30  # Max backoff seconds


@dataclass
class ConnectionCodeState:
    """Tracks rate limit state for connection code attempts"""
    attempts: int = 0
    first_attempt_time: float = 0.0
    last_attempt_time: float = 0.0
    total_failures: int = 0
    consecutive_failures: int = 0
    lockout_until: float = 0.0

    def reset_window(self) -> None:
        """Reset the sliding window"""
        self.attempts = 0
        self.first_attempt_time = time()

    def is_locked_out(self) -> bool:
        """Check if client is locked out"""
        return time() < self.lockout_until

    def get_lockout_remaining(self) -> int:
        """Get remaining lockout seconds"""
        return max(0, int(self.lockout_until - time()))

    def get_backoff_delay(self) -> float:
        """Calculate exponential backoff delay"""
        if self.consecutive_failures <= 1:
            return 0.0
        return min(
            CONNECTION_CODE_BACKOFF_MULTIPLIER ** (self.consecutive_failures - 1),
            CONNECTION_CODE_MAX_BACKOFF
        )


class ConnectionCodeLimiter:
    """
    Specialized rate limiter for connection code verification.

    SECURITY FEATURES (Dec 2025):
    - 5 attempts per minute per IP
    - Exponential backoff (2^n seconds, max 30s)
    - Lockout after 15 total failures (5 min)
    - Logging of suspicious activity
    """

    def __init__(self) -> None:
        self._states: Dict[str, ConnectionCodeState] = {}
        self._cleanup_interval = 300
        self._last_cleanup = time()

    def _get_state(self, client_ip: str) -> ConnectionCodeState:
        """Get or create state for client"""
        if client_ip not in self._states:
            self._states[client_ip] = ConnectionCodeState()
        return self._states[client_ip]

    def _cleanup_stale(self) -> None:
        """Remove stale states to prevent memory growth"""
        now = time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        self._last_cleanup = now
        stale_threshold = now - (CONNECTION_CODE_WINDOW_SECONDS * 10)

        stale = [
            ip for ip, state in self._states.items()
            if state.last_attempt_time < stale_threshold and not state.is_locked_out()
        ]

        for ip in stale:
            del self._states[ip]

        if stale:
            logger.info(f"🧹 Cleaned {len(stale)} stale connection code states")

    def check_attempt(self, client_ip: str) -> Tuple[bool, Optional[str]]:
        """
        Check if connection code attempt is allowed.

        Returns:
            Tuple of (allowed, error_message)
        """
        self._cleanup_stale()
        state = self._get_state(client_ip)
        now = time()

        # Check lockout
        if state.is_locked_out():
            remaining = state.get_lockout_remaining()
            logger.warning(f"⛔ Connection code lockout: {client_ip} ({remaining}s)")
            return False, f"Too many failed attempts. Try again in {remaining} seconds."

        # Check backoff
        backoff = state.get_backoff_delay()
        if backoff > 0:
            since_last = now - state.last_attempt_time
            if since_last < backoff:
                wait = int(backoff - since_last) + 1
                return False, f"Please wait {wait} seconds before trying again."

        # Check sliding window
        if state.first_attempt_time == 0 or (now - state.first_attempt_time) > CONNECTION_CODE_WINDOW_SECONDS:
            state.reset_window()

        state.attempts += 1
        state.last_attempt_time = now

        if state.attempts > CONNECTION_CODE_MAX_ATTEMPTS:
            logger.warning(f"⚠ Connection code rate limit: {client_ip} ({state.attempts} attempts)")
            return False, f"Rate limit exceeded. Maximum {CONNECTION_CODE_MAX_ATTEMPTS} attempts per minute."

        return True, None

    def record_failure(self, client_ip: str) -> None:
        """Record a failed connection code attempt"""
        state = self._get_state(client_ip)
        state.total_failures += 1
        state.consecutive_failures += 1

        if state.total_failures >= CONNECTION_CODE_LOCKOUT_THRESHOLD:
            state.lockout_until = time() + CONNECTION_CODE_LOCKOUT_DURATION
            logger.warning(
                f"🔒 Connection code lockout: {client_ip} "
                f"({state.total_failures} failures, {CONNECTION_CODE_LOCKOUT_DURATION}s)"
            )

    def record_success(self, client_ip: str) -> None:
        """Record a successful connection code attempt"""
        state = self._get_state(client_ip)
        state.consecutive_failures = 0

    def get_status(self, client_ip: str) -> Dict:
        """Get rate limit status for client (debugging)"""
        state = self._get_state(client_ip)
        return {
            "client_ip": client_ip,
            "attempts_in_window": state.attempts,
            "max_attempts": CONNECTION_CODE_MAX_ATTEMPTS,
            "total_failures": state.total_failures,
            "consecutive_failures": state.consecutive_failures,
            "is_locked_out": state.is_locked_out(),
            "lockout_remaining": state.get_lockout_remaining(),
            "backoff_delay": state.get_backoff_delay()
        }

    def reset(self) -> None:
        """Reset all states (for testing)"""
        self._states.clear()


# Global connection code limiter instance
connection_code_limiter = ConnectionCodeLimiter()
