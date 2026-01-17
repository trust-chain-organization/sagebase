"""Minutes repository interface."""

from abc import abstractmethod

from src.domain.entities.minutes import Minutes
from src.domain.repositories.base import BaseRepository


class MinutesRepository(BaseRepository[Minutes]):
    """Repository interface for minutes."""

    @abstractmethod
    async def get_by_meeting(self, meeting_id: int) -> Minutes | None:
        """Get minutes by meeting ID."""
        pass

    @abstractmethod
    async def get_unprocessed(self, limit: int | None = None) -> list[Minutes]:
        """Get minutes that haven't been processed yet."""
        pass

    @abstractmethod
    async def mark_processed(self, minutes_id: int) -> bool:
        """Mark minutes as processed."""
        pass

    @abstractmethod
    async def count_processed(self) -> int:
        """Count minutes that have been processed (processed_at IS NOT NULL)."""
        pass

    @abstractmethod
    async def update_role_name_mappings(
        self, minutes_id: int, mappings: dict[str, str]
    ) -> bool:
        """議事録の役職-人名マッピングを更新する

        Args:
            minutes_id: 議事録ID
            mappings: 役職-人名マッピング辞書

        Returns:
            bool: 更新成功の場合True
        """
        pass

    @abstractmethod
    async def get_all(
        self, limit: int | None = None, offset: int | None = None
    ) -> list[Minutes]:
        """全議事録を取得する

        Args:
            limit: 取得件数の上限（Noneの場合は全件）
            offset: スキップする件数（Noneの場合は0）

        Returns:
            list[Minutes]: 議事録リスト
        """
        pass
