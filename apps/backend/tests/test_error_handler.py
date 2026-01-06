"""
Comprehensive tests for api/error_handler.py

Tests the unified error handling system including:
- ErrorType enum values
- Custom exception classes (ElohimOSError, OllamaError, ValidationError, etc.)
- ErrorHandler static methods for error conversion and handling

Coverage targets:
- ErrorType: All enum values
- ElohimOSError: Base exception class
- OllamaError, ValidationError, AuthError, DataEngineError, MeshError: Subclasses
- ErrorHandler: All static methods
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import HTTPException

from api.error_handler import (
    ErrorType,
    ElohimOSError,
    OllamaError,
    ValidationError,
    AuthError,
    DataEngineError,
    MeshError,
    ErrorHandler
)


# ========== ErrorType Enum Tests ==========

class TestErrorType:
    """Tests for ErrorType enum"""

    def test_ollama_error_types(self):
        """Test Ollama-related error types exist"""
        assert ErrorType.OLLAMA_OFFLINE.value == "ollama_offline"
        assert ErrorType.OLLAMA_MODEL_NOT_FOUND.value == "ollama_model_not_found"
        assert ErrorType.OLLAMA_TIMEOUT.value == "ollama_timeout"

    def test_file_error_types(self):
        """Test file-related error types exist"""
        assert ErrorType.FILE_NOT_FOUND.value == "file_not_found"
        assert ErrorType.FILE_TOO_LARGE.value == "file_too_large"
        assert ErrorType.FILE_UPLOAD_FAILED.value == "file_upload_failed"
        assert ErrorType.INVALID_FILE_TYPE.value == "invalid_file_type"

    def test_data_error_types(self):
        """Test data/SQL-related error types exist"""
        assert ErrorType.INVALID_SQL.value == "invalid_sql"
        assert ErrorType.SQL_EXECUTION_FAILED.value == "sql_execution_failed"
        assert ErrorType.TABLE_NOT_FOUND.value == "table_not_found"
        assert ErrorType.UNAUTHORIZED_TABLE_ACCESS.value == "unauthorized_table_access"

    def test_auth_error_types(self):
        """Test auth-related error types exist"""
        assert ErrorType.SESSION_NOT_FOUND.value == "session_not_found"
        assert ErrorType.SESSION_EXPIRED.value == "session_expired"
        assert ErrorType.UNAUTHORIZED.value == "unauthorized"
        assert ErrorType.AUTH_TOKEN_INVALID.value == "auth_token_invalid"

    def test_mesh_error_types(self):
        """Test P2P/mesh-related error types exist"""
        assert ErrorType.PEER_NOT_FOUND.value == "peer_not_found"
        assert ErrorType.PEER_UNREACHABLE.value == "peer_unreachable"
        assert ErrorType.SYNC_FAILED.value == "sync_failed"
        assert ErrorType.DISCOVERY_FAILED.value == "discovery_failed"

    def test_validation_error_types(self):
        """Test validation-related error types exist"""
        assert ErrorType.INVALID_INPUT.value == "invalid_input"
        assert ErrorType.MISSING_REQUIRED_FIELD.value == "missing_required_field"
        assert ErrorType.VALIDATION_FAILED.value == "validation_failed"

    def test_generic_error_types(self):
        """Test generic error types exist"""
        assert ErrorType.RATE_LIMIT_EXCEEDED.value == "rate_limit_exceeded"
        assert ErrorType.INTERNAL_ERROR.value == "internal_error"
        assert ErrorType.SERVICE_UNAVAILABLE.value == "service_unavailable"

    def test_error_type_count(self):
        """Test total number of error types"""
        # Should have 25 error types
        assert len(ErrorType) == 25


# ========== ElohimOSError Tests ==========

class TestElohimOSError:
    """Tests for ElohimOSError base exception"""

    def test_basic_creation(self):
        """Test creating basic error"""
        error = ElohimOSError(
            message="Test error",
            error_type=ErrorType.INTERNAL_ERROR
        )

        assert error.message == "Test error"
        assert error.error_type == ErrorType.INTERNAL_ERROR
        assert error.status_code == 500  # Default
        assert error.details == {}  # Default empty dict

    def test_creation_with_all_params(self):
        """Test creating error with all parameters"""
        error = ElohimOSError(
            message="Full error",
            error_type=ErrorType.FILE_NOT_FOUND,
            status_code=404,
            details={"file": "test.txt", "path": "/data"}
        )

        assert error.message == "Full error"
        assert error.error_type == ErrorType.FILE_NOT_FOUND
        assert error.status_code == 404
        assert error.details == {"file": "test.txt", "path": "/data"}

    def test_inherits_from_exception(self):
        """Test inherits from Exception"""
        error = ElohimOSError(
            message="Inherits test",
            error_type=ErrorType.INTERNAL_ERROR
        )

        assert isinstance(error, Exception)
        assert str(error) == "Inherits test"

    def test_can_be_raised(self):
        """Test error can be raised and caught"""
        with pytest.raises(ElohimOSError) as exc_info:
            raise ElohimOSError(
                message="Raised error",
                error_type=ErrorType.INTERNAL_ERROR
            )

        assert exc_info.value.message == "Raised error"

    def test_none_details_becomes_empty_dict(self):
        """Test None details defaults to empty dict"""
        error = ElohimOSError(
            message="Test",
            error_type=ErrorType.INTERNAL_ERROR,
            details=None
        )

        assert error.details == {}


# ========== OllamaError Tests ==========

class TestOllamaError:
    """Tests for OllamaError exception"""

    def test_default_error_type(self):
        """Test default error type is OLLAMA_OFFLINE"""
        error = OllamaError(message="Ollama error")

        assert error.error_type == ErrorType.OLLAMA_OFFLINE
        assert error.status_code == 503  # Service Unavailable

    def test_custom_error_type(self):
        """Test custom error type"""
        error = OllamaError(
            message="Model error",
            error_type=ErrorType.OLLAMA_MODEL_NOT_FOUND
        )

        assert error.error_type == ErrorType.OLLAMA_MODEL_NOT_FOUND
        assert error.status_code == 503

    def test_with_details(self):
        """Test with details"""
        error = OllamaError(
            message="Timeout",
            error_type=ErrorType.OLLAMA_TIMEOUT,
            details={"model": "llama2", "timeout_sec": 30}
        )

        assert error.details == {"model": "llama2", "timeout_sec": 30}

    def test_inherits_from_elohimos_error(self):
        """Test inherits from ElohimOSError"""
        error = OllamaError(message="Test")
        assert isinstance(error, ElohimOSError)


# ========== ValidationError Tests ==========

class TestValidationError:
    """Tests for ValidationError exception"""

    def test_default_error_type(self):
        """Test default error type is INVALID_INPUT"""
        error = ValidationError(message="Invalid input")

        assert error.error_type == ErrorType.INVALID_INPUT
        assert error.status_code == 400  # Bad Request

    def test_custom_error_type(self):
        """Test custom error type"""
        error = ValidationError(
            message="Missing field",
            error_type=ErrorType.MISSING_REQUIRED_FIELD
        )

        assert error.error_type == ErrorType.MISSING_REQUIRED_FIELD

    def test_with_details(self):
        """Test with validation details"""
        error = ValidationError(
            message="Field validation failed",
            details={"field": "email", "rule": "must be valid email"}
        )

        assert error.details["field"] == "email"

    def test_inherits_from_elohimos_error(self):
        """Test inherits from ElohimOSError"""
        error = ValidationError(message="Test")
        assert isinstance(error, ElohimOSError)


# ========== AuthError Tests ==========

class TestAuthError:
    """Tests for AuthError exception"""

    def test_default_error_type(self):
        """Test default error type is UNAUTHORIZED"""
        error = AuthError(message="Not authorized")

        assert error.error_type == ErrorType.UNAUTHORIZED
        assert error.status_code == 401  # Unauthorized

    def test_custom_error_type(self):
        """Test custom error type"""
        error = AuthError(
            message="Token expired",
            error_type=ErrorType.AUTH_TOKEN_INVALID
        )

        assert error.error_type == ErrorType.AUTH_TOKEN_INVALID

    def test_with_details(self):
        """Test with auth details"""
        error = AuthError(
            message="Session expired",
            error_type=ErrorType.SESSION_EXPIRED,
            details={"session_id": "abc123", "expired_at": "2024-01-01"}
        )

        assert error.details["session_id"] == "abc123"

    def test_inherits_from_elohimos_error(self):
        """Test inherits from ElohimOSError"""
        error = AuthError(message="Test")
        assert isinstance(error, ElohimOSError)


# ========== DataEngineError Tests ==========

class TestDataEngineError:
    """Tests for DataEngineError exception"""

    def test_default_error_type(self):
        """Test default error type is SQL_EXECUTION_FAILED"""
        error = DataEngineError(message="SQL error")

        assert error.error_type == ErrorType.SQL_EXECUTION_FAILED
        assert error.status_code == 400  # Bad Request

    def test_custom_error_type(self):
        """Test custom error type"""
        error = DataEngineError(
            message="Table missing",
            error_type=ErrorType.TABLE_NOT_FOUND
        )

        assert error.error_type == ErrorType.TABLE_NOT_FOUND

    def test_with_details(self):
        """Test with SQL details"""
        error = DataEngineError(
            message="Invalid SQL",
            error_type=ErrorType.INVALID_SQL,
            details={"query": "SELECT * FROM", "error": "syntax error"}
        )

        assert error.details["query"] == "SELECT * FROM"

    def test_inherits_from_elohimos_error(self):
        """Test inherits from ElohimOSError"""
        error = DataEngineError(message="Test")
        assert isinstance(error, ElohimOSError)


# ========== MeshError Tests ==========

class TestMeshError:
    """Tests for MeshError exception"""

    def test_default_error_type(self):
        """Test default error type is PEER_NOT_FOUND"""
        error = MeshError(message="Peer error")

        assert error.error_type == ErrorType.PEER_NOT_FOUND
        assert error.status_code == 503  # Service Unavailable

    def test_custom_error_type(self):
        """Test custom error type"""
        error = MeshError(
            message="Sync error",
            error_type=ErrorType.SYNC_FAILED
        )

        assert error.error_type == ErrorType.SYNC_FAILED

    def test_with_details(self):
        """Test with mesh details"""
        error = MeshError(
            message="Peer unreachable",
            error_type=ErrorType.PEER_UNREACHABLE,
            details={"peer_id": "peer_123", "last_seen": "2024-01-01"}
        )

        assert error.details["peer_id"] == "peer_123"

    def test_inherits_from_elohimos_error(self):
        """Test inherits from ElohimOSError"""
        error = MeshError(message="Test")
        assert isinstance(error, ElohimOSError)


# ========== ErrorHandler.handle_ollama_error Tests ==========

class TestHandleOllamaError:
    """Tests for ErrorHandler.handle_ollama_error"""

    def test_connection_refused_error(self):
        """Test handling connection refused error"""
        error = Exception("Connection refused")
        result = ErrorHandler.handle_ollama_error(error)

        assert result.error_type == ErrorType.OLLAMA_OFFLINE
        assert "not running" in result.message
        assert "ollama serve" in result.details["help"]

    def test_connection_error(self):
        """Test handling generic connection error"""
        error = Exception("Failed to establish connection")
        result = ErrorHandler.handle_ollama_error(error)

        assert result.error_type == ErrorType.OLLAMA_OFFLINE

    def test_model_not_found_error(self):
        """Test handling model not found error"""
        error = Exception("Model 'llama2' not found")
        result = ErrorHandler.handle_ollama_error(error)

        assert result.error_type == ErrorType.OLLAMA_MODEL_NOT_FOUND
        assert "ollama pull" in result.details["help"]

    def test_model_does_not_exist_error(self):
        """Test handling model does not exist error"""
        error = Exception("Model does not exist: mistral")
        result = ErrorHandler.handle_ollama_error(error)

        assert result.error_type == ErrorType.OLLAMA_MODEL_NOT_FOUND

    def test_timeout_error(self):
        """Test handling timeout error"""
        error = Exception("Request timeout after 30 seconds")
        result = ErrorHandler.handle_ollama_error(error)

        assert result.error_type == ErrorType.OLLAMA_TIMEOUT
        assert "smaller model" in result.details["help"]

    def test_generic_error(self):
        """Test handling generic Ollama error"""
        error = Exception("Unknown Ollama error")
        result = ErrorHandler.handle_ollama_error(error)

        assert result.error_type == ErrorType.INTERNAL_ERROR
        assert "Unknown Ollama error" in result.message

    def test_preserves_original_error(self):
        """Test original error is preserved in details"""
        error = Exception("Original error message")
        result = ErrorHandler.handle_ollama_error(error)

        assert result.details["original_error"] == "Original error message"


# ========== ErrorHandler.to_http_exception Tests ==========

class TestToHttpException:
    """Tests for ErrorHandler.to_http_exception"""

    def test_converts_to_http_exception(self):
        """Test converts ElohimOSError to HTTPException"""
        error = ElohimOSError(
            message="Test error",
            error_type=ErrorType.INTERNAL_ERROR,
            status_code=500
        )

        result = ErrorHandler.to_http_exception(error)

        assert isinstance(result, HTTPException)
        assert result.status_code == 500
        assert result.detail["error"] == "Test error"
        assert result.detail["type"] == "internal_error"

    def test_includes_details(self):
        """Test includes details in HTTPException"""
        error = ElohimOSError(
            message="File error",
            error_type=ErrorType.FILE_NOT_FOUND,
            status_code=404,
            details={"file": "test.txt"}
        )

        result = ErrorHandler.to_http_exception(error)

        assert result.detail["details"]["file"] == "test.txt"

    def test_converts_subclass_errors(self):
        """Test converts subclass errors correctly"""
        error = OllamaError(
            message="Ollama offline",
            error_type=ErrorType.OLLAMA_OFFLINE
        )

        result = ErrorHandler.to_http_exception(error)

        assert result.status_code == 503
        assert result.detail["type"] == "ollama_offline"


# ========== ErrorHandler.check_ollama_health Tests ==========

class TestCheckOllamaHealth:
    """Tests for ErrorHandler.check_ollama_health"""

    @pytest.mark.asyncio
    async def test_healthy_ollama(self):
        """Test returns healthy status when Ollama is running"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"models": [{"name": "llama2"}, {"name": "mistral"}]}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await ErrorHandler.check_ollama_health()

        assert result["status"] == "healthy"
        assert result["message"] == "Ollama is running"
        assert result["models_available"] == 2

    @pytest.mark.asyncio
    async def test_unhealthy_ollama_connection_error(self):
        """Test returns unhealthy status when Ollama is not running"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Connection refused")
            )

            result = await ErrorHandler.check_ollama_health()

        assert result["status"] == "unhealthy"
        assert result["message"] == "Ollama is not running"
        assert "Connection refused" in result["error"]
        assert "ollama serve" in result["help"]

    @pytest.mark.asyncio
    async def test_unhealthy_ollama_timeout(self):
        """Test returns unhealthy status on timeout"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Timeout")
            )

            result = await ErrorHandler.check_ollama_health()

        assert result["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_healthy_with_no_models(self):
        """Test returns healthy with zero models available"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"models": []}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await ErrorHandler.check_ollama_health()

        assert result["status"] == "healthy"
        assert result["models_available"] == 0


# ========== ErrorHandler.handle_validation_error Tests ==========

class TestHandleValidationError:
    """Tests for ErrorHandler.handle_validation_error"""

    def test_basic_validation_error(self):
        """Test handling basic validation error"""
        error = Exception("Value must be positive")
        result = ErrorHandler.handle_validation_error(error)

        assert result.error_type == ErrorType.VALIDATION_FAILED
        assert "Validation failed" in result.message
        assert result.details["field"] is None

    def test_with_field_name(self):
        """Test handling validation error with field name"""
        error = Exception("Invalid email format")
        result = ErrorHandler.handle_validation_error(error, field="email")

        assert result.details["field"] == "email"
        assert result.details["original_error"] == "Invalid email format"

    def test_preserves_error_message(self):
        """Test preserves original error message"""
        error = Exception("Must be at least 8 characters")
        result = ErrorHandler.handle_validation_error(error, field="password")

        assert "Must be at least 8 characters" in result.message


# ========== ErrorHandler.handle_sql_error Tests ==========

class TestHandleSqlError:
    """Tests for ErrorHandler.handle_sql_error"""

    def test_table_not_found_error(self):
        """Test handling table not found error"""
        error = Exception("Table 'users' not found")
        result = ErrorHandler.handle_sql_error(error)

        assert result.error_type == ErrorType.TABLE_NOT_FOUND
        assert "Table not found" in result.message
        assert "upload data first" in result.details["help"]

    def test_table_does_not_exist_error(self):
        """Test handling table does not exist error"""
        error = Exception("Table 'orders' does not exist in database")
        result = ErrorHandler.handle_sql_error(error)

        assert result.error_type == ErrorType.TABLE_NOT_FOUND

    def test_syntax_error(self):
        """Test handling SQL syntax error"""
        error = Exception("Syntax error near 'FROM'")
        result = ErrorHandler.handle_sql_error(error)

        assert result.error_type == ErrorType.INVALID_SQL
        assert "Invalid SQL syntax" in result.message

    def test_invalid_error(self):
        """Test handling invalid SQL error"""
        error = Exception("Invalid column name 'xyz'")
        result = ErrorHandler.handle_sql_error(error)

        assert result.error_type == ErrorType.INVALID_SQL

    def test_generic_sql_error(self):
        """Test handling generic SQL error"""
        error = Exception("Database connection lost")
        result = ErrorHandler.handle_sql_error(error)

        assert result.error_type == ErrorType.SQL_EXECUTION_FAILED
        assert "SQL execution failed" in result.message

    def test_includes_query_in_details(self):
        """Test includes query in details"""
        error = Exception("Syntax error")
        query = "SELECT * FROM users WHERE"
        result = ErrorHandler.handle_sql_error(error, query=query)

        assert result.details["query"] == query

    def test_truncates_long_query(self):
        """Test truncates very long queries"""
        error = Exception("Syntax error")
        long_query = "SELECT " + "x, " * 200  # Very long query
        result = ErrorHandler.handle_sql_error(error, query=long_query)

        assert len(result.details["query"]) == 200

    def test_handles_none_query(self):
        """Test handles None query gracefully"""
        error = Exception("Error")
        result = ErrorHandler.handle_sql_error(error, query=None)

        assert result.details["query"] is None


# ========== ErrorHandler.handle_mesh_error Tests ==========

class TestHandleMeshError:
    """Tests for ErrorHandler.handle_mesh_error"""

    def test_peer_not_found_error(self):
        """Test handling peer not found error"""
        error = Exception("Peer 'abc123' not found")
        result = ErrorHandler.handle_mesh_error(error, peer_id="abc123")

        assert result.error_type == ErrorType.PEER_NOT_FOUND
        assert "abc123" in result.message
        assert "/discovery/start" in result.details["help"]

    def test_peer_unknown_error(self):
        """Test handling unknown peer error"""
        error = Exception("Unknown peer in mesh network")
        result = ErrorHandler.handle_mesh_error(error)

        assert result.error_type == ErrorType.PEER_NOT_FOUND

    def test_peer_unreachable_error(self):
        """Test handling peer unreachable error"""
        error = Exception("Connection to peer failed")
        result = ErrorHandler.handle_mesh_error(error, peer_id="peer_456")

        assert result.error_type == ErrorType.PEER_UNREACHABLE
        assert "peer_456" in result.message
        assert "firewall" in result.details["help"]

    def test_peer_connection_error(self):
        """Test handling connection error"""
        error = Exception("Peer is unreachable")
        result = ErrorHandler.handle_mesh_error(error)

        assert result.error_type == ErrorType.PEER_UNREACHABLE

    def test_sync_failed_error(self):
        """Test handling sync failed error"""
        error = Exception("Sync operation failed with peer")
        result = ErrorHandler.handle_mesh_error(error, peer_id="sync_peer")

        assert result.error_type == ErrorType.SYNC_FAILED
        assert "synchronization failed" in result.message

    def test_generic_mesh_error(self):
        """Test handling generic mesh error"""
        error = Exception("Mesh network timeout")
        result = ErrorHandler.handle_mesh_error(error)

        assert result.error_type == ErrorType.INTERNAL_ERROR
        assert "Mesh operation failed" in result.message

    def test_includes_peer_id_in_details(self):
        """Test includes peer_id in details"""
        error = Exception("Generic error")
        result = ErrorHandler.handle_mesh_error(error, peer_id="test_peer")

        assert result.details["peer_id"] == "test_peer"

    def test_handles_none_peer_id(self):
        """Test handles None peer_id gracefully"""
        error = Exception("Peer not found")
        result = ErrorHandler.handle_mesh_error(error, peer_id=None)

        assert "unknown" in result.message


# ========== ErrorHandler.create_error_response Tests ==========

class TestCreateErrorResponse:
    """Tests for ErrorHandler.create_error_response"""

    def test_creates_http_exception(self):
        """Test creates HTTPException with correct structure"""
        result = ErrorHandler.create_error_response(
            message="Test error",
            error_type=ErrorType.INTERNAL_ERROR
        )

        assert isinstance(result, HTTPException)
        assert result.status_code == 400  # Default
        assert result.detail["error"] == "Test error"
        assert result.detail["type"] == "internal_error"

    def test_custom_status_code(self):
        """Test creates with custom status code"""
        result = ErrorHandler.create_error_response(
            message="Not found",
            error_type=ErrorType.FILE_NOT_FOUND,
            status_code=404
        )

        assert result.status_code == 404

    def test_with_details(self):
        """Test creates with details"""
        result = ErrorHandler.create_error_response(
            message="File too large",
            error_type=ErrorType.FILE_TOO_LARGE,
            status_code=413,
            details={"max_size_mb": 100, "actual_size_mb": 150}
        )

        assert result.detail["details"]["max_size_mb"] == 100
        assert result.detail["details"]["actual_size_mb"] == 150

    def test_none_details_becomes_empty_dict(self):
        """Test None details becomes empty dict"""
        result = ErrorHandler.create_error_response(
            message="Error",
            error_type=ErrorType.INTERNAL_ERROR,
            details=None
        )

        assert result.detail["details"] == {}


# ========== ErrorHandler.record_error_analytics Tests ==========

class TestRecordErrorAnalytics:
    """Tests for ErrorHandler.record_error_analytics"""

    def test_records_error_to_analytics(self):
        """Test records error to analytics service"""
        error = ElohimOSError(
            message="Test error",
            error_type=ErrorType.INTERNAL_ERROR,
            status_code=500,
            details={"extra": "info"}
        )

        mock_analytics = MagicMock()

        # Patch at source module since import happens inside the function
        with patch('api.services.analytics.get_analytics_service', return_value=mock_analytics):
            ErrorHandler.record_error_analytics(
                user_id="user_123",
                error=error,
                session_id="session_456",
                team_id="team_789"
            )

        # Verify analytics.record_error was called
        mock_analytics.record_error.assert_called_once()
        call_kwargs = mock_analytics.record_error.call_args[1]
        assert call_kwargs['user_id'] == 'user_123'
        assert call_kwargs['error_code'] == 'internal_error'
        assert call_kwargs['session_id'] == 'session_456'
        assert call_kwargs['team_id'] == 'team_789'

    def test_handles_analytics_failure_gracefully(self):
        """Test handles analytics failure without raising"""
        error = ElohimOSError(
            message="Test",
            error_type=ErrorType.INTERNAL_ERROR
        )

        mock_analytics = MagicMock()
        mock_analytics.record_error.side_effect = Exception("Analytics write failed")

        with patch('api.services.analytics.get_analytics_service', return_value=mock_analytics):
            # Should not raise
            ErrorHandler.record_error_analytics(
                user_id="user_123",
                error=error
            )

    def test_handles_service_error_gracefully(self):
        """Test handles get_analytics_service failure without raising"""
        error = ElohimOSError(
            message="Test",
            error_type=ErrorType.INTERNAL_ERROR
        )

        with patch('api.services.analytics.get_analytics_service', side_effect=Exception("Service unavailable")):
            # Should not raise
            ErrorHandler.record_error_analytics(
                user_id="user_123",
                error=error
            )

    def test_handles_import_error_gracefully(self):
        """Test handles import error without raising"""
        error = ElohimOSError(
            message="Test",
            error_type=ErrorType.INTERNAL_ERROR
        )

        # Patch logger to verify warning is logged
        with patch('api.error_handler.logger') as mock_logger:
            # Simulate import failure by patching builtins.__import__
            original_import = __builtins__['__import__'] if isinstance(__builtins__, dict) else __builtins__.__import__

            def failing_import(name, *args, **kwargs):
                if name == 'api.services.analytics':
                    raise ImportError("No module named api.services.analytics")
                return original_import(name, *args, **kwargs)

            import builtins
            with patch.object(builtins, '__import__', failing_import):
                # Should not raise even if analytics unavailable
                ErrorHandler.record_error_analytics(
                    user_id="user_123",
                    error=error
                )


# ========== Integration Tests ==========

class TestIntegration:
    """Integration tests combining multiple components"""

    def test_full_error_handling_flow(self):
        """Test full flow from exception to HTTP response"""
        # 1. Original exception
        original_error = Exception("Connection refused to Ollama")

        # 2. Convert to standardized error
        ollama_error = ErrorHandler.handle_ollama_error(original_error)

        # 3. Convert to HTTP exception
        http_exc = ErrorHandler.to_http_exception(ollama_error)

        # Verify chain
        assert isinstance(ollama_error, OllamaError)
        assert isinstance(http_exc, HTTPException)
        assert http_exc.status_code == 503
        assert "ollama_offline" in http_exc.detail["type"]

    def test_sql_error_to_http_response(self):
        """Test SQL error to HTTP response flow"""
        original_error = Exception("Table 'users' not found in database")

        sql_error = ErrorHandler.handle_sql_error(original_error, query="SELECT * FROM users")
        http_exc = ErrorHandler.to_http_exception(sql_error)

        assert http_exc.status_code == 400
        assert http_exc.detail["type"] == "table_not_found"

    def test_validation_error_to_http_response(self):
        """Test validation error to HTTP response flow"""
        original_error = Exception("Email format invalid")

        val_error = ErrorHandler.handle_validation_error(original_error, field="email")
        http_exc = ErrorHandler.to_http_exception(val_error)

        assert http_exc.status_code == 400
        assert http_exc.detail["type"] == "validation_failed"
        assert http_exc.detail["details"]["field"] == "email"


# ========== Edge Cases ==========

class TestEdgeCases:
    """Tests for edge cases"""

    def test_unicode_error_message(self):
        """Test handling unicode in error messages"""
        error = ElohimOSError(
            message="エラー: 日本語メッセージ",
            error_type=ErrorType.INTERNAL_ERROR,
            details={"info": "日本語"}
        )

        assert error.message == "エラー: 日本語メッセージ"
        assert error.details["info"] == "日本語"

    def test_empty_string_message(self):
        """Test handling empty string message"""
        error = ElohimOSError(
            message="",
            error_type=ErrorType.INTERNAL_ERROR
        )

        assert error.message == ""

    def test_very_long_error_message(self):
        """Test handling very long error messages"""
        long_message = "Error: " + "x" * 10000
        error = ElohimOSError(
            message=long_message,
            error_type=ErrorType.INTERNAL_ERROR
        )

        assert len(error.message) == 10007

    def test_special_chars_in_details(self):
        """Test handling special characters in details"""
        error = ElohimOSError(
            message="Test",
            error_type=ErrorType.INTERNAL_ERROR,
            details={
                "sql": "SELECT * FROM users WHERE name = 'O'Brien'",
                "path": "/data/test<file>.txt",
                "html": "<script>alert('xss')</script>"
            }
        )

        assert "O'Brien" in error.details["sql"]
        assert "<file>" in error.details["path"]

    def test_nested_details(self):
        """Test handling nested details"""
        error = ElohimOSError(
            message="Test",
            error_type=ErrorType.INTERNAL_ERROR,
            details={
                "level1": {
                    "level2": {
                        "level3": "deep_value"
                    }
                }
            }
        )

        assert error.details["level1"]["level2"]["level3"] == "deep_value"

    def test_error_with_numeric_details(self):
        """Test handling numeric values in details"""
        error = ElohimOSError(
            message="Test",
            error_type=ErrorType.INTERNAL_ERROR,
            details={
                "count": 42,
                "ratio": 3.14159,
                "negative": -100,
                "zero": 0
            }
        )

        assert error.details["count"] == 42
        assert error.details["ratio"] == 3.14159

    def test_error_with_list_details(self):
        """Test handling list values in details"""
        error = ElohimOSError(
            message="Test",
            error_type=ErrorType.INTERNAL_ERROR,
            details={
                "items": [1, 2, 3],
                "names": ["alice", "bob"]
            }
        )

        assert error.details["items"] == [1, 2, 3]

    def test_ollama_error_case_insensitive(self):
        """Test Ollama error detection is case insensitive"""
        # Uppercase
        error1 = ErrorHandler.handle_ollama_error(Exception("CONNECTION REFUSED"))
        assert error1.error_type == ErrorType.OLLAMA_OFFLINE

        # Mixed case
        error2 = ErrorHandler.handle_ollama_error(Exception("Model Not Found"))
        assert error2.error_type == ErrorType.OLLAMA_MODEL_NOT_FOUND

    def test_sql_error_case_insensitive(self):
        """Test SQL error detection is case insensitive"""
        error1 = ErrorHandler.handle_sql_error(Exception("TABLE NOT FOUND"))
        assert error1.error_type == ErrorType.TABLE_NOT_FOUND

        error2 = ErrorHandler.handle_sql_error(Exception("SYNTAX ERROR"))
        assert error2.error_type == ErrorType.INVALID_SQL

    def test_mesh_error_case_insensitive(self):
        """Test mesh error detection is case insensitive"""
        error1 = ErrorHandler.handle_mesh_error(Exception("PEER NOT FOUND"))
        assert error1.error_type == ErrorType.PEER_NOT_FOUND

        error2 = ErrorHandler.handle_mesh_error(Exception("SYNC FAILED"))
        assert error2.error_type == ErrorType.SYNC_FAILED
