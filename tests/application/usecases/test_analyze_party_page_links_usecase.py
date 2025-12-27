"""Tests for AnalyzePartyPageLinksUseCase."""

from unittest.mock import AsyncMock, Mock

import pytest

from src.application.dtos.link_analysis_dto import AnalyzeLinksInputDTO
from src.application.usecases.analyze_party_page_links_usecase import (
    AnalyzePartyPageLinksUseCase,
)
from src.domain.services.interfaces.llm_link_classifier_service import (
    LinkClassification,
    LinkClassificationResult,
    LinkType,
)
from src.domain.services.link_analysis_domain_service import LinkAnalysisDomainService
from src.domain.value_objects.link import Link


class TestAnalyzePartyPageLinksUseCase:
    """Test cases for AnalyzePartyPageLinksUseCase."""

    @pytest.fixture
    def mock_html_extractor(self):
        """Create mock HTML link extractor service."""
        return Mock()

    @pytest.fixture
    def mock_link_classifier(self):
        """Create mock LLM link classifier service."""
        mock = Mock()
        mock.classify_links = AsyncMock()
        return mock

    @pytest.fixture
    def link_analysis_service(self):
        """Create real LinkAnalysisDomainService."""
        return LinkAnalysisDomainService()

    @pytest.fixture
    def use_case(
        self, mock_html_extractor, mock_link_classifier, link_analysis_service
    ):
        """Create AnalyzePartyPageLinksUseCase instance."""
        return AnalyzePartyPageLinksUseCase(
            html_extractor=mock_html_extractor,
            link_classifier=mock_link_classifier,
            link_analysis_service=link_analysis_service,
        )

    @pytest.mark.asyncio
    async def test_include_prefecture_list_in_member_list_urls(
        self, use_case, mock_html_extractor, mock_link_classifier
    ):
        """Prefecture list links should be included in member_list_urls."""
        # Arrange
        mock_html_extractor.extract_links.return_value = [
            Link(url="https://jcp.or.jp/list/pref/1", text="北海道"),
            Link(url="https://jcp.or.jp/other", text="その他"),
        ]

        mock_link_classifier.classify_links.return_value = LinkClassificationResult(
            classifications=[
                LinkClassification(
                    url="https://jcp.or.jp/list/pref/1",
                    link_type=LinkType.PREFECTURE_LIST,
                    confidence=0.9,
                    reason="Prefecture page",
                ),
            ],
            summary={"prefecture_list": 1},
        )

        # Act
        input_dto = AnalyzeLinksInputDTO(
            html_content="<html>...</html>",
            current_url="https://jcp.or.jp/giin/",
            party_name="日本共産党",
            context="Test",
        )
        result = await use_case.execute(input_dto)

        # Assert
        assert "https://jcp.or.jp/list/pref/1" in result.member_list_urls
        assert len(result.member_list_urls) == 1

    @pytest.mark.asyncio
    async def test_include_city_list_in_member_list_urls(
        self, use_case, mock_html_extractor, mock_link_classifier
    ):
        """City list links should be included in member_list_urls."""
        # Arrange
        mock_html_extractor.extract_links.return_value = [
            Link(url="https://jcp.or.jp/list/city/tokyo/1", text="千代田区"),
            Link(url="https://jcp.or.jp/other", text="その他"),
        ]

        mock_link_classifier.classify_links.return_value = LinkClassificationResult(
            classifications=[
                LinkClassification(
                    url="https://jcp.or.jp/list/city/tokyo/1",
                    link_type=LinkType.CITY_LIST,
                    confidence=0.85,
                    reason="City page",
                ),
            ],
            summary={"city_list": 1},
        )

        # Act
        input_dto = AnalyzeLinksInputDTO(
            html_content="<html>...</html>",
            current_url="https://jcp.or.jp/giin/",
            party_name="日本共産党",
            context="Test",
        )
        result = await use_case.execute(input_dto)

        # Assert
        assert "https://jcp.or.jp/list/city/tokyo/1" in result.member_list_urls
        assert len(result.member_list_urls) == 1

    @pytest.mark.asyncio
    async def test_include_member_list_in_member_list_urls(
        self, use_case, mock_html_extractor, mock_link_classifier
    ):
        """Member list links should be included in member_list_urls."""
        # Arrange
        mock_html_extractor.extract_links.return_value = [
            Link(url="https://jcp.or.jp/members", text="議員一覧"),
            Link(url="https://jcp.or.jp/other", text="その他"),
        ]

        mock_link_classifier.classify_links.return_value = LinkClassificationResult(
            classifications=[
                LinkClassification(
                    url="https://jcp.or.jp/members",
                    link_type=LinkType.MEMBER_LIST,
                    confidence=0.95,
                    reason="Member list page",
                ),
            ],
            summary={"member_list": 1},
        )

        # Act
        input_dto = AnalyzeLinksInputDTO(
            html_content="<html>...</html>",
            current_url="https://jcp.or.jp/giin/",
            party_name="日本共産党",
            context="Test",
        )
        result = await use_case.execute(input_dto)

        # Assert
        assert "https://jcp.or.jp/members" in result.member_list_urls
        assert len(result.member_list_urls) == 1

    @pytest.mark.asyncio
    async def test_filter_low_confidence_links(
        self, use_case, mock_html_extractor, mock_link_classifier
    ):
        """Links with confidence < 0.7 should be filtered out."""
        # Arrange
        mock_html_extractor.extract_links.return_value = [
            Link(url="https://jcp.or.jp/maybe-members", text="議員？"),
            Link(url="https://jcp.or.jp/other", text="その他"),
        ]

        mock_link_classifier.classify_links.return_value = LinkClassificationResult(
            classifications=[
                LinkClassification(
                    url="https://jcp.or.jp/maybe-members",
                    link_type=LinkType.MEMBER_LIST,
                    confidence=0.6,  # Below threshold
                    reason="Uncertain member list",
                ),
            ],
            summary={"member_list": 1},
        )

        # Act
        input_dto = AnalyzeLinksInputDTO(
            html_content="<html>...</html>",
            current_url="https://jcp.or.jp/giin/",
            party_name="日本共産党",
            context="Test",
        )
        result = await use_case.execute(input_dto)

        # Assert
        assert len(result.member_list_urls) == 0

    @pytest.mark.asyncio
    async def test_hierarchical_types_combination(
        self, use_case, mock_html_extractor, mock_link_classifier
    ):
        """All hierarchical link types should be combined in member_list_urls."""
        # Arrange
        mock_html_extractor.extract_links.return_value = [
            Link(url="https://jcp.or.jp/list/pref/1", text="北海道"),
            Link(url="https://jcp.or.jp/list/city/tokyo/1", text="千代田区"),
            Link(url="https://jcp.or.jp/members", text="議員一覧"),
            Link(url="https://jcp.or.jp/profile/123", text="山田太郎"),
            Link(url="https://jcp.or.jp/other", text="その他"),
        ]

        mock_link_classifier.classify_links.return_value = LinkClassificationResult(
            classifications=[
                LinkClassification(
                    url="https://jcp.or.jp/list/pref/1",
                    link_type=LinkType.PREFECTURE_LIST,
                    confidence=0.9,
                    reason="Prefecture page",
                ),
                LinkClassification(
                    url="https://jcp.or.jp/list/city/tokyo/1",
                    link_type=LinkType.CITY_LIST,
                    confidence=0.85,
                    reason="City page",
                ),
                LinkClassification(
                    url="https://jcp.or.jp/members",
                    link_type=LinkType.MEMBER_LIST,
                    confidence=0.95,
                    reason="Member list page",
                ),
                LinkClassification(
                    url="https://jcp.or.jp/profile/123",
                    link_type=LinkType.MEMBER_PROFILE,
                    confidence=0.9,
                    reason="Member profile",
                ),
                LinkClassification(
                    url="https://jcp.or.jp/other",
                    link_type=LinkType.OTHER,
                    confidence=0.8,
                    reason="Other page",
                ),
            ],
            summary={
                "prefecture_list": 1,
                "city_list": 1,
                "member_list": 1,
                "member_profile": 1,
                "other": 1,
            },
        )

        # Act
        input_dto = AnalyzeLinksInputDTO(
            html_content="<html>...</html>",
            current_url="https://jcp.or.jp/giin/",
            party_name="日本共産党",
            context="Test",
        )
        result = await use_case.execute(input_dto)

        # Assert
        assert len(result.member_list_urls) == 3  # Prefecture, City, Member list
        assert "https://jcp.or.jp/list/pref/1" in result.member_list_urls
        assert "https://jcp.or.jp/list/city/tokyo/1" in result.member_list_urls
        assert "https://jcp.or.jp/members" in result.member_list_urls
        assert "https://jcp.or.jp/profile/123" not in result.member_list_urls
        assert len(result.profile_urls) == 1
        assert "https://jcp.or.jp/profile/123" in result.profile_urls

    @pytest.mark.asyncio
    async def test_empty_html_content_raises_error(self, use_case):
        """Empty HTML content should raise ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="HTML content cannot be empty"):
            await use_case.execute(
                AnalyzeLinksInputDTO(
                    html_content="",
                    current_url="https://jcp.or.jp/giin/",
                    party_name="日本共産党",
                    context="Test",
                )
            )

    @pytest.mark.asyncio
    async def test_empty_current_url_raises_error(self, use_case):
        """Empty current URL should raise ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="Current URL cannot be empty"):
            await use_case.execute(
                AnalyzeLinksInputDTO(
                    html_content="<html>...</html>",
                    current_url="",
                    party_name="日本共産党",
                    context="Test",
                )
            )

    @pytest.mark.asyncio
    async def test_no_links_extracted(
        self, use_case, mock_html_extractor, mock_link_classifier
    ):
        """Should handle case with no links extracted."""
        # Arrange
        mock_html_extractor.extract_links.return_value = []

        # Act
        input_dto = AnalyzeLinksInputDTO(
            html_content="<html><body>No links</body></html>",
            current_url="https://jcp.or.jp/giin/",
            party_name="日本共産党",
            context="Test",
        )
        result = await use_case.execute(input_dto)

        # Assert
        assert result.all_links_count == 0
        assert result.child_links_count == 0
        assert len(result.member_list_urls) == 0
        assert len(result.profile_urls) == 0
        # LLM classifier should not be called when there are no links
        mock_link_classifier.classify_links.assert_not_called()

    @pytest.mark.asyncio
    async def test_profile_urls_separated_from_member_list_urls(
        self, use_case, mock_html_extractor, mock_link_classifier
    ):
        """Profile URLs should be in profile_urls, not member_list_urls."""
        # Arrange
        # Profile URLs should be child pages to be classified
        mock_html_extractor.extract_links.return_value = [
            Link(url="https://jcp.or.jp/giin/profile/123", text="山田太郎"),
            Link(url="https://jcp.or.jp/giin/profile/456", text="鈴木花子"),
        ]

        mock_link_classifier.classify_links.return_value = LinkClassificationResult(
            classifications=[
                LinkClassification(
                    url="https://jcp.or.jp/giin/profile/123",
                    link_type=LinkType.MEMBER_PROFILE,
                    confidence=0.9,
                    reason="Member profile",
                ),
                LinkClassification(
                    url="https://jcp.or.jp/giin/profile/456",
                    link_type=LinkType.MEMBER_PROFILE,
                    confidence=0.85,
                    reason="Member profile",
                ),
            ],
            summary={"member_profile": 2},
        )

        # Act
        input_dto = AnalyzeLinksInputDTO(
            html_content="<html>...</html>",
            current_url="https://jcp.or.jp/giin/",
            party_name="日本共産党",
            context="Test",
        )
        result = await use_case.execute(input_dto)

        # Assert
        assert len(result.member_list_urls) == 0
        assert len(result.profile_urls) == 2
        assert "https://jcp.or.jp/giin/profile/123" in result.profile_urls
        assert "https://jcp.or.jp/giin/profile/456" in result.profile_urls
