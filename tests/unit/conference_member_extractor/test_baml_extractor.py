"""Tests for BAML member extractor"""

from unittest.mock import AsyncMock, patch

import pytest

from src.infrastructure.external.conference_member_extractor.baml_extractor import (
    BAMLMemberExtractor,
)


class TestBAMLMemberExtractor:
    """Test cases for BAMLMemberExtractor"""

    @pytest.fixture
    def extractor(self):
        """Create a BAMLMemberExtractor instance"""
        return BAMLMemberExtractor()

    @pytest.mark.asyncio
    async def test_extract_members_success(self, extractor):
        """Test successful extraction with BAML"""

        # Mock BAML result
        class MockMember:
            def __init__(self, name, role, party_name, additional_info):
                self.name = name
                self.role = role
                self.party_name = party_name
                self.additional_info = additional_info

        mock_result = [
            MockMember("山田太郎", "委員長", "自民党", None),
            MockMember("田中花子", "副委員長", "立憲民主党", None),
            MockMember("佐藤次郎", "委員", "公明党", None),
        ]

        with patch(
            "src.infrastructure.external.conference_member_extractor.baml_extractor.b.ExtractMembers",
            new_callable=AsyncMock,
        ) as mock_baml:
            mock_baml.return_value = mock_result

            # Execute
            result = await extractor.extract_members("<html></html>", "本会議")

            # Assert
            assert len(result) == 3
            assert result[0].name == "山田太郎"
            assert result[0].role == "委員長"
            assert result[0].party_name == "自民党"
            assert result[1].name == "田中花子"
            assert result[2].name == "佐藤次郎"

            # Verify BAML was called with correct arguments
            mock_baml.assert_called_once_with("<html></html>", "本会議")

    @pytest.mark.asyncio
    async def test_extract_members_empty_result(self, extractor):
        """Test extraction with empty result"""
        with patch(
            "src.infrastructure.external.conference_member_extractor.baml_extractor.b.ExtractMembers",
            new_callable=AsyncMock,
        ) as mock_baml:
            mock_baml.return_value = []

            # Execute
            result = await extractor.extract_members("<html></html>", "本会議")

            # Assert
            assert result == []

    @pytest.mark.asyncio
    async def test_extract_members_error_handling(self, extractor):
        """Test error handling in BAML extraction"""
        with patch(
            "src.infrastructure.external.conference_member_extractor.baml_extractor.b.ExtractMembers",
            new_callable=AsyncMock,
        ) as mock_baml:
            mock_baml.side_effect = Exception("BAML error")

            # Execute
            result = await extractor.extract_members("<html></html>", "本会議")

            # Assert - should return empty list on error
            assert result == []

    @pytest.mark.asyncio
    async def test_extract_members_truncates_long_html(self, extractor, caplog):
        """Test that long HTML content is truncated"""
        # Create very long HTML content
        long_html = "x" * 60000  # More than 50000 chars

        class MockMember:
            def __init__(self, name, role, party_name, additional_info):
                self.name = name
                self.role = role
                self.party_name = party_name
                self.additional_info = additional_info

        with patch(
            "src.infrastructure.external.conference_member_extractor.baml_extractor.b.ExtractMembers",
            new_callable=AsyncMock,
        ) as mock_baml:
            mock_baml.return_value = [MockMember("山田太郎", "委員", None, None)]

            # Execute
            await extractor.extract_members(long_html, "本会議")

            # Assert - should log warning about truncation
            assert "HTML content too long" in caplog.text
            assert "truncating to 50000 chars" in caplog.text

            # Assert - BAML should be called with truncated HTML
            call_args = mock_baml.call_args[0]
            assert len(call_args[0]) <= 50003  # 50000 + "..."
            assert call_args[0].endswith("...")

    @pytest.mark.asyncio
    async def test_extract_members_with_optional_fields(self, extractor):
        """Test extraction with members having optional fields"""

        class MockMember:
            def __init__(self, name, role, party_name, additional_info):
                self.name = name
                self.role = role
                self.party_name = party_name
                self.additional_info = additional_info

        # Member with no role or party
        mock_result = [
            MockMember("山田太郎", None, None, "備考あり"),
            MockMember("田中花子", "委員長", None, None),
        ]

        with patch(
            "src.infrastructure.external.conference_member_extractor.baml_extractor.b.ExtractMembers",
            new_callable=AsyncMock,
        ) as mock_baml:
            mock_baml.return_value = mock_result

            # Execute
            result = await extractor.extract_members("<html></html>", "委員会")

            # Assert
            assert len(result) == 2
            assert result[0].name == "山田太郎"
            assert result[0].role is None
            assert result[0].party_name is None
            assert result[0].additional_info == "備考あり"
            assert result[1].name == "田中花子"
            assert result[1].role == "委員長"
