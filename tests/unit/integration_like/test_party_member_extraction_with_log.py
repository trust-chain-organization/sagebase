"""政党メンバー抽出処理の抽出ログ統合テスト。

BAMLPartyMemberExtractorとUpdatePoliticianFromExtractionUseCaseの統合テスト。

注意: このテストはbaml_clientをモックするため、他のBAML統合テストより先に実行されると
それらのテストに影響を与える可能性があります。この問題を回避するため、session-scoped
fixtureでモックを管理し、テスト終了後に復元します。
"""

import sys

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# モック前の状態を保存
_original_baml_client = sys.modules.get("baml_client")
_original_baml_async_client = sys.modules.get("baml_client.async_client")


@pytest.fixture(scope="module", autouse=True)
def mock_baml_client():
    """BAMLクライアントをモックし、テスト終了後に復元する。"""
    # モックを設定
    mock_baml = MagicMock()
    mock_async = MagicMock()
    sys.modules["baml_client"] = mock_baml
    sys.modules["baml_client.async_client"] = mock_async

    yield

    # 元の状態に復元
    if _original_baml_client is not None:
        sys.modules["baml_client"] = _original_baml_client
    else:
        sys.modules.pop("baml_client", None)

    if _original_baml_async_client is not None:
        sys.modules["baml_client.async_client"] = _original_baml_async_client
    else:
        sys.modules.pop("baml_client.async_client", None)


# baml_clientモジュールをモック（インポート時に必要）
sys.modules["baml_client"] = MagicMock()
sys.modules["baml_client.async_client"] = MagicMock()

from src.application.usecases.update_politician_from_extraction_usecase import (  # noqa: E402
    UpdatePoliticianFromExtractionUseCase,
)
from src.domain.entities.extraction_log import EntityType, ExtractionLog  # noqa: E402
from src.domain.entities.politician import Politician  # noqa: E402
from src.domain.repositories.politician_repository import (  # noqa: E402
    PoliticianRepository,
)
from src.infrastructure.external.party_member_extractor.baml_extractor import (  # noqa: E402
    BAMLPartyMemberExtractor,
)


