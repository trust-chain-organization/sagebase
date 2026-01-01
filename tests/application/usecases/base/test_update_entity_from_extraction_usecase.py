"""Tests for UpdateEntityFromExtractionUseCase."""

from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from src.application.usecases.base.update_entity_from_extraction_usecase import (
    UpdateEntityFromExtractionUseCase,
)
from src.domain.entities.extraction_log import EntityType, ExtractionLog
from src.domain.entities.politician import Politician


@dataclass
class TestExtractionResult:
    """テスト用の抽出結果DTO。"""

    name: str
    value: str

    def to_dict(self) -> dict:
        return {"name": self.name, "value": self.value}


class TestUpdateEntityUseCase(
    UpdateEntityFromExtractionUseCase[Politician, TestExtractionResult]
):
    """テスト用の具体的なUseCase実装。"""

    def __init__(self, entity_repo, extraction_log_repo, session_adapter) -> None:  # type: ignore
        super().__init__(extraction_log_repo, session_adapter)
        self._entity_repo = entity_repo

    def _get_entity_type(self) -> EntityType:
        return EntityType.POLITICIAN

    async def _get_entity(self, entity_id: int) -> Politician | None:
        return await self._entity_repo.get_by_id(entity_id)

    async def _save_entity(self, entity: Politician) -> None:
        await self._entity_repo.update(entity)

    def _to_extracted_data(self, result: TestExtractionResult) -> dict:
        return result.to_dict()

    async def _apply_extraction(
        self, entity: Politician, result: TestExtractionResult, log_id: int
    ) -> None:
        entity.name = result.name
        entity.update_from_extraction_log(log_id)


