"""
Unified Error Handler for ElohimOS
Provides consistent error handling across all services
"""

import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Standard error types"""
    # Ollama errors
    OLLAMA_OFFLINE = "ollama_offline"
    OLLAMA_MODEL_NOT_FOUND = "ollama_model_not_found"
    OLLAMA_TIMEOUT = "ollama_timeout"

    # File/upload errors
    FILE_NOT_FOUND = "file_not_found"
    FILE_TOO_LARGE = "file_too_large"
    FILE_UPLOAD_FAILED = "file_upload_failed"
    INVALID_FILE_TYPE = "invalid_file_type"

    # Data/SQL errors
    INVALID_SQL = "invalid_sql"
    SQL_EXECUTION_FAILED = "sql_execution_failed"
    TABLE_NOT_FOUND = "table_not_found"
    UNAUTHORIZED_TABLE_ACCESS = "unauthorized_table_access"

    # Session/auth errors
    SESSION_NOT_FOUND = "session_not_found"
    SESSION_EXPIRED = "session_expired"
    UNAUTHORIZED = "unauthorized"
    AUTH_TOKEN_INVALID = "auth_token_invalid"

    # P2P/mesh errors
    PEER_NOT_FOUND = "peer_not_found"
    PEER_UNREACHABLE = "peer_unreachable"
    SYNC_FAILED = "sync_failed"
    DISCOVERY_FAILED = "discovery_failed"

    # Validation errors
    INVALID_INPUT = "invalid_input"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    VALIDATION_FAILED = "validation_failed"

    # Rate limiting
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

    # Generic
    INTERNAL_ERROR = "internal_error"
    SERVICE_UNAVAILABLE = "service_unavailable"


class ElohimOSError(Exception):
    """Base exception for ElohimOS"""

    def __init__(
        self,
        message: str,
        error_type: ErrorType,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class OllamaError(ElohimOSError):
    """Ollama-specific errors"""

    def __init__(
        self,
        message: str,
        error_type: ErrorType = ErrorType.OLLAMA_OFFLINE,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_type=error_type,
            status_code=503,  # Service Unavailable
            details=details
        )


class ValidationError(ElohimOSError):
    """Validation errors"""

    def __init__(
        self,
        message: str,
        error_type: ErrorType = ErrorType.INVALID_INPUT,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_type=error_type,
            status_code=400,  # Bad Request
            details=details
        )


class AuthError(ElohimOSError):
    """Authentication/authorization errors"""

    def __init__(
        self,
        message: str,
        error_type: ErrorType = ErrorType.UNAUTHORIZED,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_type=error_type,
            status_code=401,  # Unauthorized
            details=details
        )


class DataEngineError(ElohimOSError):
    """Data engine/SQL errors"""

    def __init__(
        self,
        message: str,
        error_type: ErrorType = ErrorType.SQL_EXECUTION_FAILED,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_type=error_type,
            status_code=400,  # Bad Request
            details=details
        )


class MeshError(ElohimOSError):
    """P2P mesh networking errors"""

    def __init__(
        self,
        message: str,
        error_type: ErrorType = ErrorType.PEER_NOT_FOUND,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_type=error_type,
            status_code=503,  # Service Unavailable
            details=details
        )


class ErrorHandler:
    """Centralized error handling"""

    @staticmethod
    def handle_ollama_error(error: Exception) -> OllamaError:
        """Convert Ollama errors to standardized format"""
        error_str = str(error).lower()

        # Connection refused
        if "connection" in error_str or "refused" in error_str:
            return OllamaError(
                message="Ollama is not running. Start it with: ollama serve",
                error_type=ErrorType.OLLAMA_OFFLINE,
                details={
                    "help": "Run 'ollama serve' in terminal to start Ollama",
                    "original_error": str(error)
                }
            )

        # Model not found
        if "model" in error_str and ("not found" in error_str or "does not exist" in error_str):
            return OllamaError(
                message="Model not found in Ollama",
                error_type=ErrorType.OLLAMA_MODEL_NOT_FOUND,
                details={
                    "help": "Pull the model with: ollama pull <model-name>",
                    "original_error": str(error)
                }
            )

        # Timeout
        if "timeout" in error_str:
            return OllamaError(
                message="Ollama request timed out",
                error_type=ErrorType.OLLAMA_TIMEOUT,
                details={
                    "help": "Try a smaller model or increase timeout",
                    "original_error": str(error)
                }
            )

        # Generic Ollama error
        return OllamaError(
            message=f"Ollama error: {str(error)}",
            error_type=ErrorType.INTERNAL_ERROR,
            details={"original_error": str(error)}
        )

    @staticmethod
    def to_http_exception(error: ElohimOSError) -> HTTPException:
        """Convert ElohimOSError to FastAPI HTTPException"""
        return HTTPException(
            status_code=error.status_code,
            detail={
                "error": error.message,
                "type": error.error_type.value,
                "details": error.details
            }
        )

    @staticmethod
    async def check_ollama_health() -> Dict[str, Any]:
        """Check if Ollama is running and healthy"""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get("http://localhost:11434/api/tags")
                response.raise_for_status()

                return {
                    "status": "healthy",
                    "message": "Ollama is running",
                    "models_available": len(response.json().get("models", []))
                }

        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": "Ollama is not running",
                "error": str(e),
                "help": "Start Ollama with: ollama serve"
            }

    @staticmethod
    def handle_validation_error(error: Exception, field: Optional[str] = None) -> ValidationError:
        """Convert validation errors to standardized format"""
        error_str = str(error)

        return ValidationError(
            message=f"Validation failed: {error_str}",
            error_type=ErrorType.VALIDATION_FAILED,
            details={
                "field": field,
                "original_error": error_str
            }
        )

    @staticmethod
    def handle_sql_error(error: Exception, query: Optional[str] = None) -> DataEngineError:
        """Convert SQL errors to standardized format"""
        error_str = str(error).lower()

        # Table not found
        if "table" in error_str and ("not found" in error_str or "does not exist" in error_str):
            return DataEngineError(
                message="Table not found in database",
                error_type=ErrorType.TABLE_NOT_FOUND,
                details={
                    "help": "Ensure table exists or upload data first",
                    "original_error": str(error)
                }
            )

        # Syntax error
        if "syntax" in error_str or "invalid" in error_str:
            return DataEngineError(
                message="Invalid SQL syntax",
                error_type=ErrorType.INVALID_SQL,
                details={
                    "query": query[:200] if query else None,
                    "original_error": str(error)
                }
            )

        # Generic SQL error
        return DataEngineError(
            message=f"SQL execution failed: {str(error)}",
            error_type=ErrorType.SQL_EXECUTION_FAILED,
            details={
                "query": query[:200] if query else None,
                "original_error": str(error)
            }
        )

    @staticmethod
    def handle_mesh_error(error: Exception, peer_id: Optional[str] = None) -> MeshError:
        """Convert mesh/P2P errors to standardized format"""
        error_str = str(error).lower()

        # Peer not found
        if "peer" in error_str and ("not found" in error_str or "unknown" in error_str):
            return MeshError(
                message=f"Peer not found: {peer_id or 'unknown'}",
                error_type=ErrorType.PEER_NOT_FOUND,
                details={
                    "peer_id": peer_id,
                    "help": "Ensure peer is discovered via /discovery/start",
                    "original_error": str(error)
                }
            )

        # Connection errors
        if "connection" in error_str or "unreachable" in error_str:
            return MeshError(
                message=f"Peer unreachable: {peer_id or 'unknown'}",
                error_type=ErrorType.PEER_UNREACHABLE,
                details={
                    "peer_id": peer_id,
                    "help": "Check network connectivity and firewall settings",
                    "original_error": str(error)
                }
            )

        # Sync errors
        if "sync" in error_str:
            return MeshError(
                message="Data synchronization failed",
                error_type=ErrorType.SYNC_FAILED,
                details={
                    "peer_id": peer_id,
                    "original_error": str(error)
                }
            )

        # Generic mesh error
        return MeshError(
            message=f"Mesh operation failed: {str(error)}",
            error_type=ErrorType.INTERNAL_ERROR,
            details={
                "peer_id": peer_id,
                "original_error": str(error)
            }
        )

    @staticmethod
    def create_error_response(
        message: str,
        error_type: ErrorType,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None
    ) -> HTTPException:
        """
        Create a standardized HTTPException

        Usage:
            raise ErrorHandler.create_error_response(
                "File too large",
                ErrorType.FILE_TOO_LARGE,
                413,
                {"max_size_mb": 100, "actual_size_mb": 150}
            )
        """
        return HTTPException(
            status_code=status_code,
            detail={
                "error": message,
                "type": error_type.value,
                "details": details or {}
            }
        )
