# API Design Standards - MagnetarStudio

**Date:** 2025-12-13
**Status:** ✅ Defined
**Priority:** 3 - API Design & Consistency

---

## 🎯 Overview

This document defines the standards for all MagnetarStudio API endpoints to ensure consistency, maintainability, and excellent developer experience.

**Guiding Principles:**
1. **Consistency** - Same patterns across all endpoints
2. **Type Safety** - Pydantic models for all requests/responses
3. **Clear Errors** - Structured, actionable error messages
4. **RESTful** - Proper HTTP methods and status codes
5. **Self-Documenting** - Clear naming and automatic OpenAPI docs

---

## 📋 Standards Summary

| Area | Standard | Status |
|------|----------|--------|
| Response Format | `SuccessResponse<T>` + `ErrorResponse` | To Implement |
| Status Codes | HTTP 201/204/4xx/5xx properly used | To Implement |
| Request Validation | Always use Pydantic models | To Implement |
| Error Handling | Structured error codes + messages | To Implement |
| URL Prefixes | `/api/v1/{resource}` | Partially Done |
| Naming Conventions | `{feature}_{operation}_{resource}` | Mostly Done |
| Authentication | `Depends(get_current_user)` | Mostly Done |

---

## 1. Response Format Standard

### Success Responses

**Always use typed response models:**

```python
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional
from datetime import datetime

T = TypeVar('T')

class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response wrapper"""
    success: bool = True
    data: T
    message: Optional[str] = None
    timestamp: datetime = datetime.utcnow()

# Usage:
@router.post("/users", response_model=SuccessResponse[UserModel])
async def create_user(body: CreateUserRequest) -> SuccessResponse[UserModel]:
    result = await user_service.create(body)
    return SuccessResponse(
        data=result,
        message="User created successfully"
    )
```

**Response structure:**
```json
{
  "success": true,
  "data": { ... },
  "message": "User created successfully",
  "timestamp": "2025-12-13T10:30:00.000Z"
}
```

### Error Responses

**Always use structured error responses:**

```python
class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = False
    error_code: str  # e.g., "NOT_FOUND", "VALIDATION_ERROR"
    message: str
    details: Optional[dict] = None
    timestamp: datetime = datetime.utcnow()
    request_id: Optional[str] = None  # For debugging

# Usage:
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail=ErrorResponse(
        error_code="NOT_FOUND",
        message="User with ID '123' not found",
        details={"resource": "user", "resource_id": "123"}
    ).model_dump()
)
```

**Error response structure:**
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
  "request_id": "req_abc123"
}
```

---

## 2. HTTP Status Codes

### Standard Status Code Usage

| Status Code | When to Use | Example |
|-------------|-------------|---------|
| **200 OK** | Successful GET, PUT, PATCH | `GET /users/{id}` |
| **201 Created** | Successful POST that creates resource | `POST /users` |
| **204 No Content** | Successful DELETE or update with no body | `DELETE /users/{id}` |
| **400 Bad Request** | Invalid request data, validation error | Missing required field |
| **401 Unauthorized** | Missing or invalid authentication | No JWT token |
| **403 Forbidden** | Authenticated but not authorized | No permission |
| **404 Not Found** | Resource doesn't exist | `GET /users/999` |
| **409 Conflict** | Resource conflict (duplicate) | Email already exists |
| **422 Unprocessable Entity** | Pydantic validation error | Type mismatch |
| **429 Too Many Requests** | Rate limit exceeded | Too many login attempts |
| **500 Internal Server Error** | Unexpected server error | Database crash |
| **502 Bad Gateway** | Upstream service failed | Ollama unavailable |
| **503 Service Unavailable** | Service temporarily down | Maintenance mode |

### Always Use Status Constants

```python
from fastapi import status

# GOOD:
@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(...):
    ...

raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail=...
)

# BAD (don't use raw numbers):
@router.post("/users", status_code=201)
raise HTTPException(status_code=404, detail=...)
```

---

## 3. Request Validation

### Always Use Pydantic Models

**GOOD:**
```python
from pydantic import BaseModel, Field

class CreateUserRequest(BaseModel):
    """Create user request"""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    role: str = Field("user", regex="^(user|admin)$")

@router.post("/users")
async def create_user(
    body: CreateUserRequest,  # ← Automatic validation!
    current_user: User = Depends(get_current_user)
):
    return await user_service.create(body)
