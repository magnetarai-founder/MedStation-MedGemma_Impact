"""
Comprehensive tests for api/structured_logger.py

Tests the structured logging utilities including:
- StructuredLogFormatter for JSON output
- get_logger factory function
- Context-aware logging functions
- Request ID propagation via ContextVar

Coverage targets:
- StructuredLogFormatter: JSON formatting with request_id
- get_logger: Logger factory with optional structured output
- log_with_context: Context-aware logging
- Convenience functions: info_with_context, error_with_context, warning_with_context
"""

import json
import logging
import pytest
from unittest.mock import patch, MagicMock
from contextvars import ContextVar
from datetime import datetime

from api.structured_logger import (
    StructuredLogFormatter,
    get_logger,
    log_with_context,
    info_with_context,
    error_with_context,
    warning_with_context,
    request_id_ctx,
)


# ========== Fixtures ==========

@pytest.fixture
def clean_logger():
    """Create a clean logger for testing"""
    logger_name = f"test_logger_{id(object())}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    yield logger
    # Cleanup handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)


@pytest.fixture
def structured_handler():
    """Create a handler with StructuredLogFormatter"""
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredLogFormatter())
    return handler


@pytest.fixture
def request_id_token():
    """Set and clean up request_id context"""
    token = request_id_ctx.set("test-request-123")
    yield "test-request-123"
    request_id_ctx.reset(token)


# ========== StructuredLogFormatter Tests ==========

class TestStructuredLogFormatter:
    """Tests for StructuredLogFormatter"""

    def test_returns_json_string(self, clean_logger, structured_handler):
        """Test format returns valid JSON string"""
        clean_logger.addHandler(structured_handler)

        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )

        formatter = StructuredLogFormatter()
        result = formatter.format(record)

        # Should be valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_contains_required_fields(self):
        """Test JSON contains required fields"""
        record = logging.LogRecord(
            name="test.module",
            level=logging.WARNING,
            pathname="test.py",
            lineno=42,
            msg="Warning message",
            args=(),
            exc_info=None
        )

        formatter = StructuredLogFormatter()
        result = json.loads(formatter.format(record))

        assert "timestamp" in result
        assert "level" in result
        assert "logger" in result
        assert "message" in result
        assert "module" in result
        assert "function" in result
        assert "line" in result

    def test_level_name_correct(self):
        """Test level names are formatted correctly"""
        formatter = StructuredLogFormatter()

        for level, name in [(logging.DEBUG, "DEBUG"), (logging.INFO, "INFO"),
                            (logging.WARNING, "WARNING"), (logging.ERROR, "ERROR"),
                            (logging.CRITICAL, "CRITICAL")]:
            record = logging.LogRecord(
                name="test",
                level=level,
                pathname="test.py",
                lineno=1,
                msg="Test",
                args=(),
                exc_info=None
            )
            result = json.loads(formatter.format(record))
            assert result["level"] == name

    def test_message_formatted(self):
        """Test message is properly formatted"""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Hello %s",
            args=("World",),
            exc_info=None
        )

        formatter = StructuredLogFormatter()
        result = json.loads(formatter.format(record))

        assert result["message"] == "Hello World"

    def test_timestamp_format(self):
        """Test timestamp is ISO format with Z suffix"""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None
        )

        formatter = StructuredLogFormatter()
        result = json.loads(formatter.format(record))

        # Should end with Z
        assert result["timestamp"].endswith("Z")

        # Should be parseable as ISO format
        ts = result["timestamp"].rstrip("Z")
        datetime.fromisoformat(ts)

    def test_includes_request_id_when_set(self, request_id_token):
        """Test includes request_id when set in context"""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None
        )

        formatter = StructuredLogFormatter()
        result = json.loads(formatter.format(record))

        assert result["request_id"] == "test-request-123"

    def test_no_request_id_when_not_set(self):
        """Test request_id not included when not set"""
        # Ensure request_id is not set
        token = request_id_ctx.set("")
        try:
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg="Test",
                args=(),
                exc_info=None
            )

            formatter = StructuredLogFormatter()
            result = json.loads(formatter.format(record))

            assert "request_id" not in result
        finally:
            request_id_ctx.reset(token)

    def test_includes_exception_info(self):
        """Test includes exception info when present"""
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=1,
                msg="Error occurred",
                args=(),
                exc_info=exc_info
            )

            formatter = StructuredLogFormatter()
            result = json.loads(formatter.format(record))

            assert "exception" in result
            assert "ValueError" in result["exception"]
            assert "Test error" in result["exception"]

    def test_includes_extra_fields(self):
        """Test includes extra fields from record"""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None
        )
        record.extra = {"user_id": "user_123", "action": "login"}

        formatter = StructuredLogFormatter()
        result = json.loads(formatter.format(record))

        assert result["user_id"] == "user_123"
        assert result["action"] == "login"

    def test_module_name_correct(self):
        """Test module name is extracted from record"""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/path/to/mymodule.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None
        )

        formatter = StructuredLogFormatter()
        result = json.loads(formatter.format(record))

        assert result["module"] == "mymodule"

    def test_function_name_correct(self):
        """Test function name is included"""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None
        )
        record.funcName = "my_function"

        formatter = StructuredLogFormatter()
        result = json.loads(formatter.format(record))

        assert result["function"] == "my_function"

    def test_line_number_correct(self):
        """Test line number is included"""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test",
            args=(),
            exc_info=None
        )

        formatter = StructuredLogFormatter()
        result = json.loads(formatter.format(record))

        assert result["line"] == 42


