"""
Unified Error Handler for ElohimOS
Provides consistent error handling across all services

Module structure (P2 decomposition):
- error_handler_types.py: ErrorType enum and exception classes
- error_handler.py: ErrorHandler class (this file)
"""

import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException

# Import from sibling module (P3 decomposition)
from api.errors.types import (
    ErrorType,
    ElohimOSError,
    OllamaError,
    ValidationError,
    AuthError,
    DataEngineError,
    MeshError,
)

logger = logging.getLogger(__name__)


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

    @staticmethod
    def record_error_analytics(
        user_id: str,
        error: ElohimOSError,
        session_id: Optional[str] = None,
        team_id: Optional[str] = None
    ):
        """
        Record error to analytics (Sprint 6 Theme A)

        Args:
            user_id: User experiencing the error
            error: ElohimOSError instance
            session_id: Associated session ID
            team_id: Associated team ID
        """
        try:
            from api.services.analytics import get_analytics_service

            analytics = get_analytics_service()
            analytics.record_error(
                user_id=user_id,
                error_code=error.error_type.value,
                session_id=session_id,
                team_id=team_id,
                metadata={
                    "message": error.message,
                    "status_code": error.status_code,
                    **error.details
                }
            )
        except Exception as analytics_error:
            # Don't fail the request if analytics recording fails
            logger.warning(f"Failed to record error analytics: {analytics_error}")


# Re-exports for backwards compatibility (P2 decomposition)
__all__ = [
    # Handler
    "ErrorHandler",
    # Re-exported from error_handler_types
    "ErrorType",
    "ElohimOSError",
    "OllamaError",
    "ValidationError",
    "AuthError",
    "DataEngineError",
    "MeshError",
]
