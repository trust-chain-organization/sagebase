"""Tests for ManageParliamentaryGroupsUseCase."""

from unittest.mock import AsyncMock

import pytest

from src.application.usecases.manage_parliamentary_groups_usecase import (
    CreateParliamentaryGroupInputDto,
    CreateParliamentaryGroupOutputDto,
    DeleteParliamentaryGroupInputDto,
    DeleteParliamentaryGroupOutputDto,
    ManageParliamentaryGroupsUseCase,
    ParliamentaryGroupListInputDto,
    ParliamentaryGroupListOutputDto,
    UpdateParliamentaryGroupInputDto,
    UpdateParliamentaryGroupOutputDto,
)
from src.domain.entities.parliamentary_group import ParliamentaryGroup


class TestManageParliamentaryGroupsUseCase:
    """Test cases for ManageParliamentaryGroupsUseCase."""

    @pytest.fixture
    def mock_parliamentary_group_repository(self):
        """Create mock parliamentary group repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_membership_repository(self):
        """Create mock membership repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def use_case(self, mock_parliamentary_group_repository):
        """Create ManageParliamentaryGroupsUseCase instance."""
        return ManageParliamentaryGroupsUseCase(
            parliamentary_group_repository=mock_parliamentary_group_repository
        )

    @pytest.fixture
    def use_case_with_membership_repo(
        self, mock_parliamentary_group_repository, mock_membership_repository
    ):
        """Create UseCase instance with membership repository."""
        return ManageParliamentaryGroupsUseCase(
            parliamentary_group_repository=mock_parliamentary_group_repository,
            membership_repository=mock_membership_repository,
        )

    @pytest.mark.asyncio
    async def test_list_parliamentary_groups_success(
        self, use_case, mock_parliamentary_group_repository
    ):
        """Test listing parliamentary groups successfully."""
        # Arrange
        groups = [
            ParliamentaryGroup(
                id=1, name="自由民主党", conference_id=1, is_active=True
            ),
            ParliamentaryGroup(
                id=2, name="立憲民主党", conference_id=1, is_active=True
            ),
        ]
        mock_parliamentary_group_repository.get_all.return_value = groups

        input_dto = ParliamentaryGroupListInputDto()

        # Act
        result = await use_case.list_parliamentary_groups(input_dto)

        # Assert
        assert isinstance(result, ParliamentaryGroupListOutputDto)
        assert len(result.parliamentary_groups) == 2
        assert result.parliamentary_groups[0].name == "自由民主党"

    @pytest.mark.asyncio
    async def test_list_parliamentary_groups_filtered_by_conference(
        self, use_case, mock_parliamentary_group_repository
    ):
        """Test listing parliamentary groups filtered by conference."""
        # Arrange
        groups = [
            ParliamentaryGroup(
                id=1, name="自由民主党", conference_id=1, is_active=True
            ),
        ]
        mock_parliamentary_group_repository.get_by_conference_id.return_value = groups

        input_dto = ParliamentaryGroupListInputDto(conference_id=1)

        # Act
        result = await use_case.list_parliamentary_groups(input_dto)

        # Assert
        assert len(result.parliamentary_groups) == 1
        assert result.parliamentary_groups[0].conference_id == 1
        mock_parliamentary_group_repository.get_by_conference_id.assert_called_once_with(
            1, False
        )

    @pytest.mark.asyncio
    async def test_list_parliamentary_groups_active_only(
        self, use_case, mock_parliamentary_group_repository
    ):
        """Test listing active parliamentary groups only."""
        # Arrange
        active_group = ParliamentaryGroup(
            id=1, name="自由民主党", conference_id=1, is_active=True
        )
        inactive_group = ParliamentaryGroup(
            id=2, name="解散した会派", conference_id=1, is_active=False
        )
        all_groups = [active_group, inactive_group]
        mock_parliamentary_group_repository.get_all.return_value = all_groups

        input_dto = ParliamentaryGroupListInputDto(active_only=True)

        # Act
        result = await use_case.list_parliamentary_groups(input_dto)

        # Assert
        assert len(result.parliamentary_groups) == 1
        assert result.parliamentary_groups[0].is_active is True

    @pytest.mark.asyncio
    async def test_list_parliamentary_groups_empty(
        self, use_case, mock_parliamentary_group_repository
    ):
        """Test listing parliamentary groups when no groups exist."""
        # Arrange
        mock_parliamentary_group_repository.get_all.return_value = []

        input_dto = ParliamentaryGroupListInputDto()

        # Act
        result = await use_case.list_parliamentary_groups(input_dto)

        # Assert
        assert len(result.parliamentary_groups) == 0

    @pytest.mark.asyncio
    async def test_create_parliamentary_group_success(
        self, use_case, mock_parliamentary_group_repository
    ):
        """Test creating a parliamentary group successfully."""
        # Arrange
        mock_parliamentary_group_repository.get_by_name_and_conference.return_value = (
            None
        )
        created_group = ParliamentaryGroup(
            id=1,
            name="新しい会派",
            conference_id=1,
            url="https://example.com",
            description="テスト会派",
            is_active=True,
        )
        mock_parliamentary_group_repository.create.return_value = created_group

        input_dto = CreateParliamentaryGroupInputDto(
            name="新しい会派",
            conference_id=1,
            url="https://example.com",
            description="テスト会派",
            is_active=True,
        )

        # Act
        result = await use_case.create_parliamentary_group(input_dto)

        # Assert
        assert isinstance(result, CreateParliamentaryGroupOutputDto)
        assert result.success is True
        assert result.parliamentary_group is not None
        assert result.parliamentary_group.id == 1
        mock_parliamentary_group_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_parliamentary_group_duplicate_error(
        self, use_case, mock_parliamentary_group_repository
    ):
        """Test creating a parliamentary group with duplicate name."""
        # Arrange
        existing_group = ParliamentaryGroup(
            id=1, name="既存の会派", conference_id=1, is_active=True
        )
        mock_parliamentary_group_repository.get_by_name_and_conference.return_value = (
            existing_group
        )

        input_dto = CreateParliamentaryGroupInputDto(name="既存の会派", conference_id=1)

        # Act
        result = await use_case.create_parliamentary_group(input_dto)

        # Assert
        assert result.success is False
        assert "既に存在します" in result.error_message
        mock_parliamentary_group_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_parliamentary_group_repository_error(
        self, use_case, mock_parliamentary_group_repository
    ):
        """Test creating a parliamentary group with repository error."""
        # Arrange
        mock_parliamentary_group_repository.get_by_name_and_conference.return_value = (
            None
        )
        mock_parliamentary_group_repository.create.side_effect = Exception(
            "Database error"
        )

        input_dto = CreateParliamentaryGroupInputDto(name="新しい会派", conference_id=1)

        # Act
        result = await use_case.create_parliamentary_group(input_dto)

        # Assert
        assert result.success is False
        assert "Database error" in result.error_message

    @pytest.mark.asyncio
    async def test_update_parliamentary_group_success(
        self, use_case, mock_parliamentary_group_repository
    ):
        """Test updating a parliamentary group successfully."""
        # Arrange
        existing_group = ParliamentaryGroup(
            id=1, name="自由民主党", conference_id=1, is_active=True
        )
        mock_parliamentary_group_repository.get_by_id.return_value = existing_group

        input_dto = UpdateParliamentaryGroupInputDto(
            id=1,
            name="自由民主党（更新）",
            url="https://example.com/updated",
            description="更新された説明",
            is_active=True,
        )

        # Act
        result = await use_case.update_parliamentary_group(input_dto)

        # Assert
        assert isinstance(result, UpdateParliamentaryGroupOutputDto)
        assert result.success is True
        mock_parliamentary_group_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_parliamentary_group_not_found(
        self, use_case, mock_parliamentary_group_repository
    ):
        """Test updating a parliamentary group that does not exist."""
        # Arrange
        mock_parliamentary_group_repository.get_by_id.return_value = None

        input_dto = UpdateParliamentaryGroupInputDto(
            id=999, name="存在しない会派", is_active=True
        )

        # Act
        result = await use_case.update_parliamentary_group(input_dto)

        # Assert
        assert result.success is False
        assert "見つかりません" in result.error_message
        mock_parliamentary_group_repository.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_parliamentary_group_repository_error(
        self, use_case, mock_parliamentary_group_repository
    ):
        """Test updating a parliamentary group with repository error."""
        # Arrange
        existing_group = ParliamentaryGroup(
            id=1, name="自由民主党", conference_id=1, is_active=True
        )
        mock_parliamentary_group_repository.get_by_id.return_value = existing_group
        mock_parliamentary_group_repository.update.side_effect = Exception(
            "Database error"
        )

        input_dto = UpdateParliamentaryGroupInputDto(
            id=1, name="自由民主党", is_active=True
        )

        # Act
        result = await use_case.update_parliamentary_group(input_dto)

        # Assert
        assert result.success is False
        assert "Database error" in result.error_message

    @pytest.mark.asyncio
    async def test_delete_parliamentary_group_success(
        self, use_case, mock_parliamentary_group_repository
    ):
        """Test deleting a parliamentary group successfully."""
        # Arrange
        inactive_group = ParliamentaryGroup(
            id=1, name="解散した会派", conference_id=1, is_active=False
        )
        mock_parliamentary_group_repository.get_by_id.return_value = inactive_group

        input_dto = DeleteParliamentaryGroupInputDto(id=1)

        # Act
        result = await use_case.delete_parliamentary_group(input_dto)

        # Assert
        assert isinstance(result, DeleteParliamentaryGroupOutputDto)
        assert result.success is True
        mock_parliamentary_group_repository.delete.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_parliamentary_group_not_found(
        self, use_case, mock_parliamentary_group_repository
    ):
        """Test deleting a parliamentary group that does not exist."""
        # Arrange
        mock_parliamentary_group_repository.get_by_id.return_value = None

        input_dto = DeleteParliamentaryGroupInputDto(id=999)

        # Act
        result = await use_case.delete_parliamentary_group(input_dto)

        # Assert
        assert result.success is False
        assert "見つかりません" in result.error_message
        mock_parliamentary_group_repository.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_parliamentary_group_active_error(
        self, use_case, mock_parliamentary_group_repository
    ):
        """Test deleting an active parliamentary group."""
        # Arrange
        active_group = ParliamentaryGroup(
            id=1, name="自由民主党", conference_id=1, is_active=True
        )
        mock_parliamentary_group_repository.get_by_id.return_value = active_group

        input_dto = DeleteParliamentaryGroupInputDto(id=1)

        # Act
        result = await use_case.delete_parliamentary_group(input_dto)

        # Assert
        assert result.success is False
        assert "活動中の議員団は削除できません" in result.error_message
        mock_parliamentary_group_repository.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_parliamentary_group_repository_error(
        self, use_case, mock_parliamentary_group_repository
    ):
        """Test deleting a parliamentary group with repository error."""
        # Arrange
        inactive_group = ParliamentaryGroup(
            id=1, name="解散した会派", conference_id=1, is_active=False
        )
        mock_parliamentary_group_repository.get_by_id.return_value = inactive_group
        mock_parliamentary_group_repository.delete.side_effect = Exception(
            "Database error"
        )

        input_dto = DeleteParliamentaryGroupInputDto(id=1)

        # Act
        result = await use_case.delete_parliamentary_group(input_dto)

        # Assert
        assert result.success is False
        assert "Database error" in result.error_message

    @pytest.mark.asyncio
    async def test_delete_parliamentary_group_with_members_error(
        self,
        use_case_with_membership_repo,
        mock_parliamentary_group_repository,
        mock_membership_repository,
    ):
        """Test deleting a parliamentary group that has members."""
        # Arrange
        from datetime import date

        from src.domain.entities.parliamentary_group_membership import (
            ParliamentaryGroupMembership,
        )

        inactive_group = ParliamentaryGroup(
            id=1, name="解散した会派", conference_id=1, is_active=False
        )
        mock_parliamentary_group_repository.get_by_id.return_value = inactive_group

        # メンバーが存在する
        existing_members = [
            ParliamentaryGroupMembership(
                id=1,
                politician_id=100,
                parliamentary_group_id=1,
                start_date=date(2024, 1, 1),
            ),
            ParliamentaryGroupMembership(
                id=2,
                politician_id=101,
                parliamentary_group_id=1,
                start_date=date(2024, 1, 1),
            ),
        ]
        mock_membership_repository.get_by_group.return_value = existing_members

        input_dto = DeleteParliamentaryGroupInputDto(id=1)

        # Act
        result = await use_case_with_membership_repo.delete_parliamentary_group(
            input_dto
        )

        # Assert
        assert result.success is False
        assert "メンバーが所属している議員団は削除できません" in result.error_message
        mock_membership_repository.get_by_group.assert_called_once_with(1)
        mock_parliamentary_group_repository.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_parliamentary_group_no_members_success(
        self,
        use_case_with_membership_repo,
        mock_parliamentary_group_repository,
        mock_membership_repository,
    ):
        """Test deleting a parliamentary group with no members successfully."""
        # Arrange
        inactive_group = ParliamentaryGroup(
            id=1, name="解散した会派", conference_id=1, is_active=False
        )
        mock_parliamentary_group_repository.get_by_id.return_value = inactive_group

        # メンバーが存在しない
        mock_membership_repository.get_by_group.return_value = []

        input_dto = DeleteParliamentaryGroupInputDto(id=1)

        # Act
        result = await use_case_with_membership_repo.delete_parliamentary_group(
            input_dto
        )

        # Assert
        assert result.success is True
        mock_membership_repository.get_by_group.assert_called_once_with(1)
        mock_parliamentary_group_repository.delete.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_parliamentary_group_without_membership_repo_success(
        self, use_case, mock_parliamentary_group_repository
    ):
        """Test backward compatibility: deleting without membership repository."""
        # Arrange
        inactive_group = ParliamentaryGroup(
            id=1, name="解散した会派", conference_id=1, is_active=False
        )
        mock_parliamentary_group_repository.get_by_id.return_value = inactive_group

        input_dto = DeleteParliamentaryGroupInputDto(id=1)

        # Act
        result = await use_case.delete_parliamentary_group(input_dto)

        # Assert
        assert result.success is True
        mock_parliamentary_group_repository.delete.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_create_parliamentary_group_with_none_id(
        self, use_case, mock_parliamentary_group_repository
    ):
        """Issue #1036: 新規作成時にIDがNoneで渡されることを確認。

        シーケンス衝突を防ぐため、新規エンティティのIDはNoneである必要がある。
        """
        # Arrange
        mock_parliamentary_group_repository.get_by_name_and_conference.return_value = (
            None
        )
        created_group = ParliamentaryGroup(
            id=10,
            name="新しい会派",
            conference_id=1,
            url="https://example.com",
            description="テスト会派",
            is_active=True,
        )
        mock_parliamentary_group_repository.create.return_value = created_group

        input_dto = CreateParliamentaryGroupInputDto(
            name="新しい会派",
            conference_id=1,
            url="https://example.com",
            description="テスト会派",
            is_active=True,
        )

        # Act
        result = await use_case.create_parliamentary_group(input_dto)

        # Assert
        assert result.success is True
        # リポジトリに渡されるエンティティのIDがNoneであることを確認
        create_call = mock_parliamentary_group_repository.create.call_args
        created_entity = create_call[0][0]
        assert created_entity.id is None, "新規作成時のエンティティIDはNoneであるべき"
        assert created_entity.name == "新しい会派"
        assert created_entity.conference_id == 1

    @pytest.mark.asyncio
    async def test_create_multiple_parliamentary_groups_sequentially(
        self, use_case, mock_parliamentary_group_repository
    ):
        """Issue #1036: 連続して議員団を作成できることを確認。

        シーケンスが正しく機能している場合、連続作成でもIDが衝突しない。
        """
        # Arrange
        mock_parliamentary_group_repository.get_by_name_and_conference.return_value = (
            None
        )

        # 連続して異なるIDで作成される
        created_groups = [
            ParliamentaryGroup(
                id=i + 1,
                name=f"会派{i + 1}",
                conference_id=1,
                is_active=True,
            )
            for i in range(3)
        ]
        mock_parliamentary_group_repository.create.side_effect = created_groups

        # Act & Assert
        for i in range(3):
            input_dto = CreateParliamentaryGroupInputDto(
                name=f"会派{i + 1}",
                conference_id=1,
                is_active=True,
            )
            result = await use_case.create_parliamentary_group(input_dto)
            assert result.success is True
            assert result.parliamentary_group.id == i + 1

        # 3回呼び出されたことを確認
        assert mock_parliamentary_group_repository.create.call_count == 3
