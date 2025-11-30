"""Tests for BAML parliamentary group member extractor"""

from unittest.mock import AsyncMock, patch

import pytest

from src.infrastructure.external.parliamentary_group_member_extractor.baml_extractor import (  # noqa: E501
    BAMLParliamentaryGroupMemberExtractor,
)


class TestBAMLParliamentaryGroupMemberExtractor:
    """Test cases for BAMLParliamentaryGroupMemberExtractor"""

    @pytest.fixture
    def extractor(self):
        """Create a BAMLParliamentaryGroupMemberExtractor instance"""
        return BAMLParliamentaryGroupMemberExtractor()

    @pytest.mark.asyncio
    async def test_extract_members_success(self, extractor):
        """Test successful extraction with BAML"""

        # Mock BAML result
        class MockMember:
            def __init__(self, name, role, party_name, district, additional_info):
                self.name = name
                self.role = role
                self.party_name = party_name
                self.district = district
                self.additional_info = additional_info

        mock_result = [
            MockMember("山田太郎", "団長", "自民党", "東京都第1区", None),
            MockMember("田中花子", "副団長", "立憲民主党", "神奈川県第2区", None),
            MockMember("佐藤次郎", "幹事長", "公明党", None, "備考あり"),
        ]

        mock_html = "<html><body>議員一覧</body></html>"

        with patch.object(extractor, "_fetch_html", return_value=mock_html):
            with patch(
                "src.infrastructure.external.parliamentary_group_member_extractor.baml_extractor.b.ExtractParliamentaryGroupMembers",
                create=True,
                new_callable=AsyncMock,
            ) as mock_baml:
                mock_baml.return_value = mock_result

                # Execute
                result = await extractor.extract_members(
                    1, "https://example.com/members"
                )

                # Assert
                assert result.parliamentary_group_id == 1
                assert result.url == "https://example.com/members"
                assert len(result.extracted_members) == 3
                assert result.extracted_members[0].name == "山田太郎"
                assert result.extracted_members[0].role == "団長"
                assert result.extracted_members[0].party_name == "自民党"
                assert result.extracted_members[0].district == "東京都第1区"
                assert result.extracted_members[1].name == "田中花子"
                assert result.extracted_members[2].name == "佐藤次郎"
                assert result.error is None
                assert result.extraction_date is not None

                # Verify BAML was called
                mock_baml.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_members_empty_result(self, extractor):
        """Test extraction with empty BAML result"""
        mock_html = "<html><body>空のページ</body></html>"

        with patch.object(extractor, "_fetch_html", return_value=mock_html):
            with patch(
                "src.infrastructure.external.parliamentary_group_member_extractor.baml_extractor.b.ExtractParliamentaryGroupMembers",
                create=True,
                new_callable=AsyncMock,
            ) as mock_baml:
                mock_baml.return_value = []

                # Execute
                result = await extractor.extract_members(
                    1, "https://example.com/members"
                )

                # Assert
                assert result.parliamentary_group_id == 1
                assert result.extracted_members == []
                assert result.error is None

    @pytest.mark.asyncio
    async def test_extract_members_error_handling(self, extractor):
        """Test error handling in BAML extraction"""
        mock_html = "<html><body>議員一覧</body></html>"

        with patch.object(extractor, "_fetch_html", return_value=mock_html):
            with patch(
                "src.infrastructure.external.parliamentary_group_member_extractor.baml_extractor.b.ExtractParliamentaryGroupMembers",
                create=True,
                new_callable=AsyncMock,
            ) as mock_baml:
                mock_baml.side_effect = Exception("BAML error")

                # Execute
                result = await extractor.extract_members(
                    1, "https://example.com/members"
                )

                # Assert - internal error is caught, returns empty list with no error
                # (error is logged but not returned in DTO)
                assert result.parliamentary_group_id == 1
                assert result.extracted_members == []
                assert (
                    result.error is None
                )  # Internal errors don't propagate to error field

    @pytest.mark.asyncio
    async def test_extract_members_truncates_long_content(self, extractor, caplog):
        """Test that long HTML/text content is truncated"""
        # Create very long HTML content
        long_html = "<html>" + ("x" * 15000) + "</html>"

        class MockMember:
            def __init__(self, name, role, party_name, district, additional_info):
                self.name = name
                self.role = role
                self.party_name = party_name
                self.district = district
                self.additional_info = additional_info

        with patch.object(extractor, "_fetch_html", return_value=long_html):
            with patch(
                "src.infrastructure.external.parliamentary_group_member_extractor.baml_extractor.b.ExtractParliamentaryGroupMembers",
                create=True,
                new_callable=AsyncMock,
            ) as mock_baml:
                mock_baml.return_value = [
                    MockMember("山田太郎", "団長", None, None, None)
                ]

                # Execute
                await extractor.extract_members(1, "https://example.com/members")

                # Assert - should log warning about truncation
                assert "HTML content too long" in caplog.text
                assert "truncating to 10000 chars" in caplog.text

                # Assert - BAML should be called with truncated HTML
                call_args = mock_baml.call_args[0]
                assert len(call_args[0]) <= 10000

    @pytest.mark.asyncio
    async def test_extract_members_with_optional_fields(self, extractor):
        """Test extraction with members having optional fields"""

        class MockMember:
            def __init__(self, name, role, party_name, district, additional_info):
                self.name = name
                self.role = role
                self.party_name = party_name
                self.district = district
                self.additional_info = additional_info

        # Members with various optional field combinations
        mock_result = [
            MockMember("山田太郎", None, None, None, "備考あり"),
            MockMember("田中花子", "団長", None, "東京都第1区", None),
            MockMember("佐藤次郎", "副団長", "自民党", None, None),
        ]

        mock_html = "<html><body>議員一覧</body></html>"

        with patch.object(extractor, "_fetch_html", return_value=mock_html):
            with patch(
                "src.infrastructure.external.parliamentary_group_member_extractor.baml_extractor.b.ExtractParliamentaryGroupMembers",
                create=True,
                new_callable=AsyncMock,
            ) as mock_baml:
                mock_baml.return_value = mock_result

                # Execute
                result = await extractor.extract_members(
                    1, "https://example.com/members"
                )

                # Assert
                assert len(result.extracted_members) == 3
                assert result.extracted_members[0].name == "山田太郎"
                assert result.extracted_members[0].role is None
                assert result.extracted_members[0].party_name is None
                assert result.extracted_members[0].district is None
                assert result.extracted_members[0].additional_info == "備考あり"

                assert result.extracted_members[1].name == "田中花子"
                assert result.extracted_members[1].role == "団長"
                assert result.extracted_members[1].district == "東京都第1区"

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
    async def test_extract_members_converts_baml_to_dto(self, extractor):
        """Test conversion from BAML results to DTOs"""

        class MockMember:
            def __init__(self, name, role, party_name, district, additional_info):
                self.name = name
                self.role = role
                self.party_name = party_name
                self.district = district
                self.additional_info = additional_info

        mock_result = [
            MockMember("山田太郎", "団長", "自民党", "東京都第1区", "重要人物"),
        ]

        mock_html = "<html><body>議員一覧</body></html>"

        with patch.object(extractor, "_fetch_html", return_value=mock_html):
            with patch(
                "src.infrastructure.external.parliamentary_group_member_extractor.baml_extractor.b.ExtractParliamentaryGroupMembers",
                create=True,
                new_callable=AsyncMock,
            ) as mock_baml:
                mock_baml.return_value = mock_result

                result = await extractor.extract_members(
                    1, "https://example.com/members"
                )

                # Verify DTO fields are correctly mapped
                member = result.extracted_members[0]
                assert member.name == "山田太郎"
                assert member.role == "団長"
                assert member.party_name == "自民党"
                assert member.district == "東京都第1区"
                assert member.additional_info == "重要人物"

    @pytest.mark.asyncio
    async def test_extract_members_handles_district_field(self, extractor):
        """Test district field handling (unique to Parliamentary Group)"""

        class MockMember:
            def __init__(self, name, role, party_name, district, additional_info):
                self.name = name
                self.role = role
                self.party_name = party_name
                self.district = district
                self.additional_info = additional_info

        mock_result = [
            MockMember("山田太郎", "団長", "自民党", "比例代表", None),
            MockMember("田中花子", "副団長", "立憲民主党", "東京都第5区", None),
        ]

        mock_html = "<html><body>議員一覧</body></html>"

        with patch.object(extractor, "_fetch_html", return_value=mock_html):
            with patch(
                "src.infrastructure.external.parliamentary_group_member_extractor.baml_extractor.b.ExtractParliamentaryGroupMembers",
                create=True,
                new_callable=AsyncMock,
            ) as mock_baml:
                mock_baml.return_value = mock_result

                result = await extractor.extract_members(
                    1, "https://example.com/members"
                )

                # Verify district field
                assert result.extracted_members[0].district == "比例代表"
                assert result.extracted_members[1].district == "東京都第5区"

    @pytest.mark.asyncio
    async def test_extract_members_with_baml_internal_error_returns_empty(
        self, extractor
    ):
        """Test that _extract_members_with_baml returns empty list on error"""
        with patch(
            "src.infrastructure.external.parliamentary_group_member_extractor.baml_extractor.b.ExtractParliamentaryGroupMembers",
            create=True,
            new_callable=AsyncMock,
        ) as mock_baml:
            mock_baml.side_effect = Exception("BAML internal error")

            # Call the private method directly
            result = await extractor._extract_members_with_baml(
                "テキストコンテンツ", "<html>HTMLコンテンツ</html>"
            )

            # Should return empty list on error
            assert result == []

    @pytest.mark.asyncio
    async def test_extract_members_truncates_text_content(self, extractor, caplog):
        """Test that long text content is also truncated"""
        # Create normal HTML but very long text
        mock_html = "<html><body>議員一覧</body></html>"

        class MockMember:
            def __init__(self, name, role, party_name, district, additional_info):
                self.name = name
                self.role = role
                self.party_name = party_name
                self.district = district
                self.additional_info = additional_info

        # We need to test the internal method to check text truncation
        long_text = "議員名簿\n" + (
            "議員氏名\n" * 3000
        )  # Make it longer than 5000 chars

        with patch(
            "src.infrastructure.external.parliamentary_group_member_extractor.baml_extractor.b.ExtractParliamentaryGroupMembers",
            create=True,
            new_callable=AsyncMock,
        ) as mock_baml:
            mock_baml.return_value = [MockMember("山田太郎", "団長", None, None, None)]

            # Call internal method
            await extractor._extract_members_with_baml(long_text, mock_html)

            # Check that text was truncated
            call_args = mock_baml.call_args[0]
            # Second argument is text_content
            assert len(call_args[1]) <= 5000
