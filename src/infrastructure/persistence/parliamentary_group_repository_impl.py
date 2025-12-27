"""ParliamentaryGroup repository implementation using SQLAlchemy."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .parliamentary_group_membership_repository_impl import (
    ParliamentaryGroupMembershipRepositoryImpl,
)

from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.repositories.parliamentary_group_repository import (
    ParliamentaryGroupRepository as IParliamentaryGroupRepository,
)
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


class ParliamentaryGroupModel:
    """Parliamentary group database model (dynamic)."""

    id: int | None
    name: str
    conference_id: int
    url: str | None
    description: str | None
    is_active: bool

    def __init__(self, **kwargs: Any):
        for key, value in kwargs.items():
            setattr(self, key, value)


class ParliamentaryGroupRepositoryImpl(
    BaseRepositoryImpl[ParliamentaryGroup], IParliamentaryGroupRepository
):
    """Implementation of ParliamentaryGroupRepository using SQLAlchemy."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        super().__init__(session, ParliamentaryGroup, ParliamentaryGroupModel)

    async def create(self, entity: ParliamentaryGroup) -> ParliamentaryGroup:
        """Create a new parliamentary group using raw SQL."""
        query = text(
            """
            INSERT INTO parliamentary_groups (
                name, conference_id, url, description, is_active
            )
            VALUES (:name, :conference_id, :url, :description, :is_active)
            RETURNING id, name, conference_id, url, description, is_active
        """
        )

        result = await self.session.execute(
            query,
            {
                "name": entity.name,
                "conference_id": entity.conference_id,
                "url": entity.url,
                "description": entity.description,
                "is_active": entity.is_active,
            },
        )
        row = result.fetchone()

        if row:
            return self._row_to_entity(row)
        raise ValueError("Failed to create parliamentary group")

    async def update(self, entity: ParliamentaryGroup) -> ParliamentaryGroup:
        """Update an existing parliamentary group using raw SQL."""
        if not entity.id:
            raise ValueError("Entity must have an ID to update")

        query = text("""
            UPDATE parliamentary_groups
            SET name = :name,
                conference_id = :conference_id,
                url = :url,
                description = :description,
                is_active = :is_active
            WHERE id = :id
            RETURNING id, name, conference_id, url, description, is_active
        """)

        result = await self.session.execute(
            query,
            {
                "id": entity.id,
                "name": entity.name,
                "conference_id": entity.conference_id,
                "url": entity.url,
                "description": entity.description,
                "is_active": entity.is_active,
            },
        )
        row = result.fetchone()

        if row:
            return self._row_to_entity(row)
        raise ValueError(f"Parliamentary group with ID {entity.id} not found")

    async def get_by_name_and_conference(
        self, name: str, conference_id: int
    ) -> ParliamentaryGroup | None:
        """Get parliamentary group by name and conference."""
        query = text("""
            SELECT * FROM parliamentary_groups
            WHERE name = :name AND conference_id = :conf_id
            LIMIT 1
        """)

        result = await self.session.execute(
            query, {"name": name, "conf_id": conference_id}
        )
        row = result.fetchone()

        if row:
            return self._row_to_entity(row)
        return None

    async def get_by_conference_id(
        self, conference_id: int, active_only: bool = True
    ) -> list[ParliamentaryGroup]:
        """Get all parliamentary groups for a conference."""
        conditions = ["conference_id = :conf_id"]
        params: dict[str, Any] = {"conf_id": conference_id}

        if active_only:
            conditions.append("is_active = TRUE")

        query = text(f"""
            SELECT * FROM parliamentary_groups
            WHERE {" AND ".join(conditions)}
            ORDER BY name
        """)

        result = await self.session.execute(query, params)
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_active(self) -> list[ParliamentaryGroup]:
        """Get all active parliamentary groups."""
        query = text("""
            SELECT * FROM parliamentary_groups
            WHERE is_active = TRUE
            ORDER BY name
        """)

        result = await self.session.execute(query)
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_all(
        self, limit: int | None = None, offset: int | None = 0
    ) -> list[ParliamentaryGroup]:
        """Get all parliamentary groups."""
        query_text = """
            SELECT pg.*, c.name as conference_name, gb.name as governing_body_name
            FROM parliamentary_groups pg
            JOIN conferences c ON pg.conference_id = c.id
            JOIN governing_bodies gb ON c.governing_body_id = gb.id
            ORDER BY gb.name, c.name, pg.name
        """
        params = {}

        if limit is not None:
            query_text += " LIMIT :limit OFFSET :offset"
            params = {"limit": limit, "offset": offset or 0}

        result = await self.session.execute(
            text(query_text), params if params else None
        )
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_all_with_details(
        self,
        conference_id: int | None = None,
        active_only: bool = True,
        with_url_only: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Get all parliamentary groups with conference and governing body details.

        Returns dictionary format for CLI display purposes.

        Args:
            conference_id: Filter to specific conference (optional)
            active_only: Filter to only active groups
            with_url_only: Filter to only groups with URL set

        Returns:
            List of dictionaries with parliamentary group details
        """
        query_text = """
            SELECT pg.*, c.name as conference_name, gb.name as governing_body_name
            FROM parliamentary_groups pg
            JOIN conferences c ON pg.conference_id = c.id
            JOIN governing_bodies gb ON c.governing_body_id = gb.id
            WHERE 1=1
        """
        params: dict[str, Any] = {}

        if conference_id is not None:
            query_text += " AND pg.conference_id = :conference_id"
            params["conference_id"] = conference_id

        if active_only:
            query_text += " AND pg.is_active = true"

        if with_url_only:
            query_text += " AND pg.url IS NOT NULL"

        query_text += " ORDER BY gb.id, c.id, pg.name"

        result = await self.session.execute(text(query_text), params or None)
        rows = result.fetchall()

        # Convert rows to dictionaries
        if rows:
            keys = result.keys()
            return [dict(zip(keys, row, strict=False)) for row in rows]
        return []

    async def get_by_id(self, entity_id: int) -> ParliamentaryGroup | None:
        """Get parliamentary group by ID."""
        query = text("SELECT * FROM parliamentary_groups WHERE id = :id")
        result = await self.session.execute(query, {"id": entity_id})
        row = result.fetchone()

        if row:
            return self._row_to_entity(row)
        return None

    def _row_to_entity(self, row: Any) -> ParliamentaryGroup:
        """Convert database row to domain entity."""
        return ParliamentaryGroup(
            id=row.id,
            name=row.name,
            conference_id=row.conference_id,
            url=getattr(row, "url", None),
            description=getattr(row, "description", None),
            is_active=getattr(row, "is_active", True),
        )

    def _to_entity(self, model: ParliamentaryGroupModel) -> ParliamentaryGroup:
        """Convert database model to domain entity."""
        return ParliamentaryGroup(
            id=model.id,
            name=model.name,
            conference_id=model.conference_id,
            url=getattr(model, "url", None),
            description=model.description,
            is_active=model.is_active,
        )

    def _to_model(self, entity: ParliamentaryGroup) -> ParliamentaryGroupModel:
        """Convert domain entity to database model."""
        data = {
            "name": entity.name,
            "conference_id": entity.conference_id,
            "description": entity.description,
            "is_active": entity.is_active,
        }

        if entity.url is not None:
            data["url"] = entity.url
        if entity.id is not None:
            data["id"] = entity.id

        return ParliamentaryGroupModel(**data)

    def _update_model(
        self, model: ParliamentaryGroupModel, entity: ParliamentaryGroup
    ) -> None:
        """Update model fields from entity."""
        model.name = entity.name
        model.conference_id = entity.conference_id
        model.description = entity.description
        model.is_active = entity.is_active

        if entity.url is not None:
            model.url = entity.url


__all__ = [
    "ParliamentaryGroupRepositoryImpl",
    "ParliamentaryGroupMembershipRepositoryImpl",
]
