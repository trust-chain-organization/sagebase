"""Speaker repository interface."""

from abc import abstractmethod
from typing import Any
from uuid import UUID

from src.domain.dtos.speaker_dto import (
    SpeakerWithConversationCountDTO,
    SpeakerWithPoliticianDTO,
)
from src.domain.entities.speaker import Speaker
from src.domain.repositories.base import BaseRepository


class SpeakerRepository(BaseRepository[Speaker]):
    """Repository interface for speakers."""

    @abstractmethod
    async def get_by_name_party_position(
        self,
        name: str,
        political_party_name: str | None = None,
        position: str | None = None,
    ) -> Speaker | None:
        """Get speaker by name, party, and position."""
        pass

    @abstractmethod
    async def get_politicians(self) -> list[Speaker]:
        """Get all speakers who are politicians."""
        pass

    @abstractmethod
    async def search_by_name(self, name_pattern: str) -> list[Speaker]:
        """Search speakers by name pattern."""
        pass

    @abstractmethod
    async def upsert(self, speaker: Speaker) -> Speaker:
        """Insert or update speaker (upsert)."""
        pass

    @abstractmethod
    async def get_speakers_with_conversation_count(
        self,
        limit: int | None = None,
        offset: int | None = None,
        speaker_type: str | None = None,
        is_politician: bool | None = None,
    ) -> list[SpeakerWithConversationCountDTO]:
        """Get speakers with their conversation count."""
        pass

    @abstractmethod
    async def find_by_name(self, name: str) -> Speaker | None:
        """Find speaker by name."""
        pass

    @abstractmethod
    async def get_speakers_not_linked_to_politicians(self) -> list[Speaker]:
        """Get speakers who are not linked to politicians (is_politician=False)."""
        pass

    @abstractmethod
    async def get_speakers_with_politician_info(self) -> list[dict[str, Any]]:
        """Get speakers with linked politician information."""
        pass

    @abstractmethod
    async def get_speaker_politician_stats(self) -> dict[str, int | float]:
        """Get statistics of speaker-politician linkage."""
        pass

    @abstractmethod
    async def get_all_for_matching(self) -> list[dict[str, Any]]:
        """Get all speakers for matching purposes.

        Returns:
            List of dicts with id and name keys
        """
        pass

    @abstractmethod
    async def get_affiliated_speakers(
        self, meeting_date: str, conference_id: int
    ) -> list[dict[str, Any]]:
        """Get speakers affiliated with a conference at a specific date.

        Args:
            meeting_date: Meeting date in YYYY-MM-DD format
            conference_id: Conference ID

        Returns:
            List of dicts with speaker and politician info
        """
        pass

    @abstractmethod
    async def find_by_matched_user(
        self, user_id: "UUID | None" = None
    ) -> list[SpeakerWithPoliticianDTO]:
        """指定されたユーザーIDによってマッチングされた発言者と政治家情報を取得する

        Args:
            user_id: フィルタリング対象のユーザーID（Noneの場合は全ユーザー）

        Returns:
            発言者と紐付けられた政治家情報を含むDTOのリスト
        """
        pass

    @abstractmethod
    async def get_speaker_matching_statistics_by_user(
        self,
        user_id: "UUID | None" = None,
        start_date: Any | None = None,
        end_date: Any | None = None,
    ) -> dict[UUID, int]:
        """ユーザー別の発言者紐付け件数を集計する（データベースレベルで集計）

        Args:
            user_id: フィルタリング対象のユーザーID（Noneの場合は全ユーザー）
            start_date: 開始日時（この日時以降の作業を集計）
            end_date: 終了日時（この日時以前の作業を集計）

        Returns:
            ユーザーIDと件数のマッピング（例: {UUID('...'): 10, UUID('...'): 5}）
        """
        pass

    @abstractmethod
    async def get_speaker_matching_timeline_statistics(
        self,
        user_id: "UUID | None" = None,
        start_date: Any | None = None,
        end_date: Any | None = None,
        interval: str = "day",
    ) -> list[dict[str, Any]]:
        """時系列の発言者紐付け件数を集計する（データベースレベルで集計）

        Args:
            user_id: フィルタリング対象のユーザーID（Noneの場合は全ユーザー）
            start_date: 開始日時
            end_date: 終了日時
            interval: 集計間隔（"day", "week", "month"）

        Returns:
            時系列データのリスト（例: [{"date": "2024-01-01", "count": 5}, ...]）
        """
        pass