# ========== get_logger Tests ==========

class TestGetLogger:
    """Tests for get_logger function"""

    def test_returns_logger_instance(self):
        """Test returns a Logger instance"""
        logger = get_logger("test.module")

        assert isinstance(logger, logging.Logger)

    def test_logger_has_correct_name(self):
        """Test logger has the requested name"""
        logger = get_logger("my.custom.name")

        assert logger.name == "my.custom.name"

    def test_structured_false_no_handler(self):
        """Test structured=False doesn't add handler"""
        logger_name = f"no_handler_{id(object())}"
        logger = get_logger(logger_name, structured=False)

        # Should not have our structured handler
        assert not any(
            isinstance(h.formatter, StructuredLogFormatter)
            for h in logger.handlers
        )

    def test_structured_true_adds_handler(self):
        """Test structured=True adds structured handler"""
        logger_name = f"structured_{id(object())}"
        logger = get_logger(logger_name, structured=True)

        # Should have our structured handler
        assert any(
            isinstance(h.formatter, StructuredLogFormatter)
            for h in logger.handlers
        )

        # Cleanup
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    def test_structured_handler_not_duplicated(self):
        """Test handler not duplicated on multiple calls"""
        logger_name = f"no_dup_{id(object())}"

        logger1 = get_logger(logger_name, structured=True)
        handler_count_1 = len(logger1.handlers)

        # Call again - should not add another handler
        logger2 = get_logger(logger_name, structured=True)
        handler_count_2 = len(logger2.handlers)

        assert logger1 is logger2
        assert handler_count_1 == handler_count_2

        # Cleanup
        for handler in logger1.handlers[:]:
            logger1.removeHandler(handler)

    def test_structured_logger_propagate_false(self):
        """Test structured logger has propagate=False"""
        logger_name = f"no_prop_{id(object())}"
        logger = get_logger(logger_name, structured=True)

        assert logger.propagate is False

        # Cleanup
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    def test_returns_same_logger_instance(self):
        """Test returns same logger for same name"""
        logger1 = get_logger("same.name")
        logger2 = get_logger("same.name")

        assert logger1 is logger2


# ========== log_with_context Tests ==========

