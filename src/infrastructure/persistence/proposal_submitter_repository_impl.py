"""Repository implementation for ProposalSubmitter entities."""

import logging

from datetime import datetime
from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.proposal_submitter import ProposalSubmitter
from src.domain.repositories.proposal_submitter_repository import (
    ProposalSubmitterRepository,
)
from src.domain.repositories.session_adapter import ISessionAdapter
from src.domain.value_objects.submitter_type import SubmitterType
from src.infrastructure.exceptions import DatabaseError
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


logger = logging.getLogger(__name__)


class ProposalSubmitterModel(PydanticBaseModel):
    """Pydantic model for proposal submitter."""

    id: int | None = None
    proposal_id: int
    submitter_type: str
    politician_id: int | None = None
    parliamentary_group_id: int | None = None
    raw_name: str | None = None
    is_representative: bool = False
    display_order: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProposalSubmitterRepositoryImpl(
    BaseRepositoryImpl[ProposalSubmitter],
    ProposalSubmitterRepository,
):
    """ProposalSubmitter repository implementation using SQLAlchemy."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        """Initialize repository with database session.

        Args:
            session: AsyncSession for database operations
        """
        super().__init__(
            session=session,
            entity_class=ProposalSubmitter,
            model_class=ProposalSubmitterModel,
        )

    async def get_by_proposal(self, proposal_id: int) -> list[ProposalSubmitter]:
        """Get all submitters for a specific proposal.

        Args:
            proposal_id: ID of the proposal

        Returns:
            List of ProposalSubmitter entities ordered by display_order
        """
        try:
            query = text("""
                SELECT
                    id,
                    proposal_id,
                    submitter_type,
                    politician_id,
                    parliamentary_group_id,
                    raw_name,
                    is_representative,
                    display_order,
                    created_at,
                    updated_at
                FROM proposal_submitters
                WHERE proposal_id = :proposal_id
                ORDER BY display_order ASC, id ASC
            """)

            result = await self.session.execute(query, {"proposal_id": proposal_id})
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
            logger.error(f"Database error getting submitters by proposal: {e}")
            raise DatabaseError(
                "Failed to get submitters by proposal",
                {"proposal_id": proposal_id, "error": str(e)},
            ) from e

    async def get_by_politician(self, politician_id: int) -> list[ProposalSubmitter]:
        """Get all proposal submitters for a specific politician.

        Args:
            politician_id: ID of the politician

        Returns:
            List of ProposalSubmitter entities
        """
        try:
            query = text("""
                SELECT
                    id,
                    proposal_id,
                    submitter_type,
                    politician_id,
                    parliamentary_group_id,
                    raw_name,
                    is_representative,
                    display_order,
                    created_at,
                    updated_at
                FROM proposal_submitters
                WHERE politician_id = :politician_id
                ORDER BY created_at DESC
            """)

            result = await self.session.execute(query, {"politician_id": politician_id})
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
            logger.error(f"Database error getting submitters by politician: {e}")
            raise DatabaseError(
                "Failed to get submitters by politician",
                {"politician_id": politician_id, "error": str(e)},
            ) from e

    async def get_by_parliamentary_group(
        self, parliamentary_group_id: int
    ) -> list[ProposalSubmitter]:
        """Get all proposal submitters for a specific parliamentary group.

        Args:
            parliamentary_group_id: ID of the parliamentary group

        Returns:
            List of ProposalSubmitter entities
        """
        try:
            query = text("""
                SELECT
                    id,
                    proposal_id,
                    submitter_type,
                    politician_id,
                    parliamentary_group_id,
                    raw_name,
                    is_representative,
                    display_order,
                    created_at,
                    updated_at
                FROM proposal_submitters
                WHERE parliamentary_group_id = :parliamentary_group_id
                ORDER BY created_at DESC
            """)

            result = await self.session.execute(
                query, {"parliamentary_group_id": parliamentary_group_id}
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
            logger.error(
                f"Database error getting submitters by parliamentary group: {e}"
            )
            raise DatabaseError(
                "Failed to get submitters by parliamentary group",
                {"parliamentary_group_id": parliamentary_group_id, "error": str(e)},
            ) from e

    async def bulk_create(
        self, submitters: list[ProposalSubmitter]
    ) -> list[ProposalSubmitter]:
        """Create multiple proposal submitters at once.

        Args:
            submitters: List of ProposalSubmitter entities to create

        Returns:
            List of created ProposalSubmitter entities with IDs
        """
        if not submitters:
            return []

        try:
            query = text("""
                INSERT INTO proposal_submitters (
                    proposal_id, submitter_type, politician_id,
                    parliamentary_group_id, raw_name, is_representative, display_order
                )
                VALUES (
                    :proposal_id, :submitter_type, :politician_id,
                    :parliamentary_group_id, :raw_name,
                    :is_representative, :display_order
                )
                RETURNING id, proposal_id, submitter_type, politician_id,
                          parliamentary_group_id, raw_name, is_representative,
                          display_order, created_at, updated_at
            """)

            created_submitters = []
            for submitter in submitters:
                result = await self.session.execute(
                    query,
                    {
                        "proposal_id": submitter.proposal_id,
                        "submitter_type": submitter.submitter_type.value,
                        "politician_id": submitter.politician_id,
                        "parliamentary_group_id": submitter.parliamentary_group_id,
                        "raw_name": submitter.raw_name,
                        "is_representative": submitter.is_representative,
                        "display_order": submitter.display_order,
                    },
                )
                row = result.fetchone()
                if row:
                    if hasattr(row, "_asdict"):
                        row_dict = row._asdict()  # type: ignore[attr-defined]
                    elif hasattr(row, "_mapping"):
                        row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                    else:
                        row_dict = dict(row)
                    created_submitters.append(self._dict_to_entity(row_dict))

            await self.session.commit()
            return created_submitters

        except SQLAlchemyError as e:
            logger.error(f"Database error bulk creating submitters: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to bulk create submitters",
                {"count": len(submitters), "error": str(e)},
            ) from e

    async def delete_by_proposal(self, proposal_id: int) -> int:
        """Delete all submitters for a specific proposal.

        Args:
            proposal_id: ID of the proposal

        Returns:
            Number of deleted records
        """
        try:
            query = text(
                "DELETE FROM proposal_submitters WHERE proposal_id = :proposal_id"
            )
            result = await self.session.execute(query, {"proposal_id": proposal_id})
            await self.session.commit()

            return result.rowcount

        except SQLAlchemyError as e:
            logger.error(f"Database error deleting submitters by proposal: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to delete submitters by proposal",
                {"proposal_id": proposal_id, "error": str(e)},
            ) from e

    async def get_all(
        self, limit: int | None = None, offset: int | None = 0
    ) -> list[ProposalSubmitter]:
        """Get all proposal submitters.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of ProposalSubmitter entities
        """
        try:
            query_text = """
                SELECT
                    id,
                    proposal_id,
                    submitter_type,
                    politician_id,
                    parliamentary_group_id,
                    raw_name,
                    is_representative,
                    display_order,
                    created_at,
                    updated_at
                FROM proposal_submitters
                ORDER BY created_at DESC
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
            logger.error(f"Database error getting all submitters: {e}")
            raise DatabaseError(
                "Failed to get all submitters", {"error": str(e)}
            ) from e

    async def get_by_id(self, entity_id: int) -> ProposalSubmitter | None:
        """Get proposal submitter by ID.

        Args:
            entity_id: Submitter ID

        Returns:
            ProposalSubmitter entity or None if not found
        """
        try:
            query = text("""
                SELECT
                    id,
                    proposal_id,
                    submitter_type,
                    politician_id,
                    parliamentary_group_id,
                    raw_name,
                    is_representative,
                    display_order,
                    created_at,
                    updated_at
                FROM proposal_submitters
                WHERE id = :id
            """)

            result = await self.session.execute(query, {"id": entity_id})
            row = result.fetchone()

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
            logger.error(f"Database error getting submitter by ID: {e}")
            raise DatabaseError(
                "Failed to get submitter by ID",
                {"id": entity_id, "error": str(e)},
            ) from e

    async def create(self, entity: ProposalSubmitter) -> ProposalSubmitter:
        """Create a new proposal submitter.

        Args:
            entity: ProposalSubmitter entity to create

        Returns:
            Created ProposalSubmitter entity with ID
        """
        try:
            query = text("""
                INSERT INTO proposal_submitters (
                    proposal_id, submitter_type, politician_id,
                    parliamentary_group_id, raw_name, is_representative, display_order
                )
                VALUES (
                    :proposal_id, :submitter_type, :politician_id,
                    :parliamentary_group_id, :raw_name,
                    :is_representative, :display_order
                )
                RETURNING id, proposal_id, submitter_type, politician_id,
                          parliamentary_group_id, raw_name, is_representative,
                          display_order, created_at, updated_at
            """)

            result = await self.session.execute(
                query,
                {
                    "proposal_id": entity.proposal_id,
                    "submitter_type": entity.submitter_type.value,
                    "politician_id": entity.politician_id,
                    "parliamentary_group_id": entity.parliamentary_group_id,
                    "raw_name": entity.raw_name,
                    "is_representative": entity.is_representative,
                    "display_order": entity.display_order,
                },
            )
            row = result.fetchone()
            await self.session.commit()

            if row:
                if hasattr(row, "_asdict"):
                    row_dict = row._asdict()  # type: ignore[attr-defined]
                elif hasattr(row, "_mapping"):
                    row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                else:
                    row_dict = dict(row)
                return self._dict_to_entity(row_dict)

            raise DatabaseError("Failed to create submitter", {"entity": str(entity)})

        except SQLAlchemyError as e:
            logger.error(f"Database error creating submitter: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to create submitter",
                {"entity": str(entity), "error": str(e)},
            ) from e

    async def update(self, entity: ProposalSubmitter) -> ProposalSubmitter:
        """Update an existing proposal submitter.

        Args:
            entity: ProposalSubmitter entity with updated values

        Returns:
            Updated ProposalSubmitter entity
        """
        if not entity.id:
            raise ValueError("Entity must have an ID to update")

        try:
            query = text("""
                UPDATE proposal_submitters
                SET proposal_id = :proposal_id,
                    submitter_type = :submitter_type,
                    politician_id = :politician_id,
                    parliamentary_group_id = :parliamentary_group_id,
                    raw_name = :raw_name,
                    is_representative = :is_representative,
                    display_order = :display_order,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                RETURNING id, proposal_id, submitter_type, politician_id,
                          parliamentary_group_id, raw_name, is_representative,
                          display_order, created_at, updated_at
            """)

            result = await self.session.execute(
                query,
                {
                    "id": entity.id,
                    "proposal_id": entity.proposal_id,
                    "submitter_type": entity.submitter_type.value,
                    "politician_id": entity.politician_id,
                    "parliamentary_group_id": entity.parliamentary_group_id,
                    "raw_name": entity.raw_name,
                    "is_representative": entity.is_representative,
                    "display_order": entity.display_order,
                },
            )
            row = result.fetchone()
            await self.session.commit()

            if row:
                if hasattr(row, "_asdict"):
                    row_dict = row._asdict()  # type: ignore[attr-defined]
                elif hasattr(row, "_mapping"):
                    row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                else:
                    row_dict = dict(row)
                return self._dict_to_entity(row_dict)

            raise DatabaseError(
                f"ProposalSubmitter with ID {entity.id} not found",
                {"entity": str(entity)},
            )

        except SQLAlchemyError as e:
            logger.error(f"Database error updating submitter: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to update submitter",
                {"entity": str(entity), "error": str(e)},
            ) from e

    async def delete(self, entity_id: int) -> bool:
        """Delete a proposal submitter by ID.

        Args:
            entity_id: Submitter ID to delete

        Returns:
            True if deleted, False otherwise
        """
        try:
            query = text("DELETE FROM proposal_submitters WHERE id = :id")
            result = await self.session.execute(query, {"id": entity_id})
            await self.session.commit()

            return result.rowcount > 0

        except SQLAlchemyError as e:
            logger.error(f"Database error deleting submitter: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to delete submitter",
                {"id": entity_id, "error": str(e)},
            ) from e

    def _to_entity(self, model: ProposalSubmitterModel) -> ProposalSubmitter:
        """Convert database model to domain entity.

        Args:
            model: Database model

        Returns:
            Domain entity
        """
        return ProposalSubmitter(
            id=model.id,
            proposal_id=model.proposal_id,
            submitter_type=SubmitterType(model.submitter_type),
            politician_id=model.politician_id,
            parliamentary_group_id=model.parliamentary_group_id,
            raw_name=model.raw_name,
            is_representative=model.is_representative,
            display_order=model.display_order,
        )

    def _to_model(self, entity: ProposalSubmitter) -> ProposalSubmitterModel:
        """Convert domain entity to database model.

        Args:
            entity: Domain entity

        Returns:
            Database model
        """
        return ProposalSubmitterModel(
            id=entity.id,
            proposal_id=entity.proposal_id,
            submitter_type=entity.submitter_type.value,
            politician_id=entity.politician_id,
            parliamentary_group_id=entity.parliamentary_group_id,
            raw_name=entity.raw_name,
            is_representative=entity.is_representative,
            display_order=entity.display_order,
        )

    def _update_model(
        self,
        model: ProposalSubmitterModel,
        entity: ProposalSubmitter,
    ) -> None:
        """Update model from entity.

        Args:
            model: Database model to update
            entity: Source entity
        """
        model.proposal_id = entity.proposal_id
        model.submitter_type = entity.submitter_type.value
        model.politician_id = entity.politician_id
        model.parliamentary_group_id = entity.parliamentary_group_id
        model.raw_name = entity.raw_name
        model.is_representative = entity.is_representative
        model.display_order = entity.display_order

    def _dict_to_entity(self, data: dict[str, Any]) -> ProposalSubmitter:
        """Convert dictionary to entity.

        Args:
            data: Dictionary with entity data

        Returns:
            ProposalSubmitter entity
        """
        return ProposalSubmitter(
            id=data.get("id"),
            proposal_id=data["proposal_id"],
            submitter_type=SubmitterType(data["submitter_type"]),
            politician_id=data.get("politician_id"),
            parliamentary_group_id=data.get("parliamentary_group_id"),
            raw_name=data.get("raw_name"),
            is_representative=data.get("is_representative", False),
            display_order=data.get("display_order", 0),
        )
