"""LLM processing history repository implementation."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import declarative_base

from src.domain.entities.llm_processing_history import (
    LLMProcessingHistory,
    ProcessingStatus,
    ProcessingType,
)
from src.domain.repositories.llm_processing_history_repository import (
    LLMProcessingHistoryRepository,
)
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


Base = declarative_base()


class LLMProcessingHistoryModel(Base):
    """SQLAlchemy model for LLM processing history."""

    __tablename__ = "llm_processing_history"

    id = Column(Integer, primary_key=True)
    processing_type = Column(String(50), nullable=False)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=False)
    prompt_template = Column(Text, nullable=False)
    prompt_variables = Column(JSON, nullable=False, default={})
    input_reference_type = Column(String(50), nullable=False)
    input_reference_id = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    result = Column(JSON)
    error_message = Column(Text)
    processing_metadata = Column(JSON, nullable=False, default={})
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_by = Column(String(100), default="system")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class LLMProcessingHistoryRepositoryImpl(
    BaseRepositoryImpl[LLMProcessingHistory], LLMProcessingHistoryRepository
):
    """Implementation of LLM processing history repository using SQLAlchemy."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        super().__init__(session, LLMProcessingHistory, LLMProcessingHistoryModel)

    async def get_by_processing_type(
        self,
        processing_type: ProcessingType,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[LLMProcessingHistory]:
        """Get processing history by type."""
        query = select(self.model_class).where(
            self.model_class.processing_type == processing_type.value
        )

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        query = query.order_by(self.model_class.created_at.desc())
        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def get_by_status(
        self,
        status: ProcessingStatus,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[LLMProcessingHistory]:
        """Get processing history by status."""
        query = select(self.model_class).where(self.model_class.status == status.value)

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        query = query.order_by(self.model_class.created_at.desc())
        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def get_by_model(
        self,
        model_name: str,
        model_version: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[LLMProcessingHistory]:
        """Get processing history by model name and optionally version."""
        conditions = [self.model_class.model_name == model_name]
        if model_version:
            conditions.append(self.model_class.model_version == model_version)

        query = select(self.model_class).where(and_(*conditions))

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        query = query.order_by(self.model_class.created_at.desc())
        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def get_by_input_reference(
        self,
        input_reference_type: str,
        input_reference_id: int,
    ) -> list[LLMProcessingHistory]:
        """Get all processing history for a specific input entity."""
        query = select(self.model_class).where(
            and_(
                self.model_class.input_reference_type == input_reference_type,
                self.model_class.input_reference_id == input_reference_id,
            )
        )

        query = query.order_by(self.model_class.created_at.desc())
        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        processing_type: ProcessingType | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[LLMProcessingHistory]:
        """Get processing history within a date range."""
        conditions = [
            self.model_class.created_at >= start_date,
            self.model_class.created_at <= end_date,
        ]

        if processing_type:
            conditions.append(self.model_class.processing_type == processing_type.value)

        query = select(self.model_class).where(and_(*conditions))

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        query = query.order_by(self.model_class.created_at.desc())
        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def get_latest_by_input(
        self,
        input_reference_type: str,
        input_reference_id: int,
        processing_type: ProcessingType | None = None,
    ) -> LLMProcessingHistory | None:
        """Get the latest processing history for a specific input."""
        conditions = [
            self.model_class.input_reference_type == input_reference_type,
            self.model_class.input_reference_id == input_reference_id,
        ]

        if processing_type:
            conditions.append(self.model_class.processing_type == processing_type.value)

        query = (
            select(self.model_class)
            .where(and_(*conditions))
            .order_by(self.model_class.created_at.desc())
            .limit(1)
        )

        result = await self.session.execute(query)
        model = result.scalar_one_or_none()

        if model:
            return self._to_entity(model)
        return None

    async def count_by_status(
        self,
        status: ProcessingStatus,
        processing_type: ProcessingType | None = None,
    ) -> int:
        """Count processing history by status."""
        from sqlalchemy import func

        conditions = [self.model_class.status == status.value]
        if processing_type:
            conditions.append(self.model_class.processing_type == processing_type.value)

        query = select(func.count(self.model_class.id)).where(and_(*conditions))
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def search(
        self,
        processing_type: ProcessingType | None = None,
        model_name: str | None = None,
        status: ProcessingStatus | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[LLMProcessingHistory]:
        """Search processing history with multiple filters."""
        conditions: list[Any] = []

        if processing_type:
            conditions.append(self.model_class.processing_type == processing_type.value)
        if model_name:
            conditions.append(self.model_class.model_name == model_name)
        if status:
            conditions.append(self.model_class.status == status.value)
        if start_date:
            conditions.append(self.model_class.created_at >= start_date)
        if end_date:
            conditions.append(self.model_class.created_at <= end_date)

        query = select(self.model_class)
        if conditions:
            query = query.where(and_(*conditions))

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        query = query.order_by(self.model_class.created_at.desc())
        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    def _to_entity(self, model: Any) -> LLMProcessingHistory:
        """Convert database model to domain entity."""
        entity = LLMProcessingHistory(
            processing_type=ProcessingType(model.processing_type),
            model_name=model.model_name,
            model_version=model.model_version,
            prompt_template=model.prompt_template,
            prompt_variables=model.prompt_variables or {},
            input_reference_type=model.input_reference_type,
            input_reference_id=model.input_reference_id,
            status=ProcessingStatus(model.status),
            result=model.result,
            error_message=model.error_message,
            processing_metadata=model.processing_metadata or {},
            started_at=model.started_at,
            completed_at=model.completed_at,
            created_by=getattr(model, "created_by", "system"),
            id=model.id,
        )
        entity.created_at = model.created_at
        entity.updated_at = model.updated_at
        return entity

    def _to_model(self, entity: LLMProcessingHistory) -> LLMProcessingHistoryModel:
        """Convert domain entity to database model."""
        return LLMProcessingHistoryModel(
            processing_type=entity.processing_type.value,
            model_name=entity.model_name,
            model_version=entity.model_version,
            prompt_template=entity.prompt_template,
            prompt_variables=entity.prompt_variables,
            input_reference_type=entity.input_reference_type,
            input_reference_id=entity.input_reference_id,
            status=entity.status.value,
            result=entity.result,
            error_message=entity.error_message,
            processing_metadata=entity.processing_metadata,
            started_at=entity.started_at,
            completed_at=entity.completed_at,
            created_by=entity.created_by,
        )

    def _update_model(self, model: Any, entity: LLMProcessingHistory) -> None:
        """Update model fields from entity."""
        model.processing_type = entity.processing_type.value
        model.model_name = entity.model_name
        model.model_version = entity.model_version
        model.prompt_template = entity.prompt_template
        model.prompt_variables = entity.prompt_variables
        model.input_reference_type = entity.input_reference_type
        model.input_reference_id = entity.input_reference_id
        model.status = entity.status.value
        model.result = entity.result
        model.error_message = entity.error_message
        model.processing_metadata = entity.processing_metadata
        model.started_at = entity.started_at
        model.completed_at = entity.completed_at
        model.created_by = entity.created_by
