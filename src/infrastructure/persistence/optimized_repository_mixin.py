"""Mixin for optimized repository queries with eager loading and batching."""

from typing import TYPE_CHECKING, Any, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload


if TYPE_CHECKING:
    from typing import Protocol

    class HasSession(Protocol):
        session: AsyncSession


T = TypeVar("T")


class OptimizedRepositoryMixin:
    """Mixin to add optimized query methods to repositories."""

    session: (
        AsyncSession  # This attribute must be provided by the class using this mixin
    )

    async def get_with_relations(
        self,
        model_class: type[T],
        relations: list[str],
        filters: dict[str, Any] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[T]:
        """Get entities with eager loaded relationships.

        Args:
            model_class: The SQLAlchemy model class
            relations: List of relationship names to eager load
            filters: Optional filters to apply
            limit: Optional limit
            offset: Optional offset

        Returns:
            List of models with relationships loaded
        """
        query = select(model_class)

        # Add eager loading for relationships
        for relation in relations:
            if "." in relation:
                # Handle nested relationships (e.g., "conference.governing_body")
                # For nested relationships, we need to build the chain programmatically
                parts = relation.split(".")
                option = selectinload(getattr(model_class, parts[0]))
                for part in parts[1:]:
                    option = option.selectinload(part)  # type: ignore
                query = query.options(option)
            else:
                # Use joinedload for single relationships to reduce queries
                query = query.options(joinedload(getattr(model_class, relation)))

        # Apply filters
        if filters:
            for key, value in filters.items():
                query = query.where(getattr(model_class, key) == value)

        # Apply pagination
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)

        # Execute query
        result = await self.session.execute(query)
        return list(result.scalars().unique().all())

    async def batch_get_by_ids(
        self,
        model_class: type[T],
        ids: list[int],
        relations: list[str] | None = None,
    ) -> list[T]:
        """Get multiple entities by IDs in a single query.

        Args:
            model_class: The SQLAlchemy model class
            ids: List of IDs to fetch
            relations: Optional relationships to eager load

        Returns:
            List of models
        """
        if not ids:
            return []

        query = select(model_class).where(model_class.id.in_(ids))  # type: ignore

        # Add eager loading if specified
        if relations:
            for relation in relations:
                query = query.options(selectinload(getattr(model_class, relation)))

        result = await self.session.execute(query)
        return list(result.scalars().unique().all())

    async def get_with_pagination(
        self,
        model_class: type[T],
        page: int = 1,
        per_page: int = 50,
        filters: dict[str, Any] | None = None,
        order_by: str | None = None,
        relations: list[str] | None = None,
    ) -> tuple[list[T], int]:
        """Get paginated results with total count.

        Args:
            model_class: The SQLAlchemy model class
            page: Page number (1-indexed)
            per_page: Items per page
            filters: Optional filters
            order_by: Optional order by clause
            relations: Optional relationships to eager load

        Returns:
            Tuple of (items, total_count)
        """
        # Base query
        query = select(model_class)
        count_query = select(model_class)

        # Apply filters
        if filters:
            for key, value in filters.items():
                condition = getattr(model_class, key) == value
                query = query.where(condition)
                count_query = count_query.where(condition)

        # Add eager loading
        if relations:
            for relation in relations:
                query = query.options(selectinload(getattr(model_class, relation)))

        # Apply ordering
        if order_by:
            if order_by.startswith("-"):
                query = query.order_by(getattr(model_class, order_by[1:]).desc())
            else:
                query = query.order_by(getattr(model_class, order_by))

        # Apply pagination
        offset = (page - 1) * per_page
        query = query.limit(per_page).offset(offset)

        # Get items
        result = await self.session.execute(query)
        items = list(result.scalars().unique().all())

        # Get total count
        from sqlalchemy import func

        count_result = await self.session.execute(
            select(func.count()).select_from(count_query.subquery())
        )
        total_count = count_result.scalar() or 0

        return items, total_count
