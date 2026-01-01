"""Tests for UpdateSpeakerFromExtractionUseCase."""

from unittest.mock import AsyncMock

import pytest

from src.application.dtos.extraction_result.speaker_extraction_result import (
    SpeakerExtractionResult,
)
from src.application.usecases.update_speaker_from_extraction_usecase import (
    UpdateSpeakerFromExtractionUseCase,
)
from src.domain.entities.extraction_log import EntityType, ExtractionLog
from src.domain.entities.speaker import Speaker


class TestUpdateSpeakerFromExtractionUseCase:
    """Test cases for UpdateSpeakerFromExtractionUseCase."""

    @pytest.fixture
    def mock_speaker_repo(self):
        """Create mock speaker repository."""
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
        self, mock_speaker_repo, mock_extraction_log_repo, mock_session_adapter
    ):
        """Create UpdateSpeakerFromExtractionUseCase instance."""
        return UpdateSpeakerFromExtractionUseCase(
            speaker_repo=mock_speaker_repo,
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.mark.asyncio
    async def test_update_speaker_success(
        self,
        use_case,
        mock_speaker_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """発言者の更新が成功する。"""
        # Setup
        speaker = Speaker(
            id=1,
            name="山田太郎",
            type="議員",
            political_party_name="新党A",
            is_manually_verified=False,
        )
        extraction_result = SpeakerExtractionResult(
            name="山田太郎",
            type="議員",
            political_party_name="新党B",
            position="委員長",
            is_politician=True,
            politician_id=100,
        )
        extraction_log = ExtractionLog(
            id=200,
            entity_type=EntityType.SPEAKER,
            entity_id=1,
            pipeline_version="v1.0",
            extracted_data=extraction_result.to_dict(),
        )

        mock_speaker_repo.get_by_id.return_value = speaker
        mock_extraction_log_repo.create.return_value = extraction_log

        # Execute
        result = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result,
            pipeline_version="v1.0",
        )

        # Assert
        assert result.updated is True
        assert result.extraction_log_id == 200

        # 発言者の各フィールドが更新されたことを確認
        assert speaker.name == "山田太郎"
        assert speaker.type == "議員"
        assert speaker.political_party_name == "新党B"
        assert speaker.position == "委員長"
        assert speaker.is_politician is True
        assert speaker.politician_id == 100
        assert speaker.latest_extraction_log_id == 200

        mock_speaker_repo.update.assert_called_once_with(speaker)
        mock_session_adapter.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_skip_update_when_manually_verified(
        self,
        use_case,
        mock_speaker_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """手動検証済みの発言者は更新がスキップされる。"""
        # Setup
        speaker = Speaker(
            id=1,
            name="山田太郎",
            political_party_name="新党A",
            is_manually_verified=True,
        )
        extraction_result = SpeakerExtractionResult(
            name="山田次郎",  # 異なる名前
            political_party_name="新党B",
        )
        extraction_log = ExtractionLog(
            id=200,
            entity_type=EntityType.SPEAKER,
            entity_id=1,
            pipeline_version="v1.0",
            extracted_data=extraction_result.to_dict(),
        )

        mock_speaker_repo.get_by_id.return_value = speaker
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

        # 発言者は更新されていないことを確認
        assert speaker.name == "山田太郎"  # 元の名前のまま
        assert speaker.political_party_name == "新党A"  # 元の政党名のまま

        mock_speaker_repo.update.assert_not_called()
        mock_session_adapter.commit.assert_not_called()
