"""Conversation repository interface."""

from abc import abstractmethod
from typing import Any

from src.domain.entities.conversation import Conversation
from src.domain.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """Repository interface for conversations."""

    @abstractmethod
    async def get_by_minutes(
        self, minutes_id: int, limit: int | None = None
    ) -> list[Conversation]:
        """Get all conversations for a minutes record."""
        pass

    @abstractmethod
    async def get_by_speaker(
        self, speaker_id: int, limit: int | None = None
    ) -> list[Conversation]:
        """Get all conversations by a speaker."""
        pass

    @abstractmethod
    async def get_unlinked(self, limit: int | None = None) -> list[Conversation]:
        """Get conversations without speaker links."""
        pass

    @abstractmethod
    async def bulk_create(
        self, conversations: list[Conversation]
    ) -> list[Conversation]:
        """Create multiple conversations at once."""
        pass

    @abstractmethod
    async def save_speaker_and_speech_content_list(
        self, speaker_and_speech_content_list: list[Any], minutes_id: int | None = None
    ) -> list[int]:
        """Save speaker and speech content list.

        Args:
            speaker_and_speech_content_list: List of SpeakerAndSpeechContent objects
            minutes_id: Optional minutes ID to link conversations to

        Returns:
            List of created conversation IDs
        """
        pass

    @abstractmethod
    async def get_conversations_count(self) -> int:
        """Get total count of conversations."""
        pass

    @abstractmethod
    async def get_speaker_linking_stats(self) -> dict[str, Any]:
        """Get statistics about speaker linking."""
        pass

    @abstractmethod
    async def get_conversations_with_pagination(
        self,
        page: int = 1,
        page_size: int = 10,
        speaker_name: str | None = None,
        meeting_id: int | None = None,
        has_speaker_id: bool | None = None,
    ) -> dict[str, Any]:
        """Get conversations with pagination and filters.

        Args:
            page: Page number (1-based)
            page_size: Number of items per page
            speaker_name: Optional filter by speaker name
            meeting_id: Optional filter by meeting ID
            has_speaker_id: Optional filter by presence of speaker ID

        Returns:
            Dictionary with conversations and pagination info
        """
        pass

    @abstractmethod
    async def update_speaker_links(self) -> int:
        """Update speaker links for conversations.

        Returns:
            Number of updated conversations
        """
        pass
