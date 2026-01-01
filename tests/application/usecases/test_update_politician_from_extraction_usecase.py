"""Tests for UpdatePoliticianFromExtractionUseCase."""

from unittest.mock import AsyncMock

import pytest

from src.application.dtos.extraction_result.politician_extraction_result import (
    PoliticianExtractionResult,
)
from src.application.usecases.update_politician_from_extraction_usecase import (
    UpdatePoliticianFromExtractionUseCase,
)
from src.domain.entities.extraction_log import EntityType, ExtractionLog
from src.domain.entities.politician import Politician


class TestUpdatePoliticianFromExtractionUseCase:
    """Test cases for UpdatePoliticianFromExtractionUseCase."""

    @pytest.fixture
    def mock_politician_repo(self):
        """Create mock politician repository."""
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
        self, mock_politician_repo, mock_extraction_log_repo, mock_session_adapter
    ):
        """Create UpdatePoliticianFromExtractionUseCase instance."""
        return UpdatePoliticianFromExtractionUseCase(
            politician_repo=mock_politician_repo,
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.mark.asyncio
    async def test_update_politician_success(
        self,
        use_case,
        mock_politician_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """政治家の更新が成功する。"""
        # Setup
        politician = Politician(
            id=1,
            name="山田太郎",
            furigana="やまだたろう",
            political_party_id=1,
            district="東京1区",
            is_manually_verified=False,
        )
        extraction_result = PoliticianExtractionResult(
            name="山田太郎",
            furigana="やまだたろう",
            political_party_id=2,
            district="東京2区",
            profile_page_url="https://example.com/yamada",
            party_position="幹事長",
        )
        extraction_log = ExtractionLog(
            id=100,
            entity_type=EntityType.POLITICIAN,
            entity_id=1,
            pipeline_version="v1.0",
            extracted_data=extraction_result.to_dict(),
        )

        mock_politician_repo.get_by_id.return_value = politician
        mock_extraction_log_repo.create.return_value = extraction_log

        # Execute
        result = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result,
            pipeline_version="v1.0",
        )

        # Assert
        assert result.updated is True
        assert result.extraction_log_id == 100

        # 政治家の各フィールドが更新されたことを確認
        assert politician.name == "山田太郎"
        assert politician.furigana == "やまだたろう"
        assert politician.political_party_id == 2
        assert politician.district == "東京2区"
        assert politician.profile_page_url == "https://example.com/yamada"
        assert politician.party_position == "幹事長"
        assert politician.latest_extraction_log_id == 100

        mock_politician_repo.update.assert_called_once_with(politician)
        mock_session_adapter.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_skip_update_when_manually_verified(
        self,
        use_case,
        mock_politician_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """手動検証済みの政治家は更新がスキップされる。"""
        # Setup
        politician = Politician(
            id=1,
            name="山田太郎",
            political_party_id=1,
            is_manually_verified=True,
        )
        extraction_result = PoliticianExtractionResult(
            name="山田次郎",  # 異なる名前
            political_party_id=2,
        )
        extraction_log = ExtractionLog(
            id=100,
            entity_type=EntityType.POLITICIAN,
            entity_id=1,
            pipeline_version="v1.0",
            extracted_data=extraction_result.to_dict(),
        )

        mock_politician_repo.get_by_id.return_value = politician
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

        # 政治家は更新されていないことを確認
        assert politician.name == "山田太郎"  # 元の名前のまま
        assert politician.political_party_id == 1  # 元の政党IDのまま

        mock_politician_repo.update.assert_not_called()
        mock_session_adapter.commit.assert_not_called()
