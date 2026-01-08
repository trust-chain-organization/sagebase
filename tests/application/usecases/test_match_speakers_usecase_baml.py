"""Tests for MatchSpeakersUseCase with BAML integration (Issue #885)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.usecases.match_speakers_usecase import MatchSpeakersUseCase
from src.domain.entities.politician import Politician
from src.domain.entities.speaker import Speaker
from src.domain.value_objects.politician_match import PoliticianMatch


class TestMatchSpeakersUseCaseBAML:
    """Test cases for MatchSpeakersUseCase with BAML matching."""

    @pytest.fixture
    def mock_speaker_repo(self):
        """Create mock speaker repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_politician_repo(self):
        """Create mock politician repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_conversation_repo(self):
        """Create mock conversation repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_speaker_service(self):
        """Create mock speaker domain service."""
        service = MagicMock()
        service.normalize_speaker_name = MagicMock(side_effect=lambda x: x.strip())
        service.calculate_name_similarity = MagicMock(
            return_value=0.5
        )  # Low similarity
        return service

    @pytest.fixture
    def mock_llm_service(self):
        """Create mock LLM service."""
        service = AsyncMock()
        return service

    @pytest.fixture
    def mock_update_speaker_usecase(self):
        """Create mock update speaker usecase."""
        usecase = AsyncMock()
        usecase.execute = AsyncMock()
        return usecase

    @pytest.fixture
    def mock_baml_matching_service(self):
        """Create mock BAML politician matching service."""
        service = MagicMock()
        service.find_best_match = AsyncMock(
            return_value=PoliticianMatch(
                matched=True,
                politician_id=100,
                politician_name="BAML太郎",
                political_party_name="BAML党",
                confidence=0.95,
                reason="BAMLマッチング: 名前が一致",
            )
        )
        return service

    @pytest.fixture
    def use_case_with_baml(
        self,
        mock_speaker_repo,
        mock_politician_repo,
        mock_conversation_repo,
        mock_speaker_service,
        mock_llm_service,
        mock_update_speaker_usecase,
        mock_baml_matching_service,
    ):
        """Create MatchSpeakersUseCase instance with BAML service."""
        return MatchSpeakersUseCase(
            speaker_repository=mock_speaker_repo,
            politician_repository=mock_politician_repo,
            conversation_repository=mock_conversation_repo,
            speaker_domain_service=mock_speaker_service,
            llm_service=mock_llm_service,
            update_speaker_usecase=mock_update_speaker_usecase,
            baml_matching_service=mock_baml_matching_service,
        )

    @pytest.fixture
    def use_case_without_baml(
        self,
        mock_speaker_repo,
        mock_politician_repo,
        mock_conversation_repo,
        mock_speaker_service,
        mock_llm_service,
        mock_update_speaker_usecase,
    ):
        """Create MatchSpeakersUseCase instance without BAML service."""
        return MatchSpeakersUseCase(
            speaker_repository=mock_speaker_repo,
            politician_repository=mock_politician_repo,
            conversation_repository=mock_conversation_repo,
            speaker_domain_service=mock_speaker_service,
            llm_service=mock_llm_service,
            update_speaker_usecase=mock_update_speaker_usecase,
            baml_matching_service=None,
        )

    @pytest.mark.asyncio
    async def test_execute_with_baml_matching(
        self,
        use_case_with_baml,
        mock_speaker_repo,
        mock_politician_repo,
        mock_baml_matching_service,
        mock_update_speaker_usecase,
    ):
        """use_baml=Trueの場合、BAMLマッチングが使用される"""
        # Setup
        speaker = Speaker(id=1, name="BAML太郎", is_politician=True)

        mock_speaker_repo.get_politicians.return_value = [speaker]
        mock_politician_repo.search_by_name.return_value = []  # ルールベースマッチなし

        # Execute with use_baml=True
        results = await use_case_with_baml.execute(use_llm=True, use_baml=True)

        # Verify
        assert len(results) == 1
        assert results[0].speaker_id == 1
        assert results[0].matched_politician_id == 100
        assert results[0].confidence_score == 0.95
        assert results[0].matching_method == "baml"
        assert "BAMLマッチング" in results[0].matching_reason

        # BAMLサービスが呼び出されたことを確認
        mock_baml_matching_service.find_best_match.assert_called_once_with(
            speaker_name="BAML太郎",
            speaker_type=None,
            speaker_party=None,
        )

        # 抽出ログが記録されたことを確認
        mock_update_speaker_usecase.execute.assert_called_once()
        call_kwargs = mock_update_speaker_usecase.execute.call_args.kwargs
        assert call_kwargs["entity_id"] == 1
        assert "speaker-matching-baml-v1" in call_kwargs["pipeline_version"]

    @pytest.mark.asyncio
    async def test_execute_baml_false_uses_llm_matching(
        self,
        use_case_with_baml,
        mock_speaker_repo,
        mock_politician_repo,
        mock_llm_service,
        mock_baml_matching_service,
    ):
        """use_baml=Falseの場合、従来のLLMマッチングが使用される"""
        # Setup
        speaker = Speaker(id=2, name="LLM次郎", is_politician=True)
        politician = Politician(id=20, name="LLM次郎", political_party_id=1)

        mock_speaker_repo.get_politicians.return_value = [speaker]
        mock_politician_repo.search_by_name.return_value = []  # ルールベースマッチなし
        mock_politician_repo.get_all.return_value = [politician]
        mock_politician_repo.get_by_id.return_value = politician
        mock_llm_service.match_speaker_to_politician.return_value = {
            "matched_id": 20,
            "confidence": 0.80,
            "reason": "LLMマッチング",
        }

        # Execute with use_baml=False
        results = await use_case_with_baml.execute(use_llm=True, use_baml=False)

        # Verify
        assert len(results) == 1
        assert results[0].matching_method == "llm"

        # BAMLサービスは呼び出されない
        mock_baml_matching_service.find_best_match.assert_not_called()

        # LLMサービスが呼び出されたことを確認
        mock_llm_service.match_speaker_to_politician.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_baml_without_service_falls_back_to_llm(
        self,
        use_case_without_baml,
        mock_speaker_repo,
        mock_politician_repo,
        mock_llm_service,
    ):
        """BAMLサービスがない場合、use_baml=TrueでもLLMマッチングにフォールバック"""
        # Setup
        speaker = Speaker(id=3, name="フォールバック三郎", is_politician=True)
        politician = Politician(id=30, name="フォールバック三郎", political_party_id=1)

        mock_speaker_repo.get_politicians.return_value = [speaker]
        mock_politician_repo.search_by_name.return_value = []  # ルールベースマッチなし
        mock_politician_repo.get_all.return_value = [politician]
        mock_politician_repo.get_by_id.return_value = politician
        mock_llm_service.match_speaker_to_politician.return_value = {
            "matched_id": 30,
            "confidence": 0.75,
        }

        # Execute with use_baml=True but no BAML service configured
        results = await use_case_without_baml.execute(use_llm=True, use_baml=True)

        # Verify - should fall back to LLM
        assert len(results) == 1
        assert results[0].matching_method == "llm"
        mock_llm_service.match_speaker_to_politician.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_baml_no_match(
        self,
        use_case_with_baml,
        mock_speaker_repo,
        mock_politician_repo,
        mock_baml_matching_service,
        mock_update_speaker_usecase,
    ):
        """BAMLマッチングでマッチが見つからない場合"""
        # Setup
        speaker = Speaker(id=4, name="不明四郎", is_politician=True)

        mock_speaker_repo.get_politicians.return_value = [speaker]
        mock_politician_repo.search_by_name.return_value = []  # ルールベースマッチなし

        # BAMLサービスがマッチなしを返す
        mock_baml_matching_service.find_best_match.return_value = PoliticianMatch(
            matched=False,
            politician_id=None,
            politician_name=None,
            political_party_name=None,
            confidence=0.3,
            reason="信頼度が低いためマッチなし",
        )

        # Execute
        results = await use_case_with_baml.execute(use_llm=True, use_baml=True)

        # Verify
        assert len(results) == 1
        assert results[0].matched_politician_id is None
        assert results[0].matching_method == "none"

        # マッチなしの場合は抽出ログを記録しない
        mock_update_speaker_usecase.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_baml_error_returns_none(
        self,
        use_case_with_baml,
        mock_speaker_repo,
        mock_politician_repo,
        mock_baml_matching_service,
        mock_update_speaker_usecase,
    ):
        """BAMLマッチングでエラーが発生した場合、Noneを返す"""
        # Setup
        speaker = Speaker(id=5, name="エラー五郎", is_politician=True)

        mock_speaker_repo.get_politicians.return_value = [speaker]
        mock_politician_repo.search_by_name.return_value = []  # ルールベースマッチなし

        # BAMLサービスがエラーを発生させる
        mock_baml_matching_service.find_best_match.side_effect = Exception("BAML error")

        # Execute
        results = await use_case_with_baml.execute(use_llm=True, use_baml=True)

        # Verify - エラー時はマッチなしとして扱われる
        assert len(results) == 1
        assert results[0].matched_politician_id is None
        assert results[0].matching_method == "none"

        # 抽出ログは記録されない
        mock_update_speaker_usecase.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_baml_with_speaker_type_and_party(
        self,
        use_case_with_baml,
        mock_speaker_repo,
        mock_politician_repo,
        mock_baml_matching_service,
    ):
        """発言者タイプと政党情報がBAMLサービスに渡される"""
        # Setup
        speaker = Speaker(
            id=6,
            name="詳細六郎",
            is_politician=True,
            type="議員",
            political_party_name="自民党",
        )

        mock_speaker_repo.get_politicians.return_value = [speaker]
        mock_politician_repo.search_by_name.return_value = []  # ルールベースマッチなし

        # Execute
        await use_case_with_baml.execute(use_llm=True, use_baml=True)

        # Verify - 発言者情報がBAMLサービスに正しく渡される
        mock_baml_matching_service.find_best_match.assert_called_once_with(
            speaker_name="詳細六郎",
            speaker_type="議員",
            speaker_party="自民党",
        )

    @pytest.mark.asyncio
    async def test_rule_based_matching_takes_priority_over_baml(
        self,
        use_case_with_baml,
        mock_speaker_repo,
        mock_politician_repo,
        mock_speaker_service,
        mock_baml_matching_service,
    ):
        """ルールベースマッチングが成功した場合、BAMLは呼び出されない"""
        # Setup
        speaker = Speaker(id=7, name="ルール七郎", is_politician=True)
        politician = Politician(id=70, name="ルール七郎", political_party_id=1)

        mock_speaker_repo.get_politicians.return_value = [speaker]
        mock_politician_repo.search_by_name.return_value = [politician]
        mock_speaker_service.calculate_name_similarity.return_value = 0.95  # 高類似度

        # Execute
        results = await use_case_with_baml.execute(use_llm=True, use_baml=True)

        # Verify - ルールベースマッチングが成功
        assert len(results) == 1
        assert results[0].matched_politician_id == 70
        assert results[0].matching_method == "rule-based"

        # BAMLサービスは呼び出されない
        mock_baml_matching_service.find_best_match.assert_not_called()

    @pytest.mark.asyncio
    async def test_backward_compatibility_default_use_baml_false(
        self,
        use_case_with_baml,
        mock_speaker_repo,
        mock_politician_repo,
        mock_llm_service,
        mock_baml_matching_service,
    ):
        """デフォルトでuse_baml=Falseが使用される（後方互換性）"""
        # Setup
        speaker = Speaker(id=8, name="互換八郎", is_politician=True)
        politician = Politician(id=80, name="互換八郎", political_party_id=1)

        mock_speaker_repo.get_politicians.return_value = [speaker]
        mock_politician_repo.search_by_name.return_value = []  # ルールベースマッチなし
        mock_politician_repo.get_all.return_value = [politician]
        mock_politician_repo.get_by_id.return_value = politician
        mock_llm_service.match_speaker_to_politician.return_value = {
            "matched_id": 80,
            "confidence": 0.85,
        }

        # Execute without use_baml parameter (should default to False)
        results = await use_case_with_baml.execute(use_llm=True)

        # Verify - LLMマッチングが使用される
        assert len(results) == 1
        assert results[0].matching_method == "llm"

        # BAMLサービスは呼び出されない
        mock_baml_matching_service.find_best_match.assert_not_called()

        # LLMサービスが呼び出される
        mock_llm_service.match_speaker_to_politician.assert_called_once()
