"""
Global error handlers for FastAPI application.

Implements secure error handling that:
- Never exposes stack traces or internal details to clients
- Logs full errors internally for debugging
- Returns consistent, sanitized error responses
"""

import logging
import traceback
from typing import Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    """
    Register global error handlers on the app.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """
        Handle FastAPI HTTPException.

        - 4xx errors: Return the error detail (client errors are safe to expose)
        - 5xx errors: Log internally, return generic message
        """
        # Extract user info for logging if available
        user_id = getattr(request.state, "user_id", "anonymous")

        # Log all errors for debugging
        logger.warning(
            "HTTP %d: %s | path=%s | user=%s",
            exc.status_code,
            exc.detail,
            request.url.path,
            user_id
        )

        # For 5xx errors, don't expose the actual detail
        if exc.status_code >= 500:
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": True,
                    "status_code": exc.status_code,
                    "message": "An internal error occurred. Please try again later."
                }
            )

        # 4xx errors - safe to expose detail
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "status_code": exc.status_code,
                "message": exc.detail
            }
        )

    @app.exception_handler(StarletteHTTPException)
    async def starlette_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """Handle Starlette HTTPException (used for 404s, etc.)"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "status_code": exc.status_code,
                "message": exc.detail if exc.status_code < 500 else "An internal error occurred"
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Catch-all handler for unhandled exceptions.

        NEVER expose internal error details to clients.
        Log the full stack trace internally for debugging.
        """
        # Extract user info for logging if available
        user_id = getattr(request.state, "user_id", "anonymous")

        # Log the full exception with stack trace for internal debugging
        logger.exception(
            "Unhandled exception | path=%s | user=%s | type=%s",
            request.url.path,
            user_id,
            type(exc).__name__
        )

        # Also log to stderr in development
        import os
        if os.getenv("ENVIRONMENT", "development") == "development":
            traceback.print_exc()

        # Return generic error - NEVER expose internal details
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "status_code": 500,
                "message": "An unexpected error occurred. Please try again later."
            }
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        """Handle ValueError as a 400 Bad Request."""
        logger.warning("ValueError: %s | path=%s", str(exc), request.url.path)
        return JSONResponse(
            status_code=400,
            content={
                "error": True,
                "status_code": 400,
                "message": str(exc)
            }
        )

    @app.exception_handler(PermissionError)
    async def permission_error_handler(request: Request, exc: PermissionError) -> JSONResponse:
        """Handle PermissionError as a 403 Forbidden."""
        user_id = getattr(request.state, "user_id", "anonymous")
        logger.warning("PermissionError: %s | path=%s | user=%s", str(exc), request.url.path, user_id)
        return JSONResponse(
            status_code=403,
            content={
                "error": True,
                "status_code": 403,
                "message": "You do not have permission to perform this action"
            }
        )

    @app.exception_handler(FileNotFoundError)
    async def file_not_found_handler(request: Request, exc: FileNotFoundError) -> JSONResponse:
        """Handle FileNotFoundError as a 404 Not Found."""
        logger.warning("FileNotFoundError: %s | path=%s", str(exc), request.url.path)
        return JSONResponse(
            status_code=404,
            content={
                "error": True,
                "status_code": 404,
                "message": "The requested resource was not found"
            }
        )
