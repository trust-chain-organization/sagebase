"""Tests for ABTestMemberExtractor"""

from unittest.mock import AsyncMock, patch

import pytest

from src.infrastructure.external.conference_member_extractor.ab_test_extractor import (
    ABTestMemberExtractor,
)


class TestABTestMemberExtractor:
    """Test cases for ABTestMemberExtractor"""

    @pytest.fixture
    def extractor(self):
        """Create an ABTestMemberExtractor instance"""
        return ABTestMemberExtractor()

    @pytest.mark.asyncio
    async def test_both_implementations_executed(self, extractor):
        """両方の実装が実行されることを確認"""
        # Mock両実装
        pydantic_result = [
            {
                "name": "山田太郎",
                "role": "委員長",
                "party_name": "自民党",
                "additional_info": None,
            }
        ]
        baml_result = [
            {
                "name": "山田太郎",
                "role": "委員長",
                "party_name": "自民党",
                "additional_info": None,
            }
        ]

        with patch.object(
            extractor.pydantic_extractor, "extract_members", new_callable=AsyncMock
        ) as mock_pydantic:
            with patch.object(
                extractor.baml_extractor, "extract_members", new_callable=AsyncMock
            ) as mock_baml:
                mock_pydantic.return_value = pydantic_result
                mock_baml.return_value = baml_result

                # Execute
                result = await extractor.extract_members("<html></html>", "本会議")

                # Assert - 両方が呼ばれた
                mock_pydantic.assert_called_once_with("<html></html>", "本会議")
                mock_baml.assert_called_once_with("<html></html>", "本会議")

                # Pydantic結果を返す（デフォルト）
                assert result == pydantic_result

    @pytest.mark.asyncio
    async def test_returns_pydantic_result_by_default(self, extractor):
        """デフォルトでPydantic結果を返すことを確認"""
        pydantic_result = [
            {
                "name": "山田太郎",
                "role": "委員長",
                "party_name": "自民党",
                "additional_info": None,
            }
        ]
        baml_result = [
            {
                "name": "田中花子",
                "role": "委員",
                "party_name": "公明党",
                "additional_info": None,
            }
        ]

        with patch.object(
            extractor.pydantic_extractor, "extract_members", new_callable=AsyncMock
        ) as mock_pydantic:
            with patch.object(
                extractor.baml_extractor, "extract_members", new_callable=AsyncMock
            ) as mock_baml:
                mock_pydantic.return_value = pydantic_result
                mock_baml.return_value = baml_result

                # Execute
                result = await extractor.extract_members("<html></html>", "委員会")

                # Assert - Pydantic結果を返す
                assert result == pydantic_result
                assert result != baml_result

    @pytest.mark.asyncio
    async def test_handles_pydantic_failure(self, extractor):
        """Pydantic実装が失敗した場合にBAML結果を返すことを確認"""
        baml_result = [
            {
                "name": "山田太郎",
                "role": "委員長",
                "party_name": "自民党",
                "additional_info": None,
            }
        ]

        with patch.object(
            extractor.pydantic_extractor, "extract_members", new_callable=AsyncMock
        ) as mock_pydantic:
            with patch.object(
                extractor.baml_extractor, "extract_members", new_callable=AsyncMock
            ) as mock_baml:
                mock_pydantic.side_effect = Exception("Pydantic error")
                mock_baml.return_value = baml_result

                # Execute
                result = await extractor.extract_members("<html></html>", "本会議")

                # Assert - BAML結果にフォールバック
                assert result == baml_result

    @pytest.mark.asyncio
    async def test_handles_baml_failure(self, extractor):
        """BAML実装が失敗した場合にPydantic結果を返すことを確認"""
        pydantic_result = [
            {
                "name": "山田太郎",
                "role": "委員長",
                "party_name": "自民党",
                "additional_info": None,
            }
        ]

        with patch.object(
            extractor.pydantic_extractor, "extract_members", new_callable=AsyncMock
        ) as mock_pydantic:
            with patch.object(
                extractor.baml_extractor, "extract_members", new_callable=AsyncMock
            ) as mock_baml:
                mock_pydantic.return_value = pydantic_result
                mock_baml.side_effect = Exception("BAML error")

                # Execute
                result = await extractor.extract_members("<html></html>", "本会議")

                # Assert - Pydantic結果を返す
                assert result == pydantic_result

    @pytest.mark.asyncio
    async def test_handles_both_implementations_failure(self, extractor):
        """両実装が失敗した場合に空リストを返すことを確認"""
        with patch.object(
            extractor.pydantic_extractor, "extract_members", new_callable=AsyncMock
        ) as mock_pydantic:
            with patch.object(
                extractor.baml_extractor, "extract_members", new_callable=AsyncMock
            ) as mock_baml:
                mock_pydantic.side_effect = Exception("Pydantic error")
                mock_baml.side_effect = Exception("BAML error")

                # Execute
                result = await extractor.extract_members("<html></html>", "本会議")

                # Assert - 空リストを返す
                assert result == []
