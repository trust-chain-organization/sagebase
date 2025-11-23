"""Repository interface for parliamentary group memberships."""

from abc import abstractmethod
from datetime import date
from typing import Any
from uuid import UUID

from src.domain.dtos.parliamentary_group_membership_dto import (
    ParliamentaryGroupMembershipWithRelationsDTO,
)
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
    ) -> list[ParliamentaryGroupMembershipWithRelationsDTO]:
        """指定されたユーザーIDによって作成された議員団メンバーシップと関連情報を取得する

        Args:
            user_id: フィルタリング対象のユーザーID（Noneの場合は全ユーザー）

        Returns:
            議員団メンバーシップと関連エンティティ（政治家、議員団）を含むDTOのリスト
        """
        pass

    @abstractmethod
    async def get_membership_creation_statistics_by_user(
        self,
        user_id: "UUID | None" = None,
        start_date: Any | None = None,
        end_date: Any | None = None,
    ) -> dict[UUID, int]:
        """ユーザー別の議員団メンバー作成件数を集計する（データベースレベルで集計）

        Args:
            user_id: フィルタリング対象のユーザーID（Noneの場合は全ユーザー）
            start_date: 開始日時（この日時以降の作業を集計）
            end_date: 終了日時（この日時以前の作業を集計）

        Returns:
            ユーザーIDと件数のマッピング（例: {UUID('...'): 10, UUID('...'): 5}）
        """
        pass

    @abstractmethod
    async def get_membership_creation_timeline_statistics(
        self,
        user_id: "UUID | None" = None,
        start_date: Any | None = None,
        end_date: Any | None = None,
        interval: str = "day",
    ) -> list[dict[str, Any]]:
        """時系列の議員団メンバー作成件数を集計する（データベースレベルで集計）

        Args:
            user_id: フィルタリング対象のユーザーID（Noneの場合は全ユーザー）
            start_date: 開始日時
            end_date: 終了日時
            interval: 集計間隔（"day", "week", "month"）

        Returns:
            時系列データのリスト（例: [{"date": "2024-01-01", "count": 5}, ...]）
        """
        pass
