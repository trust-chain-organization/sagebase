"""Base repository implementation for infrastructure layer."""

from typing import Any

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.domain.entities.base import BaseEntity
from src.domain.repositories.base import BaseRepository
from src.domain.repositories.session_adapter import ISessionAdapter


class BaseRepositoryImpl[T: BaseEntity](BaseRepository[T]):
    """Base repository implementation using ISessionAdapter.

    This class provides generic CRUD operations using the ISessionAdapter
    interface, enabling dependency inversion and testability. All operations
    use the session adapter methods, avoiding direct SQLAlchemy dependencies.

    The ISessionAdapter interface allows for flexible session management,
    supporting both async and sync sessions through adapters. This design
    follows the Dependency Inversion Principle, where the domain defines
    the interface and infrastructure provides implementations.

    Type Parameters:
        T: Domain entity type that extends BaseEntity

    Attributes:
        session: Database session (AsyncSession or ISessionAdapter)
        entity_class: Domain entity class for type conversions
        model_class: Database model class for ORM operations

    Note:
        Subclasses must implement the conversion methods:
        _to_entity(), _to_model(), and _update_model()
    """

    def __init__(
        self,
        session: AsyncSession | ISessionAdapter,
        entity_class: type[T],
        model_class: type[Any],
    ):
        self.session = session
        self.entity_class = entity_class
        self.model_class = model_class

    async def get_by_id(self, entity_id: int) -> T | None:
        """Get entity by ID."""
        result = await self.session.get(self.model_class, entity_id)
        if result:
            return self._to_entity(result)
        return None

    async def get_all(
        self, limit: int | None = None, offset: int | None = None
    ) -> list[T]:
        """Get all entities with optional pagination."""
        query = select(self.model_class)

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def create(self, entity: T) -> T:
        """Create a new entity."""
        model = self._to_model(entity)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def update(self, entity: T) -> T:
        """Update an existing entity."""
        if not entity.id:
            raise ValueError("Entity must have an ID to update")

        # Get existing model
        model = await self.session.get(self.model_class, entity.id)
        if not model:
            raise ValueError(f"Entity with ID {entity.id} not found")

        # Update fields
        self._update_model(model, entity)

        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def delete(self, entity_id: int) -> bool:
        """Delete an entity by ID."""
        model = await self.session.get(self.model_class, entity_id)
        if not model:
            return False

        await self.session.delete(model)
        await self.session.flush()
        return True

    async def count(self) -> int:
        """Count total number of entities."""
        query = select(func.count()).select_from(self.model_class)
        result = await self.session.execute(query)
        count = result.scalar()
        return count if count is not None else 0

    def _to_entity(self, model: Any) -> T:
        """Convert database model to domain entity."""
        raise NotImplementedError("Subclass must implement _to_entity")

    def _to_model(self, entity: T) -> Any:
        """Convert domain entity to database model."""
        raise NotImplementedError("Subclass must implement _to_model")

    def _update_model(self, model: Any, entity: T) -> None:
        """Update model fields from entity."""
        raise NotImplementedError("Subclass must implement _update_model")
