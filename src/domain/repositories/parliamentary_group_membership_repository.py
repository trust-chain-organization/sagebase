"""Repository interface for parliamentary group memberships."""

from abc import abstractmethod
from datetime import date
from typing import Any
from uuid import UUID

from src.domain.entities.parliamentary_group_membership import (
    ParliamentaryGroupMembership,
)
from src.domain.repositories.base import BaseRepository


class ParliamentaryGroupMembershipRepository(
    BaseRepository[ParliamentaryGroupMembership]
):
    """Repository interface for parliamentary group memberships."""

    @abstractmethod
    async def get_by_group(self, group_id: int) -> list[ParliamentaryGroupMembership]:
        """Get memberships by group.

        Args:
            group_id: Parliamentary group ID

        Returns:
            List of memberships for the group
        """
        pass

    @abstractmethod
    async def get_by_politician(
        self, politician_id: int
    ) -> list[ParliamentaryGroupMembership]:
        """Get memberships by politician.

        Args:
            politician_id: Politician ID

        Returns:
            List of memberships for the politician
        """
        pass

    @abstractmethod
    async def get_active_by_group(
        self, group_id: int, as_of_date: date | None = None
    ) -> list[ParliamentaryGroupMembership]:
        """Get active memberships by group.

        Args:
            group_id: Parliamentary group ID
            as_of_date: Date to check active status (None = today)

        Returns:
            List of active memberships
        """
        pass

    @abstractmethod
    async def create_membership(
        self,
        politician_id: int,
        group_id: int,
        start_date: date,
        role: str | None = None,
        created_by_user_id: UUID | None = None,
    ) -> ParliamentaryGroupMembership:
        """Create a new membership.

        Args:
            politician_id: Politician ID
            group_id: Parliamentary group ID
            start_date: Membership start date
            role: Optional role in the group
            created_by_user_id: User ID who created the membership

        Returns:
            Created membership entity
        """
        pass

    @abstractmethod
    async def end_membership(
        self, membership_id: int, end_date: date
    ) -> ParliamentaryGroupMembership | None:
        """End a membership.

        Args:
            membership_id: Membership ID
            end_date: Membership end date

        Returns:
            Updated membership entity or None if not found
        """
        pass

    @abstractmethod
    async def get_current_members(self, group_id: int) -> list[dict[str, Any]]:
        """Get current members of a parliamentary group.

        Args:
            group_id: Parliamentary group ID

        Returns:
            List of dictionaries containing politician_id and other member info
        """
        pass

    @abstractmethod
    async def find_by_created_user(
        self, user_id: "UUID | None" = None
    ) -> list[ParliamentaryGroupMembership]:
        """指定されたユーザーIDによって作成された議員団メンバーシップを取得する

        Args:
            user_id: フィルタリング対象のユーザーID（Noneの場合は全ユーザー）

        Returns:
            作成された議員団メンバーシップのリスト
        """
        pass
