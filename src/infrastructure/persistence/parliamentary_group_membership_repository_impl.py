"""Parliamentary group membership repository implementation."""

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.dtos.parliamentary_group_membership_dto import (
    ParliamentaryGroupMembershipWithRelationsDTO,
)
from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.entities.parliamentary_group_membership import (
    ParliamentaryGroupMembership as ParliamentaryGroupMembershipEntity,
)
from src.domain.entities.politician import Politician
from src.domain.repositories.parliamentary_group_membership_repository import (
    ParliamentaryGroupMembershipRepository,
)
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl
from src.infrastructure.persistence.sqlalchemy_models import (
    ParliamentaryGroupMembershipModel,
)


# Time interval functions for timeline statistics
INTERVAL_FUNCTIONS = {
    "day": "DATE(created_at)",
    "week": "DATE_TRUNC('week', created_at)::date",
    "month": "DATE_TRUNC('month', created_at)::date",
}

# Placeholder for lazy-loaded conference_id in partial entity construction
PLACEHOLDER_CONFERENCE_ID = 0


class ParliamentaryGroupMembershipRepositoryImpl(
    BaseRepositoryImpl[ParliamentaryGroupMembershipEntity],
    ParliamentaryGroupMembershipRepository,
):
    """Parliamentary group membership repository implementation using SQLAlchemy."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        """Initialize repository.

        Args:
            session: Async database session
        """
        super().__init__(
            session=session,
            entity_class=ParliamentaryGroupMembershipEntity,
            model_class=ParliamentaryGroupMembershipModel,
        )

    async def get_by_group(
        self, group_id: int
    ) -> list[ParliamentaryGroupMembershipEntity]:
        """Get memberships by group."""
        query = select(self.model_class).where(
            self.model_class.parliamentary_group_id == group_id
        )
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]

    async def get_by_politician(
        self, politician_id: int
    ) -> list[ParliamentaryGroupMembershipEntity]:
        """Get memberships by politician."""
        query = select(self.model_class).where(
            self.model_class.politician_id == politician_id
        )
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]

    async def get_active_by_group(
        self, group_id: int, as_of_date: date | None = None
    ) -> list[ParliamentaryGroupMembershipEntity]:
        """Get active memberships by group."""
        if as_of_date is None:
            as_of_date = date.today()

        query = select(self.model_class).where(
            and_(
                self.model_class.parliamentary_group_id == group_id,
                self.model_class.start_date <= as_of_date,
                (
                    self.model_class.end_date.is_(None)
                    | (self.model_class.end_date >= as_of_date)
                ),
            )
        )
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]

    async def create_membership(
        self,
        politician_id: int,
        group_id: int,
        start_date: date,
        role: str | None = None,
        created_by_user_id: UUID | None = None,
    ) -> ParliamentaryGroupMembershipEntity:
        """Create a new membership."""
        # Check if already exists using ORM
        existing_query = select(self.model_class).where(
            and_(
                self.model_class.politician_id == politician_id,
                self.model_class.parliamentary_group_id == group_id,
                self.model_class.start_date == start_date,
            )
        )
        result = await self.session.execute(existing_query)
        existing_model = result.scalars().first()

        if existing_model:
            return self._to_entity(existing_model)

        # Create new membership using ORM
        new_model = self.model_class(
            politician_id=politician_id,
            parliamentary_group_id=group_id,
            start_date=start_date,
            role=role,
            created_by_user_id=created_by_user_id,
        )
        self.session.add(new_model)
        await self.session.flush()  # Get the ID without committing
        await self.session.refresh(new_model)  # Refresh to get all fields

        return self._to_entity(new_model)

    async def add_membership(
        self,
        politician_id: int,
        parliamentary_group_id: int,
        start_date: date,
        role: str | None = None,
        end_date: date | None = None,
        created_by_user_id: UUID | None = None,
    ) -> ParliamentaryGroupMembershipEntity:
        """Add a new parliamentary group membership.

        Args:
            politician_id: Politician ID
            parliamentary_group_id: Parliamentary group ID
            start_date: Membership start date
            role: Member role (optional)
            end_date: Membership end date (optional)
            created_by_user_id: User ID who created the membership (optional)

        Returns:
            Created membership entity
        """
        # Check if already exists
        from sqlalchemy.future import select

        existing_query = select(self.model_class).where(
            and_(
                self.model_class.politician_id == politician_id,
                self.model_class.parliamentary_group_id == parliamentary_group_id,
                self.model_class.start_date == start_date,
            )
        )
        result = await self.session.execute(existing_query)
        existing_model = result.scalars().first()

        if existing_model:
            return self._to_entity(existing_model)

        # Create new membership using ORM
        new_model = self.model_class(
            politician_id=politician_id,
            parliamentary_group_id=parliamentary_group_id,
            start_date=start_date,
            end_date=end_date,
            role=role,
            created_by_user_id=created_by_user_id,
        )
        self.session.add(new_model)
        await self.session.flush()
        await self.session.refresh(new_model)

        return self._to_entity(new_model)

    async def end_membership(
        self, membership_id: int, end_date: date
    ) -> ParliamentaryGroupMembershipEntity | None:
        """End a membership."""
        model = await self.session.get(self.model_class, membership_id)
        if not model:
            return None

        model.end_date = end_date
        await self.session.flush()
        await self.session.refresh(model)

        return self._to_entity(model)

    async def get_current_members(self, group_id: int) -> list[dict[str, Any]]:
        """Get current members of a parliamentary group."""
        today = date.today()
        query = select(self.model_class).where(
            and_(
                self.model_class.parliamentary_group_id == group_id,
                self.model_class.start_date <= today,
                (
                    self.model_class.end_date.is_(None)
                    | (self.model_class.end_date >= today)
                ),
            )
        )

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [
            {
                "id": model.id,
                "politician_id": model.politician_id,
                "parliamentary_group_id": model.parliamentary_group_id,
                "start_date": model.start_date,
                "end_date": model.end_date,
                "role": model.role,
            }
            for model in models
        ]

    def _to_entity(
        self, model: ParliamentaryGroupMembershipModel
    ) -> ParliamentaryGroupMembershipEntity:
        """Convert database model to domain entity."""
        return ParliamentaryGroupMembershipEntity(
            id=model.id,
            politician_id=model.politician_id,
            parliamentary_group_id=model.parliamentary_group_id,
            start_date=model.start_date,
            end_date=model.end_date,
            role=model.role,
            created_by_user_id=model.created_by_user_id,
            is_manually_verified=bool(getattr(model, "is_manually_verified", False)),
            latest_extraction_log_id=getattr(model, "latest_extraction_log_id", None),
        )

    def _to_model(
        self, entity: ParliamentaryGroupMembershipEntity
    ) -> ParliamentaryGroupMembershipModel:
        """Convert domain entity to database model."""
        from datetime import datetime

        return ParliamentaryGroupMembershipModel(
            id=entity.id or 0,  # Use 0 for new entities, will be set by DB
            politician_id=entity.politician_id,
            parliamentary_group_id=entity.parliamentary_group_id,
            start_date=entity.start_date,
            end_date=entity.end_date,
            role=entity.role,
            created_by_user_id=entity.created_by_user_id,
            is_manually_verified=entity.is_manually_verified,
            latest_extraction_log_id=entity.latest_extraction_log_id,
            created_at=datetime.now() if not entity.id else None,
            updated_at=datetime.now(),
        )

    def _update_model(
        self,
        model: ParliamentaryGroupMembershipModel,
        entity: ParliamentaryGroupMembershipEntity,
    ) -> None:
        """Update model fields from entity."""
        model.politician_id = entity.politician_id
        model.parliamentary_group_id = entity.parliamentary_group_id
        model.start_date = entity.start_date
        model.end_date = entity.end_date
        model.role = entity.role
        model.created_by_user_id = entity.created_by_user_id
        model.is_manually_verified = entity.is_manually_verified
        model.latest_extraction_log_id = entity.latest_extraction_log_id

    async def find_by_created_user(
        self, user_id: "UUID | None" = None
    ) -> list[ParliamentaryGroupMembershipWithRelationsDTO]:
        """指定されたユーザーIDによって作成された議員団メンバーシップと関連情報を取得する

        Args:
            user_id: フィルタリング対象のユーザーID（Noneの場合は全ユーザー）

        Returns:
            議員団メンバーシップと関連エンティティ（政治家、議員団）を含むDTOのリスト
        """
        from sqlalchemy import text

        # Build SQL query with optional user_id filter
        query_text = """
            SELECT
                pgm.id,
                pgm.politician_id,
                pgm.parliamentary_group_id,
                pgm.start_date,
                pgm.end_date,
                pgm.role,
                pgm.created_by_user_id,
                pgm.created_at,
                pgm.updated_at,
                pg.name as parliamentary_group_name,
                p.name as politician_name
            FROM parliamentary_group_memberships pgm
            LEFT JOIN parliamentary_groups pg ON pgm.parliamentary_group_id = pg.id
            LEFT JOIN politicians p ON pgm.politician_id = p.id
            WHERE pgm.created_by_user_id IS NOT NULL
        """

        params = {}
        if user_id is not None:
            query_text += " AND pgm.created_by_user_id = :user_id"
            params["user_id"] = user_id

        query = text(query_text)
        result = await self.session.execute(query, params)
        rows = result.fetchall()

        # Convert rows to DTOs
        results = []
        for row in rows:
            membership = ParliamentaryGroupMembershipEntity(
                id=row.id,
                politician_id=row.politician_id,
                parliamentary_group_id=row.parliamentary_group_id,
                start_date=row.start_date,
                end_date=row.end_date,
                role=row.role,
                created_by_user_id=row.created_by_user_id,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )

            # Create related entities if they exist
            parliamentary_group = None
            if row.parliamentary_group_name:
                parliamentary_group = ParliamentaryGroup(
                    id=row.parliamentary_group_id,
                    name=row.parliamentary_group_name,
                    conference_id=PLACEHOLDER_CONFERENCE_ID,
                )

            politician = None
            if row.politician_name:
                politician = Politician(
                    id=row.politician_id,
                    name=row.politician_name,
                    prefecture=getattr(row, "politician_prefecture", "") or "",
                    district=getattr(row, "politician_district", "") or "",
                )

            # Create DTO with membership and related entities
            results.append(
                ParliamentaryGroupMembershipWithRelationsDTO(
                    membership=membership,
                    politician=politician,
                    parliamentary_group=parliamentary_group,
                )
            )

        return results

    async def get_membership_creation_statistics_by_user(
        self,
        user_id: "UUID | None" = None,
        start_date: Any | None = None,
        end_date: Any | None = None,
    ) -> dict[UUID, int]:
        """ユーザー別の議員団メンバー作成件数を集計する（データベースレベルで集計）

        Args:
            user_id: フィルタリング対象のユーザーID（Noneの場合は全ユーザー）
            start_date: 開始日時（この日時以降の作業を集計）
            end_date: 終了日時（この日時以前の作業を集計）

        Returns:
            ユーザーIDと件数のマッピング（例: {UUID('...'): 10, UUID('...'): 5}）
        """
        from sqlalchemy import text

        # Build SQL query with GROUP BY
        query_text = """
            SELECT
                created_by_user_id,
                COUNT(*) as count
            FROM parliamentary_group_memberships
            WHERE created_by_user_id IS NOT NULL
        """

        params: dict[str, Any] = {}

        # Add user filter if specified
        if user_id is not None:
            query_text += " AND created_by_user_id = :user_id"
            params["user_id"] = user_id

        # Add date filters if specified
        if start_date is not None:
            query_text += " AND created_at >= :start_date"
            params["start_date"] = start_date

        if end_date is not None:
            query_text += " AND created_at <= :end_date"
            params["end_date"] = end_date

        query_text += " GROUP BY created_by_user_id"

        query = text(query_text)
        result = await self.session.execute(query, params)
        rows = result.fetchall()

        # Convert to dictionary
        statistics: dict[UUID, int] = {}
        for row in rows:
            # Use cast to ensure type safety
            from typing import cast

            statistics[cast(UUID, row.created_by_user_id)] = cast(int, row.count)

        return statistics

    async def get_membership_creation_timeline_statistics(
        self,
        user_id: "UUID | None" = None,
        start_date: Any | None = None,
        end_date: Any | None = None,
        interval: str = "day",
    ) -> list[dict[str, Any]]:
        """時系列の議員団メンバー作成件数を集計する（データベースレベルで集計）

        Args:
            user_id: フィルタリング対象のユーザーID（Noneの場合は全ユーザー）
            start_date: 開始日時
            end_date: 終了日時
            interval: 集計間隔（"day", "week", "month"）

        Returns:
            時系列データのリスト（例: [{"date": "2024-01-01", "count": 5}, ...]）
        """
        from sqlalchemy import text

        # Determine date truncation function based on interval
        date_trunc = INTERVAL_FUNCTIONS.get(interval)
        if date_trunc is None:
            raise ValueError(f"Invalid interval: {interval}")

        # Build SQL query
        query_text = f"""
            SELECT
                {date_trunc} as date,
                COUNT(*) as count
            FROM parliamentary_group_memberships
            WHERE created_by_user_id IS NOT NULL
              AND created_at IS NOT NULL
        """

        params: dict[str, Any] = {}

        # Add user filter if specified
        if user_id is not None:
            query_text += " AND created_by_user_id = :user_id"
            params["user_id"] = user_id

        # Add date filters if specified
        if start_date is not None:
            query_text += " AND created_at >= :start_date"
            params["start_date"] = start_date

        if end_date is not None:
            query_text += " AND created_at <= :end_date"
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
