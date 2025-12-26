"""Tests for KokkaiScraper

Tests for the National Diet Minutes Search System scraper without making
real HTTP requests or launching real browsers.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from src.web_scraper.exceptions import ScraperConnectionError, ScraperParseError
from src.web_scraper.kokkai_scraper import KokkaiScraper
from src.web_scraper.models.scraped_data import MinutesData, SpeakerData


class TestKokkaiScraperBrowserManagement:
    """Test browser creation and page loading with retry logic"""

    @pytest.mark.asyncio
    async def test_create_browser_success(self):
        scraper = KokkaiScraper()

        mock_browser = AsyncMock()
        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        with patch("src.web_scraper.kokkai_scraper.async_playwright") as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright)

            browser = await scraper._create_browser()

            assert browser == mock_browser
            mock_playwright.chromium.launch.assert_awaited_once_with(
                headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"]
            )

    @pytest.mark.asyncio
    async def test_load_page_with_retry_success_first_try(self):
        scraper = KokkaiScraper()
        mock_page = AsyncMock()
        test_url = "https://kokkai.ndl.go.jp/test"

        await scraper._load_page_with_retry(mock_page, test_url, retry_count=3)

        mock_page.goto.assert_awaited_once()
        mock_page.wait_for_timeout.assert_awaited_once_with(3000)
        mock_page.wait_for_selector.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_load_page_with_retry_success_after_retry(self):
        scraper = KokkaiScraper()
        mock_page = AsyncMock()
        test_url = "https://kokkai.ndl.go.jp/test"

        mock_page.goto.side_effect = [PlaywrightTimeoutError("Timeout"), None]

        await scraper._load_page_with_retry(mock_page, test_url, retry_count=3)

        assert mock_page.goto.await_count == 2
        mock_page.wait_for_timeout.assert_awaited()
        mock_page.wait_for_selector.assert_awaited()

    @pytest.mark.asyncio
    async def test_load_page_with_retry_max_retries_exceeded(self):
        scraper = KokkaiScraper()
        mock_page = AsyncMock()
        test_url = "https://kokkai.ndl.go.jp/test"

        mock_page.goto.side_effect = PlaywrightTimeoutError("Timeout")

        with pytest.raises(
            ScraperConnectionError, match="Failed to load page after 3 attempts"
        ):
            await scraper._load_page_with_retry(mock_page, test_url, retry_count=3)

        assert mock_page.goto.await_count == 3

    @pytest.mark.asyncio
    async def test_load_page_with_retry_timeout(self):
        scraper = KokkaiScraper()
        mock_page = AsyncMock()
        test_url = "https://kokkai.ndl.go.jp/test"

        mock_page.goto.side_effect = PlaywrightTimeoutError("Navigation timeout")

        with pytest.raises(ScraperConnectionError):
            await scraper._load_page_with_retry(mock_page, test_url, retry_count=2)


class TestKokkaiScraperMainMethods:
    """Test main scraping methods"""

    @pytest.mark.asyncio
    async def test_fetch_minutes_success(self):
        scraper = KokkaiScraper()
        test_url = "https://kokkai.ndl.go.jp/test?sessionId=123&scheduleId=456"

        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)

        expected_minutes = MinutesData(
            council_id="123",
            schedule_id="456",
            title="Test Meeting",
            date=datetime(2024, 1, 1),
            content="Test content",
            speakers=[],
            url=test_url,
            scraped_at=datetime.now(),
        )

        with patch.object(scraper, "_create_browser", return_value=mock_browser):
            with patch.object(scraper, "_load_page_with_retry", return_value=None):
                with patch.object(
                    scraper, "_extract_minutes_data", return_value=expected_minutes
                ):
                    result = await scraper.fetch_minutes(test_url)

                    assert result == expected_minutes
                    mock_browser.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_fetch_minutes_invalid_url(self):
        scraper = KokkaiScraper()
        invalid_url = "https://example.com/invalid"

        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)

        with patch.object(scraper, "_create_browser", return_value=mock_browser):
            with patch.object(scraper, "_load_page_with_retry", return_value=None):
                with patch.object(
                    scraper,
                    "_extract_minutes_data",
                    side_effect=ScraperParseError("Invalid URL format"),
                ):
                    with pytest.raises(
                        ScraperParseError, match="Failed to fetch minutes"
                    ):
                        await scraper.fetch_minutes(invalid_url)

    @pytest.mark.asyncio
    async def test_fetch_minutes_network_error(self):
        scraper = KokkaiScraper()
        test_url = "https://kokkai.ndl.go.jp/test?sessionId=123&scheduleId=456"

        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)

        with patch.object(scraper, "_create_browser", return_value=mock_browser):
            with patch.object(
                scraper,
                "_load_page_with_retry",
                side_effect=ScraperConnectionError("Network error"),
            ):
                with pytest.raises(ScraperParseError, match="Failed to fetch minutes"):
                    await scraper.fetch_minutes(test_url)

                mock_browser.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_fetch_minutes_missing_content(self):
        scraper = KokkaiScraper()
        test_url = "https://kokkai.ndl.go.jp/test?sessionId=123&scheduleId=456"

        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)

        with patch.object(scraper, "_create_browser", return_value=mock_browser):
            with patch.object(scraper, "_load_page_with_retry", return_value=None):
                with patch.object(
                    scraper,
                    "_extract_minutes_data",
                    side_effect=ScraperParseError("No content found"),
                ):
                    with pytest.raises(ScraperParseError):
                        await scraper.fetch_minutes(test_url)

    @pytest.mark.asyncio
    async def test_extract_minutes_data_complete(self):
        scraper = KokkaiScraper()
        mock_page = AsyncMock()
        test_url = "https://kokkai.ndl.go.jp/test?sessionId=123&scheduleId=456"

        with patch.object(
            scraper,
            "_extract_meeting_info",
            return_value={"title": "Test Meeting", "date": "2024年1月1日"},
        ):
            with patch.object(scraper, "_extract_title", return_value="Test Meeting"):
                with patch.object(
                    scraper, "_extract_content", return_value="Test content"
                ):
                    with patch.object(scraper, "_extract_speakers", return_value=[]):
                        result = await scraper._extract_minutes_data(
                            mock_page, test_url
                        )

                        assert isinstance(result, MinutesData)
                        assert result.title == "Test Meeting"
                        assert result.content == "Test content"

    @pytest.mark.asyncio
    async def test_extract_minutes_data_minimal(self):
        scraper = KokkaiScraper()
        mock_page = AsyncMock()
        test_url = "https://kokkai.ndl.go.jp/test?sessionId=123&scheduleId=456"

        with patch.object(
            scraper,
            "_extract_meeting_info",
            return_value={"title": "Minimal Meeting", "date": ""},
        ):
            with patch.object(
                scraper, "_extract_title", return_value="Minimal Meeting"
            ):
                with patch.object(
                    scraper, "_extract_content", return_value="Some content"
                ):
                    with patch.object(scraper, "_extract_speakers", return_value=[]):
                        result = await scraper._extract_minutes_data(
                            mock_page, test_url
                        )

                        assert result.title == "Minimal Meeting"
                        assert result.date is None

    @pytest.mark.asyncio
    async def test_extract_meeting_info_success(self):
        scraper = KokkaiScraper()
        mock_page = AsyncMock()

        mock_h2_element = MagicMock()
        mock_h2_element.inner_text = AsyncMock(
            return_value="第123回国会　衆議院　予算委員会　第1号　令和6年1月15日"
        )
        mock_page.query_selector = AsyncMock(return_value=mock_h2_element)

        result = await scraper._extract_meeting_info(mock_page)

        assert (
            result["title"] == "第123回国会　衆議院　予算委員会　第1号　令和6年1月15日"
        )
        assert "date" in result
        assert result["date"] == "令和6年1月15日"

    @pytest.mark.asyncio
    async def test_extract_meeting_info_missing_fields(self):
        scraper = KokkaiScraper()
        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)

        result = await scraper._extract_meeting_info(mock_page)

        assert result == {}


class TestKokkaiScraperContentExtraction:
    """Test content and speaker extraction methods"""

    @pytest.mark.asyncio
    async def test_extract_title_success(self):
        scraper = KokkaiScraper()
        mock_page = AsyncMock()

        mock_element = MagicMock()
        mock_element.inner_text = AsyncMock(return_value="第123回国会 予算委員会 第1号")
        mock_page.query_selector = AsyncMock(return_value=mock_element)

        result = await scraper._extract_title(mock_page)

        assert result == "第123回国会 予算委員会 第1号"
        mock_page.query_selector.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_extract_title_not_found(self):
        scraper = KokkaiScraper()
        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.title = AsyncMock(return_value="")

        result = await scraper._extract_title(mock_page)

        assert result == ""

    @pytest.mark.asyncio
    async def test_extract_content_with_tables(self):
        scraper = KokkaiScraper()
        mock_page = AsyncMock()

        mock_cell = MagicMock()
        mock_cell.inner_text = AsyncMock(
            return_value="これは議事録の本文です。二十文字以上のテキストを含む内容です。"
        )

        mock_row = MagicMock()
        mock_row.query_selector_all = AsyncMock(return_value=[MagicMock(), mock_cell])

        mock_table = MagicMock()
        mock_table.query_selector_all = AsyncMock(return_value=[mock_row])

        mock_page.query_selector_all = AsyncMock(return_value=[mock_table])

        result = await scraper._extract_content(mock_page)

        assert "議事録の本文" in result

    @pytest.mark.asyncio
    async def test_extract_content_fallback_to_body(self):
        scraper = KokkaiScraper()
        mock_page = AsyncMock()

        mock_page.query_selector_all = AsyncMock(return_value=[])
        mock_page.inner_text = AsyncMock(return_value="これは長いテキストです。" * 10)

        result = await scraper._extract_content(mock_page)

        assert "これは長いテキストです" in result

    @pytest.mark.asyncio
    async def test_extract_content_empty(self):
        scraper = KokkaiScraper()
        mock_page = AsyncMock()
        mock_page.query_selector_all = AsyncMock(return_value=[])
        mock_page.inner_text = AsyncMock(return_value="")

        result = await scraper._extract_content(mock_page)

        assert result == ""

    @pytest.mark.asyncio
    async def test_extract_speakers_multiple(self):
        scraper = KokkaiScraper()
        mock_page = AsyncMock()

        mock_speaker1 = MagicMock()
        mock_speaker1.inner_text = AsyncMock(return_value="001 山田太郎 発言者情報")
        mock_speaker2 = MagicMock()
        mock_speaker2.inner_text = AsyncMock(return_value="002 佐藤花子 発言者情報")

        mock_page.query_selector_all = AsyncMock(
            return_value=[mock_speaker1, mock_speaker2]
        )

        result = await scraper._extract_speakers(mock_page)

        assert len(result) == 2
        assert all(isinstance(s, SpeakerData) for s in result)
        assert result[0].name == "山田太郎"
        assert result[1].name == "佐藤花子"

    @pytest.mark.asyncio
    async def test_extract_speakers_single(self):
        scraper = KokkaiScraper()
        mock_page = AsyncMock()

        mock_speaker = MagicMock()
        mock_speaker.inner_text = AsyncMock(return_value="001 委員長 発言者情報")
        mock_page.query_selector_all = AsyncMock(return_value=[mock_speaker])

        result = await scraper._extract_speakers(mock_page)

        assert len(result) == 1
        assert result[0].name == "委員長"

    @pytest.mark.asyncio
    async def test_extract_speakers_none(self):
        scraper = KokkaiScraper()
        mock_page = AsyncMock()
        mock_page.query_selector_all = AsyncMock(return_value=[])

        result = await scraper._extract_speakers(mock_page)

        assert result == []


class TestKokkaiScraperUtilityMethods:
    """Test utility and helper methods"""

    def test_normalize_speaker_name_with_honorifics(self):
        scraper = KokkaiScraper()

        assert scraper._normalize_speaker_name("山田太郎君") == "山田太郎"
        assert scraper._normalize_speaker_name("山田太郎議員") == "山田太郎"
        assert scraper._normalize_speaker_name("○山田太郎君") == "山田太郎"

    def test_normalize_speaker_name_without_honorifics(self):
        scraper = KokkaiScraper()

        assert scraper._normalize_speaker_name("山田太郎") == "山田太郎"
        assert scraper._normalize_speaker_name("委員長") == "委員長"

    def test_parse_date_japanese_era(self):
        scraper = KokkaiScraper()

        result = scraper._parse_date("令和6年1月15日")
        assert result == datetime(2024, 1, 15)

    def test_parse_date_western_format(self):
        scraper = KokkaiScraper()

        result = scraper._parse_date("2024年1月15日")
        assert result == datetime(2024, 1, 15)

    def test_parse_date_invalid_format(self):
        scraper = KokkaiScraper()

        result = scraper._parse_date("invalid date")
        assert result is None

    def test_extract_ids_from_url_success(self):
        scraper = KokkaiScraper()

        url = "https://kokkai.ndl.go.jp/minutes?minId=121705253X00320250423"
        council_id, schedule_id = scraper._extract_ids_from_url(url)

        assert council_id == "kokkai_121705253"
        assert schedule_id == "X00320250423"

    def test_extract_ids_from_url_no_minid(self):
        scraper = KokkaiScraper()

        url = "https://kokkai.ndl.go.jp/invalid"
        council_id, schedule_id = scraper._extract_ids_from_url(url)

        assert council_id == "kokkai_unknown"
        assert schedule_id == "1"

    @pytest.mark.asyncio
    async def test_extract_minutes_text_stub(self):
        scraper = KokkaiScraper()

        result = await scraper.extract_minutes_text("")

        assert result == ""

    @pytest.mark.asyncio
    async def test_extract_speakers_stub(self):
        scraper = KokkaiScraper()

        result = await scraper.extract_speakers("")

        assert result == []
