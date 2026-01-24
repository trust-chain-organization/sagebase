"""Tests for ManageProposalsUseCase."""

from unittest.mock import AsyncMock

import pytest

from src.application.usecases.manage_proposals_usecase import (
    CreateProposalInputDto,
    CreateProposalOutputDto,
    DeleteProposalInputDto,
    DeleteProposalOutputDto,
    ManageProposalsUseCase,
    ProposalListInputDto,
    ProposalListOutputDto,
    UpdateProposalInputDto,
    UpdateProposalOutputDto,
)
from src.domain.entities.proposal import Proposal


class TestManageProposalsUseCase:
    """Test cases for ManageProposalsUseCase."""

    @pytest.fixture
    def mock_proposal_repository(self):
        """Create mock proposal repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def use_case(self, mock_proposal_repository):
        """Create ManageProposalsUseCase instance."""
        return ManageProposalsUseCase(repository=mock_proposal_repository)

    @pytest.mark.asyncio
    async def test_list_proposals_success(self, use_case, mock_proposal_repository):
        """Test listing proposals successfully."""
        # Arrange
        proposals = [
            Proposal(
                id=1,
                title="予算案第1号",
                detail_url="https://example.com/1",
            ),
            Proposal(
                id=2,
                title="予算案第2号",
                status_url="https://example.com/status/2",
                votes_url="https://example.com/votes/2",
            ),
        ]
        mock_proposal_repository.get_all.return_value = proposals

        input_dto = ProposalListInputDto()

        # Act
        result = await use_case.list_proposals(input_dto)

        # Assert
        assert isinstance(result, ProposalListOutputDto)
        assert len(result.proposals) == 2
        assert result.statistics.total == 2
        assert result.statistics.with_detail_url == 1
        assert result.statistics.with_status_url == 1
        assert result.statistics.with_votes_url == 1

    @pytest.mark.asyncio
    async def test_list_proposals_filtered_by_meeting(
        self, use_case, mock_proposal_repository
    ):
        """Test listing proposals filtered by meeting."""
        # Arrange
        proposals = [
            Proposal(
                id=1,
                title="予算案第1号",
                meeting_id=100,
            )
        ]
        mock_proposal_repository.get_by_meeting_id.return_value = proposals

        input_dto = ProposalListInputDto(filter_type="by_meeting", meeting_id=100)

        # Act
        result = await use_case.list_proposals(input_dto)

        # Assert
        assert len(result.proposals) == 1
        assert result.proposals[0].meeting_id == 100
        mock_proposal_repository.get_by_meeting_id.assert_called_once_with(100)

    @pytest.mark.asyncio
    async def test_list_proposals_filtered_by_conference(
        self, use_case, mock_proposal_repository
    ):
        """Test listing proposals filtered by conference."""
        # Arrange
        proposals = [
            Proposal(
                id=1,
                title="予算案第1号",
                conference_id=10,
            )
        ]
        mock_proposal_repository.get_by_conference_id.return_value = proposals

        input_dto = ProposalListInputDto(filter_type="by_conference", conference_id=10)

        # Act
        result = await use_case.list_proposals(input_dto)

        # Assert
        assert len(result.proposals) == 1
        assert result.proposals[0].conference_id == 10
        mock_proposal_repository.get_by_conference_id.assert_called_once_with(10)

    @pytest.mark.asyncio
    async def test_list_proposals_empty(self, use_case, mock_proposal_repository):
        """Test listing proposals when no proposals exist."""
        # Arrange
        mock_proposal_repository.get_all.return_value = []

        input_dto = ProposalListInputDto()

        # Act
        result = await use_case.list_proposals(input_dto)

        # Assert
        assert len(result.proposals) == 0
        assert result.statistics.total == 0
        assert result.statistics.with_detail_url == 0
        assert result.statistics.with_status_url == 0
        assert result.statistics.with_votes_url == 0

    @pytest.mark.asyncio
    async def test_create_proposal_success(self, use_case, mock_proposal_repository):
        """Test creating a proposal successfully."""
        # Arrange
        created_proposal = Proposal(
            id=1,
            title="新しい予算案",
            detail_url="https://example.com/new",
            meeting_id=100,
        )
        mock_proposal_repository.create.return_value = created_proposal

        input_dto = CreateProposalInputDto(
            title="新しい予算案",
            detail_url="https://example.com/new",
            meeting_id=100,
        )

        # Act
        result = await use_case.create_proposal(input_dto)

        # Assert
        assert isinstance(result, CreateProposalOutputDto)
        assert result.success is True
        assert result.proposal is not None
        assert result.proposal.id == 1
        assert "作成しました" in result.message
        mock_proposal_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_proposal_repository_error(
        self, use_case, mock_proposal_repository
    ):
        """Test creating a proposal with repository error."""
        # Arrange
        mock_proposal_repository.create.side_effect = Exception("Database error")

        input_dto = CreateProposalInputDto(title="新しい予算案")

        # Act
        result = await use_case.create_proposal(input_dto)

        # Assert
        assert result.success is False
        assert "エラーが発生しました" in result.message
        assert "Database error" in result.message

    @pytest.mark.asyncio
    async def test_update_proposal_success(self, use_case, mock_proposal_repository):
        """Test updating a proposal successfully."""
        # Arrange
        existing_proposal = Proposal(id=1, title="既存の予算案", meeting_id=100)
        mock_proposal_repository.get_by_id.return_value = existing_proposal

        updated_proposal = Proposal(
            id=1, title="更新された予算案", meeting_id=100, conference_id=10
        )
        mock_proposal_repository.update.return_value = updated_proposal

        input_dto = UpdateProposalInputDto(
            proposal_id=1, title="更新された予算案", conference_id=10
        )

        # Act
        result = await use_case.update_proposal(input_dto)

        # Assert
        assert isinstance(result, UpdateProposalOutputDto)
        assert result.success is True
        assert result.proposal is not None
        assert result.proposal.conference_id == 10
        assert "更新しました" in result.message
        mock_proposal_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_proposal_not_found(self, use_case, mock_proposal_repository):
        """Test updating a proposal that does not exist."""
        # Arrange
        mock_proposal_repository.get_by_id.return_value = None

        input_dto = UpdateProposalInputDto(proposal_id=999, title="存在しない議案")

        # Act
        result = await use_case.update_proposal(input_dto)

        # Assert
        assert result.success is False
        assert "見つかりません" in result.message
        mock_proposal_repository.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_proposal_repository_error(
        self, use_case, mock_proposal_repository
    ):
        """Test updating a proposal with repository error."""
        # Arrange
        existing_proposal = Proposal(id=1, title="既存の予算案")
        mock_proposal_repository.get_by_id.return_value = existing_proposal
        mock_proposal_repository.update.side_effect = Exception("Database error")

        input_dto = UpdateProposalInputDto(proposal_id=1, title="更新された予算案")

        # Act
        result = await use_case.update_proposal(input_dto)

        # Assert
        assert result.success is False
        assert "エラーが発生しました" in result.message
        assert "Database error" in result.message

    @pytest.mark.asyncio
    async def test_delete_proposal_success(self, use_case, mock_proposal_repository):
        """Test deleting a proposal successfully."""
        # Arrange
        existing_proposal = Proposal(id=1, title="既存の予算案")
        mock_proposal_repository.get_by_id.return_value = existing_proposal
        mock_proposal_repository.delete.return_value = True

        input_dto = DeleteProposalInputDto(proposal_id=1)

        # Act
        result = await use_case.delete_proposal(input_dto)

        # Assert
        assert isinstance(result, DeleteProposalOutputDto)
        assert result.success is True
        assert "削除しました" in result.message
        mock_proposal_repository.delete.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_proposal_not_found(self, use_case, mock_proposal_repository):
        """Test deleting a proposal that does not exist."""
        # Arrange
        mock_proposal_repository.get_by_id.return_value = None

        input_dto = DeleteProposalInputDto(proposal_id=999)

        # Act
        result = await use_case.delete_proposal(input_dto)

        # Assert
        assert result.success is False
        assert "見つかりません" in result.message
        mock_proposal_repository.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_proposal_repository_error(
        self, use_case, mock_proposal_repository
    ):
        """Test deleting a proposal with repository error."""
        # Arrange
        existing_proposal = Proposal(id=1, title="既存の予算案")
        mock_proposal_repository.get_by_id.return_value = existing_proposal
        mock_proposal_repository.delete.side_effect = Exception("Database error")

        input_dto = DeleteProposalInputDto(proposal_id=1)

        # Act
        result = await use_case.delete_proposal(input_dto)

        # Assert
        assert result.success is False
        assert "エラーが発生しました" in result.message
        assert "Database error" in result.message
