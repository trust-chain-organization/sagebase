"""Parliamentary group membership domain entity"""

from datetime import date
from uuid import UUID

from .base import BaseEntity


class ParliamentaryGroupMembership(BaseEntity):
    """Parliamentary group membership entity

    Represents a politician's membership in a parliamentary group
    with time bounds and optional role.
    """

    def __init__(
        self,
        politician_id: int,
        parliamentary_group_id: int,
        start_date: date,
        end_date: date | None = None,
        role: str | None = None,
        created_by_user_id: UUID | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.politician_id = politician_id
        self.parliamentary_group_id = parliamentary_group_id
        self.start_date = start_date
        self.end_date = end_date
        self.role = role
        self.created_by_user_id = created_by_user_id

    def is_active(self, as_of_date: date | None = None) -> bool:
        """Check if membership is active as of a specific date"""
        if as_of_date is None:
            as_of_date = date.today()

        if self.start_date > as_of_date:
            return False

        if self.end_date is None:
            return True

        return self.end_date >= as_of_date

    def overlaps_with(self, start_date: date, end_date: date | None = None) -> bool:
        """Check if this membership overlaps with a given date range"""
        # If this membership hasn't started yet compared to the range end
        if end_date and self.start_date > end_date:
            return False

        # If this membership has ended before the range starts
        if self.end_date and self.end_date < start_date:
            return False

        return True
