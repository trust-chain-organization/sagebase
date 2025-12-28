"""Monitoring repository implementation for Clean Architecture."""

from typing import Any, TypedDict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.repositories.session_adapter import ISessionAdapter


class ActivityDetails(TypedDict, total=False):
    """Type definition for activity details."""

    conference: str | None
    governing_body: str | None
    party: str | None


class Activity(TypedDict):
    """Type definition for activity."""

    type: str
    id: int
    name: str
    date: str | None
    created_at: str | None
    details: ActivityDetails


class ConferenceCoverage(TypedDict):
    """Type definition for conference coverage."""

    id: int
    name: str
    governing_body: str
    meetings: int
    politicians: int
    conversations: int
    period: dict[str, str | None]


class TimelineEntry(TypedDict):
    """Type definition for timeline entry."""

    date: str
    count: int


class PartyCoverage(TypedDict):
    """Type definition for party coverage."""

    id: int
    name: str
    politicians: int
    speakers: int
    conversations: int


class PrefectureCoverage(TypedDict):
    """Type definition for prefecture coverage."""

    id: int
    name: str
    type: str
    organization_code: str | None
    organization_type: str | None
    status: str
    conferences: int
    meetings: int
    politicians: int
    conversations: int
    period: dict[str, str | None]


class PrefectureSummary(TypedDict):
    """Type definition for prefecture summary."""

    total: int
    with_data: int
    coverage: float


class CommitteeType(TypedDict):
    """Type definition for committee type."""

    type: str
    conferences: int
    meetings: int
    governing_bodies: int


