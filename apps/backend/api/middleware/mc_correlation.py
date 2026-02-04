"""
Correlation ID Middleware

Adds correlation IDs to all requests for distributed tracing.
Correlation IDs help track requests across services and log aggregation.

Features:
- Generates unique correlation ID for each request
- Accepts correlation ID from X-Correlation-ID header
- Adds correlation ID to response headers
- Makes correlation ID available in request.state
- Integrates with structured logging
"""

import uuid
from contextvars import ContextVar

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Context variable for storing correlation ID
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add correlation IDs to all requests.

    Usage:
        app.add_middleware(CorrelationIDMiddleware)
    """

    async def dispatch(self, request: Request, call_next):
        """Add correlation ID to request and response"""

        # Get or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")

        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Store in request state
        request.state.correlation_id = correlation_id

        # Store in context var (accessible anywhere in request lifecycle)
        correlation_id_var.set(correlation_id)

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        return response


def get_correlation_id() -> str:
    """
    Get the current request's correlation ID.

    Returns:
        Correlation ID string or empty string if not set

    Usage:
        from api.middleware.correlation import get_correlation_id

        correlation_id = get_correlation_id()
        logger.info("Processing request", correlation_id=correlation_id)
    """
    return correlation_id_var.get()