class TestLogWithContext:
    """Tests for log_with_context function"""

    def test_logs_at_correct_level(self, clean_logger):
        """Test logs at the specified level"""
        with patch.object(clean_logger, 'info') as mock_info:
            log_with_context(clean_logger, 'info', 'Test message')
            mock_info.assert_called_once()

        with patch.object(clean_logger, 'error') as mock_error:
            log_with_context(clean_logger, 'error', 'Error message')
            mock_error.assert_called_once()

    def test_includes_extra_data(self, clean_logger):
        """Test includes extra data in log"""
        with patch.object(clean_logger, 'info') as mock_info:
            log_with_context(clean_logger, 'info', 'Test', extra={"key": "value"})

            call_kwargs = mock_info.call_args[1]
            assert call_kwargs['extra']['key'] == 'value'

    def test_includes_request_id_when_set(self, clean_logger, request_id_token):
        """Test includes request_id from context"""
        with patch.object(clean_logger, 'info') as mock_info:
            log_with_context(clean_logger, 'info', 'Test')

            call_kwargs = mock_info.call_args[1]
            assert call_kwargs['extra']['request_id'] == 'test-request-123'

    def test_no_request_id_when_not_set(self, clean_logger):
        """Test no request_id when context is empty"""
        token = request_id_ctx.set("")
        try:
            with patch.object(clean_logger, 'info') as mock_info:
                log_with_context(clean_logger, 'info', 'Test')

                call_kwargs = mock_info.call_args[1]
                assert 'request_id' not in call_kwargs['extra']
        finally:
            request_id_ctx.reset(token)

    def test_level_case_insensitive(self, clean_logger):
        """Test level parameter is case insensitive"""
        with patch.object(clean_logger, 'warning') as mock_warning:
            log_with_context(clean_logger, 'WARNING', 'Test')
            mock_warning.assert_called_once()

        with patch.object(clean_logger, 'debug') as mock_debug:
            log_with_context(clean_logger, 'DEBUG', 'Test')
            mock_debug.assert_called_once()

    def test_extra_none_creates_empty_dict(self, clean_logger):
        """Test None extra creates empty dict"""
        token = request_id_ctx.set("")
        try:
            with patch.object(clean_logger, 'info') as mock_info:
                log_with_context(clean_logger, 'info', 'Test', extra=None)

                call_kwargs = mock_info.call_args[1]
                assert call_kwargs['extra'] == {}
        finally:
            request_id_ctx.reset(token)


# ========== Convenience Function Tests ==========

class TestConvenienceFunctions:
    """Tests for convenience logging functions"""

    def test_info_with_context(self, clean_logger, request_id_token):
        """Test info_with_context function"""
        with patch.object(clean_logger, 'info') as mock_info:
            info_with_context(clean_logger, 'Info message', user='alice')

            mock_info.assert_called_once()
            call_args, call_kwargs = mock_info.call_args
            assert call_args[0] == 'Info message'
            assert call_kwargs['extra']['user'] == 'alice'
            assert call_kwargs['extra']['request_id'] == 'test-request-123'

    def test_error_with_context(self, clean_logger, request_id_token):
        """Test error_with_context function"""
        with patch.object(clean_logger, 'error') as mock_error:
            error_with_context(clean_logger, 'Error message', code=500)

            mock_error.assert_called_once()
            call_args, call_kwargs = mock_error.call_args
            assert call_args[0] == 'Error message'
            assert call_kwargs['extra']['code'] == 500
            assert call_kwargs['extra']['request_id'] == 'test-request-123'

    def test_warning_with_context(self, clean_logger, request_id_token):
        """Test warning_with_context function"""
        with patch.object(clean_logger, 'warning') as mock_warning:
            warning_with_context(clean_logger, 'Warning message', threshold=80)

            mock_warning.assert_called_once()
            call_args, call_kwargs = mock_warning.call_args
            assert call_args[0] == 'Warning message'
            assert call_kwargs['extra']['threshold'] == 80
            assert call_kwargs['extra']['request_id'] == 'test-request-123'

    def test_convenience_functions_without_kwargs(self, clean_logger):
        """Test convenience functions work without extra kwargs"""
        with patch.object(clean_logger, 'info') as mock_info:
            info_with_context(clean_logger, 'Simple message')
            mock_info.assert_called_once()

        with patch.object(clean_logger, 'error') as mock_error:
            error_with_context(clean_logger, 'Simple error')
            mock_error.assert_called_once()

        with patch.object(clean_logger, 'warning') as mock_warning:
            warning_with_context(clean_logger, 'Simple warning')
            mock_warning.assert_called_once()


# ========== Integration Tests ==========

