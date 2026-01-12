"""Tests for ManagePoliticiansUseCase."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.usecases.manage_politicians_usecase import (
    CreatePoliticianInputDto,
    CreatePoliticianOutputDto,
    DeletePoliticianInputDto,
    DeletePoliticianOutputDto,
    ManagePoliticiansUseCase,
    MergePoliticiansInputDto,
    MergePoliticiansOutputDto,
    PoliticianListInputDto,
    PoliticianListOutputDto,
    UpdatePoliticianInputDto,
    UpdatePoliticianOutputDto,
)
from src.domain.entities.politician import Politician
from src.domain.entities.politician_operation_log import PoliticianOperationType


class TestManagePoliticiansUseCase:
    """Test cases for ManagePoliticiansUseCase."""

    @pytest.fixture
    def mock_politician_repository(self):
        """Create mock politician repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def use_case(self, mock_politician_repository):
        """Create ManagePoliticiansUseCase instance."""
        return ManagePoliticiansUseCase(
            politician_repository=mock_politician_repository
        )

    @pytest.mark.asyncio
    async def test_list_politicians_success(self, use_case, mock_politician_repository):
        """Test listing politicians successfully."""
        # Arrange
        politicians = [
            Politician(
                id=1,
                name="山田太郎",
                prefecture="東京都",
                district="東京1区",
                political_party_id=1,
            ),
            Politician(
                id=2,
                name="鈴木花子",
                prefecture="大阪府",
                district="大阪1区",
                political_party_id=2,
            ),
        ]
        mock_politician_repository.get_all.return_value = politicians

        input_dto = PoliticianListInputDto()

        # Act
        result = await use_case.list_politicians(input_dto)

        # Assert
        assert isinstance(result, PoliticianListOutputDto)
        assert len(result.politicians) == 2
        assert result.politicians[0].name == "山田太郎"
        assert result.politicians[1].name == "鈴木花子"

    @pytest.mark.asyncio
    async def test_list_politicians_filtered_by_party(
        self, use_case, mock_politician_repository
    ):
        """Test listing politicians filtered by party ID."""
        # Arrange
        politicians = [
            Politician(
                id=1,
                name="山田太郎",
                prefecture="東京都",
                district="東京1区",
                political_party_id=1,
            )
        ]
        mock_politician_repository.get_by_party.return_value = politicians

        input_dto = PoliticianListInputDto(party_id=1)

        # Act
        result = await use_case.list_politicians(input_dto)

        # Assert
        assert len(result.politicians) == 1
        assert result.politicians[0].political_party_id == 1

    @pytest.mark.asyncio
    async def test_list_politicians_empty(self, use_case, mock_politician_repository):
        """Test listing politicians when no politicians exist."""
        # Arrange
        mock_politician_repository.get_all.return_value = []

        input_dto = PoliticianListInputDto()

        # Act
        result = await use_case.list_politicians(input_dto)

        # Assert
        assert len(result.politicians) == 0

    @pytest.mark.asyncio
    async def test_create_politician_success(
        self, use_case, mock_politician_repository
    ):
        """Test creating a politician successfully."""
        # Arrange
        mock_politician_repository.get_by_name_and_party.return_value = None
        created_politician = Politician(
            id=1,
            name="田中次郎",
            prefecture="東京都",
            political_party_id=1,
            district="東京都第1区",
        )
        mock_politician_repository.create.return_value = created_politician

        input_dto = CreatePoliticianInputDto(
            name="田中次郎",
            prefecture="東京都",
            party_id=1,
            district="東京都第1区",
        )

        # Act
        result = await use_case.create_politician(input_dto)

        # Assert
        assert isinstance(result, CreatePoliticianOutputDto)
        assert result.success is True
        assert result.politician_id == 1
        mock_politician_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_politician_duplicate_error(
        self, use_case, mock_politician_repository
    ):
        """Test creating a politician with duplicate name and party."""
        # Arrange
        existing_politician = Politician(
            id=1,
            name="田中次郎",
            prefecture="東京都",
            district="東京1区",
            political_party_id=1,
        )
        mock_politician_repository.get_by_name_and_party.return_value = (
            existing_politician
        )

        input_dto = CreatePoliticianInputDto(
            name="田中次郎",
            prefecture="東京都",
            district="東京1区",
            party_id=1,
        )

        # Act
        result = await use_case.create_politician(input_dto)

        # Assert
        assert result.success is False
        assert "既に存在" in result.error_message
        mock_politician_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_politician_repository_error(
        self, use_case, mock_politician_repository
    ):
        """Test creating a politician when repository raises an error."""
        # Arrange
        mock_politician_repository.get_by_name_and_party.return_value = None
        mock_politician_repository.create.side_effect = Exception("Database error")

        input_dto = CreatePoliticianInputDto(
            name="田中次郎",
            prefecture="東京都",
            district="東京1区",
            party_id=1,
        )

        # Act
        result = await use_case.create_politician(input_dto)

        # Assert
        assert result.success is False
        assert "Database error" in result.error_message

    @pytest.mark.asyncio
    async def test_update_politician_success(
        self, use_case, mock_politician_repository
    ):
        """Test updating a politician successfully."""
        # Arrange
        existing_politician = Politician(
            id=1,
            name="山田太郎",
            prefecture="東京都",
            political_party_id=1,
            district="東京都第1区",
        )
        mock_politician_repository.get_by_id.return_value = existing_politician
        mock_politician_repository.update.return_value = existing_politician

        input_dto = UpdatePoliticianInputDto(
            id=1,
            name="山田太郎",
            prefecture="東京都",
            district="東京都第2区",
        )

        # Act
        result = await use_case.update_politician(input_dto)

        # Assert
        assert isinstance(result, UpdatePoliticianOutputDto)
        assert result.success is True
        mock_politician_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_politician_not_found(
        self, use_case, mock_politician_repository
    ):
        """Test updating a politician that does not exist."""
        # Arrange
        mock_politician_repository.get_by_id.return_value = None

        input_dto = UpdatePoliticianInputDto(
            id=999,
            name="不明な議員",
            prefecture="東京都",
            district="東京都第2区",
        )

        # Act
        result = await use_case.update_politician(input_dto)

        # Assert
        assert result.success is False
        assert "見つかりません" in result.error_message
        mock_politician_repository.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_politician_repository_error(
        self, use_case, mock_politician_repository
    ):
        """Test updating a politician when repository raises an error."""
        # Arrange
        existing_politician = Politician(
            id=1,
            name="山田太郎",
            prefecture="東京都",
            district="東京1区",
            political_party_id=1,
        )
        mock_politician_repository.get_by_id.return_value = existing_politician
        mock_politician_repository.update.side_effect = Exception("Update failed")

        input_dto = UpdatePoliticianInputDto(
            id=1,
            name="山田太郎",
            prefecture="東京都",
            district="東京都第2区",
        )

        # Act
        result = await use_case.update_politician(input_dto)

        # Assert
        assert result.success is False
        assert "Update failed" in result.error_message

    @pytest.mark.asyncio
    async def test_delete_politician_success(
        self, use_case, mock_politician_repository
    ):
        """Test deleting a politician successfully."""
        # Arrange
        existing_politician = Politician(
            id=1,
            name="山田太郎",
            prefecture="東京都",
            district="東京1区",
            political_party_id=1,
        )
        mock_politician_repository.get_by_id.return_value = existing_politician
        mock_politician_repository.delete.return_value = None

        input_dto = DeletePoliticianInputDto(id=1)

        # Act
        result = await use_case.delete_politician(input_dto)

        # Assert
        assert isinstance(result, DeletePoliticianOutputDto)
        assert result.success is True
        mock_politician_repository.delete.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_politician_not_found(
        self, use_case, mock_politician_repository
    ):
        """Test deleting a politician that does not exist."""
        # Arrange
        mock_politician_repository.get_by_id.return_value = None

        input_dto = DeletePoliticianInputDto(id=999)

        # Act
        result = await use_case.delete_politician(input_dto)

        # Assert
        assert result.success is False
        assert "見つかりません" in result.error_message
        mock_politician_repository.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_politician_repository_error(
        self, use_case, mock_politician_repository
    ):
        """Test deleting a politician when repository raises an error."""
        # Arrange
        existing_politician = Politician(
            id=1,
            name="山田太郎",
            prefecture="東京都",
            district="東京1区",
            political_party_id=1,
        )
        mock_politician_repository.get_by_id.return_value = existing_politician
        mock_politician_repository.delete.side_effect = Exception("Delete failed")

        input_dto = DeletePoliticianInputDto(id=1)

        # Act
        result = await use_case.delete_politician(input_dto)

        # Assert
        assert result.success is False
        assert "Delete failed" in result.error_message

    @pytest.mark.asyncio
    async def test_merge_politicians_not_implemented(
        self, use_case, mock_politician_repository
    ):
        """Test that merge functionality is not yet implemented."""
        # Arrange
        source_politician = Politician(
            id=1,
            name="山田太郎A",
            prefecture="東京都",
            district="東京1区",
            political_party_id=1,
        )
        target_politician = Politician(
            id=2,
            name="山田太郎B",
            prefecture="東京都",
            district="東京2区",
            political_party_id=1,
        )
        mock_politician_repository.get_by_id.side_effect = [
            source_politician,
            target_politician,
        ]

        input_dto = MergePoliticiansInputDto(
            source_id=1,
            target_id=2,
        )

        # Act
        result = await use_case.merge_politicians(input_dto)

        # Assert
        assert isinstance(result, MergePoliticiansOutputDto)
        assert result.success is False
        assert "実装中" in result.error_message

    @pytest.mark.asyncio
    async def test_merge_politicians_source_not_found(
        self, use_case, mock_politician_repository
    ):
        """Test merging politicians when source does not exist."""
        # Arrange
        mock_politician_repository.get_by_id.return_value = None

        input_dto = MergePoliticiansInputDto(
            source_id=999,
            target_id=2,
        )

        # Act
        result = await use_case.merge_politicians(input_dto)

        # Assert
        assert result.success is False
        assert "マージ元" in result.error_message

    @pytest.mark.asyncio
    async def test_merge_politicians_target_not_found(
        self, use_case, mock_politician_repository
    ):
        """Test merging politicians when target does not exist."""
        # Arrange
        source_politician = Politician(
            id=1,
            name="山田太郎A",
            prefecture="東京都",
            district="東京1区",
            political_party_id=1,
        )

        async def side_effect_func(politician_id):
            if politician_id == 1:
                return source_politician
            return None

        mock_politician_repository.get_by_id.side_effect = side_effect_func

        input_dto = MergePoliticiansInputDto(
            source_id=1,
            target_id=999,
        )

        # Act
        result = await use_case.merge_politicians(input_dto)

        # Assert
        assert result.success is False
        assert "マージ先" in result.error_message

    @pytest.mark.asyncio
    async def test_merge_politicians_repository_error(
        self, use_case, mock_politician_repository
    ):
        """Test merging politicians when repository raises an error."""
        # Arrange
        mock_politician_repository.get_by_id.side_effect = Exception("Database error")

        input_dto = MergePoliticiansInputDto(
            source_id=1,
            target_id=2,
        )

        # Act
        result = await use_case.merge_politicians(input_dto)

        # Assert
        assert result.success is False
        assert "Database error" in result.error_message