class TestUpdateEntityFromExtractionUseCase:
    """Test cases for UpdateEntityFromExtractionUseCase."""

    @pytest.fixture
    def mock_entity_repo(self):
        """Create mock entity repository."""
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
        self, mock_entity_repo, mock_extraction_log_repo, mock_session_adapter
    ):
        """Create UpdateEntityUseCase instance."""
        return TestUpdateEntityUseCase(
            entity_repo=mock_entity_repo,
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.mark.asyncio
    async def test_update_success_when_not_manually_verified(
        self,
        use_case,
        mock_entity_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """手動検証されていないエンティティは更新が成功する。"""
        # Setup
        entity = Politician(
            id=1,
            name="旧名前",
            is_manually_verified=False,
            latest_extraction_log_id=None,
        )
        extraction_result = TestExtractionResult(name="新名前", value="test_value")
        extraction_log = ExtractionLog(
            id=100,
            entity_type=EntityType.POLITICIAN,
            entity_id=1,
            pipeline_version="v1.0",
            extracted_data={"name": "新名前", "value": "test_value"},
        )

        mock_entity_repo.get_by_id.return_value = entity
        mock_extraction_log_repo.create.return_value = extraction_log

        # Execute
        result = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result,
            pipeline_version="v1.0",
        )

        # Assert
        assert result.updated is True
        assert result.reason is None
        assert result.extraction_log_id == 100

        # 抽出ログが保存されたことを確認
        mock_extraction_log_repo.create.assert_called_once()

        # エンティティが更新されたことを確認
        mock_entity_repo.update.assert_called_once_with(entity)
        assert entity.name == "新名前"
        assert entity.latest_extraction_log_id == 100

        # トランザクションがコミットされたことを確認
        mock_session_adapter.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_skip_update_when_manually_verified(
        self,
        use_case,
        mock_entity_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """手動検証済みエンティティは更新がスキップされる。"""
        # Setup
        entity = Politician(
            id=1,
            name="旧名前",
            is_manually_verified=True,
            latest_extraction_log_id=50,
        )
        extraction_result = TestExtractionResult(name="新名前", value="test_value")
        extraction_log = ExtractionLog(
            id=100,
            entity_type=EntityType.POLITICIAN,
            entity_id=1,
            pipeline_version="v1.0",
            extracted_data={"name": "新名前", "value": "test_value"},
        )

        mock_entity_repo.get_by_id.return_value = entity
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
        assert result.extraction_log_id == 100

        # 抽出ログは保存されたことを確認
        mock_extraction_log_repo.create.assert_called_once()

        # エンティティは更新されていないことを確認
        mock_entity_repo.update.assert_not_called()
        assert entity.name == "旧名前"  # 名前は変更されていない
        assert entity.latest_extraction_log_id == 50  # ログIDも変更されていない

        # トランザクションはコミットされていないことを確認
        mock_session_adapter.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_return_entity_not_found_when_entity_does_not_exist(
        self,
        use_case,
        mock_entity_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """エンティティが存在しない場合、entity_not_foundが返される。"""
        # Setup
        extraction_result = TestExtractionResult(name="新名前", value="test_value")
        extraction_log = ExtractionLog(
            id=100,
            entity_type=EntityType.POLITICIAN,
            entity_id=999,
            pipeline_version="v1.0",
            extracted_data={"name": "新名前", "value": "test_value"},
        )

        mock_entity_repo.get_by_id.return_value = None
        mock_extraction_log_repo.create.return_value = extraction_log

        # Execute
        result = await use_case.execute(
            entity_id=999,
            extraction_result=extraction_result,
            pipeline_version="v1.0",
        )

        # Assert
        assert result.updated is False
        assert result.reason == "entity_not_found"
        assert result.extraction_log_id == 100

        # 抽出ログは保存されたことを確認
        mock_extraction_log_repo.create.assert_called_once()

        # エンティティの更新は試行されていないことを確認
        mock_entity_repo.update.assert_not_called()

        # トランザクションはコミットされていないことを確認
        mock_session_adapter.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_extraction_log_is_always_saved(
        self,
        use_case,
        mock_entity_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """更新の成否に関わらず、抽出ログは必ず保存される。"""
        # Setup: 手動検証済みのエンティティ（更新されない）
        entity = Politician(
            id=1,
            name="旧名前",
            is_manually_verified=True,
            latest_extraction_log_id=None,
        )
        extraction_result = TestExtractionResult(name="新名前", value="test_value")
        extraction_log = ExtractionLog(
            id=100,
            entity_type=EntityType.POLITICIAN,
            entity_id=1,
            pipeline_version="v1.0",
            extracted_data={"name": "新名前", "value": "test_value"},
        )

        mock_entity_repo.get_by_id.return_value = entity
        mock_extraction_log_repo.create.return_value = extraction_log

        # Execute
        await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result,
            pipeline_version="v1.0",
        )

        # Assert: 抽出ログは保存されたことを確認
        mock_extraction_log_repo.create.assert_called_once()

        # 抽出ログの内容を確認
        call_args = mock_extraction_log_repo.create.call_args
        saved_log = call_args[0][0]
        assert saved_log.entity_type == EntityType.POLITICIAN
        assert saved_log.entity_id == 1
        assert saved_log.pipeline_version == "v1.0"
        assert saved_log.extracted_data == {"name": "新名前", "value": "test_value"}

    @pytest.mark.asyncio
    async def test_rollback_on_error(
        self,
        use_case,
        mock_entity_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """エラー発生時にロールバックされる。"""
        # Setup
        entity = Politician(
            id=1,
            name="旧名前",
            is_manually_verified=False,
            latest_extraction_log_id=None,
        )
        extraction_result = TestExtractionResult(name="新名前", value="test_value")
        extraction_log = ExtractionLog(
            id=100,
            entity_type=EntityType.POLITICIAN,
            entity_id=1,
            pipeline_version="v1.0",
            extracted_data={"name": "新名前", "value": "test_value"},
        )

        mock_entity_repo.get_by_id.return_value = entity
        mock_extraction_log_repo.create.return_value = extraction_log
        # updateでエラーを発生させる
        mock_entity_repo.update.side_effect = Exception("Database error")

        # Execute & Assert
        with pytest.raises(Exception, match="Database error"):
            await use_case.execute(
                entity_id=1,
                extraction_result=extraction_result,
                pipeline_version="v1.0",
            )

        # ロールバックが呼ばれたことを確認
        mock_session_adapter.rollback.assert_called_once()
        # コミットは呼ばれていないことを確認
        mock_session_adapter.commit.assert_not_called()
