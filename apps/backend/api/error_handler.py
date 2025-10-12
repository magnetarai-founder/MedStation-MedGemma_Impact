"""
Unified Error Handler for Omni-Studio
Provides consistent error handling across all services
"""

import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Standard error types"""
    OLLAMA_OFFLINE = "ollama_offline"
    OLLAMA_MODEL_NOT_FOUND = "ollama_model_not_found"
    OLLAMA_TIMEOUT = "ollama_timeout"
    FILE_NOT_FOUND = "file_not_found"
    FILE_TOO_LARGE = "file_too_large"
    INVALID_INPUT = "invalid_input"
    SESSION_NOT_FOUND = "session_not_found"
    INTERNAL_ERROR = "internal_error"


class OmniStudioError(Exception):
    """Base exception for OmniStudio"""

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


class OllamaError(OmniStudioError):
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
    def to_http_exception(error: OmniStudioError) -> HTTPException:
        """Convert OmniStudioError to FastAPI HTTPException"""
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
