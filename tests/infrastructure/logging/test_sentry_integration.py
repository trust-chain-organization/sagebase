"""Tests for Sentry integration"""

import os
from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.config.sentry import (
    before_send_filter,
    before_send_transaction_filter,
    capture_exception,
    capture_message,
    init_sentry,
    monitor_db_query,
    monitor_llm_call,
    monitor_performance,
    monitor_web_scraping,
    sanitize_message,
)


class TestSentryInitialization:
    """Test Sentry SDK initialization"""

    def setup_method(self):
        """Reset the global initialization flag before each test"""
        import src.infrastructure.config.sentry

        src.infrastructure.config.sentry.initialized = False

    @patch("src.infrastructure.config.sentry.sentry_sdk.init")
    @patch.dict(os.environ, {"SENTRY_DSN": "https://test@sentry.io/123"})
    def test_init_sentry_with_dsn(self, mock_init):
        """Test Sentry initialization with DSN"""
        init_sentry()

        mock_init.assert_called_once()
        call_args = mock_init.call_args[1]

        assert call_args["dsn"] == "https://test@sentry.io/123"
        assert call_args["environment"] == "development"
        assert call_args["send_default_pii"] is False
        assert call_args["attach_stacktrace"] is True

    @patch("src.infrastructure.config.sentry.sentry_sdk.init")
    @patch("src.infrastructure.config.sentry.logger")
    @patch.dict(os.environ, {"SENTRY_DSN": ""})
    def test_init_sentry_without_dsn(self, mock_logger, mock_init):
        """Test Sentry initialization without DSN"""
        init_sentry()

        mock_init.assert_not_called()
        mock_logger.info.assert_called_with(
            "Sentry DSN not configured, skipping Sentry initialization"
        )

    @patch(
        "src.infrastructure.config.sentry.sentry_sdk.init",
        side_effect=Exception("Init failed"),
    )
    @patch("src.infrastructure.config.sentry.logger")
    @patch.dict(os.environ, {"SENTRY_DSN": "https://test@sentry.io/123"})
    def test_init_sentry_with_error(self, mock_logger, mock_init):
        """Test Sentry initialization with error"""
        init_sentry()

        mock_logger.error.assert_called_with("Failed to initialize Sentry: Init failed")

    @patch("src.infrastructure.config.sentry.sentry_sdk.init")
    @patch("src.infrastructure.config.sentry.logger")
    @patch.dict(os.environ, {"SENTRY_DSN": "https://test@sentry.io/123"})
    def test_init_sentry_called_multiple_times(self, mock_logger, mock_init):
        """Test that Sentry is only initialized once even when called multiple times"""
        # First call should initialize
        init_sentry()
        mock_init.assert_called_once()
        mock_logger.info.assert_called_with(
            "Sentry initialized successfully for environment: development"
        )

        # Second call should skip initialization
        init_sentry()
        # Still should be called only once
        mock_init.assert_called_once()
        # Debug log should be called for the second attempt
        mock_logger.debug.assert_called_with(
            "Sentry is already initialized, skipping..."
        )

        # Third call should also skip
        init_sentry()
        # Still only one init call
        mock_init.assert_called_once()


class TestSentryFilters:
    """Test Sentry event filters"""

    def test_before_send_filter_keyboard_interrupt(self):
        """Test filtering KeyboardInterrupt"""
        event = {"message": "test"}
        hint = {"exc_info": (KeyboardInterrupt, KeyboardInterrupt(), None)}

        result = before_send_filter(event, hint)
        assert result is None

    def test_before_send_filter_sanitize_request_data(self):
        """Test sanitizing sensitive data from request"""
        event = {
            "request": {
                "data": {
                    "api_key": "secret_key",
                    "password": "secret_pass",
                    "username": "user123",
                }
            }
        }
        hint = {}

        result = before_send_filter(event, hint)

        assert "api_key" not in result["request"]["data"]
        assert "password" not in result["request"]["data"]
        assert result["request"]["data"]["username"] == "user123"

    def test_before_send_filter_sanitize_exception_message(self):
        """Test sanitizing exception messages"""
        event = {
            "exception": {"values": [{"value": "Error with GOOGLE_API_KEY=secret123"}]}
        }
        hint = {}

        result = before_send_filter(event, hint)

        assert "secret123" not in result["exception"]["values"][0]["value"]
        assert "[REDACTED_API_KEY]" in result["exception"]["values"][0]["value"]

    def test_before_send_transaction_filter_health_check(self):
        """Test filtering health check transactions"""
        event = {"transaction": "/health"}
        hint = {}

        result = before_send_transaction_filter(event, hint)
        assert result is None

    def test_before_send_transaction_filter_normal(self):
        """Test normal transaction passes through"""
        event = {"transaction": "/api/meetings"}
        hint = {}

        result = before_send_transaction_filter(event, hint)
        assert result == event