class TestPartyMemberExtractionWithLog:
    """政党メンバー抽出処理の抽出ログ統合テスト。"""

    @pytest.fixture
    def mock_politician_repo(self):
        """モック政治家リポジトリを作成。"""
        repo = AsyncMock(spec=PoliticianRepository)
        return repo

    @pytest.fixture
    def mock_extraction_log_repo(self):
        """モック抽出ログリポジトリを作成。"""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_session_adapter(self):
        """モックセッションアダプターを作成。"""
        adapter = AsyncMock()
        return adapter

    @pytest.fixture
    def update_politician_usecase(
        self, mock_politician_repo, mock_extraction_log_repo, mock_session_adapter
    ):
        """UpdatePoliticianFromExtractionUseCaseを作成。"""
        return UpdatePoliticianFromExtractionUseCase(
            politician_repo=mock_politician_repo,
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.fixture
    def extractor(self, mock_politician_repo, update_politician_usecase):
        """BAMLPartyMemberExtractorを作成。"""
        return BAMLPartyMemberExtractor(
            politician_repository=mock_politician_repo,
            update_politician_usecase=update_politician_usecase,
        )

    @pytest.mark.asyncio
    async def test_extraction_with_existing_politician_log_recording(
        self,
        extractor,
        mock_politician_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """既存政治家の抽出時に抽出ログが記録される。"""
        # Setup - 既存の政治家を返す
        existing_politician = Politician(
            id=100,
            name="山田太郎",
            political_party_id=1,
            is_manually_verified=False,
        )
        mock_politician_repo.get_by_name_and_party.return_value = existing_politician
        mock_politician_repo.get_by_id.return_value = existing_politician

        # 抽出ログの作成
        extraction_log = ExtractionLog(
            id=1,
            entity_type=EntityType.POLITICIAN,
            entity_id=100,
            pipeline_version="party-member-extraction-v1",
            extracted_data={},
        )
        mock_extraction_log_repo.create.return_value = extraction_log

        # BAMLの結果をモック
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

                # Execute
                result = await extractor.extract_members(
                    party_id=1, url="https://example.com/members"
                )

        # Assert - 抽出結果
        assert len(result.extracted_members) == 1
        assert result.extracted_members[0].name == "山田太郎"
        assert result.error is None

        # Assert - 政治家検索が呼ばれた
        mock_politician_repo.get_by_name_and_party.assert_called_with(
            name="山田太郎",
            political_party_id=1,
        )

        # Assert - 抽出ログが記録された
        mock_extraction_log_repo.create.assert_called_once()
        created_log_call = mock_extraction_log_repo.create.call_args
        created_log = created_log_call[0][0]

        assert created_log.entity_type == EntityType.POLITICIAN
        assert created_log.entity_id == 100
        assert created_log.pipeline_version == "party-member-extraction-v1"
        assert created_log.extracted_data["name"] == "山田太郎"
        assert created_log.extracted_data["political_party_id"] == 1
        assert created_log.extracted_data["district"] == "東京1区"
        assert created_log.confidence_score == 1.0

    @pytest.mark.asyncio
    async def test_extraction_with_new_politician_log_recording(
        self,
        extractor,
        mock_politician_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """新規政治家の抽出時に政治家作成と抽出ログが記録される。"""
        # Setup - 既存の政治家が見つからない
        mock_politician_repo.get_by_name_and_party.return_value = None

        # 新規作成された政治家を返す
        created_politician = Politician(
            id=200,
            name="新人議員",
            political_party_id=1,
            is_manually_verified=False,
        )
        mock_politician_repo.upsert.return_value = created_politician
        mock_politician_repo.get_by_id.return_value = created_politician

        # 抽出ログの作成
        extraction_log = ExtractionLog(
            id=2,
            entity_type=EntityType.POLITICIAN,
            entity_id=200,
            pipeline_version="party-member-extraction-v1",
            extracted_data={},
        )
        mock_extraction_log_repo.create.return_value = extraction_log

        # BAMLの結果をモック
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

                # Execute
                result = await extractor.extract_members(
                    party_id=1, url="https://example.com/members"
                )

        # Assert - 抽出結果
        assert len(result.extracted_members) == 1
        assert result.extracted_members[0].name == "新人議員"

        # Assert - 新規政治家が作成された
        mock_politician_repo.upsert.assert_called_once()
        created_pol = mock_politician_repo.upsert.call_args[0][0]
        assert created_pol.name == "新人議員"
        assert created_pol.political_party_id == 1
        assert created_pol.district == "大阪1区"
        assert created_pol.profile_page_url == "https://example.com/new"

        # Assert - 抽出ログが新規政治家のIDで記録された
        mock_extraction_log_repo.create.assert_called_once()
        created_log_call = mock_extraction_log_repo.create.call_args
        created_log = created_log_call[0][0]
        assert created_log.entity_id == 200

    @pytest.mark.asyncio
    async def test_extraction_multiple_members_logs_all(
        self,
        extractor,
        mock_politician_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """複数メンバーの抽出時に全員分のログが記録される。"""
        # Setup
        politician1 = Politician(
            id=1, name="議員A", political_party_id=1, is_manually_verified=False
        )
        politician2 = Politician(
            id=2, name="議員B", political_party_id=1, is_manually_verified=False
        )

        # get_by_name_and_partyの戻り値を名前に応じて変える
        async def get_by_name_and_party_side_effect(name, political_party_id):
            if name == "議員A":
                return politician1
            elif name == "議員B":
                return politician2
            return None

        mock_politician_repo.get_by_name_and_party.side_effect = (
            get_by_name_and_party_side_effect
        )
        mock_politician_repo.get_by_id.side_effect = [politician1, politician2]

        # 抽出ログの作成（2回呼ばれる）
        extraction_log1 = ExtractionLog(
            id=1,
            entity_type=EntityType.POLITICIAN,
            entity_id=1,
            pipeline_version="v1",
            extracted_data={},
        )
        extraction_log2 = ExtractionLog(
            id=2,
            entity_type=EntityType.POLITICIAN,
            entity_id=2,
            pipeline_version="v1",
            extracted_data={},
        )
        mock_extraction_log_repo.create.side_effect = [extraction_log1, extraction_log2]

        # BAMLの結果をモック（2名）
        mock_member1 = MagicMock()
        mock_member1.name = "議員A"
        mock_member1.position = None
        mock_member1.electoral_district = None
        mock_member1.prefecture = None
        mock_member1.profile_url = None
        mock_member1.party_position = None

        mock_member2 = MagicMock()
        mock_member2.name = "議員B"
        mock_member2.position = None
        mock_member2.electoral_district = None
        mock_member2.prefecture = None
        mock_member2.profile_url = None
        mock_member2.party_position = None

        mock_html = "<html><body><main>党員一覧</main></body></html>"

        with patch.object(
            extractor, "_fetch_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = mock_html

            with patch(
                "src.infrastructure.external.party_member_extractor.baml_extractor.b.ExtractPartyMembers",
                new_callable=AsyncMock,
            ) as mock_baml:
                mock_baml.return_value = [mock_member1, mock_member2]

                # Execute
                result = await extractor.extract_members(
                    party_id=1, url="https://example.com/members"
                )

        # Assert - 2名抽出
        assert len(result.extracted_members) == 2

        # Assert - 2回ログが記録された
        assert mock_extraction_log_repo.create.call_count == 2

    @pytest.mark.asyncio
    async def test_extraction_log_error_does_not_affect_extraction_result(
        self,
        extractor,
        mock_politician_repo,
        mock_extraction_log_repo,
    ):
        """抽出ログ記録の失敗が抽出処理に影響しない。"""
        # Setup - リポジトリでエラー発生
        mock_politician_repo.get_by_name_and_party.side_effect = Exception(
            "Database error"
        )

        # BAMLの結果をモック
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

                # Execute
                result = await extractor.extract_members(
                    party_id=1, url="https://example.com/members"
                )

        # Assert - エラーが発生しても抽出結果は返される
        assert len(result.extracted_members) == 1
        assert result.extracted_members[0].name == "エラー議員"
        assert result.error is None

        # Assert - 抽出ログは記録されなかった（エラーのため）
        mock_extraction_log_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_extraction_without_dependencies_backward_compatible(self):
        """依存関係なしでも抽出が成功する（後方互換性）。"""
        # 依存関係なしで作成
        extractor = BAMLPartyMemberExtractor()

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

                # Execute
                result = await extractor.extract_members(
                    party_id=1, url="https://example.com/members"
                )

        # Assert - 抽出成功
        assert len(result.extracted_members) == 1
        assert result.error is None
