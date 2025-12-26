"""Unit tests for base_scraper module"""

import logging
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.web_scraper.base_scraper import BaseScraper
from src.web_scraper.models import MinutesData, SpeakerData


class ConcreteScraperForTesting(BaseScraper):
    """Concrete implementation of BaseScraper for testing"""

    async def fetch_minutes(self, url: str) -> MinutesData | None:
        return MinutesData(
            council_id="test-council-001",
            schedule_id="test-schedule-001",
            title="Test Meeting",
            date=datetime(2024, 1, 1),
            content="Test content",
            speakers=[],
            url=url,
            scraped_at=datetime.now(),
        )

    async def extract_minutes_text(self, html_content: str) -> str:
        return "Extracted text"

    async def extract_speakers(self, html_content: str) -> list[SpeakerData]:
        return [
            SpeakerData(
                name="Speaker 1",
                content="Test speaker content",
                role="議員",
            )
        ]


class TestBaseScraper:
    """Test cases for BaseScraper"""

    def test_init_with_default_logger(self):
        """Test initialization with default logger"""
        scraper = ConcreteScraperForTesting()
        assert scraper.logger is not None
        assert scraper.date_parser is not None

    def test_init_with_custom_logger(self):
        """Test initialization with custom logger"""
        custom_logger = logging.getLogger("custom_logger")
        scraper = ConcreteScraperForTesting(logger=custom_logger)
        assert scraper.logger == custom_logger

    @pytest.mark.asyncio
    async def test_abstract_methods_implemented(self):
        """Test that abstract methods are properly implemented"""
        scraper = ConcreteScraperForTesting()

        # Test fetch_minutes
        result = await scraper.fetch_minutes("http://test.com")
        assert isinstance(result, MinutesData)
        assert result.council_id == "test-council-001"
        assert result.schedule_id == "test-schedule-001"
        assert result.title == "Test Meeting"

        # Test extract_minutes_text
        text = await scraper.extract_minutes_text("<html>Test</html>")
        assert text == "Extracted text"

        # Test extract_speakers
        speakers = await scraper.extract_speakers("<html>Speakers</html>")
        assert len(speakers) == 1
        assert speakers[0].name == "Speaker 1"

    @patch("src.web_scraper.extractors.date_parser.DateParser.parse")
    def test_parse_japanese_date(self, mock_parse):
        """Test Japanese date parsing"""
        scraper = ConcreteScraperForTesting()

        # Setup mock
        expected_date = datetime(2024, 1, 15)
        mock_parse.return_value = expected_date

        # Execute
        result = scraper.parse_japanese_date("令和6年1月15日")

        # Verify
        assert result == expected_date
        mock_parse.assert_called_once_with("令和6年1月15日")

    def test_parse_japanese_date_none(self):
        """Test Japanese date parsing returns None for invalid date"""
        scraper = ConcreteScraperForTesting()

        # Mock date parser to return None
        scraper.date_parser.parse = MagicMock(return_value=None)

        # Execute
        result = scraper.parse_japanese_date("Invalid date")

        # Verify
        assert result is None


class TestBaseScraperAbstract:
    """Test that BaseScraper cannot be instantiated directly"""

    def test_cannot_instantiate_abstract_class(self):
        """Test that BaseScraper cannot be instantiated"""
        with pytest.raises(TypeError) as exc_info:
            BaseScraper()

        assert "Can't instantiate abstract class" in str(exc_info.value)
