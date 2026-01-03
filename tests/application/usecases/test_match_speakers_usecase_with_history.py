"""Tests for MatchSpeakersUseCase with LLM history recording."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.application.usecases.match_speakers_usecase import MatchSpeakersUseCase
from src.domain.entities import Politician, Speaker
from src.domain.entities.llm_processing_history import (
    LLMProcessingHistory,
    ProcessingStatus,
    ProcessingType,
)
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
        service.match_speaker_to_politician = AsyncMock(
            return_value={
                "matched_id": 1,
                "confidence": 0.95,
                "reason": "High name similarity and matching party affiliation",
            }
        )
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
    def use_case(
        self,
        mock_speaker_repo: MagicMock,
        mock_politician_repo: MagicMock,
        mock_conversation_repo: MagicMock,
        mock_speaker_service: MagicMock,
        instrumented_llm_service: InstrumentedLLMService,
        mock_update_speaker_usecase: AsyncMock,
    ) -> MatchSpeakersUseCase:
        """Create MatchSpeakersUseCase with all dependencies."""
        return MatchSpeakersUseCase(
            speaker_repository=mock_speaker_repo,
            politician_repository=mock_politician_repo,
            conversation_repository=mock_conversation_repo,
            speaker_domain_service=mock_speaker_service,
            llm_service=instrumented_llm_service,
            update_speaker_usecase=mock_update_speaker_usecase,
        )

    @pytest.mark.asyncio
    async def test_llm_matching_records_history(
        self,
        use_case: MatchSpeakersUseCase,
        mock_speaker_repo: MagicMock,
        mock_politician_repo: MagicMock,
        mock_history_repo: MagicMock,
    ):
        """Test that LLM-based matching records history."""
        # Arrange
        speaker = Speaker(
            id=1,
            name="山田太郎",
            political_party_name="自民党",
            position="議員",
        )

        politician = Politician(
            id=1,
            name="山田太郎",
            political_party_id=1,
        )

        mock_speaker_repo.get_politicians.return_value = [speaker]
        # No existing politician link
        mock_politician_repo.search_by_name.return_value = []  # No rule-based match
        mock_politician_repo.get_all.return_value = [politician]
        mock_politician_repo.get_by_id.return_value = politician

        # Act
        results = await use_case.execute(use_llm=True)

        # Assert
        assert len(results) == 1
        result = results[0]
        assert result.speaker_id == 1
        assert result.matched_politician_id == 1
        assert result.confidence_score == 0.95
        assert result.matching_method == "llm"
        assert (
            result.matching_reason
            == "High name similarity and matching party affiliation"
        )

        # Verify history was recorded
        mock_history_repo.create.assert_called_once()
        history_call = mock_history_repo.create.call_args[0][0]
        assert history_call.processing_type == ProcessingType.SPEAKER_MATCHING
        assert history_call.status == ProcessingStatus.IN_PROGRESS  # Initial status
        assert history_call.model_name == "gemini-2.0-flash"

        # Verify history was updated with completion
        mock_history_repo.update.assert_called_once()
        updated_history = mock_history_repo.update.call_args[0][0]
        assert updated_history.status == ProcessingStatus.COMPLETED

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
    async def test_set_input_reference_called(
        self,
        use_case: MatchSpeakersUseCase,
        mock_speaker_repo: MagicMock,
        mock_politician_repo: MagicMock,
        instrumented_llm_service: InstrumentedLLMService,
    ):
        """Test that set_input_reference is called when LLM matching is used."""
        # Arrange
        speaker = Speaker(
            id=123,
            name="佐藤花子",
            political_party_name="立憲民主党",
        )

        politician = Politician(
            id=456,
            name="佐藤花子",
            political_party_id=2,
        )

        mock_speaker_repo.get_politicians.return_value = [speaker]
        # No existing politician link
        mock_politician_repo.search_by_name.return_value = []  # No rule-based match
        mock_politician_repo.get_all.return_value = [politician]
        mock_politician_repo.get_by_id.return_value = politician

        # Spy on set_input_reference
        with patch.object(
            instrumented_llm_service, "set_input_reference"
        ) as mock_set_ref:
            # Act
            await use_case.execute(use_llm=True)

            # Assert
            mock_set_ref.assert_called_once_with(
                reference_type="speaker",
                reference_id=123,
            )

    @pytest.mark.asyncio
    async def test_matching_with_no_candidates(
        self,
        use_case: MatchSpeakersUseCase,
        mock_speaker_repo: MagicMock,
        mock_politician_repo: MagicMock,
        mock_history_repo: MagicMock,
    ):
        """Test matching when no politician candidates are available."""
        # Arrange
        speaker = Speaker(
            id=1,
            name="新人議員",
        )

        mock_speaker_repo.get_politicians.return_value = [speaker]
        # No existing politician link
        mock_politician_repo.search_by_name.return_value = []
        mock_politician_repo.get_all.return_value = []  # No candidates
        # Ensure get_all_cached doesn't exist so it uses get_all
        if hasattr(mock_politician_repo, "get_all_cached"):
            del mock_politician_repo.get_all_cached

        # Act
        results = await use_case.execute(use_llm=True)

        # Assert
        assert len(results) == 1
        result = results[0]
        assert result.speaker_id == 1
        assert result.matched_politician_id is None
        assert result.confidence_score == 0.0
        assert result.matching_method == "none"
        assert result.matching_reason == "No matching politician found"

        # Verify history was NOT recorded (no LLM call made)
        mock_history_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_history_recording_failure_doesnt_break_matching(
        self,
        use_case: MatchSpeakersUseCase,
        mock_speaker_repo: MagicMock,
        mock_politician_repo: MagicMock,
        mock_history_repo: MagicMock,
    ):
        """Test that history recording failure doesn't break the matching process."""
        # Arrange
        speaker = Speaker(
            id=1,
            name="エラーテスト議員",
        )

        politician = Politician(
            id=1,
            name="エラーテスト議員",
            political_party_id=1,
        )

        mock_speaker_repo.get_politicians.return_value = [speaker]
        # No existing politician link
        mock_politician_repo.search_by_name.return_value = []
        mock_politician_repo.get_all.return_value = [politician]
        mock_politician_repo.get_by_id.return_value = politician

        # Make history recording fail
        mock_history_repo.create.side_effect = Exception("Database error")

        # Act
        results = await use_case.execute(use_llm=True)

        # Assert - matching should still succeed
        assert len(results) == 1
        result = results[0]
        assert result.speaker_id == 1
        assert result.matched_politician_id == 1
        assert result.confidence_score == 0.95
        assert result.matching_method == "llm"
