"""Unit tests for ProposalScraperService."""

import json

from typing import Any
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

import pytest

from src.domain.services.interfaces.llm_service import ILLMService
from src.domain.types.scraper_types import ScrapedProposal
from src.infrastructure.external.proposal_scraper_service import (
    ProposalScraperService,
)


class TestProposalScraperService:
    """Test suite for ProposalScraperService."""

    @pytest.fixture
    def mock_llm_service(self) -> MagicMock:
        """Create a mock LLM service."""
        return create_autospec(ILLMService, spec_set=True)

    @pytest.fixture
    def scraper(self, mock_llm_service: MagicMock) -> ProposalScraperService:
        """Create a ProposalScraperService instance."""
        return ProposalScraperService(llm_service=mock_llm_service, headless=True)

    def test_is_supported_url_valid_urls(self, scraper: ProposalScraperService) -> None:
        """Test that any valid HTTP/HTTPS URLs are supported."""
        urls = [
            "https://www.shugiin.go.jp/internet/itdb_gian.nsf/html/gian/honbun/houan/g21009001.htm",
            "http://example.com/some/page",
            "https://www.city.kyoto.lg.jp/shikai/page/0000123456.html",
            "https://www.google.com",
            "https://www.any-website.com/page",
        ]
        for url in urls:
            assert scraper.is_supported_url(url) is True

    def test_is_supported_url_invalid_urls(
        self, scraper: ProposalScraperService
    ) -> None:
        """Test that invalid URLs are not supported."""
        urls: list[Any] = [
            "not-a-url",
            "ftp://example.com",
            "",
            None,
        ]
        for url in urls:
            assert scraper.is_supported_url(url) is False

    @pytest.mark.asyncio
    async def test_scrape_proposal_invalid_url(
        self, scraper: ProposalScraperService
    ) -> None:
        """Test that scraping invalid URLs raises ValueError."""
        url = "not-a-valid-url"
        with pytest.raises(ValueError, match="Invalid URL format"):
            await scraper.scrape_proposal(url)

    @pytest.mark.asyncio
    @patch("src.infrastructure.external.proposal_scraper_service.async_playwright")
    async def test_scrape_proposal_with_llm(
        self,
        mock_playwright: MagicMock,
        scraper: ProposalScraperService,
        mock_llm_service: MagicMock,
    ) -> None:
        """Test scraping a proposal using LLM extraction."""
        # Mock the HTML content
        html_content = """
        <html>
            <head><title>第210回国会 第1号 環境基本法改正案</title></head>
            <body>
                <h1>第210回国会 第1号 環境基本法改正案</h1>
                <div>提出日：2023年12月1日</div>
                <div class="summary">この法案は環境保護を強化するものです。</div>
            </body>
        </html>
        """

        # Set up mocks
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.content.return_value = html_content
        mock_browser.new_page.return_value = mock_page

        mock_chromium = AsyncMock()
        mock_chromium.launch.return_value = mock_browser

        mock_p = AsyncMock()
        mock_p.chromium = mock_chromium
        mock_p.__aenter__.return_value = mock_p
        mock_p.__aexit__.return_value = None

        mock_playwright.return_value = mock_p

        # Mock LLM response
        llm_response = json.dumps(
            {
                "content": "環境基本法改正案",
                "proposal_number": "第210回国会 第1号",
                "submission_date": "2023年12月1日",
                "summary": "この法案は環境保護を強化するものです。",
            }
        )
        mock_llm_service.invoke_llm.return_value = llm_response

        # Execute
        url = "https://www.shugiin.go.jp/test"
        result = await scraper.scrape_proposal(url)

        # Assert
        assert isinstance(result, ScrapedProposal)
        assert result.url == url
        assert result.content == "環境基本法改正案"
        assert result.proposal_number == "第210回国会 第1号"
        assert result.submission_date == "2023年12月1日"
        assert result.summary == "この法案は環境保護を強化するものです。"

        # Verify LLM was called
        mock_llm_service.invoke_llm.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.infrastructure.external.proposal_scraper_service.async_playwright")
    async def test_scrape_different_council_proposal(
        self,
        mock_playwright: MagicMock,
        scraper: ProposalScraperService,
        mock_llm_service: MagicMock,
    ) -> None:
        """Test scraping any council proposal with flexible LLM extraction."""
        # Mock the HTML content (could be from any council)
        html_content = """
        <html>
            <head><title>大阪府議会議案</title></head>
            <body>
                <h1>大阪府デジタル化推進条例案</h1>
                <div>議案番号：第25号</div>
                <div>上程日：令和5年12月20日</div>
                <section class="詳細">
                    デジタル技術を活用した行政サービスの向上を図る条例案
                </section>
            </body>
        </html>
        """

        # Set up mocks
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.content.return_value = html_content
        mock_browser.new_page.return_value = mock_page

        mock_chromium = AsyncMock()
        mock_chromium.launch.return_value = mock_browser

        mock_p = AsyncMock()
        mock_p.chromium = mock_chromium
        mock_p.__aenter__.return_value = mock_p
        mock_p.__aexit__.return_value = None

        mock_playwright.return_value = mock_p

        # Mock LLM response - extracts without date format conversion
        llm_response = json.dumps(
            {
                "content": "大阪府デジタル化推進条例案",
                "proposal_number": "第25号",
                "submission_date": "令和5年12月20日",
                "summary": "デジタル技術を活用した行政サービスの向上を図る条例案",
            }
        )
        mock_llm_service.invoke_llm.return_value = llm_response

        # Execute
        url = "https://www.pref.osaka.lg.jp/test"
        result = await scraper.scrape_proposal(url)

        # Assert - dates are kept as extracted, no conversion
        assert isinstance(result, ScrapedProposal)
        assert result.url == url
        assert result.content == "大阪府デジタル化推進条例案"
        assert result.proposal_number == "第25号"
        assert result.submission_date == "令和5年12月20日"  # Not converted to ISO
        assert result.summary == "デジタル技術を活用した行政サービスの向上を図る条例案"

    @pytest.mark.asyncio
    @patch("src.infrastructure.external.proposal_scraper_service.async_playwright")
    async def test_scrape_proposal_runtime_error(
        self, mock_playwright: MagicMock, scraper: ProposalScraperService
    ) -> None:
        """Test that scraping errors are properly handled."""
        # Set up mocks to raise an exception
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.goto.side_effect = Exception("Network error")
        mock_browser.new_page.return_value = mock_page

        mock_chromium = AsyncMock()
        mock_chromium.launch.return_value = mock_browser

        mock_p = AsyncMock()
        mock_p.chromium = mock_chromium
        mock_p.__aenter__.return_value = mock_p
        mock_p.__aexit__.return_value = None

        mock_playwright.return_value = mock_p

        # Execute and assert
        url = "https://www.shugiin.go.jp/test"
        with pytest.raises(RuntimeError, match="Failed to scrape proposal from"):
            await scraper.scrape_proposal(url)

    @pytest.mark.asyncio
    @patch("src.infrastructure.external.proposal_scraper_service.async_playwright")
    async def test_scrape_proposal_with_invalid_json_response(
        self,
        mock_playwright: MagicMock,
        scraper: ProposalScraperService,
        mock_llm_service: MagicMock,
    ) -> None:
        """Test handling of invalid JSON response from LLM."""
        # Mock the HTML content
        html_content = "<html><body><h1>Test</h1></body></html>"

        # Set up mocks
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.content.return_value = html_content
        mock_browser.new_page.return_value = mock_page

        mock_chromium = AsyncMock()
        mock_chromium.launch.return_value = mock_browser

        mock_p = AsyncMock()
        mock_p.chromium = mock_chromium
        mock_p.__aenter__.return_value = mock_p
        mock_p.__aexit__.return_value = None

        mock_playwright.return_value = mock_p

        # Mock LLM response with invalid JSON
        mock_llm_service.invoke_llm.return_value = "This is not valid JSON"

        # Execute
        url = "https://www.city.tokyo.lg.jp/test"
        result = await scraper.scrape_proposal(url)

        # Assert - should handle gracefully and return empty fields
        assert isinstance(result, ScrapedProposal)
        assert result.url == url
        assert result.content == ""
        assert result.proposal_number is None
        assert result.submission_date is None
        assert result.summary is None
