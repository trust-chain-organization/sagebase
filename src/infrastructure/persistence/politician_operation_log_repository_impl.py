"""政治家操作ログリポジトリ実装."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.politician_operation_log import (
    PoliticianOperationLog,
    PoliticianOperationType,
)
from src.domain.repositories.politician_operation_log_repository import (
    PoliticianOperationLogRepository,
)
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl
from src.infrastructure.persistence.sqlalchemy_models import (
    PoliticianOperationLogModel,
)


class PoliticianOperationLogRepositoryImpl(
    BaseRepositoryImpl[PoliticianOperationLog], PoliticianOperationLogRepository
):
    """政治家操作ログリポジトリ実装."""

    def __init__(self, session: AsyncSession):
        super().__init__(
            session=session,
            entity_class=PoliticianOperationLog,
            model_class=PoliticianOperationLogModel,
        )

    def _to_entity(self, model: PoliticianOperationLogModel) -> PoliticianOperationLog:
        """モデルをエンティティに変換."""
        return PoliticianOperationLog(
            id=model.id,
            politician_id=model.politician_id,
            politician_name=model.politician_name,
            operation_type=PoliticianOperationType(model.operation_type),
            user_id=model.user_id,
            operation_details=model.operation_details or {},
            operated_at=model.operated_at,
        )

    def _to_model(self, entity: PoliticianOperationLog) -> PoliticianOperationLogModel:
        """エンティティをモデルに変換."""
        return PoliticianOperationLogModel(
            id=entity.id,
            politician_id=entity.politician_id,
            politician_name=entity.politician_name,
            operation_type=entity.operation_type.value,
            user_id=entity.user_id,
            operation_details=entity.operation_details,
            operated_at=entity.operated_at,
        )

    def _update_model(
        self, model: PoliticianOperationLogModel, entity: PoliticianOperationLog
    ) -> None:
        """モデルを更新."""
        model.politician_id = entity.politician_id
        model.politician_name = entity.politician_name
        model.operation_type = entity.operation_type.value
        model.user_id = entity.user_id
        model.operation_details = entity.operation_details
        model.operated_at = entity.operated_at

    async def find_by_user(
        self, user_id: UUID | None = None
    ) -> list[PoliticianOperationLog]:
        """指定されたユーザーIDの操作ログを取得する."""
        query = select(PoliticianOperationLogModel)

        if user_id is not None:
            query = query.where(PoliticianOperationLogModel.user_id == user_id)

        query = query.order_by(PoliticianOperationLogModel.operated_at.desc())

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def find_by_filters(
        self,
        user_id: UUID | None = None,
        operation_type: PoliticianOperationType | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[PoliticianOperationLog]:
        """条件に基づいて操作ログを取得する."""
        query = select(PoliticianOperationLogModel)

        if user_id is not None:
            query = query.where(PoliticianOperationLogModel.user_id == user_id)

        if operation_type is not None:
            query = query.where(
                PoliticianOperationLogModel.operation_type == operation_type.value
            )

        if start_date is not None:
            query = query.where(PoliticianOperationLogModel.operated_at >= start_date)

        if end_date is not None:
            query = query.where(PoliticianOperationLogModel.operated_at <= end_date)

        query = query.order_by(PoliticianOperationLogModel.operated_at.desc())

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def get_statistics_by_user(
        self,
        user_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[UUID, int]:
        """ユーザー別の操作件数を集計する."""
        query = select(
            PoliticianOperationLogModel.user_id,
            func.count(PoliticianOperationLogModel.id).label("count"),
        )

        if user_id is not None:
            query = query.where(PoliticianOperationLogModel.user_id == user_id)

        if start_date is not None:
            query = query.where(PoliticianOperationLogModel.operated_at >= start_date)

        if end_date is not None:
            query = query.where(PoliticianOperationLogModel.operated_at <= end_date)

        # user_idがNULLのログは集計から除外
        query = query.where(PoliticianOperationLogModel.user_id.isnot(None))
        query = query.group_by(PoliticianOperationLogModel.user_id)

        result = await self.session.execute(query)
        rows = result.all()

        return {row[0]: row[1] for row in rows}

    async def get_timeline_statistics(
        self,
        user_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        interval: str = "day",
    ) -> list[dict[str, Any]]:
        """時系列の操作件数を集計する."""
        # PostgreSQL用の日付truncate関数
        if interval == "day":
            date_trunc = func.date_trunc("day", PoliticianOperationLogModel.operated_at)
        elif interval == "week":
            date_trunc = func.date_trunc(
                "week", PoliticianOperationLogModel.operated_at
            )
        elif interval == "month":
            date_trunc = func.date_trunc(
                "month", PoliticianOperationLogModel.operated_at
            )
        else:
            date_trunc = func.date_trunc("day", PoliticianOperationLogModel.operated_at)

        query = select(
            date_trunc.label("date"),
            func.count(PoliticianOperationLogModel.id).label("count"),
        )

        if user_id is not None:
            query = query.where(PoliticianOperationLogModel.user_id == user_id)

        if start_date is not None:
            query = query.where(PoliticianOperationLogModel.operated_at >= start_date)

        if end_date is not None:
            query = query.where(PoliticianOperationLogModel.operated_at <= end_date)

        query = query.group_by(date_trunc).order_by(date_trunc)

        result = await self.session.execute(query)
        rows = result.all()

        return [
            {"date": row[0].strftime("%Y-%m-%d") if row[0] else None, "count": row[1]}
            for row in rows
        ]
