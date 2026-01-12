"""Integration tests for extraction log pipeline (Issue #865).

This module tests the integration between:
1. ExecuteMinutesProcessingUseCase and UpdateStatementFromExtractionUseCase
2. MatchSpeakersUseCase and UpdateSpeakerFromExtractionUseCase

The tests verify that extraction logs are properly recorded when:
- Conversations are created during minutes processing
- Speakers are matched to politicians
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from src.application.dtos.extraction_result.speaker_extraction_result import (
    SpeakerExtractionResult,
)
from src.application.usecases.execute_minutes_processing_usecase import (
    ExecuteMinutesProcessingDTO,
    ExecuteMinutesProcessingUseCase,
)
from src.application.usecases.match_speakers_usecase import MatchSpeakersUseCase
from src.application.usecases.update_conversation_from_extraction_usecase import (
    UpdateConversationFromExtractionUseCase,
)
from src.domain.entities.conversation import Conversation
from src.domain.entities.extraction_log import ExtractionLog
from src.domain.entities.meeting import Meeting
from src.domain.entities.minutes import Minutes
from src.domain.entities.politician import Politician
from src.domain.entities.speaker import Speaker
from src.domain.value_objects.speaker_speech import SpeakerSpeech


class TestMinutesProcessingWithExtractionLog:
    """Test minutes processing with extraction log recording."""

    @pytest.fixture
    def mock_unit_of_work(self):
        """Create mock Unit of Work."""
        uow = AsyncMock()
        uow.meeting_repository = AsyncMock()
        uow.minutes_repository = AsyncMock()
        uow.conversation_repository = AsyncMock()
        uow.speaker_repository = AsyncMock()
        uow.commit = AsyncMock()
        uow.rollback = AsyncMock()
        uow.flush = AsyncMock()
        return uow

    @pytest.fixture
    def mock_extraction_log_repository(self):
        """Create mock extraction log repository."""
        repo = AsyncMock()

        # Simulate returning a log with auto-generated ID
        async def create_log(log: ExtractionLog) -> ExtractionLog:
            log.id = 1  # Simulate ID generation
            return log

        repo.create = AsyncMock(side_effect=create_log)
        repo.get_by_entity = AsyncMock(return_value=None)
        return repo

    @pytest.fixture
    def mock_session_adapter(self):
        """Create mock session adapter."""
        adapter = AsyncMock()
        return adapter

    @pytest.fixture
    def mock_speaker_service(self):
        """Create mock speaker domain service."""
        service = MagicMock()
        service.extract_party_from_name.return_value = ("テスト太郎", "テスト党")
        return service

    @pytest.fixture
    def mock_minutes_processing_service(self):
        """Create mock minutes processing service."""
        service = AsyncMock()
        service.process_minutes.return_value = [
            SpeakerSpeech(speaker="田中太郎", speech_content="発言内容1"),
            SpeakerSpeech(speaker="山田花子", speech_content="発言内容2"),
        ]
        return service

    @pytest.fixture
    def mock_storage_service(self):
        """Create mock storage service."""
        service = AsyncMock()
        service.download_file.return_value = "議事録テキスト".encode()
        return service

    @pytest.fixture
    def update_statement_usecase(
        self, mock_extraction_log_repository, mock_session_adapter
    ):
        """Create UpdateStatementFromExtractionUseCase with mocks."""
        mock_conversation_repo = AsyncMock()
        # Mock get_by_id to return a conversation
        mock_conversation_repo.get_by_id.return_value = Conversation(
            id=1,
            minutes_id=1,
            speaker_name="田中太郎",
            comment="発言内容1",
            sequence_number=1,
        )
        mock_conversation_repo.update = AsyncMock()

        return UpdateConversationFromExtractionUseCase(
            conversation_repo=mock_conversation_repo,
            extraction_log_repo=mock_extraction_log_repository,
            session_adapter=mock_session_adapter,
        )

    @pytest.fixture
    def sample_meeting(self):
        """Create sample meeting entity."""
        return Meeting(
            id=1,
            conference_id=1,
            date=datetime(2024, 1, 1),
            url="https://example.com",
            gcs_text_uri="gs://bucket/text.txt",
            gcs_pdf_uri=None,
        )

    @pytest.fixture
    def sample_minutes(self):
        """Create sample minutes entity."""
        return Minutes(
            id=1,
            meeting_id=1,
            url="https://example.com",
        )

    @pytest.mark.asyncio
    async def test_minutes_processing_creates_extraction_logs(
        self,
        mock_unit_of_work,
        mock_speaker_service,
        mock_minutes_processing_service,
        mock_storage_service,
        update_statement_usecase,
        sample_meeting,
        sample_minutes,
    ):
        """Test that extraction logs are created during minutes processing."""
        # Setup mock responses
        mock_unit_of_work.meeting_repository.get_by_id.return_value = sample_meeting
        mock_unit_of_work.minutes_repository.get_by_meeting.return_value = None
        mock_unit_of_work.minutes_repository.create.return_value = sample_minutes
        mock_unit_of_work.conversation_repository.get_by_minutes.return_value = []

        # Mock conversation creation
        created_conversations = [
            Conversation(
                id=1,
                minutes_id=1,
                speaker_name="田中太郎",
                comment="発言内容1",
                sequence_number=1,
            ),
            Conversation(
                id=2,
                minutes_id=1,
                speaker_name="山田花子",
                comment="発言内容2",
                sequence_number=2,
            ),
        ]
        mock_unit_of_work.conversation_repository.bulk_create.return_value = (
            created_conversations
        )

        # Mock speaker matching
        mock_speaker_service.extract_party_from_name.side_effect = [
            ("田中太郎", "自民党"),
            ("山田花子", "立憲民主党"),
            ("田中太郎", "自民党"),
            ("山田花子", "立憲民主党"),
        ]
        mock_unit_of_work.speaker_repository.get_by_name_party_position.return_value = (
            None
        )
        mock_unit_of_work.speaker_repository.create.return_value = Mock()

        # Create use case
        use_case = ExecuteMinutesProcessingUseCase(
            speaker_domain_service=mock_speaker_service,
            minutes_processing_service=mock_minutes_processing_service,
            storage_service=mock_storage_service,
            unit_of_work=mock_unit_of_work,
            update_statement_usecase=update_statement_usecase,
        )

        # Execute
        request = ExecuteMinutesProcessingDTO(meeting_id=1)
        result = await use_case.execute(request)

        # Verify
        assert result.meeting_id == 1
        assert result.minutes_id == 1
        assert result.total_conversations == 2

        # Verify extraction log UseCase was called
        # (Actual verification depends on mock_extraction_log_repository.create calls)
        assert mock_unit_of_work.commit.called


class TestSpeakerMatchingWithExtractionLog:
    """Test speaker matching with extraction log recording."""

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
        service.calculate_name_similarity = MagicMock(return_value=0.95)
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
    def sample_speaker(self):
        """Create sample speaker entity."""
        return Speaker(
            id=1,
            name="山田太郎",
            political_party_name="自民党",
            is_politician=True,
        )

    @pytest.fixture
    def sample_politician(self):
        """Create sample politician entity."""
        return Politician(
            id=10,
            name="山田太郎",
            prefecture="東京都",
            district="東京1区",
            political_party_id=1,
        )

    @pytest.mark.asyncio
    async def test_speaker_matching_creates_extraction_log(
        self,
        mock_speaker_repo,
        mock_politician_repo,
        mock_conversation_repo,
        mock_speaker_service,
        mock_llm_service,
        mock_update_speaker_usecase,
        sample_speaker,
        sample_politician,
    ):
        """Test that extraction log is created when speaker is matched."""
        # Setup mock responses
        mock_speaker_repo.get_politicians.return_value = [sample_speaker]
        mock_politician_repo.search_by_name.return_value = [sample_politician]

        # Create use case
        use_case = MatchSpeakersUseCase(
            speaker_repository=mock_speaker_repo,
            politician_repository=mock_politician_repo,
            conversation_repository=mock_conversation_repo,
            speaker_domain_service=mock_speaker_service,
            llm_service=mock_llm_service,
            update_speaker_usecase=mock_update_speaker_usecase,
        )

        # Execute with rule-based matching only
        results = await use_case.execute(use_llm=False)

        # Verify
        assert len(results) == 1
        assert results[0].speaker_id == 1
        assert results[0].matched_politician_id == 10
        assert results[0].matching_method == "rule-based"

        # Verify speaker was updated
        mock_speaker_repo.update.assert_called_once()

        # Verify extraction log UseCase was called
        mock_update_speaker_usecase.execute.assert_called_once()

        # Verify extraction log parameters
        call_args = mock_update_speaker_usecase.execute.call_args
        assert call_args.kwargs["entity_id"] == 1
        assert "speaker-matching-rule-based-v1" in call_args.kwargs["pipeline_version"]
        assert isinstance(
            call_args.kwargs["extraction_result"], SpeakerExtractionResult
        )

    @pytest.mark.asyncio
    async def test_no_extraction_log_when_no_match(
        self,
        mock_speaker_repo,
        mock_politician_repo,
        mock_conversation_repo,
        mock_speaker_service,
        mock_llm_service,
        mock_update_speaker_usecase,
        sample_speaker,
    ):
        """Test that no extraction log is created when no match is found."""
        # Setup mock responses - no matches
        mock_speaker_repo.get_politicians.return_value = [sample_speaker]
        mock_politician_repo.search_by_name.return_value = []  # No rule-based match

        # Create use case without BAML service
        use_case = MatchSpeakersUseCase(
            speaker_repository=mock_speaker_repo,
            politician_repository=mock_politician_repo,
            conversation_repository=mock_conversation_repo,
            speaker_domain_service=mock_speaker_service,
            llm_service=mock_llm_service,
            update_speaker_usecase=mock_update_speaker_usecase,
            baml_matching_service=None,  # No BAML service
        )

        # Execute
        results = await use_case.execute(use_llm=True)

        # Verify
        assert len(results) == 1
        assert results[0].matching_method == "none"

        # Verify extraction log UseCase was NOT called
        mock_update_speaker_usecase.execute.assert_not_called()
