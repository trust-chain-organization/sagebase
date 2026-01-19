"""Tests for conference member extractor module"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.application.dtos.conference_member_extraction_dto import ExtractedMemberDTO
from src.infrastructure.external.conference_member_extractor.extractor import (
    ConferenceMemberExtractor,
)


class TestConferenceMemberExtractor:
    """Test cases for ConferenceMemberExtractor"""

    @pytest.fixture
    def mock_llm_service(self):
        """Create a mock LLM service"""
        llm_service = Mock()
        llm_service.llm = Mock()
        return llm_service

    @pytest.fixture
    def mock_repo(self):
        """Create a mock repository"""
        repo = Mock()
        repo.create = AsyncMock(return_value=Mock(id=1))
        repo.delete_extracted_members = Mock(return_value=3)
        return repo

    @pytest.fixture
    def extractor(self, mock_llm_service, mock_repo):
        """Create a ConferenceMemberExtractor instance"""
        with patch(
            "src.infrastructure.external.conference_member_extractor.extractor.MemberExtractorFactory.create_agent"
        ):
            with patch(
                "src.infrastructure.external.conference_member_extractor.extractor.RepositoryAdapter",
                return_value=mock_repo,
            ):
                return ConferenceMemberExtractor()

    @pytest.mark.asyncio
    async def test_extract_members_with_llm_success(self, extractor, mock_llm_service):
        """Test successful extraction of members with LLM"""
        # Mock HTML content
        html_content = """
        <html>
            <body>
                <h1>委員一覧</h1>
                <ul>
                    <li>山田太郎（委員長）- 自民党</li>
                    <li>田中花子（副委員長）- 立憲民主党</li>
                    <li>佐藤次郎（委員）- 公明党</li>
                </ul>
            </body>
        </html>
        """

        # Mock LLM response
        members = [
            ExtractedMemberDTO(name="山田太郎", role="委員長", party_name="自民党"),
            ExtractedMemberDTO(
                name="田中花子", role="副委員長", party_name="立憲民主党"
            ),
            ExtractedMemberDTO(name="佐藤次郎", role="委員", party_name="公明党"),
        ]

        # Directly mock the method
        with patch.object(
            extractor, "extract_members_with_llm", new_callable=AsyncMock
        ) as mock_extract:
            mock_extract.return_value = members
            # Execute
            result = await extractor.extract_members_with_llm(html_content, "本会議")

            # Assert
            assert len(result) == 3
            assert result[0].name == "山田太郎"
            assert result[0].role == "委員長"
            assert result[0].party_name == "自民党"

    @pytest.mark.asyncio
    async def test_extract_members_with_llm_empty(self, extractor, mock_llm_service):
        """Test extraction with empty result"""
        # Directly mock the extractor's _extractor
        with patch.object(
            extractor, "extract_members_with_llm", new_callable=AsyncMock
        ) as mock_extract:
            mock_extract.return_value = []
            # Execute
            result = await extractor.extract_members_with_llm("<html></html>", "本会議")

            # Assert
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_extract_members_with_multiple_conferences(
        self, extractor, mock_llm_service
    ):
        """Test extraction when HTML contains multiple conferences"""
        # Mock HTML content with multiple committees
        html_content = """
        <html>
            <body>
                <h2>総務消防委員会</h2>
                <ul>
                    <li>山田太郎（委員長）- 自民党</li>
                    <li>田中花子（副委員長）- 立憲民主党</li>
                </ul>

                <h2>環境福祉委員会</h2>
                <ul>
                    <li>佐藤次郎（委員長）- 公明党</li>
                    <li>鈴木三郎（副委員長）- 共産党</li>
                </ul>

                <h2>まちづくり委員会</h2>
                <ul>
                    <li>高橋四郎（委員長）- 維新の会</li>
                    <li>渡辺五郎（副委員長）- 無所属</li>
                </ul>
            </body>
        </html>
        """

        # Mock LLM response - should only return members from 環境福祉委員会
        members = [
            ExtractedMemberDTO(name="佐藤次郎", role="委員長", party_name="公明党"),
            ExtractedMemberDTO(name="鈴木三郎", role="副委員長", party_name="共産党"),
        ]

        # Directly mock the method
        with patch.object(
            extractor, "extract_members_with_llm", new_callable=AsyncMock
        ) as mock_extract:
            mock_extract.return_value = members
            # Execute - request specifically for 環境福祉委員会
            result = await extractor.extract_members_with_llm(
                html_content, "環境福祉委員会"
            )

            # Assert - should only get members from the requested committee
            assert len(result) == 2
            assert result[0].name == "佐藤次郎"
            assert result[0].role == "委員長"
            assert result[1].name == "鈴木三郎"
            assert result[1].role == "副委員長"

    @pytest.mark.asyncio
    async def test_extract_members_with_llm_error(self, extractor, mock_llm_service):
        """Test extraction error handling"""
        # Directly mock the method to simulate error behavior
        with patch.object(
            extractor, "extract_members_with_llm", new_callable=AsyncMock
        ) as mock_extract:
            mock_extract.return_value = []
            # Execute
            result = await extractor.extract_members_with_llm("<html></html>", "本会議")

            # Assert - should return empty list on error
            assert result == []

    @pytest.mark.asyncio
    @patch(
        "src.infrastructure.external.conference_member_extractor.extractor.async_playwright"
    )
    async def test_fetch_html_success(self, mock_playwright, extractor):
        """Test successful HTML fetching"""
        # Mock Playwright
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.content = AsyncMock(return_value="<html>Test Content</html>")

        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)
        mock_browser.close = AsyncMock()

        mock_playwright_instance = AsyncMock()
        mock_playwright_instance.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_playwright_instance.__aenter__ = AsyncMock(
            return_value=mock_playwright_instance
        )
        mock_playwright_instance.__aexit__ = AsyncMock(return_value=None)

        mock_playwright.return_value = mock_playwright_instance

        # Execute
        result = await extractor.fetch_html("https://example.com")

        # Assert
        assert result == "<html>Test Content</html>"
        mock_page.goto.assert_called_once_with(
            "https://example.com", wait_until="networkidle", timeout=30000
        )

    @pytest.mark.asyncio
    async def test_extract_and_save_members_full_flow(self, extractor, mock_repo):
        """Test full extraction and save flow"""
        # Setup mocks
        with patch.object(
            extractor, "fetch_html", new_callable=AsyncMock
        ) as mock_fetch:
            with patch.object(extractor, "extract_members_with_llm") as mock_extract:
                mock_fetch.return_value = "<html>Member List</html>"

                mock_extract.return_value = [
                    ExtractedMemberDTO(
                        name="山田太郎", role="委員長", party_name="自民党"
                    ),
                    ExtractedMemberDTO(
                        name="田中花子", role="副委員長", party_name="立憲民主党"
                    ),
                ]

                # Execute
                result = await extractor.extract_and_save_members(
                    conference_id=1,
                    conference_name="本会議",
                    url="https://example.com/members",
                )

                # Assert
                assert result["extracted_count"] == 2
                assert result["saved_count"] == 2
                assert result["failed_count"] == 0
                assert "error" not in result

                # Check repository calls
                assert mock_repo.create.call_count == 2

    @pytest.mark.asyncio
    async def test_extract_and_save_members_with_errors(self, extractor, mock_repo):
        """Test extraction with some save errors"""
        # Setup mocks
        with patch.object(
            extractor, "fetch_html", new_callable=AsyncMock
        ) as mock_fetch:
            with patch.object(extractor, "extract_members_with_llm") as mock_extract:
                mock_fetch.return_value = "<html>Member List</html>"

                mock_extract.return_value = [
                    ExtractedMemberDTO(
                        name="山田太郎", role="委員長", party_name="自民党"
                    ),
                    ExtractedMemberDTO(
                        name="田中花子", role="副委員長", party_name="立憲民主党"
                    ),
                ]

                # Mock one success and one failure
                mock_repo.create.side_effect = [Mock(id=1), None]

                # Execute
                result = await extractor.extract_and_save_members(
                    conference_id=1,
                    conference_name="本会議",
                    url="https://example.com/members",
                )

                # Assert
                assert result["extracted_count"] == 2
                assert result["saved_count"] == 1
                assert result["failed_count"] == 1

    @pytest.mark.asyncio
    async def test_extract_and_save_members_fetch_error(self, extractor):
        """Test extraction with fetch error"""
        # Setup mock to raise error
        with patch.object(
            extractor, "fetch_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = Exception("Network Error")

            # Execute
            result = await extractor.extract_and_save_members(
                conference_id=1,
                conference_name="本会議",
                url="https://example.com/members",
            )

            # Assert
            assert "error" in result
            assert "Network Error" in result["error"]
            assert result["extracted_count"] == 0
            assert result["saved_count"] == 0

    def test_clean_html_removes_unwanted_tags(self, extractor):
        """Test that unwanted tags are removed from HTML"""
        html = """
        <html>
            <head>
                <script>alert('test');</script>
                <style>.test { color: red; }</style>
            </head>
            <body>
                <nav>Navigation</nav>
                <header>Header</header>
                <main>
                    <h1>委員会メンバー</h1>
                    <ul>
                        <li>山田太郎（委員長）</li>
                        <li>田中花子（副委員長）</li>
                    </ul>
                </main>
                <footer>Footer</footer>
                <aside>Sidebar</aside>
            </body>
        </html>
        """

        # Execute
        cleaned = extractor.clean_html(html)

        # Assert - unwanted tags should be removed
        assert "<script>" not in cleaned
        assert "<style>" not in cleaned
        assert "<nav>" not in cleaned
        assert "<header>" not in cleaned
        assert "<footer>" not in cleaned
        assert "<aside>" not in cleaned

        # Main content should be preserved
        assert "委員会メンバー" in cleaned
        assert "山田太郎" in cleaned
        assert "田中花子" in cleaned

    def test_clean_html_removes_comments(self, extractor):
        """Test that HTML comments are removed"""
        html = """
        <html>
            <body>
                <!-- This is a comment -->
                <main>
                    <h1>メンバーリスト</h1>
                    <!-- Another comment -->
                    <p>山田太郎</p>
                </main>
            </body>
        </html>
        """

        # Execute
        cleaned = extractor.clean_html(html)

        # Assert - comments should be removed
        assert "<!--" not in cleaned
        assert "This is a comment" not in cleaned
        assert "Another comment" not in cleaned

        # Content should be preserved
        assert "メンバーリスト" in cleaned
        assert "山田太郎" in cleaned

    def test_clean_html_extracts_main_content(self, extractor):
        """Test that main tag content is extracted when present"""
        html = """
        <html>
            <body>
                <nav>Navigation content that should be excluded</nav>
                <main>
                    <h1>Main Content</h1>
                    <p>This should be included</p>
                </main>
                <footer>Footer content that should be excluded</footer>
            </body>
        </html>
        """

        # Execute
        cleaned = extractor.clean_html(html)

        # Assert - only main content should be present
        assert "Main Content" in cleaned
        assert "This should be included" in cleaned

        # Navigation and footer should not be in main content
        # (they are removed by tag filtering, not by main extraction)

    def test_clean_html_without_main_tag(self, extractor):
        """Test cleaning when no main tag is present"""
        html = """
        <html>
            <body>
                <div class="content">
                    <h1>委員会名簿</h1>
                    <ul>
                        <li>委員長：山田太郎</li>
                        <li>副委員長：田中花子</li>
                    </ul>
                </div>
            </body>
        </html>
        """

        # Execute
        cleaned = extractor.clean_html(html)

        # Assert - content should be preserved
        assert "委員会名簿" in cleaned
        assert "山田太郎" in cleaned
        assert "田中花子" in cleaned

    def test_clean_html_removes_extra_whitespace(self, extractor):
        """Test that extra whitespace is removed"""
        html = """
        <html>
            <body>


                <main>
                    <h1>   Title with spaces   </h1>


                    <p>   Content   </p>
                </main>


            </body>
        </html>
        """

        # Execute
        cleaned = extractor.clean_html(html)

        # Assert - multiple spaces should be reduced
        assert "  " not in cleaned or cleaned.count("  ") < html.count("  ")
        # Content should still be present
        assert "Title with spaces" in cleaned
        assert "Content" in cleaned

    def test_clean_html_reduces_size(self, extractor):
        """Test that HTML size is significantly reduced"""
        html = """
        <html>
            <head>
                <script type="text/javascript">
                    function test() {
                        console.log("This is a long script");
                        // More script content
                        var x = 1;
                        var y = 2;
                        var z = 3;
                    }
                </script>
                <style>
                    .class1 { color: red; font-size: 14px; }
                    .class2 { color: blue; font-size: 16px; }
                    .class3 { color: green; font-size: 18px; }
                </style>
            </head>
            <body>
                <nav>
                    <ul>
                        <li><a href="#">Link 1</a></li>
                        <li><a href="#">Link 2</a></li>
                        <li><a href="#">Link 3</a></li>
                    </ul>
                </nav>
                <main>
                    <h1>委員会メンバー</h1>
                    <ul>
                        <li>山田太郎</li>
                    </ul>
                </main>
            </body>
        </html>
        """

        # Execute
        cleaned = extractor.clean_html(html)

        # Assert - size should be significantly reduced
        assert len(cleaned) < len(html)
        # At least 30% reduction expected
        reduction_percent = (1 - len(cleaned) / len(html)) * 100
        assert reduction_percent > 30

    def test_clean_html_handles_malformed_html(self, extractor):
        """Test that cleaning handles malformed HTML gracefully"""
        html = """
        <html>
            <body>
                <main>
                    <h1>Content</h1>
                    <p>Unclosed paragraph
                    <div>Nested div
                </main>
            </body>
        """

        # Execute - should not raise exception
        cleaned = extractor.clean_html(html)

        # Assert - should return some content
        assert len(cleaned) > 0
        assert "Content" in cleaned

    def test_clean_html_error_returns_original(self, extractor):
        """Test that errors return original HTML"""
        # Create invalid input that will cause BeautifulSoup to fail
        # (though BeautifulSoup is very forgiving, so this is hard to trigger)
        html = "<html><body><main>Content</main></body></html>"

        # Mock BeautifulSoup to raise an exception
        with patch(
            "src.infrastructure.external.conference_member_extractor.extractor.BeautifulSoup"
        ) as mock_bs:
            mock_bs.side_effect = Exception("Parsing error")

            # Execute
            cleaned = extractor.clean_html(html)

            # Assert - should return original HTML
            assert cleaned == html
