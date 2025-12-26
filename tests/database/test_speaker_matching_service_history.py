"""Tests for speaker matching service history recording functionality."""

# Skip entire module - legacy code removed during Clean Architecture migration
# ChainFactory was removed - speaker matching now uses MatchSpeakersUseCase
# ruff: noqa: E402

import pytest


pytestmark = pytest.mark.skip(reason="Legacy tests - ChainFactory removed")

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

from src.domain.services.speaker_matching_service import SpeakerMatchingService


# Type aliases for shorter lines
MockGen = Generator[MagicMock]


class TestSpeakerMatchingServiceHistory:
    """Test cases for speaker matching service history recording."""

    @pytest.fixture
    def mock_llm_service(self) -> MagicMock:
        """Mock LLM service."""
        mock = MagicMock()
        mock.model_name = "gemini-1.5-flash"
        return mock

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Mock database session."""
        return MagicMock()

    @pytest.fixture
    def mock_history_helper(self) -> MockGen:
        """Mock history helper."""
        with patch(
            "src.domain.services.speaker_matching_service.SyncLLMHistoryHelper"
        ) as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance
            yield mock_instance

    @patch("src.domain.services.speaker_matching_service.get_db_session")
    @patch("src.domain.services.speaker_matching_service.ChainFactory")
    def test_init_with_history_enabled(
        self,
        mock_chain_factory: MagicMock,
        mock_get_session: MagicMock,
        mock_llm_service: MagicMock,
        mock_history_helper: MagicMock,
    ) -> None:
        """Test initialization with history enabled."""
        mock_get_session.return_value = MagicMock()

        service = SpeakerMatchingService(
            llm_service=mock_llm_service, enable_history=True
        )

        assert service.history_helper is not None
        assert service.model_name == "gemini-1.5-flash"

    @patch("src.domain.services.speaker_matching_service.get_db_session")
    @patch("src.domain.services.speaker_matching_service.ChainFactory")
    def test_init_with_history_disabled(
        self,
        mock_chain_factory: Any,
        mock_get_session: Any,
        mock_llm_service: Any,
    ) -> None:
        """Test initialization with history disabled."""
        mock_get_session.return_value = MagicMock()

        service = SpeakerMatchingService(
            llm_service=mock_llm_service, enable_history=False
        )

        assert service.history_helper is None

    @patch("src.domain.services.speaker_matching_service.get_db_session")
    @patch("src.domain.services.speaker_matching_service.ChainFactory")
    def test_find_best_match_records_history_on_success(
        self,
        mock_chain_factory: Any,
        mock_get_session: Any,
        mock_llm_service: Any,
    ) -> None:
        """Test that successful matching records history."""
        # Setup mocks
        mock_get_session.return_value = MagicMock()
        mock_chain = MagicMock()
        mock_chain_factory.return_value.create_speaker_matching_chain.return_value = (
            mock_chain
        )
        mock_chain_factory.return_value.invoke_with_retry.return_value = {
            "matched": True,
            "speaker_id": 123,
            "speaker_name": "山田太郎",
            "confidence": 0.95,
            "reason": "完全一致",
        }

        # Create service with mocked history helper
        with patch(
            "src.domain.services.speaker_matching_service.SyncLLMHistoryHelper"
        ) as mock_helper_class:
            mock_history_instance = MagicMock()
            mock_helper_class.return_value = mock_history_instance

            service = SpeakerMatchingService(
                llm_service=mock_llm_service, enable_history=True
            )

            # Mock available speakers
            mock_get_speakers = MagicMock(
                return_value=[{"id": 123, "name": "山田太郎"}]
            )
            service._get_available_speakers = mock_get_speakers  # type: ignore[misc]

            # Call the method with a name that won't match with rule-based
            # to ensure LLM matching is used
            result = service.find_best_match("山田委員長")

            # Verify result
            assert result.matched is True
            assert result.speaker_id == 123
            assert result.confidence == 0.95

            # Verify history was recorded
            mock_history_instance.record_speaker_matching.assert_called_once_with(
                speaker_name="山田委員長",
                matched=True,
                speaker_id=123,
                confidence=0.95,
                reason="完全一致",
                model_name="gemini-1.5-flash",
                prompt_template="speaker_matching",
            )

    @patch("src.domain.services.speaker_matching_service.get_db_session")
    @patch("src.domain.services.speaker_matching_service.ChainFactory")
    def test_find_best_match_records_history_on_no_match(
        self,
        mock_chain_factory: Any,
        mock_get_session: Any,
        mock_llm_service: Any,
    ) -> None:
        """Test that no match also records history."""
        mock_get_session.return_value = MagicMock()
        mock_chain = MagicMock()
        mock_chain_factory.return_value.create_speaker_matching_chain.return_value = (
            mock_chain
        )
        mock_chain_factory.return_value.invoke_with_retry.return_value = {
            "matched": False,
            "speaker_id": None,
            "speaker_name": None,
            "confidence": 0.3,
            "reason": "一致する発言者が見つかりません",
        }

        with patch(
            "src.domain.services.speaker_matching_service.SyncLLMHistoryHelper"
        ) as mock_helper_class:
            mock_history_instance = MagicMock()
            mock_helper_class.return_value = mock_history_instance

            service = SpeakerMatchingService(
                llm_service=mock_llm_service, enable_history=True
            )

            mock_get_speakers = MagicMock(return_value=[{"id": 1, "name": "別の人"}])
            service._get_available_speakers = mock_get_speakers  # type: ignore[misc]

            result = service.find_best_match("未知の発言者")

            assert result.matched is False
            assert result.speaker_id is None

            # History should still be recorded
            mock_history_instance.record_speaker_matching.assert_called_once()
            call_args = mock_history_instance.record_speaker_matching.call_args
            assert call_args.kwargs["matched"] is False
            assert call_args.kwargs["speaker_id"] is None
            assert call_args.kwargs["confidence"] == 0.3

    @patch("src.domain.services.speaker_matching_service.get_db_session")
    @patch("src.domain.services.speaker_matching_service.ChainFactory")
    def test_history_recording_failure_does_not_break_main_flow(
        self,
        mock_chain_factory: Any,
        mock_get_session: Any,
        mock_llm_service: Any,
    ) -> None:
        """Test that history recording failure doesn't break the main operation."""
        mock_get_session.return_value = MagicMock()
        mock_chain = MagicMock()
        mock_chain_factory.return_value.create_speaker_matching_chain.return_value = (
            mock_chain
        )
        mock_chain_factory.return_value.invoke_with_retry.return_value = {
            "matched": True,
            "speaker_id": 123,
            "speaker_name": "山田太郎",
            "confidence": 0.95,
            "reason": "完全一致",
        }

        with patch(
            "src.domain.services.speaker_matching_service.SyncLLMHistoryHelper"
        ) as mock_helper_class:
            mock_history_instance = MagicMock()
            # Make history recording raise an exception
            mock_history_instance.record_speaker_matching.side_effect = Exception(
                "History DB error"
            )
            mock_helper_class.return_value = mock_history_instance

            service = SpeakerMatchingService(
                llm_service=mock_llm_service, enable_history=True
            )

            mock_get_speakers = MagicMock(
                return_value=[{"id": 123, "name": "山田太郎"}]
            )
            service._get_available_speakers = mock_get_speakers  # type: ignore[misc]

            # Should not raise exception
            result = service.find_best_match("山田太郎")

            # Result should still be valid
            assert result.matched is True
            assert result.speaker_id == 123

    @patch("src.domain.services.speaker_matching_service.get_db_session")
    @patch("src.domain.services.speaker_matching_service.ChainFactory")
    def test_batch_update_closes_history_helper(
        self,
        mock_chain_factory: Any,
        mock_get_session: Any,
        mock_llm_service: Any,
    ) -> None:
        """Test that batch update closes history helper in finally block."""
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Mock query results
        mock_session.execute.return_value.fetchall.return_value = []

        with patch(
            "src.domain.services.speaker_matching_service.SyncLLMHistoryHelper"
        ) as mock_helper_class:
            mock_history_instance = MagicMock()
            mock_helper_class.return_value = mock_history_instance

            service = SpeakerMatchingService(
                llm_service=mock_llm_service, enable_history=True
            )

            # Call batch update
            service.batch_update_speaker_links()

            # Verify history helper was closed
            mock_history_instance.close.assert_called_once()

    @patch("src.domain.services.speaker_matching_service.get_db_session")
    @patch("src.domain.services.speaker_matching_service.ChainFactory")
    def test_low_confidence_match_still_records_history(
        self,
        mock_chain_factory: Any,
        mock_get_session: Any,
        mock_llm_service: Any,
    ) -> None:
        """Test that low confidence matches (< 0.8) still record history."""
        mock_get_session.return_value = MagicMock()
        mock_chain = MagicMock()
        mock_chain_factory.return_value.create_speaker_matching_chain.return_value = (
            mock_chain
        )

        # Return a match with confidence below threshold
        mock_chain_factory.return_value.invoke_with_retry.return_value = {
            "matched": True,
            "speaker_id": 123,
            "speaker_name": "山田太郎",
            "confidence": 0.7,  # Below 0.8 threshold
            "reason": "部分一致",
        }

        with patch(
            "src.domain.services.speaker_matching_service.SyncLLMHistoryHelper"
        ) as mock_helper_class:
            mock_history_instance = MagicMock()
            mock_helper_class.return_value = mock_history_instance

            service = SpeakerMatchingService(
                llm_service=mock_llm_service, enable_history=True
            )

            mock_get_speakers = MagicMock(
                return_value=[{"id": 123, "name": "山田太郎"}]
            )
            service._get_available_speakers = mock_get_speakers  # type: ignore[misc]

            result = service.find_best_match("山田")

            # Result should be marked as not matched due to low confidence
            assert result.matched is False
            assert result.speaker_id is None

            # But history should still be recorded with the original values
            mock_history_instance.record_speaker_matching.assert_called_once_with(
                speaker_name="山田",
                matched=False,  # After threshold check
                speaker_id=None,  # After threshold check
                confidence=0.7,
                reason="部分一致",
                model_name="gemini-1.5-flash",
                prompt_template="speaker_matching",
            )