class MonitoringRepositoryImpl:
    """Implementation of monitoring repository using AsyncSession."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        self.session = session

    async def get_overall_metrics(self) -> dict[str, Any]:
        """Get overall system metrics."""
        query = text("""
            WITH metrics AS (
                SELECT
                    (SELECT COUNT(*) FROM governing_bodies) as total_governing_bodies,
                    (SELECT COUNT(DISTINCT governing_body_id) FROM conferences)
                        as active_governing_bodies,
                    (SELECT COUNT(*) FROM conferences) as total_conferences,
                    (SELECT COUNT(DISTINCT conference_id) FROM meetings)
                        as active_conferences,
                    (SELECT COUNT(*) FROM meetings) as total_meetings,
                    (SELECT COUNT(*) FROM politicians) as total_politicians,
                    (SELECT COUNT(DISTINCT p.id)
                     FROM politicians p
                     JOIN politician_affiliations pa ON p.id = pa.politician_id)
                        as active_politicians,
                    (SELECT COUNT(*) FROM political_parties) as total_parties,
                    (SELECT COUNT(DISTINCT political_party_id) FROM politicians
                     WHERE political_party_id IS NOT NULL) as active_parties,
                    (SELECT COUNT(*) FROM conversations) as total_conversations,
                    (SELECT COUNT(DISTINCT speaker_id) FROM conversations
                     WHERE speaker_id IS NOT NULL) as linked_conversations,
                    (SELECT COUNT(*) FROM speakers) as total_speakers,
                    (SELECT COUNT(*) FROM speakers
                     WHERE type = 'politician' OR type = '政治家')
                        as linked_speakers
            )
            SELECT * FROM metrics
        """)

        result = await self.session.execute(query)
        row = result.fetchone()

        if not row:
            return {
                "governing_bodies": {"total": 0, "active": 0, "coverage": 0.0},
                "conferences": {"total": 0, "active": 0, "coverage": 0.0},
                "meetings": {"total": 0},
                "politicians": {"total": 0, "active": 0, "utilization": 0.0},
                "parties": {"total": 0, "active": 0, "coverage": 0.0},
                "conversations": {"total": 0, "linked": 0, "linkage_rate": 0.0},
                "speakers": {"total": 0, "linked": 0, "linkage_rate": 0.0},
            }

        return {
            "governing_bodies": {
                "total": row.total_governing_bodies,
                "active": row.active_governing_bodies,
                "coverage": (
                    (row.active_governing_bodies / row.total_governing_bodies * 100)
                    if row.total_governing_bodies > 0
                    else 0.0
                ),
            },
            "conferences": {
                "total": row.total_conferences,
                "active": row.active_conferences,
                "coverage": (
                    (row.active_conferences / row.total_conferences * 100)
                    if row.total_conferences > 0
                    else 0.0
                ),
            },
            "meetings": {"total": row.total_meetings},
            "politicians": {
                "total": row.total_politicians,
                "active": row.active_politicians,
                "utilization": (
                    (row.active_politicians / row.total_politicians * 100)
                    if row.total_politicians > 0
                    else 0.0
                ),
            },
            "parties": {
                "total": row.total_parties,
                "active": row.active_parties,
                "coverage": (
                    (row.active_parties / row.total_parties * 100)
                    if row.total_parties > 0
                    else 0.0
                ),
            },
            "conversations": {
                "total": row.total_conversations,
                "linked": row.linked_conversations,
                "linkage_rate": (
                    (row.linked_conversations / row.total_conversations * 100)
                    if row.total_conversations > 0
                    else 0.0
                ),
            },
            "speakers": {
                "total": row.total_speakers,
                "linked": row.linked_speakers,
                "linkage_rate": (
                    (row.linked_speakers / row.total_speakers * 100)
                    if row.total_speakers > 0
                    else 0.0
                ),
            },
        }

    async def get_recent_activities(self, limit: int = 10) -> list[Activity]:
        """Get recent system activities."""
        query = text("""
            WITH recent_activities AS (
                SELECT
                    'meeting' as type,
                    m.id,
                    m.name,
                    m.date,
                    m.created_at,
                    c.name as conference_name,
                    gb.name as governing_body_name
                FROM meetings m
                JOIN conferences c ON m.conference_id = c.id
                JOIN governing_bodies gb ON c.governing_body_id = gb.id
                WHERE m.created_at IS NOT NULL

                UNION ALL

                SELECT
                    'politician' as type,
                    p.id,
                    p.name,
                    NULL as date,
                    p.created_at,
                    pp.name as conference_name,
                    NULL as governing_body_name
                FROM politicians p
                LEFT JOIN political_parties pp ON p.political_party_id = pp.id
                WHERE p.created_at IS NOT NULL

                UNION ALL

                SELECT
                    'speaker' as type,
                    s.id,
                    s.name,
                    NULL as date,
                    s.created_at,
                    NULL as conference_name,
                    NULL as governing_body_name
                FROM speakers s
                WHERE s.created_at IS NOT NULL
            )
            SELECT * FROM recent_activities
            ORDER BY created_at DESC
            LIMIT :limit
        """)

        result = await self.session.execute(query, {"limit": limit})
        activities: list[Activity] = []

        for row in result:
            activity: Activity = {
                "type": row.type,
                "id": row.id,
                "name": row.name,
                "date": row.date.isoformat() if row.date else None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "details": {},
            }

            if row.type == "meeting":
                activity["details"]["conference"] = row.conference_name
                activity["details"]["governing_body"] = row.governing_body_name
            elif row.type == "politician":
                activity["details"]["party"] = row.conference_name

            activities.append(activity)

        return activities

    async def get_conference_coverage(self) -> list[ConferenceCoverage]:
        """Get coverage statistics by conference."""
        query = text("""
            SELECT
                c.id,
                c.name,
                gb.name as governing_body_name,
                COUNT(DISTINCT m.id) as meeting_count,
                COUNT(DISTINCT pa.politician_id) as politician_count,
                COUNT(DISTINCT conv.id) as conversation_count,
                MIN(m.date) as first_meeting_date,
                MAX(m.date) as last_meeting_date
            FROM conferences c
            JOIN governing_bodies gb ON c.governing_body_id = gb.id
            LEFT JOIN meetings m ON c.id = m.conference_id
            LEFT JOIN politician_affiliations pa ON c.id = pa.conference_id
            LEFT JOIN minutes min ON m.id = min.meeting_id
            LEFT JOIN conversations conv ON min.id = conv.minutes_id
            GROUP BY c.id, c.name, gb.name
            ORDER BY meeting_count DESC
        """)

        result = await self.session.execute(query)
        coverage_data: list[ConferenceCoverage] = []

        for row in result:
            coverage_data.append(
                {
                    "id": row.id,
                    "name": row.name,
                    "governing_body": row.governing_body_name,
                    "meetings": row.meeting_count,
                    "politicians": row.politician_count,
                    "conversations": row.conversation_count,
                    "period": {
                        "start": (
                            row.first_meeting_date.isoformat()
                            if row.first_meeting_date
                            else None
                        ),
                        "end": (
                            row.last_meeting_date.isoformat()
                            if row.last_meeting_date
                            else None
                        ),
                    },
                }
            )

        return coverage_data

    async def get_timeline_data(
        self, period_days: int = 30
    ) -> dict[str, list[TimelineEntry]]:
        """Get timeline data for various metrics."""
        query = text("""
            WITH date_series AS (
                SELECT generate_series(
                    CURRENT_DATE - INTERVAL ':days days',
                    CURRENT_DATE,
                    '1 day'::interval
                )::date as date
            ),
            daily_meetings AS (
                SELECT
                    DATE(date) as date,
                    COUNT(*) as count
                FROM meetings
                WHERE date >= CURRENT_DATE - INTERVAL ':days days'
                GROUP BY DATE(date)
            ),
            daily_conversations AS (
                SELECT
                    DATE(m.date) as date,
                    COUNT(c.id) as count
                FROM conversations c
                JOIN minutes min ON c.minutes_id = min.id
                JOIN meetings m ON min.meeting_id = m.id
                WHERE m.date >= CURRENT_DATE - INTERVAL ':days days'
                GROUP BY DATE(m.date)
            ),
            daily_politicians AS (
                SELECT
                    DATE(created_at) as date,
                    COUNT(*) as count
                FROM politicians
                WHERE created_at >= CURRENT_DATE - INTERVAL ':days days'
                GROUP BY DATE(created_at)
            )
            SELECT
                ds.date,
                COALESCE(dm.count, 0) as meeting_count,
                COALESCE(dc.count, 0) as conversation_count,
                COALESCE(dp.count, 0) as politician_count
            FROM date_series ds
            LEFT JOIN daily_meetings dm ON ds.date = dm.date
            LEFT JOIN daily_conversations dc ON ds.date = dc.date
            LEFT JOIN daily_politicians dp ON ds.date = dp.date
            ORDER BY ds.date
        """)

        # Note: PostgreSQL doesn't support named parameters in INTERVAL expressions
        # We need to use a different approach
        query = text(f"""
            WITH date_series AS (
                SELECT generate_series(
                    CURRENT_DATE - INTERVAL '{period_days} days',
                    CURRENT_DATE,
                    '1 day'::interval
                )::date as date
            ),
            daily_meetings AS (
                SELECT
                    DATE(date) as date,
                    COUNT(*) as count
                FROM meetings
                WHERE date >= CURRENT_DATE - INTERVAL '{period_days} days'
                GROUP BY DATE(date)
            ),
            daily_conversations AS (
                SELECT
                    DATE(m.date) as date,
                    COUNT(c.id) as count
                FROM conversations c
                JOIN minutes min ON c.minutes_id = min.id
                JOIN meetings m ON min.meeting_id = m.id
                WHERE m.date >= CURRENT_DATE - INTERVAL '{period_days} days'
                GROUP BY DATE(m.date)
            ),
            daily_politicians AS (
                SELECT
                    DATE(created_at) as date,
                    COUNT(*) as count
                FROM politicians
                WHERE created_at >= CURRENT_DATE - INTERVAL '{period_days} days'
                GROUP BY DATE(created_at)
            )
            SELECT
                ds.date,
                COALESCE(dm.count, 0) as meeting_count,
                COALESCE(dc.count, 0) as conversation_count,
                COALESCE(dp.count, 0) as politician_count
            FROM date_series ds
            LEFT JOIN daily_meetings dm ON ds.date = dm.date
            LEFT JOIN daily_conversations dc ON ds.date = dc.date
            LEFT JOIN daily_politicians dp ON ds.date = dp.date
            ORDER BY ds.date
        """)

        result = await self.session.execute(query)

        meetings_timeline: list[TimelineEntry] = []
        conversations_timeline: list[TimelineEntry] = []
        politicians_timeline: list[TimelineEntry] = []

        for row in result:
            date_str = row.date.isoformat()
            meetings_timeline.append({"date": date_str, "count": row.meeting_count})
            conversations_timeline.append(
                {"date": date_str, "count": row.conversation_count}
            )
            politicians_timeline.append(
                {"date": date_str, "count": row.politician_count}
            )

        return {
            "meetings": meetings_timeline,
            "conversations": conversations_timeline,
            "politicians": politicians_timeline,
        }

    async def get_party_coverage(self) -> list[PartyCoverage]:
        """Get coverage statistics by political party."""
        query = text("""
            SELECT
                pp.id,
                pp.name,
                COUNT(DISTINCT p.id) as politician_count,
                COUNT(DISTINCT s.id) as speaker_count,
                COUNT(DISTINCT c.id) as conversation_count
            FROM political_parties pp
            LEFT JOIN politicians p ON pp.id = p.political_party_id
            LEFT JOIN speakers s ON pp.name = s.political_party_name
            LEFT JOIN conversations c ON s.id = c.speaker_id
            GROUP BY pp.id, pp.name
            ORDER BY politician_count DESC
        """)

        result = await self.session.execute(query)
        party_data: list[PartyCoverage] = []

        for row in result:
            party_data.append(
                {
                    "id": row.id,
                    "name": row.name,
                    "politicians": row.politician_count,
                    "speakers": row.speaker_count,
                    "conversations": row.conversation_count,
                }
            )

        return party_data

    async def get_prefecture_detailed_coverage(self) -> list[PrefectureCoverage]:
        """Get detailed coverage statistics by prefecture."""
        query = text("""
            WITH prefecture_stats AS (
                SELECT
                    gb.id,
                    gb.name,
                    gb.type,
                    gb.organization_code,
                    gb.organization_type,
                    COUNT(DISTINCT c.id) as conference_count,
                    COUNT(DISTINCT m.id) as meeting_count,
                    COUNT(DISTINCT pa.politician_id) as politician_count,
                    COUNT(DISTINCT conv.id) as conversation_count,
                    MIN(m.date) as first_meeting_date,
                    MAX(m.date) as last_meeting_date
                FROM governing_bodies gb
                LEFT JOIN conferences c ON gb.id = c.governing_body_id
                LEFT JOIN meetings m ON c.id = m.conference_id
                LEFT JOIN politician_affiliations pa ON c.id = pa.conference_id
                LEFT JOIN minutes min ON m.id = min.meeting_id
                LEFT JOIN conversations conv ON min.id = conv.minutes_id
                WHERE gb.type IN ('都道府県', '市町村')
                GROUP BY gb.id, gb.name, gb.type,
                    gb.organization_code, gb.organization_type
            )
            SELECT
                ps.*,
                CASE
                    WHEN ps.meeting_count > 0 THEN 'active'
                    WHEN ps.conference_count > 0 THEN 'partial'
                    ELSE 'inactive'
                END as status
            FROM prefecture_stats ps
            ORDER BY ps.type, ps.name
        """)

        result = await self.session.execute(query)
        coverage_data: list[PrefectureCoverage] = []

        for row in result:
            coverage_data.append(
                {
                    "id": row.id,
                    "name": row.name,
                    "type": row.type,
                    "organization_code": row.organization_code,
                    "organization_type": row.organization_type,
                    "status": row.status,
                    "conferences": row.conference_count,
                    "meetings": row.meeting_count,
                    "politicians": row.politician_count,
                    "conversations": row.conversation_count,
                    "period": {
                        "start": (
                            row.first_meeting_date.isoformat()
                            if row.first_meeting_date
                            else None
                        ),
                        "end": (
                            row.last_meeting_date.isoformat()
                            if row.last_meeting_date
                            else None
                        ),
                    },
                }
            )

        return coverage_data

    async def get_prefecture_coverage(self) -> dict[str, Any]:
        """Get summary of prefecture coverage."""
        query = text("""
            WITH coverage AS (
                SELECT
                    gb.type,
                    COUNT(DISTINCT gb.id) as total,
                    COUNT(DISTINCT CASE
                        WHEN m.id IS NOT NULL THEN gb.id END) as with_data
                FROM governing_bodies gb
                LEFT JOIN conferences c ON gb.id = c.governing_body_id
                LEFT JOIN meetings m ON c.id = m.conference_id
                WHERE gb.type IN ('都道府県', '市町村')
                GROUP BY gb.type
            )
            SELECT
                type,
                total,
                with_data,
                ROUND(CAST(CAST(with_data AS REAL) / total * 100 AS NUMERIC), 2)
                    as coverage_percentage
            FROM coverage
        """)

        result = await self.session.execute(query)
        summary: dict[str, Any] = {"prefectures": {}, "municipalities": {}}

        for row in result:
            data: PrefectureSummary = {
                "total": row.total,
                "with_data": row.with_data,
                "coverage": float(row.coverage_percentage),
            }

            if row.type == "都道府県":
                summary["prefectures"] = data
            elif row.type == "市町村":
                summary["municipalities"] = data

        return summary

    async def get_committee_type_coverage(self) -> list[CommitteeType]:
        """Get coverage by committee type."""
        query = text("""
            SELECT
                c.type as committee_type,
                COUNT(DISTINCT c.id) as conference_count,
                COUNT(DISTINCT m.id) as meeting_count,
                COUNT(DISTINCT gb.id) as governing_body_count
            FROM conferences c
            LEFT JOIN meetings m ON c.id = m.conference_id
            LEFT JOIN governing_bodies gb ON c.governing_body_id = gb.id
            GROUP BY c.type
            ORDER BY conference_count DESC
        """)

        result = await self.session.execute(query)
        committee_data: list[CommitteeType] = []

        for row in result:
            committee_data.append(
                {
                    "type": row.committee_type or "未分類",
                    "conferences": row.conference_count,
                    "meetings": row.meeting_count,
                    "governing_bodies": row.governing_body_count,
                }
            )

        return committee_data
