"""Tests for Pydantic parliamentary group member extractor"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.dtos.parliamentary_group_member_dto import (
    ExtractedParliamentaryGroupMemberDTO,
)
from src.infrastructure.external.parliamentary_group_member_extractor.pydantic_extractor import (  # noqa: E501
    PydanticParliamentaryGroupMemberExtractor,
)
from src.parliamentary_group_member_extractor.models import (
    ExtractedMember,
    ExtractedMemberList,
)


class TestPydanticParliamentaryGroupMemberExtractor:
    """Test cases for PydanticParliamentaryGroupMemberExtractor"""

    @pytest.fixture
    def extractor(self):
        """Create a PydanticParliamentaryGroupMemberExtractor instance"""
        return PydanticParliamentaryGroupMemberExtractor()

    @pytest.fixture
    def mock_llm_service(self):
        """Create a mock LLM service"""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_extract_members_success(self, extractor):
        """Test successful member extraction"""
        # Mock HTML fetch
        mock_html = "<html><body>議員一覧</body></html>"

        # Mock LLM extraction result
        mock_members = [
            ExtractedMember(
                name="山田太郎",
                role="団長",
                party_name="自民党",
                district="東京都第1区",
            ),
            ExtractedMember(name="田中花子", role="副団長", party_name="立憲民主党"),
        ]

        with patch.object(
            extractor, "_fetch_html", return_value=mock_html
        ) as mock_fetch:
            with patch.object(
                extractor, "_extract_members_with_llm", return_value=mock_members
            ) as mock_extract:
                result = await extractor.extract_members(
                    1, "https://example.com/members"
                )

                # Assert
                assert result.parliamentary_group_id == 1
                assert result.url == "https://example.com/members"
                assert len(result.extracted_members) == 2
                assert result.extracted_members[0].name == "山田太郎"
                assert result.extracted_members[0].role == "団長"
                assert result.extracted_members[1].name == "田中花子"
                assert result.error is None
                assert result.extraction_date is not None

                # Verify calls
                mock_fetch.assert_called_once_with("https://example.com/members")
                mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_members_fetch_html_returns_none(self, extractor):
        """Test when HTML fetch returns None"""
        with patch.object(extractor, "_fetch_html", return_value=None):
            result = await extractor.extract_members(1, "https://example.com/members")

            # Assert error result
            assert result.parliamentary_group_id == 1
            assert result.url == "https://example.com/members"
            assert result.extracted_members == []
            assert result.error is not None
            assert "URLからコンテンツを取得できませんでした" in result.error

    @pytest.mark.asyncio
    async def test_extract_members_fetch_html_raises_exception(self, extractor):
        """Test when HTML fetch raises an exception"""
        with patch.object(
            extractor, "_fetch_html", side_effect=Exception("Network error")
        ):
            result = await extractor.extract_members(1, "https://example.com/members")

            # Assert error result
            assert result.parliamentary_group_id == 1
            assert result.extracted_members == []
            assert result.error == "Network error"

    @pytest.mark.asyncio
    async def test_extract_members_playwright_error_message(self, extractor):
        """Test Playwright-specific error message"""
        with patch.object(
            extractor,
            "_fetch_html",
            side_effect=Exception("playwright installation required"),
        ):
            result = await extractor.extract_members(1, "https://example.com/members")

            # Assert error contains playwright-related info
            assert result.error is not None
            assert "playwright" in result.error.lower()

    @pytest.mark.asyncio
    async def test_extract_members_llm_returns_empty_list(self, extractor):
        """Test when LLM extraction returns empty list"""
        mock_html = "<html><body>空のページ</body></html>"

        with patch.object(extractor, "_fetch_html", return_value=mock_html):
            with patch.object(extractor, "_extract_members_with_llm", return_value=[]):
                result = await extractor.extract_members(
                    1, "https://example.com/members"
                )

                # Assert successful but empty result
                assert result.parliamentary_group_id == 1
                assert result.extracted_members == []
                assert result.error is None

    @pytest.mark.asyncio
    async def test_extract_members_llm_raises_exception(self, extractor):
        """Test when LLM extraction raises an exception"""
        mock_html = "<html><body>議員一覧</body></html>"

        with patch.object(extractor, "_fetch_html", return_value=mock_html):
            with patch.object(
                extractor,
                "_extract_members_with_llm",
                side_effect=Exception("LLM error"),
            ):
                result = await extractor.extract_members(
                    1, "https://example.com/members"
                )

                # Assert error result
                assert result.extracted_members == []
                assert result.error == "LLM error"

    @pytest.mark.asyncio
    async def test_extract_members_truncates_long_content(self, extractor):
        """Test that long HTML/text content is truncated"""
        # Create very long HTML
        long_html = "<html>" + ("x" * 20000) + "</html>"

        mock_members = [ExtractedMember(name="山田太郎")]

        # Mock structured LLM
        mock_structured_llm = AsyncMock()
        mock_structured_llm.ainvoke = AsyncMock(
            return_value=ExtractedMemberList(members=mock_members)
        )

        mock_llm_service = MagicMock()
        mock_llm_service.get_structured_llm = MagicMock(
            return_value=mock_structured_llm
        )

        extractor_with_mock = PydanticParliamentaryGroupMemberExtractor(
            llm_service=mock_llm_service
        )

        with patch.object(extractor_with_mock, "_fetch_html", return_value=long_html):
            await extractor_with_mock.extract_members(1, "https://example.com/members")

            # Assert truncation happened
            call_args = mock_structured_llm.ainvoke.call_args
            formatted_prompt = call_args[0][0]

            # Check that HTML was truncated to 10000 chars
            # (exact assertion depends on prompt format)
            assert len(formatted_prompt) < len(long_html)

    @pytest.mark.asyncio
    async def test_extract_members_calls_llm_service_correctly(self, mock_llm_service):
        """Test that LLM service is called with correct parameters"""
        mock_html = "<html><body>議員一覧</body></html>"
        mock_members = [ExtractedMember(name="山田太郎", role="団長")]

        # Setup mock
        mock_structured_llm = AsyncMock()
        mock_structured_llm.ainvoke = AsyncMock(
            return_value=ExtractedMemberList(members=mock_members)
        )
        mock_llm_service.get_structured_llm = MagicMock(
            return_value=mock_structured_llm
        )

        extractor = PydanticParliamentaryGroupMemberExtractor(
            llm_service=mock_llm_service
        )

        with patch.object(extractor, "_fetch_html", return_value=mock_html):
            result = await extractor.extract_members(1, "https://example.com/members")

            # Verify LLM service was called
            mock_llm_service.get_structured_llm.assert_called_once_with(
                ExtractedMemberList
            )
            mock_structured_llm.ainvoke.assert_called_once()

            # Verify result
            assert len(result.extracted_members) == 1
            assert result.extracted_members[0].name == "山田太郎"

    @pytest.mark.asyncio
    async def test_extract_members_converts_pydantic_to_dto(self, extractor):
        """Test conversion from Pydantic models to DTOs"""
        mock_html = "<html><body>議員一覧</body></html>"

        # Pydantic models
        mock_members = [
            ExtractedMember(
                name="山田太郎",
                role="団長",
                party_name="自民党",
                district="東京都第1区",
                additional_info="備考",
            ),
        ]

        with patch.object(extractor, "_fetch_html", return_value=mock_html):
            with patch.object(
                extractor, "_extract_members_with_llm", return_value=mock_members
            ):
                result = await extractor.extract_members(
                    1, "https://example.com/members"
                )

                # Verify DTO conversion
                assert isinstance(
                    result.extracted_members[0], ExtractedParliamentaryGroupMemberDTO
                )
                assert result.extracted_members[0].name == "山田太郎"
                assert result.extracted_members[0].role == "団長"
                assert result.extracted_members[0].party_name == "自民党"
                assert result.extracted_members[0].district == "東京都第1区"
                assert result.extracted_members[0].additional_info == "備考"

    @pytest.mark.asyncio
    async def test_extract_members_handles_optional_fields(self, extractor):
        """Test handling of optional fields in conversion"""
        mock_html = "<html><body>議員一覧</body></html>"

        # Member with only required field
        mock_members = [
            ExtractedMember(name="山田太郎"),
            ExtractedMember(name="田中花子", role="副団長"),
        ]

        with patch.object(extractor, "_fetch_html", return_value=mock_html):
            with patch.object(
                extractor, "_extract_members_with_llm", return_value=mock_members
            ):
                result = await extractor.extract_members(
                    1, "https://example.com/members"
                )

                # Verify optional fields are None
                assert result.extracted_members[0].role is None
                assert result.extracted_members[0].party_name is None
                assert result.extracted_members[0].district is None
                assert result.extracted_members[0].additional_info is None

                # Second member has role
                assert result.extracted_members[1].role == "副団長"

    @pytest.mark.asyncio
    async def test_extract_members_with_llm_error_returns_empty_list(
        self, mock_llm_service
    ):
        """Test that _extract_members_with_llm returns empty list on error"""
        # Setup mock to raise exception
        mock_structured_llm = AsyncMock()
        mock_structured_llm.ainvoke = AsyncMock(side_effect=Exception("LLM API error"))
        mock_llm_service.get_structured_llm = MagicMock(
            return_value=mock_structured_llm
        )

        extractor = PydanticParliamentaryGroupMemberExtractor(
            llm_service=mock_llm_service
        )

        # Call the private method directly
        result = await extractor._extract_members_with_llm(
            "テキストコンテンツ", "<html>HTMLコンテンツ</html>"
        )

        # Should return empty list on error
        assert result == []

    @pytest.mark.asyncio
    async def test_extract_members_with_llm_handles_non_extractedmemberlist_result(
        self, mock_llm_service
    ):
        """Test handling when LLM returns unexpected type"""
        # Setup mock to return wrong type
        mock_structured_llm = AsyncMock()
        mock_structured_llm.ainvoke = AsyncMock(return_value="unexpected string")
        mock_llm_service.get_structured_llm = MagicMock(
            return_value=mock_structured_llm
        )

        extractor = PydanticParliamentaryGroupMemberExtractor(
            llm_service=mock_llm_service
        )

        # Call the private method
        result = await extractor._extract_members_with_llm(
            "テキストコンテンツ", "<html>HTMLコンテンツ</html>"
        )

        # Should return empty list for unexpected type
        assert result == []
