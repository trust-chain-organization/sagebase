"""Tests for MatchSpeakersUseCase with history recording.

Note: Issue #906 removed legacy LLM matching. BAML is now the only LLM matching method.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.usecases.match_speakers_usecase import MatchSpeakersUseCase
from src.domain.entities import Politician, Speaker
from src.domain.entities.llm_processing_history import (
    LLMProcessingHistory,
    ProcessingStatus,
    ProcessingType,
)
from src.domain.value_objects.politician_match import PoliticianMatch
from src.infrastructure.external.instrumented_llm_service import InstrumentedLLMService


class TestMatchSpeakersUseCaseWithHistory:
    """Test cases for MatchSpeakersUseCase with history recording."""

    @pytest.fixture
    def mock_speaker_repo(self) -> AsyncMock:
        """Create mock speaker repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_politician_repo(self) -> AsyncMock:
        """Create mock politician repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_conversation_repo(self) -> AsyncMock:
        """Create mock conversation repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_speaker_service(self) -> MagicMock:
        """Create mock speaker domain service."""
        service = MagicMock()
        service.normalize_speaker_name.return_value = "normalized_name"
        service.calculate_name_similarity.return_value = 0.9
        return service

    @pytest.fixture
    def mock_base_llm_service(self) -> AsyncMock:
        """Create mock base LLM service."""
        service = AsyncMock()
        service.temperature = 0.1
        service.model_name = "gemini-2.0-flash"
        return service

    @pytest.fixture
    def mock_history_repo(self) -> AsyncMock:
        """Create mock history repository."""
        repo = AsyncMock()

        # Create a proper history entry that starts in IN_PROGRESS and gets updated
        history_entry = LLMProcessingHistory(
            processing_type=ProcessingType.SPEAKER_MATCHING,
            status=ProcessingStatus.IN_PROGRESS,
            model_name="gemini-2.0-flash",
            model_version="2.0",
            prompt_template="speaker_matching",
            prompt_variables={"speaker_name": "山田太郎"},
            input_reference_type="speaker",
            input_reference_id=1,
            result={"matched_id": 1, "confidence": 0.95},
        )

        # Mock create to return the entry and update to modify it
        async def mock_create(entry: LLMProcessingHistory) -> LLMProcessingHistory:
            # Copy the entry's properties to our fixture
            history_entry.status = entry.status
            history_entry.processing_type = entry.processing_type
            history_entry.model_name = entry.model_name
            history_entry.model_version = entry.model_version
            return history_entry

        async def mock_update(entry: LLMProcessingHistory) -> LLMProcessingHistory:
            # Update status when update is called
            history_entry.status = entry.status
            history_entry.result = entry.result
            return history_entry

        repo.create = AsyncMock(side_effect=mock_create)
        repo.update = AsyncMock(side_effect=mock_update)

        return repo

    @pytest.fixture
    def instrumented_llm_service(
        self, mock_base_llm_service: MagicMock, mock_history_repo: MagicMock
    ) -> InstrumentedLLMService:
        """Create instrumented LLM service with history recording."""
        return InstrumentedLLMService(
            llm_service=mock_base_llm_service,
            history_repository=mock_history_repo,
            model_name="gemini-2.0-flash",
            model_version="2.0",
        )

    @pytest.fixture
    def mock_update_speaker_usecase(self) -> AsyncMock:
        """Create mock update speaker usecase."""
        usecase = AsyncMock()
        usecase.execute = AsyncMock()
        return usecase

    @pytest.fixture
    def mock_baml_matching_service(self) -> MagicMock:
        """Create mock BAML matching service."""
        service = MagicMock()
        service.find_best_match = AsyncMock(
            return_value=PoliticianMatch(
                matched=True,
                politician_id=1,
                politician_name="山田太郎",
                political_party_name="自民党",
                confidence=0.95,
                reason="BAMLマッチング: 名前が一致",
            )
        )
        return service

    @pytest.fixture
    def use_case(
        self,
        mock_speaker_repo: MagicMock,
        mock_politician_repo: MagicMock,
        mock_conversation_repo: MagicMock,
        mock_speaker_service: MagicMock,
        instrumented_llm_service: InstrumentedLLMService,
        mock_update_speaker_usecase: AsyncMock,
        mock_baml_matching_service: MagicMock,
    ) -> MatchSpeakersUseCase:
        """Create MatchSpeakersUseCase with all dependencies."""
        return MatchSpeakersUseCase(
            speaker_repository=mock_speaker_repo,
            politician_repository=mock_politician_repo,
            conversation_repository=mock_conversation_repo,
            speaker_domain_service=mock_speaker_service,
            llm_service=instrumented_llm_service,
            update_speaker_usecase=mock_update_speaker_usecase,
            baml_matching_service=mock_baml_matching_service,
        )

    @pytest.mark.asyncio
    async def test_baml_matching_creates_extraction_log(
        self,
        use_case: MatchSpeakersUseCase,
        mock_speaker_repo: MagicMock,
        mock_politician_repo: MagicMock,
        mock_baml_matching_service: MagicMock,
        mock_update_speaker_usecase: AsyncMock,
    ):
        """Test that BAML-based matching creates extraction log."""
        # Arrange
        speaker = Speaker(
            id=1,
            name="山田太郎",
            political_party_name="自民党",
            position="議員",
        )

        mock_speaker_repo.get_politicians.return_value = [speaker]
        mock_politician_repo.search_by_name.return_value = []  # No rule-based match

        # Act
        results = await use_case.execute(use_llm=True)

        # Assert
        assert len(results) == 1
        result = results[0]
        assert result.speaker_id == 1
        assert result.matched_politician_id == 1
        assert result.confidence_score == 0.95
        assert result.matching_method == "baml"
        assert "BAMLマッチング" in result.matching_reason

        # Verify BAML service was called
        mock_baml_matching_service.find_best_match.assert_called_once()

        # Verify extraction log was created
        mock_update_speaker_usecase.execute.assert_called_once()
        call_kwargs = mock_update_speaker_usecase.execute.call_args.kwargs
        assert call_kwargs["entity_id"] == 1
        assert "speaker-matching-baml-v1" in call_kwargs["pipeline_version"]

    @pytest.mark.asyncio
    async def test_rule_based_matching_no_history(
        self,
        use_case: MatchSpeakersUseCase,
        mock_speaker_repo: MagicMock,
        mock_politician_repo: MagicMock,
        mock_history_repo: MagicMock,
    ):
        """Test that rule-based matching doesn't record LLM history."""
        # Arrange
        speaker = Speaker(
            id=1,
            name="山田太郎",
            political_party_name="自民党",
        )

        politician = Politician(
            id=1,
            name="山田太郎",
            prefecture="東京都",
            district="東京1区",
            political_party_id=1,
        )

        mock_speaker_repo.get_politicians.return_value = [speaker]
        # No existing politician link
        mock_politician_repo.search_by_name.return_value = [
            politician
        ]  # Rule-based match found

        # Act
        results = await use_case.execute(use_llm=False)

        # Assert
        assert len(results) == 1
        result = results[0]
        assert result.speaker_id == 1
        assert result.matched_politician_id == 1
        assert result.matching_method == "rule-based"

        # Verify history was NOT recorded (rule-based doesn't use LLM)
        mock_history_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_baml_matching_no_match(
        self,
        use_case: MatchSpeakersUseCase,
        mock_speaker_repo: MagicMock,
        mock_politician_repo: MagicMock,
        mock_baml_matching_service: MagicMock,
        mock_update_speaker_usecase: AsyncMock,
    ):
        """Test matching when BAML service returns no match."""
        # Arrange
        speaker = Speaker(
            id=1,
            name="新人議員",
        )

        mock_speaker_repo.get_politicians.return_value = [speaker]
        mock_politician_repo.search_by_name.return_value = []

        # BAML service returns no match
        mock_baml_matching_service.find_best_match.return_value = PoliticianMatch(
            matched=False,
            politician_id=None,
            politician_name=None,
            political_party_name=None,
            confidence=0.3,
            reason="信頼度が低いためマッチなし",
        )

        # Act
        results = await use_case.execute(use_llm=True)

        # Assert
        assert len(results) == 1
        result = results[0]
        assert result.speaker_id == 1
        assert result.matched_politician_id is None
        assert result.confidence_score == 0.0
        assert result.matching_method == "none"

        # Verify extraction log was NOT created for no match
        mock_update_speaker_usecase.execute.assert_not_called()
