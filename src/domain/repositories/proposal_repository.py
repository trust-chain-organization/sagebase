"""Proposal repository interface."""

from abc import abstractmethod

from src.domain.entities.proposal import Proposal
from src.domain.repositories.base import BaseRepository


class ProposalRepository(BaseRepository[Proposal]):
    """Proposal repository interface."""

    @abstractmethod
    async def get_by_meeting_id(self, meeting_id: int) -> list[Proposal]:
        """Get proposals by meeting ID.

        Args:
            meeting_id: Meeting ID to filter by

        Returns:
            List of proposals associated with the specified meeting
        """
        pass

    @abstractmethod
    async def get_by_conference_id(self, conference_id: int) -> list[Proposal]:
        """Get proposals by conference ID.

        Args:
            conference_id: Conference ID to filter by

        Returns:
            List of proposals associated with the specified conference
        """
        pass

    @abstractmethod
    async def find_by_url(self, url: str) -> Proposal | None:
        """Find proposal by URL.

        Args:
            url: URL of the proposal (detail_url, status_url, or votes_url)

        Returns:
            Proposal if found, None otherwise
        """
        pass
