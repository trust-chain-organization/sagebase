"""政党メンバー抽出器（BAML実装）のテスト

BAMLPartyMemberExtractorの動作を検証します。
このテストでは、LLMの呼び出しをモックして外部APIコストを発生させません。
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# baml_clientモジュールをモック
sys.modules["baml_client"] = MagicMock()
sys.modules["baml_client.async_client"] = MagicMock()

from src.domain.dtos.party_member_dto import (  # noqa: E402
    PartyMemberExtractionResultDTO,
)
from src.infrastructure.external.party_member_extractor.baml_extractor import (  # noqa: E402, E501
    BAMLPartyMemberExtractor,
)


class TestBAMLPartyMemberExtractor:
    """BAMLPartyMemberExtractorのテスト"""

    @pytest.mark.asyncio
    async def test_extract_members_success(self) -> None:
        """メンバー抽出が成功すること"""
        # Arrange
        extractor = BAMLPartyMemberExtractor()

        # モックデータ: BAMLの出力形式（属性を明示的に設定）
        mock_member1 = MagicMock()
        mock_member1.name = "山田太郎"
        mock_member1.position = "衆議院議員"
        mock_member1.electoral_district = "東京1区"
        mock_member1.prefecture = "東京都"
        mock_member1.profile_url = "https://example.com/yamada"
        mock_member1.party_position = "幹事長"

        mock_member2 = MagicMock()
        mock_member2.name = "佐藤花子"
        mock_member2.position = "参議院議員"
        mock_member2.electoral_district = "比例代表"
        mock_member2.prefecture = None
        mock_member2.profile_url = "https://example.com/sato"
        mock_member2.party_position = None

        mock_baml_result = [mock_member1, mock_member2]

        # HTMLフェッチをモック
        mock_html = """
        <html>
            <body>
                <h1>党員一覧</h1>
                <ul>
                    <li>山田太郎</li>
                    <li>佐藤花子</li>
                </ul>
            </body>
        </html>
        """

        with patch.object(
            extractor, "_fetch_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = mock_html

            with patch(
                "src.infrastructure.external.party_member_extractor.baml_extractor.b.ExtractPartyMembers",
                new_callable=AsyncMock,
            ) as mock_baml:
                mock_baml.return_value = mock_baml_result

                # Act
                result = await extractor.extract_members(
                    party_id=1, url="https://example.com/members"
                )

        # Assert
        assert isinstance(result, PartyMemberExtractionResultDTO)
        assert result.party_id == 1
        assert result.url == "https://example.com/members"
        assert len(result.extracted_members) == 2
        assert result.error is None
        assert result.extraction_date is not None

        # 1人目のメンバー確認
        member1 = result.extracted_members[0]
        assert member1.name == "山田太郎"
        assert member1.position == "衆議院議員"
        assert member1.electoral_district == "東京1区"
        assert member1.prefecture == "東京都"
        assert member1.profile_url == "https://example.com/yamada"
        assert member1.party_position == "幹事長"

        # 2人目のメンバー確認
        member2 = result.extracted_members[1]
        assert member2.name == "佐藤花子"
        assert member2.position == "参議院議員"

    @pytest.mark.asyncio
    async def test_extract_members_html_fetch_error(self) -> None:
        """HTML取得エラー時にエラーメッセージを含む結果を返すこと"""
        # Arrange
        extractor = BAMLPartyMemberExtractor()

        with patch.object(
            extractor, "_fetch_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = None

            # Act
            result = await extractor.extract_members(
                party_id=1, url="https://example.com/members"
            )

        # Assert
        assert isinstance(result, PartyMemberExtractionResultDTO)
        assert result.party_id == 1
        assert result.url == "https://example.com/members"
        assert len(result.extracted_members) == 0
        assert result.error is not None
        assert "URLからコンテンツを取得できませんでした" in result.error
        assert result.extraction_date is None

    @pytest.mark.asyncio
    async def test_extract_members_baml_extraction_error(self) -> None:
        """BAML抽出エラー時に空の結果を返すこと（エラーは内部でログされる）"""
        # Arrange
        extractor = BAMLPartyMemberExtractor()
        mock_html = "<html><body>Test</body></html>"

        with patch.object(
            extractor, "_fetch_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = mock_html

            with patch(
                "src.infrastructure.external.party_member_extractor.baml_extractor.b.ExtractPartyMembers",
                new_callable=AsyncMock,
            ) as mock_baml:
                mock_baml.side_effect = Exception("LLM API error")

                # Act
                result = await extractor.extract_members(
                    party_id=1, url="https://example.com/members"
                )

        # Assert
        # エラーは_extract_members_with_bamlで捕捉され、空のリストが返される
        # extract_membersメソッドは正常に完了するため、errorフィールドはNone
        assert isinstance(result, PartyMemberExtractionResultDTO)
        assert result.party_id == 1
        assert len(result.extracted_members) == 0
        assert result.error is None  # エラーは内部で処理される
        assert result.extraction_date is not None  # 正常終了として扱われる

    @pytest.mark.asyncio
    async def test_extract_members_empty_result(self) -> None:
        """抽出結果が空の場合に空のリストを返すこと"""
        # Arrange
        extractor = BAMLPartyMemberExtractor()
        mock_html = "<html><body>No members here</body></html>"

        with patch.object(
            extractor, "_fetch_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = mock_html

            with patch(
                "src.infrastructure.external.party_member_extractor.baml_extractor.b.ExtractPartyMembers",
                new_callable=AsyncMock,
            ) as mock_baml:
                mock_baml.return_value = []

                # Act
                result = await extractor.extract_members(
                    party_id=1, url="https://example.com/members"
                )

        # Assert
        assert isinstance(result, PartyMemberExtractionResultDTO)
        assert result.party_id == 1
        assert len(result.extracted_members) == 0
        assert result.error is None
        assert result.extraction_date is not None

    @pytest.mark.asyncio
    async def test_implements_interface(self) -> None:
        """インターフェースを正しく実装していること"""
        # Arrange
        from src.domain.interfaces.party_member_extractor_service import (
            IPartyMemberExtractorService,
        )

        extractor = BAMLPartyMemberExtractor()

        # Assert
        assert isinstance(extractor, IPartyMemberExtractorService)