```

**BAD (never do this):**
```python
@router.post("/users")
async def create_user(
    request: Request,  # ← Don't use Request for body
    current_user: User = Depends(get_current_user)
):
    body_data = await request.json()  # ← Manual parsing
    body = CreateUserRequest(**body_data)  # ← Manual validation
```

### Query Parameter Validation

```python
from fastapi import Query

@router.get("/users")
async def list_users(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    sort_by: str = Query("created_at", regex="^(created_at|updated_at|username)$"),
    role: Optional[str] = Query(None, regex="^(user|admin)$")
):
    return await user_service.list(skip=skip, limit=limit, sort_by=sort_by, role=role)
```

---

## 4. Error Handling

### Error Code Classification

```python
# Define standard error codes (api/errors.py)
class ErrorCode(str, Enum):
    # Client errors (4xx)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    CONFLICT = "CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"

    # Server errors (5xx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    GATEWAY_ERROR = "GATEWAY_ERROR"
```

### Custom Exception Classes

```python
# api/errors.py
class APIError(Exception):
    """Base API error"""
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int,
        details: Optional[dict] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)

class NotFoundError(APIError):
    """Resource not found"""
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            code=ErrorCode.NOT_FOUND,
            message=f"{resource} with ID '{resource_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource": resource, "resource_id": resource_id}
        )

class ValidationError(APIError):
    """Request validation error"""
    def __init__(self, field: str, error: str):
        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"Validation error on field '{field}': {error}",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"field": field, "error": error}
        )
```

### Error Handling Pattern

```python
@router.post("/users")
async def create_user(body: CreateUserRequest):
    try:
        return await user_service.create(body)

    except NotFoundError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=ErrorResponse(
                error_code=e.code,
                message=e.message,
                details=e.details
            ).model_dump()
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=ErrorResponse(
                error_code=e.code,
                message=e.message,
                details=e.details
            ).model_dump()
        )

    except HTTPException:
        raise  # Re-raise FastAPI exceptions as-is

    except Exception as e:
        logger.error(f"Unexpected error creating user", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="An unexpected error occurred while creating user",
                # Do NOT expose e.message in production!
            ).model_dump()
        )
```

**Key Rules:**
- ✅ **Never** expose raw exception messages (`str(e)`) in production
- ✅ **Always** log full exceptions with `exc_info=True`
- ✅ **Always** use structured error codes for client handling
- ✅ **Always** re-raise HTTPException without modification

---

## 5. URL Prefixes

### Standard Prefix: `/api/v1/{resource}`

**All routers must use versioned prefix:**

```python
from fastapi import APIRouter

router = APIRouter(
    prefix="/api/v1/users",  # ← Always include /api/v1
    tags=["users"]
)
```

### Sub-Router Pattern

```python
# api/routes/chat/__init__.py
router = APIRouter(
    prefix="/api/v1/chat",
    tags=["chat"],
    dependencies=[Depends(get_current_user)]
)

# Include sub-routers (they inherit prefix)
from .sessions import router as sessions_router
from .messages import router as messages_router

router.include_router(sessions_router)  # No prefix needed
router.include_router(messages_router)
```

```python
# api/routes/chat/sessions.py
router = APIRouter()  # No prefix - inherits /api/v1/chat

@router.post("/sessions")  # Full path: /api/v1/chat/sessions
async def create_session(...):
    ...
```

---

## 6. Naming Conventions

### Endpoint Name Format

**Pattern:** `{feature}_{operation}_{resource}`

```python
# Examples:
@router.get("/sessions", name="chat_get_sessions")
@router.post("/sessions", name="chat_create_session")
@router.put("/sessions/{id}", name="chat_update_session")
@router.delete("/sessions/{id}", name="chat_delete_session")

@router.get("/users/me", name="users_get_current")
@router.post("/users", name="users_create")

@router.post("/vault/unlock", name="vault_unlock_biometric")
```

### Function Name Format

**NO `_endpoint` suffix - use descriptive verb + noun:**

```python
# GOOD:
async def create_session(...):
async def get_user_profile(...):
async def delete_vault_item(...):

# BAD:
async def create_session_endpoint(...):  # ← No suffix!
async def get_current_user_endpoint(...):
```

### Resource Naming

- Use **plural** for collections: `/users`, `/sessions`, `/items`
- Use **singular** for single resource: `/users/{id}`, `/profile/me`
- Use **kebab-case** for multi-word: `/api/v1/user-profiles`

---

## 7. Authentication & Authorization

### Router-Level Protection

**Use for blanket protection:**

```python
router = APIRouter(
    prefix="/api/v1/users",
    tags=["users"],
    dependencies=[Depends(get_current_user)]  # All endpoints require auth
)
```

### Endpoint-Level Protection

**Use for fine-grained permissions:**

```python
@router.post("/admin/reset", name="admin_reset")
@require_perm("system.manage_settings")
async def reset_system(
    current_user: User = Depends(get_current_user)
):
    ...
