"""議案操作ログリポジトリ実装."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.proposal_operation_log import (
    ProposalOperationLog,
    ProposalOperationType,
)
from src.domain.repositories.proposal_operation_log_repository import (
    ProposalOperationLogRepository,
)
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


class ProposalOperationLogModel(PydanticBaseModel):
    """議案操作ログデータベースモデル."""

    id: int | None = None
    proposal_id: int
    proposal_title: str
    operation_type: str
    user_id: UUID | None = None
    operation_details: dict[str, Any] | None = None
    operated_at: datetime

    class Config:
        arbitrary_types_allowed = True


class ProposalOperationLogRepositoryImpl(
    BaseRepositoryImpl[ProposalOperationLog], ProposalOperationLogRepository
):
    """議案操作ログリポジトリ実装."""

    def __init__(self, session: AsyncSession):
        super().__init__(
            session=session,
            entity_class=ProposalOperationLog,
            model_class=ProposalOperationLogModel,
        )

    def _to_entity(self, model: ProposalOperationLogModel) -> ProposalOperationLog:
        """モデルをエンティティに変換."""
        return ProposalOperationLog(
            id=model.id,
            proposal_id=model.proposal_id,
            proposal_title=model.proposal_title,
            operation_type=ProposalOperationType(model.operation_type),
            user_id=model.user_id,
            operation_details=model.operation_details or {},
            operated_at=model.operated_at,
        )

    def _to_model(self, entity: ProposalOperationLog) -> ProposalOperationLogModel:
        """エンティティをモデルに変換."""
        return ProposalOperationLogModel(
            id=entity.id,
            proposal_id=entity.proposal_id,
            proposal_title=entity.proposal_title,
            operation_type=entity.operation_type.value,
            user_id=entity.user_id,
            operation_details=entity.operation_details,
            operated_at=entity.operated_at,
        )

    def _update_model(
        self, model: ProposalOperationLogModel, entity: ProposalOperationLog
    ) -> None:
        """モデルを更新."""
        model.proposal_id = entity.proposal_id
        model.proposal_title = entity.proposal_title
        model.operation_type = entity.operation_type.value
        model.user_id = entity.user_id
        model.operation_details = entity.operation_details
        model.operated_at = entity.operated_at

    async def find_by_user(
        self, user_id: UUID | None = None
    ) -> list[ProposalOperationLog]:
        """指定されたユーザーIDの操作ログを取得する."""
        from sqlalchemy import text

        query_str = """
            SELECT id, proposal_id, proposal_title, operation_type,
                   user_id, operation_details, operated_at
            FROM proposal_operation_logs
        """
        params: dict[str, Any] = {}

        if user_id is not None:
            query_str += " WHERE user_id = :user_id"
            params["user_id"] = str(user_id)

        query_str += " ORDER BY operated_at DESC"

        result = await self.session.execute(text(query_str), params)
        rows = result.fetchall()

        logs = []
        for row in rows:
            logs.append(
                ProposalOperationLog(
                    id=row[0],
                    proposal_id=row[1],
                    proposal_title=row[2],
                    operation_type=ProposalOperationType(row[3]),
                    user_id=UUID(str(row[4])) if row[4] else None,
                    operation_details=row[5] or {},
                    operated_at=row[6],
                )
            )
        return logs

    async def find_by_filters(
        self,
        user_id: UUID | None = None,
        operation_type: ProposalOperationType | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[ProposalOperationLog]:
        """条件に基づいて操作ログを取得する."""
        from sqlalchemy import text

        query_str = """
            SELECT id, proposal_id, proposal_title, operation_type,
                   user_id, operation_details, operated_at
            FROM proposal_operation_logs
            WHERE 1=1
        """
        params: dict[str, Any] = {}

        if user_id is not None:
            query_str += " AND user_id = :user_id"
            params["user_id"] = str(user_id)

        if operation_type is not None:
            query_str += " AND operation_type = :operation_type"
            params["operation_type"] = operation_type.value

        if start_date is not None:
            query_str += " AND operated_at >= :start_date"
            params["start_date"] = start_date

        if end_date is not None:
            query_str += " AND operated_at <= :end_date"
            params["end_date"] = end_date

        query_str += " ORDER BY operated_at DESC"

        result = await self.session.execute(text(query_str), params)
        rows = result.fetchall()

        logs = []
        for row in rows:
            logs.append(
                ProposalOperationLog(
                    id=row[0],
                    proposal_id=row[1],
                    proposal_title=row[2],
                    operation_type=ProposalOperationType(row[3]),
                    user_id=UUID(str(row[4])) if row[4] else None,
                    operation_details=row[5] or {},
                    operated_at=row[6],
                )
            )
        return logs

    async def get_statistics_by_user(
        self,
        user_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[UUID, int]:
        """ユーザー別の操作件数を集計する."""
        from sqlalchemy import text

        query_str = """
            SELECT user_id, COUNT(*) as count
            FROM proposal_operation_logs
            WHERE user_id IS NOT NULL
        """
        params: dict[str, Any] = {}

        if user_id is not None:
            query_str += " AND user_id = :user_id"
            params["user_id"] = str(user_id)

        if start_date is not None:
            query_str += " AND operated_at >= :start_date"
            params["start_date"] = start_date

        if end_date is not None:
            query_str += " AND operated_at <= :end_date"
            params["end_date"] = end_date

        query_str += " GROUP BY user_id"

        result = await self.session.execute(text(query_str), params)
        rows = result.fetchall()

        return {UUID(str(row[0])): row[1] for row in rows}

    async def get_timeline_statistics(
        self,
        user_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        interval: str = "day",
    ) -> list[dict[str, Any]]:
        """時系列の操作件数を集計する."""
        from sqlalchemy import text

        # PostgreSQL用の日付truncate
        date_trunc = f"date_trunc('{interval}', operated_at)"

        query_str = f"""
            SELECT {date_trunc} as date, COUNT(*) as count
            FROM proposal_operation_logs
            WHERE 1=1
        """
        params: dict[str, Any] = {}

        if user_id is not None:
            query_str += " AND user_id = :user_id"
            params["user_id"] = str(user_id)

        if start_date is not None:
            query_str += " AND operated_at >= :start_date"
            params["start_date"] = start_date

        if end_date is not None:
            query_str += " AND operated_at <= :end_date"
            params["end_date"] = end_date

        query_str += f" GROUP BY {date_trunc} ORDER BY {date_trunc}"

        result = await self.session.execute(text(query_str), params)
        rows = result.fetchall()

        return [
            {"date": row[0].strftime("%Y-%m-%d") if row[0] else None, "count": row[1]}
            for row in rows
        ]

    async def create(self, entity: ProposalOperationLog) -> ProposalOperationLog:
        """操作ログを作成する."""
        from sqlalchemy import text

        query = text("""
            INSERT INTO proposal_operation_logs
                (proposal_id, proposal_title, operation_type, user_id,
                 operation_details, operated_at)
            VALUES
                (:proposal_id, :proposal_title, :operation_type, :user_id,
                 :operation_details, :operated_at)
            RETURNING id, proposal_id, proposal_title, operation_type,
                      user_id, operation_details, operated_at
        """)

        import json

        result = await self.session.execute(
            query,
            {
                "proposal_id": entity.proposal_id,
                "proposal_title": entity.proposal_title,
                "operation_type": entity.operation_type.value,
                "user_id": str(entity.user_id) if entity.user_id else None,
                "operation_details": json.dumps(entity.operation_details),
                "operated_at": entity.operated_at,
            },
        )
        row = result.fetchone()
        await self.session.commit()

        if row:
            return ProposalOperationLog(
                id=row[0],
                proposal_id=row[1],
                proposal_title=row[2],
                operation_type=ProposalOperationType(row[3]),
                user_id=UUID(str(row[4])) if row[4] else None,
                operation_details=row[5] or {},
                operated_at=row[6],
            )

        raise RuntimeError("Failed to create proposal operation log")
