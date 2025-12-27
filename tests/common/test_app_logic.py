"""Tests for common application logic."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.application.exceptions import (
    ConfigurationError,
    PDFProcessingError,
    ProcessingError,
)
from src.common.app_logic import (
    load_pdf_text,
    print_completion_message,
    run_main_process,
    setup_environment,
    validate_database_connection,
)
from src.infrastructure.exceptions import DatabaseError
from src.infrastructure.exceptions import (
    FileNotFoundException as PolibaseFileNotFoundError,
)


class TestSetupEnvironment:
    """Test cases for setup_environment function."""

    @patch("src.common.app_logic.config.validate_config")
    @patch("src.common.app_logic.config.set_env")
    def test_setup_environment_success(self, mock_set_env, mock_validate):
        """Test successful environment setup."""
        # Execute
        setup_environment()

        # Verify
        mock_set_env.assert_called_once()
        mock_validate.assert_called_once()

    @patch("src.common.app_logic.config.set_env")
    def test_setup_environment_failure(self, mock_set_env):
        """Test environment setup failure."""
        # Setup
        mock_set_env.side_effect = Exception("Config error")

        # Execute and verify
        with pytest.raises(ConfigurationError) as exc_info:
            setup_environment()

        assert "Failed to setup application environment" in str(exc_info.value)


class TestLoadPdfText:
    """Test cases for load_pdf_text function."""

    @patch("os.path.exists")
    def test_load_pdf_text_file_not_found(self, mock_exists):
        """Test error when PDF file doesn't exist."""
        # Setup
        mock_exists.return_value = False

        # Execute and verify
        with pytest.raises(PolibaseFileNotFoundError) as exc_info:
            load_pdf_text("/nonexistent.pdf")

        # Check that the error message contains the file path
        assert "/nonexistent.pdf" in str(exc_info.value)

    @patch("os.path.exists")
    @patch("builtins.open")
    def test_load_pdf_text_empty_file(self, mock_open, mock_exists):
        """Test error when PDF file is empty."""
        # Setup
        mock_exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = b""
        mock_open.return_value.__enter__.return_value = mock_file

        # Execute and verify
        with pytest.raises(PDFProcessingError) as exc_info:
            load_pdf_text("/empty.pdf")

        assert "PDF file is empty" in str(exc_info.value)

    @patch("os.path.exists")
    @patch("builtins.open")
    @patch("src.common.app_logic.extract_text_from_pdf")
    def test_load_pdf_text_success(self, mock_extract, mock_open, mock_exists):
        """Test successful PDF text loading."""
        # Setup
        mock_exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = b"PDF content"
        mock_open.return_value.__enter__.return_value = mock_file
        mock_extract.return_value = "Extracted text"

        # Execute
        result = load_pdf_text("/test.pdf")

        # Verify
        assert result == "Extracted text"
        mock_extract.assert_called_once_with(b"PDF content")

    @patch("os.path.exists")
    @patch("builtins.open")
    @patch("src.common.app_logic.extract_text_from_pdf")
    def test_load_pdf_text_extraction_error(self, mock_extract, mock_open, mock_exists):
        """Test PDF processing error propagation."""
        # Setup
        mock_exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = b"PDF content"
        mock_open.return_value.__enter__.return_value = mock_file
        mock_extract.side_effect = PDFProcessingError("Extraction failed")

        # Execute and verify
        with pytest.raises(PDFProcessingError) as exc_info:
            load_pdf_text("/test.pdf")

        assert "Extraction failed" in str(exc_info.value)

    @patch("os.path.exists")
    @patch("builtins.open")
    def test_load_pdf_text_read_error(self, mock_open, mock_exists):
        """Test error when file reading fails."""
        # Setup
        mock_exists.return_value = True
        mock_open.side_effect = OSError("Read error")

        # Execute and verify
        with pytest.raises(PDFProcessingError) as exc_info:
            load_pdf_text("/test.pdf")

        assert "Failed to process PDF file" in str(exc_info.value)


class TestValidateDatabaseConnection:
    """Test cases for validate_database_connection function."""

    @patch("src.common.app_logic.test_connection")
    def test_validate_database_connection_success(self, mock_test_conn):
        """Test successful database connection validation."""
        # Setup
        mock_test_conn.return_value = True

        # Execute
        result = validate_database_connection()

        # Verify
        assert result is True
        mock_test_conn.assert_called_once()

    @patch("src.common.app_logic.test_connection")
    def test_validate_database_connection_failure(self, mock_test_conn):
        """Test failed database connection validation."""
        # Setup
        mock_test_conn.return_value = False

        # Execute
        result = validate_database_connection()

        # Verify
        assert result is False

    @patch("src.common.app_logic.test_connection")
    def test_validate_database_connection_error(self, mock_test_conn):
        """Test database connection test error."""
        # Setup
        mock_test_conn.side_effect = Exception("Connection error")

        # Execute and verify
        with pytest.raises(DatabaseError) as exc_info:
            validate_database_connection()

        assert "Failed to test database connection" in str(exc_info.value)


