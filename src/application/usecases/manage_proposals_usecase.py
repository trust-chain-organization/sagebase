"""Use case for managing proposals.

This module provides use cases for proposal management including
listing, creating, updating, and deleting proposals.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.common.logging import get_logger
from src.domain.entities.proposal import Proposal
from src.domain.entities.proposal_operation_log import (
    ProposalOperationLog,
    ProposalOperationType,
)
from src.domain.repositories.proposal_operation_log_repository import (
    ProposalOperationLogRepository,
)
from src.domain.repositories.proposal_repository import ProposalRepository


@dataclass
class ProposalListInputDto:
    """Input DTO for listing proposals."""

    filter_type: str | None = None  # 'all', 'by_meeting', 'by_conference'
    meeting_id: int | None = None  # Filter by meeting (if filter_type='by_meeting')
    conference_id: int | None = None  # Filter by conference
    order_by: str = "id"


@dataclass
class ProposalStatistics:
    """Statistics for proposals."""

    total: int
    with_detail_url: int
    with_status_url: int
    with_votes_url: int

    @property
    def with_detail_url_percentage(self) -> float:
        """Calculate percentage of proposals with detail URL."""
        if self.total == 0:
            return 0.0
        return (self.with_detail_url / self.total) * 100

    @property
    def with_status_url_percentage(self) -> float:
        """Calculate percentage of proposals with status URL."""
        if self.total == 0:
            return 0.0
        return (self.with_status_url / self.total) * 100


@dataclass
class ProposalListOutputDto:
    """Output DTO for listing proposals."""

    proposals: list[Proposal]
    statistics: ProposalStatistics


@dataclass
class CreateProposalInputDto:
    """Input DTO for creating a proposal."""

    title: str
    detail_url: str | None = None
    status_url: str | None = None
    votes_url: str | None = None
    meeting_id: int | None = None
    conference_id: int | None = None
    user_id: UUID | None = None  # 操作を行ったユーザーID


@dataclass
class CreateProposalOutputDto:
    """Output DTO for creating a proposal."""

    success: bool
    message: str
    proposal: Proposal | None = None


@dataclass
class UpdateProposalInputDto:
    """Input DTO for updating a proposal."""

    proposal_id: int
    title: str | None = None
    detail_url: str | None = None
    status_url: str | None = None
    votes_url: str | None = None
    meeting_id: int | None = None
    conference_id: int | None = None
    user_id: UUID | None = None  # 操作を行ったユーザーID


@dataclass
class UpdateProposalOutputDto:
    """Output DTO for updating a proposal."""

    success: bool
    message: str
    proposal: Proposal | None = None


@dataclass
class DeleteProposalInputDto:
    """Input DTO for deleting a proposal."""

    proposal_id: int
    user_id: UUID | None = None  # 操作を行ったユーザーID


@dataclass
class DeleteProposalOutputDto:
    """Output DTO for deleting a proposal."""

    success: bool
    message: str


class ManageProposalsUseCase:
    """Use case for managing proposals."""

    def __init__(
        self,
        repository: ProposalRepository,
        operation_log_repository: ProposalOperationLogRepository | None = None,
    ):
        """Initialize the use case.

        Args:
            repository: Proposal repository (can be sync or async)
            operation_log_repository: 議案操作ログリポジトリ（オプション）
        """
        self.repository = repository
        self.operation_log_repo = operation_log_repository
        self.logger = get_logger(self.__class__.__name__)

    async def list_proposals(
        self, input_dto: ProposalListInputDto
    ) -> ProposalListOutputDto:
        """List proposals with optional filtering.

        Args:
            input_dto: Input parameters for listing

        Returns:
            Output DTO with proposals and statistics
        """
        try:
            # Get proposals based on filter
            if input_dto.filter_type == "by_meeting" and input_dto.meeting_id:
                proposals = await self.repository.get_by_meeting_id(
                    input_dto.meeting_id
                )
            elif input_dto.filter_type == "by_conference" and input_dto.conference_id:
                proposals = await self.repository.get_by_conference_id(
                    input_dto.conference_id
                )
            else:
                proposals = await self.repository.get_all()

            # Sort proposals
            if input_dto.order_by == "id":
                proposals.sort(key=lambda p: p.id or 0)

            # Calculate statistics
            total = len(proposals)
            with_detail_url = sum(1 for p in proposals if p.detail_url)
            with_status_url = sum(1 for p in proposals if p.status_url)
            with_votes_url = sum(1 for p in proposals if p.votes_url)

            statistics = ProposalStatistics(
                total=total,
                with_detail_url=with_detail_url,
                with_status_url=with_status_url,
                with_votes_url=with_votes_url,
            )

            return ProposalListOutputDto(proposals=proposals, statistics=statistics)

        except Exception as e:
            self.logger.error(f"Error listing proposals: {e}", exc_info=True)
            raise

    async def create_proposal(
        self, input_dto: CreateProposalInputDto
    ) -> CreateProposalOutputDto:
        """Create a new proposal.

        Args:
            input_dto: Input parameters for creating

        Returns:
            Output DTO with result
        """
        try:
            # Create new proposal entity
            proposal = Proposal(
                title=input_dto.title,
                detail_url=input_dto.detail_url,
                status_url=input_dto.status_url,
                votes_url=input_dto.votes_url,
                meeting_id=input_dto.meeting_id,
                conference_id=input_dto.conference_id,
            )

            # Save to repository
            created_proposal = await self.repository.create(proposal)

            # 操作ログを記録
            if self.operation_log_repo and created_proposal.id:
                operation_log = ProposalOperationLog(
                    proposal_id=created_proposal.id,
                    proposal_title=created_proposal.title,
                    operation_type=ProposalOperationType.CREATE,
                    user_id=input_dto.user_id,
                    operation_details={
                        "detail_url": created_proposal.detail_url,
                        "status_url": created_proposal.status_url,
                        "votes_url": created_proposal.votes_url,
                        "meeting_id": created_proposal.meeting_id,
                        "conference_id": created_proposal.conference_id,
                    },
                    operated_at=datetime.now(),
                )
                await self.operation_log_repo.create(operation_log)

            return CreateProposalOutputDto(
                success=True, message="議案を作成しました", proposal=created_proposal
            )

        except Exception as e:
            self.logger.error(f"Error creating proposal: {e}", exc_info=True)
            return CreateProposalOutputDto(
                success=False, message=f"作成中にエラーが発生しました: {str(e)}"
            )

    async def update_proposal(
        self, input_dto: UpdateProposalInputDto
    ) -> UpdateProposalOutputDto:
        """Update an existing proposal.

        Args:
            input_dto: Input parameters for updating

        Returns:
            Output DTO with result
        """
        try:
            # Get the proposal
            proposal = await self.repository.get_by_id(input_dto.proposal_id)
            if not proposal:
                return UpdateProposalOutputDto(
                    success=False,
                    message=f"議案ID {input_dto.proposal_id} が見つかりません",
                )

            # 更新前の状態を保存
            old_values = {
                "title": proposal.title,
                "detail_url": proposal.detail_url,
                "status_url": proposal.status_url,
                "votes_url": proposal.votes_url,
                "meeting_id": proposal.meeting_id,
                "conference_id": proposal.conference_id,
            }

            # Update fields if provided
            if input_dto.title is not None:
                proposal.title = input_dto.title
            if input_dto.detail_url is not None:
                proposal.detail_url = input_dto.detail_url
            if input_dto.status_url is not None:
                proposal.status_url = input_dto.status_url
            if input_dto.votes_url is not None:
                proposal.votes_url = input_dto.votes_url
            if input_dto.meeting_id is not None:
                proposal.meeting_id = input_dto.meeting_id
            if input_dto.conference_id is not None:
                proposal.conference_id = input_dto.conference_id

            # Save updated proposal
            updated_proposal = await self.repository.update(proposal)

            # 操作ログを記録
            if self.operation_log_repo and updated_proposal.id:
                new_values = {
                    "title": updated_proposal.title,
                    "detail_url": updated_proposal.detail_url,
                    "status_url": updated_proposal.status_url,
                    "votes_url": updated_proposal.votes_url,
                    "meeting_id": updated_proposal.meeting_id,
                    "conference_id": updated_proposal.conference_id,
                }
                operation_log = ProposalOperationLog(
                    proposal_id=updated_proposal.id,
                    proposal_title=updated_proposal.title,
                    operation_type=ProposalOperationType.UPDATE,
                    user_id=input_dto.user_id,
                    operation_details={
                        "old_values": old_values,
                        "new_values": new_values,
                    },
                    operated_at=datetime.now(),
                )
                await self.operation_log_repo.create(operation_log)

            return UpdateProposalOutputDto(
                success=True, message="議案を更新しました", proposal=updated_proposal
            )

        except Exception as e:
            self.logger.error(f"Error updating proposal: {e}", exc_info=True)
            return UpdateProposalOutputDto(
                success=False, message=f"更新中にエラーが発生しました: {str(e)}"
            )

    async def delete_proposal(
        self, input_dto: DeleteProposalInputDto
    ) -> DeleteProposalOutputDto:
        """Delete a proposal.

        Args:
            input_dto: Input parameters for deleting

        Returns:
            Output DTO with result
        """
        try:
            # Check if proposal exists
            proposal = await self.repository.get_by_id(input_dto.proposal_id)
            if not proposal:
                return DeleteProposalOutputDto(
                    success=False,
                    message=f"議案ID {input_dto.proposal_id} が見つかりません",
                )

            # 削除前に情報を保存
            proposal_id = proposal.id
            proposal_title = proposal.title

            # Delete the proposal
            success = await self.repository.delete(input_dto.proposal_id)

            if success:
                # 操作ログを記録
                if self.operation_log_repo and proposal_id:
                    operation_log = ProposalOperationLog(
                        proposal_id=proposal_id,
                        proposal_title=proposal_title,
                        operation_type=ProposalOperationType.DELETE,
                        user_id=input_dto.user_id,
                        operation_details={
                            "deleted_proposal": {
                                "id": proposal_id,
                                "title": proposal_title,
                                "detail_url": proposal.detail_url,
                                "status_url": proposal.status_url,
                                "votes_url": proposal.votes_url,
                                "meeting_id": proposal.meeting_id,
                                "conference_id": proposal.conference_id,
                            }
                        },
                        operated_at=datetime.now(),
                    )
                    await self.operation_log_repo.create(operation_log)

                return DeleteProposalOutputDto(
                    success=True, message="議案を削除しました"
                )
            else:
                return DeleteProposalOutputDto(
                    success=False, message="削除に失敗しました"
                )

        except Exception as e:
            self.logger.error(f"Error deleting proposal: {e}", exc_info=True)
            return DeleteProposalOutputDto(
                success=False, message=f"削除中にエラーが発生しました: {str(e)}"
            )