class TestSentryUtilities:
    """Test Sentry utility functions"""

    def test_sanitize_message(self):
        """Test message sanitization"""
        message = "Error connecting to postgresql://user:pass@localhost/db"
        sanitized = sanitize_message(message)

        assert "postgresql://[REDACTED]" in sanitized
        assert "user:pass" not in sanitized

    def test_sanitize_message_api_key(self):
        """Test API key sanitization"""
        message = "Invalid GOOGLE_API_KEY=AIzaSyC123456"
        sanitized = sanitize_message(message)

        assert "[REDACTED_API_KEY]" in sanitized
        assert "AIzaSyC123456" not in sanitized

    @patch("src.infrastructure.config.sentry.sentry_sdk.capture_message")
    def test_capture_message(self, mock_capture):
        """Test capturing message to Sentry"""
        capture_message("Test message", level="warning", extra={"user": "test"})

        mock_capture.assert_called_once_with(
            "Test message", level="warning", extra={"user": "test"}
        )

    @patch("src.infrastructure.config.sentry.sentry_sdk.capture_exception")
    def test_capture_exception(self, mock_capture):
        """Test capturing exception to Sentry"""
        error = ValueError("Test error")
        capture_exception(error, extra={"context": "test"})

        mock_capture.assert_called_once_with(error, extra={"context": "test"})


class TestPerformanceMonitoring:
    """Test performance monitoring decorators"""

    @patch("src.infrastructure.config.sentry.sentry_sdk.start_transaction")
    def test_monitor_performance_decorator(self, mock_start_transaction):
        """Test performance monitoring decorator"""
        mock_transaction = MagicMock()
        mock_start_transaction.return_value.__enter__.return_value = mock_transaction

        @monitor_performance(op="test.operation")
        def test_function():
            return "result"

        result = test_function()

        assert result == "result"
        mock_start_transaction.assert_called_once()
        mock_transaction.set_status.assert_called_with("ok")

    @patch("src.infrastructure.config.sentry.sentry_sdk.start_transaction")
    def test_monitor_db_query_decorator(self, mock_start_transaction):
        """Test database query monitoring decorator"""
        mock_transaction = MagicMock()
        mock_start_transaction.return_value.__enter__.return_value = mock_transaction

        @monitor_db_query("fetch_meetings")
        def fetch_data():
            return ["data"]

        result = fetch_data()

        assert result == ["data"]
        call_args = mock_start_transaction.call_args[1]
        assert call_args["op"] == "db.query"
        assert call_args["name"] == "fetch_meetings"

    @patch("src.infrastructure.config.sentry.sentry_sdk.start_transaction")
    def test_monitor_llm_call_decorator(self, mock_start_transaction):
        """Test LLM call monitoring decorator"""
        mock_transaction = MagicMock()
        mock_start_transaction.return_value.__enter__.return_value = mock_transaction

        @monitor_llm_call(model="gemini-2.0-flash")
        def call_llm():
            return "response"

        result = call_llm()

        assert result == "response"
        call_args = mock_start_transaction.call_args[1]
        assert call_args["op"] == "llm.gemini-2.0-flash"
        mock_transaction.set_tag.assert_called_with("llm.model", "gemini-2.0-flash")

    @patch("src.infrastructure.config.sentry.sentry_sdk.start_transaction")
    def test_monitor_web_scraping_decorator(self, mock_start_transaction):
        """Test web scraping monitoring decorator"""
        mock_transaction = MagicMock()
        mock_start_transaction.return_value.__enter__.return_value = mock_transaction

        @monitor_web_scraping(url="https://example.com")
        def scrape_page():
            return "content"

        result = scrape_page()

        assert result == "content"
        call_args = mock_start_transaction.call_args[1]
        assert call_args["op"] == "http.client"
        mock_transaction.set_tag.assert_called_with("url", "https://example.com")

    @patch("src.infrastructure.config.sentry.sentry_sdk.start_transaction")
    def test_monitor_performance_with_exception(self, mock_start_transaction):
        """Test performance monitoring with exception"""
        mock_transaction = MagicMock()
        mock_start_transaction.return_value.__enter__.return_value = mock_transaction

        @monitor_performance()
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

        mock_transaction.set_status.assert_called_with("internal_error")
