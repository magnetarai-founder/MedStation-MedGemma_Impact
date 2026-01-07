"""
Standard Response Models

Provides consistent response structures for all API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Generic, TypeVar, Optional
from datetime import datetime

T = TypeVar('T')


class SuccessResponse(BaseModel, Generic[T]):
    """
    Standard success response wrapper.

    Wraps all successful API responses with consistent structure.

    Example:
        ```python
        @router.post("/users", response_model=SuccessResponse[UserModel])
        async def create_user(body: CreateUserRequest):
            user = await user_service.create(body)
            return SuccessResponse(
                data=user,
                message="User created successfully"
            )
        ```

    Response:
        ```json
        {
            "success": true,
            "data": { ... },
            "message": "User created successfully",
            "timestamp": "2025-12-13T10:30:00.000Z"
        }
        ```
    """
    success: bool = Field(True, description="Always true for success responses")
    data: T = Field(..., description="Response payload")
    message: Optional[str] = Field(None, description="Optional success message")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp (UTC)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"id": "123", "name": "Example"},
                "message": "Operation completed successfully",
                "timestamp": "2025-12-13T10:30:00.000Z"
            }
        }


class ErrorResponse(BaseModel):
    """
    Standard error response.

    Provides structured error information for client handling.

    Example:
        ```python
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error_code="NOT_FOUND",
                message="User with ID '123' not found",
                details={"resource": "user", "resource_id": "123"}
            ).model_dump()
        )
        ```

    Response:
        ```json
        {
            "success": false,
            "error_code": "NOT_FOUND",
            "message": "User with ID '123' not found",
            "details": {
                "resource": "user",
                "resource_id": "123"
            },
            "timestamp": "2025-12-13T10:30:00.000Z",
            "request_id": null
        }
        ```
    """
    success: bool = Field(False, description="Always false for error responses")
    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict] = Field(None, description="Additional error context")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Error timestamp (UTC)"
    )
    request_id: Optional[str] = Field(None, description="Request ID for debugging")

    def model_dump(self, **kwargs) -> dict:
        """Override model_dump to serialize datetime to ISO format for JSON compatibility."""
        data = super().model_dump(**kwargs)
        if isinstance(data.get("timestamp"), datetime):
            data["timestamp"] = data["timestamp"].isoformat()
        return data

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error_code": "NOT_FOUND",
                "message": "Resource not found",
                "details": {"resource": "user", "resource_id": "123"},
                "timestamp": "2025-12-13T10:30:00.000Z",
                "request_id": "req_abc123"
            }
        }


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Paginated list response.

    Standard structure for list endpoints with pagination.

    Example:
        ```python
        @router.get("/users", response_model=PaginatedResponse[UserModel])
        async def list_users(skip: int = 0, limit: int = 50):
            users, total = await user_service.list(skip, limit)
            return PaginatedResponse(
                data=users,
                total=total,
                skip=skip,
                limit=limit
            )
        ```

    Response:
        ```json
        {
            "success": true,
            "data": [...],
            "total": 100,
            "skip": 0,
            "limit": 50,
            "timestamp": "2025-12-13T10:30:00.000Z"
        }
        ```
    """
    success: bool = Field(True, description="Always true for success responses")
    data: list[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items (all pages)")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Maximum items per page")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp (UTC)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": [{"id": "1", "name": "Item 1"}],
                "total": 100,
                "skip": 0,
                "limit": 50,
                "timestamp": "2025-12-13T10:30:00.000Z"
            }
        }
