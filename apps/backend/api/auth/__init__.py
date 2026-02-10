"""
Authentication Package

Provides authentication and authorization for MedStation:
- AuthService: Core authentication with JWT tokens
- User model and session management
- Rate limiting and security middleware
- Founder bootstrap utilities
"""

from api.auth.middleware import (
    AuthService,
    auth_service,
    User,
    get_current_user,
    get_current_user_optional,
    extract_websocket_token,
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_EXPIRATION_MINUTES,
)
from api.auth.types import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    ChangePasswordFirstLoginRequest,
    LoginResponse,
    UserResponse,
)
from api.auth.bootstrap import (
    ensure_dev_founder_user,
    create_founder_user_explicit,
)

__all__ = [
    # Core classes
    "AuthService",
    "auth_service",
    "User",
    # Authentication functions
    "get_current_user",
    "get_current_user_optional",
    "extract_websocket_token",
    # Constants
    "JWT_SECRET",
    "JWT_ALGORITHM",
    "JWT_EXPIRATION_MINUTES",
    # Request/Response models
    "RegisterRequest",
    "LoginRequest",
    "RefreshRequest",
    "ChangePasswordFirstLoginRequest",
    "LoginResponse",
    "UserResponse",
    # Bootstrap utilities
    "ensure_dev_founder_user",
    "create_founder_user_explicit",
]
