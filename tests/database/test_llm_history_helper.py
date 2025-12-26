"""Tests for LLM history helper."""

import json
from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.persistence.llm_history_helper import SyncLLMHistoryHelper


# Type aliases for shorter lines
MockGen = Generator[MagicMock]


class TestSyncLLMHistoryHelper:
    """Test cases for SyncLLMHistoryHelper."""

    @pytest.fixture
    def mock_settings(self) -> MockGen:
        """Mock settings."""
        with patch(
            "src.infrastructure.persistence.llm_history_helper.settings"
        ) as mock:
            mock.get_database_url.return_value = "sqlite:///:memory:"
            yield mock

    @pytest.fixture
    def helper(self, mock_settings: MagicMock) -> SyncLLMHistoryHelper:
        """Create helper instance with mocked settings."""
        return SyncLLMHistoryHelper()

    def test_init_creates_engine_and_session_maker(self, mock_settings: Any) -> None:
        """Test that initialization creates engine and session maker."""
        helper = SyncLLMHistoryHelper()

        assert helper.engine is not None
        assert helper.session_maker is not None
        mock_settings.get_database_url.assert_called_once()

    def test_record_speaker_matching_success(self, helper: Any) -> None:
        """Test successful recording of speaker matching."""
        # Mock session and its methods
        mock_session = MagicMock()
        mock_execute = MagicMock()
        mock_session.execute = mock_execute
        mock_session.commit = MagicMock()
        mock_session.rollback = MagicMock()
        mock_session.close = MagicMock()

        # Replace session maker with mock
        helper.session_maker = MagicMock(return_value=mock_session)

        # Call the method
        helper.record_speaker_matching(
            speaker_name="山田太郎",
            matched=True,
            speaker_id=123,
            confidence=0.95,
            reason="完全一致",
            model_name="gemini-1.5-flash",
            prompt_template="speaker_matching",
        )

        # Verify session methods were called
        assert mock_execute.called
        assert mock_session.commit.called
        assert not mock_session.rollback.called
        assert mock_session.close.called

        # Verify the SQL query and data
        call_args = mock_execute.call_args
        query = call_args[0][0]
        data = call_args[0][1]

        # Check query type
        assert hasattr(query, "text")  # It's a text() query

        # Check data contents
        assert data["processing_type"] == "speaker_matching"
        assert data["model_name"] == "gemini-1.5-flash"
        assert data["model_version"] == "1.5"
        assert data["prompt_template"] == "speaker_matching"
        assert data["input_reference_type"] == "speaker_name"
        assert data["status"] == "completed"

        # Check JSON fields
        prompt_vars = json.loads(data["prompt_variables"])
        assert prompt_vars["speaker_name"] == "山田太郎"

        metadata = json.loads(data["processing_metadata"])
        assert metadata["matched"] is True
        assert metadata["speaker_id"] == 123
        assert metadata["confidence"] == 0.95
        assert metadata["reason"] == "完全一致"

        # token_usage field has been removed from the implementation

    def test_record_speaker_matching_no_match(self, helper: Any) -> None:
        """Test recording when no match is found."""
        mock_session = MagicMock()
        helper.session_maker = MagicMock(return_value=mock_session)

        helper.record_speaker_matching(
            speaker_name="未知の発言者",
            matched=False,
            speaker_id=None,
            confidence=0.0,
            reason="一致なし",
        )

        # Get the data that was passed to execute
        data = mock_session.execute.call_args[0][1]

        # Check that None values are handled correctly
        metadata = json.loads(data["processing_metadata"])
        assert metadata["matched"] is False
        assert metadata["speaker_id"] is None
        assert metadata["confidence"] == 0.0
        assert metadata["reason"] == "一致なし"

    def test_record_speaker_matching_database_error(self, helper: Any) -> None:
        """Test that database errors are handled gracefully."""
        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("Database error")
        helper.session_maker = MagicMock(return_value=mock_session)

        # Should not raise exception
        helper.record_speaker_matching(
            speaker_name="テスト",
            matched=True,
            speaker_id=1,
            confidence=0.8,
            reason="テスト",
        )

        # Verify rollback was called
        assert mock_session.rollback.called
        assert mock_session.close.called

    def test_close_disposes_engine(self, helper: Any) -> None:
        """Test that close method disposes the engine."""
        mock_dispose = MagicMock()
        helper.engine.dispose = mock_dispose

        helper.close()

        assert mock_dispose.called

    def test_context_manager(self, mock_settings: MagicMock) -> None:
        """Test that helper works as a context manager."""
        with SyncLLMHistoryHelper() as helper:
            assert helper is not None
            assert helper.engine is not None

        # Engine should be disposed after context exit
        # (In real implementation, engine.dispose() would be called)

    def test_hash_function_consistency(self, helper: Any) -> None:
        """Test that the hash function produces consistent results."""
        mock_session = MagicMock()
        helper.session_maker = MagicMock(return_value=mock_session)

        # Record same speaker name twice
        speaker_name = "委員長(平山たかお)"

        helper.record_speaker_matching(
            speaker_name=speaker_name,
            matched=True,
            speaker_id=1,
            confidence=0.9,
            reason="一致",
        )

        helper.record_speaker_matching(
            speaker_name=speaker_name,
            matched=True,
            speaker_id=1,
            confidence=0.9,
            reason="一致",
        )

        # Get the reference IDs from both calls
        call1_data = mock_session.execute.call_args_list[0][0][1]
        call2_data = mock_session.execute.call_args_list[1][0][1]

        # Hash should be consistent
        assert call1_data["input_reference_id"] == call2_data["input_reference_id"]

    def test_datetime_fields(self, helper: Any) -> None:
        """Test that datetime fields are properly set."""
        mock_session = MagicMock()
        helper.session_maker = MagicMock(return_value=mock_session)

        # Record with current time
        before_time = datetime.now(UTC)

        helper.record_speaker_matching(
            speaker_name="テスト",
            matched=True,
            speaker_id=1,
            confidence=0.8,
            reason="テスト",
        )

        after_time = datetime.now(UTC)

        # Get the data
        data = mock_session.execute.call_args[0][1]

        # Check datetime fields
        assert isinstance(data["started_at"], datetime)
        assert isinstance(data["completed_at"], datetime)
        assert before_time <= data["started_at"] <= after_time
        assert before_time <= data["completed_at"] <= after_time
