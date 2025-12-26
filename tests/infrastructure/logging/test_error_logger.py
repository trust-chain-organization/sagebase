"""Tests for ErrorLogger."""

import logging
from unittest.mock import MagicMock, patch

import pytest

from src.domain.exceptions import PolibaseException
from src.infrastructure.logging.error_logger import (
    ErrorLogger,
    get_error_logger,
    log_exception,
)


@pytest.fixture
def error_logger():
    """Create error logger instance."""
    return ErrorLogger("test.logger")


@pytest.fixture
def mock_logger():
    """Create mock logger."""
    return MagicMock(spec=logging.Logger)


class TestErrorLoggerInit:
    """Test ErrorLogger initialization."""

    def test_init_with_logger_name(self):
        """Test initialization with logger name."""
        logger = ErrorLogger("test.module")

        assert logger.logger.name == "test.module"
        assert logger._context == {}

    def test_init_with_default_name(self):
        """Test initialization with default logger name."""
        logger = ErrorLogger()

        # Default name should be the module name
        assert logger.logger.name == "src.infrastructure.logging.error_logger"


class TestLogError:
    """Test log_error method."""

    @patch("src.infrastructure.logging.error_logger.logging.getLogger")
    def test_log_error_basic(self, mock_get_logger, error_logger):
        """Test basic error logging."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        error_logger.logger = mock_logger

        exception = ValueError("Test error")

        error_logger.log_error(exception)

        # Verify logger was called
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        assert call_args[0][0] == logging.ERROR

    @patch("src.infrastructure.logging.error_logger.logging.getLogger")
    def test_log_error_with_context(self, mock_get_logger, error_logger):
        """Test error logging with context."""
        mock_logger = MagicMock()
        error_logger.logger = mock_logger

        exception = ValueError("Test error")
        context = {"user_id": "123", "operation": "test"}

        error_logger.log_error(exception, context=context)

        # Verify context was included
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        assert "extra" in call_args[1]

    @patch("src.infrastructure.logging.error_logger.logging.getLogger")
    def test_log_error_with_user_message(self, mock_get_logger, error_logger):
        """Test error logging with user message."""
        mock_logger = MagicMock()
        error_logger.logger = mock_logger

        exception = ValueError("Test error")
        user_message = "Something went wrong"

        error_logger.log_error(exception, user_message=user_message)

        mock_logger.log.assert_called_once()

    @patch("src.infrastructure.logging.error_logger.logging.getLogger")
    def test_log_error_without_traceback(self, mock_get_logger, error_logger):
        """Test error logging without traceback."""
        mock_logger = MagicMock()
        error_logger.logger = mock_logger

        exception = ValueError("Test error")

        error_logger.log_error(exception, include_traceback=False)

        mock_logger.log.assert_called_once()

    @patch("src.infrastructure.logging.error_logger.logging.getLogger")
    def test_log_error_sagebase_exception(self, mock_get_logger, error_logger):
        """Test logging Sagebase exception includes error code."""
        mock_logger = MagicMock()
        error_logger.logger = mock_logger

        exception = PolibaseException(
            "Test error", error_code="TEST_001", details={"key": "value"}
        )

        error_logger.log_error(exception)

        mock_logger.log.assert_called_once()


class TestLogWarning:
    """Test log_warning method."""

    @patch("src.infrastructure.logging.error_logger.logging.getLogger")
    def test_log_warning(self, mock_get_logger, error_logger):
        """Test warning level logging."""
        mock_logger = MagicMock()
        error_logger.logger = mock_logger

        exception = ValueError("Test warning")

        error_logger.log_warning(exception)

        # Verify warning level was used
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        assert call_args[0][0] == logging.WARNING

    @patch("src.infrastructure.logging.error_logger.logging.getLogger")
    def test_log_warning_with_context(self, mock_get_logger, error_logger):
        """Test warning logging with context."""
        mock_logger = MagicMock()
        error_logger.logger = mock_logger

        exception = ValueError("Test warning")
        context = {"user_id": "123"}

        error_logger.log_warning(exception, context=context)

        mock_logger.log.assert_called_once()


class TestLogCritical:
    """Test log_critical method."""

    @patch("src.infrastructure.logging.error_logger.logging.getLogger")
    def test_log_critical(self, mock_get_logger, error_logger):
        """Test critical level logging."""
        mock_logger = MagicMock()
        error_logger.logger = mock_logger

        exception = ValueError("Critical error")

        error_logger.log_critical(exception)

        # Verify critical level was used
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        assert call_args[0][0] == logging.CRITICAL


class TestLogWithRetryInfo:
    """Test log_with_retry_info method."""

    @patch("src.infrastructure.logging.error_logger.logging.getLogger")
    def test_log_with_retry_info_not_final(self, mock_get_logger, error_logger):
        """Test retry logging when not final attempt."""
        mock_logger = MagicMock()
        error_logger.logger = mock_logger

        exception = ValueError("Retry error")

        error_logger.log_with_retry_info(exception, retry_count=1, max_retries=3)

        # Should log as WARNING
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        assert call_args[0][0] == logging.WARNING

    @patch("src.infrastructure.logging.error_logger.logging.getLogger")
    def test_log_with_retry_info_final_attempt(self, mock_get_logger, error_logger):
        """Test retry logging on final attempt."""
        mock_logger = MagicMock()
        error_logger.logger = mock_logger

        exception = ValueError("Final retry error")

        error_logger.log_with_retry_info(exception, retry_count=3, max_retries=3)

        # Should log as ERROR
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        assert call_args[0][0] == logging.ERROR

    @patch("src.infrastructure.logging.error_logger.logging.getLogger")
    def test_log_with_retry_info_includes_context(self, mock_get_logger, error_logger):
        """Test retry logging includes retry context."""
        mock_logger = MagicMock()
        error_logger.logger = mock_logger

        exception = ValueError("Retry error")
        additional_context = {"operation": "test"}

        error_logger.log_with_retry_info(
            exception, retry_count=1, max_retries=3, context=additional_context
        )

        mock_logger.log.assert_called_once()


class TestLogPerformanceIssue:
    """Test log_performance_issue method."""

    @patch("src.infrastructure.logging.error_logger.logging.getLogger")
    def test_log_performance_issue(self, mock_get_logger, error_logger):
        """Test performance issue logging."""
        mock_logger = MagicMock()
        error_logger.logger = mock_logger

        error_logger.log_performance_issue(
            operation="slow_query", duration_seconds=5.0, threshold_seconds=2.0
        )

        # Verify warning was logged
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert "Performance issue detected" in call_args[0][0]

    @patch("src.infrastructure.logging.error_logger.logging.getLogger")
    def test_log_performance_issue_with_context(self, mock_get_logger, error_logger):
        """Test performance logging with additional context."""
        mock_logger = MagicMock()
        error_logger.logger = mock_logger

        context = {"query": "SELECT * FROM users"}

        error_logger.log_performance_issue(
            operation="database_query",
            duration_seconds=10.0,
            threshold_seconds=5.0,
            context=context,
        )

        mock_logger.warning.assert_called_once()


class TestBuildLogData:
    """Test _build_log_data method."""

    def test_build_log_data_basic(self, error_logger):
        """Test building basic log data."""
        exception = ValueError("Test error")

        log_data = error_logger._build_log_data(exception, None, False, None)

        assert "timestamp" in log_data
        assert log_data["exception_type"] == "ValueError"
        assert log_data["message"] == "Test error"

    def test_build_log_data_with_traceback(self, error_logger):
        """Test building log data with traceback."""
        exception = ValueError("Test error")

        log_data = error_logger._build_log_data(exception, None, True, None)

        assert "traceback" in log_data
        assert "stack_info" in log_data

    def test_build_log_data_with_context(self, error_logger):
        """Test building log data with context."""
        exception = ValueError("Test error")
        context = {"user": "test_user", "operation": "test_op"}

        log_data = error_logger._build_log_data(exception, context, False, None)

        assert log_data["context"] == context

    def test_build_log_data_with_user_message(self, error_logger):
        """Test building log data with user message."""
        exception = ValueError("Test error")
        user_message = "User-friendly message"

        log_data = error_logger._build_log_data(exception, None, False, user_message)

        assert log_data["user_message"] == user_message

    def test_build_log_data_with_global_context(self, error_logger):
        """Test building log data includes global context."""
        error_logger._context = {"global_key": "global_value"}
        exception = ValueError("Test error")

        log_data = error_logger._build_log_data(exception, None, False, None)

        assert log_data["global_context"] == {"global_key": "global_value"}

    def test_build_log_data_sagebase_exception(self, error_logger):
        """Test building log data for Sagebase exception."""
        exception = PolibaseException(
            "Test error", error_code="ERR_001", details={"key": "value"}
        )

        log_data = error_logger._build_log_data(exception, None, False, None)

        assert log_data["error_code"] == "ERR_001"
        assert log_data["error_details"] == {"key": "value"}


class TestExtractStackInfo:
    """Test _extract_stack_info method."""

    def test_extract_stack_info(self, error_logger):
        """Test extracting stack information."""
        stack_info = error_logger._extract_stack_info()

        assert isinstance(stack_info, list)
        assert len(stack_info) > 0
        assert all("filename" in frame for frame in stack_info)
        assert all("line_number" in frame for frame in stack_info)
        assert all("function" in frame for frame in stack_info)

    def test_extract_stack_info_limit(self, error_logger):
        """Test stack info is limited to 10 frames."""
        stack_info = error_logger._extract_stack_info()

        assert len(stack_info) <= 10


class TestContextManagement:
    """Test context management methods."""

    def test_set_context(self, error_logger):
        """Test setting context."""
        error_logger.set_context(user_id="123", operation="test")

        assert error_logger._context["user_id"] == "123"
        assert error_logger._context["operation"] == "test"

    def test_set_context_updates_existing(self, error_logger):
        """Test setting context updates existing values."""
        error_logger.set_context(key1="value1")
        error_logger.set_context(key2="value2")

        assert error_logger._context["key1"] == "value1"
        assert error_logger._context["key2"] == "value2"

    def test_clear_context(self, error_logger):
        """Test clearing context."""
        error_logger.set_context(key="value")
        error_logger.clear_context()

        assert error_logger._context == {}

    def test_context_manager(self, error_logger):
        """Test context manager."""
        error_logger._context = {"global_key": "global_value"}

        with error_logger.context(temp_key="temp_value"):
            assert error_logger._context["temp_key"] == "temp_value"
            assert error_logger._context["global_key"] == "global_value"

        # After context manager, temp_key should be removed
        assert "temp_key" not in error_logger._context
        assert error_logger._context["global_key"] == "global_value"

    def test_context_manager_restores_on_exception(self, error_logger):
        """Test context manager restores context even on exception."""
        error_logger._context = {"original": "value"}

        try:
            with error_logger.context(temp="temp"):
                assert error_logger._context["temp"] == "temp"
                raise ValueError("Test error")
        except ValueError:
            pass

        # Context should be restored
        assert "temp" not in error_logger._context
        assert error_logger._context["original"] == "value"


class TestCreateChild:
    """Test create_child method."""

    def test_create_child_logger(self, error_logger):
        """Test creating child logger."""
        error_logger._context = {"parent_key": "parent_value"}

        child = error_logger.create_child("sub_module", child_key="child_value")

        assert child.logger.name == "test.logger.sub_module"
        assert child._context["parent_key"] == "parent_value"
        assert child._context["child_key"] == "child_value"

    def test_create_child_inherits_parent_context(self, error_logger):
        """Test child logger inherits parent context."""
        error_logger._context = {"key1": "value1", "key2": "value2"}

        child = error_logger.create_child("sub")

        assert child._context == error_logger._context

    def test_create_child_context_does_not_affect_parent(self, error_logger):
        """Test child context changes don't affect parent."""
        child = error_logger.create_child("sub")

        child.set_context(child_only="value")

        assert "child_only" in child._context
        assert "child_only" not in error_logger._context


