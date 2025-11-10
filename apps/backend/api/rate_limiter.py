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
"""

from collections import defaultdict
from time import time
from typing import Dict


class SimpleRateLimiter:
    """
    Token bucket rate limiter

    Usage:
        if not rate_limiter.check_rate_limit(f"endpoint:{client_ip}", max_requests=10, window_seconds=60):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
    """

    def __init__(self):
        self.buckets: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"tokens": 0, "last_update": time()}
        )

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
        bucket = self.buckets[key]

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
