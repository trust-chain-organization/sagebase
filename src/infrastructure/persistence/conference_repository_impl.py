"""Conference repository implementation using SQLAlchemy."""

import logging

from datetime import datetime
from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.conference import Conference
from src.domain.repositories.conference_repository import ConferenceRepository
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.exceptions import (
    DatabaseError,
    RecordNotFoundError,
    UpdateError,
)
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


logger = logging.getLogger(__name__)


class ConferenceModel(PydanticBaseModel):
    """Conference database model."""

    id: int | None = None
    name: str
    type: str | None = None
    governing_body_id: int
    members_introduction_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        arbitrary_types_allowed = True


class ConferenceRepositoryImpl(BaseRepositoryImpl[Conference], ConferenceRepository):
    """Conference repository implementation using SQLAlchemy."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        """Initialize repository with database session.

        Args:
            session: AsyncSession for database operations
        """
        super().__init__(
            session=session,
            entity_class=Conference,
            model_class=ConferenceModel,
        )

    async def get_by_name_and_governing_body(
        self, name: str, governing_body_id: int
    ) -> Conference | None:
        """Get conference by name and governing body.

        Args:
            name: Conference name
            governing_body_id: Governing body ID

        Returns:
            Conference entity or None if not found
        """
        try:
            query = text("""
                SELECT
                    id,
                    name,
                    type,
                    governing_body_id,
                    members_introduction_url,
                    created_at,
                    updated_at
                FROM conferences
                WHERE name = :name
                AND governing_body_id = :governing_body_id
            """)

            result = await self.session.execute(
                query, {"name": name, "governing_body_id": governing_body_id}
            )
            row = result.fetchone()

            if row:
                # Use row._asdict() or _mapping if available, else convert to dict
                if hasattr(row, "_asdict"):
                    row_dict = row._asdict()  # type: ignore[attr-defined]
                elif hasattr(row, "_mapping"):
                    row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                else:
                    row_dict = dict(row)
                return self._dict_to_entity(row_dict)
            return None

        except SQLAlchemyError as e:
            logger.error(f"Database error getting conference: {e}")
            raise DatabaseError(
                "Failed to get conference by name and governing body",
                {"name": name, "governing_body_id": governing_body_id, "error": str(e)},
            ) from e

    async def get_by_governing_body(self, governing_body_id: int) -> list[Conference]:
        """Get all conferences for a governing body.

        Args:
            governing_body_id: Governing body ID

        Returns:
            List of Conference entities
        """
        try:
            query = text("""
                SELECT
                    id,
                    name,
                    type,
                    governing_body_id,
                    members_introduction_url,
                    created_at,
                    updated_at
                FROM conferences
                WHERE governing_body_id = :governing_body_id
                ORDER BY name
            """)

            result = await self.session.execute(
                query, {"governing_body_id": governing_body_id}
            )
            rows = result.fetchall()

            results = []
            for row in rows:
                if hasattr(row, "_asdict"):
                    row_dict = row._asdict()  # type: ignore[attr-defined]
                elif hasattr(row, "_mapping"):
                    row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                else:
                    row_dict = dict(row)
                results.append(self._dict_to_entity(row_dict))
            return results

        except SQLAlchemyError as e:
            logger.error(f"Database error getting conferences by governing body: {e}")
            raise DatabaseError(
                "Failed to get conferences by governing body",
                {"governing_body_id": governing_body_id, "error": str(e)},
            ) from e

    async def get_with_members_url(self) -> list[Conference]:
        """Get conferences that have members introduction URL.

        Returns:
            List of Conference entities with members URL
        """
        try:
            query = text("""
                SELECT
                    id,
                    name,
                    type,
                    governing_body_id,
                    members_introduction_url,
                    created_at,
                    updated_at
                FROM conferences
                WHERE members_introduction_url IS NOT NULL
                ORDER BY governing_body_id, name
            """)

            result = await self.session.execute(query)
            rows = result.fetchall()

            results = []
            for row in rows:
                if hasattr(row, "_asdict"):
                    row_dict = row._asdict()  # type: ignore[attr-defined]
                elif hasattr(row, "_mapping"):
                    row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                else:
                    row_dict = dict(row)
                results.append(self._dict_to_entity(row_dict))
            return results

        except SQLAlchemyError as e:
            logger.error(f"Database error getting conferences with members URL: {e}")
            raise DatabaseError(
                "Failed to get conferences with members URL", {"error": str(e)}
            ) from e

    async def update_members_url(
        self, conference_id: int, members_introduction_url: str | None
    ) -> bool:
        """Update conference members introduction URL.

        Args:
            conference_id: Conference ID
            members_introduction_url: New members introduction URL

        Returns:
            True if update was successful
        """
        try:
            query = text("""
                UPDATE conferences
                SET members_introduction_url = :members_introduction_url,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :conference_id
            """)

            result = await self.session.execute(
                query,
                {
                    "conference_id": conference_id,
                    "members_introduction_url": members_introduction_url,
                },
            )

            # Check if any rows were affected
            if hasattr(result, "rowcount") and result.rowcount == 0:  # type: ignore[attr-defined]
                raise RecordNotFoundError("Conference", conference_id)

            await self.session.commit()
            logger.info(f"Updated members URL for conference ID: {conference_id}")
            return True

        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Database error updating conference members URL: {e}")
            raise UpdateError(
                f"Failed to update members URL for conference ID {conference_id}",
                {"conference_id": conference_id, "error": str(e)},
            ) from e

    async def get_all(
        self, limit: int | None = None, offset: int | None = 0
    ) -> list[Conference]:
        """Get all conferences.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of Conference entities
        """
        try:
            query_text = """
                SELECT
                    c.id,
                    c.name,
                    c.type,
                    c.governing_body_id,
                    c.members_introduction_url,
                    c.created_at,
                    c.updated_at,
                    gb.name as governing_body_name,
                    gb.type as governing_body_type
                FROM conferences c
                LEFT JOIN governing_bodies gb ON c.governing_body_id = gb.id
                ORDER BY gb.name, c.name
            """

            params: dict[str, int | None] = {}
            if limit is not None:
                query_text += " LIMIT :limit OFFSET :offset"
                params = {"limit": limit, "offset": offset or 0}

            result = await self.session.execute(text(query_text), params)
            rows = result.fetchall()

            results = []
            for row in rows:
                if hasattr(row, "_asdict"):
                    row_dict = row._asdict()  # type: ignore[attr-defined]
                elif hasattr(row, "_mapping"):
                    row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                else:
                    row_dict = dict(row)
                results.append(self._dict_to_entity(row_dict))
            return results

        except SQLAlchemyError as e:
            logger.error(f"Database error getting all conferences: {e}")
            raise DatabaseError(
                "Failed to get all conferences", {"error": str(e)}
            ) from e

    async def get_by_id(self, entity_id: int) -> Conference | None:
        """Get conference by ID.

        Args:
            entity_id: Conference ID

        Returns:
            Conference entity or None if not found
        """
        try:
            query = text("""
                SELECT
                    id,
                    name,
                    type,
                    governing_body_id,
                    members_introduction_url,
                    created_at,
                    updated_at
                FROM conferences
                WHERE id = :id
            """)

            result = await self.session.execute(query, {"id": entity_id})
            row = result.first()

            if row:
                if hasattr(row, "_asdict"):
                    row_dict = row._asdict()  # type: ignore[attr-defined]
                elif hasattr(row, "_mapping"):
                    row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                else:
                    row_dict = dict(row)
                return self._dict_to_entity(row_dict)
            return None

        except SQLAlchemyError as e:
            logger.error(f"Database error getting conference by ID: {e}")
            raise DatabaseError(
                "Failed to get conference by ID", {"id": entity_id, "error": str(e)}
            ) from e

    async def create(self, entity: Conference) -> Conference:
        """Create a new conference.

        Args:
            entity: Conference entity to create

        Returns:
            Created Conference entity with ID
        """
        try:
            from datetime import datetime

            query = text("""
                INSERT INTO conferences (
                    name, type, governing_body_id,
                    members_introduction_url, created_at, updated_at
                )
                VALUES (
                    :name, :type, :governing_body_id,
                    :members_introduction_url, :created_at, :updated_at
                )
                RETURNING *
            """)

            params = {
                "name": entity.name,
                "type": entity.type,
                "governing_body_id": entity.governing_body_id,
                "members_introduction_url": entity.members_introduction_url,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

            result = await self.session.execute(query, params)
            await self.session.commit()

            row = result.first()
            if row:
                if hasattr(row, "_asdict"):
                    row_dict = row._asdict()  # type: ignore[attr-defined]
                elif hasattr(row, "_mapping"):
                    row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                else:
                    row_dict = dict(row)
                return self._dict_to_entity(row_dict)
            raise RuntimeError("Failed to create conference")

        except SQLAlchemyError as e:
            logger.error(f"Database error creating conference: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to create conference", {"entity": entity, "error": str(e)}
            ) from e

    async def update(self, entity: Conference) -> Conference:
        """Update an existing conference.

        Args:
            entity: Conference entity to update

        Returns:
            Updated Conference entity
        """
        try:
            from datetime import datetime

            query = text("""
                UPDATE conferences
                SET name = :name,
                    type = :type,
                    governing_body_id = :governing_body_id,
                    members_introduction_url = :members_introduction_url,
                    updated_at = :updated_at
                WHERE id = :id
                RETURNING *
            """)

            params = {
                "id": entity.id,
                "name": entity.name,
                "type": entity.type,
                "governing_body_id": entity.governing_body_id,
                "members_introduction_url": entity.members_introduction_url,
                "updated_at": datetime.now(),
            }

            result = await self.session.execute(query, params)
            await self.session.commit()

            row = result.first()
            if row:
                if hasattr(row, "_asdict"):
                    row_dict = row._asdict()  # type: ignore[attr-defined]
                elif hasattr(row, "_mapping"):
                    row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                else:
                    row_dict = dict(row)
                return self._dict_to_entity(row_dict)
            raise UpdateError(f"Conference with ID {entity.id} not found")

        except SQLAlchemyError as e:
            logger.error(f"Database error updating conference: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to update conference", {"entity": entity, "error": str(e)}
            ) from e

    async def delete(self, entity_id: int) -> bool:
        """Delete a conference by ID.

        Args:
            entity_id: Conference ID to delete

        Returns:
            True if deleted, False otherwise
        """
        try:
            # Check if there are related records
            check_query = text("""
                SELECT COUNT(*) FROM meetings WHERE conference_id = :conference_id
            """)
            result = await self.session.execute(
                check_query, {"conference_id": entity_id}
            )
            count = result.scalar()

            if count and count > 0:
                return False  # Cannot delete if there are related meetings

            query = text("DELETE FROM conferences WHERE id = :id")
            result = await self.session.execute(query, {"id": entity_id})
            await self.session.commit()

            return result.rowcount > 0  # type: ignore[attr-defined]

        except SQLAlchemyError as e:
            logger.error(f"Database error deleting conference: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to delete conference", {"id": entity_id, "error": str(e)}
            ) from e

    async def count(self) -> int:
        """Count total number of conferences."""
        query = text("SELECT COUNT(*) FROM conferences")
        result = await self.session.execute(query)
        count = result.scalar()
        return count if count is not None else 0

    def _to_entity(self, model: ConferenceModel) -> Conference:
        """Convert database model to domain entity.

        Args:
            model: Database model

        Returns:
            Domain entity
        """
        return Conference(
            id=model.id,
            name=model.name,
            type=model.type,
            governing_body_id=model.governing_body_id,
            members_introduction_url=model.members_introduction_url,
        )

    def _to_model(self, entity: Conference) -> ConferenceModel:
        """Convert domain entity to database model.

        Args:
            entity: Domain entity

        Returns:
            Database model
        """
        return ConferenceModel(
            id=entity.id,
            name=entity.name,
            type=entity.type,
            governing_body_id=entity.governing_body_id,
            members_introduction_url=entity.members_introduction_url,
        )

    def _update_model(self, model: ConferenceModel, entity: Conference) -> None:
        """Update model from entity.

        Args:
            model: Database model to update
            entity: Source entity
        """
        model.name = entity.name
        model.type = entity.type
        model.governing_body_id = entity.governing_body_id
        model.members_introduction_url = entity.members_introduction_url

    def _dict_to_entity(self, data: dict[str, Any]) -> Conference:
        """Convert dictionary to entity.

        Args:
            data: Dictionary with entity data

        Returns:
            Conference entity
        """
        return Conference(
            id=data.get("id"),
            name=data["name"],
            type=data.get("type"),
            governing_body_id=data["governing_body_id"],
            members_introduction_url=data.get("members_introduction_url"),
        )
