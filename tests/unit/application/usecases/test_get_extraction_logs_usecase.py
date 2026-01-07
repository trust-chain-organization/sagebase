"""GetExtractionLogsUseCaseの単体テスト。"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.dtos.extraction_log_dto import (
    ExtractionLogFilterDTO,
)
from src.application.usecases.get_extraction_logs_usecase import (
    GetExtractionLogsUseCase,
)
from src.domain.entities.extraction_log import EntityType, ExtractionLog


class TestGetExtractionLogsUseCase:
    """GetExtractionLogsUseCaseのテスト。"""

    @pytest.fixture
    def mock_repo(self) -> MagicMock:
        """抽出ログリポジトリのモック。"""
        return MagicMock()

    @pytest.fixture
    def usecase(self, mock_repo: MagicMock) -> GetExtractionLogsUseCase:
        """UseCaseのインスタンス。"""
        return GetExtractionLogsUseCase(extraction_log_repository=mock_repo)

    @pytest.fixture
    def sample_logs(self) -> list[ExtractionLog]:
        """テスト用の抽出ログリスト。"""
        return [
            ExtractionLog(
                id=1,
                entity_type=EntityType.POLITICIAN,
                entity_id=100,
                pipeline_version="gemini-2.0-flash-v1",
                extracted_data={"name": "テスト政治家"},
                confidence_score=0.95,
                extraction_metadata={"model_name": "gemini-2.0-flash"},
            ),
            ExtractionLog(
                id=2,
                entity_type=EntityType.SPEAKER,
                entity_id=200,
                pipeline_version="gemini-2.0-flash-v1",
                extracted_data={"speaker_name": "テスト話者"},
                confidence_score=0.85,
                extraction_metadata={"model_name": "gemini-2.0-flash"},
            ),
        ]

    @pytest.mark.asyncio
    async def test_execute_success(
        self,
        usecase: GetExtractionLogsUseCase,
        mock_repo: MagicMock,
        sample_logs: list[ExtractionLog],
    ) -> None:
        """抽出ログ検索成功のテスト。"""
        # Arrange
        mock_repo.search_with_date_range = AsyncMock(return_value=sample_logs)
        mock_repo.count_with_filters = AsyncMock(return_value=2)

        filter_dto = ExtractionLogFilterDTO(
            entity_type=EntityType.POLITICIAN,
            limit=10,
            offset=0,
        )

        # Act
        result = await usecase.execute(filter_dto)

        # Assert
        assert len(result.logs) == 2
        assert result.total_count == 2
        assert result.page_size == 10
        assert result.current_offset == 0
        mock_repo.search_with_date_range.assert_called_once()
        mock_repo.count_with_filters.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_date_range(
        self,
        usecase: GetExtractionLogsUseCase,
        mock_repo: MagicMock,
        sample_logs: list[ExtractionLog],
    ) -> None:
        """日時範囲付き検索のテスト。"""
        # Arrange
        mock_repo.search_with_date_range = AsyncMock(return_value=sample_logs)
        mock_repo.count_with_filters = AsyncMock(return_value=2)

        date_from = datetime.now() - timedelta(days=7)
        date_to = datetime.now()

        filter_dto = ExtractionLogFilterDTO(
            date_from=date_from,
            date_to=date_to,
            limit=25,
            offset=0,
        )

        # Act
        result = await usecase.execute(filter_dto)

        # Assert
        assert len(result.logs) == 2
        mock_repo.search_with_date_range.assert_called_once_with(
            entity_type=None,
            entity_id=None,
            pipeline_version=None,
            min_confidence_score=None,
            date_from=date_from,
            date_to=date_to,
            limit=25,
            offset=0,
        )

    @pytest.mark.asyncio
    async def test_execute_with_pipeline_version(
        self,
        usecase: GetExtractionLogsUseCase,
        mock_repo: MagicMock,
        sample_logs: list[ExtractionLog],
    ) -> None:
        """パイプラインバージョン指定検索のテスト。"""
        # Arrange
        mock_repo.search_with_date_range = AsyncMock(return_value=sample_logs)
        mock_repo.count_with_filters = AsyncMock(return_value=2)

        filter_dto = ExtractionLogFilterDTO(
            pipeline_version="gemini-2.0-flash-v1",
            limit=10,
            offset=0,
        )

        # Act
        result = await usecase.execute(filter_dto)

        # Assert
        assert len(result.logs) == 2
        mock_repo.search_with_date_range.assert_called_once()
        call_kwargs = mock_repo.search_with_date_range.call_args.kwargs
        assert call_kwargs["pipeline_version"] == "gemini-2.0-flash-v1"

    @pytest.mark.asyncio
    async def test_execute_empty_result(
        self,
        usecase: GetExtractionLogsUseCase,
        mock_repo: MagicMock,
    ) -> None:
        """検索結果が空の場合のテスト。"""
        # Arrange
        mock_repo.search_with_date_range = AsyncMock(return_value=[])
        mock_repo.count_with_filters = AsyncMock(return_value=0)

        filter_dto = ExtractionLogFilterDTO(
            entity_type=EntityType.STATEMENT,
            limit=10,
            offset=0,
        )

        # Act
        result = await usecase.execute(filter_dto)

        # Assert
        assert len(result.logs) == 0
        assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_execute_handles_exception(
        self,
        usecase: GetExtractionLogsUseCase,
        mock_repo: MagicMock,
    ) -> None:
        """例外発生時のエラーハンドリングテスト。"""
        # Arrange
        mock_repo.search_with_date_range = AsyncMock(
            side_effect=Exception("Database error")
        )

        filter_dto = ExtractionLogFilterDTO(limit=10, offset=0)

        # Act
        result = await usecase.execute(filter_dto)

        # Assert
        assert len(result.logs) == 0
        assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_get_statistics_success(
        self,
        usecase: GetExtractionLogsUseCase,
        mock_repo: MagicMock,
    ) -> None:
        """統計情報取得成功のテスト。"""
        # Arrange
        mock_repo.count_with_filters = AsyncMock(return_value=100)
        mock_repo.get_distinct_pipeline_versions = AsyncMock(
            return_value=["gemini-2.0-flash-v1"]
        )
        mock_repo.get_average_confidence_score = AsyncMock(return_value=0.85)
        mock_repo.get_count_by_date = AsyncMock(
            return_value=[
                (datetime(2024, 1, 1), 10),
                (datetime(2024, 1, 2), 15),
            ]
        )

        # Act
        result = await usecase.get_statistics()

        # Assert
        assert result.total_count == 100
        assert result.average_confidence == 0.85
        mock_repo.count_with_filters.assert_called()
        mock_repo.get_distinct_pipeline_versions.assert_called_once()
        mock_repo.get_average_confidence_score.assert_called()
        mock_repo.get_count_by_date.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_statistics_with_entity_type_filter(
        self,
        usecase: GetExtractionLogsUseCase,
        mock_repo: MagicMock,
    ) -> None:
        """エンティティタイプフィルタ付き統計情報取得のテスト。"""
        # Arrange
        mock_repo.count_with_filters = AsyncMock(return_value=50)
        mock_repo.get_distinct_pipeline_versions = AsyncMock(return_value=[])
        mock_repo.get_average_confidence_score = AsyncMock(return_value=0.90)
        mock_repo.get_count_by_date = AsyncMock(return_value=[])

        # Act
        result = await usecase.get_statistics(entity_type=EntityType.POLITICIAN)

        # Assert
        assert result.total_count == 50
        assert result.average_confidence == 0.90

    @pytest.mark.asyncio
    async def test_get_by_id_success(
        self,
        usecase: GetExtractionLogsUseCase,
        mock_repo: MagicMock,
        sample_logs: list[ExtractionLog],
    ) -> None:
        """ID指定でのログ取得成功のテスト。"""
        # Arrange
        log = sample_logs[0]
        mock_repo.get_by_id = AsyncMock(return_value=log)

        # Act
        result = await usecase.get_by_id(1)

        # Assert
        assert result is not None
        assert result.id == 1
        mock_repo.get_by_id.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        usecase: GetExtractionLogsUseCase,
        mock_repo: MagicMock,
    ) -> None:
        """存在しないIDでのログ取得のテスト。"""
        # Arrange
        mock_repo.get_by_id = AsyncMock(return_value=None)

        # Act
        result = await usecase.get_by_id(999)

        # Assert
        assert result is None
        mock_repo.get_by_id.assert_called_once_with(999)

    @pytest.mark.asyncio
    async def test_get_by_entity_success(
        self,
        usecase: GetExtractionLogsUseCase,
        mock_repo: MagicMock,
        sample_logs: list[ExtractionLog],
    ) -> None:
        """特定エンティティのログ取得成功のテスト。"""
        # Arrange
        mock_repo.get_by_entity = AsyncMock(return_value=[sample_logs[0]])

        # Act
        result = await usecase.get_by_entity(EntityType.POLITICIAN, 100)

        # Assert
        assert len(result) == 1
        assert result[0].entity_id == 100
        mock_repo.get_by_entity.assert_called_once_with(
            entity_type=EntityType.POLITICIAN,
            entity_id=100,
        )

    @pytest.mark.asyncio
    async def test_get_pipeline_versions_success(
        self,
        usecase: GetExtractionLogsUseCase,
        mock_repo: MagicMock,
    ) -> None:
        """パイプラインバージョン一覧取得成功のテスト。"""
        # Arrange
        versions = ["gemini-2.0-flash-v1", "gemini-1.5-flash-v1"]
        mock_repo.get_distinct_pipeline_versions = AsyncMock(return_value=versions)

        # Act
        result = await usecase.get_pipeline_versions()

        # Assert
        assert result == versions
        mock_repo.get_distinct_pipeline_versions.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_entity_types(
        self,
        usecase: GetExtractionLogsUseCase,
    ) -> None:
        """エンティティタイプ一覧取得のテスト。"""
        # Act
        result = await usecase.get_entity_types()

        # Assert
        assert "politician" in result
        assert "speaker" in result
        assert "statement" in result
        assert "conference_member" in result
        assert "parliamentary_group_member" in result
