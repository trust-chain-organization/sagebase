"""議案操作ログエンティティ."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from src.domain.entities.base import BaseEntity


class ProposalOperationType(str, Enum):
    """議案操作種別."""

    CREATE = "create"
    """作成"""

    UPDATE = "update"
    """更新"""

    DELETE = "delete"
    """削除"""


class ProposalOperationLog(BaseEntity):
    """議案操作ログエンティティ.

    議案の作成・更新・削除操作を記録します。
    """

    def __init__(
        self,
        proposal_id: int,
        proposal_title: str,
        operation_type: ProposalOperationType,
        user_id: UUID | None = None,
        operation_details: dict[str, Any] | None = None,
        operated_at: datetime | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.proposal_id = proposal_id
        self.proposal_title = proposal_title
        self.operation_type = operation_type
        self.user_id = user_id
        self.operation_details = operation_details or {}
        self.operated_at = operated_at or datetime.now()

    def __str__(self) -> str:
        return (
            f"ProposalOperationLog("
            f"proposal_id={self.proposal_id}, "
            f"proposal_title={self.proposal_title[:30]}..., "
            f"operation_type={self.operation_type.value})"
        )
