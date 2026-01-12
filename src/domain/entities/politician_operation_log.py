"""政治家操作ログエンティティ."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from src.domain.entities.base import BaseEntity


class PoliticianOperationType(str, Enum):
    """政治家操作種別."""

    CREATE = "create"
    """作成"""

    UPDATE = "update"
    """更新"""

    DELETE = "delete"
    """削除"""


class PoliticianOperationLog(BaseEntity):
    """政治家操作ログエンティティ.

    政治家の作成・更新・削除操作を記録します。
    """

    def __init__(
        self,
        politician_id: int,
        politician_name: str,
        operation_type: PoliticianOperationType,
        user_id: UUID | None = None,
        operation_details: dict[str, Any] | None = None,
        operated_at: datetime | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.politician_id = politician_id
        self.politician_name = politician_name
        self.operation_type = operation_type
        self.user_id = user_id
        self.operation_details = operation_details or {}
        self.operated_at = operated_at or datetime.now()

    def __str__(self) -> str:
        return (
            f"PoliticianOperationLog("
            f"politician_id={self.politician_id}, "
            f"politician_name={self.politician_name}, "
            f"operation_type={self.operation_type.value})"
        )
