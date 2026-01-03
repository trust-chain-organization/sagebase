"""政治家マッチング処理の抽出ログ統合テスト。"""

from unittest.mock import AsyncMock

import pytest

from src.application.usecases.update_politician_from_extraction_usecase import (
    UpdatePoliticianFromExtractionUseCase,
)
from src.domain.entities.extraction_log import EntityType, ExtractionLog
from src.domain.entities.politician import Politician
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.services.baml_politician_matching_service import (
    BAMLPoliticianMatchingService,
)
from src.domain.services.interfaces.llm_service import ILLMService


class TestPoliticianMatchingWithExtractionLog:
    """政治家マッチング処理の抽出ログ統合テスト。"""

    @pytest.fixture
    def mock_llm_service(self):
        """モックLLMサービスを作成。"""
        return AsyncMock(spec=ILLMService)

    @pytest.fixture
    def mock_politician_repo(self):
        """モック政治家リポジトリを作成。"""
        repo = AsyncMock(spec=PoliticianRepository)
        # get_all_for_matching用のモックデータ
        repo.get_all_for_matching.return_value = [
            {
                "id": 1,
                "name": "山田太郎",
                "party_name": "テスト党",
                "position": None,
                "prefecture": "東京都",
                "electoral_district": "東京1区",
            },
            {
                "id": 2,
                "name": "佐藤花子",
                "party_name": "サンプル党",
                "position": None,
                "prefecture": "大阪府",
                "electoral_district": "大阪2区",
            },
        ]
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
    def matching_service(
        self, mock_llm_service, mock_politician_repo, update_politician_usecase
    ):
        """BAMLPoliticianMatchingServiceを作成。"""
        return BAMLPoliticianMatchingService(
            llm_service=mock_llm_service,
            politician_repository=mock_politician_repo,
            update_politician_usecase=update_politician_usecase,
        )

    @pytest.mark.asyncio
    async def test_matching_with_extraction_log_recording(
        self,
        matching_service,
        mock_politician_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """マッチング成功時に抽出ログが記録される。"""
        # Setup
        politician = Politician(
            id=1,
            name="山田太郎",
            political_party_id=1,
            is_manually_verified=False,
        )
        extraction_log = ExtractionLog(
            id=100,
            entity_type=EntityType.POLITICIAN,
            entity_id=1,
            pipeline_version="politician-matching-v1",
            extracted_data={
                "match_confidence": 0.95,
                "match_reason": "名前と政党が完全一致",
            },
        )

        mock_politician_repo.get_by_id.return_value = politician
        mock_extraction_log_repo.create.return_value = extraction_log

        # Execute - ルールベースマッチングで完全一致
        result = await matching_service.find_best_match(
            speaker_name="山田太郎", speaker_type="議員", speaker_party="テスト党"
        )

        # Assert - マッチング結果
        assert result.matched is True
        assert result.politician_id == 1
        assert result.politician_name == "山田太郎"
        assert result.confidence >= 0.9  # 完全一致なので高い信頼度

        # Assert - 抽出ログが記録された
        mock_extraction_log_repo.create.assert_called_once()
        created_log_call = mock_extraction_log_repo.create.call_args
        created_log = created_log_call[0][0]

        assert created_log.entity_type == EntityType.POLITICIAN
        assert created_log.entity_id == 1
        assert created_log.pipeline_version == "politician-matching-v1"
        assert "match_confidence" in created_log.extracted_data
        assert "match_reason" in created_log.extracted_data

        # Assert - セッションがコミットされた
        mock_session_adapter.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_matching_failure_no_log_recording(
        self,
        matching_service,
        mock_politician_repo,
        mock_extraction_log_repo,
    ):
        """マッチング失敗時は抽出ログが記録されない。"""
        # Setup - マッチング候補なし
        mock_politician_repo.get_all_for_matching.return_value = []

        # Execute
        result = await matching_service.find_best_match(
            speaker_name="存在しない議員", speaker_type="議員", speaker_party="不明党"
        )

        # Assert - マッチング失敗
        assert result.matched is False
        assert result.politician_id is None

        # Assert - 抽出ログは記録されない（マッチング失敗のため）
        mock_extraction_log_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_matching_log_recording_does_not_affect_result(
        self,
        matching_service,
        mock_politician_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """抽出ログ記録の失敗がマッチング結果に影響しない。"""
        # Setup
        politician = Politician(
            id=1,
            name="山田太郎",
            political_party_id=1,
            is_manually_verified=False,
        )
        mock_politician_repo.get_by_id.return_value = politician

        # 抽出ログの作成は成功するが、commitでエラー
        extraction_log = ExtractionLog(
            id=100,
            entity_type=EntityType.POLITICIAN,
            entity_id=1,
            pipeline_version="politician-matching-v1",
            extracted_data={},
        )
        mock_extraction_log_repo.create.return_value = extraction_log
        mock_session_adapter.commit.side_effect = Exception("Database error")

        # Execute - ルールベースマッチングで完全一致
        result = await matching_service.find_best_match(
            speaker_name="山田太郎", speaker_type="議員", speaker_party="テスト党"
        )

        # Assert - マッチング結果は成功（ログ記録の失敗に影響されない）
        assert result.matched is True
        assert result.politician_id == 1
        assert result.politician_name == "山田太郎"