class TestManagePoliticiansUseCaseWithLogging:
    """Test cases for ManagePoliticiansUseCase with operation logging."""

    @pytest.fixture
    def mock_politician_repository(self):
        """Create mock politician repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_operation_log_repository(self):
        """Create mock operation log repository."""
        return AsyncMock()

    @pytest.fixture
    def use_case_with_logging(
        self, mock_politician_repository, mock_operation_log_repository
    ):
        """Create ManagePoliticiansUseCase with logging repository."""
        return ManagePoliticiansUseCase(
            politician_repository=mock_politician_repository,
            operation_log_repository=mock_operation_log_repository,
        )

    @pytest.mark.asyncio
    async def test_create_politician_logs_operation(
        self,
        use_case_with_logging,
        mock_politician_repository,
        mock_operation_log_repository,
    ):
        """Test that creating a politician logs the operation."""
        # Arrange
        user_id = uuid4()
        mock_politician_repository.get_by_name_and_party.return_value = None
        created_politician = Politician(
            id=1,
            name="田中次郎",
            prefecture="東京都",
            political_party_id=1,
            district="東京都第1区",
        )
        mock_politician_repository.create.return_value = created_politician

        input_dto = CreatePoliticianInputDto(
            name="田中次郎",
            prefecture="東京都",
            party_id=1,
            district="東京都第1区",
            user_id=user_id,
        )

        # Act
        result = await use_case_with_logging.create_politician(input_dto)

        # Assert
        assert result.success is True
        mock_operation_log_repository.create.assert_called_once()
        log_call = mock_operation_log_repository.create.call_args[0][0]
        assert log_call.politician_id == 1
        assert log_call.politician_name == "田中次郎"
        assert log_call.operation_type == PoliticianOperationType.CREATE
        assert log_call.user_id == user_id

    @pytest.mark.asyncio
    async def test_update_politician_logs_operation(
        self,
        use_case_with_logging,
        mock_politician_repository,
        mock_operation_log_repository,
    ):
        """Test that updating a politician logs the operation."""
        # Arrange
        user_id = uuid4()
        existing_politician = Politician(
            id=1,
            name="山田太郎",
            prefecture="東京都",
            political_party_id=1,
            district="東京都第1区",
        )
        mock_politician_repository.get_by_id.return_value = existing_politician
        mock_politician_repository.update.return_value = existing_politician

        input_dto = UpdatePoliticianInputDto(
            id=1,
            name="山田太郎",
            prefecture="神奈川県",
            district="神奈川1区",
            user_id=user_id,
        )

        # Act
        result = await use_case_with_logging.update_politician(input_dto)

        # Assert
        assert result.success is True
        mock_operation_log_repository.create.assert_called_once()
        log_call = mock_operation_log_repository.create.call_args[0][0]
        assert log_call.politician_id == 1
        assert log_call.politician_name == "山田太郎"
        assert log_call.operation_type == PoliticianOperationType.UPDATE
        assert log_call.user_id == user_id

    @pytest.mark.asyncio
    async def test_delete_politician_logs_operation(
        self,
        use_case_with_logging,
        mock_politician_repository,
        mock_operation_log_repository,
    ):
        """Test that deleting a politician logs the operation."""
        # Arrange
        user_id = uuid4()
        existing_politician = Politician(
            id=1,
            name="山田太郎",
            prefecture="東京都",
            political_party_id=1,
            district="東京1区",
        )
        mock_politician_repository.get_by_id.return_value = existing_politician

        input_dto = DeletePoliticianInputDto(id=1, user_id=user_id)

        # Act
        result = await use_case_with_logging.delete_politician(input_dto)

        # Assert
        assert result.success is True
        mock_operation_log_repository.create.assert_called_once()
        log_call = mock_operation_log_repository.create.call_args[0][0]
        assert log_call.politician_id == 1
        assert log_call.politician_name == "山田太郎"
        assert log_call.operation_type == PoliticianOperationType.DELETE
        assert log_call.user_id == user_id

    @pytest.mark.asyncio
    async def test_create_does_not_log_on_failure(
        self,
        use_case_with_logging,
        mock_politician_repository,
        mock_operation_log_repository,
    ):
        """Test that failed create operation does not log."""
        # Arrange
        existing_politician = Politician(
            id=1,
            name="田中次郎",
            prefecture="東京都",
            district="東京1区",
            political_party_id=1,
        )
        mock_politician_repository.get_by_name_and_party.return_value = (
            existing_politician
        )

        input_dto = CreatePoliticianInputDto(
            name="田中次郎",
            prefecture="東京都",
            district="東京1区",
            party_id=1,
        )

        # Act
        result = await use_case_with_logging.create_politician(input_dto)

        # Assert
        assert result.success is False
        mock_operation_log_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_log_failure_does_not_affect_main_operation(
        self,
        use_case_with_logging,
        mock_politician_repository,
        mock_operation_log_repository,
    ):
        """Test that log failure does not affect the main operation."""
        # Arrange
        mock_politician_repository.get_by_name_and_party.return_value = None
        created_politician = Politician(
            id=1,
            name="田中次郎",
            prefecture="東京都",
            political_party_id=1,
            district="東京都第1区",
        )
        mock_politician_repository.create.return_value = created_politician
        mock_operation_log_repository.create.side_effect = Exception("Log failed")

        input_dto = CreatePoliticianInputDto(
            name="田中次郎",
            prefecture="東京都",
            party_id=1,
            district="東京都第1区",
        )

        # Act
        result = await use_case_with_logging.create_politician(input_dto)

        # Assert - main operation should still succeed
        assert result.success is True
        assert result.politician_id == 1

    @pytest.mark.asyncio
    async def test_usecase_without_log_repository_still_works(
        self, mock_politician_repository
    ):
        """Test that UseCase works without operation log repository."""
        # Arrange
        use_case = ManagePoliticiansUseCase(
            politician_repository=mock_politician_repository,
            operation_log_repository=None,  # No log repository
        )
        mock_politician_repository.get_by_name_and_party.return_value = None
        created_politician = Politician(
            id=1,
            name="田中次郎",
            prefecture="東京都",
            political_party_id=1,
            district="東京都第1区",
        )
        mock_politician_repository.create.return_value = created_politician

        input_dto = CreatePoliticianInputDto(
            name="田中次郎",
            prefecture="東京都",
            party_id=1,
            district="東京都第1区",
        )

        # Act
        result = await use_case.create_politician(input_dto)

        # Assert
        assert result.success is True
        assert result.politician_id == 1
