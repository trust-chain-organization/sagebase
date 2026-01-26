"""ProposalParliamentaryGroupJudge repository implementation.

Many-to-Many構造: 中間テーブルを使用して1つの賛否レコードに複数の会派・政治家を紐付け。
"""

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
from src.domain.value_objects.judge_type import JudgeType
from src.infrastructure.exceptions import DatabaseError
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


logger = logging.getLogger(__name__)


class ProposalParliamentaryGroupJudgeModel(PydanticBaseModel):
    """Pydantic model for proposal parliamentary group judge."""

    id: int | None = None
    proposal_id: int
    judge_type: str = "parliamentary_group"
    judgment: str
    member_count: int | None = None
    note: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProposalParliamentaryGroupJudgeRepositoryImpl(
    BaseRepositoryImpl[ProposalParliamentaryGroupJudge],
    ProposalParliamentaryGroupJudgeRepository,
):
    """ProposalParliamentaryGroupJudge repository implementation using SQLAlchemy.

    Many-to-Many構造に対応:
    - proposal_parliamentary_group_judges: 賛否レコード本体
    - proposal_judge_parliamentary_groups: 賛否⇔会派の中間テーブル
    - proposal_judge_politicians: 賛否⇔政治家の中間テーブル
    """

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

    async def _fetch_related_ids(self, judge_id: int) -> tuple[list[int], list[int]]:
        """Fetch related parliamentary group IDs and politician IDs for a judge.

        Args:
            judge_id: ID of the judge

        Returns:
            Tuple of (parliamentary_group_ids, politician_ids)
        """
        # 会派IDを取得
        pg_query = text("""
            SELECT parliamentary_group_id
            FROM proposal_judge_parliamentary_groups
            WHERE judge_id = :judge_id
            ORDER BY id
        """)
        pg_result = await self.session.execute(pg_query, {"judge_id": judge_id})
        pg_ids = [row[0] for row in pg_result.fetchall()]

        # 政治家IDを取得
        pol_query = text("""
            SELECT politician_id
            FROM proposal_judge_politicians
            WHERE judge_id = :judge_id
            ORDER BY id
        """)
        pol_result = await self.session.execute(pol_query, {"judge_id": judge_id})
        pol_ids = [row[0] for row in pol_result.fetchall()]

        return pg_ids, pol_ids

    async def _insert_related_ids(
        self,
        judge_id: int,
        parliamentary_group_ids: list[int],
        politician_ids: list[int],
    ) -> None:
        """Insert related IDs into junction tables.

        Args:
            judge_id: ID of the judge
            parliamentary_group_ids: List of parliamentary group IDs
            politician_ids: List of politician IDs
        """
        # 会派IDを中間テーブルに挿入
        for pg_id in parliamentary_group_ids:
            pg_query = text(
                """
                INSERT INTO proposal_judge_parliamentary_groups
                    (judge_id, parliamentary_group_id)
                VALUES (:judge_id, :parliamentary_group_id)
                ON CONFLICT (judge_id, parliamentary_group_id) DO NOTHING
                """
            )
            await self.session.execute(
                pg_query, {"judge_id": judge_id, "parliamentary_group_id": pg_id}
            )

        # 政治家IDを中間テーブルに挿入
        for pol_id in politician_ids:
            pol_query = text("""
                INSERT INTO proposal_judge_politicians (judge_id, politician_id)
                VALUES (:judge_id, :politician_id)
                ON CONFLICT (judge_id, politician_id) DO NOTHING
            """)
            await self.session.execute(
                pol_query, {"judge_id": judge_id, "politician_id": pol_id}
            )

    async def _delete_related_ids(self, judge_id: int) -> None:
        """Delete related IDs from junction tables.

        Args:
            judge_id: ID of the judge
        """
        pg_query = text(
            "DELETE FROM proposal_judge_parliamentary_groups WHERE judge_id = :judge_id"
        )
        await self.session.execute(pg_query, {"judge_id": judge_id})

        pol_query = text(
            "DELETE FROM proposal_judge_politicians WHERE judge_id = :judge_id"
        )
        await self.session.execute(pol_query, {"judge_id": judge_id})

    async def get_by_proposal(
        self, proposal_id: int
    ) -> list[ProposalParliamentaryGroupJudge]:
        """Get all parliamentary group judges for a specific proposal.

        Args:
            proposal_id: ID of the proposal

        Returns:
            List of ProposalParliamentaryGroupJudge entities with related IDs populated
        """
        try:
            query = text("""
                SELECT
                    id,
                    proposal_id,
                    judge_type,
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
                row_dict = self._row_to_dict(row)
                judge_id = row_dict["id"]

                # 関連IDを取得
                pg_ids, pol_ids = await self._fetch_related_ids(judge_id)
                row_dict["parliamentary_group_ids"] = pg_ids
                row_dict["politician_ids"] = pol_ids

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
        """Get all proposal judges that include a specific parliamentary group.

        Args:
            parliamentary_group_id: ID of the parliamentary group

        Returns:
            List of ProposalParliamentaryGroupJudge entities
        """
        try:
            query = text("""
                SELECT DISTINCT
                    j.id,
                    j.proposal_id,
                    j.judge_type,
                    j.judgment,
                    j.member_count,
                    j.note,
                    j.created_at,
                    j.updated_at
                FROM proposal_parliamentary_group_judges j
                INNER JOIN proposal_judge_parliamentary_groups pjpg
                    ON j.id = pjpg.judge_id
                WHERE pjpg.parliamentary_group_id = :parliamentary_group_id
                ORDER BY j.created_at DESC
            """)

            result = await self.session.execute(
                query, {"parliamentary_group_id": parliamentary_group_id}
            )
            rows = result.fetchall()

            results = []
            for row in rows:
                row_dict = self._row_to_dict(row)
                judge_id = row_dict["id"]

                pg_ids, pol_ids = await self._fetch_related_ids(judge_id)
                row_dict["parliamentary_group_ids"] = pg_ids
                row_dict["politician_ids"] = pol_ids

                results.append(self._dict_to_entity(row_dict))
            return results

        except SQLAlchemyError as e:
            logger.error(f"Database error getting judges by parliamentary group: {e}")
            raise DatabaseError(
                "Failed to get judges by parliamentary group",
                {"parliamentary_group_id": parliamentary_group_id, "error": str(e)},
            ) from e

    async def get_by_proposal_and_groups(
        self, proposal_id: int, parliamentary_group_ids: list[int]
    ) -> ProposalParliamentaryGroupJudge | None:
        """Get judge for proposal containing all specified parliamentary groups.

        Args:
            proposal_id: ID of the proposal
            parliamentary_group_ids: List of parliamentary group IDs

        Returns:
            ProposalParliamentaryGroupJudge entity or None if not found
        """
        if not parliamentary_group_ids:
            return None

        try:
            # 指定されたすべての会派IDを含むjudge_idを検索
            query = text("""
                SELECT j.id, j.proposal_id, j.judge_type, j.judgment,
                       j.member_count, j.note, j.created_at, j.updated_at
                FROM proposal_parliamentary_group_judges j
                WHERE j.proposal_id = :proposal_id
                AND (
                    SELECT COUNT(DISTINCT pjpg.parliamentary_group_id)
                    FROM proposal_judge_parliamentary_groups pjpg
                    WHERE pjpg.judge_id = j.id
                    AND pjpg.parliamentary_group_id = ANY(:pg_ids)
                ) = :pg_count
                LIMIT 1
            """)

            result = await self.session.execute(
                query,
                {
                    "proposal_id": proposal_id,
                    "pg_ids": parliamentary_group_ids,
                    "pg_count": len(parliamentary_group_ids),
                },
            )
            row = result.fetchone()

            if row:
                row_dict = self._row_to_dict(row)
                judge_id = row_dict["id"]
                pg_ids, pol_ids = await self._fetch_related_ids(judge_id)
                row_dict["parliamentary_group_ids"] = pg_ids
                row_dict["politician_ids"] = pol_ids
                return self._dict_to_entity(row_dict)
            return None

        except SQLAlchemyError as e:
            logger.error(f"Database error getting judge by proposal and groups: {e}")
            raise DatabaseError(
                "Failed to get judge by proposal and groups",
                {
                    "proposal_id": proposal_id,
                    "parliamentary_group_ids": parliamentary_group_ids,
                    "error": str(e),
                },
            ) from e

    async def get_by_proposal_and_politicians(
        self, proposal_id: int, politician_ids: list[int]
    ) -> ProposalParliamentaryGroupJudge | None:
        """Get judge for a specific proposal that contains all specified politicians.

        Args:
            proposal_id: ID of the proposal
            politician_ids: List of politician IDs

        Returns:
            ProposalParliamentaryGroupJudge entity or None if not found
        """
        if not politician_ids:
            return None

        try:
            query = text("""
                SELECT j.id, j.proposal_id, j.judge_type, j.judgment,
                       j.member_count, j.note, j.created_at, j.updated_at
                FROM proposal_parliamentary_group_judges j
                WHERE j.proposal_id = :proposal_id
                AND (
                    SELECT COUNT(DISTINCT pjp.politician_id)
                    FROM proposal_judge_politicians pjp
                    WHERE pjp.judge_id = j.id
                    AND pjp.politician_id = ANY(:pol_ids)
                ) = :pol_count
                LIMIT 1
            """)

            result = await self.session.execute(
                query,
                {
                    "proposal_id": proposal_id,
                    "pol_ids": politician_ids,
                    "pol_count": len(politician_ids),
                },
            )
            row = result.fetchone()

            if row:
                row_dict = self._row_to_dict(row)
                judge_id = row_dict["id"]
                pg_ids, pol_ids = await self._fetch_related_ids(judge_id)
                row_dict["parliamentary_group_ids"] = pg_ids
                row_dict["politician_ids"] = pol_ids
                return self._dict_to_entity(row_dict)
            return None

        except SQLAlchemyError as e:
            logger.error(f"Error getting judge by proposal and politicians: {e}")
            raise DatabaseError(
                "Failed to get judge by proposal and politicians",
                {
                    "proposal_id": proposal_id,
                    "politician_ids": politician_ids,
                    "error": str(e),
                },
            ) from e

    async def get_by_politician(
        self, politician_id: int
    ) -> list[ProposalParliamentaryGroupJudge]:
        """Get all proposal judges that include a specific politician.

        Args:
            politician_id: ID of the politician

        Returns:
            List of ProposalParliamentaryGroupJudge entities
        """
        try:
            query = text("""
                SELECT DISTINCT
                    j.id,
                    j.proposal_id,
                    j.judge_type,
                    j.judgment,
                    j.member_count,
                    j.note,
                    j.created_at,
                    j.updated_at
                FROM proposal_parliamentary_group_judges j
                INNER JOIN proposal_judge_politicians pjp
                    ON j.id = pjp.judge_id
                WHERE pjp.politician_id = :politician_id
                ORDER BY j.created_at DESC
            """)

            result = await self.session.execute(query, {"politician_id": politician_id})
            rows = result.fetchall()

            results = []
            for row in rows:
                row_dict = self._row_to_dict(row)
                judge_id = row_dict["id"]

                pg_ids, pol_ids = await self._fetch_related_ids(judge_id)
                row_dict["parliamentary_group_ids"] = pg_ids
                row_dict["politician_ids"] = pol_ids

                results.append(self._dict_to_entity(row_dict))
            return results

        except SQLAlchemyError as e:
            logger.error(f"Database error getting judges by politician: {e}")
            raise DatabaseError(
                "Failed to get judges by politician",
                {"politician_id": politician_id, "error": str(e)},
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
            created_judges = []
            for judge in judges:
                # 本体を挿入
                query = text("""
                    INSERT INTO proposal_parliamentary_group_judges (
                        proposal_id, judge_type, judgment, member_count, note
                    )
                    VALUES (
                        :proposal_id, :judge_type, :judgment, :member_count, :note
                    )
                    RETURNING id, proposal_id, judge_type, judgment, member_count, note,
                              created_at, updated_at
                """)

                result = await self.session.execute(
                    query,
                    {
                        "proposal_id": judge.proposal_id,
                        "judge_type": judge.judge_type.value,
                        "judgment": judge.judgment,
                        "member_count": judge.member_count,
                        "note": judge.note,
                    },
                )
                row = result.fetchone()
                if row:
                    row_dict = self._row_to_dict(row)
                    judge_id = row_dict["id"]

                    # 中間テーブルに関連IDを挿入
                    await self._insert_related_ids(
                        judge_id, judge.parliamentary_group_ids, judge.politician_ids
                    )

                    row_dict["parliamentary_group_ids"] = judge.parliamentary_group_ids
                    row_dict["politician_ids"] = judge.politician_ids
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
                    judge_type,
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
                row_dict = self._row_to_dict(row)
                judge_id = row_dict["id"]

                pg_ids, pol_ids = await self._fetch_related_ids(judge_id)
                row_dict["parliamentary_group_ids"] = pg_ids
                row_dict["politician_ids"] = pol_ids

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
                    judge_type,
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
                row_dict = self._row_to_dict(row)
                judge_id = row_dict["id"]

                pg_ids, pol_ids = await self._fetch_related_ids(judge_id)
                row_dict["parliamentary_group_ids"] = pg_ids
                row_dict["politician_ids"] = pol_ids

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
            # 本体を挿入
            query = text("""
                INSERT INTO proposal_parliamentary_group_judges (
                    proposal_id, judge_type, judgment, member_count, note
                )
                VALUES (
                    :proposal_id, :judge_type, :judgment, :member_count, :note
                )
                RETURNING id, proposal_id, judge_type, judgment, member_count, note,
                          created_at, updated_at
            """)

            result = await self.session.execute(
                query,
                {
                    "proposal_id": entity.proposal_id,
                    "judge_type": entity.judge_type.value,
                    "judgment": entity.judgment,
                    "member_count": entity.member_count,
                    "note": entity.note,
                },
            )
            row = result.fetchone()

            if row:
                row_dict = self._row_to_dict(row)
                judge_id = row_dict["id"]

                # 中間テーブルに関連IDを挿入
                await self._insert_related_ids(
                    judge_id, entity.parliamentary_group_ids, entity.politician_ids
                )

                await self.session.commit()

                row_dict["parliamentary_group_ids"] = entity.parliamentary_group_ids
                row_dict["politician_ids"] = entity.politician_ids
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
            # 本体を更新
            query = text("""
                UPDATE proposal_parliamentary_group_judges
                SET proposal_id = :proposal_id,
                    judge_type = :judge_type,
                    judgment = :judgment,
                    member_count = :member_count,
                    note = :note,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                RETURNING id, proposal_id, judge_type, judgment, member_count, note,
                          created_at, updated_at
            """)

            result = await self.session.execute(
                query,
                {
                    "id": entity.id,
                    "proposal_id": entity.proposal_id,
                    "judge_type": entity.judge_type.value,
                    "judgment": entity.judgment,
                    "member_count": entity.member_count,
                    "note": entity.note,
                },
            )
            row = result.fetchone()

            if row:
                # 中間テーブルを更新（DELETE + INSERT）
                await self._delete_related_ids(entity.id)
                await self._insert_related_ids(
                    entity.id, entity.parliamentary_group_ids, entity.politician_ids
                )

                await self.session.commit()

                row_dict = self._row_to_dict(row)
                row_dict["parliamentary_group_ids"] = entity.parliamentary_group_ids
                row_dict["politician_ids"] = entity.politician_ids
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

        中間テーブルはCASCADE DELETEで自動削除されます。

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

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        """Convert a database row to a dictionary.

        Args:
            row: Database row

        Returns:
            Dictionary representation
        """
        if hasattr(row, "_asdict"):
            return row._asdict()  # type: ignore[attr-defined]
        elif hasattr(row, "_mapping"):
            return dict(row._mapping)  # type: ignore[attr-defined]
        else:
            return dict(row)

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
            judgment=model.judgment,
            judge_type=JudgeType(model.judge_type),
            parliamentary_group_ids=[],
            politician_ids=[],
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
            judge_type=entity.judge_type.value,
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
        model.judge_type = entity.judge_type.value
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
        judge_type_str = data.get("judge_type", "parliamentary_group")
        return ProposalParliamentaryGroupJudge(
            id=data.get("id"),
            proposal_id=data["proposal_id"],
            judgment=data["judgment"],
            judge_type=JudgeType(judge_type_str),
            parliamentary_group_ids=data.get("parliamentary_group_ids", []),
            politician_ids=data.get("politician_ids", []),
            member_count=data.get("member_count"),
            note=data.get("note"),
        )
