"""Speaker repository implementation."""

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.dtos.speaker_dto import (
    SpeakerWithConversationCountDTO,
    SpeakerWithPoliticianDTO,
)
from src.domain.entities.politician import Politician
from src.domain.entities.speaker import Speaker
from src.domain.repositories.session_adapter import ISessionAdapter
from src.domain.repositories.speaker_repository import SpeakerRepository
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


# Time interval functions for timeline statistics
INTERVAL_FUNCTIONS = {
    "day": "DATE(updated_at)",
    "week": "DATE_TRUNC('week', updated_at)::date",
    "month": "DATE_TRUNC('month', updated_at)::date",
}


class SpeakerModel:
    """Speaker database model (dynamic)."""

    id: int | None
    name: str
    political_party_name: str | None
    position: str | None
    is_politician: bool
    politician_id: int | None
    matched_by_user_id: UUID | None

    def __init__(self, **kwargs: Any):
        for key, value in kwargs.items():
            setattr(self, key, value)


class SpeakerRepositoryImpl(BaseRepositoryImpl[Speaker], SpeakerRepository):
    """Implementation of speaker repository using SQLAlchemy."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        """Initialize repository with async session or session adapter."""
        super().__init__(session, Speaker, SpeakerModel)

    async def get_by_name_party_position(
        self,
        name: str,
        political_party_name: str | None = None,
        position: str | None = None,
    ) -> Speaker | None:
        """Get speaker by name, party, and position."""
        conditions = ["name = :name"]
        params = {"name": name}

        if political_party_name is not None:
            conditions.append("political_party_name = :political_party_name")
            params["political_party_name"] = political_party_name
        if position is not None:
            conditions.append("position = :position")
            params["position"] = position

        query = text(f"""
            SELECT * FROM speakers
            WHERE {" AND ".join(conditions)}
            LIMIT 1
        """)
        result = await self.session.execute(query, params)
        row = result.fetchone()

        if row:
            return self._row_to_entity(row)
        return None

    async def get_politicians(self) -> list[Speaker]:
        """Get all speakers who are politicians."""
        query = text("""
            SELECT * FROM speakers
            WHERE is_politician = true
            ORDER BY name
        """)
        result = await self.session.execute(query)
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def search_by_name(self, name_pattern: str) -> list[Speaker]:
        """Search speakers by name pattern."""
        query = text("""
            SELECT * FROM speakers
            WHERE name ILIKE :pattern
            ORDER BY name
        """)
        result = await self.session.execute(query, {"pattern": f"%{name_pattern}%"})
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def upsert(self, speaker: Speaker) -> Speaker:
        """Insert or update speaker (upsert)."""
        # Check if exists
        existing = await self.get_by_name_party_position(
            speaker.name,
            speaker.political_party_name,
            speaker.position,
        )

        if existing:
            # Update existing
            speaker.id = existing.id
            return await self.update(speaker)
        else:
            # Create new
            return await self.create(speaker)

    def _to_entity(self, model: Any) -> Speaker:
        """Convert database model to domain entity."""
        return Speaker(
            name=model.name,
            type=model.type,
            political_party_name=model.political_party_name,
            position=model.position,
            is_politician=model.is_politician,
            politician_id=getattr(model, "politician_id", None),
            matched_by_user_id=getattr(model, "matched_by_user_id", None),
            id=model.id,
        )

    def _to_model(self, entity: Speaker) -> Any:
        """Convert domain entity to database model."""
        return self.model_class(
            name=entity.name,
            type=entity.type,
            political_party_name=entity.political_party_name,
            position=entity.position,
            is_politician=entity.is_politician,
            politician_id=entity.politician_id,
            matched_by_user_id=entity.matched_by_user_id,
        )

    def _update_model(self, model: Any, entity: Speaker) -> None:
        """Update model fields from entity."""
        model.name = entity.name
        model.type = entity.type
        model.political_party_name = entity.political_party_name
        model.position = entity.position
        model.is_politician = entity.is_politician
        model.politician_id = entity.politician_id
        model.matched_by_user_id = entity.matched_by_user_id

    async def get_speakers_with_conversation_count(
        self,
        limit: int | None = None,
        offset: int | None = None,
        speaker_type: str | None = None,
        is_politician: bool | None = None,
    ) -> list[SpeakerWithConversationCountDTO]:
        """Get speakers with their conversation count."""
        # Build the WHERE clause conditions
        conditions = []
        params = {}

        if speaker_type is not None:
            conditions.append("s.type = :speaker_type")
            params["speaker_type"] = speaker_type

        if is_politician is not None:
            conditions.append("s.is_politician = :is_politician")
            params["is_politician"] = is_politician

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        # Build the pagination clause
        pagination_clause = ""
        if limit is not None:
            pagination_clause += " LIMIT :limit"
            params["limit"] = limit
        if offset is not None:
            pagination_clause += " OFFSET :offset"
            params["offset"] = offset

        # Execute the query
        query = text(f"""
            SELECT
                s.id,
                s.name,
                s.type,
                s.political_party_name,
                s.position,
                s.is_politician,
                COUNT(c.id) as conversation_count
            FROM speakers s
            LEFT JOIN conversations c ON s.id = c.speaker_id
            {where_clause}
            GROUP BY s.id, s.name, s.type, s.political_party_name,
                     s.position, s.is_politician
            ORDER BY s.name
            {pagination_clause}
        """)

        result = await self.session.execute(query, params)
        rows = result.fetchall()

        # Convert rows to DTOs
        return [
            SpeakerWithConversationCountDTO(
                id=row.id,
                name=row.name,
                type=row.type,
                political_party_name=row.political_party_name,
                position=row.position,
                is_politician=row.is_politician,
                conversation_count=row.conversation_count,
            )
            for row in rows
        ]

    async def find_by_name(self, name: str) -> Speaker | None:
        """Find speaker by name."""
        query = text("""
            SELECT * FROM speakers
            WHERE name = :name
            LIMIT 1
        """)
        result = await self.session.execute(query, {"name": name})
        row = result.fetchone()

        if row:
            return self._row_to_entity(row)
        return None

    async def get_speakers_not_linked_to_politicians(self) -> list[Speaker]:
        """Get speakers who are not linked to politicians (is_politician=False)."""
        query = text("""
            SELECT * FROM speakers
            WHERE is_politician = false
            ORDER BY name
        """)
        result = await self.session.execute(query)
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_all(
        self, limit: int | None = None, offset: int | None = 0
    ) -> list[Speaker]:
        """Get all speakers."""
        query_text = "SELECT * FROM speakers ORDER BY name"
        params = {}

        if limit is not None:
            query_text += " LIMIT :limit OFFSET :offset"
            params = {"limit": limit, "offset": offset or 0}

        result = await self.session.execute(
            text(query_text), params if params else None
        )
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_by_id(self, entity_id: int) -> Speaker | None:
        """Get speaker by ID."""
        query = text("SELECT * FROM speakers WHERE id = :id")
        result = await self.session.execute(query, {"id": entity_id})
        row = result.fetchone()

        if row:
            return self._row_to_entity(row)
        return None

    async def create(self, entity: Speaker) -> Speaker:
        """Create a new speaker."""
        query = text("""
            INSERT INTO speakers (
                name, type, political_party_name, position, is_politician,
                matched_by_user_id
            )
            VALUES (
                :name, :type, :political_party_name, :position, :is_politician,
                :matched_by_user_id
            )
            RETURNING *
        """)

        params = {
            "name": entity.name,
            "type": entity.type,
            "political_party_name": entity.political_party_name,
            "position": entity.position,
            "is_politician": entity.is_politician,
            "matched_by_user_id": entity.matched_by_user_id,
        }

        result = await self.session.execute(query, params)
        await self.session.commit()

        row = result.first()
        if row:
            return self._row_to_entity(row)
        raise RuntimeError("Failed to create speaker")

    async def update(self, entity: Speaker) -> Speaker:
        """Update an existing speaker."""
        query = text("""
            UPDATE speakers
            SET name = :name,
                type = :type,
                political_party_name = :political_party_name,
                position = :position,
                is_politician = :is_politician,
                politician_id = :politician_id,
                matched_by_user_id = :matched_by_user_id
            WHERE id = :id
            RETURNING *
        """)

        params = {
            "id": entity.id,
            "name": entity.name,
            "type": entity.type,
            "political_party_name": entity.political_party_name,
            "position": entity.position,
            "is_politician": entity.is_politician,
            "politician_id": entity.politician_id,
            "matched_by_user_id": entity.matched_by_user_id,
        }

        result = await self.session.execute(query, params)
        await self.session.commit()

        row = result.first()
        if row:
            return self._row_to_entity(row)
        raise ValueError(f"Speaker with ID {entity.id} not found")

    def _row_to_entity(self, row: Any) -> Speaker:
        """Convert database row to domain entity."""
        return Speaker(
            id=row.id,
            name=row.name,
            type=getattr(row, "type", None),
            political_party_name=getattr(row, "political_party_name", None),
            position=getattr(row, "position", None),
            is_politician=getattr(row, "is_politician", False),
            politician_id=getattr(row, "politician_id", None),
            matched_by_user_id=getattr(row, "matched_by_user_id", None),
        )

    async def get_speakers_with_politician_info(self) -> list[dict[str, Any]]:
        """Get speakers with linked politician information."""
        query = text("""
            SELECT
                s.id,
                s.name,
                s.type,
                s.political_party_name,
                s.position,
                s.is_politician,
                p.id as politician_id,
                p.name as politician_name,
                pp.name as party_name_from_politician,
                COUNT(c.id) as conversation_count
            FROM speakers s
            LEFT JOIN politicians p ON s.politician_id = p.id
            LEFT JOIN political_parties pp ON p.political_party_id = pp.id
            LEFT JOIN conversations c ON s.id = c.speaker_id
            GROUP BY s.id, s.name, s.type, s.political_party_name,
                     s.position, s.is_politician, p.id, p.name, pp.name
            ORDER BY s.name
        """)

        result = await self.session.execute(query)
        rows = result.fetchall()

        return [
            {
                "id": row.id,
                "name": row.name,
                "type": row.type,
                "political_party_name": row.political_party_name,
                "position": row.position,
                "is_politician": row.is_politician,
                "politician_id": row.politician_id,
                "politician_name": row.politician_name,
                "party_name_from_politician": row.party_name_from_politician,
                "conversation_count": row.conversation_count,
            }
            for row in rows
        ]

    async def get_speaker_politician_stats(self) -> dict[str, int | float]:
        """Get statistics of speaker-politician linkage."""
        query = text("""
            WITH stats AS (
                SELECT
                    COUNT(*) as total_speakers,
                    COUNT(CASE WHEN is_politician = TRUE THEN 1 END)
                        as politician_speakers,
                    COUNT(CASE WHEN is_politician = FALSE THEN 1 END)
                        as non_politician_speakers
                FROM speakers
            ),
            linked_stats AS (
                SELECT
                    COUNT(DISTINCT s.id) as linked_speakers,
                    COUNT(
                        DISTINCT CASE WHEN s.is_politician = TRUE THEN s.id END
                    ) as linked_politician_speakers
                FROM speakers s
                INNER JOIN politicians p ON s.id = p.speaker_id
            )
            SELECT
                stats.total_speakers,
                linked_stats.linked_speakers,
                stats.politician_speakers,
                linked_stats.linked_politician_speakers,
                stats.non_politician_speakers,
                CASE
                    WHEN stats.politician_speakers > 0
                    THEN ROUND(
                        CAST(
                            linked_stats.linked_politician_speakers AS NUMERIC
                        ) * 100.0 / stats.politician_speakers, 1
                    )
                    ELSE 0
                END as link_rate
            FROM stats, linked_stats
        """)

        result = await self.session.execute(query)
        row = result.fetchone()

        if row:
            return {
                "total_speakers": row.total_speakers,
                "linked_speakers": row.linked_speakers,
                "politician_speakers": row.politician_speakers,
                "linked_politician_speakers": row.linked_politician_speakers,
                "non_politician_speakers": row.non_politician_speakers,
                "link_rate": float(row.link_rate),
            }
        else:
            return {
                "total_speakers": 0,
                "linked_speakers": 0,
                "politician_speakers": 0,
                "linked_politician_speakers": 0,
                "non_politician_speakers": 0,
                "link_rate": 0.0,
            }

    async def get_all_for_matching(self) -> list[dict[str, Any]]:
        """Get all speakers for matching purposes."""
        query = text("SELECT id, name FROM speakers ORDER BY name")
        result = await self.session.execute(query)
        rows = result.fetchall()

        return [{"id": row.id, "name": row.name} for row in rows]

    async def get_affiliated_speakers(
        self, meeting_date: str, conference_id: int
    ) -> list[dict[str, Any]]:
        """Get speakers affiliated with a conference at a specific date."""
        query = text("""
            SELECT DISTINCT
                s.id as speaker_id,
                s.name as speaker_name,
                p.id as politician_id,
                p.name as politician_name,
                pa.role as role
            FROM politician_affiliations pa
            JOIN politicians p ON pa.politician_id = p.id
            JOIN speakers s ON p.speaker_id = s.id
            WHERE pa.conference_id = :conference_id
                AND pa.start_date <= CAST(:meeting_date AS date)
                AND (pa.end_date IS NULL OR
                     pa.end_date >= CAST(:meeting_date AS date))
            ORDER BY s.name
        """)

        result = await self.session.execute(
            query, {"conference_id": conference_id, "meeting_date": meeting_date}
        )
        rows = result.fetchall()

        return [
            {
                "speaker_id": row.speaker_id,
                "speaker_name": row.speaker_name,
                "politician_id": row.politician_id,
                "politician_name": row.politician_name,
                "role": row.role,
            }
            for row in rows
        ]

    async def find_by_matched_user(
        self, user_id: "UUID | None" = None
    ) -> list[SpeakerWithPoliticianDTO]:
        """指定されたユーザーIDによってマッチングされた発言者と政治家情報を取得する

        Args:
            user_id: フィルタリング対象のユーザーID（Noneの場合は全ユーザー）

        Returns:
            発言者と紐付けられた政治家情報を含むDTOのリスト
        """
        # Build SQL query with optional user_id filter
        query_text = """
            SELECT
                s.id,
                s.name,
                s.type,
                s.political_party_name,
                s.position,
                s.is_politician,
                s.politician_id,
                s.matched_by_user_id,
                s.updated_at,
                p.id as politician_id_from_join,
                p.name as politician_name
            FROM speakers s
            LEFT JOIN politicians p ON s.politician_id = p.id
            WHERE s.matched_by_user_id IS NOT NULL
        """

        params = {}
        if user_id is not None:
            query_text += " AND s.matched_by_user_id = :user_id"
            params["user_id"] = user_id

        query = text(query_text)
        result = await self.session.execute(query, params)
        rows = result.fetchall()

        # Convert rows to DTOs
        results = []
        for row in rows:
            speaker = Speaker(
                id=row.id,
                name=row.name,
                type=row.type,
                political_party_name=row.political_party_name,
                position=row.position,
                is_politician=row.is_politician,
                politician_id=row.politician_id,
                matched_by_user_id=row.matched_by_user_id,
                updated_at=row.updated_at,
            )

            # Create politician entity if exists
            politician = None
            if row.politician_id_from_join:
                politician = Politician(
                    id=row.politician_id_from_join,
                    name=row.politician_name,
                )

            # Create DTO with speaker and politician
            results.append(
                SpeakerWithPoliticianDTO(speaker=speaker, politician=politician)
            )

        return results

    async def get_speaker_matching_statistics_by_user(
        self,
        user_id: "UUID | None" = None,
        start_date: Any | None = None,
        end_date: Any | None = None,
    ) -> dict[UUID, int]:
        """ユーザー別の発言者紐付け件数を集計する（データベースレベルで集計）

        Args:
            user_id: フィルタリング対象のユーザーID（Noneの場合は全ユーザー）
            start_date: 開始日時（この日時以降の作業を集計）
            end_date: 終了日時（この日時以前の作業を集計）

        Returns:
            ユーザーIDと件数のマッピング（例: {UUID('...'): 10, UUID('...'): 5}）
        """
        # Build SQL query with GROUP BY
        query_text = """
            SELECT
                matched_by_user_id,
                COUNT(*) as count
            FROM speakers
            WHERE matched_by_user_id IS NOT NULL
        """

        params: dict[str, Any] = {}

        # Add user filter if specified
        if user_id is not None:
            query_text += " AND matched_by_user_id = :user_id"
            params["user_id"] = user_id

        # Add date filters if specified
        if start_date is not None:
            query_text += " AND updated_at >= :start_date"
            params["start_date"] = start_date

        if end_date is not None:
            query_text += " AND updated_at <= :end_date"
            params["end_date"] = end_date

        query_text += " GROUP BY matched_by_user_id"

        query = text(query_text)
        result = await self.session.execute(query, params)
        rows = result.fetchall()

        # Convert to dictionary
        statistics: dict[UUID, int] = {}
        for row in rows:
            # Use cast to ensure type safety
            from typing import cast

            statistics[cast(UUID, row.matched_by_user_id)] = cast(int, row.count)

        return statistics

    async def get_speaker_matching_timeline_statistics(
        self,
        user_id: "UUID | None" = None,
        start_date: Any | None = None,
        end_date: Any | None = None,
        interval: str = "day",
    ) -> list[dict[str, Any]]:
        """時系列の発言者紐付け件数を集計する（データベースレベルで集計）

        Args:
            user_id: フィルタリング対象のユーザーID（Noneの場合は全ユーザー）
            start_date: 開始日時
            end_date: 終了日時
            interval: 集計間隔（"day", "week", "month"）

        Returns:
            時系列データのリスト（例: [{"date": "2024-01-01", "count": 5}, ...]）
        """
        # Determine date truncation function based on interval
        date_trunc = INTERVAL_FUNCTIONS.get(interval)
        if date_trunc is None:
            raise ValueError(f"Invalid interval: {interval}")

        # Build SQL query
        query_text = f"""
            SELECT
                {date_trunc} as date,
                COUNT(*) as count
            FROM speakers
            WHERE matched_by_user_id IS NOT NULL
              AND updated_at IS NOT NULL
        """

        params: dict[str, Any] = {}

        # Add user filter if specified
        if user_id is not None:
            query_text += " AND matched_by_user_id = :user_id"
            params["user_id"] = user_id

        # Add date filters if specified
        if start_date is not None:
            query_text += " AND updated_at >= :start_date"
            params["start_date"] = start_date

        if end_date is not None:
            query_text += " AND updated_at <= :end_date"
            params["end_date"] = end_date

        query_text += f" GROUP BY {date_trunc} ORDER BY date"

        query = text(query_text)
        result = await self.session.execute(query, params)
        rows = result.fetchall()

        # Convert to list of dictionaries
        timeline = []
        for row in rows:
            timeline.append({"date": str(row.date), "count": row.count})

        return timeline
