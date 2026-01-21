"""ProposalParliamentaryGroupJudge repository implementation."""

import logging

from datetime import datetime
from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.proposal_parliamentary_group_judge import (
    ProposalParliamentaryGroupJudge,
)
from src.domain.repositories.proposal_parliamentary_group_judge_repository import (
    ProposalParliamentaryGroupJudgeRepository,
)
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.exceptions import DatabaseError
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


logger = logging.getLogger(__name__)


class ProposalParliamentaryGroupJudgeModel(PydanticBaseModel):
    """Pydantic model for proposal parliamentary group judge."""

    id: int | None = None
    proposal_id: int
    parliamentary_group_id: int
    judgment: str
    member_count: int | None = None
    note: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProposalParliamentaryGroupJudgeRepositoryImpl(
    BaseRepositoryImpl[ProposalParliamentaryGroupJudge],
    ProposalParliamentaryGroupJudgeRepository,
):
    """ProposalParliamentaryGroupJudge repository implementation using SQLAlchemy."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        """Initialize repository with database session.

        Args:
            session: AsyncSession for database operations
        """
        super().__init__(
            session=session,
            entity_class=ProposalParliamentaryGroupJudge,
            model_class=ProposalParliamentaryGroupJudgeModel,
        )

    async def get_by_proposal(
        self, proposal_id: int
    ) -> list[ProposalParliamentaryGroupJudge]:
        """Get all parliamentary group judges for a specific proposal.

        Args:
            proposal_id: ID of the proposal

        Returns:
            List of ProposalParliamentaryGroupJudge entities
        """
        try:
            query = text("""
                SELECT
                    id,
                    proposal_id,
                    parliamentary_group_id,
                    judgment,
                    member_count,
                    note,
                    created_at,
                    updated_at
                FROM proposal_parliamentary_group_judges
                WHERE proposal_id = :proposal_id
                ORDER BY created_at DESC
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

    async def get_by_parliamentary_group(
        self, parliamentary_group_id: int
    ) -> list[ProposalParliamentaryGroupJudge]:
        """Get all proposal judges for a specific parliamentary group.

        Args:
            parliamentary_group_id: ID of the parliamentary group

        Returns:
            List of ProposalParliamentaryGroupJudge entities
        """
        try:
            query = text("""
                SELECT
                    id,
                    proposal_id,
                    parliamentary_group_id,
                    judgment,
                    member_count,
                    note,
                    created_at,
                    updated_at
                FROM proposal_parliamentary_group_judges
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
            logger.error(f"Database error getting judges by parliamentary group: {e}")
            raise DatabaseError(
                "Failed to get judges by parliamentary group",
                {"parliamentary_group_id": parliamentary_group_id, "error": str(e)},
            ) from e

    async def get_by_proposal_and_group(
        self, proposal_id: int, parliamentary_group_id: int
    ) -> ProposalParliamentaryGroupJudge | None:
        """Get judge for a specific proposal and parliamentary group.

        Args:
            proposal_id: ID of the proposal
            parliamentary_group_id: ID of the parliamentary group

        Returns:
            ProposalParliamentaryGroupJudge entity or None if not found
        """
        try:
            query = text("""
                SELECT
                    id,
                    proposal_id,
                    parliamentary_group_id,
                    judgment,
                    member_count,
                    note,
                    created_at,
                    updated_at
                FROM proposal_parliamentary_group_judges
                WHERE proposal_id = :proposal_id
                AND parliamentary_group_id = :parliamentary_group_id
            """)

            result = await self.session.execute(
                query,
                {
                    "proposal_id": proposal_id,
                    "parliamentary_group_id": parliamentary_group_id,
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
                return self._dict_to_entity(row_dict)
            return None

        except SQLAlchemyError as e:
            logger.error(f"Database error getting judge by proposal and group: {e}")
            raise DatabaseError(
                "Failed to get judge by proposal and group",
                {
                    "proposal_id": proposal_id,
                    "parliamentary_group_id": parliamentary_group_id,
                    "error": str(e),
                },
            ) from e

    async def bulk_create(
        self, judges: list[ProposalParliamentaryGroupJudge]
    ) -> list[ProposalParliamentaryGroupJudge]:
        """Create multiple parliamentary group judges at once.

        Args:
            judges: List of ProposalParliamentaryGroupJudge entities to create

        Returns:
            List of created ProposalParliamentaryGroupJudge entities with IDs
        """
        if not judges:
            return []

        try:
            query = text("""
                INSERT INTO proposal_parliamentary_group_judges (
                    proposal_id, parliamentary_group_id, judgment, member_count, note
                )
                VALUES (
                    :proposal_id, :parliamentary_group_id, :judgment,
                    :member_count, :note
                )
                RETURNING id, proposal_id, parliamentary_group_id, judgment,
                          member_count, note, created_at, updated_at
            """)

            created_judges = []
            for judge in judges:
                result = await self.session.execute(
                    query,
                    {
                        "proposal_id": judge.proposal_id,
                        "parliamentary_group_id": judge.parliamentary_group_id,
                        "judgment": judge.judgment,
                        "member_count": judge.member_count,
                        "note": judge.note,
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
                    created_judges.append(self._dict_to_entity(row_dict))

            await self.session.commit()
            return created_judges

        except SQLAlchemyError as e:
            logger.error(
                f"Database error bulk creating parliamentary group judges: {e}"
            )
            await self.session.rollback()
            raise DatabaseError(
                "Failed to bulk create parliamentary group judges",
                {"count": len(judges), "error": str(e)},
            ) from e

    async def get_all(
        self, limit: int | None = None, offset: int | None = 0
    ) -> list[ProposalParliamentaryGroupJudge]:
        """Get all parliamentary group judges.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of ProposalParliamentaryGroupJudge entities
        """
        try:
            query_text = """
                SELECT
                    id,
                    proposal_id,
                    parliamentary_group_id,
                    judgment,
                    member_count,
                    note,
                    created_at,
                    updated_at
                FROM proposal_parliamentary_group_judges
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
            logger.error(f"Database error getting all parliamentary group judges: {e}")
            raise DatabaseError(
                "Failed to get all parliamentary group judges", {"error": str(e)}
            ) from e

    async def get_by_id(self, entity_id: int) -> ProposalParliamentaryGroupJudge | None:
        """Get parliamentary group judge by ID.

        Args:
            entity_id: Judge ID

        Returns:
            ProposalParliamentaryGroupJudge entity or None if not found
        """
        try:
            query = text("""
                SELECT
                    id,
                    proposal_id,
                    parliamentary_group_id,
                    judgment,
                    member_count,
                    note,
                    created_at,
                    updated_at
                FROM proposal_parliamentary_group_judges
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
            logger.error(f"Database error getting parliamentary group judge by ID: {e}")
            raise DatabaseError(
                "Failed to get parliamentary group judge by ID",
                {"id": entity_id, "error": str(e)},
            ) from e

    async def create(
        self, entity: ProposalParliamentaryGroupJudge
    ) -> ProposalParliamentaryGroupJudge:
        """Create a new parliamentary group judge.

        Args:
            entity: ProposalParliamentaryGroupJudge entity to create

        Returns:
            Created ProposalParliamentaryGroupJudge entity with ID
        """
        try:
            query = text("""
                INSERT INTO proposal_parliamentary_group_judges (
                    proposal_id, parliamentary_group_id, judgment, member_count, note
                )
                VALUES (
                    :proposal_id, :parliamentary_group_id, :judgment,
                    :member_count, :note
                )
                RETURNING id, proposal_id, parliamentary_group_id, judgment,
                          member_count, note, created_at, updated_at
            """)

            result = await self.session.execute(
                query,
                {
                    "proposal_id": entity.proposal_id,
                    "parliamentary_group_id": entity.parliamentary_group_id,
                    "judgment": entity.judgment,
                    "member_count": entity.member_count,
                    "note": entity.note,
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
                "Failed to create parliamentary group judge", {"entity": str(entity)}
            )

        except SQLAlchemyError as e:
            logger.error(f"Database error creating parliamentary group judge: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to create parliamentary group judge",
                {"entity": str(entity), "error": str(e)},
            ) from e

    async def update(
        self, entity: ProposalParliamentaryGroupJudge
    ) -> ProposalParliamentaryGroupJudge:
        """Update an existing parliamentary group judge.

        Args:
            entity: ProposalParliamentaryGroupJudge entity with updated values

        Returns:
            Updated ProposalParliamentaryGroupJudge entity
        """
        if not entity.id:
            raise ValueError("Entity must have an ID to update")

        try:
            query = text("""
                UPDATE proposal_parliamentary_group_judges
                SET proposal_id = :proposal_id,
                    parliamentary_group_id = :parliamentary_group_id,
                    judgment = :judgment,
                    member_count = :member_count,
                    note = :note,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                RETURNING id, proposal_id, parliamentary_group_id, judgment,
                          member_count, note, created_at, updated_at
            """)

            result = await self.session.execute(
                query,
                {
                    "id": entity.id,
                    "proposal_id": entity.proposal_id,
                    "parliamentary_group_id": entity.parliamentary_group_id,
                    "judgment": entity.judgment,
                    "member_count": entity.member_count,
                    "note": entity.note,
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
                f"ProposalParliamentaryGroupJudge with ID {entity.id} not found",
                {"entity": str(entity)},
            )

        except SQLAlchemyError as e:
            logger.error(f"Database error updating parliamentary group judge: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to update parliamentary group judge",
                {"entity": str(entity), "error": str(e)},
            ) from e

    async def delete(self, entity_id: int) -> bool:
        """Delete a parliamentary group judge by ID.

        Args:
            entity_id: Judge ID to delete

        Returns:
            True if deleted, False otherwise
        """
        try:
            query = text(
                "DELETE FROM proposal_parliamentary_group_judges WHERE id = :id"
            )
            result = await self.session.execute(query, {"id": entity_id})
            await self.session.commit()

            return result.rowcount > 0

        except SQLAlchemyError as e:
            logger.error(f"Database error deleting parliamentary group judge: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to delete parliamentary group judge",
                {"id": entity_id, "error": str(e)},
            ) from e

    def _to_entity(
        self, model: ProposalParliamentaryGroupJudgeModel
    ) -> ProposalParliamentaryGroupJudge:
        """Convert database model to domain entity.

        Args:
            model: Database model

        Returns:
            Domain entity
        """
        return ProposalParliamentaryGroupJudge(
            id=model.id,
            proposal_id=model.proposal_id,
            parliamentary_group_id=model.parliamentary_group_id,
            judgment=model.judgment,
            member_count=model.member_count,
            note=model.note,
        )

    def _to_model(
        self, entity: ProposalParliamentaryGroupJudge
    ) -> ProposalParliamentaryGroupJudgeModel:
        """Convert domain entity to database model.

        Args:
            entity: Domain entity

        Returns:
            Database model
        """
        return ProposalParliamentaryGroupJudgeModel(
            id=entity.id,
            proposal_id=entity.proposal_id,
            parliamentary_group_id=entity.parliamentary_group_id,
            judgment=entity.judgment,
            member_count=entity.member_count,
            note=entity.note,
        )

    def _update_model(
        self,
        model: ProposalParliamentaryGroupJudgeModel,
        entity: ProposalParliamentaryGroupJudge,
    ) -> None:
        """Update model from entity.

        Args:
            model: Database model to update
            entity: Source entity
        """
        model.proposal_id = entity.proposal_id
        model.parliamentary_group_id = entity.parliamentary_group_id
        model.judgment = entity.judgment
        model.member_count = entity.member_count
        model.note = entity.note

    def _dict_to_entity(self, data: dict[str, Any]) -> ProposalParliamentaryGroupJudge:
        """Convert dictionary to entity.

        Args:
            data: Dictionary with entity data

        Returns:
            ProposalParliamentaryGroupJudge entity
        """
        return ProposalParliamentaryGroupJudge(
            id=data.get("id"),
            proposal_id=data["proposal_id"],
            parliamentary_group_id=data["parliamentary_group_id"],
            judgment=data["judgment"],
            member_count=data.get("member_count"),
            note=data.get("note"),
        )
