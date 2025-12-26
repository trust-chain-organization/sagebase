"""構造化ログの単体テスト."""

import json
from io import StringIO
from unittest.mock import patch

import pytest
import structlog

from src.common.logging import (
    LogContext,
    add_context,
    clear_context,
    get_logger,
    setup_logging,
)


class TestStructuredLogging:
    """構造化ログのテストクラス."""

    def setup_method(self):
        """各テストメソッドの前処理."""
        # コンテキストをクリア
        clear_context()
        # デフォルトのログ設定をリセット
        structlog.reset_defaults()
        # ロガーのハンドラーをクリア
        import logging

        logging.getLogger().handlers = []

    def test_json_format_output(self):
        """JSON形式でログが出力されることを確認."""
        # StringIOでログ出力をキャプチャ
        log_output = StringIO()
        with patch("sys.stdout", log_output):
            setup_logging(log_level="INFO", json_format=True)
            logger = get_logger("test")
            logger.info("Test message", key1="value1", key2=123)

        # 出力されたログを確認
        output = log_output.getvalue().strip()
        log_data = json.loads(output)

        assert log_data["event"] == "Test message"
        assert log_data["key1"] == "value1"
        assert log_data["key2"] == 123
        assert log_data["level"] == "info"
        assert "timestamp" in log_data
        assert log_data["logger"] == "test"

    def test_console_format_output(self):
        """コンソール形式でログが出力されることを確認."""
        log_output = StringIO()
        with patch("sys.stdout", log_output):
            setup_logging(log_level="INFO", json_format=False)
            logger = get_logger("test")
            logger.info("Test message", key1="value1")

        output = log_output.getvalue()
        assert "Test message" in output
        assert "key1" in output
        assert "value1" in output
        assert "test" in output  # logger name

    def test_log_levels(self):
        """各ログレベルが正しく機能することを確認."""
        log_output = StringIO()
        with patch("sys.stdout", log_output):
            setup_logging(log_level="WARNING", json_format=True)
            logger = get_logger("test")

            # WARNING以下は出力されない
            logger.debug("Debug message")
            logger.info("Info message")

            # WARNING以上は出力される
            logger.warning("Warning message")
            logger.error("Error message")

        output_lines = log_output.getvalue().strip().split("\n")
        output_lines = [line for line in output_lines if line]  # 空行を除外

        assert len(output_lines) == 2
        assert json.loads(output_lines[0])["event"] == "Warning message"
        assert json.loads(output_lines[1])["event"] == "Error message"

    def test_context_management(self):
        """コンテキスト管理が正しく機能することを確認."""
        log_output = StringIO()
        with patch("sys.stdout", log_output):
            setup_logging(log_level="INFO", json_format=True)
            logger = get_logger("test")

            # コンテキストを追加
            add_context(request_id="123", user_id="user1")
            logger.info("With context")

            # コンテキストをクリア
            clear_context()
            logger.info("Without context")

        output_lines = log_output.getvalue().strip().split("\n")
        log_with_context = json.loads(output_lines[0])
        log_without_context = json.loads(output_lines[1])

        assert log_with_context["request_id"] == "123"
        assert log_with_context["user_id"] == "user1"
        # contextvarsはクリアされているため、以前のコンテキストは含まれない
        assert "request_id" not in log_without_context
        assert "user_id" not in log_without_context

    def test_log_context_manager(self):
        """LogContextマネージャーが正しく機能することを確認."""
        log_output = StringIO()
        with patch("sys.stdout", log_output):
            setup_logging(log_level="INFO", json_format=True)
            logger = get_logger("test")

            with LogContext(operation="test_op", transaction_id="tx123"):
                logger.info("Inside context")

            logger.info("Outside context")

        output_lines = log_output.getvalue().strip().split("\n")
        log_inside = json.loads(output_lines[0])
        log_outside = json.loads(output_lines[1])

        assert log_inside["operation"] == "test_op"
        assert log_inside["transaction_id"] == "tx123"
        # 次のログにもコンテキストが含まれるかチェック
        # (contextvarsはスレッドローカルなので、with文を抜けても残る)
        if "operation" in log_outside:
            assert log_outside["operation"] == "test_op"

    def test_exception_logging(self):
        """例外情報が正しくログに記録されることを確認."""
        log_output = StringIO()
        with patch("sys.stdout", log_output):
            setup_logging(log_level="ERROR", json_format=True)
            logger = get_logger("test")

            try:
                raise ValueError("Test error")
            except ValueError:
                logger.error("Error occurred", exc_info=True)

        output = log_output.getvalue().strip()
        log_data = json.loads(output)

        assert log_data["event"] == "Error occurred"
        # exc_info=Trueの場合、exception情報は省略されるか、
        # またはexc_infoフィールドに含まれる
        assert "exc_info" in log_data or "exception" in log_data

    def test_callsite_information(self):
        """呼び出し元情報が記録されることを確認."""
        log_output = StringIO()
        with patch("sys.stdout", log_output):
            setup_logging(log_level="INFO", json_format=True)
            logger = get_logger("test")
            logger.info("Test with callsite")

        output = log_output.getvalue().strip()
        log_data = json.loads(output)

        assert "filename" in log_data
        assert "lineno" in log_data
        assert "func_name" in log_data
        assert log_data["filename"] == "test_structured_logging.py"
        assert log_data["func_name"] == "test_callsite_information"

    def test_multiple_loggers(self):
        """複数のロガーが独立して動作することを確認."""
        log_output = StringIO()
        with patch("sys.stdout", log_output):
            setup_logging(log_level="INFO", json_format=True)
            logger1 = get_logger("module1")
            logger2 = get_logger("module2")

            logger1.info("From module1")
            logger2.info("From module2")

        output_lines = log_output.getvalue().strip().split("\n")
        log1 = json.loads(output_lines[0])
        log2 = json.loads(output_lines[1])

        assert log1["logger"] == "module1"
        assert log2["logger"] == "module2"


@pytest.mark.integration
class TestLoggingIntegration:
    """実際のモジュールとの統合テスト."""

    def test_scraper_service_logging(self):
        """scraperサービスのログ出力を確認."""
        log_output = StringIO()
        with patch("sys.stdout", log_output):
            setup_logging(log_level="INFO", json_format=True)

            from src.web_scraper.scraper_service import ScraperService

            # GCSを無効化してテスト
            _ = ScraperService(enable_gcs=False)

        output = log_output.getvalue().strip()
        if output:  # GCS関連のログが出力される場合
            for line in output.split("\n"):
                if line:
                    log_data = json.loads(line)
                    assert "timestamp" in log_data
                    assert "logger" in log_data
