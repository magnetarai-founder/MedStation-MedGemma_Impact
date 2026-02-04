"""
Reusable decorators for API endpoints.

Eliminates duplication in error handling, validation, and common patterns.
"""

import functools
from collections.abc import Callable
from pathlib import Path

from fastapi import HTTPException

from api.utils.structured_logging import get_logger

logger = get_logger(__name__)


def handle_api_errors(func: Callable) -> Callable:
    """
    Decorator to handle common API errors with standardized responses.

    Catches common exceptions and converts them to HTTPExceptions.
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=f"File not found: {e!s}")
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=f"Permission denied: {e!s}")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid value: {e!s}")
        except KeyError as e:
            raise HTTPException(status_code=400, detail=f"Missing required field: {e!s}")
        except TimeoutError as e:
            raise HTTPException(status_code=504, detail=f"Request timeout: {e!s}")
        except Exception as e:
            # Log unexpected errors
            logger.error(f"Unexpected error in {func.__name__}: {type(e).__name__}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    return wrapper


def require_workspace(func: Callable) -> Callable:
    """
    Decorator to validate workspace_path parameter exists and is accessible.

    Expects function to have a 'workspace_path' parameter (str or Path).
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        workspace_path = kwargs.get("workspace_path")
        if not workspace_path:
            raise HTTPException(status_code=400, detail="workspace_path parameter is required")

        workspace = Path(workspace_path)
        if not workspace.exists():
            raise HTTPException(status_code=404, detail=f"Workspace not found: {workspace_path}")

        if not workspace.is_dir():
            raise HTTPException(
                status_code=400, detail=f"Workspace path is not a directory: {workspace_path}"
            )

        return await func(*args, **kwargs)

    return wrapper


def validate_pagination(
    max_limit: int = 100, default_limit: int = 20, max_offset: int = 10000
) -> Callable:
    """
    Decorator to validate and set defaults for pagination parameters.

    Args:
        max_limit: Maximum allowed limit value
        default_limit: Default limit if not provided
        max_offset: Maximum allowed offset value
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Validate and set limit
            limit = kwargs.get("limit", default_limit)
            if limit < 1:
                raise HTTPException(status_code=400, detail="Limit must be at least 1")
            if limit > max_limit:
                raise HTTPException(status_code=400, detail=f"Limit cannot exceed {max_limit}")
            kwargs["limit"] = limit

            # Validate offset
            offset = kwargs.get("offset", 0)
            if offset < 0:
                raise HTTPException(status_code=400, detail="Offset cannot be negative")
            if offset > max_offset:
                raise HTTPException(status_code=400, detail=f"Offset cannot exceed {max_offset}")

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def rate_limit_with_feedback(limit: str, error_message: str | None = None) -> Callable:
    """
    Decorator to add rate limiting with custom error message.

    Args:
        limit: Rate limit string (e.g., "10/minute")
        error_message: Custom error message when rate limit exceeded
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Rate limiting is handled by slowapi middleware
            # This decorator adds custom error messaging
            try:
                return await func(*args, **kwargs)
            except HTTPException as e:
                if e.status_code == 429:
                    detail = error_message or f"Rate limit exceeded: {limit}"
                    raise HTTPException(status_code=429, detail=detail)
                raise

        return wrapper

    return decorator


def log_endpoint_access(func: Callable) -> Callable:
    """
    Decorator to log endpoint access for audit purposes.

    Logs: endpoint name, timestamp, user (if available), result.
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        import time
        from datetime import datetime

        start_time = time.time()
        endpoint = func.__name__
        timestamp = datetime.utcnow().isoformat()

        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time

            # Log successful access
            logger.info("AUDIT", endpoint=endpoint, status="success", duration_s=f"{duration:.2f}")

            return result
        except Exception as e:
            duration = time.time() - start_time

            # Log failed access
            logger.warning(
                "AUDIT",
                endpoint=endpoint,
                status="failed",
                error=type(e).__name__,
                duration_s=f"{duration:.2f}",
            )

            raise

    return wrapper
