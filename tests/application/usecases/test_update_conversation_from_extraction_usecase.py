"""Tests for UpdateConversationFromExtractionUseCase."""

from unittest.mock import AsyncMock

import pytest

from src.application.dtos.extraction_result.conversation_extraction_result import (
    ConversationExtractionResult,
)
from src.application.usecases.update_conversation_from_extraction_usecase import (
    UpdateConversationFromExtractionUseCase,
)
from src.domain.entities.conversation import Conversation
from src.domain.entities.extraction_log import EntityType, ExtractionLog


class TestUpdateConversationFromExtractionUseCase:
    """Test cases for UpdateConversationFromExtractionUseCase."""

    @pytest.fixture
    def mock_conversation_repo(self):
        """Create mock conversation repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_extraction_log_repo(self):
        """Create mock extraction log repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_session_adapter(self):
        """Create mock session adapter."""
        adapter = AsyncMock()
        return adapter

    @pytest.fixture
    def use_case(
        self, mock_conversation_repo, mock_extraction_log_repo, mock_session_adapter
    ):
        """Create UpdateConversationFromExtractionUseCase instance."""
        return UpdateConversationFromExtractionUseCase(
            conversation_repo=mock_conversation_repo,
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.mark.asyncio
    async def test_update_conversation_success(
        self,
        use_case,
        mock_conversation_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """発言の更新が成功する。"""
        # Setup
        conversation = Conversation(
            id=1,
            comment="古い発言内容",
            sequence_number=1,
            speaker_name="山田太郎",
            is_manually_verified=False,
        )
        extraction_result = ConversationExtractionResult(
            comment="新しい発言内容",
            sequence_number=1,
            speaker_name="山田太郎",
            speaker_id=100,
            chapter_number=2,
            sub_chapter_number=3,
            minutes_id=50,
        )
        extraction_log = ExtractionLog(
            id=300,
            entity_type=EntityType.STATEMENT,
            entity_id=1,
            pipeline_version="v1.0",
            extracted_data=extraction_result.to_dict(),
        )

        mock_conversation_repo.get_by_id.return_value = conversation
        mock_extraction_log_repo.create.return_value = extraction_log

        # Execute
        result = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result,
            pipeline_version="v1.0",
        )

        # Assert
        assert result.updated is True
        assert result.extraction_log_id == 300

        # 発言の各フィールドが更新されたことを確認
        assert conversation.comment == "新しい発言内容"
        assert conversation.sequence_number == 1
        assert conversation.speaker_name == "山田太郎"
        assert conversation.speaker_id == 100
        assert conversation.chapter_number == 2
        assert conversation.sub_chapter_number == 3
        assert conversation.minutes_id == 50
        assert conversation.latest_extraction_log_id == 300

        mock_conversation_repo.update.assert_called_once_with(conversation)
        mock_session_adapter.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_skip_update_when_manually_verified(
        self,
        use_case,
        mock_conversation_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """手動検証済みの発言は更新がスキップされる。"""
        # Setup
        conversation = Conversation(
            id=1,
            comment="元の発言内容",
            sequence_number=1,
            is_manually_verified=True,
        )
        extraction_result = ConversationExtractionResult(
            comment="新しい発言内容",
            sequence_number=1,
        )
        extraction_log = ExtractionLog(
            id=300,
            entity_type=EntityType.STATEMENT,
            entity_id=1,
            pipeline_version="v1.0",
            extracted_data=extraction_result.to_dict(),
        )

        mock_conversation_repo.get_by_id.return_value = conversation
        mock_extraction_log_repo.create.return_value = extraction_log

        # Execute
        result = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result,
            pipeline_version="v1.0",
        )

        # Assert
        assert result.updated is False
        assert result.reason == "manually_verified"

        # 発言は更新されていないことを確認
        assert conversation.comment == "元の発言内容"  # 元の内容のまま

        mock_conversation_repo.update.assert_not_called()
        mock_session_adapter.commit.assert_not_called()
