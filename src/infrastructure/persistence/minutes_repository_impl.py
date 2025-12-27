"""Minutes repository implementation."""

from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, Integer, String, func, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import declarative_base

from src.domain.entities.minutes import Minutes
from src.domain.repositories.minutes_repository import MinutesRepository
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


Base = declarative_base()


class MinutesModel(Base):
    """SQLAlchemy model for minutes."""

    __tablename__ = "minutes"

    id = Column(Integer, primary_key=True)
    meeting_id = Column(Integer, nullable=False)
    url = Column(String)
    processed_at = Column(DateTime)


class MinutesRepositoryImpl(BaseRepositoryImpl[Minutes], MinutesRepository):
    """Implementation of MinutesRepository using SQLAlchemy."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        """Initialize repository with async session or session adapter."""
        super().__init__(session, Minutes, MinutesModel)

    async def get_by_meeting(self, meeting_id: int) -> Minutes | None:
        """Get minutes by meeting ID."""
        query = select(MinutesModel).where(MinutesModel.meeting_id == meeting_id)
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()

        if model:
            return self._to_entity(model)
        return None

    async def get_unprocessed(self, limit: int | None = None) -> list[Minutes]:
        """Get minutes that haven't been processed yet."""
        query = select(MinutesModel).where(MinutesModel.processed_at.is_(None))

        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def mark_processed(self, minutes_id: int) -> bool:
        """Mark minutes as processed."""
        stmt = (
            update(MinutesModel)
            .where(MinutesModel.id == minutes_id)
            .values(processed_at=datetime.utcnow())
        )

        result = await self.session.execute(stmt)
        await self.session.commit()

        return result.rowcount > 0

    async def count(self) -> int:
        """Count total number of minutes."""
        query = text("SELECT COUNT(*) FROM minutes")
        result = await self.session.execute(query)
        count = result.scalar()
        return count if count is not None else 0

    async def count_processed(self) -> int:
        """Count minutes that have been processed (processed_at IS NOT NULL)."""
        query = select(func.count()).where(MinutesModel.processed_at.is_not(None))
        result = await self.session.execute(query)
        count = result.scalar()
        return count if count is not None else 0

    def _to_entity(self, model: Any) -> Minutes:
        """Convert SQLAlchemy model to domain entity."""
        return Minutes(
            id=model.id,
            meeting_id=model.meeting_id,
            url=model.url,
            processed_at=model.processed_at,
        )

    def _to_model(self, entity: Minutes) -> Any:
        """Convert domain entity to SQLAlchemy model."""
        data = {
            "meeting_id": entity.meeting_id,
            "url": entity.url,
            "processed_at": entity.processed_at,
        }
        if entity.id:
            data["id"] = entity.id
        return MinutesModel(**data)

    def _update_model(self, model: Any, entity: Minutes) -> None:
        """Update SQLAlchemy model from domain entity."""
        model.meeting_id = entity.meeting_id
        model.url = entity.url
        model.processed_at = entity.processed_at
