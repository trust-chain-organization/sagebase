"""Integration test for minutes processing with LLM history recording."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.domain.entities.llm_processing_history import (
    LLMProcessingHistory,
    ProcessingStatus,
    ProcessingType,
)
from src.infrastructure.external.instrumented_llm_service import InstrumentedLLMService
from src.infrastructure.external.minutes_divider.baml_minutes_divider import (
    BAMLMinutesDivider,
)
from src.minutes_divide_processor.minutes_process_agent import MinutesProcessAgent
from src.services.llm_factory import LLMServiceFactory


class TestMinutesProcessingWithHistory:
    """Test minutes processing with LLM history recording."""

    @pytest.fixture
    def mock_llm_service(self):
        """Create a mock LLM service."""
        # Create a mock without spec to allow arbitrary attributes
        mock = Mock()

        # Mock the methods used by MinutesDivider
        mock.get_structured_llm = Mock(return_value=Mock())
        mock.get_prompt = Mock(return_value=Mock())
        mock.invoke_with_retry = Mock(
            return_value=Mock(
                section_info_list=[
                    Mock(chapter_number=1, keyword="開会"),
                    Mock(chapter_number=2, keyword="議事"),
                ]
            )
        )

        # Mock async methods required by ILLMService
        mock.set_history_repository = AsyncMock()
        mock.get_processing_history = AsyncMock(return_value=[])
        mock.match_speaker_to_politician = AsyncMock(return_value=None)
        mock.extract_speeches_from_text = AsyncMock(
            return_value=[
                {"speaker": "田中議員", "content": "本日の議題について説明します。"},
                {"speaker": "山田議員", "content": "質問があります。"},
            ]
        )
        mock.extract_party_members = AsyncMock(return_value=Mock())
        mock.match_conference_member = AsyncMock(return_value=None)

        return mock

    @pytest.fixture
    def mock_history_repository(self):
        """Create a mock history repository."""
        mock = AsyncMock()
        mock.create = AsyncMock(side_effect=lambda x: x)
        mock.update = AsyncMock()
        return mock

    @pytest.fixture
    def instrumented_llm_service(self, mock_llm_service, mock_history_repository):
        """Create an instrumented LLM service."""
        service = InstrumentedLLMService(
            llm_service=mock_llm_service,
            history_repository=mock_history_repository,
            model_name="gemini-2.0-flash-exp",
            model_version="latest",
            input_reference_type="meeting",
            input_reference_id=123,
        )
        return service

    def test_minutes_process_agent_with_instrumented_service(
        self, instrumented_llm_service
    ):
        """Test that MinutesProcessAgent works with InstrumentedLLMService."""
        # Create agent with instrumented service
        agent = MinutesProcessAgent(llm_service=instrumented_llm_service)

        # Verify it was initialized correctly - agent should have minutes_divider
        assert agent.minutes_divider is not None
        # Verify it's a BAML implementation
        assert agent.minutes_divider.__class__.__name__ == "BAMLMinutesDivider"

    @pytest.mark.asyncio
    async def test_history_recording_on_extract_speeches(
        self, instrumented_llm_service, mock_history_repository
    ):
        """Test that history is recorded when extracting speeches."""
        # Test text
        test_text = "これはテスト議事録です。"

        # Call extract_speeches_from_text (async method)
        await instrumented_llm_service.extract_speeches_from_text(test_text)

        # Verify history repository was called
        assert mock_history_repository.create.called
        assert mock_history_repository.update.called

        # Verify the history entry was created with correct data
        history_entry = mock_history_repository.create.call_args[0][0]
        assert isinstance(history_entry, LLMProcessingHistory)
        assert history_entry.processing_type == ProcessingType.SPEECH_EXTRACTION
        assert history_entry.model_name == "gemini-2.0-flash-exp"
        assert history_entry.input_reference_type == "meeting"
        assert history_entry.input_reference_id == 123

    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key"})
    def test_llm_factory_creates_instrumented_service(self):
        """Test that LLMServiceFactory creates InstrumentedLLMService by default."""
        factory = LLMServiceFactory()
        service = factory.create_advanced(temperature=0.0)

        # Verify it's an InstrumentedLLMService
        assert isinstance(service, InstrumentedLLMService)
        assert service._model_name == "gemini-2.0-flash-exp"

    def test_instrumented_service_delegation_methods(
        self, instrumented_llm_service, mock_llm_service
    ):
        """Test that delegation methods work correctly."""
        # Test get_structured_llm delegation
        schema = Mock()
        instrumented_llm_service.get_structured_llm(schema)
        mock_llm_service.get_structured_llm.assert_called_once_with(schema)

        # Test get_prompt delegation
        prompt_name = "test_prompt"
        instrumented_llm_service.get_prompt(prompt_name)
        mock_llm_service.get_prompt.assert_called_once_with(prompt_name)

        # Test invoke_with_retry delegation
        chain = Mock()
        inputs = {"test": "data"}
        instrumented_llm_service.invoke_with_retry(chain, inputs)
        mock_llm_service.invoke_with_retry.assert_called_once_with(chain, inputs)

    @pytest.mark.asyncio
    async def test_history_recording_handles_errors(
        self, mock_llm_service, mock_history_repository
    ):
        """Test that history recording handles errors gracefully."""
        # Configure LLM service to raise an error
        mock_llm_service.extract_speeches_from_text = Mock(
            side_effect=Exception("Test error")
        )

        # Create instrumented service
        service = InstrumentedLLMService(
            llm_service=mock_llm_service,
            history_repository=mock_history_repository,
            model_name="test-model",
            model_version="1.0",
        )

        # Call should raise the error
        with pytest.raises(Exception, match="Test error"):
            await service.extract_speeches_from_text("test")

        # But history should still be recorded with failed status
        assert mock_history_repository.create.called
        assert mock_history_repository.update.called

        # Check that the history was marked as failed
        update_call = mock_history_repository.update.call_args[0][0]
        assert update_call.status == ProcessingStatus.FAILED
        assert update_call.error_message == "Test error"

    def test_minutes_processing_without_history_repository(self, mock_llm_service):
        """Test that processing works even without history repository."""
        # Create service without history repository
        service = InstrumentedLLMService(
            llm_service=mock_llm_service,
            history_repository=None,  # No repository
            model_name="test-model",
        )

        # Create BAMLMinutesDivider - should work without errors
        divider = BAMLMinutesDivider(llm_service=service)
        assert divider.llm_service == service

        # Processing should work without history recording
        # (actual processing would happen here in a real test)

    def test_invoke_with_retry_records_history(
        self, mock_llm_service, mock_history_repository
    ):
        """Test that invoke_with_retry records history for minutes processing."""
        # Configure mock LLM service to return a result
        mock_result = Mock(
            section_info_list=[
                Mock(chapter_number=1, keyword="開会"),
                Mock(chapter_number=2, keyword="議事"),
            ]
        )
        mock_llm_service.invoke_with_retry = Mock(return_value=mock_result)

        # Create instrumented service with meeting context
        service = InstrumentedLLMService(
            llm_service=mock_llm_service,
            history_repository=mock_history_repository,
            model_name="gemini-2.0-flash-exp",
            model_version="latest",
            input_reference_type="meeting",
            input_reference_id=123,
        )

        # Create a mock chain
        mock_chain = Mock()
        mock_chain.first = Mock()
        mock_chain.first.template = "Test template for minutes division"

        # Call invoke_with_retry
        inputs = {"minutes": "テスト議事録"}
        result = service.invoke_with_retry(mock_chain, inputs)

        # Verify result
        assert result == mock_result

        # Verify history was recorded (called in sync context with run_until_complete)
        assert mock_history_repository.create.called
        assert mock_history_repository.update.called

        # Check the history entry
        history_entry = mock_history_repository.create.call_args[0][0]
        assert isinstance(history_entry, LLMProcessingHistory)
        assert history_entry.processing_type == ProcessingType.MINUTES_DIVISION
        assert history_entry.model_name == "gemini-2.0-flash-exp"
        assert history_entry.input_reference_type == "meeting"
        assert history_entry.input_reference_id == 123
        assert history_entry.prompt_variables == inputs

    def test_invoke_with_retry_handles_speech_extraction(
        self, mock_llm_service, mock_history_repository
    ):
        """Test that invoke_with_retry correctly identifies speech extraction."""
        # Configure mock
        mock_result = Mock(
            speaker_and_speech_content_list=[
                Mock(speaker="田中議員", content="発言内容", speech_order=1)
            ]
        )
        mock_llm_service.invoke_with_retry = Mock(return_value=mock_result)

        # Create instrumented service
        service = InstrumentedLLMService(
            llm_service=mock_llm_service,
            history_repository=mock_history_repository,
            model_name="gemini-2.0-flash-exp",
            model_version="latest",
            input_reference_type="meeting",
            input_reference_id=456,
        )

        # Create a mock chain with speech template
        mock_chain = Mock()
        mock_chain.first = Mock()
        mock_chain.first.template = "Extract speeches from section"

        # Call with section_string in inputs (indicates speech extraction)
        inputs = {"section_string": "議事録セクション"}
        result = service.invoke_with_retry(mock_chain, inputs)

        # Verify result
        assert result == mock_result

        # Check that it was recorded as speech extraction
        history_entry = mock_history_repository.create.call_args[0][0]
        assert history_entry.processing_type == ProcessingType.SPEECH_EXTRACTION
        assert history_entry.prompt_template == "speech_extraction"

    def test_invoke_with_retry_handles_errors_with_history(
        self, mock_llm_service, mock_history_repository
    ):
        """Test that invoke_with_retry records errors in history."""
        # Configure mock to raise error
        mock_llm_service.invoke_with_retry = Mock(
            side_effect=Exception("Processing failed")
        )

        # Create instrumented service
        service = InstrumentedLLMService(
            llm_service=mock_llm_service,
            history_repository=mock_history_repository,
            model_name="test-model",
            model_version="1.0",
            input_reference_type="meeting",
            input_reference_id=789,
        )

        # Call should raise the error
        with pytest.raises(Exception, match="Processing failed"):
            service.invoke_with_retry(Mock(), {"test": "data"})

        # Verify history was still recorded with failed status
        assert mock_history_repository.create.called
        assert mock_history_repository.update.called

        # Check that status was marked as failed
        update_call = mock_history_repository.update.call_args[0][0]
        assert update_call.status == ProcessingStatus.FAILED
        assert update_call.error_message == "Processing failed"
