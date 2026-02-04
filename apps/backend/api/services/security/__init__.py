"""
Security module for MagnetarCode

Provides security utilities including command validation,
input sanitization, code sandboxing, and audit logging.
"""

from .audit_logger import AuditLogger, log_command_execution
from .command_validator import (
    CommandValidationError,
    CommandValidator,
    is_safe_command,
    validate_command,
)

# Sandbox requires RestrictedPython - import conditionally
try:
    from .sandbox import (
        PythonSandbox,
        SandboxExecutionError,
        SandboxTimeoutError,
        execute_sandboxed,
        validate_code,
    )
    _SANDBOX_AVAILABLE = True
except ImportError:
    PythonSandbox = None
    SandboxExecutionError = Exception
    SandboxTimeoutError = Exception
    execute_sandboxed = None
    validate_code = None
    _SANDBOX_AVAILABLE = False

__all__ = [
    "AuditLogger",
    "CommandValidationError",
    "CommandValidator",
    "is_safe_command",
    "log_command_execution",
    "validate_command",
]

# Only export sandbox items if available
if _SANDBOX_AVAILABLE:
    __all__.extend([
        "PythonSandbox",
        "SandboxExecutionError",
        "SandboxTimeoutError",
        "execute_sandboxed",
        "validate_code",
    ])
