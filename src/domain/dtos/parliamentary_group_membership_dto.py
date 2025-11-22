"""Parliamentary group membership DTOs for domain layer repository contracts."""

from dataclasses import dataclass

from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.entities.parliamentary_group_membership import (
    ParliamentaryGroupMembership,
)
from src.domain.entities.politician import Politician


@dataclass
class ParliamentaryGroupMembershipWithRelationsDTO:
    """DTO for parliamentary group membership with related entities.

    This DTO is used when retrieving memberships along with their related
    politician and parliamentary group data. It maintains Clean Architecture
    by avoiding dynamic attribute assignment on domain entities.
    """

    membership: ParliamentaryGroupMembership
    politician: Politician | None
    parliamentary_group: ParliamentaryGroup | None