```

### Explicit Dependency Injection

```python
# ALWAYS use Depends() for authentication
async def my_endpoint(
    current_user: User = Depends(get_current_user)  # ← Explicit!
):
    ...

# NEVER skip Depends()
async def my_endpoint(request: Request):  # ← Missing auth!
    ...
```

---

## 8. File Organization

### Recommended Structure

```
api/
├── routes/
│   ├── __init__.py          # Main router aggregator
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── requests.py      # All request models
│   │   ├── responses.py     # SuccessResponse, ErrorResponse
│   │   └── errors.py        # Error codes, custom exceptions
│   ├── chat/
│   │   ├── __init__.py      # Chat router aggregator
│   │   ├── sessions.py      # Session CRUD
│   │   ├── messages.py      # Message operations
│   │   └── models.py        # Model management
│   ├── users.py
│   ├── vault_auth.py
│   └── team.py
├── services/               # Business logic (no HTTP)
│   ├── users.py
│   ├── chat.py
│   └── vault.py
└── errors.py              # Custom exception classes
```

### Schema Organization

```python
# api/routes/schemas/requests.py
from pydantic import BaseModel, Field

class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3)
    email: str
    role: str = "user"

class UpdateUserRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=3)
    email: Optional[str] = None

# api/routes/schemas/responses.py
from typing import TypeVar, Generic
from pydantic import BaseModel

T = TypeVar('T')

class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    message: Optional[str] = None

class UserModel(BaseModel):
    id: str
    username: str
    email: str
    role: str
    created_at: datetime
```

---

## 9. Code Examples

### Example: Full CRUD Endpoint

```python
# api/routes/users.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from api.auth_middleware import get_current_user, User
from api.permissions import require_perm
from api.routes.schemas.requests import CreateUserRequest, UpdateUserRequest
from api.routes.schemas.responses import SuccessResponse, ErrorResponse, UserModel
from api.services import users as user_service
from api.errors import NotFoundError, ValidationError
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/users",
    tags=["users"],
    dependencies=[Depends(get_current_user)]
)

# CREATE
@router.post(
    "",
    response_model=SuccessResponse[UserModel],
    status_code=status.HTTP_201_CREATED,
    name="users_create"
)
async def create_user(
    body: CreateUserRequest,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[UserModel]:
    """Create a new user"""
    try:
        result = await user_service.create(body, current_user.id)
        return SuccessResponse(data=result, message="User created successfully")

    except ValidationError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=ErrorResponse(
                error_code=e.code,
                message=e.message,
                details=e.details
            ).model_dump()
        )

    except Exception as e:
        logger.error(f"Failed to create user", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="INTERNAL_ERROR",
                message="Failed to create user"
            ).model_dump()
        )

# READ (List)
@router.get(
    "",
    response_model=SuccessResponse[List[UserModel]],
    name="users_list"
)
async def list_users(
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records"),
    role: Optional[str] = Query(None, regex="^(user|admin)$"),
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[List[UserModel]]:
    """List all users with pagination"""
    try:
        users = await user_service.list(skip=skip, limit=limit, role=role)
        return SuccessResponse(
            data=users,
            message=f"Found {len(users)} users"
        )
    except Exception as e:
        logger.error(f"Failed to list users", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="INTERNAL_ERROR",
                message="Failed to list users"
            ).model_dump()
        )

# READ (Single)
@router.get(
    "/{user_id}",
    response_model=SuccessResponse[UserModel],
    name="users_get"
)
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[UserModel]:
    """Get user by ID"""
    try:
        user = await user_service.get(user_id)
        return SuccessResponse(data=user)

    except NotFoundError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=ErrorResponse(
                error_code=e.code,
                message=e.message,
                details=e.details
            ).model_dump()
        )

    except Exception as e:
        logger.error(f"Failed to get user {user_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="INTERNAL_ERROR",
                message="Failed to get user"
            ).model_dump()
        )

