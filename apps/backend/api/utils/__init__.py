"""
Utility functions and decorators for MagnetarCode API.
"""

from .cache import (
    cache_file_tree,
    cache_ollama_models,
    cache_vector_search,
    cached,
    get_cache,
    invalidate_ollama_cache,
    invalidate_workspace_cache,
)
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    get_all_circuit_breakers,
    get_circuit_breaker,
    reset_all_circuit_breakers,
)
from .decorators import handle_api_errors, require_workspace, validate_pagination
from .errors import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
    raise_forbidden,
    raise_not_found,
    raise_unauthorized,
    raise_validation_error,
)
from .path_security import sanitize_file_path, validate_workspace_path
from .retry import (
    ErrorBudget,
    GracefulDegradation,
    RetryConfig,
    RetryExhaustedError,
    retry,
    safe_execute,
    safe_execute_async,
    with_timeout,
)
from .structured_logging import (
    StructuredLogger,
    configure_logging,
    get_logger,
    log_api_request,
    log_audit,
    log_error,
    log_execution,
)

__all__ = [
    # Circuit breakers
    "CircuitBreaker",
    "CircuitBreakerOpenError",
    "CircuitState",
    "ConflictError",
    "ErrorBudget",
    "ForbiddenError",
    "GracefulDegradation",
    # Error utilities
    "NotFoundError",
    "RetryConfig",
    "RetryExhaustedError",
    # Structured logging
    "StructuredLogger",
    "UnauthorizedError",
    "ValidationError",
    "cache_file_tree",
    "cache_ollama_models",
    "cache_vector_search",
    "cached",
    "configure_logging",
    "get_all_circuit_breakers",
    # Caching
    "get_cache",
    "get_circuit_breaker",
    "get_logger",
    # Decorators
    "handle_api_errors",
    "invalidate_ollama_cache",
    "invalidate_workspace_cache",
    "log_api_request",
    "log_audit",
    "log_error",
    "log_execution",
    "raise_forbidden",
    "raise_not_found",
    "raise_unauthorized",
    "raise_validation_error",
    "require_workspace",
    "reset_all_circuit_breakers",
    # Retry and error recovery
    "retry",
    "safe_execute",
    "safe_execute_async",
    "sanitize_file_path",
    "validate_pagination",
    # Path security
    "validate_workspace_path",
    "with_timeout",
]
