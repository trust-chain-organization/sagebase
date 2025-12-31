"""PoliticalParty repository implementation using SQLAlchemy."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.political_party import PoliticalParty
from src.domain.repositories.political_party_repository import (
    PoliticalPartyRepository as IPoliticalPartyRepository,
)
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


class PoliticalPartyModel:
    """Political party database model (dynamic)."""

    id: int | None
    name: str
    members_list_url: str | None

    def __init__(self, **kwargs: Any):
        for key, value in kwargs.items():
            setattr(self, key, value)


class PoliticalPartyRepositoryImpl(
    BaseRepositoryImpl[PoliticalParty], IPoliticalPartyRepository
):
    """Implementation of PoliticalPartyRepository using SQLAlchemy."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        super().__init__(session, PoliticalParty, PoliticalPartyModel)

    async def get_by_name(self, name: str) -> PoliticalParty | None:
        """Get political party by name."""
        query = text("""
            SELECT * FROM political_parties
            WHERE name = :name
            LIMIT 1
        """)

        result = await self.session.execute(query, {"name": name})
        row = result.fetchone()

        if row:
            return self._row_to_entity(row)
        return None

    async def get_with_members_url(self) -> list[PoliticalParty]:
        """Get political parties that have members list URL."""
        query = text("""
            SELECT * FROM political_parties
            WHERE members_list_url IS NOT NULL
            ORDER BY name
        """)

        result = await self.session.execute(query)
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def search_by_name(self, name_pattern: str) -> list[PoliticalParty]:
        """Search political parties by name pattern."""
        query = text("""
            SELECT * FROM political_parties
            WHERE name ILIKE :pattern
            ORDER BY name
        """)

        result = await self.session.execute(query, {"pattern": f"%{name_pattern}%"})
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_all(
        self, limit: int | None = None, offset: int | None = 0
    ) -> list[PoliticalParty]:
        """Get all political parties."""
        query_text = "SELECT * FROM political_parties ORDER BY name"
        params = {}

        if limit is not None:
            query_text += " LIMIT :limit OFFSET :offset"
            params = {"limit": limit, "offset": offset or 0}

        result = await self.session.execute(
            text(query_text), params if params else None
        )
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_by_id(self, entity_id: int) -> PoliticalParty | None:
        """Get political party by ID."""
        query = text("SELECT * FROM political_parties WHERE id = :id")
        result = await self.session.execute(query, {"id": entity_id})
        row = result.fetchone()

        if row:
            return self._row_to_entity(row)
        return None

    async def create(self, entity: PoliticalParty) -> PoliticalParty:
        """Create a new political party."""
        query = text("""
            INSERT INTO political_parties (name, members_list_url)
            VALUES (:name, :members_list_url)
            RETURNING id, name, members_list_url
        """)

        result = await self.session.execute(
            query,
            {
                "name": entity.name,
                "members_list_url": entity.members_list_url,
            },
        )
        row = result.fetchone()

        if row:
            return self._row_to_entity(row)
        raise RuntimeError("Failed to create political party")

    async def update(self, entity: PoliticalParty) -> PoliticalParty:
        """Update an existing political party."""
        if entity.id is None:
            raise ValueError("Cannot update entity without ID")

        query = text("""
            UPDATE political_parties
            SET name = :name, members_list_url = :members_list_url
            WHERE id = :id
            RETURNING id, name, members_list_url
        """)

        result = await self.session.execute(
            query,
            {
                "id": entity.id,
                "name": entity.name,
                "members_list_url": entity.members_list_url,
            },
        )
        row = result.fetchone()

        if row:
            return self._row_to_entity(row)
        raise RuntimeError(f"Failed to update political party with ID {entity.id}")

    def _row_to_entity(self, row: Any) -> PoliticalParty:
        """Convert database row to domain entity."""
        return PoliticalParty(
            id=row.id,
            name=row.name,
            members_list_url=getattr(row, "members_list_url", None),
        )

    def _to_entity(self, model: PoliticalPartyModel) -> PoliticalParty:
        """Convert database model to domain entity."""
        return PoliticalParty(
            id=model.id,
            name=model.name,
            members_list_url=model.members_list_url,
        )

    def _to_model(self, entity: PoliticalParty) -> PoliticalPartyModel:
        """Convert domain entity to database model."""
        data = {
            "name": entity.name,
            "members_list_url": entity.members_list_url,
        }

        if entity.id is not None:
            data["id"] = entity.id

        return PoliticalPartyModel(**data)

    def _update_model(self, model: PoliticalPartyModel, entity: PoliticalParty) -> None:
        """Update model fields from entity."""
        model.name = entity.name
        model.members_list_url = entity.members_list_url
