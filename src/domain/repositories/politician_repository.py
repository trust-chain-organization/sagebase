"""Politician repository interface."""

from abc import abstractmethod
from typing import Any

from src.domain.entities.politician import Politician
from src.domain.repositories.base import BaseRepository


class PoliticianRepository(BaseRepository[Politician]):
    """Repository interface for politicians."""

    @abstractmethod
    async def get_by_name_and_party(
        self, name: str, political_party_id: int | None = None
    ) -> Politician | None:
        """Get politician by name and political party."""
        pass

    @abstractmethod
    async def get_by_party(self, political_party_id: int) -> list[Politician]:
        """Get all politicians for a political party."""
        pass

    @abstractmethod
    async def search_by_name(self, name_pattern: str) -> list[Politician]:
        """Search politicians by name pattern."""
        pass

    @abstractmethod
    async def upsert(self, politician: Politician) -> Politician:
        """Insert or update politician (upsert)."""
        pass

    @abstractmethod
    async def bulk_create_politicians(
        self, politicians_data: list[dict[str, Any]]
    ) -> dict[str, list[Politician] | list[dict[str, Any]]]:
        """Bulk create or update politicians."""
        pass

    @abstractmethod
    async def fetch_as_dict_async(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute raw SQL query and return results as dictionaries (async)."""
        pass

    @abstractmethod
    async def count_by_party(self, political_party_id: int) -> int:
        """Count politicians by political party.

        Args:
            political_party_id: Political party ID

        Returns:
            Number of politicians in the party
        """
        pass

    @abstractmethod
    async def get_all_for_matching(self) -> list[dict[str, Any]]:
        """Get all politicians for matching purposes.

        Returns:
            List of dicts with id, name, position, prefecture,
            electoral_district, and party_name
        """
        pass

    @abstractmethod
    async def get_related_data_counts(self, politician_id: int) -> dict[str, int]:
        """指定された政治家に紐づく関連データの件数を取得する.

        Args:
            politician_id: 政治家ID

        Returns:
            テーブル名をキー、件数を値とする辞書
            例: {"speakers": 2, "parliamentary_group_memberships": 1, ...}
        """
        pass

    @abstractmethod
    async def delete_related_data(self, politician_id: int) -> dict[str, int]:
        """指定された政治家に紐づく関連データを削除・解除する.

        - NULLableなカラムはNULLに設定
        - NOT NULLなカラムを持つレコードは削除

        Args:
            politician_id: 政治家ID

        Returns:
            テーブル名をキー、処理件数を値とする辞書
        """
        pass
