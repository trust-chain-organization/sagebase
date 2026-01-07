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

    @pytest.mark.asyncio
    async def test_extract_members_with_extraction_log_existing_politician(
        self,
    ) -> None:
        """既存政治家に対して抽出ログが記録されること"""
        # Arrange
        from src.domain.entities.politician import Politician

        mock_politician_repo = AsyncMock()
        mock_update_usecase = AsyncMock()

        # 既存の政治家を返す
        existing_politician = Politician(
            id=100,
            name="山田太郎",
            political_party_id=1,
        )
        mock_politician_repo.get_by_name_and_party.return_value = existing_politician

        # UseCaseの戻り値を設定
        mock_update_usecase.execute.return_value = MagicMock(
            updated=True, extraction_log_id=1
        )

        extractor = BAMLPartyMemberExtractor(
            politician_repository=mock_politician_repo,
            update_politician_usecase=mock_update_usecase,
        )

        # モックデータ
        mock_member = MagicMock()
        mock_member.name = "山田太郎"
        mock_member.position = "衆議院議員"
        mock_member.electoral_district = "東京1区"
        mock_member.prefecture = "東京都"
        mock_member.profile_url = "https://example.com/yamada"
        mock_member.party_position = "幹事長"

        mock_html = "<html><body><main>党員一覧</main></body></html>"

        with patch.object(
            extractor, "_fetch_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = mock_html

            with patch(
                "src.infrastructure.external.party_member_extractor.baml_extractor.b.ExtractPartyMembers",
                new_callable=AsyncMock,
            ) as mock_baml:
                mock_baml.return_value = [mock_member]

                # Act
                result = await extractor.extract_members(
                    party_id=1, url="https://example.com/members"
                )

        # Assert
        assert isinstance(result, PartyMemberExtractionResultDTO)
        assert len(result.extracted_members) == 1
        assert result.error is None

        # 政治家検索が呼ばれたことを確認
        mock_politician_repo.get_by_name_and_party.assert_called_once_with(
            name="山田太郎",
            political_party_id=1,
        )

        # UseCaseが既存政治家のIDで呼ばれたことを確認
        mock_update_usecase.execute.assert_called_once()
        call_args = mock_update_usecase.execute.call_args
        assert call_args.kwargs["entity_id"] == 100
        assert call_args.kwargs["pipeline_version"] == "party-member-extraction-v1"

    @pytest.mark.asyncio
    async def test_extract_members_with_extraction_log_new_politician(self) -> None:
        """新規政治家に対して抽出ログが記録されること"""
        # Arrange
        from src.domain.entities.politician import Politician

        mock_politician_repo = AsyncMock()
        mock_update_usecase = AsyncMock()

        # 既存の政治家が見つからない
        mock_politician_repo.get_by_name_and_party.return_value = None

        # 新規作成された政治家を返す
        created_politician = Politician(
            id=200,
            name="新人議員",
            political_party_id=1,
        )
        mock_politician_repo.upsert.return_value = created_politician

        # UseCaseの戻り値を設定
        mock_update_usecase.execute.return_value = MagicMock(
            updated=True, extraction_log_id=2
        )

        extractor = BAMLPartyMemberExtractor(
            politician_repository=mock_politician_repo,
            update_politician_usecase=mock_update_usecase,
        )

        # モックデータ
        mock_member = MagicMock()
        mock_member.name = "新人議員"
        mock_member.position = "衆議院議員"
        mock_member.electoral_district = "大阪1区"
        mock_member.prefecture = None
        mock_member.profile_url = "https://example.com/new"
        mock_member.party_position = None

        mock_html = "<html><body><main>党員一覧</main></body></html>"

        with patch.object(
            extractor, "_fetch_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = mock_html

            with patch(
                "src.infrastructure.external.party_member_extractor.baml_extractor.b.ExtractPartyMembers",
                new_callable=AsyncMock,
            ) as mock_baml:
                mock_baml.return_value = [mock_member]

                # Act
                result = await extractor.extract_members(
                    party_id=1, url="https://example.com/members"
                )

        # Assert
        assert isinstance(result, PartyMemberExtractionResultDTO)
        assert len(result.extracted_members) == 1

        # upsertが呼ばれたことを確認
        mock_politician_repo.upsert.assert_called_once()
        created_pol = mock_politician_repo.upsert.call_args[0][0]
        assert created_pol.name == "新人議員"
        assert created_pol.political_party_id == 1
        assert created_pol.district == "大阪1区"

        # UseCaseが新規政治家のIDで呼ばれたことを確認
        mock_update_usecase.execute.assert_called_once()
        call_args = mock_update_usecase.execute.call_args
        assert call_args.kwargs["entity_id"] == 200

    @pytest.mark.asyncio
    async def test_extract_members_without_dependencies(self) -> None:
        """依存関係が注入されていない場合でも抽出は成功すること（後方互換性）"""
        # Arrange
        extractor = BAMLPartyMemberExtractor()  # 依存関係なし

        mock_member = MagicMock()
        mock_member.name = "テスト議員"
        mock_member.position = None
        mock_member.electoral_district = None
        mock_member.prefecture = None
        mock_member.profile_url = None
        mock_member.party_position = None

        mock_html = "<html><body><main>党員一覧</main></body></html>"

        with patch.object(
            extractor, "_fetch_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = mock_html

            with patch(
                "src.infrastructure.external.party_member_extractor.baml_extractor.b.ExtractPartyMembers",
                new_callable=AsyncMock,
            ) as mock_baml:
                mock_baml.return_value = [mock_member]

                # Act
                result = await extractor.extract_members(
                    party_id=1, url="https://example.com/members"
                )

        # Assert
        assert isinstance(result, PartyMemberExtractionResultDTO)
        assert len(result.extracted_members) == 1
        assert result.error is None

    @pytest.mark.asyncio
    async def test_extraction_log_error_does_not_affect_extraction(self) -> None:
        """抽出ログ記録のエラーが抽出処理に影響しないこと"""
        # Arrange
        mock_politician_repo = AsyncMock()
        mock_update_usecase = AsyncMock()

        # get_by_name_and_partyでエラーを発生させる
        mock_politician_repo.get_by_name_and_party.side_effect = Exception(
            "Database error"
        )

        extractor = BAMLPartyMemberExtractor(
            politician_repository=mock_politician_repo,
            update_politician_usecase=mock_update_usecase,
        )

        mock_member = MagicMock()
        mock_member.name = "エラー議員"
        mock_member.position = None
        mock_member.electoral_district = None
        mock_member.prefecture = None
        mock_member.profile_url = None
        mock_member.party_position = None

        mock_html = "<html><body><main>党員一覧</main></body></html>"

        with patch.object(
            extractor, "_fetch_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = mock_html

            with patch(
                "src.infrastructure.external.party_member_extractor.baml_extractor.b.ExtractPartyMembers",
                new_callable=AsyncMock,
            ) as mock_baml:
                mock_baml.return_value = [mock_member]

                # Act
                result = await extractor.extract_members(
                    party_id=1, url="https://example.com/members"
                )

        # Assert: エラーが発生しても抽出結果は返される
        assert isinstance(result, PartyMemberExtractionResultDTO)
        assert len(result.extracted_members) == 1
        assert result.error is None

    @pytest.mark.asyncio
    async def test_convert_to_extraction_result(self) -> None:
        """ExtractedPartyMemberDTOがPoliticianExtractionResultに正しく変換されること"""
        # Arrange
        from src.application.dtos.extraction_result.politician_extraction_result import (  # noqa: E501
            PoliticianExtractionResult,
        )
        from src.domain.dtos.party_member_dto import ExtractedPartyMemberDTO

        extractor = BAMLPartyMemberExtractor()

        member_dto = ExtractedPartyMemberDTO(
            name="テスト議員",
            position="衆議院議員",
            electoral_district="東京1区",
            prefecture="東京都",
            profile_url="https://example.com/profile",
            party_position="幹事長",
        )

        # Act
        result = extractor._convert_to_extraction_result(member_dto, party_id=5)

        # Assert
        assert isinstance(result, PoliticianExtractionResult)
        assert result.name == "テスト議員"
        assert result.political_party_id == 5
        assert result.district == "東京1区"
        assert result.profile_page_url == "https://example.com/profile"
        assert result.party_position == "幹事長"
        assert result.confidence_score == 1.0
