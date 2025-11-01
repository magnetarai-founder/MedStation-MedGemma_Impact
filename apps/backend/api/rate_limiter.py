"""
Simple Token Bucket Rate Limiter for ElohimOS
Provides shared rate limiting across all routers
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
