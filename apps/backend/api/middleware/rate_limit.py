"""
Rate limiting middleware configuration.

Uses slowapi for rate limiting with decorator-based limits on sensitive endpoints.
File upload endpoints are NOT rate limited to avoid compatibility issues.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# Create limiter instance - no default limits (we apply limits per-endpoint)
limiter = Limiter(key_func=get_remote_address)


async def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom handler for rate limit exceeded errors.

    Returns a JSON response with retry-after header.
    """
    retry_after = exc.detail.split("per")[-1].strip() if exc.detail else "1 minute"
    return JSONResponse(
        status_code=429,
        content={
            "error": True,
            "status_code": 429,
            "message": f"Too many requests. Please try again in {retry_after}.",
            "retry_after": retry_after
        },
        headers={"Retry-After": "60"}
    )


def configure_rate_limiting(app: FastAPI) -> Limiter:
    """
    Initialize and attach the rate limiter to the app.

    Rate limiting strategy:
    - Authentication endpoints: Strict limits (5/minute for login, 3/minute for register)
    - Regular API endpoints: No global limit (handled per-endpoint if needed)
    - File upload endpoints: No limits (would cause issues with large uploads)

    Args:
        app: FastAPI application instance

    Returns:
        Limiter instance for use in endpoint decorators
    """
    # Attach limiter to app state for access in routes
    app.state.limiter = limiter

    # Register the rate limit exceeded exception handler
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    return limiter


# Common rate limit strings for use in decorators
RATE_LIMITS = {
    # Authentication - strict limits to prevent brute force
    "login": "5/minute",           # 5 login attempts per minute
    "register": "3/minute",        # 3 registration attempts per minute
    "password_reset": "3/minute",  # 3 password reset requests per minute
    "token_refresh": "10/minute",  # 10 token refreshes per minute

    # Sensitive operations
    "vault_unlock": "10/minute",   # 10 vault unlock attempts per minute
    "webauthn": "5/minute",        # 5 WebAuthn operations per minute

    # General API - more lenient
    "api_read": "100/minute",      # 100 read operations per minute
    "api_write": "30/minute",      # 30 write operations per minute

    # Search/compute heavy
    "search": "20/minute",         # 20 search operations per minute
    "ai_chat": "30/minute",        # 30 AI chat messages per minute
}