class TestIntegration:
    """Integration tests"""

    def test_full_structured_logging_flow(self, request_id_token):
        """Test full flow: get_logger -> log_with_context -> format"""
        import io

        # Create logger with structured output
        logger_name = f"integration_{id(object())}"
        logger = get_logger(logger_name, structured=True)
        logger.setLevel(logging.DEBUG)

        # Capture output
        stream = io.StringIO()
        for handler in logger.handlers:
            handler.stream = stream

        # Log a message using log_with_context (which properly sets record.extra)
        log_with_context(logger, 'info', 'Test message', extra={"user_id": "123"})

        # Check output
        output = stream.getvalue()
        log_entry = json.loads(output.strip())

        assert log_entry["message"] == "Test message"
        assert log_entry["level"] == "INFO"
        assert log_entry["request_id"] == "test-request-123"
        # Note: extra fields from log_with_context are passed via extra kwarg to logger
        # but Python logging adds them as record attributes, not record.extra
        # The request_id is included because log_with_context adds it to the extra kwarg

        # Cleanup
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    def test_multiple_request_ids_isolated(self):
        """Test request IDs are isolated per context"""
        import asyncio

        results = []

        async def log_with_id(request_id):
            token = request_id_ctx.set(request_id)
            try:
                # Small delay to ensure interleaving
                await asyncio.sleep(0.01)
                results.append(request_id_ctx.get())
            finally:
                request_id_ctx.reset(token)

        async def run_test():
            await asyncio.gather(
                log_with_id("req-1"),
                log_with_id("req-2"),
                log_with_id("req-3")
            )

        asyncio.run(run_test())

        # Each context should have preserved its request ID
        assert set(results) == {"req-1", "req-2", "req-3"}


# ========== Edge Cases ==========

class TestEdgeCases:
    """Tests for edge cases"""

    def test_unicode_message(self):
        """Test handles unicode in message"""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="日本語メッセージ 🔐",
            args=(),
            exc_info=None
        )

        formatter = StructuredLogFormatter()
        result = json.loads(formatter.format(record))

        assert result["message"] == "日本語メッセージ 🔐"

    def test_unicode_in_extra(self):
        """Test handles unicode in extra fields"""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None
        )
        record.extra = {"user": "用户", "emoji": "✅"}

        formatter = StructuredLogFormatter()
        result = json.loads(formatter.format(record))

        assert result["user"] == "用户"
        assert result["emoji"] == "✅"

    def test_very_long_message(self):
        """Test handles very long messages"""
        long_msg = "x" * 10000
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=long_msg,
            args=(),
            exc_info=None
        )

        formatter = StructuredLogFormatter()
        result = json.loads(formatter.format(record))

        assert len(result["message"]) == 10000

    def test_special_chars_in_message(self):
        """Test handles special characters"""
        msg = 'Message with "quotes" and \\backslashes\\ and \nnewlines'
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=msg,
            args=(),
            exc_info=None
        )

        formatter = StructuredLogFormatter()
        result = json.loads(formatter.format(record))

        assert "quotes" in result["message"]
        assert "backslashes" in result["message"]
        assert "newlines" in result["message"]

    def test_nested_extra_data(self):
        """Test handles nested extra data"""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None
        )
        record.extra = {
            "nested": {
                "level1": {
                    "level2": "value"
                }
            }
        }

        formatter = StructuredLogFormatter()
        result = json.loads(formatter.format(record))

        assert result["nested"]["level1"]["level2"] == "value"

    def test_request_id_context_isolation(self):
        """Test request ID context is properly isolated"""
        # Set a request ID
        token1 = request_id_ctx.set("id-1")

        # Verify it's set
        assert request_id_ctx.get() == "id-1"

        # Reset it
        request_id_ctx.reset(token1)

        # Should be back to default (empty string)
        assert request_id_ctx.get() == ""

    def test_logger_name_with_dots(self):
        """Test logger names with multiple dots work"""
        logger = get_logger("api.services.auth.oauth")
        assert logger.name == "api.services.auth.oauth"

    def test_empty_logger_name(self):
        """Test empty logger name works (root logger)"""
        logger = get_logger("")
        assert logger.name == "root"
