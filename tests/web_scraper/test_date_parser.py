"""Unit tests for date_parser module"""

import logging
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.web_scraper.extractors.date_parser import DateParser


class TestDateParser:
    """Test cases for DateParser"""

    @pytest.fixture
    def parser(self):
        """Create DateParser instance"""
        return DateParser()

    @pytest.fixture
    def parser_with_logger(self):
        """Create DateParser with custom logger"""
        logger = MagicMock(spec=logging.Logger)
        return DateParser(logger=logger), logger

    def test_init_default_logger(self, parser):
        """Test initialization with default logger"""
        assert parser.logger is not None
        assert len(parser._patterns) > 0

    def test_init_custom_logger(self):
        """Test initialization with custom logger"""
        custom_logger = logging.getLogger("test_logger")
        parser = DateParser(logger=custom_logger)
        assert parser.logger == custom_logger

    def test_parse_reiwa_date(self, parser):
        """Test parsing Reiwa era dates"""
        # Test various Reiwa dates
        test_cases = [
            ("令和6年12月20日", datetime(2024, 12, 20)),
            ("令和5年1月1日", datetime(2023, 1, 1)),
            ("令和1年5月1日", datetime(2019, 5, 1)),
        ]

        for date_str, expected in test_cases:
            result = parser.parse(date_str)
            assert result == expected

    def test_parse_heisei_date(self, parser):
        """Test parsing Heisei era dates"""
        test_cases = [
            ("平成31年4月30日", datetime(2019, 4, 30)),
            ("平成30年12月1日", datetime(2018, 12, 1)),
            ("平成1年1月8日", datetime(1989, 1, 8)),
        ]

        for date_str, expected in test_cases:
            result = parser.parse(date_str)
            assert result == expected

    def test_parse_western_date(self, parser):
        """Test parsing Western calendar dates"""
        test_cases = [
            ("2024年12月20日", datetime(2024, 12, 20)),
            ("2023年1月1日", datetime(2023, 1, 1)),
            ("1989年1月8日", datetime(1989, 1, 8)),
        ]

        for date_str, expected in test_cases:
            result = parser.parse(date_str)
            assert result == expected

    def test_parse_fullwidth_numbers(self, parser):
        """Test parsing dates with full-width numbers"""
        test_cases = [
            ("令和６年１２月２０日", datetime(2024, 12, 20)),
            ("平成３１年４月３０日", datetime(2019, 4, 30)),
            ("２０２４年１２月２０日", datetime(2024, 12, 20)),
        ]

        for date_str, expected in test_cases:
            result = parser.parse(date_str)
            assert result == expected

    def test_parse_iso_format(self, parser):
        """Test parsing ISO format dates"""
        test_cases = [
            ("2024-12-20", datetime(2024, 12, 20)),
            ("2023-01-01", datetime(2023, 1, 1)),
            (" 2024-12-20 ", datetime(2024, 12, 20)),  # With whitespace
        ]

        for date_str, expected in test_cases:
            result = parser.parse(date_str)
            assert result == expected

    def test_parse_invalid_dates(self, parser):
        """Test parsing invalid dates returns None"""
        test_cases = [
            "",  # Empty string
            None,  # None value
            "Not a date",  # Invalid format
            "令和100年13月32日",  # Invalid month/day
            "2024/12/20",  # Wrong separator
        ]

        for date_str in test_cases:
            result = parser.parse(date_str)
            assert result is None

    def test_parse_date_in_text(self, parser):
        """Test parsing dates embedded in text"""
        test_cases = [
            ("会議は令和6年12月20日に開催されました。", datetime(2024, 12, 20)),
            ("平成31年4月30日付けで退位", datetime(2019, 4, 30)),
            ("議事録（2024年12月20日）", datetime(2024, 12, 20)),
        ]

        for text, expected in test_cases:
            result = parser.parse(text)
            assert result == expected

    def test_normalize_numbers(self, parser):
        """Test full-width to half-width number conversion"""
        test_cases = [
            ("０１２３４５６７８９", "0123456789"),
            ("令和６年", "令和6年"),
            ("２０２４年１２月", "2024年12月"),
        ]

        for input_text, expected in test_cases:
            result = parser._normalize_numbers(input_text)
            assert result == expected

    def test_create_datetime_valid(self, parser):
        """Test creating valid datetime"""
        result = parser._create_datetime(2024, 12, 20)
        assert result == datetime(2024, 12, 20)

    def test_create_datetime_invalid(self, parser_with_logger):
        """Test creating invalid datetime logs warning"""
        parser, logger = parser_with_logger

        # Try to create invalid date
        result = parser._create_datetime(2024, 13, 32)  # Invalid month/day

        # Should return None and log warning
        assert result is None
        logger.warning.assert_called_once()
        warning_message = logger.warning.call_args[0][0]
        assert "Invalid date:" in warning_message
        assert "year=2024" in warning_message
        assert "month=13" in warning_message
        assert "day=32" in warning_message

    def test_parse_logs_debug_on_failure(self, parser_with_logger):
        """Test that parse logs debug message on failure"""
        parser, logger = parser_with_logger

        # Parse invalid date
        result = parser.parse("This is not a date")

        # Should return None and log debug
        assert result is None
        logger.debug.assert_called_once()
        debug_message = logger.debug.call_args[0][0]
        assert "Failed to parse date" in debug_message
        assert "This is not a date" in debug_message

    def test_patterns_compiled(self, parser):
        """Test that patterns are properly compiled"""
        assert len(parser._patterns) >= 6  # At least 6 patterns

        # Test each pattern is a compiled regex
        for pattern in parser._patterns:
            assert hasattr(pattern, "search")
            assert hasattr(pattern, "match")
