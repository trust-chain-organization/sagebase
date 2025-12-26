"""Unit of Work interface for transaction management.

This interface provides a clean abstraction for managing database transactions
across multiple repository operations while maintaining Clean Architecture principles.
"""

from abc import ABC, abstractmethod
from typing import TypeVar

from src.domain.repositories.conversation_repository import ConversationRepository
from src.domain.repositories.meeting_repository import MeetingRepository
from src.domain.repositories.minutes_repository import MinutesRepository
from src.domain.repositories.speaker_repository import SpeakerRepository


T = TypeVar("T")


class IUnitOfWork(ABC):
    """Unit of Work interface for transaction management.

    This interface ensures that all repository operations within a use case
    share the same database transaction, providing ACID guarantees.
    """

    @property
    @abstractmethod
    def meeting_repository(self) -> MeetingRepository:
        """Get the meeting repository for this unit of work."""
        pass

    @property
    @abstractmethod
    def minutes_repository(self) -> MinutesRepository:
        """Get the minutes repository for this unit of work."""
        pass

    @property
    @abstractmethod
    def conversation_repository(self) -> ConversationRepository:
        """Get the conversation repository for this unit of work."""
        pass

    @property
    @abstractmethod
    def speaker_repository(self) -> SpeakerRepository:
        """Get the speaker repository for this unit of work."""
        pass

    @abstractmethod
    async def commit(self) -> None:
        """Commit the current transaction."""
        pass

    @abstractmethod
    async def rollback(self) -> None:
        """Rollback the current transaction."""
        pass

    @abstractmethod
    async def flush(self) -> None:
        """Flush changes to database without committing.

        This is useful when you need to make foreign key references available
        within the same transaction.
        """
        pass
