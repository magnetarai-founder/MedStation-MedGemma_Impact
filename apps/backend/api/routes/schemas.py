"""
Shared schema types used by route modules.
"""

from enum import Enum
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None


class ErrorResponse:
    """Standardized error response format"""

    @staticmethod
    def bad_request(message: str, details: dict | None = None):
        from fastapi import HTTPException
        return HTTPException(
            status_code=400,
            detail={"message": message, "details": details or {}},
        )

    @staticmethod
    def unauthorized(message: str = "Unauthorized"):
        from fastapi import HTTPException
        return HTTPException(status_code=401, detail=message)

    @staticmethod
    def not_found(message: str = "Not found"):
        from fastapi import HTTPException
        return HTTPException(status_code=404, detail=message)

    @staticmethod
    def internal_error(message: str = "Internal server error"):
        from fastapi import HTTPException
        return HTTPException(status_code=500, detail=message)


try:
    from api.errors.codes_data import ErrorCode
except ImportError:
    class ErrorCode(str, Enum):
        AUTH_INVALID_CREDENTIALS = "ERR-1001"
        MODEL_NOT_FOUND = "ERR-2001"
        GENERAL_ERROR = "ERR-9999"


__all__ = ["SuccessResponse", "ErrorResponse", "ErrorCode"]
