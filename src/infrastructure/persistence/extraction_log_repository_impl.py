"""ExtractionLog repository implementation using SQLAlchemy."""

import logging

from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, Float, Integer, String, and_, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import declarative_base

from src.domain.entities.extraction_log import EntityType, ExtractionLog
from src.domain.repositories.extraction_log_repository import (
    ExtractionLogRepository,
)
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


logger = logging.getLogger(__name__)

Base = declarative_base()


class ExtractionLogModel(Base):
    """SQLAlchemy model for extraction logs."""

    __tablename__ = "extraction_logs"

    id = Column(Integer, primary_key=True)
    entity_type = Column(String(50), nullable=False)
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
        """
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
        """
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
        """
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
        """
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
        """
        conditions: list[Any] = []

        if entity_type:
            conditions.append(self.model_class.entity_type == entity_type.value)
        if pipeline_version:
            conditions.append(self.model_class.pipeline_version == pipeline_version)
        if min_confidence_score is not None:
            conditions.append(self.model_class.confidence_score >= min_confidence_score)

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

    async def count_by_entity_type(
        self,
        entity_type: EntityType,
    ) -> int:
        """Count extraction logs by entity type.

        Args:
            entity_type: Type of the entity

        Returns:
            Number of extraction logs
        """
        query = select(func.count(self.model_class.id)).where(
            self.model_class.entity_type == entity_type.value
        )

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def count_by_pipeline_version(
        self,
        version: str,
    ) -> int:
        """Count extraction logs by pipeline version.

        Args:
            version: Pipeline version

        Returns:
            Number of extraction logs
        """
        query = select(func.count(self.model_class.id)).where(
            self.model_class.pipeline_version == version
        )

        result = await self.session.execute(query)
        return result.scalar() or 0

    def _to_entity(self, model: Any) -> ExtractionLog:
        """Convert database model to domain entity.

        Args:
            model: Database model

        Returns:
            Domain entity
        """
        entity = ExtractionLog(
            entity_type=EntityType(model.entity_type),
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
            entity_type=entity.entity_type.value,
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
