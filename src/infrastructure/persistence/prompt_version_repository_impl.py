"""Prompt version repository implementation."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    ARRAY,
    JSON,
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    and_,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import declarative_base

from src.domain.entities.prompt_version import PromptVersion
from src.domain.repositories.prompt_version_repository import PromptVersionRepository
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


Base = declarative_base()


class PromptVersionModel(Base):
    """SQLAlchemy model for prompt versions."""

    __tablename__ = "prompt_versions"

    id = Column(Integer, primary_key=True)
    prompt_key = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False)
    template = Column(Text, nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, nullable=False, default=True)
    variables = Column(ARRAY(String))
    prompt_metadata = Column(JSON, nullable=False, default={})
    created_by = Column(String(100))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class PromptVersionRepositoryImpl(
    BaseRepositoryImpl[PromptVersion], PromptVersionRepository
):
    """Implementation of prompt version repository using SQLAlchemy."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        super().__init__(session, PromptVersion, PromptVersionModel)

    async def get_active_version(self, prompt_key: str) -> PromptVersion | None:
        """Get the currently active version for a prompt key."""
        query = select(self.model_class).where(
            and_(
                self.model_class.prompt_key == prompt_key,
                self.model_class.is_active.is_(True),
            )
        )

        result = await self.session.execute(query)
        model = result.scalar_one_or_none()

        if model:
            return self._to_entity(model)
        return None

    async def get_by_key_and_version(
        self, prompt_key: str, version: str
    ) -> PromptVersion | None:
        """Get a specific version of a prompt."""
        query = select(self.model_class).where(
            and_(
                self.model_class.prompt_key == prompt_key,
                self.model_class.version == version,
            )
        )

        result = await self.session.execute(query)
        model = result.scalar_one_or_none()

        if model:
            return self._to_entity(model)
        return None

    async def get_versions_by_key(
        self, prompt_key: str, limit: int | None = None
    ) -> list[PromptVersion]:
        """Get all versions for a specific prompt key."""
        query = (
            select(self.model_class)
            .where(self.model_class.prompt_key == prompt_key)
            .order_by(self.model_class.created_at.desc())
        )

        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def get_all_active_versions(self) -> list[PromptVersion]:
        """Get all active prompt versions."""
        query = (
            select(self.model_class)
            .where(self.model_class.is_active.is_(True))
            .order_by(self.model_class.prompt_key)
        )

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def activate_version(self, prompt_key: str, version: str) -> bool:
        """Activate a specific version of a prompt."""
        # First, check if the version exists
        existing_query = select(self.model_class).where(
            and_(
                self.model_class.prompt_key == prompt_key,
                self.model_class.version == version,
            )
        )
        result = await self.session.execute(existing_query)
        model = result.scalar_one_or_none()

        if not model:
            return False

        # Deactivate all other versions
        await self.deactivate_all_versions(prompt_key)

        # Activate the requested version
        model.is_active = True
        await self.session.commit()

        return True

    async def deactivate_all_versions(self, prompt_key: str) -> int:
        """Deactivate all versions of a prompt."""
        query = select(self.model_class).where(
            and_(
                self.model_class.prompt_key == prompt_key,
                self.model_class.is_active.is_(True),
            )
        )

        result = await self.session.execute(query)
        models = result.scalars().all()

        count = 0
        for model in models:
            model.is_active = False
            count += 1

        if count > 0:
            await self.session.commit()

        return count

    async def create_version(
        self,
        prompt_key: str,
        template: str,
        version: str,
        description: str | None = None,
        variables: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        created_by: str | None = None,
        activate: bool = True,
    ) -> PromptVersion:
        """Create a new prompt version."""
        # Create the entity
        entity = PromptVersion(
            prompt_key=prompt_key,
            template=template,
            version=version,
            description=description,
            is_active=activate,
            variables=variables or [],
            metadata=metadata or {},
            created_by=created_by,
        )

        # If activating, deactivate other versions first
        if activate:
            await self.deactivate_all_versions(prompt_key)

        # Save the entity
        return await self.create(entity)

    async def search(
        self,
        prompt_key: str | None = None,
        is_active: bool | None = None,
        created_by: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[PromptVersion]:
        """Search prompt versions with filters."""
        conditions: list[Any] = []

        if prompt_key:
            conditions.append(self.model_class.prompt_key == prompt_key)
        if is_active is not None:
            conditions.append(self.model_class.is_active == is_active)
        if created_by:
            conditions.append(self.model_class.created_by == created_by)

        query = select(self.model_class)
        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(self.model_class.created_at.desc())

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    def _to_entity(self, model: Any) -> PromptVersion:
        """Convert database model to domain entity."""
        entity = PromptVersion(
            prompt_key=model.prompt_key,
            template=model.template,
            version=model.version,
            description=model.description,
            is_active=model.is_active,
            variables=model.variables or [],
            metadata=model.prompt_metadata or {},
            created_by=model.created_by,
            id=model.id,
        )
        entity.created_at = model.created_at
        entity.updated_at = model.updated_at
        return entity

    def _to_model(self, entity: PromptVersion) -> PromptVersionModel:
        """Convert domain entity to database model."""
        return PromptVersionModel(
            prompt_key=entity.prompt_key,
            template=entity.template,
            version=entity.version,
            description=entity.description,
            is_active=entity.is_active,
            variables=entity.variables,
            prompt_metadata=entity.metadata,
            created_by=entity.created_by,
        )

    def _update_model(self, model: Any, entity: PromptVersion) -> None:
        """Update model fields from entity."""
        model.prompt_key = entity.prompt_key
        model.template = entity.template
        model.version = entity.version
        model.description = entity.description
        model.is_active = entity.is_active
        model.variables = entity.variables
        model.prompt_metadata = entity.metadata
        model.created_by = entity.created_by
