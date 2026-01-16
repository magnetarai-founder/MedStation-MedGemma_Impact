"""
Compatibility Shim for Rate Limiter

The implementation now lives in the `api.security` package:
- api.security.rate_limiter: RateLimiter, ConnectionCodeLimiter

This shim maintains backward compatibility.
"""

from api.security.rate_limiter import (
    RateLimiter,
    rate_limiter,
    get_client_ip,
    ConnectionCodeLimiter,
    connection_code_limiter,
)

__all__ = [
    "RateLimiter",
    "rate_limiter",
    "get_client_ip",
    "ConnectionCodeLimiter",
    "connection_code_limiter",
]
