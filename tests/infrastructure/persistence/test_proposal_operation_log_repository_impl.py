"""ProposalOperationLogRepositoryImplのテスト."""

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.proposal_operation_log import (
    ProposalOperationLog,
    ProposalOperationType,
)
from src.infrastructure.persistence.proposal_operation_log_repository_impl import (
    ProposalOperationLogModel,
    ProposalOperationLogRepositoryImpl,
)


class TestProposalOperationLogRepositoryImpl:
    """ProposalOperationLogRepositoryImplのテストスイート."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """モックAsyncSessionを作成."""
        session = MagicMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> ProposalOperationLogRepositoryImpl:
        """リポジトリインスタンスを作成."""
        return ProposalOperationLogRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_log_dict(self) -> dict[str, Any]:
        """サンプルログデータを辞書として作成."""
        return {
            "id": 1,
            "proposal_id": 42,
            "proposal_title": "テスト議案",
            "operation_type": "create",
            "user_id": "12345678-1234-5678-1234-567812345678",
            "operation_details": {"key": "value"},
            "operated_at": datetime(2024, 1, 15, 10, 30, 0),
        }

    def test_to_entity(self, repository: ProposalOperationLogRepositoryImpl) -> None:
        """_to_entity変換のテスト."""
        model = ProposalOperationLogModel(
            id=1,
            proposal_id=42,
            proposal_title="テスト議案",
            operation_type="create",
            user_id=None,
            operation_details={"key": "value"},
            operated_at=datetime(2024, 1, 15, 10, 30, 0),
        )

        entity = repository._to_entity(model)

        assert entity.id == 1
        assert entity.proposal_id == 42
        assert entity.proposal_title == "テスト議案"
        assert entity.operation_type == ProposalOperationType.CREATE
        assert entity.user_id is None
        assert entity.operation_details == {"key": "value"}
        assert entity.operated_at == datetime(2024, 1, 15, 10, 30, 0)

    def test_to_model(self, repository: ProposalOperationLogRepositoryImpl) -> None:
        """_to_model変換のテスト."""
        entity = ProposalOperationLog(
            id=1,
            proposal_id=42,
            proposal_title="テスト議案",
            operation_type=ProposalOperationType.UPDATE,
            user_id=None,
            operation_details={"old": "value", "new": "value2"},
            operated_at=datetime(2024, 1, 15, 10, 30, 0),
        )

        model = repository._to_model(entity)

        assert model.id == 1
        assert model.proposal_id == 42
        assert model.proposal_title == "テスト議案"
        assert model.operation_type == "update"
        assert model.user_id is None
        assert model.operation_details == {"old": "value", "new": "value2"}
        assert model.operated_at == datetime(2024, 1, 15, 10, 30, 0)

    def test_update_model(self, repository: ProposalOperationLogRepositoryImpl) -> None:
        """_update_modelのテスト."""
        model = ProposalOperationLogModel(
            id=1,
            proposal_id=1,
            proposal_title="古いタイトル",
            operation_type="create",
            user_id=None,
            operation_details={},
            operated_at=datetime(2024, 1, 1, 0, 0, 0),
        )
        entity = ProposalOperationLog(
            id=1,
            proposal_id=42,
            proposal_title="新しいタイトル",
            operation_type=ProposalOperationType.DELETE,
            user_id=None,
            operation_details={"reason": "test"},
            operated_at=datetime(2024, 1, 15, 10, 30, 0),
        )

        repository._update_model(model, entity)

        assert model.proposal_id == 42
        assert model.proposal_title == "新しいタイトル"
        assert model.operation_type == "delete"
        assert model.operation_details == {"reason": "test"}
        assert model.operated_at == datetime(2024, 1, 15, 10, 30, 0)

    @pytest.mark.asyncio
    async def test_create_success(
        self,
        repository: ProposalOperationLogRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """createメソッドの成功テスト."""
        # Arrange
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (
            1,  # id
            42,  # proposal_id
            "テスト議案",  # proposal_title
            "create",  # operation_type
            None,  # user_id
            {},  # operation_details
            datetime(2024, 1, 15, 10, 30, 0),  # operated_at
        )
        mock_session.execute.return_value = mock_result

        entity = ProposalOperationLog(
            proposal_id=42,
            proposal_title="テスト議案",
            operation_type=ProposalOperationType.CREATE,
            operated_at=datetime(2024, 1, 15, 10, 30, 0),
        )

        # Act
        result = await repository.create(entity)

        # Assert
        assert result.id == 1
        assert result.proposal_id == 42
        assert result.proposal_title == "テスト議案"
        assert result.operation_type == ProposalOperationType.CREATE
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_with_user_id(
        self,
        repository: ProposalOperationLogRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """user_id付きのcreateテスト."""
        from uuid import UUID

        user_id = UUID("12345678-1234-5678-1234-567812345678")

        mock_result = MagicMock()
        mock_result.fetchone.return_value = (
            1,
            42,
            "テスト議案",
            "create",
            str(user_id),
            {},
            datetime(2024, 1, 15, 10, 30, 0),
        )
        mock_session.execute.return_value = mock_result

        entity = ProposalOperationLog(
            proposal_id=42,
            proposal_title="テスト議案",
            operation_type=ProposalOperationType.CREATE,
            user_id=user_id,
            operated_at=datetime(2024, 1, 15, 10, 30, 0),
        )

        result = await repository.create(entity)

        assert result.user_id == user_id

    @pytest.mark.asyncio
    async def test_create_failure_raises_runtime_error(
        self,
        repository: ProposalOperationLogRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """createがNoneを返した場合にRuntimeErrorが発生することを確認."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result

        entity = ProposalOperationLog(
            proposal_id=42,
            proposal_title="テスト議案",
            operation_type=ProposalOperationType.CREATE,
        )

        with pytest.raises(
            RuntimeError, match="Failed to create proposal operation log"
        ):
            await repository.create(entity)

    @pytest.mark.asyncio
    async def test_find_by_user_without_user_id(
        self,
        repository: ProposalOperationLogRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """user_idなしでのfind_by_userテスト（全件取得）."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (1, 42, "議案1", "create", None, {}, datetime(2024, 1, 15, 10, 0, 0)),
            (2, 43, "議案2", "update", None, {}, datetime(2024, 1, 14, 10, 0, 0)),
        ]
        mock_session.execute.return_value = mock_result

        results = await repository.find_by_user(user_id=None)

        assert len(results) == 2
        assert results[0].id == 1
        assert results[0].proposal_id == 42
        assert results[1].id == 2
        assert results[1].proposal_id == 43

    @pytest.mark.asyncio
    async def test_find_by_user_with_user_id(
        self,
        repository: ProposalOperationLogRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """user_id指定でのfind_by_userテスト."""
        from uuid import UUID

        user_id = UUID("12345678-1234-5678-1234-567812345678")

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (
                1,
                42,
                "議案1",
                "create",
                str(user_id),
                {},
                datetime(2024, 1, 15, 10, 0, 0),
            ),
        ]
        mock_session.execute.return_value = mock_result

        results = await repository.find_by_user(user_id=user_id)

        assert len(results) == 1
        assert results[0].user_id == user_id

    @pytest.mark.asyncio
    async def test_find_by_filters_all_filters(
        self,
        repository: ProposalOperationLogRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """全フィルタ指定でのfind_by_filtersテスト."""
        from uuid import UUID

        user_id = UUID("12345678-1234-5678-1234-567812345678")
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (
                1,
                42,
                "議案1",
                "create",
                str(user_id),
                {},
                datetime(2024, 1, 15, 10, 0, 0),
            ),
        ]
        mock_session.execute.return_value = mock_result

        results = await repository.find_by_filters(
            user_id=user_id,
            operation_type=ProposalOperationType.CREATE,
            start_date=start_date,
            end_date=end_date,
        )

        assert len(results) == 1
        assert results[0].operation_type == ProposalOperationType.CREATE

    @pytest.mark.asyncio
    async def test_find_by_filters_no_filters(
        self,
        repository: ProposalOperationLogRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """フィルタなしでのfind_by_filtersテスト."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result

        results = await repository.find_by_filters()

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_get_statistics_by_user(
        self,
        repository: ProposalOperationLogRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """get_statistics_by_userテスト."""
        from uuid import UUID

        user_id_1 = UUID("12345678-1234-5678-1234-567812345678")
        user_id_2 = UUID("87654321-4321-8765-4321-876543218765")

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (str(user_id_1), 10),
            (str(user_id_2), 5),
        ]
        mock_session.execute.return_value = mock_result

        results = await repository.get_statistics_by_user()

        assert len(results) == 2
        assert results[user_id_1] == 10
        assert results[user_id_2] == 5

    @pytest.mark.asyncio
    async def test_get_statistics_by_user_with_filters(
        self,
        repository: ProposalOperationLogRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """フィルタ付きget_statistics_by_userテスト."""
        from uuid import UUID

        user_id = UUID("12345678-1234-5678-1234-567812345678")
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (str(user_id), 3),
        ]
        mock_session.execute.return_value = mock_result

        results = await repository.get_statistics_by_user(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )

        assert len(results) == 1
        assert results[user_id] == 3

    @pytest.mark.asyncio
    async def test_get_timeline_statistics(
        self,
        repository: ProposalOperationLogRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """get_timeline_statisticsテスト."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (datetime(2024, 1, 1), 5),
            (datetime(2024, 1, 2), 3),
        ]
        mock_session.execute.return_value = mock_result

        results = await repository.get_timeline_statistics()

        assert len(results) == 2
        assert results[0]["date"] == "2024-01-01"
        assert results[0]["count"] == 5
        assert results[1]["date"] == "2024-01-02"
        assert results[1]["count"] == 3

    @pytest.mark.asyncio
    async def test_get_timeline_statistics_with_interval(
        self,
        repository: ProposalOperationLogRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """interval指定でのget_timeline_statisticsテスト."""
        from uuid import UUID

        user_id = UUID("12345678-1234-5678-1234-567812345678")

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (datetime(2024, 1, 1), 10),
        ]
        mock_session.execute.return_value = mock_result

        results = await repository.get_timeline_statistics(
            user_id=user_id,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            interval="week",
        )

        assert len(results) == 1
        assert results[0]["count"] == 10


class TestProposalOperationLogModel:
    """ProposalOperationLogModelのテスト."""

    def test_model_creation(self) -> None:
        """モデル作成のテスト."""
        model = ProposalOperationLogModel(
            id=1,
            proposal_id=42,
            proposal_title="テスト議案",
            operation_type="create",
            user_id=None,
            operation_details={"key": "value"},
            operated_at=datetime(2024, 1, 15, 10, 30, 0),
        )

        assert model.id == 1
        assert model.proposal_id == 42
        assert model.proposal_title == "テスト議案"
        assert model.operation_type == "create"
        assert model.user_id is None
        assert model.operation_details == {"key": "value"}
        assert model.operated_at == datetime(2024, 1, 15, 10, 30, 0)

    def test_model_with_uuid_user_id(self) -> None:
        """UUID形式のuser_idを持つモデルのテスト."""
        from uuid import UUID

        user_id = UUID("12345678-1234-5678-1234-567812345678")

        model = ProposalOperationLogModel(
            id=1,
            proposal_id=42,
            proposal_title="テスト議案",
            operation_type="update",
            user_id=user_id,
            operation_details=None,
            operated_at=datetime(2024, 1, 15, 10, 30, 0),
        )

        assert model.user_id == user_id
