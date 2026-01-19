"""Tests for InstrumentedLLMService."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.dtos.base_dto import PoliticianBaseDTO
from src.domain.entities.llm_processing_history import (
    LLMProcessingHistory,
    ProcessingStatus,
    ProcessingType,
)
from src.domain.repositories.llm_processing_history_repository import (
    LLMProcessingHistoryRepository,
)
from src.domain.types import (
    LLMExtractResult,
    LLMMatchResult,
)
from src.infrastructure.external.instrumented_llm_service import InstrumentedLLMService


class MockLLMService:
    """Mock LLM service for testing."""

    def __init__(self):
        self.temperature = 0.1
        self.model_name = "test-model"

    def set_history_repository(
        self, repository: LLMProcessingHistoryRepository | None
    ) -> None:
        pass

    def get_processing_history(
        self, reference_type: str | None = None, reference_id: int | None = None
    ) -> list[LLMProcessingHistory]:
        return []

    def extract_speeches_from_text(self, text: str) -> list[dict[str, str]]:
        return [{"speaker": "Test Speaker", "content": "Test content"}]

    def extract_party_members(
        self, html_content: str, party_id: int
    ) -> LLMExtractResult:
        return LLMExtractResult(
            success=True,
            extracted_data=[{"name": "Test Politician"}],
            error=None,
            metadata={"test": "data"},
        )

    def match_conference_member(
        self,
        member_name: str,
        party_name: str | None,
        candidates: list[PoliticianBaseDTO],
    ) -> LLMMatchResult | None:
        return LLMMatchResult(
            matched=True,
            confidence=0.9,
            reason="Test match",
            matched_id=456,
            metadata={"test": "data"},
        )


@pytest.fixture
def mock_llm_service():
    """Create mock LLM service."""
    return MockLLMService()


@pytest.fixture
def mock_history_repository():
    """Create mock history repository."""
    repo = MagicMock(spec=LLMProcessingHistoryRepository)
    repo.create = AsyncMock(side_effect=lambda x: x)  # Return the same object
    repo.update = AsyncMock(return_value=None)
    repo.get_by_input_reference = MagicMock(return_value=[])
    return repo


@pytest.fixture
def instrumented_service(mock_llm_service, mock_history_repository):
    """Create instrumented LLM service."""
    return InstrumentedLLMService(
        llm_service=mock_llm_service,
        history_repository=mock_history_repository,
        model_name="test-model",
        model_version="1.0.0",
    )


class TestInstrumentedLLMService:
    """Test InstrumentedLLMService functionality."""

    @pytest.mark.asyncio
    async def test_extract_speeches_with_history(
        self, instrumented_service, mock_history_repository
    ):
        """Test speech extraction records history."""
        text = "Test meeting minutes text"

        result = await instrumented_service.extract_speeches_from_text(text)

        # Verify result
        assert len(result) == 1
        assert result[0]["speaker"] == "Test Speaker"

        # Verify history was recorded
        assert mock_history_repository.create.called
        assert mock_history_repository.update.called

        # Check history entry
        history_call = mock_history_repository.create.call_args[0][0]
        assert history_call.processing_type == ProcessingType.SPEECH_EXTRACTION
        assert history_call.prompt_variables["text_length"] == len(text)

    @pytest.mark.asyncio
    async def test_extract_party_members_with_history(
        self, instrumented_service, mock_history_repository
    ):
        """Test party member extraction records history."""
        html_content = "<html>Test content</html>"
        party_id = 5

        result = await instrumented_service.extract_party_members(
            html_content, party_id
        )

        # Verify result
        assert result["success"] is True
        assert len(result["extracted_data"]) == 1

        # Verify history was recorded
        assert mock_history_repository.create.called
        assert mock_history_repository.update.called

        # Check history entry
        history_call = mock_history_repository.create.call_args[0][0]
        assert history_call.processing_type == ProcessingType.POLITICIAN_EXTRACTION
        assert history_call.input_reference_type == "party"
        assert history_call.input_reference_id == party_id

    @pytest.mark.asyncio
    async def test_match_conference_member_with_history(
        self, instrumented_service, mock_history_repository
    ):
        """Test conference member matching records history."""
        member_name = "Test Member"
        party_name = "Test Party"
        candidates = [
            PoliticianBaseDTO(id=1, name="Politician 1", party_name="Party A"),
            PoliticianBaseDTO(id=2, name="Politician 2", party_name="Party B"),
        ]

        result = await instrumented_service.match_conference_member(
            member_name, party_name, candidates
        )

        # Verify result
        assert result is not None
        assert result["matched"] is True
        assert result["confidence"] == 0.9

        # Verify history was recorded
        assert mock_history_repository.create.called
        assert mock_history_repository.update.called

        # Check history entry
        history_call = mock_history_repository.create.call_args[0][0]
        assert history_call.processing_type == ProcessingType.CONFERENCE_MEMBER_MATCHING
        assert history_call.prompt_variables["member_name"] == member_name
        assert history_call.prompt_variables["party_name"] == party_name
        assert history_call.prompt_variables["candidates_count"] == 2

    @pytest.mark.asyncio
    async def test_processing_with_error(
        self, mock_llm_service, mock_history_repository
    ):
        """Test history recording when processing fails."""
        # Make the LLM service raise an error
        mock_llm_service.extract_speeches_from_text = MagicMock(
            side_effect=Exception("Test error")
        )

        instrumented_service = InstrumentedLLMService(
            llm_service=mock_llm_service,
            history_repository=mock_history_repository,
            model_name="test-model",
            model_version="1.0.0",
        )

        text = "Test meeting minutes text"

        # Should raise the exception
        with pytest.raises(Exception, match="Test error"):
            await instrumented_service.extract_speeches_from_text(text)

        # Verify history was still recorded with failure
        assert mock_history_repository.create.called
        assert mock_history_repository.update.called

        # Check that the update call recorded the failure
        update_call = mock_history_repository.update.call_args[0][0]
        assert update_call.status == ProcessingStatus.FAILED
        assert update_call.error_message == "Test error"

    @pytest.mark.asyncio
    async def test_no_history_repository(self, mock_llm_service):
        """Test service works without history repository."""
        instrumented_service = InstrumentedLLMService(
            llm_service=mock_llm_service,
            history_repository=None,  # No repository
            model_name="test-model",
            model_version="1.0.0",
        )

        text = "Test meeting minutes text"

        # Should work normally without recording history
        result = await instrumented_service.extract_speeches_from_text(text)
        assert result is not None
        assert len(result) == 1
        assert result[0]["speaker"] == "Test Speaker"

    def test_get_processing_history(
        self, instrumented_service, mock_history_repository
    ):
        """Test retrieving processing history."""
        # Set up mock return value
        expected_history = [
            LLMProcessingHistory(
                processing_type=ProcessingType.SPEAKER_MATCHING,
                model_name="test-model",
                model_version="1.0.0",
                prompt_template="test",
                prompt_variables={},
                input_reference_type="speaker",
                input_reference_id=1,
            )
        ]
        mock_history_repository.get_by_input_reference.return_value = expected_history

        # Get history
        history = instrumented_service.get_processing_history("speaker", 1)

        # Verify
        assert len(history) == 1
        assert history[0].processing_type == ProcessingType.SPEAKER_MATCHING
        mock_history_repository.get_by_input_reference.assert_called_with("speaker", 1)

    def test_set_history_repository(self, mock_llm_service):
        """Test setting history repository."""
        service = InstrumentedLLMService(
            llm_service=mock_llm_service,
            history_repository=None,
            model_name="test-model",
            model_version="1.0.0",
        )

        # Initially no repository
        assert service._history_repository is None

        # Set repository
        new_repo = MagicMock(spec=LLMProcessingHistoryRepository)
        service.set_history_repository(new_repo)

        # Verify it was set
        assert service._history_repository == new_repo

    def test_extract_result_metadata(self, instrumented_service):
        """Test metadata extraction from results."""
        # Dict result with matching fields
        dict_result = {"matched": True, "confidence": 0.8, "other": "data"}
        metadata = instrumented_service._extract_result_metadata(dict_result)
        assert metadata["type"] == "dict"
        assert metadata["keys"] == ["matched", "confidence", "other"]
        assert metadata["matched"] is True
        assert metadata["confidence"] == 0.8

        # List result
        list_result = [1, 2, 3]
        metadata = instrumented_service._extract_result_metadata(list_result)
        assert metadata["type"] == "list"
        assert metadata["count"] == 3

        # None result
        metadata = instrumented_service._extract_result_metadata(None)
        assert metadata["type"] == "NoneType"
        assert metadata["is_null"] is True
