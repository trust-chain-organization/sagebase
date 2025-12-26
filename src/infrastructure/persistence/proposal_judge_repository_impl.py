"""ProposalJudge repository implementation using SQLAlchemy."""

import logging

from datetime import datetime
from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.proposal_judge import ProposalJudge
from src.domain.repositories.proposal_judge_repository import ProposalJudgeRepository
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.exceptions import DatabaseError
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


logger = logging.getLogger(__name__)


class ProposalJudgeModel(PydanticBaseModel):
    """ProposalJudge database model."""

    id: int | None = None
    proposal_id: int
    politician_id: int
    politician_party_id: int | None = None
    approve: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        arbitrary_types_allowed = True


class ProposalJudgeRepositoryImpl(
    BaseRepositoryImpl[ProposalJudge], ProposalJudgeRepository
):
    """ProposalJudge repository implementation using SQLAlchemy."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        """Initialize repository with database session.

        Args:
            session: AsyncSession for database operations
        """
        super().__init__(
            session=session,
            entity_class=ProposalJudge,
            model_class=ProposalJudgeModel,
        )

    async def get_by_proposal(self, proposal_id: int) -> list[ProposalJudge]:
        """Get all judges for a proposal.

        Args:
            proposal_id: ID of the proposal

        Returns:
            List of proposal judges for the specified proposal
        """
        try:
            query = text("""
                SELECT
                    pj.id,
                    pj.proposal_id,
                    pj.politician_id,
                    pj.politician_party_id,
                    pj.approve,
                    pj.created_at,
                    pj.updated_at
                FROM proposal_judges pj
                WHERE pj.proposal_id = :proposal_id
                ORDER BY pj.created_at DESC
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
            logger.error(f"Database error getting judges by proposal: {e}")
            raise DatabaseError(
                "Failed to get judges by proposal",
                {"proposal_id": proposal_id, "error": str(e)},
            ) from e

    async def get_by_politician(self, politician_id: int) -> list[ProposalJudge]:
        """Get all proposal judges by a politician.

        Args:
            politician_id: ID of the politician

        Returns:
            List of proposal judges by the specified politician
        """
        try:
            query = text("""
                SELECT
                    pj.id,
                    pj.proposal_id,
                    pj.politician_id,
                    pj.politician_party_id,
                    pj.approve,
                    pj.created_at,
                    pj.updated_at
                FROM proposal_judges pj
                WHERE pj.politician_id = :politician_id
                ORDER BY pj.created_at DESC
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
            logger.error(f"Database error getting judges by politician: {e}")
            raise DatabaseError(
                "Failed to get judges by politician",
                {"politician_id": politician_id, "error": str(e)},
            ) from e

    async def get_by_proposal_and_politician(
        self, proposal_id: int, politician_id: int
    ) -> ProposalJudge | None:
        """Get a specific judge by proposal and politician.

        Args:
            proposal_id: ID of the proposal
            politician_id: ID of the politician

        Returns:
            The proposal judge if found, None otherwise
        """
        try:
            query = text("""
                SELECT
                    id,
                    proposal_id,
                    politician_id,
                    politician_party_id,
                    approve,
                    created_at,
                    updated_at
                FROM proposal_judges
                WHERE proposal_id = :proposal_id
                AND politician_id = :politician_id
            """)

            result = await self.session.execute(
                query, {"proposal_id": proposal_id, "politician_id": politician_id}
            )
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
            logger.error(
                f"Database error getting judge by proposal and politician: {e}"
            )
            raise DatabaseError(
                "Failed to get judge by proposal and politician",
                {
                    "proposal_id": proposal_id,
                    "politician_id": politician_id,
                    "error": str(e),
                },
            ) from e

    async def bulk_create(self, judges: list[ProposalJudge]) -> list[ProposalJudge]:
        """Create multiple proposal judges at once.

        Args:
            judges: List of ProposalJudge entities to create

        Returns:
            List of created ProposalJudge entities with IDs
        """
        if not judges:
            return []

        try:
            # Build values for bulk insert
            values = []
            for judge in judges:
                values.append(
                    {
                        "proposal_id": judge.proposal_id,
                        "politician_id": judge.politician_id,
                        "politician_party_id": judge.politician_party_id,
                        "approve": judge.approve,
                    }
                )

            # Create bulk insert query
            query = text("""
                INSERT INTO proposal_judges (
                    proposal_id, politician_id, politician_party_id, approve
                )
                VALUES (:proposal_id, :politician_id, :politician_party_id, :approve)
                RETURNING id, proposal_id, politician_id, politician_party_id,
                          approve, created_at, updated_at
            """)

            created_judges = []
            for value in values:
                result = await self.session.execute(query, value)
                row = result.fetchone()
                if row:
                    if hasattr(row, "_asdict"):
                        row_dict = row._asdict()  # type: ignore[attr-defined]
                    elif hasattr(row, "_mapping"):
                        row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                    else:
                        row_dict = dict(row)
                    created_judges.append(self._dict_to_entity(row_dict))

            await self.session.commit()
            return created_judges

        except SQLAlchemyError as e:
            logger.error(f"Database error bulk creating proposal judges: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to bulk create proposal judges",
                {"count": len(judges), "error": str(e)},
            ) from e

    async def get_all(
        self, limit: int | None = None, offset: int | None = 0
    ) -> list[ProposalJudge]:
        """Get all proposal judges.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of ProposalJudge entities
        """
        try:
            query_text = """
                SELECT
                    pj.id,
                    pj.proposal_id,
                    pj.politician_id,
                    pj.politician_party_id,
                    pj.approve,
                    pj.created_at,
                    pj.updated_at
                FROM proposal_judges pj
                ORDER BY pj.created_at DESC
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
            logger.error(f"Database error getting all proposal judges: {e}")
            raise DatabaseError(
                "Failed to get all proposal judges", {"error": str(e)}
            ) from e

    async def get_by_id(self, entity_id: int) -> ProposalJudge | None:
        """Get proposal judge by ID.

        Args:
            entity_id: ProposalJudge ID

        Returns:
            ProposalJudge entity or None if not found
        """
        try:
            query = text("""
                SELECT
                    id,
                    proposal_id,
                    politician_id,
                    politician_party_id,
                    approve,
                    created_at,
                    updated_at
                FROM proposal_judges
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
            logger.error(f"Database error getting proposal judge by ID: {e}")
            raise DatabaseError(
                "Failed to get proposal judge by ID",
                {"id": entity_id, "error": str(e)},
            ) from e

    async def create(self, entity: ProposalJudge) -> ProposalJudge:
        """Create a new proposal judge.

        Args:
            entity: ProposalJudge entity to create

        Returns:
            Created ProposalJudge entity with ID
        """
        try:
            query = text("""
                INSERT INTO proposal_judges (
                    proposal_id, politician_id, politician_party_id, approve
                )
                VALUES (:proposal_id, :politician_id, :politician_party_id, :approve)
                RETURNING id, proposal_id, politician_id, politician_party_id,
                          approve, created_at, updated_at
            """)

            result = await self.session.execute(
                query,
                {
                    "proposal_id": entity.proposal_id,
                    "politician_id": entity.politician_id,
                    "politician_party_id": entity.politician_party_id,
                    "approve": entity.approve,
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

            raise DatabaseError("Failed to create proposal judge", {"entity": entity})

        except SQLAlchemyError as e:
            logger.error(f"Database error creating proposal judge: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to create proposal judge", {"entity": entity, "error": str(e)}
            ) from e

    async def update(self, entity: ProposalJudge) -> ProposalJudge:
        """Update an existing proposal judge.

        Args:
            entity: ProposalJudge entity with updated values

        Returns:
            Updated ProposalJudge entity
        """
        if not entity.id:
            raise ValueError("Entity must have an ID to update")

        try:
            query = text("""
                UPDATE proposal_judges
                SET proposal_id = :proposal_id,
                    politician_id = :politician_id,
                    politician_party_id = :politician_party_id,
                    approve = :approve,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                RETURNING id, proposal_id, politician_id, politician_party_id,
                          approve, created_at, updated_at
            """)

            result = await self.session.execute(
                query,
                {
                    "id": entity.id,
                    "proposal_id": entity.proposal_id,
                    "politician_id": entity.politician_id,
                    "politician_party_id": entity.politician_party_id,
                    "approve": entity.approve,
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
                f"ProposalJudge with ID {entity.id} not found", {"entity": entity}
            )

        except SQLAlchemyError as e:
            logger.error(f"Database error updating proposal judge: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to update proposal judge", {"entity": entity, "error": str(e)}
            ) from e

    async def delete(self, entity_id: int) -> bool:
        """Delete a proposal judge by ID.

        Args:
            entity_id: ProposalJudge ID to delete

        Returns:
            True if deleted, False otherwise
        """
        try:
            query = text("DELETE FROM proposal_judges WHERE id = :id")
            result = await self.session.execute(query, {"id": entity_id})
            await self.session.commit()

            return result.rowcount > 0  # type: ignore[attr-defined]

        except SQLAlchemyError as e:
            logger.error(f"Database error deleting proposal judge: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to delete proposal judge", {"id": entity_id, "error": str(e)}
            ) from e

    def _to_entity(self, model: ProposalJudgeModel) -> ProposalJudge:
        """Convert database model to domain entity.

        Args:
            model: Database model

        Returns:
            Domain entity
        """
        return ProposalJudge(
            id=model.id,
            proposal_id=model.proposal_id,
            politician_id=model.politician_id,
            politician_party_id=model.politician_party_id,
            approve=model.approve,
        )

    def _to_model(self, entity: ProposalJudge) -> ProposalJudgeModel:
        """Convert domain entity to database model.

        Args:
            entity: Domain entity

        Returns:
            Database model
        """
        return ProposalJudgeModel(
            id=entity.id,
            proposal_id=entity.proposal_id,
            politician_id=entity.politician_id,
            politician_party_id=entity.politician_party_id,
            approve=entity.approve,
        )

    def _update_model(self, model: ProposalJudgeModel, entity: ProposalJudge) -> None:
        """Update model from entity.

        Args:
            model: Database model to update
            entity: Source entity
        """
        model.proposal_id = entity.proposal_id
        model.politician_id = entity.politician_id
        model.politician_party_id = entity.politician_party_id
        model.approve = entity.approve

    def _dict_to_entity(self, data: dict[str, Any]) -> ProposalJudge:
        """Convert dictionary to entity.

        Args:
            data: Dictionary with entity data

        Returns:
            ProposalJudge entity
        """
        return ProposalJudge(
            id=data.get("id"),
            proposal_id=data["proposal_id"],
            politician_id=data["politician_id"],
            politician_party_id=data.get("politician_party_id"),
            approve=data.get("approve"),
        )
