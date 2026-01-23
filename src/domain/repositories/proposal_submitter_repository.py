"""Repository interface for ProposalSubmitter entities."""

from abc import abstractmethod

from src.domain.entities.proposal_submitter import ProposalSubmitter
from src.domain.repositories.base import BaseRepository


class ProposalSubmitterRepository(BaseRepository[ProposalSubmitter]):
    """Repository interface for ProposalSubmitter entities."""

    @abstractmethod
    async def get_by_proposal(self, proposal_id: int) -> list[ProposalSubmitter]:
        """Get all submitters for a specific proposal.

        Args:
            proposal_id: ID of the proposal

        Returns:
            List of ProposalSubmitter entities ordered by display_order
        """
        pass

    @abstractmethod
    async def get_by_politician(self, politician_id: int) -> list[ProposalSubmitter]:
        """Get all proposal submitters for a specific politician.

        Args:
            politician_id: ID of the politician

        Returns:
            List of ProposalSubmitter entities
        """
        pass

    @abstractmethod
    async def get_by_parliamentary_group(
        self, parliamentary_group_id: int
    ) -> list[ProposalSubmitter]:
        """Get all proposal submitters for a specific parliamentary group.

        Args:
            parliamentary_group_id: ID of the parliamentary group

        Returns:
            List of ProposalSubmitter entities
        """
        pass

    @abstractmethod
    async def bulk_create(
        self, submitters: list[ProposalSubmitter]
    ) -> list[ProposalSubmitter]:
        """Create multiple proposal submitters at once.

        Args:
            submitters: List of ProposalSubmitter entities to create

        Returns:
            List of created ProposalSubmitter entities with IDs
        """
        pass

    @abstractmethod
    async def delete_by_proposal(self, proposal_id: int) -> int:
        """Delete all submitters for a specific proposal.

        Args:
            proposal_id: ID of the proposal

        Returns:
            Number of deleted records
        """
        pass