class TestGetErrorLogger:
    """Test get_error_logger function."""

    def test_get_error_logger_with_name(self):
        """Test getting error logger with name."""
        logger = get_error_logger("test.module")

        assert logger.logger.name == "test.module"

    def test_get_error_logger_global(self):
        """Test getting global error logger."""
        # Clear global logger first
        import src.infrastructure.logging.error_logger

        src.infrastructure.logging.error_logger._error_logger = None

        logger1 = get_error_logger()
        logger2 = get_error_logger()

        # Should return same instance
        assert logger1 is logger2
        assert logger1.logger.name == "sagebase.error"

    def test_get_error_logger_returns_new_instance_with_name(self):
        """Test getting error logger with name returns new instance each time."""
        logger1 = get_error_logger("test1")
        logger2 = get_error_logger("test2")

        # Should be different instances with different names
        assert logger1 is not logger2
        assert logger1.logger.name == "test1"
        assert logger2.logger.name == "test2"


class TestLogExceptionFunction:
    """Test log_exception convenience function."""

    @patch("src.infrastructure.logging.error_logger.get_error_logger")
    def test_log_exception(self, mock_get_logger):
        """Test log_exception function."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        exception = ValueError("Test error")
        context = {"key": "value"}

        log_exception(exception, context)

        mock_get_logger.assert_called_once_with(None)
        mock_logger.log_error.assert_called_once_with(exception, context)

    @patch("src.infrastructure.logging.error_logger.get_error_logger")
    def test_log_exception_with_logger_name(self, mock_get_logger):
        """Test log_exception with logger name."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        exception = ValueError("Test error")

        log_exception(exception, logger_name="custom.logger")

        mock_get_logger.assert_called_once_with("custom.logger")
        mock_logger.log_error.assert_called_once()


class TestErrorLoggerIntegration:
    """Integration tests for ErrorLogger."""

    @patch("src.infrastructure.logging.error_logger.logging.getLogger")
    def test_full_logging_workflow(self, mock_get_logger):
        """Test complete logging workflow."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        error_logger = ErrorLogger("test.workflow")

        # Set global context
        error_logger.set_context(session_id="sess_123")

        # Log with local context
        exception = ValueError("Test error")
        error_logger.log_error(exception, context={"operation": "test_op"})

        # Verify logging was called
        mock_logger.log.assert_called_once()

    @patch("src.infrastructure.logging.error_logger.logging.getLogger")
    def test_multiple_log_levels(self, mock_get_logger):
        """Test logging at multiple levels."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        error_logger = ErrorLogger("test.levels")

        # Log at different levels
        error_logger.log_warning(ValueError("Warning"))
        error_logger.log_error(ValueError("Error"))
        error_logger.log_critical(ValueError("Critical"))

        # Verify all were logged
        assert mock_logger.log.call_count == 3
