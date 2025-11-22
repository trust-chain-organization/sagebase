"""Parliamentary group membership repository implementation."""

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.parliamentary_group_membership import (
    ParliamentaryGroupMembership as ParliamentaryGroupMembershipEntity,
)
from src.domain.repositories.parliamentary_group_membership_repository import (
    ParliamentaryGroupMembershipRepository,
)
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl
from src.infrastructure.persistence.sqlalchemy_models import (
    ParliamentaryGroupMembershipModel,
)


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

    async def find_by_created_user(
        self, user_id: "UUID | None" = None
    ) -> list[ParliamentaryGroupMembershipEntity]:
        """指定されたユーザーIDによって作成された議員団メンバーシップを取得する

        Args:
            user_id: フィルタリング対象のユーザーID（Noneの場合は全ユーザー）

        Returns:
            作成された議員団メンバーシップのリスト
        """
        from sqlalchemy import select
        from sqlalchemy.orm import joinedload

        from src.infrastructure.persistence.sqlalchemy_models import (
            ParliamentaryGroupMembershipModel,
        )

        query = (
            select(ParliamentaryGroupMembershipModel)
            .options(
                joinedload(ParliamentaryGroupMembershipModel.parliamentary_group),
                joinedload(ParliamentaryGroupMembershipModel.politician),
            )
            .filter(ParliamentaryGroupMembershipModel.created_by_user_id.is_not(None))
        )

        if user_id is not None:
            query = query.filter(
                ParliamentaryGroupMembershipModel.created_by_user_id == user_id
            )

        result = await self.session.execute(query)
        models = result.scalars().unique().all()

        return [self._to_entity(model) for model in models]
