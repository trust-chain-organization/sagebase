"""政治家操作ログリポジトリインターフェース."""

from abc import abstractmethod
from datetime import datetime
from typing import Any
from uuid import UUID

from src.domain.entities.politician_operation_log import (
    PoliticianOperationLog,
    PoliticianOperationType,
)
from src.domain.repositories.base import BaseRepository


class PoliticianOperationLogRepository(BaseRepository[PoliticianOperationLog]):
    """政治家操作ログリポジトリインターフェース."""

    @abstractmethod
    async def find_by_user(
        self, user_id: UUID | None = None
    ) -> list[PoliticianOperationLog]:
        """指定されたユーザーIDの操作ログを取得する.

        Args:
            user_id: フィルタリング対象のユーザーID（Noneの場合は全ユーザー）

        Returns:
            操作ログのリスト
        """
        pass

    @abstractmethod
    async def find_by_filters(
        self,
        user_id: UUID | None = None,
        operation_type: PoliticianOperationType | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[PoliticianOperationLog]:
        """条件に基づいて操作ログを取得する.

        Args:
            user_id: フィルタリング対象のユーザーID（Noneの場合は全ユーザー）
            operation_type: 操作種別でフィルタ（Noneの場合は全種別）
            start_date: 開始日時（この日時以降のログを取得）
            end_date: 終了日時（この日時以前のログを取得）

        Returns:
            操作ログのリスト
        """
        pass

    @abstractmethod
    async def get_statistics_by_user(
        self,
        user_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[UUID, int]:
        """ユーザー別の操作件数を集計する.

        Args:
            user_id: フィルタリング対象のユーザーID（Noneの場合は全ユーザー）
            start_date: 開始日時
            end_date: 終了日時

        Returns:
            ユーザーIDと件数のマッピング
        """
        pass

    @abstractmethod
    async def get_timeline_statistics(
        self,
        user_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        interval: str = "day",
    ) -> list[dict[str, Any]]:
        """時系列の操作件数を集計する.

        Args:
            user_id: フィルタリング対象のユーザーID（Noneの場合は全ユーザー）
            start_date: 開始日時
            end_date: 終了日時
            interval: 集計間隔（"day", "week", "month"）

        Returns:
            時系列データのリスト
        """
        pass
