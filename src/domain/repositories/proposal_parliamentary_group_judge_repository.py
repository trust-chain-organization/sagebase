"""ProposalParliamentaryGroupJudge repository interface."""

from abc import abstractmethod

from src.domain.entities.proposal_parliamentary_group_judge import (
    ProposalParliamentaryGroupJudge,
)
from src.domain.repositories.base import BaseRepository


class ProposalParliamentaryGroupJudgeRepository(
    BaseRepository[ProposalParliamentaryGroupJudge]
):
    """Repository interface for ProposalParliamentaryGroupJudge entities.

    Many-to-Many構造: 1つの賛否レコードに複数の会派・政治家を紐付け可能。
    """

    @abstractmethod
    async def get_by_proposal(
        self, proposal_id: int
    ) -> list[ProposalParliamentaryGroupJudge]:
        """Get all parliamentary group judges for a specific proposal.

        Args:
            proposal_id: ID of the proposal

        Returns:
            List of ProposalParliamentaryGroupJudge entities with related IDs populated
        """
        pass

    @abstractmethod
    async def get_by_parliamentary_group(
        self, parliamentary_group_id: int
    ) -> list[ProposalParliamentaryGroupJudge]:
        """Get all proposal judges that include a specific parliamentary group.

        Args:
            parliamentary_group_id: ID of the parliamentary group

        Returns:
            List of ProposalParliamentaryGroupJudge entities
        """
        pass

    @abstractmethod
    async def get_by_proposal_and_groups(
        self, proposal_id: int, parliamentary_group_ids: list[int]
    ) -> ProposalParliamentaryGroupJudge | None:
        """Get judge for proposal containing all specified parliamentary groups.

        Args:
            proposal_id: ID of the proposal
            parliamentary_group_ids: List of parliamentary group IDs

        Returns:
            ProposalParliamentaryGroupJudge entity or None if not found
        """
        pass

    @abstractmethod
    async def get_by_proposal_and_politicians(
        self, proposal_id: int, politician_ids: list[int]
    ) -> ProposalParliamentaryGroupJudge | None:
        """Get judge for a specific proposal that contains all specified politicians.

        Args:
            proposal_id: ID of the proposal
            politician_ids: List of politician IDs

        Returns:
            ProposalParliamentaryGroupJudge entity or None if not found
        """
        pass

    @abstractmethod
    async def get_by_politician(
        self, politician_id: int
    ) -> list[ProposalParliamentaryGroupJudge]:
        """Get all proposal judges that include a specific politician.

        Args:
            politician_id: ID of the politician

        Returns:
            List of ProposalParliamentaryGroupJudge entities
        """
        pass

    @abstractmethod
    async def bulk_create(
        self, judges: list[ProposalParliamentaryGroupJudge]
    ) -> list[ProposalParliamentaryGroupJudge]:
        """Create multiple parliamentary group judges at once.

        Args:
            judges: List of ProposalParliamentaryGroupJudge entities to create

        Returns:
            List of created ProposalParliamentaryGroupJudge entities with IDs
        """
        pass