class TestRunMainProcess:
    """Test cases for run_main_process function."""

    @patch("src.common.app_logic.validate_database_connection")
    def test_run_main_process_db_validation_fails(self, mock_validate_db):
        """Test when database validation fails."""
        # Setup
        mock_validate_db.return_value = False
        mock_process = Mock()
        mock_display = Mock()
        mock_save = Mock()

        # Execute
        result = run_main_process(mock_process, "TestProcess", mock_display, mock_save)

        # Verify
        assert result is None
        mock_process.assert_not_called()

    @patch("src.common.app_logic.validate_database_connection")
    def test_run_main_process_no_results(self, mock_validate_db):
        """Test when process returns no results."""
        # Setup
        mock_validate_db.return_value = True
        mock_process = Mock(return_value=None)
        mock_display = Mock()
        mock_save = Mock()

        # Execute
        result = run_main_process(
            mock_process, "TestProcess", mock_display, mock_save, "arg1", key="value"
        )

        # Verify
        assert result is None
        mock_process.assert_called_once_with("arg1", key="value")
        mock_save.assert_not_called()

    @patch("src.common.app_logic.validate_database_connection")
    def test_run_main_process_success(self, mock_validate_db):
        """Test successful process execution."""
        # Setup
        mock_validate_db.return_value = True
        process_result = {"data": "test"}
        mock_process = Mock(return_value=process_result)
        mock_display = Mock()
        mock_save = Mock(return_value=[1, 2, 3])

        # Execute
        result = run_main_process(mock_process, "TestProcess", mock_display, mock_save)

        # Verify
        assert result == process_result
        mock_display.assert_called()
        mock_save.assert_called_once_with(process_result)

    @patch("src.common.app_logic.validate_database_connection")
    def test_run_main_process_save_returns_empty(self, mock_validate_db):
        """Test when save function returns empty list."""
        # Setup
        mock_validate_db.return_value = True
        process_result = {"data": "test"}
        mock_process = Mock(return_value=process_result)
        mock_display = Mock()
        mock_save = Mock(return_value=[])

        # Execute
        result = run_main_process(mock_process, "TestProcess", mock_display, mock_save)

        # Verify
        assert result == process_result
        mock_save.assert_called_once_with(process_result)

    @patch("src.common.app_logic.validate_database_connection")
    def test_run_main_process_database_error(self, mock_validate_db):
        """Test DatabaseError propagation."""
        # Setup
        mock_validate_db.return_value = True
        mock_process = Mock(side_effect=DatabaseError("DB error"))
        mock_display = Mock()
        mock_save = Mock()

        # Execute and verify
        with pytest.raises(DatabaseError) as exc_info:
            run_main_process(mock_process, "TestProcess", mock_display, mock_save)

        assert "DB error" in str(exc_info.value)

    @patch("src.common.app_logic.validate_database_connection")
    def test_run_main_process_generic_error(self, mock_validate_db):
        """Test generic error handling."""
        # Setup
        mock_validate_db.return_value = True
        mock_process = Mock(side_effect=RuntimeError("Unexpected error"))
        mock_display = Mock()
        mock_save = Mock()

        # Execute and verify
        with pytest.raises(ProcessingError) as exc_info:
            run_main_process(mock_process, "TestProcess", mock_display, mock_save)

        assert "TestProcess processing failed" in str(exc_info.value)


class TestPrintCompletionMessage:
    """Test cases for print_completion_message function."""

    def test_print_completion_message_none_result(self, capsys):
        """Test with None result."""
        print_completion_message(None, "テスト処理")

        captured = capsys.readouterr()
        assert "✅ テスト処理が全部終わったよ" in captured.out

    def test_print_completion_message_empty_list(self, capsys):
        """Test with empty list."""
        print_completion_message([], "テスト処理")

        captured = capsys.readouterr()
        assert "結果数: 0件" in captured.out

    def test_print_completion_message_small_list(self, capsys):
        """Test with small list (5 or fewer items)."""
        items = ["Item1", "Item2", "Item3"]
        print_completion_message(items, "テスト処理")

        captured = capsys.readouterr()
        assert "結果数: 3件" in captured.out
        assert "1. Item1" in captured.out
        assert "2. Item2" in captured.out
        assert "3. Item3" in captured.out

    def test_print_completion_message_large_list(self, capsys):
        """Test with large list (more than 5 items)."""
        items = [f"Item{i}" for i in range(10)]
        print_completion_message(items, "テスト処理")

        captured = capsys.readouterr()
        assert "結果数: 10件" in captured.out
        assert "1. Item0" in captured.out
        assert "2. Item1" in captured.out
        assert "3. Item2" in captured.out
        assert "... 他 7 件" in captured.out

    def test_print_completion_message_non_list(self, capsys):
        """Test with non-list result."""
        result = {"key": "value", "count": 42}
        print_completion_message(result, "テスト処理")

        captured = capsys.readouterr()
        assert str(result) in captured.out
