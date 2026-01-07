"""ExtractionLog repository implementation using SQLAlchemy."""

import logging

from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, Float, Integer, String, and_, cast, func
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql.sqltypes import Date

from src.domain.entities.extraction_log import EntityType, ExtractionLog
from src.domain.repositories.extraction_log_repository import (
    ExtractionLogRepository,
)
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.exceptions import DatabaseError
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


logger = logging.getLogger(__name__)

Base = declarative_base()


class ExtractionLogModel(Base):
    """SQLAlchemy model for extraction logs."""

    __tablename__ = "extraction_logs"

    id = Column(Integer, primary_key=True)
    # PostgreSQL ENUM型にマッピング（valueはEntityType.valueと一致）
    entity_type = Column(
        ENUM(
            "statement",
            "politician",
            "speaker",
            "conference_member",
            "parliamentary_group_member",
            name="entity_type",
            create_type=False,  # 既存のPostgreSQL ENUM型を使用
        ),
        nullable=False,
    )
    entity_id = Column(Integer, nullable=False)
    pipeline_version = Column(String(100), nullable=False)
    extracted_data = Column(JSONB, nullable=False)
    confidence_score = Column(Float, nullable=True)
    extraction_metadata = Column(JSONB, nullable=False, default={})
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ExtractionLogRepositoryImpl(
    BaseRepositoryImpl[ExtractionLog], ExtractionLogRepository
):
    """Implementation of ExtractionLogRepository using SQLAlchemy."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        """Initialize repository with database session.

        Args:
            session: AsyncSession or ISessionAdapter for database operations
        """
        super().__init__(session, ExtractionLog, ExtractionLogModel)

    async def get_by_entity(
        self,
        entity_type: EntityType,
        entity_id: int,
    ) -> list[ExtractionLog]:
        """Get all extraction logs for a specific entity.

        Args:
            entity_type: Type of the entity
            entity_id: ID of the entity

        Returns:
            List of extraction logs ordered by created_at descending

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            query = (
                select(self.model_class)
                .where(
                    and_(
                        self.model_class.entity_type == entity_type.value,
                        self.model_class.entity_id == entity_id,
                    )
                )
                .order_by(self.model_class.created_at.desc())
            )

            result = await self.session.execute(query)
            models = result.scalars().all()

            return [self._to_entity(model) for model in models]
        except SQLAlchemyError as e:
            logger.error(
                f"Failed to get extraction logs for "
                f"{entity_type.value}:{entity_id}: {e}"
            )
            raise DatabaseError(
                f"Failed to retrieve extraction logs for {entity_type.value}"
            ) from e

    async def get_by_pipeline_version(
        self,
        version: str,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[ExtractionLog]:
        """Get extraction logs by pipeline version.

        Args:
            version: Pipeline version
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of extraction logs ordered by created_at descending

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            query = select(self.model_class).where(
                self.model_class.pipeline_version == version
            )

            if offset is not None:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)

            query = query.order_by(self.model_class.created_at.desc())

            result = await self.session.execute(query)
            models = result.scalars().all()

            return [self._to_entity(model) for model in models]
        except SQLAlchemyError as e:
            logger.error(
                f"Failed to get extraction logs for pipeline version {version}: {e}"
            )
            raise DatabaseError(
                f"Failed to retrieve extraction logs for pipeline version {version}"
            ) from e

    async def get_by_entity_type(
        self,
        entity_type: EntityType,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[ExtractionLog]:
        """Get extraction logs by entity type.

        Args:
            entity_type: Type of the entity
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of extraction logs ordered by created_at descending

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            query = select(self.model_class).where(
                self.model_class.entity_type == entity_type.value
            )

            if offset is not None:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)

            query = query.order_by(self.model_class.created_at.desc())

            result = await self.session.execute(query)
            models = result.scalars().all()

            return [self._to_entity(model) for model in models]
        except SQLAlchemyError as e:
            logger.error(
                f"Failed to get extraction logs for "
                f"entity type {entity_type.value}: {e}"
            )
            raise DatabaseError(
                f"Failed to retrieve logs for entity type {entity_type.value}"
            ) from e

    async def get_latest_by_entity(
        self,
        entity_type: EntityType,
        entity_id: int,
    ) -> ExtractionLog | None:
        """Get the latest extraction log for a specific entity.

        Args:
            entity_type: Type of the entity
            entity_id: ID of the entity

        Returns:
            Latest extraction log or None if not found

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            query = (
                select(self.model_class)
                .where(
                    and_(
                        self.model_class.entity_type == entity_type.value,
                        self.model_class.entity_id == entity_id,
                    )
                )
                .order_by(self.model_class.created_at.desc())
                .limit(1)
            )

            result = await self.session.execute(query)
            model = result.scalar_one_or_none()

            if model:
                return self._to_entity(model)
            return None
        except SQLAlchemyError as e:
            logger.error(
                f"Failed to get latest extraction log for "
                f"{entity_type.value}:{entity_id}: {e}"
            )
            raise DatabaseError(
                f"Failed to retrieve latest extraction log for {entity_type.value}"
            ) from e

    async def search(
        self,
        entity_type: EntityType | None = None,
        pipeline_version: str | None = None,
        min_confidence_score: float | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[ExtractionLog]:
        """Search extraction logs with multiple filters.

        Args:
            entity_type: Filter by entity type
            pipeline_version: Filter by pipeline version
            min_confidence_score: Filter by minimum confidence score
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of extraction logs ordered by created_at descending

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            conditions: list[Any] = []

            if entity_type:
                conditions.append(self.model_class.entity_type == entity_type.value)
            if pipeline_version:
                conditions.append(self.model_class.pipeline_version == pipeline_version)
            if min_confidence_score is not None:
                conditions.append(
                    self.model_class.confidence_score >= min_confidence_score
                )

            query = select(self.model_class)
            if conditions:
                query = query.where(and_(*conditions))

            if offset is not None:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)

            query = query.order_by(self.model_class.created_at.desc())

            result = await self.session.execute(query)
            models = result.scalars().all()

            return [self._to_entity(model) for model in models]
        except SQLAlchemyError as e:
            logger.error(f"Failed to search extraction logs: {e}")
            raise DatabaseError("Failed to search extraction logs") from e

    async def count_by_entity_type(
        self,
        entity_type: EntityType,
    ) -> int:
        """Count extraction logs by entity type.

        Args:
            entity_type: Type of the entity

        Returns:
            Number of extraction logs

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            query = select(func.count(self.model_class.id)).where(
                self.model_class.entity_type == entity_type.value
            )

            result = await self.session.execute(query)
            return result.scalar() or 0
        except SQLAlchemyError as e:
            logger.error(
                f"Failed to count extraction logs for entity type "
                f"{entity_type.value}: {e}"
            )
            raise DatabaseError(
                f"Failed to count extraction logs for entity type {entity_type.value}"
            ) from e

    async def count_by_pipeline_version(
        self,
        version: str,
    ) -> int:
        """Count extraction logs by pipeline version.

        Args:
            version: Pipeline version

        Returns:
            Number of extraction logs

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            query = select(func.count(self.model_class.id)).where(
                self.model_class.pipeline_version == version
            )

            result = await self.session.execute(query)
            return result.scalar() or 0
        except SQLAlchemyError as e:
            logger.error(
                f"Failed to count extraction logs for pipeline version {version}: {e}"
            )
            raise DatabaseError(
                f"Failed to count extraction logs for pipeline version {version}"
            ) from e

    def _build_conditions(
        self,
        entity_type: EntityType | None = None,
        entity_id: int | None = None,
        pipeline_version: str | None = None,
        min_confidence_score: float | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[Any]:
        """検索条件を構築する。

        Args:
            entity_type: エンティティタイプ（フィルタ）
            entity_id: エンティティID（フィルタ）
            pipeline_version: パイプラインバージョン（フィルタ）
            min_confidence_score: 最小信頼度スコア（フィルタ）
            date_from: 検索開始日時（フィルタ）
            date_to: 検索終了日時（フィルタ）

        Returns:
            SQLAlchemy条件のリスト
        """
        conditions: list[Any] = []

        if entity_type:
            conditions.append(self.model_class.entity_type == entity_type.value)
        if entity_id is not None:
            conditions.append(self.model_class.entity_id == entity_id)
        if pipeline_version:
            conditions.append(self.model_class.pipeline_version == pipeline_version)
        if min_confidence_score is not None:
            conditions.append(self.model_class.confidence_score >= min_confidence_score)
        if date_from:
            conditions.append(self.model_class.created_at >= date_from)
        if date_to:
            conditions.append(self.model_class.created_at <= date_to)

        return conditions

    def _to_entity(self, model: Any) -> ExtractionLog:
        """Convert database model to domain entity.

        Args:
            model: Database model

        Returns:
            Domain entity
        """
        entity = ExtractionLog(
            entity_type=EntityType(model.entity_type),  # StringからEnumに変換
            entity_id=model.entity_id,
            pipeline_version=model.pipeline_version,
            extracted_data=model.extracted_data,
            confidence_score=model.confidence_score,
            extraction_metadata=model.extraction_metadata or {},
            id=model.id,
        )
        entity.created_at = model.created_at
        entity.updated_at = model.updated_at
        return entity

    def _to_model(self, entity: ExtractionLog) -> ExtractionLogModel:
        """Convert domain entity to database model.

        Args:
            entity: Domain entity

        Returns:
            Database model
        """
        return ExtractionLogModel(
            entity_type=entity.entity_type.value,  # EnumからStringに変換
            entity_id=entity.entity_id,
            pipeline_version=entity.pipeline_version,
            extracted_data=entity.extracted_data,
            confidence_score=entity.confidence_score,
            extraction_metadata=entity.extraction_metadata,
        )

    def _update_model(self, model: Any, entity: ExtractionLog) -> None:
        """Update model fields from entity.

        Note: ExtractionLog is immutable, so this method should not be used.
        If called, it will raise NotImplementedError.

        Args:
            model: Database model
            entity: Domain entity

        Raises:
            NotImplementedError: ExtractionLog is immutable
        """
        raise NotImplementedError(
            "ExtractionLog is immutable and cannot be updated. "
            "Create a new log entry instead."
        )

    async def search_with_date_range(
        self,
        entity_type: EntityType | None = None,
        entity_id: int | None = None,
        pipeline_version: str | None = None,
        min_confidence_score: float | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[ExtractionLog]:
        """日時範囲を含む複数の条件で抽出ログを検索する。

        Args:
            entity_type: エンティティタイプ（フィルタ）
            entity_id: エンティティID（フィルタ）
            pipeline_version: パイプラインバージョン（フィルタ）
            min_confidence_score: 最小信頼度スコア（フィルタ）
            date_from: 検索開始日時（フィルタ）
            date_to: 検索終了日時（フィルタ）
            limit: 取得件数の上限
            offset: 取得開始位置

        Returns:
            抽出ログのリスト（作成日時の降順）

        Raises:
            DatabaseError: データベース操作に失敗した場合
        """
        try:
            conditions = self._build_conditions(
                entity_type=entity_type,
                entity_id=entity_id,
                pipeline_version=pipeline_version,
                min_confidence_score=min_confidence_score,
                date_from=date_from,
                date_to=date_to,
            )

            query = select(self.model_class)
            if conditions:
                query = query.where(and_(*conditions))

            query = query.order_by(self.model_class.created_at.desc())

            if offset is not None:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)

            result = await self.session.execute(query)
            models = result.scalars().all()

            return [self._to_entity(model) for model in models]
        except SQLAlchemyError as e:
            logger.error(f"Failed to search extraction logs with date range: {e}")
            raise DatabaseError("Failed to search extraction logs") from e

    async def count_with_filters(
        self,
        entity_type: EntityType | None = None,
        entity_id: int | None = None,
        pipeline_version: str | None = None,
        min_confidence_score: float | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        """フィルター条件に一致するログ件数を取得する。

        Args:
            entity_type: エンティティタイプ（フィルタ）
            entity_id: エンティティID（フィルタ）
            pipeline_version: パイプラインバージョン（フィルタ）
            min_confidence_score: 最小信頼度スコア（フィルタ）
            date_from: 検索開始日時（フィルタ）
            date_to: 検索終了日時（フィルタ）

        Returns:
            ログ件数

        Raises:
            DatabaseError: データベース操作に失敗した場合
        """
        try:
            conditions = self._build_conditions(
                entity_type=entity_type,
                entity_id=entity_id,
                pipeline_version=pipeline_version,
                min_confidence_score=min_confidence_score,
                date_from=date_from,
                date_to=date_to,
            )

            query = select(func.count(self.model_class.id))
            if conditions:
                query = query.where(and_(*conditions))

            result = await self.session.execute(query)
            return result.scalar() or 0
        except SQLAlchemyError as e:
            logger.error(f"Failed to count extraction logs with filters: {e}")
            raise DatabaseError("Failed to count extraction logs") from e

    async def get_distinct_pipeline_versions(self) -> list[str]:
        """登録されている全てのパイプラインバージョンを取得する。

        Returns:
            パイプラインバージョンのリスト（重複なし）

        Raises:
            DatabaseError: データベース操作に失敗した場合
        """
        try:
            query = select(self.model_class.pipeline_version).distinct()

            result = await self.session.execute(query)
            versions = result.scalars().all()

            return list(versions)
        except SQLAlchemyError as e:
            logger.error(f"Failed to get distinct pipeline versions: {e}")
            raise DatabaseError("Failed to get pipeline versions") from e

    async def get_total_count(self) -> int:
        """全ての抽出ログ件数を取得する。

        Returns:
            総ログ件数

        Raises:
            DatabaseError: データベース操作に失敗した場合
        """
        try:
            query = select(func.count(self.model_class.id))

            result = await self.session.execute(query)
            return result.scalar() or 0
        except SQLAlchemyError as e:
            logger.error(f"Failed to get total count: {e}")
            raise DatabaseError("Failed to get total count") from e

    async def get_average_confidence_score(
        self,
        entity_type: EntityType | None = None,
        pipeline_version: str | None = None,
    ) -> float | None:
        """平均信頼度スコアを取得する。

        Args:
            entity_type: エンティティタイプ（フィルタ）
            pipeline_version: パイプラインバージョン（フィルタ）

        Returns:
            平均信頼度スコア、データがない場合はNone

        Raises:
            DatabaseError: データベース操作に失敗した場合
        """
        try:
            conditions = self._build_conditions(
                entity_type=entity_type,
                pipeline_version=pipeline_version,
            )

            query = select(func.avg(self.model_class.confidence_score))
            if conditions:
                query = query.where(and_(*conditions))

            result = await self.session.execute(query)
            avg_score = result.scalar()

            return float(avg_score) if avg_score is not None else None
        except SQLAlchemyError as e:
            logger.error(f"Failed to get average confidence score: {e}")
            raise DatabaseError("Failed to get average confidence score") from e

    async def get_count_by_date(
        self,
        entity_type: EntityType | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[tuple[datetime, int]]:
        """日別の抽出ログ件数を取得する。

        Args:
            entity_type: エンティティタイプ（フィルタ）
            date_from: 検索開始日時（フィルタ）
            date_to: 検索終了日時（フィルタ）

        Returns:
            (日付, 件数)のタプルのリスト

        Raises:
            DatabaseError: データベース操作に失敗した場合
        """
        try:
            conditions = self._build_conditions(
                entity_type=entity_type,
                date_from=date_from,
                date_to=date_to,
            )

            # 日付でグループ化してカウント
            date_column = cast(self.model_class.created_at, Date)
            query = (
                select(
                    date_column.label("date"),
                    func.count(self.model_class.id).label("count"),
                )
                .group_by(date_column)
                .order_by(date_column)
            )

            if conditions:
                query = query.where(and_(*conditions))

            result = await self.session.execute(query)
            rows = result.all()

            # rowはタプル(date, count)として取得される
            return_list: list[tuple[datetime, int]] = []
            for row in rows:
                date_val = datetime.combine(row[0], datetime.min.time())
                count_val = int(row[1])
                return_list.append((date_val, count_val))
            return return_list
        except SQLAlchemyError as e:
            logger.error(f"Failed to get count by date: {e}")
            raise DatabaseError("Failed to get count by date") from e

    async def get_count_grouped_by_entity_type(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[EntityType, int]:
        """エンティティタイプ別の件数を一括取得する。

        N+1クエリを避けるため、GROUP BYで一括取得する。

        Args:
            date_from: 検索開始日時（フィルタ）
            date_to: 検索終了日時（フィルタ）

        Returns:
            エンティティタイプをキー、件数を値とする辞書

        Raises:
            DatabaseError: データベース操作に失敗した場合
        """
        try:
            conditions = self._build_conditions(
                date_from=date_from,
                date_to=date_to,
            )

            query = select(
                self.model_class.entity_type,
                func.count(self.model_class.id).label("count"),
            ).group_by(self.model_class.entity_type)

            if conditions:
                query = query.where(and_(*conditions))

            result = await self.session.execute(query)
            rows = result.all()

            return {EntityType(row[0]): int(row[1]) for row in rows}
        except SQLAlchemyError as e:
            logger.error(f"Failed to get count grouped by entity type: {e}")
            raise DatabaseError("Failed to get count grouped by entity type") from e

    async def get_count_grouped_by_pipeline_version(
        self,
        entity_type: EntityType | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[str, int]:
        """パイプラインバージョン別の件数を一括取得する。

        N+1クエリを避けるため、GROUP BYで一括取得する。

        Args:
            entity_type: エンティティタイプ（フィルタ）
            date_from: 検索開始日時（フィルタ）
            date_to: 検索終了日時（フィルタ）

        Returns:
            パイプラインバージョンをキー、件数を値とする辞書

        Raises:
            DatabaseError: データベース操作に失敗した場合
        """
        try:
            conditions = self._build_conditions(
                entity_type=entity_type,
                date_from=date_from,
                date_to=date_to,
            )

            query = select(
                self.model_class.pipeline_version,
                func.count(self.model_class.id).label("count"),
            ).group_by(self.model_class.pipeline_version)

            if conditions:
                query = query.where(and_(*conditions))

            result = await self.session.execute(query)
            rows = result.all()

            return {str(row[0]): int(row[1]) for row in rows}
        except SQLAlchemyError as e:
            logger.error(f"Failed to get count grouped by pipeline version: {e}")
            raise DatabaseError(
                "Failed to get count grouped by pipeline version"
            ) from e

    async def get_avg_confidence_grouped_by_pipeline_version(
        self,
        entity_type: EntityType | None = None,
    ) -> dict[str, float]:
        """パイプラインバージョン別の平均信頼度を一括取得する。

        N+1クエリを避けるため、GROUP BYで一括取得する。

        Args:
            entity_type: エンティティタイプ（フィルタ）

        Returns:
            パイプラインバージョンをキー、平均信頼度を値とする辞書

        Raises:
            DatabaseError: データベース操作に失敗した場合
        """
        try:
            conditions = self._build_conditions(entity_type=entity_type)

            query = select(
                self.model_class.pipeline_version,
                func.avg(self.model_class.confidence_score).label("avg_confidence"),
            ).group_by(self.model_class.pipeline_version)

            if conditions:
                query = query.where(and_(*conditions))

            result = await self.session.execute(query)
            rows = result.all()

            return {
                str(row[0]): round(float(row[1]), 3) if row[1] is not None else 0.0
                for row in rows
            }
        except SQLAlchemyError as e:
            logger.error(
                f"Failed to get avg confidence grouped by pipeline version: {e}"
            )
            raise DatabaseError(
                "Failed to get avg confidence grouped by pipeline version"
            ) from e
