"""MarkEntityAsVerifiedUseCaseの単体テスト。"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.usecases.mark_entity_as_verified_usecase import (
    EntityType,
    MarkEntityAsVerifiedInputDto,
    MarkEntityAsVerifiedUseCase,
)
from src.domain.entities import Politician


class TestMarkEntityAsVerifiedUseCase:
    """MarkEntityAsVerifiedUseCaseのテスト。"""

    @pytest.fixture
    def mock_politician_repo(self) -> MagicMock:
        """政治家リポジトリのモック。"""
        return MagicMock()

    @pytest.fixture
    def mock_conversation_repo(self) -> MagicMock:
        """発言リポジトリのモック。"""
        return MagicMock()

    @pytest.fixture
    def mock_conference_member_repo(self) -> MagicMock:
        """会議体メンバーリポジトリのモック。"""
        return MagicMock()

    @pytest.fixture
    def mock_parliamentary_group_member_repo(self) -> MagicMock:
        """議員団メンバーリポジトリのモック。"""
        return MagicMock()

    @pytest.fixture
    def usecase(
        self,
        mock_politician_repo: MagicMock,
        mock_conversation_repo: MagicMock,
        mock_conference_member_repo: MagicMock,
        mock_parliamentary_group_member_repo: MagicMock,
    ) -> MarkEntityAsVerifiedUseCase:
        """UseCaseのインスタンス。"""
        return MarkEntityAsVerifiedUseCase(
            politician_repository=mock_politician_repo,
            conversation_repository=mock_conversation_repo,
            conference_member_repository=mock_conference_member_repo,
            parliamentary_group_member_repository=mock_parliamentary_group_member_repo,
        )

    @pytest.mark.asyncio
    async def test_mark_politician_as_verified_success(
        self,
        usecase: MarkEntityAsVerifiedUseCase,
        mock_politician_repo: MagicMock,
    ) -> None:
        """政治家を手動検証済みにマーク成功のテスト。"""
        # Arrange
        politician = Politician(id=1, name="テスト政治家")
        mock_politician_repo.get_by_id = AsyncMock(return_value=politician)
        mock_politician_repo.update = AsyncMock()

        input_dto = MarkEntityAsVerifiedInputDto(
            entity_type=EntityType.POLITICIAN,
            entity_id=1,
            is_verified=True,
        )

        # Act
        result = await usecase.execute(input_dto)

        # Assert
        assert result.success is True
        assert result.error_message is None
        assert politician.is_manually_verified is True
        mock_politician_repo.get_by_id.assert_called_once_with(1)
        mock_politician_repo.update.assert_called_once_with(politician)

    @pytest.mark.asyncio
    async def test_mark_politician_as_unverified_success(
        self,
        usecase: MarkEntityAsVerifiedUseCase,
        mock_politician_repo: MagicMock,
    ) -> None:
        """政治家の手動検証済みを解除するテスト。"""
        # Arrange
        politician = Politician(id=1, name="テスト政治家")
        politician.mark_as_manually_verified()
        assert politician.is_manually_verified is True

        mock_politician_repo.get_by_id = AsyncMock(return_value=politician)
        mock_politician_repo.update = AsyncMock()

        input_dto = MarkEntityAsVerifiedInputDto(
            entity_type=EntityType.POLITICIAN,
            entity_id=1,
            is_verified=False,
        )

        # Act
        result = await usecase.execute(input_dto)

        # Assert
        assert result.success is True
        assert result.error_message is None
        assert politician.is_manually_verified is False

    @pytest.mark.asyncio
    async def test_mark_politician_not_found(
        self,
        usecase: MarkEntityAsVerifiedUseCase,
        mock_politician_repo: MagicMock,
    ) -> None:
        """政治家が見つからない場合のテスト。"""
        # Arrange
        mock_politician_repo.get_by_id = AsyncMock(return_value=None)

        input_dto = MarkEntityAsVerifiedInputDto(
            entity_type=EntityType.POLITICIAN,
            entity_id=999,
            is_verified=True,
        )

        # Act
        result = await usecase.execute(input_dto)

        # Assert
        assert result.success is False
        assert result.error_message == "政治家が見つかりません。"

    @pytest.mark.asyncio
    async def test_repository_not_configured(self) -> None:
        """リポジトリが未設定の場合のテスト。"""
        # Arrange
        usecase = MarkEntityAsVerifiedUseCase()  # リポジトリなしで作成

        input_dto = MarkEntityAsVerifiedInputDto(
            entity_type=EntityType.POLITICIAN,
            entity_id=1,
            is_verified=True,
        )

        # Act
        result = await usecase.execute(input_dto)

        # Assert
        assert result.success is False
        assert "not configured" in result.error_message  # type: ignore[operator]

    @pytest.mark.asyncio
    async def test_repository_error_handling(
        self,
        usecase: MarkEntityAsVerifiedUseCase,
        mock_politician_repo: MagicMock,
    ) -> None:
        """リポジトリエラー時のハンドリングテスト。"""
        # Arrange
        mock_politician_repo.get_by_id = AsyncMock(
            side_effect=Exception("Database error")
        )

        input_dto = MarkEntityAsVerifiedInputDto(
            entity_type=EntityType.POLITICIAN,
            entity_id=1,
            is_verified=True,
        )

        # Act
        result = await usecase.execute(input_dto)

        # Assert
        assert result.success is False
        assert "Database error" in result.error_message  # type: ignore[operator]