# UPDATE
@router.put(
    "/{user_id}",
    response_model=SuccessResponse[UserModel],
    name="users_update"
)
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[UserModel]:
    """Update user by ID"""
    try:
        result = await user_service.update(user_id, body)
        return SuccessResponse(data=result, message="User updated successfully")

    except NotFoundError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=ErrorResponse(
                error_code=e.code,
                message=e.message,
                details=e.details
            ).model_dump()
        )

    except Exception as e:
        logger.error(f"Failed to update user {user_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="INTERNAL_ERROR",
                message="Failed to update user"
            ).model_dump()
        )

# DELETE
@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    name="users_delete"
)
@require_perm("users.delete")
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete user by ID (requires permission)"""
    try:
        await user_service.delete(user_id)
        return  # 204 has no response body

    except NotFoundError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=ErrorResponse(
                error_code=e.code,
                message=e.message,
                details=e.details
            ).model_dump()
        )

    except Exception as e:
        logger.error(f"Failed to delete user {user_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="INTERNAL_ERROR",
                message="Failed to delete user"
            ).model_dump()
        )
```

---

## 10. Migration Checklist

### For Each Endpoint:

- [ ] Uses typed response model (`response_model=SuccessResponse[T]`)
- [ ] Uses Pydantic request models (no manual `request.json()`)
- [ ] Uses correct HTTP status code (`status_code=`)
- [ ] Uses status constants (`status.HTTP_*`)
- [ ] Has proper error handling with error codes
- [ ] Has authentication (`Depends(get_current_user)`)
- [ ] Has correct URL prefix (`/api/v1/...`)
- [ ] Has consistent naming (`{feature}_{operation}_{resource}`)
- [ ] Logs errors with `exc_info=True`
- [ ] Never exposes raw exception messages

### For Each Router:

- [ ] Has correct prefix (`prefix="/api/v1/resource"`)
- [ ] Has tags (`tags=["resource"]`)
- [ ] Has auth dependency if needed (`dependencies=[Depends(...)]`)
- [ ] Imports from `api.routes.schemas.*`

---

## 11. Testing Standards

### Test Every Endpoint

```python
# tests/test_users_api.py
import pytest
from fastapi.testclient import TestClient

def test_create_user_success(client: TestClient, auth_token: str):
    """Test successful user creation"""
    response = client.post(
        "/api/v1/users",
        json={"username": "testuser", "email": "test@example.com"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["success"] == True
    assert "data" in data
    assert data["data"]["username"] == "testuser"

def test_create_user_validation_error(client: TestClient, auth_token: str):
    """Test user creation with invalid data"""
    response = client.post(
        "/api/v1/users",
        json={"username": "ab"},  # Too short
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 422  # Pydantic validation
    data = response.json()
    assert "detail" in data

def test_get_user_not_found(client: TestClient, auth_token: str):
    """Test getting non-existent user"""
    response = client.get(
        "/api/v1/users/999",
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 404
    data = response.json()
    assert data["success"] == False
    assert data["error_code"] == "NOT_FOUND"
```

---

## 12. Documentation

### OpenAPI/Swagger Auto-Generation

FastAPI automatically generates docs from your code:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

**Make it better with descriptions:**

```python
@router.post(
    "/users",
    response_model=SuccessResponse[UserModel],
    status_code=status.HTTP_201_CREATED,
    name="users_create",
    summary="Create a new user",
    description="""
    Create a new user account with the provided information.

    Requires authentication and will set the creator as the user's manager.

    Returns the created user with generated ID and timestamps.
    """,
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Validation error"},
        401: {"description": "Not authenticated"},
        409: {"description": "User already exists"}
    }
)
async def create_user(body: CreateUserRequest):
    ...
```

---

## ✅ Summary

**Priority 3 (API Design & Consistency) Standards:**

1. ✅ **Response Format** - SuccessResponse<T> + ErrorResponse
2. ✅ **Status Codes** - Proper HTTP codes with constants
3. ✅ **Request Validation** - Always Pydantic models
4. ✅ **Error Handling** - Structured error codes + messages
5. ✅ **URL Prefixes** - /api/v1/{resource}
6. ✅ **Naming** - Consistent conventions
7. ✅ **Authentication** - Explicit Depends()
8. ✅ **File Organization** - Clean separation
9. ✅ **Testing** - Comprehensive coverage
10. ✅ **Documentation** - Auto-generated + enhanced

**Next Steps:**
1. Create base schemas (SuccessResponse, ErrorResponse, Error codes)
2. Migrate high-traffic endpoints first
3. Add comprehensive tests
4. Update documentation
5. Move to Priority 4 (Testing Infrastructure)

---

**Status:** ✅ Standards Defined
**Date:** 2025-12-13
**Ready for:** Implementation
